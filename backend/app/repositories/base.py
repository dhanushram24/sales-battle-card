from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from app.schemas.lead import LeadInfo, LeadInteraction


class BaseLeadRepository(ABC):
    """
    Abstract interface for Lead data access.
    Allows easy swapping between direct MySQL queries and future Paramantra REST APIs.
    """

    @abstractmethod
    def get_lead_by_id(self, lead_id: str) -> Optional[LeadInfo]:
        """Fetch lead profile details."""
        pass

    @abstractmethod
    def get_lead_interactions(self, lead_id: str) -> List[LeadInteraction]:
        """Fetch interaction logs (calls, emails, notes) for a lead."""
        pass

    @abstractmethod
    def get_cached_battlecard(self, lead_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve previously saved battlecard score to avoid redundant LLM calls."""
        pass

    @abstractmethod
    def save_battlecard(self, lead_id: str, data: Dict[str, Any]) -> None:
        """Store/cache latest battlecard and score for a lead."""
        pass

    @abstractmethod
    def get_evidence_memory(self, lead_id: str) -> Optional[Dict[str, Any]]:
        """Read the latest structured evidence snapshot for incremental summaries."""
        pass

    @abstractmethod
    def save_evidence_memory(self, lead_id: str, data: Dict[str, Any]) -> None:
        """Persist a completed summary even if subsequent scoring fails."""
        pass
