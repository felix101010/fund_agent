"""
公司主题映射
将公司股票代码映射到默认主题
"""

COMPANY_THEME_MAP = {
    "000758.SZ": {
        "stock_name": "中色股份",
        "primary_theme_id": "nonferrous_metals",
        "primary_theme_name": "有色金属",
        "secondary_theme_id": "lead_zinc",
        "secondary_theme_name": "铅锌",
        "keywords": ["中色股份", "铅锌矿", "采选扩建", "矿业", "矿山", "资源开发"]
    },
    "300121.SZ": {
        "stock_name": "阳谷华泰",
        "primary_theme_id": "chemical_materials",
        "primary_theme_name": "化工材料",
        "secondary_theme_id": "chemical_safety",
        "secondary_theme_name": "化工安全",
        "keywords": ["阳谷华泰", "安全事故", "化工事故", "生产事故", "橡胶助剂"]
    },
    "688177.SH": {
        "stock_name": "百奥泰",
        "primary_theme_id": "biologics",
        "primary_theme_name": "生物药",
        "secondary_theme_id": "innovative_drug",
        "secondary_theme_name": "创新药",
        "keywords": ["百奥泰", "GMP", "EU GMP", "生物药", "单抗", "抗体药"]
    },
    "688506.SH": {
        "stock_name": "百利天恒",
        "primary_theme_id": "innovative_drug",
        "primary_theme_name": "创新药",
        "secondary_theme_id": "ADC",
        "secondary_theme_name": "ADC药物",
        "keywords": ["百利天恒", "ADC", "双抗ADC", "EGFR", "HER3", "药品上市申请", "三阴乳腺癌"]
    },
    "000030.SZ": {
        "stock_name": "富奥股份",
        "primary_theme_id": "auto_parts",
        "primary_theme_name": "汽车零部件",
        "keywords": ["富奥股份", "汽车零部件"]
    },
    "300681.SZ": {
        "stock_name": "英搏尔",
        "primary_theme_id": "new_energy_vehicle",
        "primary_theme_name": "新能源汽车",
        "secondary_theme_id": "motor_controller",
        "secondary_theme_name": "电机控制器",
        "keywords": ["英搏尔", "电机控制器", "电驱动", "新能源车"]
    }
}


def get_company_theme(stock_code: str, title: str = "") -> dict:
    """
    获取公司默认主题

    Args:
        stock_code: 股票代码
        title: 公告标题（用于二级主题匹配）

    Returns:
        主题信息字典
    """
    if stock_code not in COMPANY_THEME_MAP:
        return {}

    mapping = COMPANY_THEME_MAP[stock_code]
    result = {
        'primary_theme_id': mapping['primary_theme_id'],
        'primary_theme_name': mapping['primary_theme_name'],
        'secondary_theme_id': mapping.get('secondary_theme_id'),
        'secondary_theme_name': mapping.get('secondary_theme_name')
    }

    # 关键词匹配：如果标题命中关键词，确认二级主题
    if title:
        title_lower = title.lower()
        keywords = mapping.get('keywords', [])
        matched = any(kw in title_lower for kw in keywords)

        if matched and not result['secondary_theme_id']:
            # 如果有二级主题配置且匹配，启用
            pass

    return result


__all__ = ['COMPANY_THEME_MAP', 'get_company_theme']
