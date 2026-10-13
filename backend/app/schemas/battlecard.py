from typing import List, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field


class ScoreBreakdown(BaseModel):
    sentiment_score: float = Field(..., ge=0.0, le=10.0, description="Customer sentiment score (0 to 10)")
    engagement_score: float = Field(..., ge=0.0, le=10.0, description="Responsiveness and interaction frequency (0 to 10)")
    intent_score: float = Field(..., ge=0.0, le=10.0, description="Buying intent and urgency (0 to 10)")
    risk_penalty: float = Field(..., ge=0.0, le=5.0, description="Penalty deducted for severe objections or stalls (0 to 5)")


class SentimentDriver(BaseModel):
    quote: str = Field(..., description="Exact quoted phrase from prospect or interaction")
    channel: str = Field(..., description="Channel origin: WhatsApp, Email, Call, Portal, Note")
    impact: str = Field(..., description="Impact explanation, e.g. '+1.5 Urgent PO Intent' or '-0.8 Setup Fee Pushback'")


class EmotionalDimensions(BaseModel):
    trust_and_rapport: float = Field(..., ge=0.0, le=10.0, description="Prospect trust, openness, and collaborative relationship (0 to 10)")
    commercial_urgency: float = Field(..., ge=0.0, le=10.0, description="Speed and deadline pressure to close (0 to 10)")
    negotiation_stance: str = Field(..., description="Stance: 'Hard Bargaining', 'Collaborative', 'Detached / Stalled', 'Ready to Sign'")


class ChannelSentiment(BaseModel):
    channel: str = Field(..., description="whatsapp, email, call, cti, etc.")
    score: float = Field(..., ge=0.0, le=10.0, description="Sentiment score in this channel")
    status: str = Field(..., description="Positive, Neutral, Hesitant")


class InteractionSentimentTag(BaseModel):
    interaction_idx: int = Field(..., description="1-based index corresponding to the interaction in the timeline")
    score: float = Field(..., ge=0.0, le=10.0, description="Sentiment score for this single interaction")
    label: str = Field(..., description="'positive', 'hesitant', 'neutral', 'friction'")
    tone: str = Field(..., description="e.g. 'Enthusiastic', 'Commercial Pushback', 'Evaluating', 'Urgent Closing'")
    key_phrase: Optional[str] = Field(None, description="Key phrase that defined the sentiment")


class CompetitorInsight(BaseModel):
    competitor_name: str = Field(..., description="Name of competitor mentioned or inferred")
    context: str = Field(..., description="Context in which the prospect brought them up")
    counter_strategy: str = Field(..., description="Tactical counter-argument or differentiator to pitch")


class ObjectionDetail(BaseModel):
    objection: str = Field(..., description="Specific hurdle raised (budget, timing, features, authority)")
    severity: str = Field(..., description="Low, Medium, or High")
    recommended_handling: str = Field(..., description="How the rep should respond")


class BattlecardAIOutput(BaseModel):
    """Schema enforced on OpenAI Structured Outputs."""
    purchase_outlook: Literal["likely", "unlikely", "undecided", "insufficient_evidence"] = "insufficient_evidence"
    confidence: Literal["low", "medium", "high"] = "low"
    evidence_summary: str = ""
    summary_compressed: bool = False
    source_utf8_bytes: int = 0
    scoring_evidence_utf8_bytes: int = 0
    overall_score: float = Field(..., ge=0.0, le=10.0, description="Final predicted lead health/closing score out of 10")
    classification: str = Field(..., description="e.g. Hot - Ready to Close, Warm - High Potential, At Risk, Cold")
    score_breakdown: ScoreBreakdown
    sentiment_summary: str = Field(..., description="Brief 2-3 sentence overview of prospect sentiment and tone")
    sentiment_trend: str = Field(..., description="Improving, Stable, or Deteriorating")
    
    # Enhanced Enterprise Sentiment Features
    emotional_dimensions: EmotionalDimensions
    channel_sentiments: List[ChannelSentiment] = Field(default_factory=list)
    positive_drivers: List[SentimentDriver] = Field(default_factory=list, description="Top positive quotes boosting sentiment")
    friction_drivers: List[SentimentDriver] = Field(default_factory=list, description="Top friction quotes dragging sentiment")
    interaction_sentiments: List[InteractionSentimentTag] = Field(default_factory=list, description="Sentiment tag per chronological interaction")

    # Battlecard Tactical Intelligence
    buying_signals: List[str] = Field(default_factory=list, description="Key positive cues indicating readiness to purchase")
    objections: List[ObjectionDetail] = Field(default_factory=list, description="List of identified objections")
    competitors: List[CompetitorInsight] = Field(default_factory=list, description="Competitors identified and battlecard counters")
    recommended_talk_tracks: List[str] = Field(default_factory=list, description="Suggested talking points for the next interaction")
    next_best_action: str = Field(..., description="Recommended immediate next step for the sales rep")


class BattlecardResponse(BattlecardAIOutput):
    """API response model including lead metadata and timestamp."""
    analysis_version: str = "evidence-v2"
    source_fingerprint: str = ""
    cache_saved: bool = True
    lead_id: str
    lead_name: Optional[str] = None
    company: Optional[str] = None
    analyzed_interactions_count: int
    last_synced_at: datetime
