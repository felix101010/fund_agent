#!/usr/bin/env python3
"""
华尔街见闻新闻 Daemon 常驻程序
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

from fund_quant.pipelines.news_pipeline.news_batch_pipeline import NewsBatchPipeline
from fund_quant.data_sources.news.wallstreetcn_collector import WallstreetcnCollector
from fund_quant.pipelines.news_pipeline.pipeline_models import DaemonRunResult


class WallstreetcnDaemon:
    """
    华尔街见闻新闻 Daemon

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

        # 初始化采集器
        self.collector = WallstreetcnCollector(rss_url=args.rss_url)

        # 初始化 Pipeline
        self.pipeline = NewsBatchPipeline(
            source="wallstreetcn",
            source_role="market_context",
            collector=self.collector,
            limit=args.limit,
            only_new=args.only_new,
            verbose=args.verbose,
            model=args.model,
            save_raw=args.save_raw,
            save_events=args.save_events,
            save_jsonl=args.save_jsonl,
            save_by_source_jsonl=True,
            save_global_jsonl=True,
            save_summary=args.save_summary,
            output_dir=args.output_dir,
        )

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

                print(f"\n累计统计（已运行 {self.total_loops} 轮）：")
                print(f"  总抓取: {self.total_fetched}")
                print(f"  总新增: {self.total_new}")
                print(f"  AI成功: {self.total_ai_success}")
                print(f"  AI失败: {self.total_ai_failed}")

            except Exception as e:
                daemon_run.status = "failed"
                daemon_run.error = str(e)
                print(f"\n处理失败: {e}")

                # 出错后等待
                print(f"等待 {self.args.sleep_on_error} 秒后重试...")
                time.sleep(self.args.sleep_on_error)
                loop_index += 1
                continue

            # 检查是否达到最大循环次数
            if self.args.max_loops > 0 and loop_index >= self.args.max_loops:
                print(f"\n已达到最大循环次数 {self.args.max_loops}，退出")
                break

            # 休眠
            if not self.should_stop and (self.args.max_loops == 0 or loop_index < self.args.max_loops):
                print(f"\n等待 {self.args.interval} 秒...\n")
                for _ in range(self.args.interval):
                    if self.should_stop:
                        break
                    time.sleep(1)

            loop_index += 1

        # 打印最终统计
        self._print_final_stats()

    def _print_startup_info(self):
        """打印启动信息"""
        print(f"\n{'='*80}")
        print(f"华尔街见闻新闻 Daemon 启动")
        print(f"{'='*80}")
        print(f"run_id: {self.run_id}")
        print(f"启动时间: {self.daemon_start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"\n配置:")
        print(f"  interval: {self.args.interval}秒")
        print(f"  limit: {self.args.limit}条/轮")
        print(f"  max_loops: {self.args.max_loops if self.args.max_loops > 0 else '无限'}")
        print(f"  only_new: {self.args.only_new}")
        print(f"  save_raw: {self.args.save_raw}")
        print(f"  save_events: {self.args.save_events}")
        print(f"  save_jsonl: {self.args.save_jsonl}")
        print(f"  save_summary: {self.args.save_summary}")
        print(f"  output_dir: {self.args.output_dir}")
        if self.args.rss_url:
            print(f"  rss_url: {self.args.rss_url}")
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
        description='华尔街见闻新闻 Daemon 常驻程序',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        '--interval',
        type=int,
        default=300,
        help='轮询间隔（秒），默认300秒（5分钟）'
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
        help='追加保存到 JSONL 文件（默认开启）'
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
        default='data/review/news_batch_outputs',
        help='输出目录'
    )

    parser.add_argument(
        '--rss-url',
        type=str,
        default=None,
        help='自定义 RSS URL，默认使用 http://127.0.0.1:1201/wallstreetcn/live/global/1'
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
    args = parse_args()
    daemon = WallstreetcnDaemon(args)
    daemon.run()


if __name__ == '__main__':
    main()
