import re
from datetime import datetime, timezone
from typing import List, Optional, Tuple
from app.schemas.lead import LeadInfo, LeadInteraction
from app.schemas.battlecard import (
    BattlecardAIOutput, ScoreBreakdown, EmotionalDimensions,
    ChannelSentiment, SentimentDriver, InteractionSentimentTag,
    CompetitorInsight, ObjectionDetail, AnalysisMetrics, UsageReport
)
from app.services.providers.base import BaseLLMProvider


KNOWN_COMPETITORS = {
    "salesforce": (
        "Salesforce Service Cloud",
        "Highlight Paramantra's native omnichannel CTI and telephony integration without per-user connector licensing fees."
    ),
    "zoho": (
        "Zoho CRM",
        "Demonstrate deep carrier telephony CTI logging, multi-rep thread assignment, and automated workflow dispatch."
    ),
    "hubspot": (
        "HubSpot Sales Hub",
        "Emphasize native Indian telephony carrier compatibility, zero-latency call disposition, and transparent pricing."
    ),
    "freshworks": (
        "Freshsales",
        "Showcase unified omnichannel timeline consolidating WhatsApp, call recordings, and customer support threads."
    ),
    "dynamics": (
        "Microsoft Dynamics 365",
        "Point out rapid 30-day onboarding versus extended 6-month Dynamics implementation cycles."
    ),
    "leadsquared": (
        "LeadSquared",
        "Highlight superior omnichannel conversation intelligence, integrated WhatsApp bridge, and flexible workflows."
    ),
    "pipedrive": (
        "Pipedrive",
        "Demonstrate enterprise telephony routing, automated supervisor monitoring, and end-to-end communication sync."
    )
}

POSITIVE_MARKERS = [
    r"\bkeen\b", r"\bimpressed\b", r"\bgreat\b", r"\bproposal\b", r"\blicens(e|ing)\b",
    r"\bagree\b", r"\bproceed\b", r"\bready\b", r"\burgent\b", r"\bapprov(ed|al)\b",
    r"\bcomplete\s+crm\b", r"\bautomation\b", r"\binterested\b", r"\bcontract\b", r"\bsign\b",
    r"\bpositive\b", r"\bexcited\b", r"\bvalidated\b", r"\bschedule\b"
]

FRICTION_MARKERS = [
    r"\bexpensive\b", r"\bcost\b", r"\bbudget\b", r"\bdelay\b", r"\bsla\b",
    r"\bconcern\b", r"\bcompetitor\b", r"\bdiscount\b", r"\bpushback\b",
    r"\bissue\b", r"\brisk\b", r"\bholding\s+off\b", r"\bnext\s+quarter\b",
    r"\bcomplex\b", r"\bmigration\b", r"\bunacceptable\b"
]


class OfflineHeuristicProvider(BaseLLMProvider):
    """
    Deterministic semantic extraction engine.
    Analyzes actual conversation text when external LLM providers are unavailable,
    expired, or running in an air-gapped demo mode.
    """

    @property
    def name(self) -> str:
        return "offline_heuristic"

    def is_configured(self) -> bool:
        return True

    def analyze(
        self,
        lead: LeadInfo,
        interactions: List[LeadInteraction],
        transcript_text: str,
        compressed: bool,
        source_bytes: int
    ) -> BattlecardAIOutput:
        if not interactions:
            raise ValueError("No interactions available to analyze.")

        positive_count = 0
        friction_count = 0
        positive_drivers: List[SentimentDriver] = []
        friction_drivers: List[SentimentDriver] = []
        interaction_tags: List[InteractionSentimentTag] = []
        channel_stats = {}
        detected_competitors: List[CompetitorInsight] = []
        detected_objections: List[ObjectionDetail] = []
        buying_signals: List[str] = []

        # Analyze each interaction chronologically
        for idx, item in enumerate(interactions, 1):
            content = item.content or ""
            content_lower = content.lower()
            ch = (item.interaction_type or "note").lower()

            item_pos = sum(1 for m in POSITIVE_MARKERS if re.search(m, content_lower))
            item_fric = sum(1 for m in FRICTION_MARKERS if re.search(m, content_lower))

            positive_count += item_pos
            friction_count += item_fric

            # Score per interaction (baseline 6.5)
            interaction_score = round(max(2.0, min(9.5, 6.5 + (item_pos * 1.0) - (item_fric * 1.2))), 1)
            if item_pos > item_fric:
                label = "positive"
                tone = "Enthusiastic" if item_pos >= 2 else "Evaluating"
            elif item_fric > item_pos:
                label = "friction"
                tone = "Commercial Pushback" if "budget" in content_lower or "cost" in content_lower else "Concern"
            else:
                label = "neutral"
                tone = "Informational"

            # Extract quote snippet for tags
            first_sentence = content.split(".")[0].strip()[:80]
            interaction_tags.append(InteractionSentimentTag(
                interaction_idx=idx,
                score=interaction_score,
                label=label,
                tone=tone,
                key_phrase=first_sentence if len(first_sentence) > 10 else None
            ))

            # Channel aggregation
            if ch not in channel_stats:
                channel_stats[ch] = {"total_score": 0.0, "count": 0}
            channel_stats[ch]["total_score"] += interaction_score
            channel_stats[ch]["count"] += 1

            # Extract positive drivers (up to 3)
            if item_pos > 0 and len(positive_drivers) < 3 and len(content) > 15:
                # Find the matched sentence
                quotes = [s.strip() for s in content.split(".") if any(re.search(m, s.lower()) for m in POSITIVE_MARKERS)]
                if quotes:
                    quote = quotes[0][:120]
                    positive_drivers.append(SentimentDriver(
                        quote=quote,
                        channel=ch.capitalize(),
                        impact=f"+{min(1.8, 0.8 + item_pos * 0.4):.1f} High Buyer Readiness"
                    ))

            # Extract friction drivers (up to 3)
            if item_fric > 0 and len(friction_drivers) < 3 and len(content) > 15:
                quotes = [s.strip() for s in content.split(".") if any(re.search(m, s.lower()) for m in FRICTION_MARKERS)]
                if quotes:
                    quote = quotes[0][:120]
                    friction_drivers.append(SentimentDriver(
                        quote=quote,
                        channel=ch.capitalize(),
                        impact=f"-{min(1.5, 0.5 + item_fric * 0.4):.1f} Timeline / Commercial Dependency"
                    ))

            # Detect competitors from conversation text
            for comp_key, (c_name, c_strategy) in KNOWN_COMPETITORS.items():
                if comp_key in content_lower and not any(c.competitor_name == c_name for c in detected_competitors):
                    # Extract the exact sentence mentioning the competitor
                    c_sentences = [s.strip() for s in content.split(".") if comp_key in s.lower()]
                    c_context = f"Mentioned in {ch}: \"{c_sentences[0][:120]}\"" if c_sentences else f"Prospect evaluating {c_name}."
                    detected_competitors.append(CompetitorInsight(
                        competitor_name=c_name,
                        context=c_context,
                        counter_strategy=c_strategy
                    ))

            # Detect buying signals dynamically from positive interactions
            if item_pos > 0:
                pos_sentences = [s.strip() for s in content.split(".") if any(re.search(m, s.lower()) for m in POSITIVE_MARKERS)]
                for ps in pos_sentences:
                    clean_ps = ps.strip()
                    if len(clean_ps) > 15:
                        sig_text = f"Validated interest ({ch}): \"{clean_ps[:90]}\""
                        if sig_text not in buying_signals and len(buying_signals) < 4:
                            buying_signals.append(sig_text)

            # Detect objections dynamically from friction interactions
            if item_fric > 0:
                fric_sentences = [s.strip() for s in content.split(".") if any(re.search(m, s.lower()) for m in FRICTION_MARKERS)]
                for fs in fric_sentences:
                    clean_fs = fs.strip()
                    if len(clean_fs) > 15 and not any(clean_fs[:40].lower() in o.objection.lower() for o in detected_objections) and len(detected_objections) < 3:
                        is_high = any(k in clean_fs.lower() for k in ["expensive", "delay", "pushback", "unacceptable", "holding off", "risk"])
                        
                        # Contextual handling based on objection topic
                        if any(k in clean_fs.lower() for k in ["cost", "budget", "expensive", "pricing", "discount"]):
                            handling = "Demonstrate total cost reduction through consolidated telephony CTI and eliminate per-connector add-on fees."
                        elif any(k in clean_fs.lower() for k in ["timeline", "sla", "delay", "schedule"]):
                            handling = "Present committed 30-day onboarding sprint with dedicated solutions engineering lead and milestone checkpoints."
                        elif any(k in clean_fs.lower() for k in ["migration", "excel", "salesforce", "data"]):
                            handling = "Offer automated field-mapping import utilities and parallel trial validation to de-risk migration."
                        else:
                            handling = "Acknowledge requirement directly and arrange technical walkthrough to demonstrate capability."

                        detected_objections.append(ObjectionDetail(
                            objection=f"{clean_fs[:120]}",
                            severity="High" if is_high else "Medium",
                            recommended_handling=handling
                        ))

        # Channel sentiment list
        channel_sentiments = []
        for ch, stat in channel_stats.items():
            avg = round(stat["total_score"] / stat["count"], 1)
            channel_sentiments.append(ChannelSentiment(
                channel=ch,
                score=avg,
                status="Positive" if avg >= 7.0 else ("Hesitant" if avg < 5.5 else "Neutral")
            ))

        # Calculate score breakdown
        base_sentiment = min(10.0, max(1.0, 5.0 + (positive_count * 0.7) - (friction_count * 0.8)))
        engagement_score = min(10.0, max(2.0, 4.0 + len(interactions) * 0.6))
        intent_score = min(10.0, max(1.0, 5.0 + len(buying_signals) * 1.5 - len(detected_objections) * 0.5))
        risk_penalty = min(4.0, max(0.2, len(detected_objections) * 0.4 + (friction_count * 0.2)))

        overall_score = round(max(1.0, min(9.6, (base_sentiment * 0.4) + (engagement_score * 0.3) + (intent_score * 0.3) - (risk_penalty * 0.5))), 1)

        # Classification and outlook
        if overall_score >= 8.0:
            classification = "Hot - Ready to Close"
            outlook = "likely"
            confidence = "high"
        elif overall_score >= 6.5:
            classification = "Warm - High Potential"
            outlook = "likely"
            confidence = "medium"
        elif overall_score >= 5.0:
            classification = "At Risk - Needs Nurturing"
            outlook = "undecided"
            confidence = "medium"
        else:
            classification = "Cold - Low Engagement"
            outlook = "unlikely"
            confidence = "low"

        # Stance & emotions
        trust = round(min(10.0, max(2.0, 5.5 + positive_count * 0.5)), 1)
        urgency = round(min(10.0, max(2.0, 5.0 + len(buying_signals) * 1.2)), 1)
        if overall_score >= 8.0:
            stance = "Ready to Sign"
        elif friction_count > positive_count:
            stance = "Hard Bargaining"
        else:
            stance = "Collaborative"

        summary_text = (
            f"{lead.name or 'Prospect'} at {lead.company or 'the organization'} demonstrates {outlook} purchase intent. "
            f"Analyzed {len(interactions)} historical CRM conversations across {len(channel_stats)} channels with "
            f"{positive_count} strong buying markers and {len(detected_objections)} active commercial objection(s)."
        )

        # Dynamic talk tracks synthesized from detected competitors, objections, and positive drivers
        dynamic_talk_tracks: List[str] = []
        if detected_competitors:
            dynamic_talk_tracks.append(
                f"Competitive Angle: Position Paramantra against {detected_competitors[0].competitor_name} by highlighting: {detected_competitors[0].counter_strategy}"
            )
        if detected_objections:
            dynamic_talk_tracks.append(
                f"Objection Handling: For '{detected_objections[0].objection[:70]}', {detected_objections[0].recommended_handling}"
            )
        if positive_drivers:
            dynamic_talk_tracks.append(
                f"Positive Momentum: Leverage buyer interest from {positive_drivers[0].channel} regarding \"{positive_drivers[0].quote[:70]}\"."
            )
        if not dynamic_talk_tracks:
            dynamic_talk_tracks.append(
                f"Discovery Track: Review {lead.company or 'account'} operational priorities and map out native telephony and CRM capabilities."
            )

        # Dynamic next best action tailored to deal status, score, and objections
        if overall_score >= 8.0 and lead.stage and ("proposal" in lead.stage.lower() or "negotiation" in lead.stage.lower()):
            dynamic_next_action = f"Deliver customized closing contract to {lead.name or 'the buyer'} at {lead.company or 'the organization'} and schedule executive alignment call."
        elif detected_objections:
            dynamic_next_action = f"Coordinate solution review with {lead.name or 'the contact'} focusing on resolving: \"{detected_objections[0].objection[:75]}\"."
        elif buying_signals and overall_score >= 6.5:
            dynamic_next_action = f"Schedule proposal walkthrough with {lead.name or 'the decision maker'} to advance agreement on licensing terms."
        else:
            dynamic_next_action = f"Follow up with {lead.name or 'the prospect'} at {lead.company or 'the organization'} to clarify timeline and evaluation criteria."

        return BattlecardAIOutput(
            purchase_outlook=outlook,
            confidence=confidence,
            overall_score=overall_score,
            classification=classification,
            score_breakdown=ScoreBreakdown(
                sentiment_score=round(base_sentiment, 1),
                engagement_score=round(engagement_score, 1),
                intent_score=round(intent_score, 1),
                risk_penalty=round(risk_penalty, 1)
            ),
            sentiment_summary=summary_text,
            sentiment_trend="Improving" if positive_count >= friction_count else "Deteriorating",
            emotional_dimensions=EmotionalDimensions(
                trust_and_rapport=trust,
                commercial_urgency=urgency,
                negotiation_stance=stance
            ),
            channel_sentiments=channel_sentiments,
            positive_drivers=positive_drivers,
            friction_drivers=friction_drivers,
            interaction_sentiments=interaction_tags,
            buying_signals=buying_signals,
            objections=detected_objections,
            competitors=detected_competitors,
            recommended_talk_tracks=dynamic_talk_tracks,
            next_best_action=dynamic_next_action,
            evidence_summary="",
            summary_compressed=compressed,
            source_utf8_bytes=source_bytes,
            scoring_evidence_utf8_bytes=len(transcript_text.encode("utf-8")),
            analysis_metrics=AnalysisMetrics(
                summary_mode="offline_heuristic",
                summary_model="heuristic-engine-v2",
                scoring_model="offline_heuristic",
                reused_interactions=0,
                summary_processed_utf8_bytes=0,
                summary_cache_saved=True,
                summary_usage=UsageReport(),
                scoring_usage=UsageReport()
            )
        )

