"""
Unclassified公告复盘工具
分析剩余unclassified公告，给出建议但不修改规则
"""
import argparse
import json
import csv
from pathlib import Path
from datetime import datetime
from collections import Counter
from typing import List, Dict


# 低价值流程类关键词
LOW_VALUE_KEYWORDS = [
    "补充公告", "更正公告", "修订", "说明公告", "股东大会资料", "股东会资料",
    "独立董事意见", "法律意见书", "专项说明", "审计报告", "鉴证报告",
    "核查意见", "承诺函", "公告摘要", "提示性公告", "问询函回复", "监管函回复",
    "申请文件", "上市保荐书", "发行保荐书", "募集说明书", "权益分派",
    "分红派息", "可转债", "转债", "付息", "兑息", "摘牌", "停牌", "复牌"
]

# 疑似高价值/风险类关键词
HIGH_VALUE_KEYWORDS = [
    "安全事故", "事故", "停产", "重大合同", "中标", "签订合同", "签署协议",
    "对外投资", "投资建设", "扩建", "产能", "股权转让", "收购", "出售资产",
    "终止", "募投项目", "药品上市申请", "GMP", "临床试验", "注册申请",
    "异常波动", "立案", "处罚", "诉讼", "仲裁", "减持", "回购",
    "业绩预告", "业绩快报"
]


class UnclassifiedReviewer:
    """Unclassified公告复盘工具"""

    def __init__(self, jsonl_path: str):
        """
        初始化

        Args:
            jsonl_path: JSONL文件路径
        """
        self.jsonl_path = jsonl_path
        self.data = []
        self.unclassified = []
        self.keyword_stats = Counter()

    def load_data(self):
        """加载数据"""
        print(f"📂 加载数据: {self.jsonl_path}")

        with open(self.jsonl_path, 'r', encoding='utf-8') as f:
            self.data = [json.loads(line) for line in f]

        # 筛选unclassified
        self.unclassified = [
            d for d in self.data
            if d.get('announcement_type') == 'unclassified'
        ]

        print(f"✅ 总公告数: {len(self.data)}")
        print(f"✅ Unclassified: {len(self.unclassified)} ({len(self.unclassified)/len(self.data)*100:.1f}%)")

    def analyze_keywords(self, title: str) -> Dict:
        """
        分析标题关键词

        Args:
            title: 标题

        Returns:
            分析结果
        """
        title_lower = title.lower()

        # 命中的低价值关键词
        low_hits = [kw for kw in LOW_VALUE_KEYWORDS if kw in title_lower]

        # 命中的高价值关键词（需排除误报）
        high_hits = []
        for kw in HIGH_VALUE_KEYWORDS:
            if kw in title_lower:
                # 排除"处罚"误报：未被处罚
                if kw in ["处罚"] and any(neg in title_lower for neg in ["未被", "未受到", "未受", "最近五年未"]):
                    continue
                # 排除"回购"误报：回购注销限制性股票
                if kw in ["回购"] and any(equity in title_lower for equity in ["限制性股票", "股票期权", "股权激励"]):
                    continue
                high_hits.append(kw)

        # 统计
        for kw in low_hits:
            self.keyword_stats[f"low:{kw}"] += 1
        for kw in high_hits:
            self.keyword_stats[f"high:{kw}"] += 1

        # 特殊识别：无处罚声明
        if "未被" in title_lower and "处罚" in title_lower:
            return {
                'suggested_action': 'archive',
                'suggested_type': 'regulatory_clean_record',
                'suspicious_unclassified': False,
                'suspicious_reason': '',
                'keyword_hits': '无监管处罚记录声明'
            }

        # 特殊识别：股权激励调整
        if "回购" in title_lower and ("限制性股票" in title_lower or "股票期权" in title_lower):
            return {
                'suggested_action': 'archive',
                'suggested_type': 'equity_incentive_adjustment',
                'suspicious_unclassified': False,
                'suspicious_reason': '',
                'keyword_hits': '股权激励调整'
            }

        # 建议
        if high_hits:
            return {
                'suggested_action': 'manual_review',
                'suggested_type': 'possible_business_or_risk_event',
                'suspicious_unclassified': True,
                'suspicious_reason': f"含高价值关键词: {', '.join(high_hits[:3])}",
                'keyword_hits': ', '.join(high_hits + low_hits)
            }
        elif low_hits:
            return {
                'suggested_action': 'archive',
                'suggested_type': 'possible_routine_notice',
                'suspicious_unclassified': False,
                'suspicious_reason': '',
                'keyword_hits': ', '.join(low_hits)
            }
        else:
            return {
                'suggested_action': 'keep_watch',
                'suggested_type': 'unknown_low_priority',
                'suspicious_unclassified': False,
                'suspicious_reason': '',
                'keyword_hits': ''
            }

    def generate_review_csv(self, output_dir: str):
        """生成复盘CSV"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_path = output_path / f'unclassified_review_{timestamp}.csv'

        fieldnames = [
            'announcement_id', 'stock_code', 'stock_name', 'title',
            'announcement_type_raw', 'action', 'need_ai', 'need_pdf',
            'pre_score', 'matched_keywords', 'reasons',
            'suggested_type', 'suggested_action', 'suspicious_unclassified',
            'suspicious_reason', 'keyword_hits'
        ]

        with open(csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for item in self.unclassified:
                analysis = self.analyze_keywords(item.get('title', ''))

                row = {
                    'announcement_id': item.get('announcement_id', ''),
                    'stock_code': item.get('stock_code', ''),
                    'stock_name': item.get('stock_name', ''),
                    'title': item.get('title', ''),
                    'announcement_type_raw': item.get('announcement_type_raw', ''),
                    'action': item.get('action', ''),
                    'need_ai': item.get('need_ai', ''),
                    'need_pdf': item.get('need_pdf', ''),
                    'pre_score': item.get('pre_score', ''),
                    'matched_keywords': ','.join(item.get('matched_keywords', [])),
                    'reasons': ','.join(item.get('reasons', [])),
                    'suggested_type': analysis['suggested_type'],
                    'suggested_action': analysis['suggested_action'],
                    'suspicious_unclassified': analysis['suspicious_unclassified'],
                    'suspicious_reason': analysis['suspicious_reason'],
                    'keyword_hits': analysis['keyword_hits']
                }
                writer.writerow(row)

        print(f"✅ Review CSV: {csv_path}")
        return csv_path

    def generate_keyword_stats_csv(self, output_dir: str):
        """生成关键词统计CSV"""
        output_path = Path(output_dir)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_path = output_path / f'unclassified_keywords_{timestamp}.csv'

        with open(csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['keyword', 'category', 'count'])

            for kw, count in self.keyword_stats.most_common():
                category, keyword = kw.split(':', 1)
                writer.writerow([keyword, category, count])

        print(f"✅ Keywords CSV: {csv_path}")
        return csv_path

    def generate_summary_md(self, output_dir: str):
        """生成Summary"""
        output_path = Path(output_dir)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        md_path = output_path / f'unclassified_summary_{timestamp}.md'

        # 统计suggested_action
        suggested_actions = Counter()
        suspicious_list = []

        for item in self.unclassified:
            analysis = self.analyze_keywords(item.get('title', ''))
            suggested_actions[analysis['suggested_action']] += 1

            if analysis['suspicious_unclassified']:
                suspicious_list.append({
                    'stock_code': item.get('stock_code', ''),
                    'stock_name': item.get('stock_name', ''),
                    'title': item.get('title', ''),
                    'reason': analysis['suspicious_reason']
                })

        # 生成summary
        lines = []
        lines.append(f"# Unclassified公告复盘报告\n")
        lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        lines.append(f"**数据源**: {Path(self.jsonl_path).name}\n")

        lines.append(f"\n## 统计摘要\n")
        lines.append(f"- 总公告数: {len(self.data)}")
        lines.append(f"- Unclassified数: {len(self.unclassified)}")
        lines.append(f"- Unclassified占比: {len(self.unclassified)/len(self.data)*100:.1f}%\n")

        lines.append(f"\n## Suggested Action分布\n")
        for action, count in suggested_actions.most_common():
            lines.append(f"- {action}: {count} ({count/len(self.unclassified)*100:.1f}%)")

        lines.append(f"\n## Suspicious Unclassified\n")
        lines.append(f"**数量**: {len(suspicious_list)}\n")

        if suspicious_list:
            lines.append(f"**明细**（疑似高价值/风险公告被误判为unclassified）:\n")
            for item in suspicious_list[:20]:
                lines.append(f"- [{item['stock_code']}] {item['stock_name']}")
                lines.append(f"  {item['title']}")
                lines.append(f"  原因: {item['reason']}\n")

        lines.append(f"\n## 高频关键词 Top 30\n")
        for kw, count in self.keyword_stats.most_common(30):
            category, keyword = kw.split(':', 1)
            cat_label = "⚠️ 高价值" if category == "high" else "📋 低价值"
            lines.append(f"- {cat_label} **{keyword}**: {count}次")

        lines.append(f"\n## 建议下一步\n")

        if suspicious_list:
            lines.append(f"1. ⚠️  **优先处理**：{len(suspicious_list)}条疑似高价值公告被误判")
            lines.append(f"   - 建议补充规则覆盖这些关键词")
            lines.append(f"   - 检查是否有真实业务事件被遗漏\n")

        archive_count = suggested_actions.get('archive', 0)
        if archive_count > 0:
            lines.append(f"2. 📋 可归档：{archive_count}条疑似低价值流程公告")
            lines.append(f"   - 建议补充规则自动archive")
            lines.append(f"   - 查看关键词统计决定是否值得\n")

        keep_watch_count = suggested_actions.get('keep_watch', 0)
        if keep_watch_count > 0:
            lines.append(f"3. 🔍 保持观察：{keep_watch_count}条无明显特征")
            lines.append(f"   - 暂时保持watch即可")
            lines.append(f"   - 等积累更多样本再决定\n")

        with open(md_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        print(f"✅ Summary MD: {md_path}")
        return md_path

    def run(self, output_dir: str = "data/review/cninfo_unclassified"):
        """运行复盘"""
        print("=" * 80)
        print("🔍 Unclassified公告复盘工具")
        print("=" * 80)

        self.load_data()

        if not self.unclassified:
            print("\n✅ 没有unclassified公告，无需复盘")
            return

        print(f"\n📊 开始分析 {len(self.unclassified)} 条unclassified公告...\n")

        # 生成报告
        self.generate_review_csv(output_dir)
        self.generate_keyword_stats_csv(output_dir)
        summary_path = self.generate_summary_md(output_dir)

        print("\n" + "=" * 80)
        print("✅ 复盘完成")
        print("=" * 80)

        # 打印摘要
        with open(summary_path, 'r', encoding='utf-8') as f:
            print(f.read())


def main():
    parser = argparse.ArgumentParser(description='Unclassified公告复盘工具')

    parser.add_argument('--input', type=str, help='JSONL文件路径')
    parser.add_argument('--save-csv', action='store_true', help='保存CSV（默认开启）')
    parser.add_argument('--output-dir', type=str, default='data/review/cninfo_unclassified',
                        help='输出目录')

    args = parser.parse_args()

    # 如果没有指定输入，自动找最新的
    if not args.input:
        import glob
        jsonl_files = glob.glob('output/cninfo/*.jsonl')
        if jsonl_files:
            args.input = max(jsonl_files, key=lambda p: Path(p).stat().st_mtime)
            print(f"📁 自动选择最新文件: {args.input}")
        else:
            print("❌ 未找到JSONL文件，请用--input指定")
            return

    reviewer = UnclassifiedReviewer(args.input)
    reviewer.run(args.output_dir)


if __name__ == '__main__':
    main()
