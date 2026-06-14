"""
巨潮资讯守护进程
定期采集最新公告
"""
import argparse
import time
import signal
import sys
from datetime import datetime
from fund_quant.pipelines.announcement_pipeline import CninfoBatchPipeline


class CninfoDaemon:
    """巨潮资讯守护进程"""

    def __init__(self, interval: int, limit: int, output_dir: str, save_raw: bool, save_jsonl: bool, save_csv: bool):
        self.interval = interval
        self.limit = limit
        self.output_dir = output_dir
        self.save_raw = save_raw
        self.save_jsonl = save_jsonl
        self.save_csv = save_csv
        self.running = True
        self.pipeline = CninfoBatchPipeline()

        # 注册信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """信号处理器"""
        print(f"\n🛑 收到停止信号，优雅退出...")
        self.running = False

    def run(self):
        """运行守护进程"""
        print("=" * 80)
        print("🔄 巨潮资讯守护进程启动")
        print("=" * 80)
        print(f"采集间隔: {self.interval}秒")
        print(f"每次限制: {self.limit}条")
        print(f"输出目录: {self.output_dir}")
        print(f"Ctrl+C 停止")
        print("=" * 80)

        iteration = 0

        while self.running:
            iteration += 1
            print(f"\n🔄 第 {iteration} 次采集 [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]")

            try:
                batch_result = self.pipeline.run(
                    limit=self.limit,
                    save_raw=self.save_raw,
                    save_jsonl=self.save_jsonl,
                    save_csv=self.save_csv,
                    output_dir=self.output_dir
                )

                print(f"✅ 采集完成: 新增 {batch_result.new_count}，处理 {batch_result.processed_count}")

            except Exception as e:
                print(f"❌ 采集失败: {e}")

            # 等待下一次
            if self.running:
                print(f"⏳ 等待 {self.interval} 秒...")
                for _ in range(self.interval):
                    if not self.running:
                        break
                    time.sleep(1)

        print("\n✅ 守护进程已停止")


def main():
    parser = argparse.ArgumentParser(description='巨潮资讯守护进程')

    parser.add_argument('--interval', type=int, default=600, help='采集间隔（秒），默认600秒')
    parser.add_argument('--limit', type=int, default=50, help='每次采集数量，默认50')
    parser.add_argument('--save-raw', action='store_true', help='保存原始数据')
    parser.add_argument('--save-jsonl', action='store_true', default=True, help='保存JSONL')
    parser.add_argument('--save-csv', action='store_true', default=True, help='保存CSV')
    parser.add_argument('--output-dir', type=str, default='output/cninfo', help='输出目录')

    args = parser.parse_args()

    daemon = CninfoDaemon(
        interval=args.interval,
        limit=args.limit,
        output_dir=args.output_dir,
        save_raw=args.save_raw,
        save_jsonl=args.save_jsonl,
        save_csv=args.save_csv
    )

    daemon.run()


if __name__ == '__main__':
    main()
