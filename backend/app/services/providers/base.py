from abc import ABC, abstractmethod
from typing import List
from app.schemas.lead import LeadInfo, LeadInteraction
from app.schemas.battlecard import BattlecardAIOutput


class ProviderError(RuntimeError):
    """Base exception for LLM provider errors."""
    def __init__(self, message: str, provider: str, error_type: str = "generic"):
        super().__init__(message)
        self.provider = provider
        self.error_type = error_type


class BaseLLMProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier, e.g. 'openai', 'gemini', 'offline_heuristic'"""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Returns True if the provider has necessary credentials and configuration."""
        pass

    @abstractmethod
    def analyze(
        self,
        lead: LeadInfo,
        interactions: List[LeadInteraction],
        transcript_text: str,
        compressed: bool,
        source_bytes: int
    ) -> BattlecardAIOutput:
        """Performs semantic analysis and returns structured BattlecardAIOutput."""
        pass

