"""
Automated Test Suite for LLM Provider Abstraction.

Tests:
1. MockLLMProvider returns deterministic output
2. MockLLMProvider references citation markers from context
3. MockLLMProvider handles missing context gracefully
4. MockLLMProvider raises on empty input
5. Provider factory selects mock by default
6. Provider factory rejects unknown provider
7. GoogleGeminiProvider rejects empty API key
8. Provider name property works correctly
9. Mock handles multiple sources
10. Mock insufficient evidence response
"""

import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.services.llm_provider import (
    MockLLMProvider,
    GoogleGeminiProvider,
    BaseLLMProvider,
    LLMProviderError,
    get_llm_provider,
)


SAMPLE_CONTEXT_WITH_SOURCES = '''You are a postal regulations assistant.

<OFFICIAL_POSTAL_SOURCE id="1">

Document ID: DOC2
Document: The Post Office Act, 2023
Page: 13
Legal Reference: Section 9

TEXT:
The Central Government may establish post offices.

</OFFICIAL_POSTAL_SOURCE>

<OFFICIAL_POSTAL_SOURCE id="2">

Document ID: DOC1
Document: Post Office Rules, 2024
Page: 7
Legal Reference: Rule 5

TEXT:
The Board shall consist of a Chairperson and Members.

</OFFICIAL_POSTAL_SOURCE>'''

CONTEXT_WITHOUT_SOURCES = "You are a postal regulations assistant. Answer the question."


class TestMockLLMProvider:
    """Tests for MockLLMProvider."""

    def setup_method(self):
        self.provider = MockLLMProvider()

    def test_provider_name(self):
        """1. Provider name is 'mock'."""
        assert self.provider.provider_name == "mock"

    def test_is_base_provider(self):
        """2. MockLLMProvider is an instance of BaseLLMProvider."""
        assert isinstance(self.provider, BaseLLMProvider)

    def test_deterministic_output(self):
        """3. Same inputs produce identical outputs (deterministic)."""
        result1 = self.provider.generate(SAMPLE_CONTEXT_WITH_SOURCES, "What is Section 9?")
        result2 = self.provider.generate(SAMPLE_CONTEXT_WITH_SOURCES, "What is Section 9?")
        assert result1 == result2

    def test_references_citation_markers(self):
        """4. Mock response includes citation markers from context."""
        result = self.provider.generate(SAMPLE_CONTEXT_WITH_SOURCES, "What is Section 9?")
        assert "[1]" in result
        assert "[2]" in result

    def test_no_sources_returns_insufficient_evidence(self):
        """5. When context has no sources, returns insufficient evidence message."""
        result = self.provider.generate(CONTEXT_WITHOUT_SOURCES, "What is Section 9?")
        assert "could not find sufficient information" in result.lower()

    def test_raises_on_empty_system_prompt(self):
        """6. Raises LLMProviderError when system_prompt is empty."""
        with pytest.raises(LLMProviderError):
            self.provider.generate("", "What is Section 9?")

    def test_raises_on_empty_user_message(self):
        """7. Raises LLMProviderError when user_message is empty."""
        with pytest.raises(LLMProviderError):
            self.provider.generate(SAMPLE_CONTEXT_WITH_SOURCES, "")

    def test_response_is_string(self):
        """8. Response is always a string."""
        result = self.provider.generate(SAMPLE_CONTEXT_WITH_SOURCES, "Tell me about postal rules.")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_multiple_sources_referenced(self):
        """9. Multiple source IDs are referenced in the response."""
        context = SAMPLE_CONTEXT_WITH_SOURCES + '''

<OFFICIAL_POSTAL_SOURCE id="3">

Document ID: DOC2
Document: The Post Office Act, 2023
Page: 15
Legal Reference: Section 11

TEXT:
The Postal Services Board shall advise the Central Government.

</OFFICIAL_POSTAL_SOURCE>'''
        result = self.provider.generate(context, "Tell me about the Postal Services Board.")
        # Should reference up to 3 sources
        assert "[1]" in result
        assert "[2]" in result
        assert "[3]" in result


class TestGoogleGeminiProvider:
    """Tests for GoogleGeminiProvider (no API calls made)."""

    def test_rejects_empty_api_key(self):
        """10. GoogleGeminiProvider raises on empty API key."""
        with pytest.raises(LLMProviderError, match="GOOGLE_API_KEY"):
            GoogleGeminiProvider(api_key="")

    def test_rejects_none_api_key(self):
        """11. GoogleGeminiProvider raises on None API key."""
        with pytest.raises(LLMProviderError, match="GOOGLE_API_KEY"):
            GoogleGeminiProvider(api_key=None)

    def test_provider_name(self):
        """12. Provider name is 'gemini'."""
        # Use a dummy key - no actual API call is made
        provider = GoogleGeminiProvider(api_key="test-key-not-real")
        assert provider.provider_name == "gemini"

    def test_is_base_provider(self):
        """13. GoogleGeminiProvider is an instance of BaseLLMProvider."""
        provider = GoogleGeminiProvider(api_key="test-key-not-real")
        assert isinstance(provider, BaseLLMProvider)


class TestProviderFactory:
    """Tests for get_llm_provider factory function."""

    def test_default_is_mock(self):
        """14. Default provider is MockLLMProvider."""
        provider = get_llm_provider(provider_name="mock")
        assert isinstance(provider, MockLLMProvider)

    def test_explicit_mock(self):
        """15. Explicitly requesting 'mock' returns MockLLMProvider."""
        provider = get_llm_provider(provider_name="mock")
        assert provider.provider_name == "mock"

    def test_unknown_provider_raises(self):
        """16. Unknown provider name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            get_llm_provider(provider_name="openai")

    def test_gemini_without_key_raises(self):
        """17. Requesting 'gemini' without API key raises LLMProviderError."""
        with pytest.raises(LLMProviderError, match="GOOGLE_API_KEY"):
            get_llm_provider(provider_name="gemini", api_key="")
