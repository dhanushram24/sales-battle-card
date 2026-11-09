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



class MomentumMetrics(BaseModel):
    """Phase 3: Temporal sentiment decay and momentum velocity (dS/dt)."""
    velocity_score: float = Field(0.0, description="Rate of sentiment shift over time (-5.0 to +5.0 per week)")
    momentum_direction: str = Field("neutral", description="'accelerating', 'steady', 'decelerating', 'stalled'")
    stall_risk_level: str = Field("Low", description="'Low', 'Moderate', 'High', 'Critical (Ghosting)'")
    days_since_last_customer_touch: int = Field(0, description="Calendar days since last inbound customer interaction")
    decay_weighted_score: float = Field(5.0, description="Recency-decay-weighted health score")


class StakeholderProfile(BaseModel):
    """Phase 3: Individual decision maker and committee mapping."""
    role: str = Field(..., description="'Champion', 'Economic Buyer', 'Technical Evaluator', 'Blocker', 'General Contact'")
    name: Optional[str] = None
    sentiment: float = Field(..., ge=0.0, le=10.0)
    stance: str = Field("neutral", description="'Supporter', 'Skeptic', 'Evaluating', 'Sign-Off Ready'")
    key_concerns: List[str] = Field(default_factory=list)


class CommitteeConsensus(BaseModel):
    """Phase 3: Multi-stakeholder consensus index across the buying organization."""
    consensus_index: float = Field(..., ge=0.0, le=10.0, description="Consensus score across stakeholders (0-10)")
    has_economic_buyer_alignment: bool = Field(True, description="Whether CFO/VP has directly engaged")
    stakeholders: List[StakeholderProfile] = Field(default_factory=list)


class DealSimulationRequest(BaseModel):
    """Phase 3: What-If deal scenario simulation input."""
    discount_percent: float = Field(default=0.0, ge=0.0, le=50.0, description="Hypothetical licensing discount percentage (0-50%)")
    waive_setup_fees: bool = Field(default=False, description="Whether CTI/setup connector fees are waived")
    guarantee_sla: bool = Field(default=False, description="Whether committed 99.9% uptime SLA is included")
    shorten_onboarding_days: int = Field(default=0, ge=0, le=60, description="Accelerated onboarding sprint days")
    custom_concession: Optional[str] = Field(default=None, description="Optional custom commercial concession")


class DealSimulationResponse(BaseModel):
    """Phase 3: What-If deal scenario simulation output."""
    lead_id: str
    base_score: float
    simulated_score: float
    score_delta: float
    simulated_outlook: str
    projected_buyer_reaction: str
    closing_pitch_script: str
    recommended_closing_tactic: str


class CallIntelligence(BaseModel):
    """Phase 3: Telephony speech diarization and acoustic intent analysis."""
    talk_ratio_rep: float = Field(..., ge=0.0, le=100.0, description="Percentage of conversation spoken by sales rep")
    talk_ratio_customer: float = Field(..., ge=0.0, le=100.0, description="Percentage spoken by customer")
    patience_score: float = Field(..., ge=0.0, le=10.0, description="Rep patience score; penalizes interruptions (0-10)")
    hesitation_detected: bool = Field(False, description="Whether buyer exhibited hesitation markers during pricing/SLA discussion")
    speech_summary: str = Field(..., description="Summary of call dynamics and verbal engagement")


class PortfolioLeadSummary(BaseModel):
    lead_id: str
    name: str
    company: str
    stage: str
    score: float
    classification: str
    momentum: str
    slippage_risk: bool


class PortfolioRadarResponse(BaseModel):
    """Phase 3: Pipeline portfolio risk and slippage radar metrics."""
    total_leads: int
    average_health_score: float
    healthy_deals_count: int
    at_risk_deals_count: int
    stalled_deals_count: int
    leads: List[PortfolioLeadSummary] = Field(default_factory=list)


class ReengagementPackage(BaseModel):
    """Phase 4: Autonomous deal intervention and recovery package."""
    lead_id: str
    recipient_name: str
    recipient_company: str
    urgency_level: str
    intervention_headline: str
    email_subject: str
    email_body: str
    executive_call_agenda: List[str] = Field(default_factory=list)
    recommended_concession: str


class AccountContactSummary(BaseModel):
    lead_id: str
    name: str
    role: str
    stage: str
    status: str
    assigned_to: str
    score: float


class AccountDossier(BaseModel):
    """Phase 4: Multi-contact enterprise account collective intelligence."""
    company_name: str
    total_contacts: int
    collective_health_score: float
    account_classification: str
    primary_competitor: Optional[str] = None
    active_objections: List[str] = Field(default_factory=list)
    contacts: List[AccountContactSummary] = Field(default_factory=list)
    account_risk_summary: str


class BattlecardAnalysis(BaseModel):
    """Schema enforced on OpenAI Structured Outputs."""
    purchase_outlook: Literal["likely", "unlikely", "undecided", "insufficient_evidence"] = "insufficient_evidence"
    confidence: Literal["low", "medium", "high"] = "low"
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

    # Phase 3 Advanced Semantic Intelligence
    momentum: Optional[MomentumMetrics] = None
    committee: Optional[CommitteeConsensus] = None
    call_intelligence: Optional[CallIntelligence] = None


class UsageReport(BaseModel):
    calls: int = 0
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None


class AnalysisMetrics(BaseModel):
    summary_mode: Literal["direct", "rebuilt", "incremental", "reused", "offline_heuristic"] = "direct"
    summary_model: str = ""
    scoring_model: str = ""
    reused_interactions: int = 0
    summary_processed_utf8_bytes: int = 0
    summary_cache_saved: bool = True
    summary_usage: UsageReport = Field(default_factory=UsageReport)
    scoring_usage: UsageReport = Field(default_factory=UsageReport)


class BattlecardAIOutput(BattlecardAnalysis):
    """Analysis plus application-generated metadata, never requested from the LLM."""
    evidence_summary: str = ""
    summary_compressed: bool = False
    source_utf8_bytes: int = 0
    scoring_evidence_utf8_bytes: int = 0
    analysis_metrics: Optional[AnalysisMetrics] = None


class BattlecardResponse(BattlecardAIOutput):
    """API response model including lead metadata and timestamp."""
    analysis_version: str = "evidence-v3"
    source_fingerprint: str = ""
    cache_saved: bool = True
    lead_id: str
    lead_name: Optional[str] = None
    company: Optional[str] = None
    analyzed_interactions_count: int
    last_synced_at: datetime
