#!/usr/bin/env python
"""
主题指数 → ETF交易池自动映射系统

功能：
1. 建立指数名称→代码映射表
2. 识别ETF跟踪指数
3. 计算ETF流动性
4. 生成主题ETF池
"""
import sys
import argparse
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import yaml
from difflib import get_close_matches

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from fund_quant.market.tushare_provider import get_tushare_pro
from fund_quant.data.storage import ClickHouseClient
from fund_quant.common.logger import logger


class ThemeETFMapper:
    """主题-ETF映射器"""

    def __init__(self, min_avg_amount: float = 10000000, lookback_days: int = 60, top_n: int = 3):
        """
        初始化

        Args:
            min_avg_amount: 最小平均成交额（默认1000万）
            lookback_days: 回溯天数（默认60天）
            top_n: 每个主题保留ETF数量（默认3只）
        """
        try:
            self.client = ClickHouseClient()
            self.use_clickhouse = True
        except Exception as e:
            logger.warning(f"ClickHouse连接失败，将使用Tushare API: {e}")
            self.client = None
            self.use_clickhouse = False

        self.min_avg_amount = min_avg_amount
        self.lookback_days = lookback_days
        self.top_n = top_n

        # 统计信息
        self.stats = {
            'total_themes': 0,
            'total_etfs': 0,
            'exact_match': 0,
            'manual_match': 0,
            'fuzzy_match': 0,
            'no_match': 0,
            'themes_with_etf': 0,
            'themes_without_etf': 0,
        }

    def build_index_name_mapping(self) -> Dict[str, str]:
        """
        建立指数名称→代码映射表

        Returns:
            {'中证人工智能主题指数': '931071.CSI', ...}
        """
        logger.info("=" * 60)
        logger.info("步骤1: 建立指数名称映射表")
        logger.info("=" * 60)

        df = None

        # 优先从ClickHouse读取
        if self.use_clickhouse:
            sql = """
            SELECT symbol, name
            FROM symbol_master
            WHERE asset_type = 'INDEX' AND status = 'active'
            """
            try:
                df = self.client.query_df(sql)
                # 如果数据量太少，说明symbol_master不全，fallback到Tushare
                if df is not None and len(df) < 3000:
                    logger.warning(f"symbol_master中指数数量较少({len(df)}个)，使用Tushare数据")
                    df = None
            except Exception as e:
                logger.warning(f"从ClickHouse读取失败: {e}")

        # 兜底：从Tushare获取
        if df is None or len(df) == 0:
            logger.info("从Tushare获取指数数据")
            pro = get_tushare_pro()

            import time
            df_sse = pro.index_basic(market='SSE')
            time.sleep(0.5)

            df_szse = pro.index_basic(market='SZSE')
            time.sleep(0.5)

            df_csi = pro.index_basic(market='CSI')

            df = pd.concat([df_sse, df_szse, df_csi], ignore_index=True)
            df = df.rename(columns={'ts_code': 'symbol'})

        # 建立映射
        mapping = {}
        for _, row in df.iterrows():
            name = str(row['name']).strip()
            symbol = str(row['symbol']).strip()
            mapping[name] = symbol

        logger.info(f"✓ 建立指数名称映射: {len(mapping)} 个指数")
        return mapping

    def clean_benchmark_name(self, benchmark: str) -> str:
        """
        清洗benchmark名称

        Args:
            benchmark: 原始benchmark名称

        Returns:
            清洗后的名称
        """
        if pd.isna(benchmark) or not benchmark:
            return ""

        # 去掉常见后缀
        cleaned = str(benchmark).strip()
        cleaned = re.sub(r'收益率$', '', cleaned)
        cleaned = re.sub(r'净值增长率$', '', cleaned)
        cleaned = re.sub(r'\(.*?\)', '', cleaned)  # 去掉括号内容
        cleaned = re.sub(r'（.*?）', '', cleaned)
        cleaned = re.sub(r'\s+', '', cleaned)  # 去掉空格

        # 去掉常见前缀（关键修改）
        cleaned = re.sub(r'^中证', '', cleaned)
        cleaned = re.sub(r'^国证', '', cleaned)
        cleaned = re.sub(r'^上证', '', cleaned)
        cleaned = re.sub(r'^深证', '', cleaned)
        cleaned = re.sub(r'^恒生', '', cleaned)
        cleaned = re.sub(r'^中华', '', cleaned)  # 添加中华前缀处理

        # 去掉常见后缀（关键修改）
        cleaned = re.sub(r'指数$', '', cleaned)
        cleaned = re.sub(r'主题$', '', cleaned)
        cleaned = re.sub(r'产业$', '', cleaned)
        cleaned = re.sub(r'行业$', '', cleaned)

        return cleaned.strip()

    def match_index_code(
        self,
        benchmark: str,
        index_mapping: Dict[str, str],
        manual_mapping: Dict[str, str]
    ) -> Tuple[Optional[str], str, str]:
        """
        匹配指数代码

        Args:
            benchmark: ETF的benchmark名称
            index_mapping: 指数名称映射表
            manual_mapping: 手动映射表

        Returns:
            (index_code, match_method, match_confidence)
        """
        if pd.isna(benchmark) or not benchmark:
            return None, 'none', 'none'

        # 清洗名称
        cleaned_name = self.clean_benchmark_name(benchmark)

        # 第一优先：精确匹配
        if cleaned_name in index_mapping:
            return index_mapping[cleaned_name], 'exact_name', 'exact_name_high'

        # 第二优先：手动映射
        if cleaned_name in manual_mapping:
            return manual_mapping[cleaned_name], 'manual', 'manual_high'

        # 第三优先：模糊匹配
        index_names = list(index_mapping.keys())
        matches = get_close_matches(cleaned_name, index_names, n=1, cutoff=0.92)

        if matches:
            matched_name = matches[0]
            # 计算相似度
            from difflib import SequenceMatcher
            similarity = SequenceMatcher(None, cleaned_name, matched_name).ratio()

            if similarity >= 0.92:
                return index_mapping[matched_name], 'fuzzy', 'fuzzy_medium'
            elif similarity >= 0.80:
                # 低置信度，不允许进入交易池
                return index_mapping[matched_name], 'fuzzy', 'fuzzy_low'

        return None, 'none', 'none'

    def load_manual_mapping(self) -> Dict[str, str]:
        """
        加载手动映射表

        Returns:
            {'清洗后的benchmark名称': 'index_code'}
        """
        mapping_file = project_root / "configs" / "etf_index_mapping.yaml"

        if not mapping_file.exists():
            logger.info("手动映射文件不存在，跳过")
            return {}

        with open(mapping_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        manual_mapping = {}
        if config and 'manual_mappings' in config and config['manual_mappings']:
            for item in config['manual_mappings']:
                if item:  # 确保item不为None
                    benchmark_name = self.clean_benchmark_name(item.get('benchmark_name', ''))
                    tracking_index = item.get('tracking_index', '')
                    if benchmark_name and tracking_index:
                        manual_mapping[benchmark_name] = tracking_index

        logger.info(f"✓ 加载手动映射: {len(manual_mapping)} 条")
        return manual_mapping

    def fetch_etf_with_tracking_index(
        self,
        index_mapping: Dict[str, str],
        manual_mapping: Dict[str, str]
    ) -> pd.DataFrame:
        """
        获取ETF及其跟踪指数

        Returns:
            DataFrame with tracking_index_code
        """
        logger.info("=" * 60)
        logger.info("步骤2: 获取ETF跟踪指数")
        logger.info("=" * 60)

        # 从Tushare获取ETF基础信息
        pro = get_tushare_pro()
        df = pro.fund_basic(market='E', status='L')

        logger.info(f"✓ 获取ETF数据: {len(df)} 只")

        # 转换benchmark为指数代码
        results = []
        for _, row in df.iterrows():
            benchmark = row.get('benchmark', '')
            index_code, match_method, match_confidence = self.match_index_code(
                benchmark, index_mapping, manual_mapping
            )

            results.append({
                'ts_code': row['ts_code'],
                'name': row['name'],
                'benchmark': benchmark,
                'tracking_index_code': index_code,
                'match_method': match_method,
                'match_confidence': match_confidence,
                'list_date': row.get('list_date'),
            })

            # 统计
            if match_method == 'exact_name':
                self.stats['exact_match'] += 1
            elif match_method == 'manual':
                self.stats['manual_match'] += 1
            elif match_method == 'fuzzy':
                self.stats['fuzzy_match'] += 1
            else:
                self.stats['no_match'] += 1

        result_df = pd.DataFrame(results)
        self.stats['total_etfs'] = len(result_df)

        logger.info(f"✓ 转换完成:")
        logger.info(f"  精确匹配: {self.stats['exact_match']}")
        logger.info(f"  手动映射: {self.stats['manual_match']}")
        logger.info(f"  模糊匹配: {self.stats['fuzzy_match']}")
        logger.info(f"  无法匹配: {self.stats['no_match']}")

        # 诊断：打印匹配成功的ETF跟踪的指数
        matched_df = result_df[result_df['tracking_index_code'].notna()]
        if len(matched_df) > 0:
            logger.info(f"\n✓ 匹配成功的ETF跟踪的指数分布:")
            index_counts = matched_df['tracking_index_code'].value_counts()
            for idx, count in index_counts.head(30).items():
                logger.info(f"  {idx}: {count}只ETF")

        return result_df

    def calculate_liquidity(self, etf_df: pd.DataFrame) -> pd.DataFrame:
        """
        计算ETF流动性指标

        Args:
            etf_df: ETF基础信息

        Returns:
            添加流动性指标的DataFrame
        """
        logger.info("=" * 60)
        logger.info("步骤3: 计算ETF流动性")
        logger.info("=" * 60)

        bars_df = None

        # 优先从ClickHouse读取
        if self.use_clickhouse:
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=self.lookback_days)

            # 调试：先查询daily_bars总体情况
            debug_sql = """
            SELECT
                COUNT(*) as total_bars,
                COUNT(DISTINCT symbol) as unique_etfs,
                MIN(trade_date) as min_date,
                MAX(trade_date) as max_date
            FROM daily_bars
            WHERE asset_type = 'ETF'
            """
            try:
                debug_df = self.client.query_df(debug_sql)
                logger.info(f"\n【调试信息1】daily_bars表统计:")
                logger.info(f"  总记录数: {debug_df.iloc[0]['total_bars']}")
                logger.info(f"  唯一ETF数: {debug_df.iloc[0]['unique_etfs']}")
                logger.info(f"  日期范围: {debug_df.iloc[0]['min_date']} ~ {debug_df.iloc[0]['max_date']}")
            except Exception as e:
                logger.error(f"调试查询失败: {e}")

            # 调试：随机打印5个ETF代码
            sample_sql = """
            SELECT DISTINCT symbol
            FROM daily_bars
            WHERE asset_type = 'ETF'
            LIMIT 5
            """
            try:
                sample_df = self.client.query_df(sample_sql)
                logger.info(f"\n【调试信息2】daily_bars中的ETF代码示例:")
                for symbol in sample_df['symbol'].tolist():
                    logger.info(f"  {symbol}")
            except Exception as e:
                logger.error(f"示例查询失败: {e}")

            # 调试：检查etf_df中的代码格式
            logger.info(f"\n【调试信息3】etf_df中的ETF代码示例:")
            for code in etf_df['ts_code'].head(5).tolist():
                logger.info(f"  {code}")

            # 调试：检查日期过滤范围
            logger.info(f"\n【调试信息4】日期过滤范围:")
            logger.info(f"  start_date: {start_date}")
            logger.info(f"  end_date: {end_date}")
            logger.info(f"  lookback_days: {self.lookback_days}")

            sql = f"""
            SELECT
                symbol,
                trade_date,
                close,
                amount
            FROM daily_bars
            WHERE asset_type = 'ETF'
              AND trade_date >= '{start_date}'
              AND trade_date <= '{end_date}'
            ORDER BY symbol, trade_date
            """

            try:
                bars_df = self.client.query_df(sql)
                logger.info(f"\n【调试信息5】查询结果:")
                logger.info(f"  返回记录数: {len(bars_df)}")
                if len(bars_df) > 0:
                    logger.info(f"  唯一ETF数: {bars_df['symbol'].nunique()}")
                    logger.info(f"  日期范围: {bars_df['trade_date'].min()} ~ {bars_df['trade_date'].max()}")
                    logger.info(f"  示例数据:")
                    logger.info(f"{bars_df.head(3).to_string()}")
            except Exception as e:
                logger.warning(f"从ClickHouse读取行情失败: {e}")

        if bars_df is None or len(bars_df) == 0:
            logger.warning("没有ETF行情数据，所有ETF标记为不活跃")
            # 添加空列
            etf_df['avg_amount_5d'] = 0
            etf_df['avg_amount_20d'] = 0
            etf_df['avg_amount_60d'] = 0
            etf_df['latest_amount'] = 0
            etf_df['latest_close'] = 0
            etf_df['trading_days_count'] = 0
            etf_df['is_active'] = False
            return etf_df

        # 调试：检查代码匹配情况
        etf_codes_in_df = set(etf_df['ts_code'].unique())
        etf_codes_in_bars = set(bars_df['symbol'].unique())
        matched_codes = etf_codes_in_df & etf_codes_in_bars

        logger.info(f"\n【调试信息6】代码匹配情况:")
        logger.info(f"  etf_df中的ETF数: {len(etf_codes_in_df)}")
        logger.info(f"  bars_df中的ETF数: {len(etf_codes_in_bars)}")
        logger.info(f"  匹配成功的ETF数: {len(matched_codes)}")

        if len(matched_codes) > 0:
            logger.info(f"  匹配成功示例:")
            for code in list(matched_codes)[:5]:
                logger.info(f"    {code}")

        if len(matched_codes) < len(etf_codes_in_df):
            unmatched = etf_codes_in_df - etf_codes_in_bars
            logger.info(f"  未匹配的ETF数: {len(unmatched)}")
            logger.info(f"  未匹配示例:")
            for code in list(unmatched)[:5]:
                logger.info(f"    {code}")

        # 计算流动性指标
        liquidity_results = []

        for etf_code in etf_df['ts_code'].unique():
            etf_bars = bars_df[bars_df['symbol'] == etf_code].sort_values('trade_date')

            if len(etf_bars) == 0:
                liquidity_results.append({
                    'ts_code': etf_code,
                    'avg_amount_5d': 0,
                    'avg_amount_20d': 0,
                    'avg_amount_60d': 0,
                    'latest_amount': 0,
                    'latest_close': 0,
                    'trading_days_count': 0,
                    'is_active': False,
                })
                continue

            # 最近N天平均成交额（amount单位是千元，需要转换为元）
            avg_amount_5d = etf_bars.tail(5)['amount'].mean() * 1000 if len(etf_bars) >= 5 else 0
            avg_amount_20d = etf_bars.tail(20)['amount'].mean() * 1000 if len(etf_bars) >= 20 else 0
            avg_amount_60d = etf_bars['amount'].mean() * 1000

            # 最新数据
            latest = etf_bars.iloc[-1]
            latest_amount = latest['amount'] * 1000
            latest_close = latest['close']

            # 交易天数
            trading_days_count = len(etf_bars.tail(20))

            # 是否活跃
            is_active = (
                trading_days_count >= 15 and
                avg_amount_20d >= self.min_avg_amount
            )

            liquidity_results.append({
                'ts_code': etf_code,
                'avg_amount_5d': avg_amount_5d,
                'avg_amount_20d': avg_amount_20d,
                'avg_amount_60d': avg_amount_60d,
                'latest_amount': latest_amount,
                'latest_close': latest_close,
                'trading_days_count': trading_days_count,
                'is_active': is_active,
            })

        liquidity_df = pd.DataFrame(liquidity_results)

        # 调试：统计活跃ETF
        active_count = liquidity_df['is_active'].sum()
        logger.info(f"\n【调试信息7】流动性计算结果:")
        logger.info(f"  计算了{len(liquidity_df)}只ETF的流动性")
        logger.info(f"  活跃ETF数: {active_count}")
        logger.info(f"  流动性阈值: {self.min_avg_amount/10000:.0f}万")

        if active_count > 0:
            active_etfs = liquidity_df[liquidity_df['is_active'] == True].head(5)
            logger.info(f"  活跃ETF示例:")
            for _, row in active_etfs.iterrows():
                logger.info(f"    {row['ts_code']}: 20日均{row['avg_amount_20d']/10000:.0f}万, 交易天数{row['trading_days_count']}")

        # 合并
        result_df = etf_df.merge(liquidity_df, on='ts_code', how='left')

        # 填充缺失值
        result_df = result_df.fillna({
            'avg_amount_5d': 0,
            'avg_amount_20d': 0,
            'avg_amount_60d': 0,
            'latest_amount': 0,
            'latest_close': 0,
            'trading_days_count': 0,
            'is_active': False,
        })

        active_count = result_df['is_active'].sum()
        logger.info(f"✓ 流动性计算完成: {active_count}/{len(result_df)} 只ETF活跃")

        return result_df

    def load_theme_config(self) -> List[Dict]:
        """
        加载主题配置

        Returns:
            主题列表
        """
        config_file = project_root / "configs" / "themes" / "theme_index_mapping.yaml"

        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        themes = []
        for mapping in config['mappings']:
            themes.append({
                'theme_id': mapping['theme_id'],
                'theme_name': mapping['theme_name'],
                'primary_index_code': mapping['primary_index']['code'],
                'primary_index_name': mapping['primary_index']['name'],
                'acceptable_tracking_indices': mapping.get('acceptable_tracking_indices', []),
            })

        self.stats['total_themes'] = len(themes)
        return themes

    def match_etf_to_theme(
        self,
        etf_row: pd.Series,
        theme: Dict,
        index_mapping: Dict[str, str]
    ) -> Tuple[bool, str]:
        """
        判断ETF是否匹配主题

        Args:
            etf_row: ETF行数据
            theme: 主题配置
            index_mapping: 指数名称→代码映射

        Returns:
            (是否匹配, 匹配关系类型)
        """
        tracking_code = etf_row.get('tracking_index_code')
        if pd.isna(tracking_code):
            return False, 'rejected'

        primary_code = theme['primary_index_code']
        acceptable_indices = theme['acceptable_tracking_indices']

        # 1. 精确匹配primary_index
        if tracking_code == primary_code:
            return True, 'same_as_primary'

        # 2. 匹配acceptable_tracking_indices中的指数代码
        if tracking_code in acceptable_indices:
            return True, 'accepted_alternative'

        # 3. 匹配acceptable_tracking_indices中的指数名称关键词
        benchmark = str(etf_row.get('benchmark', ''))
        cleaned_benchmark = self.clean_benchmark_name(benchmark)

        for acceptable in acceptable_indices:
            # 如果是指数代码格式（包含.），跳过
            if '.' in acceptable:
                continue
            # 如果是名称关键词，检查是否包含
            if acceptable in cleaned_benchmark or acceptable in benchmark:
                return True, 'accepted_alternative'

        return False, 'rejected'

    def build_theme_etf_pool(
        self,
        themes: List[Dict],
        etf_df: pd.DataFrame,
        index_mapping: Dict[str, str]
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        构建主题ETF池

        Args:
            themes: 主题列表
            etf_df: ETF数据（含流动性）
            index_mapping: 指数名称→代码映射

        Returns:
            (theme_etf_pool, report)
        """
        logger.info("=" * 60)
        logger.info("步骤4: 构建主题ETF池")
        logger.info("=" * 60)

        pool_results = []
        report_results = []

        for theme in themes:
            theme_id = theme['theme_id']
            theme_name = theme['theme_name']
            primary_code = theme['primary_index_code']
            primary_name = theme['primary_index_name']

            # 匹配ETF：使用新的匹配逻辑
            matched_etfs = []
            for _, etf_row in etf_df.iterrows():
                is_match, relation = self.match_etf_to_theme(etf_row, theme, index_mapping)
                if is_match:
                    etf_dict = etf_row.to_dict()
                    etf_dict['tracking_index_relation'] = relation
                    matched_etfs.append(etf_dict)

            matched_df = pd.DataFrame(matched_etfs) if matched_etfs else pd.DataFrame()

            matched_count = len(matched_etfs)

            # 筛选活跃ETF
            if len(matched_df) > 0:
                active_etfs = matched_df[matched_df['is_active'] == True].copy()
            else:
                active_etfs = pd.DataFrame()

            # 排序
            if len(active_etfs) > 0:
                active_etfs = active_etfs.sort_values('avg_amount_20d', ascending=False)

            # 取Top N
            selected_etfs = active_etfs.head(self.top_n) if len(active_etfs) > 0 else pd.DataFrame()
            selected_count = len(selected_etfs)

            # 添加排名
            for rank, (_, etf) in enumerate(selected_etfs.iterrows(), 1):
                pool_results.append({
                    'theme': theme_id,
                    'theme_name': theme_name,
                    'primary_index_code': primary_code,
                    'primary_index_name': primary_name,
                    'etf_code': etf['ts_code'],
                    'etf_name': etf['name'],
                    'tracking_index_code': etf['tracking_index_code'],
                    'tracking_index_relation': etf['tracking_index_relation'],
                    'match_method': etf['match_method'],
                    'match_confidence': etf['match_confidence'],
                    'avg_amount_5d': etf['avg_amount_5d'],
                    'avg_amount_20d': etf['avg_amount_20d'],
                    'avg_amount_60d': etf['avg_amount_60d'],
                    'latest_amount': etf['latest_amount'],
                    'latest_close': etf['latest_close'],
                    'rank_in_theme': rank,
                    'trading_days_count': etf['trading_days_count'],
                    'is_active': etf['is_active'],
                    'reason': f'Top {rank} by avg_amount_20d',
                })

            # 生成报告
            if selected_count > 0:
                best_etf = selected_etfs.iloc[0]
                status = 'ok'
                warning = ''
                self.stats['themes_with_etf'] += 1
            elif matched_count > 0:
                status = 'low_liquidity'
                warning = f'Matched {matched_count} ETFs but all below liquidity threshold'
                best_etf = None
                self.stats['themes_without_etf'] += 1
            else:
                status = 'no_etf_found'
                warning = f'No ETF tracks index {primary_code}'
                best_etf = None
                self.stats['themes_without_etf'] += 1

            report_results.append({
                'theme': theme_id,
                'theme_name': theme_name,
                'primary_index_code': primary_code,
                'primary_index_name': primary_name,
                'matched_etf_count': matched_count,
                'selected_etf_count': selected_count,
                'best_etf': best_etf['ts_code'] if best_etf is not None else '',
                'best_avg_amount_20d': best_etf['avg_amount_20d'] if best_etf is not None else 0,
                'status': status,
                'warning': warning,
            })

        pool_df = pd.DataFrame(pool_results)
        report_df = pd.DataFrame(report_results)

        logger.info(f"✓ ETF池构建完成:")
        logger.info(f"  有ETF的主题: {self.stats['themes_with_etf']}/{self.stats['total_themes']}")
        logger.info(f"  无ETF的主题: {self.stats['themes_without_etf']}/{self.stats['total_themes']}")

        return pool_df, report_df

    def print_summary(self, pool_df: pd.DataFrame, report_df: pd.DataFrame):
        """打印汇总信息"""
        logger.info("\n" + "=" * 60)
        logger.info("最终汇总")
        logger.info("=" * 60)

        # 1. 每个主题选中的ETF
        logger.info("\n【1. 每个主题选中的ETF】")

        if len(report_df) == 0:
            logger.warning("  没有主题数据")
            return

        for _, theme_info in report_df.iterrows():
            theme = theme_info['theme']
            theme_etfs = pool_df[pool_df['theme'] == theme] if len(pool_df) > 0 else pd.DataFrame()

            logger.info(f"\n{theme} ({theme_info['theme_name']}):")
            logger.info(f"  主题分析指数: {theme_info['primary_index_code']} - {theme_info['primary_index_name']}")

            if len(theme_etfs) > 0:
                for _, etf in theme_etfs.iterrows():
                    logger.info(f"  [{etf['rank_in_theme']}] {etf['etf_code']} {etf['etf_name']}")
                    logger.info(f"      跟踪指数: {etf['tracking_index_code']} ({etf['tracking_index_relation']})")
                    logger.info(f"      成交额20日均: {etf['avg_amount_20d']/10000:.0f}万")
                    logger.info(f"      匹配方式: {etf['match_confidence']}")
            else:
                logger.info(f"  ❌ {theme_info['warning']}")

        # 2. 无ETF主题
        logger.info("\n【2. 无ETF主题】")
        no_etf_themes = report_df[report_df['status'] == 'no_etf_found']
        if len(no_etf_themes) > 0:
            for _, theme in no_etf_themes.iterrows():
                logger.info(f"  ❌ {theme['theme']} - {theme['warning']}")
        else:
            logger.info("  ✓ 所有主题都有ETF")

        # 3. 流动性不足主题
        logger.info("\n【3. 流动性不足主题】")
        low_liq_themes = report_df[report_df['status'] == 'low_liquidity']
        if len(low_liq_themes) > 0:
            for _, theme in low_liq_themes.iterrows():
                logger.info(f"  ⚠ {theme['theme']} - {theme['warning']}")
        else:
            logger.info("  ✓ 无流动性不足主题")

        # 4. 只有模糊匹配主题
        logger.info("\n【4. 只有模糊匹配主题】")
        if len(pool_df) > 0 and 'match_confidence' in pool_df.columns:
            fuzzy_etfs = pool_df[pool_df['match_confidence'] == 'fuzzy_medium']
            fuzzy_themes = fuzzy_etfs['theme'].unique()
            if len(fuzzy_themes) > 0:
                for theme in fuzzy_themes:
                    logger.info(f"  ⚠ {theme}")
            else:
                logger.info("  ✓ 无模糊匹配主题")
        else:
            logger.info("  ✓ 无模糊匹配主题")

        # 5. 统计
        logger.info("\n【5. 统计数据】")
        logger.info(f"  总主题数: {self.stats['total_themes']}")
        logger.info(f"  有ETF主题: {self.stats['themes_with_etf']} ({self.stats['themes_with_etf']/self.stats['total_themes']*100:.1f}%)")
        logger.info(f"  无ETF主题: {self.stats['themes_without_etf']} ({self.stats['themes_without_etf']/self.stats['total_themes']*100:.1f}%)")
        logger.info(f"  总ETF数: {self.stats['total_etfs']}")
        logger.info(f"  精确匹配: {self.stats['exact_match']} ({self.stats['exact_match']/self.stats['total_etfs']*100:.1f}%)")
        logger.info(f"  手动映射: {self.stats['manual_match']} ({self.stats['manual_match']/self.stats['total_etfs']*100:.1f}%)")
        logger.info(f"  模糊匹配: {self.stats['fuzzy_match']} ({self.stats['fuzzy_match']/self.stats['total_etfs']*100:.1f}%)")
        logger.info(f"  无法匹配: {self.stats['no_match']} ({self.stats['no_match']/self.stats['total_etfs']*100:.1f}%)")

        # 6. 改进建议
        logger.info("\n【6. 改进建议】")
        if self.stats['themes_without_etf'] > 0:
            logger.info("  • 考虑为无ETF主题添加手动映射")
        if self.stats['no_match'] > 100:
            logger.info("  • benchmark转换成功率较低，建议扩充手动映射表")
        if len(fuzzy_themes) > 3:
            logger.info("  • 模糊匹配主题较多，建议人工验证准确性")
        if len(low_liq_themes) > 0:
            logger.info("  • 部分主题流动性不足，考虑降低流动性阈值")

        logger.info("=" * 60)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='构建主题ETF池',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('--top-n', type=int, default=3, help='每个主题保留ETF数量')
    parser.add_argument('--min-avg-amount', type=float, default=10000000, help='最小平均成交额（元）')
    parser.add_argument('--lookback', type=int, default=60, help='回溯天数')
    parser.add_argument('--output', type=str, default='data/processed/theme_etf_pool.csv', help='输出文件路径')

    args = parser.parse_args()

    try:
        # 创建输出目录
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 初始化
        mapper = ThemeETFMapper(
            min_avg_amount=args.min_avg_amount,
            lookback_days=args.lookback,
            top_n=args.top_n
        )

        # 步骤1: 建立指数名称映射
        index_mapping = mapper.build_index_name_mapping()

        # 步骤1.5: 加载手动映射
        manual_mapping = mapper.load_manual_mapping()

        # 步骤2: 获取ETF跟踪指数
        etf_df = mapper.fetch_etf_with_tracking_index(index_mapping, manual_mapping)

        # 步骤3: 计算流动性
        etf_df = mapper.calculate_liquidity(etf_df)

        # 步骤4: 加载主题配置
        themes = mapper.load_theme_config()

        # 诊断：检查我们的22个主题指数有多少被ETF跟踪
        theme_indices = [t['primary_index_code'] for t in themes]
        matched_etf_df = etf_df[etf_df['tracking_index_code'].notna()]
        matched_theme_indices = matched_etf_df[matched_etf_df['tracking_index_code'].isin(theme_indices)]['tracking_index_code'].unique()
        logger.info(f"\n✓ 我们的22个主题指数中，有{len(matched_theme_indices)}个被ETF直接跟踪:")
        for idx in matched_theme_indices:
            etf_count = len(matched_etf_df[matched_etf_df['tracking_index_code'] == idx])
            theme_name = next((t['theme_name'] for t in themes if t['primary_index_code'] == idx), idx)
            logger.info(f"  {idx} ({theme_name}): {etf_count}只ETF")

        # 步骤5: 构建主题ETF池（使用新的匹配逻辑，包含acceptable_tracking_indices）
        pool_df, report_df = mapper.build_theme_etf_pool(themes, etf_df, index_mapping)

        # 保存文件
        pool_df.to_csv(output_path, index=False, encoding='utf-8-sig')
        logger.info(f"\n✓ ETF池已保存: {output_path}")

        report_path = output_path.parent / "theme_etf_pool_report.csv"
        report_df.to_csv(report_path, index=False, encoding='utf-8-sig')
        logger.info(f"✓ 报告已保存: {report_path}")

        # 打印汇总
        mapper.print_summary(pool_df, report_df)

        sys.exit(0)

    except KeyboardInterrupt:
        logger.warning("\n⚠ 用户中断")
        sys.exit(1)

    except Exception as e:
        logger.error(f"\n✗ 任务失败: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
