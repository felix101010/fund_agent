#!/usr/bin/env python3
"""
财联社新闻 Daemon 常驻程序
持续采集 + 自动处理 + 样本积累
"""
import argparse
import sys
import time
import signal
from pathlib import Path
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fund_quant.pipelines.news_pipeline.cls_batch_pipeline import ClsBatchPipeline
from fund_quant.pipelines.news_pipeline.pipeline_reporter import PipelineReporter
from fund_quant.pipelines.news_pipeline.pipeline_models import DaemonRunResult


class ClsDaemon:
    """
    财联社新闻 Daemon

    职责：
    1. 定时轮询抓取
    2. 累计统计
    3. 优雅退出
    4. 错误重试
    """

    def __init__(self, args):
        """初始化"""
        self.args = args
        self.daemon_start_time = datetime.now()
        self.run_id = f"daemon_{self.daemon_start_time.strftime('%Y%m%d_%H%M%S')}"

        # 初始化 Pipeline
        self.pipeline = ClsBatchPipeline(
            limit=args.limit,
            only_new=args.only_new,
            verbose=args.verbose,
            model=args.model,
            save_raw=args.save_raw,
            save_events=args.save_events,
            save_jsonl=args.save_jsonl,
            save_summary=args.save_summary,
            output_dir=args.output_dir,
            seen_file_path="data/review/seen_cls_news_ids.txt"
        )

        self.reporter = PipelineReporter()

        # 累计统计
        self.total_loops = 0
        self.total_fetched = 0
        self.total_new = 0
        self.total_ai_success = 0
        self.total_ai_failed = 0

        # 信号处理
        self.should_stop = False
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """处理退出信号"""
        print(f"\n\n收到退出信号，正在优雅退出...")
        self.should_stop = True

    def run(self):
        """运行 Daemon"""
        self._print_startup_info()

        loop_index = 1

        while not self.should_stop:
            daemon_run = DaemonRunResult(
                daemon_start_time=self.daemon_start_time,
                run_id=self.run_id,
                batch_id="",
                loop_index=loop_index,
                status="pending",
                sleep_seconds=self.args.interval
            )

            try:
                # 执行一轮处理
                batch_result = self.pipeline.run_once(
                    run_id=self.run_id,
                    loop_index=loop_index
                )

                daemon_run.batch_id = batch_result.batch_id
                daemon_run.batch_result = batch_result
                daemon_run.status = "success"

                # 更新累计统计
                self.total_loops += 1
                self.total_fetched += batch_result.total_fetched
                self.total_new += batch_result.new_count
                self.total_ai_success += batch_result.ai_success
                self.total_ai_failed += batch_result.ai_failed

                # 打印汇总
                if not self.args.quiet:
                    self.reporter.print_batch_summary(batch_result)
                else:
                    self.reporter.print_daemon_loop_summary(daemon_run)

            except KeyboardInterrupt:
                raise  # 让外层捕获
            except Exception as e:
                daemon_run.status = "failed"
                daemon_run.error = str(e)
                print(f"\n❌ 处理失败: {str(e)}")

                # 错误后等待
                if not self.should_stop:
                    print(f"等待 {self.args.sleep_on_error} 秒后重试...")
                    time.sleep(self.args.sleep_on_error)
                    continue

            # 检查是否达到最大循环次数
            if self.args.max_loops > 0 and loop_index >= self.args.max_loops:
                print(f"\n✅ 达到最大循环次数 {self.args.max_loops}，退出")
                break

            # 等待下一轮
            if not self.should_stop:
                if not self.args.quiet:
                    print(f"\n⏰ 等待 {self.args.interval} 秒后继续...")
                time.sleep(self.args.interval)

            loop_index += 1

        # 打印累计统计
        self._print_final_stats()

    def _print_startup_info(self):
        """打印启动信息"""
        print(f"\n{'='*80}")
        print(f"财联社新闻 Daemon 启动")
        print(f"{'='*80}")
        print(f"run_id: {self.run_id}")
        print(f"启动时间: {self.daemon_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"")
        print(f"配置:")
        print(f"  interval: {self.args.interval}秒")
        print(f"  limit: {self.args.limit}条/轮")
        print(f"  max_loops: {self.args.max_loops if self.args.max_loops > 0 else '无限'}")
        print(f"  only_new: {self.args.only_new}")
        print(f"  save_raw: {self.args.save_raw}")
        print(f"  save_events: {self.args.save_events}")
        print(f"  save_jsonl: {self.args.save_jsonl}")
        print(f"  save_summary: {self.args.save_summary}")
        print(f"  output_dir: {self.args.output_dir}")
        if self.args.model:
            print(f"  model: {self.args.model}")
        print(f"{'='*80}\n")

    def _print_final_stats(self):
        """打印最终统计"""
        runtime = datetime.now() - self.daemon_start_time
        print(f"\n{'='*80}")
        print(f"Daemon 累计统计")
        print(f"{'='*80}")
        print(f"运行时长: {runtime}")
        print(f"总循环次数: {self.total_loops}")
        print(f"总抓取数: {self.total_fetched}")
        print(f"总新增数: {self.total_new}")
        print(f"AI成功: {self.total_ai_success}")
        print(f"AI失败: {self.total_ai_failed}")
        print(f"{'='*80}\n")


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='财联社新闻 Daemon 常驻程序',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--interval',
        type=int,
        default=300,
        help='轮询间隔（秒），默认300秒'
    )

    parser.add_argument(
        '--limit',
        type=int,
        default=20,
        help='每轮抓取数量，默认20'
    )

    parser.add_argument(
        '--max-loops',
        type=int,
        default=0,
        help='最大循环次数，0表示无限循环'
    )

    parser.add_argument(
        '--only-new',
        action='store_true',
        default=True,
        help='只处理新增新闻（默认开启）'
    )

    parser.add_argument(
        '--save-raw',
        action='store_true',
        help='保存原始新闻到 raw_news 表'
    )

    parser.add_argument(
        '--save-events',
        action='store_true',
        help='保存结构化事件到 extracted_events 表'
    )

    parser.add_argument(
        '--save-jsonl',
        action='store_true',
        default=True,
        help='追加保存到单个 JSONL 文件（默认开启）'
    )

    parser.add_argument(
        '--save-summary',
        action='store_true',
        default=True,
        help='每轮生成独立 summary.md（默认开启）'
    )

    parser.add_argument(
        '--output-dir',
        type=str,
        default='data/review/cls_batch_outputs',
        help='输出目录'
    )

    parser.add_argument(
        '--model',
        type=str,
        default=None,
        help='指定 Ollama 模型'
    )

    parser.add_argument(
        '--verbose',
        action='store_true',
        help='详细输出'
    )

    parser.add_argument(
        '--quiet',
        action='store_true',
        help='只打印每轮汇总'
    )

    parser.add_argument(
        '--sleep-on-error',
        type=int,
        default=60,
        help='出错后等待秒数，默认60秒'
    )

    return parser.parse_args()


def main():
    """主函数"""
    args = parse_args()

    # 确保目录存在
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)
    Path("data/review").mkdir(parents=True, exist_ok=True)
    Path("logs").mkdir(parents=True, exist_ok=True)

    # 启动 Daemon
    daemon = ClsDaemon(args)

    try:
        daemon.run()
    except KeyboardInterrupt:
        print(f"\n\n用户中断（Ctrl+C）")
    except Exception as e:
        print(f"\n\n❌ Daemon 异常退出: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
