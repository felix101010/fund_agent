"""
Ollama LLM 客户端 - 调用本地 Ollama 模型进行新闻事件抽取
"""
import os
import requests
import json
from typing import Optional


class OllamaClient:
    """Ollama 本地模型客户端"""

    def __init__(
        self,
        base_url: str = None,
        model: str = None,
        timeout: int = 60
    ):
        """
        初始化 Ollama 客户端

        Args:
            base_url: Ollama API 地址（默认从环境变量 OLLAMA_BASE_URL 读取，否则 http://localhost:11434）
                - WSL 访问 Windows: http://127.0.0.1:11435 或 http://10.x.x.x:11435
                - 本地: http://localhost:11434
            model: 模型名称（默认从环境变量 OLLAMA_MODEL 读取，否则 qwen2.5:7b）
                例如 qwen2.5:7b, qwen2.5:1.5b, llama3.1:8b
            timeout: 请求超时时间（秒）
        """
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")).rstrip('/')
        self.model = model or os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
        self.timeout = timeout
        self._test_connection()

    def _test_connection(self):
        """测试连接"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m["name"] for m in models]
                print(f"✅ Ollama 连接成功，可用模型: {model_names}")
                if self.model not in model_names:
                    print(f"⚠️  警告: 模型 {self.model} 不在可用列表中")
            else:
                print(f"⚠️  Ollama 连接异常: HTTP {response.status_code}")
        except Exception as e:
            print(f"❌ Ollama 连接失败: {e}")
            print(f"   请确认 Ollama 正在运行，地址: {self.base_url}")

    def generate(self, prompt: str) -> str:
        """
        生成文本（兼容 AIEventExtractor 的接口）

        Args:
            prompt: 提示词

        Returns:
            生成的文本
        """
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,  # 低温度，更确定性
                        "top_p": 0.9,
                        "num_predict": 2048  # 最大生成长度
                    }
                },
                timeout=self.timeout
            )

            if response.status_code == 200:
                result = response.json()
                return result.get("response", "")
            else:
                raise Exception(f"Ollama API 错误: HTTP {response.status_code}")

        except requests.exceptions.Timeout:
            raise Exception(f"Ollama 请求超时（{self.timeout}秒）")
        except Exception as e:
            raise Exception(f"Ollama 调用失败: {str(e)}")

    def chat(self, messages: list[dict]) -> str:
        """
        Chat 模式（可选）

        Args:
            messages: 消息列表，格式：
                [
                    {"role": "system", "content": "..."},
                    {"role": "user", "content": "..."}
                ]

        Returns:
            生成的文本
        """
        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "top_p": 0.9
                    }
                },
                timeout=self.timeout
            )

            if response.status_code == 200:
                result = response.json()
                message = result.get("message", {})
                return message.get("content", "")
            else:
                raise Exception(f"Ollama API 错误: HTTP {response.status_code}")

        except Exception as e:
            raise Exception(f"Ollama Chat 调用失败: {str(e)}")


__all__ = ['OllamaClient']
