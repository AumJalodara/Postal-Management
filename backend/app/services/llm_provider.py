"""
LLM Provider Abstraction for Grounded RAG.

Provides a pluggable provider interface for LLM text generation:
- BaseLLMProvider: Abstract base class
- MockLLMProvider: Deterministic offline provider for automated tests
- GoogleGeminiProvider: Real provider using google-genai SDK

Provider selection is controlled via LLM_PROVIDER environment variable.
Credentials are loaded exclusively from environment variables.
No secrets are stored in source code.
"""

import re
import logging
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger("smart_postal.llm_provider")


class LLMProviderError(Exception):
    """Raised when the LLM provider encounters an error."""
    pass


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate(self, system_prompt: str, user_message: str) -> str:
        """
        Generate a response given a system prompt and user message.

        Args:
            system_prompt: The system-level instructions (includes grounded context).
            user_message: The user's question.

        Returns:
            The generated text response.

        Raises:
            LLMProviderError: If generation fails.
        """
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the name of this provider."""
        pass


class MockLLMProvider(BaseLLMProvider):
    """
    Deterministic mock LLM provider for automated testing.

    Produces grounded responses that reference citation markers [1], [2], etc.
    based on the sources present in the system prompt context.
    Works completely offline with no network access or API keys required.
    """

    @property
    def provider_name(self) -> str:
        return "mock"

    def generate(self, system_prompt: str, user_message: str) -> str:
        """
        Generate a deterministic mock response based on the provided context.

        The mock analyzes the system prompt to find OFFICIAL_POSTAL_SOURCE blocks
        and produces a response that references them with proper citation markers.
        """
        if not system_prompt or not user_message:
            raise LLMProviderError("Both system_prompt and user_message are required.")

        # Extract source IDs from the context
        source_ids = re.findall(r'<OFFICIAL_POSTAL_SOURCE id="(\d+)">', system_prompt)

        if not source_ids:
            return (
                "I could not find sufficient information in the available "
                "official postal documents to answer this question reliably."
            )

        # Build a deterministic grounded response
        citation_refs = ", ".join(f"[{sid}]" for sid in source_ids[:3])

        response = (
            f"Based on the official postal documents provided, "
            f"the relevant information can be found in the referenced sources. "
            f"According to the official postal regulations {citation_refs}, "
            f"the provisions address the matter as specified in the cited documents. "
            f"Please refer to the original source documents for the complete legal text."
        )

        return response


class GoogleGeminiProvider(BaseLLMProvider):
    """
    Real LLM provider using Google Gemini via the google-genai SDK.

    Requires:
    - GOOGLE_API_KEY environment variable
    - google-genai package installed

    This provider is optional and only used when LLM_PROVIDER=gemini.
    All automated tests work without this provider.
    """

    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash"):
        if not api_key:
            raise LLMProviderError(
                "GOOGLE_API_KEY environment variable is required for Gemini provider. "
                "Set LLM_PROVIDER=mock for offline operation."
            )
        self._api_key = api_key
        self._model_name = model_name
        self._client = None

    @property
    def provider_name(self) -> str:
        return "gemini"

    def _get_client(self):
        """Lazy-initialize the Gemini client."""
        if self._client is None:
            try:
                from google import genai
                self._client = genai.Client(api_key=self._api_key)
            except ImportError:
                raise LLMProviderError(
                    "google-genai package is not installed. "
                    "Install with: pip install google-genai"
                )
            except Exception as e:
                raise LLMProviderError(f"Failed to initialize Gemini client: {e}")
        return self._client

    def generate(self, system_prompt: str, user_message: str) -> str:
        """Generate a response using Google Gemini."""
        if not system_prompt or not user_message:
            raise LLMProviderError("Both system_prompt and user_message are required.")

        try:
            client = self._get_client()
            response = client.models.generate_content(
                model=self._model_name,
                contents=user_message,
                config={
                    "system_instruction": system_prompt,
                    "temperature": 0.1,
                    "max_output_tokens": 2048,
                },
            )
            if response and response.text:
                return response.text
            raise LLMProviderError("Gemini returned empty response.")
        except LLMProviderError:
            raise
        except Exception as e:
            raise LLMProviderError(f"Gemini generation failed: {e}")

class GroqProvider(BaseLLMProvider):
    """
    Real LLM provider using Groq via the groq SDK.
    Requires GROQ_API_KEY environment variable.
    """
    def __init__(self, api_key: str, model_name: str = "qwen/qwen3.8-27b"):
        if not api_key:
            raise LLMProviderError(
                "GROQ_API_KEY environment variable is required for Groq provider. "
                "Please configure a valid Groq API key."
            )
        self._api_key = api_key
        self._model_name = model_name
        self._client = None

    @property
    def provider_name(self) -> str:
        return "groq"

    def _get_client(self):
        if self._client is None:
            try:
                from groq import Groq
                self._client = Groq(api_key=self._api_key)
            except ImportError:
                raise LLMProviderError(
                    "groq package is not installed. "
                    "Install with: pip install groq"
                )
            except Exception as e:
                raise LLMProviderError(f"Failed to initialize Groq client: {e}")
        return self._client

    def generate(self, system_prompt: str, user_message: str) -> str:
        if not system_prompt or not user_message:
            raise LLMProviderError("Both system_prompt and user_message are required.")

        try:
            client = self._get_client()
            response = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                model=self._model_name,
                temperature=0.1,
                max_tokens=2048,
            )
            if response and response.choices and response.choices[0].message.content:
                return response.choices[0].message.content
            raise LLMProviderError("Groq returned empty response.")
        except Exception as e:
            raise LLMProviderError(f"Groq generation failed: {e}")


def get_llm_provider(
    provider_name: Optional[str] = None,
    api_key: Optional[str] = None,
    model_name: Optional[str] = None,
) -> BaseLLMProvider:
    """
    Factory function to create the appropriate LLM provider.

    Args:
        provider_name: 'mock' or 'gemini'. Defaults to config setting.
        api_key: API key for real providers. Defaults to config setting.
        model_name: Model name for real providers. Defaults to config setting.

    Returns:
        An instance of BaseLLMProvider.
    """
    from app.config import settings

    effective_provider = (provider_name or getattr(settings, "LLM_PROVIDER", "mock")).lower()
    effective_api_key = api_key or getattr(settings, "GOOGLE_API_KEY", "")
    effective_model = model_name or getattr(settings, "LLM_MODEL_NAME", "gemini-2.0-flash")

    if effective_provider == "mock":
        logger.info("Using MockLLMProvider (offline, deterministic)")
        return MockLLMProvider()
    elif effective_provider == "gemini":
        logger.info(f"Using GoogleGeminiProvider (model={effective_model})")
        return GoogleGeminiProvider(
            api_key=effective_api_key,
            model_name=effective_model,
        )
    elif effective_provider == "groq":
        effective_groq_key = api_key or getattr(settings, "GROQ_API_KEY", "")
        effective_groq_model = model_name or getattr(settings, "GROQ_MODEL", "llama-3.3-70b-versatile")
        logger.info(f"Using GroqProvider (model={effective_groq_model})")
        return GroqProvider(
            api_key=effective_groq_key,
            model_name=effective_groq_model,
        )

    else:
        raise ValueError(
            f"Unknown LLM provider '{effective_provider}'. "
            f"Supported: 'mock', 'gemini', 'groq'"
        )
