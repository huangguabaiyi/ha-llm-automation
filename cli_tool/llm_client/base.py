from __future__ import annotations

import re
from abc import ABC, abstractmethod


class BaseLLMClient(ABC):
    """LLM 接口抽象基类"""

    def __init__(self, config: dict):
        self.model = config.get("model", "")
        self.max_tokens = config.get("max_tokens", 8192)
        self.temperature = config.get("temperature", 0.3)

    @abstractmethod
    def chat(self, messages: list[dict], system: str = "") -> str:
        """
        发送对话请求，返回文本响应。

        messages 格式: [{"role": "user"|"assistant", "content": "..."}]
        """
        raise NotImplementedError

    def extract_yaml(self, response: str) -> str:
        """从 LLM 响应中提取 YAML 代码块"""
        pattern = r"```(?:yaml)?\s*\n(.*?)```"
        match = re.search(pattern, response, re.DOTALL)
        if match:
            return match.group(1).strip()
        return response.strip()

    def chat_with_retry(self, messages: list[dict], system: str = "", max_retries: int = 2) -> str:
        """带重试的对话（最多重试 max_retries 次）"""
        last_exc: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                return self.chat(messages, system)
            except Exception as e:
                last_exc = e
                if attempt < max_retries:
                    continue
        raise RuntimeError(f"LLM 调用失败（已重试 {max_retries} 次）: {last_exc}") from last_exc
