"""
SEC 8-K 事件抽取器
使用LLM从8-K filing中提取结构化事件信息
"""
import json
import re
from typing import Dict, Any, Optional

from fund_quant.nlp.prompts.sec_edgar import build_sec_8k_event_prompt
from fund_quant.nlp.event_extraction.sec_edgar.sec_content_reducer import reduce_sec_content_for_ai
from fund_quant.nlp.event_extraction.sec_edgar.sec_content_reducer import reduce_sec_content_for_ai


class SEC8KEventExtractor:
    """
    SEC 8-K 事件抽取器

    职责：
    1. 构建SEC专用Prompt
    2. 调用LLM
    3. 解析JSON输出
    4. 验证核心字段
    5. Fallback处理
    """

    def __init__(self, llm_client=None, provider: str = "ollama"):
        """
        初始化

        Args:
            llm_client: LLM客户端（可选，用于依赖注入）
            provider: LLM提供商（ollama/openai等）
        """
        self.llm_client = llm_client
        self.provider = provider

        # 如果没有注入client，尝试创建默认client
        if not self.llm_client:
            self._init_default_client()

    def _init_default_client(self):
        """初始化默认LLM客户端（兼容现有项目）"""
        try:
            # 加载环境变量
            from pathlib import Path
            from dotenv import load_dotenv

            # 查找.env文件
            env_path = Path(__file__).parent.parent.parent.parent.parent.parent / ".env"
            if env_path.exists():
                load_dotenv(env_path)

            from fund_quant.nlp.news_ai import OllamaClient
            self.llm_client = OllamaClient()
            print(f"✅ OllamaClient初始化成功，模型: {self.llm_client.model}")
        except Exception as e:
            print(f"⚠️  未找到OllamaClient: {str(e)}")
            self.llm_client = None

    def extract(self, filing: Dict[str, Any]) -> Dict[str, Any]:
        """
        提取事件信息

        Args:
            filing: Filing数据

        Returns:
            {
                "ai_status": "success/failed/parse_failed/partial_success",
                "error": "错误信息",
                "ai_result": {...},
                "fallback_used": bool
            }
        """
        try:
            # 1. 压缩内容（如果是财报类）
            original_content_len = len(filing.get('content', ''))

            if filing.get("event_hint") == "earnings_release":
                reduced_content = reduce_sec_content_for_ai(filing, max_chars=12000)
                filing_for_prompt = dict(filing)
                filing_for_prompt["content"] = reduced_content
                filing_for_prompt["ai_input_content_len"] = len(reduced_content)

                print(f"  📊 内容压缩: {original_content_len} → {len(reduced_content)} chars ({len(reduced_content)/original_content_len*100:.1f}%)")
            else:
                filing_for_prompt = filing
                filing_for_prompt["ai_input_content_len"] = original_content_len

            # 2. 构建Prompt
            prompt = build_sec_8k_event_prompt(filing_for_prompt)

            # 2. 调用LLM
            if not self.llm_client:
                return self._build_fallback_result(filing, "LLM client未初始化", "failed")

            response = self._call_llm(prompt)

            if not response:
                return self._build_fallback_result(filing, "LLM返回为空", "failed")

            # 3. 解析JSON
            parsed = self._parse_json_response(response)

            if parsed is None:
                return self._build_fallback_result(filing, "JSON解析失败", "parse_failed")

            # 4. 验证核心字段
            is_valid, validation_error = self._validate_ai_result(parsed)

            if not is_valid:
                # 字段不完整，使用fallback补全
                return self._build_fallback_result(filing, validation_error, "partial_success")

            # 5. 成功
            return {
                "ai_status": "success",
                "error": "",
                "ai_result": parsed,
                "fallback_used": False
            }

        except Exception as e:
            return self._build_fallback_result(filing, str(e), "failed")

    def _call_llm(self, prompt: str) -> Optional[str]:
        """调用LLM"""
        try:
            # 兼容OllamaClient接口
            if hasattr(self.llm_client, 'generate'):
                response = self.llm_client.generate(prompt)
                return response
            elif hasattr(self.llm_client, 'chat'):
                response = self.llm_client.chat(prompt)
                return response
            else:
                response = self.llm_client(prompt)
                return response

        except Exception as e:
            print(f"⚠️  LLM调用失败: {str(e)}")
            return None

    def _parse_json_response(self, response: str) -> Optional[Dict[str, Any]]:
        """解析JSON响应（容错）"""
        if not response:
            return None

        # 策略1: 直接解析
        try:
            return json.loads(response)
        except:
            pass

        # 策略2: 剥离markdown code block
        try:
            match = re.search(r'```(?:json)?\s*\n(.*?)\n```', response, re.DOTALL)
            if match:
                json_str = match.group(1)
                return json.loads(json_str)
        except:
            pass

        # 策略3: 提取第一个JSON object
        try:
            start = response.find('{')
            if start != -1:
                end = response.rfind('}')
                if end != -1 and end > start:
                    json_str = response[start:end+1]
                    return json.loads(json_str)
        except:
            pass

        return None

    def _validate_ai_result(self, ai_result: Dict[str, Any]) -> tuple:
        """验证AI结果的核心字段"""
        event_type = ai_result.get('event_type', '').strip()
        event_level = ai_result.get('event_level', '').strip()

        if not event_type:
            return False, "core_fields_empty: event_type为空"
        if not event_level:
            return False, "core_fields_empty: event_level为空"

        summary_zh = ai_result.get('summary_zh', '').strip()
        key_facts = ai_result.get('key_facts', [])

        if not summary_zh and not key_facts:
            return False, "core_fields_empty: summary_zh和key_facts都为空"

        return True, ""

    def _build_fallback_result(self, filing: Dict[str, Any], error: str = "", status: str = "partial_success") -> Dict[str, Any]:
        """
        构建Fallback结果（基于规则）

        Args:
            filing: Filing数据
            error: 错误信息
            status: AI状态

        Returns:
            完整的结果字典
        """
        event_hint = filing.get('event_hint', 'other_material_event')
        pre_score = filing.get('pre_score', 50)
        ticker = filing.get('ticker', 'UNKNOWN')
        company_name = filing.get('company_name', 'UNKNOWN')
        items = filing.get('items', [])

        # 映射event_level
        event_level = self._level_from_pre_score(pre_score)

        # 生成summary
        summary_zh = self._build_fallback_summary(filing)

        # 构建key_facts
        key_facts = [
            f"form_type={filing.get('form_type', '8-K')}",
            f"items={', '.join(items) if items else 'Unknown'}",
            f"event_hint={event_hint}",
            "基于SEC规则判断，AI解析失败使用fallback"
        ]

        ai_result = {
            "event_type": event_hint,
            "event_level": event_level,
            "sentiment": "neutral",
            "ticker": ticker,
            "company_name": company_name,
            "summary_zh": summary_zh,
            "key_facts": key_facts,
            "financial_metrics": {
                "revenue": "unknown",
                "eps": "unknown",
                "gross_margin": "unknown",
                "data_center_revenue": "unknown",
                "guidance": "unknown",
                "outlook": "unknown"
            },
            "management_changes": [],
            "trading_relevance": "基于SEC Item规则判断，需进一步人工复核。",
            "financial_impact": "unknown",
            "risk_flags": filing.get('risk_flags', []),
            "confidence": 0.5
        }

        return {
            "ai_status": status,
            "error": error,
            "ai_result": ai_result,
            "fallback_used": True
        }

    def _level_from_pre_score(self, pre_score: int) -> str:
        """根据pre_score映射event_level"""
        if pre_score >= 90:
            return "A"
        elif pre_score >= 80:
            return "B"
        elif pre_score >= 65:
            return "C"
        else:
            return "D"

    def _build_fallback_summary(self, filing: Dict[str, Any]) -> str:
        """生成fallback summary"""
        event_hint = filing.get("event_hint", "")
        ticker = filing.get("ticker", "UNKNOWN")

        summary_map = {
            "earnings_release": f"{ticker}提交8-K，披露经营业绩/财报信息，并包含相关Exhibit附件。",
            "executive_change": f"{ticker}提交8-K，披露董事或高管变动事项。",
            "guidance_update": f"{ticker}提交8-K，披露业绩指引更新。",
            "material_agreement": f"{ticker}提交8-K，披露重大协议相关事项。",
            "mna_completed": f"{ticker}提交8-K，披露并购交易完成。",
            "financing": f"{ticker}提交8-K，披露融资事项。",
            "delisting_risk": f"{ticker}提交8-K，披露退市风险警示。",
            "bankruptcy_restructuring": f"{ticker}提交8-K，披露破产或重组事项。",
        }

        return summary_map.get(event_hint, f"{ticker}提交8-K，披露SEC重大事项。")


__all__ = ['SEC8KEventExtractor']
