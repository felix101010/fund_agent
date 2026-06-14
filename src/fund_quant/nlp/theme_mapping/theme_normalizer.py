"""
主题标准化器
将AI输出的自然语言主题映射为标准theme_id
"""
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Any


def get_field(obj: Any, name: str, default=None):
    """兼容获取字段值"""
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


@dataclass
class NormalizedTheme:
    """标准化主题"""
    theme_id: str
    canonical_name: str
    confidence: float
    matched_alias: str
    index_codes: list = field(default_factory=list)
    etf_codes: list = field(default_factory=list)
    industry_chain: list = field(default_factory=list)


class ThemeNormalizer:
    """
    主题标准化器

    职责：
    1. 加载主题分类体系（theme_taxonomy.yaml）
    2. 将自然语言主题映射为标准theme_id
    3. 补充指数/ETF/产业链信息
    """

    def __init__(self, taxonomy_file: Path = None):
        """初始化标准化器"""
        if taxonomy_file is None:
            taxonomy_file = Path(__file__).parent / "theme_taxonomy.yaml"

        # 加载主题分类体系
        with open(taxonomy_file, 'r', encoding='utf-8') as f:
            self.taxonomy = yaml.safe_load(f)

        # 构建别名索引（小写）
        self.alias_to_theme_id = {}
        for theme_id, theme_data in self.taxonomy.items():
            for alias in theme_data.get('aliases', []):
                self.alias_to_theme_id[alias.lower()] = theme_id

    def normalize(self, ai_event_result: Any) -> dict:
        """
        标准化主题

        Args:
            ai_event_result: AI事件结果对象

        Returns:
            {
                'normalized_themes': list[NormalizedTheme],
                'primary_theme_id': str,
                'primary_theme_name': str,
                'theme_confidence': float,
                'mapping_notes': list[str]
            }
        """
        mapping_notes = []
        normalized_themes = []

        # 获取AI输出的主题
        theme = get_field(ai_event_result, 'theme', '')
        sub_themes = get_field(ai_event_result, 'sub_themes', [])
        title = get_field(ai_event_result, 'title', '') if hasattr(ai_event_result, 'title') else ''
        content = get_field(ai_event_result, 'content', '') if hasattr(ai_event_result, 'content') else ''

        # 收集所有候选主题
        candidate_themes = []
        if theme and theme != "无":
            candidate_themes.extend([t.strip() for t in theme.split(',') if t.strip()])
        if sub_themes:
            candidate_themes.extend(sub_themes)

        # 去重
        candidate_themes = list(set(candidate_themes))

        # 映射到标准主题
        for candidate in candidate_themes:
            candidate_lower = candidate.lower()

            # 精确匹配
            if candidate_lower in self.alias_to_theme_id:
                theme_id = self.alias_to_theme_id[candidate_lower]
                theme_data = self.taxonomy[theme_id]

                normalized_themes.append(NormalizedTheme(
                    theme_id=theme_id,
                    canonical_name=theme_data['canonical_name'],
                    confidence=0.9,
                    matched_alias=candidate,
                    index_codes=theme_data.get('index_codes', []),
                    etf_codes=theme_data.get('etf_codes', []),
                    industry_chain=theme_data.get('industry_chain', [])
                ))
                mapping_notes.append(f"主题映射: {candidate} → {theme_data['canonical_name']} ({theme_id})")

        # 模糊匹配（从标题和内容）- 按优先级顺序
        text = f"{title} {content}".lower()

        # 优先级规则：先匹配特定主题，再匹配泛主题
        priority_themes = [
            'xr_optics', 'power_grid_equipment', 'optical_module',
            'semiconductor_material', 'robot'
        ]

        if not normalized_themes:
            # 优先匹配高优先级主题
            for theme_id in priority_themes:
                if theme_id not in self.taxonomy:
                    continue
                theme_data = self.taxonomy[theme_id]
                for alias in theme_data.get('aliases', []):
                    if alias.lower() in text:
                        # 避免重复
                        if not any(t.theme_id == theme_id for t in normalized_themes):
                            normalized_themes.append(NormalizedTheme(
                                theme_id=theme_id,
                                canonical_name=theme_data['canonical_name'],
                                confidence=0.8,
                                matched_alias=alias,
                                index_codes=theme_data.get('index_codes', []),
                                etf_codes=theme_data.get('etf_codes', []),
                                industry_chain=theme_data.get('industry_chain', [])
                            ))
                            mapping_notes.append(f"文本优先匹配: {alias} → {theme_data['canonical_name']} ({theme_id})")
                            break

            # 如果优先主题没匹配，再匹配其他主题
            if not normalized_themes:
                for theme_id, theme_data in self.taxonomy.items():
                    if theme_id in priority_themes:
                        continue  # 已经处理过
                    for alias in theme_data.get('aliases', []):
                        if alias.lower() in text:
                            # 避免重复
                            if not any(t.theme_id == theme_id for t in normalized_themes):
                                normalized_themes.append(NormalizedTheme(
                                    theme_id=theme_id,
                                    canonical_name=theme_data['canonical_name'],
                                    confidence=0.7,
                                    matched_alias=alias,
                                    index_codes=theme_data.get('index_codes', []),
                                    etf_codes=theme_data.get('etf_codes', []),
                                    industry_chain=theme_data.get('industry_chain', [])
                                ))
                                mapping_notes.append(f"文本模糊匹配: {alias} → {theme_data['canonical_name']} ({theme_id})")
                                break

        # 排除规则：光波导不能映射到新能源车
        if "光波导" in text or "体全息" in text or "xr" in text or "ar光学" in text:
            # 移除new_energy_vehicle
            normalized_themes = [t for t in normalized_themes if t.theme_id != 'new_energy_vehicle']
            if not any(t.theme_id == 'xr_optics' for t in normalized_themes):
                # 强制添加xr_optics
                if 'xr_optics' in self.taxonomy:
                    theme_data = self.taxonomy['xr_optics']
                    normalized_themes.insert(0, NormalizedTheme(
                        theme_id='xr_optics',
                        canonical_name=theme_data['canonical_name'],
                        confidence=0.85,
                        matched_alias='光波导',
                        index_codes=theme_data.get('index_codes', []),
                        etf_codes=theme_data.get('etf_codes', []),
                        industry_chain=theme_data.get('industry_chain', [])
                    ))
                    mapping_notes.append("排除规则: 光波导 → xr_optics (排除new_energy_vehicle)")

        # 排除规则：变压器优先映射电网设备
        if "变压器" in text or "输变电" in text or "特高压" in text or "电网设备" in text:
            # 将power_grid_equipment提到第一位
            power_grid_themes = [t for t in normalized_themes if t.theme_id == 'power_grid_equipment']
            other_themes = [t for t in normalized_themes if t.theme_id != 'power_grid_equipment']
            if power_grid_themes:
                normalized_themes = power_grid_themes + other_themes
                mapping_notes.append("排除规则: 变压器 → power_grid_equipment优先")
            elif 'power_grid_equipment' in self.taxonomy:
                # 强制添加
                theme_data = self.taxonomy['power_grid_equipment']
                normalized_themes.insert(0, NormalizedTheme(
                    theme_id='power_grid_equipment',
                    canonical_name=theme_data['canonical_name'],
                    confidence=0.85,
                    matched_alias='变压器',
                    index_codes=theme_data.get('index_codes', []),
                    etf_codes=theme_data.get('etf_codes', []),
                    industry_chain=theme_data.get('industry_chain', [])
                ))
                mapping_notes.append("排除规则: 变压器 → power_grid_equipment (强制添加)")

        # 排除规则：展会/意向成交不能映射具体产业主题
        if any(kw in text for kw in ["上交会", "展会", "博览会", "意向成交", "成交项目数", "项目数突破"]):
            # 如果没有明确公司名或订单金额，清空主题
            has_specific_info = any(kw in text for kw in ["订单金额", "亿元", "万元", "上市公司"])
            if not has_specific_info:
                normalized_themes = []
                mapping_notes.append("排除规则: 展会/意向成交且无明确信息 → 清空主题")

        # 确定主主题
        primary_theme_id = None
        primary_theme_name = None
        theme_confidence = 0.0

        if normalized_themes:
            # 按置信度排序，选择第一个
            normalized_themes.sort(key=lambda t: t.confidence, reverse=True)
            primary = normalized_themes[0]
            primary_theme_id = primary.theme_id
            primary_theme_name = primary.canonical_name
            theme_confidence = primary.confidence

            # 过滤掉泛政策（如果有其他更具体的主题）
            if len(normalized_themes) > 1 and primary_theme_id == 'general_policy':
                # 使用第二个主题
                primary = normalized_themes[1]
                primary_theme_id = primary.theme_id
                primary_theme_name = primary.canonical_name
                theme_confidence = primary.confidence
                mapping_notes.append("泛政策降级，使用次要主题")

        # 公司默认主题补充：如果AI没抽到主题，但标题包含重点公司
        if not primary_theme_id:
            # 重点公司列表
            company_theme_mappings = {
                "中际旭创": ("optical_module", "光模块/CPO"),
                "海康威视": ("smart_security", "智能安防"),
                "富祥股份": ("battery_material", "电池材料"),
            }

            for company_name, (theme_id, theme_name) in company_theme_mappings.items():
                if company_name in title:
                    if theme_id in self.taxonomy:
                        theme_data = self.taxonomy[theme_id]
                        normalized_themes.append(NormalizedTheme(
                            theme_id=theme_id,
                            canonical_name=theme_data['canonical_name'],
                            confidence=0.75,
                            matched_alias=company_name,
                            index_codes=theme_data.get('index_codes', []),
                            etf_codes=theme_data.get('etf_codes', []),
                            industry_chain=theme_data.get('industry_chain', [])
                        ))
                        primary_theme_id = theme_id
                        primary_theme_name = theme_data['canonical_name']
                        theme_confidence = 0.75
                        mapping_notes.append(f"公司默认主题: {company_name} → {theme_data['canonical_name']} ({theme_id})")
                        break

        return {
            'normalized_themes': normalized_themes,
            'primary_theme_id': primary_theme_id,
            'primary_theme_name': primary_theme_name,
            'theme_confidence': theme_confidence,
            'mapping_notes': mapping_notes
        }


__all__ = ['NormalizedTheme', 'ThemeNormalizer']
