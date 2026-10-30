"""Prepare compact evidence, reusing verified append-only summary snapshots."""
import hashlib
import logging
from dataclasses import dataclass, field
from app.services.summary import (
    EvidenceSummarizer, SUMMARY_VERSION, CHUNK_MAX_BYTES, format_interactions, validate_memory,
)
from app.services.usage import TokenUsage

logger = logging.getLogger(__name__)


@dataclass
class PreparedEvidence:
    text: str
    source_bytes: int
    processed_bytes: int = 0
    mode: str = "direct"
    reused_interactions: int = 0
    summary_cache_saved: bool = True
    usage: TokenUsage = field(default_factory=TokenUsage)

    @property
    def compressed(self):
        return self.mode != "direct"


class EvidencePreparationAgent:
    def __init__(self, client, model, store=None):
        self.client, self.model, self.store = client, model, store

    def prepare(self, lead_id, interactions, max_source_bytes, use_summary=True):
        transcript = format_interactions(interactions)
        source_bytes = len(transcript.encode("utf-8"))
        if source_bytes > max_source_bytes:
            raise ValueError("Conversation history exceeds MAX_EVIDENCE_BYTES. Review the processing budget before increasing the limit.")
        if not use_summary or source_bytes <= CHUNK_MAX_BYTES:
            return PreparedEvidence(text=transcript, source_bytes=source_bytes)

        hashes = [hashlib.sha256(item.model_dump_json().encode()).hexdigest() for item in interactions]
        cached = None
        if self.store is not None:
            try:
                cached = self.store.get_evidence_memory(lead_id)
            except Exception as error:
                logger.warning("Evidence memory lookup failed (%s)", type(error).__name__)
        prior = None
        reused = 0
        if isinstance(cached, dict) and cached.get("version") == SUMMARY_VERSION and cached.get("model") == self.model and cached.get("lead_id") == lead_id:
            previous_hashes = cached.get("interaction_hashes")
            if isinstance(previous_hashes, list) and previous_hashes and len(previous_hashes) <= len(hashes) and hashes[:len(previous_hashes)] == previous_hashes:
                try:
                    prior = validate_memory(cached.get("memory"))
                    reused = len(previous_hashes)
                except (ValueError, TypeError):
                    pass

        if prior is not None and reused == len(hashes):
            return PreparedEvidence(text=prior, source_bytes=source_bytes, mode="reused", reused_interactions=reused)

        delta = format_interactions(interactions[reused:], start_index=reused + 1)
        summarizer = EvidenceSummarizer(self.client, self.model)
        memory = summarizer.summarize(delta, prior_memory=prior)
        # Validate again at the persistence boundary: never save unbounded evidence.
        memory = validate_memory(memory)
        prepared = PreparedEvidence(text=memory, source_bytes=source_bytes,
            processed_bytes=len(delta.encode("utf-8")), mode="incremental" if reused else "rebuilt",
            reused_interactions=reused, usage=summarizer.usage)
        if self.store is not None:
            try:
                self.store.save_evidence_memory(lead_id, {
                    "lead_id": lead_id, "version": SUMMARY_VERSION, "model": self.model,
                    "interaction_hashes": hashes, "memory": memory,
                })
            except Exception as error:
                prepared.summary_cache_saved = False
                logger.warning("Evidence memory persistence failed (%s)", type(error).__name__)
        else:
            prepared.summary_cache_saved = False
        return prepared
