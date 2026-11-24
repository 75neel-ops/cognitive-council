"""Provider-neutral interface and adapters."""
from __future__ import annotations
from abc import ABC, abstractmethod

class AIProvider(ABC):
    @abstractmethod
    def generate(self, model: str, system_prompt: str, user_prompt: str) -> str:
        raise NotImplementedError

class OpenAIProvider(AIProvider):
    def generate(self, model: str, system_prompt: str, user_prompt: str) -> str:
        from openai import OpenAI
        from config import get_secret
        key = get_secret("OPENAI_API_KEY")
        if not key:
            raise RuntimeError("OPENAI_API_KEY is not configured.")
        response = OpenAI(api_key=key).chat.completions.create(
            model=model,
            messages=[{"role":"system","content":system_prompt},{"role":"user","content":user_prompt}],
            temperature=0.4,
        )
        return response.choices[0].message.content or ""

class GeminiProvider(AIProvider):
    def generate(self, model: str, system_prompt: str, user_prompt: str) -> str:
        from google import genai
        from config import get_secret
        key = get_secret("GEMINI_API_KEY")
        if not key:
            raise RuntimeError("GEMINI_API_KEY is not configured.")
        client = genai.Client(api_key=key)
        response = client.models.generate_content(
            model=model,
            contents=f"{system_prompt}\n\n{user_prompt}",
        )
        return response.text or ""

class AnthropicProvider(AIProvider):
    def generate(self, model: str, system_prompt: str, user_prompt: str) -> str:
        import anthropic
        from config import get_secret
        key = get_secret("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY is not configured.")
        client = anthropic.Anthropic(api_key=key)
        response = client.messages.create(
            model=model, max_tokens=1800, temperature=0.4,
            system=system_prompt,
            messages=[{"role":"user","content":user_prompt}],
        )
        return "\n".join(block.text for block in response.content if getattr(block, "type", "") == "text")

def get_provider(name: str) -> AIProvider:
    providers = {"openai": OpenAIProvider, "gemini": GeminiProvider, "anthropic": AnthropicProvider}
    if name not in providers:
        raise ValueError(f"Unsupported provider: {name}")
    return providers[name]()
