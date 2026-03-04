from openai import OpenAI

from .base import BaseLLMClient


class OpenAIClient(BaseLLMClient):
    """OpenAI 及兼容接口客户端（支持 Ollama、DeepSeek 等）"""

    def __init__(self, config: dict):
        super().__init__(config)
        api_key = config.get("api_key", "sk-placeholder")
        base_url = config.get("base_url")
        kwargs: dict = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = OpenAI(**kwargs)

    def chat(self, messages: list[dict], system: str = "") -> str:
        all_messages = []
        if system:
            all_messages.append({"role": "system", "content": system})
        all_messages.extend(messages)

        response = self._client.chat.completions.create(
            model=self.model,
            messages=all_messages,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )
        return response.choices[0].message.content or ""
