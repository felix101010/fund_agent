"""
Tushare 数据提供者
提供 ETF 基础信息、日线行情、分钟行情等数据
支持自定义 API 地址和本地缓存
"""
import os
import time
import pandas as pd
import tushare as ts
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path

from fund_quant.common.config import settings
from fund_quant.common.logger import logger


def get_tushare_pro():
    """
    获取 Tushare Pro API 实例
    支持自定义 API 地址

    Returns:
        Tushare Pro API 实例

    Raises:
        ValueError: 如果未配置 TUSHARE_TOKEN
    """
    if not settings.tushare_token:
        raise ValueError(
            "未配置 TUSHARE_TOKEN。\n"
            "请在 .env 文件中设置 TUSHARE_TOKEN"
        )

    # 设置 token
    ts.set_token(settings.tushare_token)

    # 初始化 API
    pro = ts.pro_api()

    # 如果配置了自定义 API 地址，则修改
    if settings.tushare_api_url:
        pro._DataApi__http_url = settings.tushare_api_url
        logger.info(f"Tushare Pro API 初始化成功（自定义地址: {settings.tushare_api_url}）")

        # 特殊设置：实时行情接口需要额外配置
        try:
            from tushare.stock import cons as ct
            ct.verify_token_url = f"{settings.tushare_api_url}/dataapi/sdk-event"
            logger.info("实时行情接口已配置")
        except Exception as e:
            logger.warning(f"实时行情接口配置失败: {e}")
    else:
        logger.info("Tushare Pro API 初始化成功（官方地址）")

    return pro


def fetch_etf_basic(save_csv: bool = True) -> Optional[pd.DataFrame]:
    """
    获取 ETF 基础信息

    Args:
        save_csv: 是否保存到 CSV

    Returns:
        ETF 基础信息 DataFrame
    """
    logger.info("调用 Tushare 接口: pro.etf_basic()")

    try:
        pro = get_tushare_pro()
        df = pro.fund_basic(
            market='E',  # E=ETF
            status='L'   # L=上市
        )

        if df is None or len(df) == 0:
            logger.warning("返回数据为空")
            return None

        logger.info(f"成功获取 {len(df)} 条 ETF 基础信息")
        logger.debug(f"前 5 条数据:\n{df.head()}")

        if save_csv:
            csv_path = settings.data_dir / "raw" / "tushare_etf_basic.csv"
            csv_path.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(csv_path, index=False, encoding='utf-8-sig')
            logger.info(f"已保存到: {csv_path}")

        return df

    except Exception as e:
        logger.error(f"获取失败: {e}")
        return None


def fetch_etf_daily(
    ts_code: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    use_cache: bool = True,
    force_refresh: bool = False,
    cache_expire_days: int = 1
) -> Optional[pd.DataFrame]:
    """
    获取 ETF 日线行情（支持本地缓存）

    Args:
        ts_code: ETF 代码，如 159272.SZ
        start_date: 开始日期，格式 YYYYMMDD
        end_date: 结束日期，格式 YYYYMMDD
        use_cache: 是否使用缓存
        force_refresh: 是否强制刷新（忽略缓存）
        cache_expire_days: 缓存有效期（天），默认1天

    Returns:
        ETF 日线行情 DataFrame
    """
    # 缓存路径
    cache_dir = settings.data_dir / "raw" / "cache" / "etf_daily"
    cache_dir.mkdir(parents=True, exist_ok=True)

    # 缓存文件名包含 ts_code, start_date, end_date
    cache_file = cache_dir / f"{ts_code}_{start_date or 'none'}_{end_date or 'none'}.csv"

    logger.info(f"获取 ETF 日线: {ts_code}")
    logger.info(f"  日期范围: {start_date or '最早'} ~ {end_date or '最新'}")
    logger.debug(f"  缓存文件: {cache_file.name}")

    # 检查缓存
    cache_valid = False
    if use_cache and not force_refresh and cache_file.exists():
        try:
            # 检查缓存文件修改时间
            cache_mtime = cache_file.stat().st_mtime
            cache_age = (datetime.now() - datetime.fromtimestamp(cache_mtime)).days

            logger.debug(f"  缓存年龄: {cache_age} 天")

            if cache_age <= cache_expire_days:
                df = pd.read_csv(cache_file, encoding='utf-8-sig')

                if df is not None and len(df) > 0:
                    # 检查缓存数据的日期范围
                    cache_min_date = df['trade_date'].min()
                    cache_max_date = df['trade_date'].max()

                    logger.debug(f"  缓存日期范围: {cache_min_date} ~ {cache_max_date}")

                    # 判断缓存是否覆盖请求范围
                    cache_covers_request = True

                    if start_date and cache_min_date > start_date:
                        logger.debug(f"  缓存开始日期 {cache_min_date} 晚于请求 {start_date}")
                        cache_covers_request = False

                    if end_date and cache_max_date < end_date:
                        logger.debug(f"  缓存结束日期 {cache_max_date} 早于请求 {end_date}")
                        cache_covers_request = False

                    # 如果没有指定 end_date，检查缓存是否包含最新数据（今天或昨天）
                    if not end_date:
                        today = datetime.now().strftime("%Y%m%d")
                        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")

                        if cache_max_date < yesterday:
                            logger.debug(f"  缓存最新日期 {cache_max_date} 过旧（今天: {today}）")
                            cache_covers_request = False

                    if cache_covers_request:
                        logger.info(f"  使用缓存 ({len(df)} 条)")
                        cache_valid = True
                        return df
                    else:
                        logger.info("  缓存不满足请求范围，重新获取")
            else:
                logger.debug(f"  缓存已过期（>{cache_expire_days}天）")

        except Exception as e:
            logger.warning(f"  缓存读取失败: {e}")

    # 请求 Tushare
    if not cache_valid:
        logger.info("  调用 Tushare API...")

        max_retries = 2
        for attempt in range(max_retries):
            try:
                pro = get_tushare_pro()

                # 请求前延迟
                time.sleep(0.8)

                df = pro.fund_daily(
                    ts_code=ts_code,
                    start_date=start_date,
                    end_date=end_date,
                    fields='ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount'
                )

                if df is None or len(df) == 0:
                    logger.warning("  返回数据为空")
                    return None

                logger.info(f"  成功获取 {len(df)} 条数据")
                logger.info(f"  日期范围: {df['trade_date'].min()} ~ {df['trade_date'].max()}")

                # 保存缓存
                if use_cache:
                    try:
                        df.to_csv(cache_file, index=False, encoding='utf-8-sig')
                        logger.debug("  已保存缓存")
                    except Exception as e:
                        logger.warning(f"  缓存保存失败: {e}")

                return df

            except Exception as e:
                error_msg = str(e)

                # 检测频率限制
                if "频率" in error_msg or "冷却" in error_msg:
                    if attempt < max_retries - 1:
                        logger.warning(f"  触发频率限制，等待 360 秒后重试...")
                        time.sleep(360)
                        logger.info(f"  重试 {attempt + 2}/{max_retries}...")
                        continue
                    else:
                        logger.error(f"  已达最大重试次数，频率限制: {error_msg}")
                        return None
                else:
                    logger.error(f"  获取失败 (尝试 {attempt + 1}/{max_retries}): {error_msg}")
                    if attempt < max_retries - 1:
                        time.sleep(2)
                        continue
                    else:
                        return None

    return None


def fetch_etf_minutes(
    ts_code: str,
    freq: str = "5min",
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Optional[pd.DataFrame]:
    """
    获取 ETF 分钟行情

    Args:
        ts_code: ETF 代码，如 159272.SZ
        freq: 频率，支持 1min/5min/15min/30min/60min
        start_date: 开始时间，格式 "YYYY-MM-DD HH:MM:SS"
        end_date: 结束时间，格式 "YYYY-MM-DD HH:MM:SS"

    Returns:
        ETF 分钟行情 DataFrame
    """
    logger.info(f"调用 Tushare 接口: pro.stk_mins()")
    logger.info(f"  ETF 代码: {ts_code}")
    logger.info(f"  频率: {freq}")
    logger.info(f"  时间范围: {start_date or '最早'} ~ {end_date or '最新'}")

    # 转换时间格式
    if start_date:
        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S").strftime("%Y%m%d %H%M%S")
        except:
            pass

    if end_date:
        try:
            end_date = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S").strftime("%Y%m%d %H%M%S")
        except:
            pass

    try:
        pro = get_tushare_pro()

        # 注意：stk_mins 接口数据量大，官方有限速
        max_retries = 3
        for attempt in range(max_retries):
            try:
                df = pro.stk_mins(
                    ts_code=ts_code,
                    freq=freq,
                    start_date=start_date,
                    end_date=end_date
                )

                if df is None or len(df) == 0:
                    logger.warning("返回数据为空")
                    return None

                logger.info(f"成功获取 {len(df)} 条分钟数据")
                logger.debug(f"前 5 条数据:\n{df.head()}")

                return df

            except Exception as e:
                error_msg = str(e)

                # 如果是限速错误，重试
                if "限速" in error_msg or "频率" in error_msg:
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 2
                        logger.warning(f"触发限速，等待 {wait_time} 秒后重试...")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"已达最大重试次数，限速错误: {error_msg}")
                        return None
                else:
                    raise

    except Exception as e:
        error_msg = str(e)

        # 友好提示权限问题
        if "权限" in error_msg or "积分" in error_msg:
            logger.warning(f"权限不足: {error_msg}")
            logger.info("提示: 分钟行情数据需要 Tushare 高级权限")
        else:
            logger.error(f"获取失败: {error_msg}")

        return None


def fetch_stock_daily(
    ts_code: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    use_cache: bool = True,
    cache_expire_days: int = 1
) -> Optional[pd.DataFrame]:
    """
    获取股票日线行情

    Args:
        ts_code: 股票代码，如 000001.SZ
        start_date: 开始日期，格式 YYYYMMDD
        end_date: 结束日期，格式 YYYYMMDD
        use_cache: 是否使用缓存
        cache_expire_days: 缓存有效期（天）

    Returns:
        股票日线行情 DataFrame
    """
    cache_dir = settings.data_dir / "raw" / "cache" / "stock_daily"
    cache_dir.mkdir(parents=True, exist_ok=True)

    cache_file = cache_dir / f"{ts_code}_{start_date or 'none'}_{end_date or 'none'}.csv"

    # 检查缓存
    if use_cache and cache_file.exists():
        cache_age = (datetime.now() - datetime.fromtimestamp(cache_file.stat().st_mtime)).days
        if cache_age <= cache_expire_days:
            logger.info(f"使用缓存: {ts_code}")
            return pd.read_csv(cache_file, encoding='utf-8-sig')

    # 请求数据
    try:
        pro = get_tushare_pro()
        time.sleep(0.3)

        df = pro.daily(
            ts_code=ts_code,
            start_date=start_date,
            end_date=end_date,
            fields='ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount'
        )

        if df is not None and len(df) > 0:
            logger.info(f"获取股票日线: {ts_code}, {len(df)} 条")
            if use_cache:
                df.to_csv(cache_file, index=False, encoding='utf-8-sig')
            return df

    except Exception as e:
        logger.error(f"获取股票日线失败 {ts_code}: {e}")

    return None
