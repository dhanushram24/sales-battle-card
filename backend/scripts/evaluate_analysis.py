"""Compare full-history and compact evidence on synthetic sales scenarios.

Default: validate fixtures without API calls. --run-api makes paid API requests.
This small illustrative suite is not a production accuracy certification.
"""
import argparse
import copy
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.config import settings
from app.schemas.lead import LeadInfo, LeadInteraction
from app.services.analyzer import OpenAILeadAnalyzer
from app.services.summary import format_interactions, CHUNK_MAX_BYTES


class EvaluationMemoryStore:
    def __init__(self):
        self.data = {}

    def get_evidence_memory(self, lead_id):
        return copy.deepcopy(self.data.get(lead_id))

    def save_evidence_memory(self, lead_id, data):
        self.data[lead_id] = copy.deepcopy(data)


def make_history(case):
    date = datetime(2026, 1, 1, tzinfo=timezone.utc)
    # Low-information middle material forces compression while decisive facts
    # remain at opposite ends of the history. No CRM records are used.
    filler = "Rep: Product information was shared for review. No purchase decision was made during this interaction. " * 140
    return [LeadInteraction(id=str(index), lead_id=case["id"], content=content,
                interaction_type="rep_note" if index == 2 else case.get("channel", "email"),
                direction="internal" if index == 2 else case.get("direction", "inbound"),
                created_at=date + timedelta(days=index))
            for index, content in enumerate([case["opening"], filler, case["closing"]], 1)]


def assess(case, result):
    return {
        "passed": result.purchase_outlook in case["outlooks"] and case["score_min"] <= result.overall_score <= case["score_max"],
        "score": result.overall_score, "outlook": result.purchase_outlook,
        "confidence": result.confidence, "reasoning": result.sentiment_summary,
        "evidence_summary": result.evidence_summary,
        "source_utf8_bytes": result.source_utf8_bytes,
        "scoring_evidence_utf8_bytes": result.scoring_evidence_utf8_bytes,
        "usage": result.analysis_metrics.model_dump(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-api", action="store_true", help="Run the paid API comparison, including a repeated compact scoring pass")
    parser.add_argument("--case", help="Run a single fixture by id")
    parser.add_argument("--output", type=Path, default=Path("eval-results.json"))
    args = parser.parse_args()
    cases = json.loads((Path(__file__).resolve().parents[1] / "evals" / "sales_cases.json").read_text(encoding="utf-8"))
    if args.case:
        cases = [case for case in cases if case["id"] == args.case]
        if not cases:
            parser.error("Unknown case id")
    for case in cases:
        size = len(format_interactions(make_history(case)).encode("utf-8"))
        if not CHUNK_MAX_BYTES < size <= settings.MAX_EVIDENCE_BYTES:
            parser.error(f"Fixture {case['id']} does not fit the configured long-history budget")
    if not args.run_api:
        print(f"Validated {len(cases)} synthetic long-history cases. No API calls made. Use --run-api to compare model outputs and usage.")
        return 0

    results = []
    for case in cases:
        analyzer = OpenAILeadAnalyzer(summary_store=EvaluationMemoryStore())
        lead = LeadInfo(id=case["id"], name="Synthetic evaluation buyer", company="Synthetic evaluation company")
        history = make_history(case)
        try:
            baseline = analyzer.analyze_lead(lead, history, use_summary=False)
            compact = analyzer.analyze_lead(lead, history)
            reused = analyzer.analyze_lead(lead, history)
            results.append({"case": case["id"], "review_fact": case["review_fact"],
                "expected_outlooks": case["outlooks"], "expected_score_range": [case["score_min"], case["score_max"]],
                "baseline": assess(case, baseline), "compact": assess(case, compact), "reused": assess(case, reused),
                "score_delta": round(compact.overall_score - baseline.overall_score, 2)})
        except Exception as error:
            results.append({"case": case["id"], "error": str(error)})
    args.output.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    failed = sum("error" in item or not all(item[mode]["passed"] for mode in ("baseline", "compact", "reused")) for item in results)
    print(f"Wrote {len(results)} comparisons to {args.output}; {failed} cases need review. Inspect reasoning and retained facts, not only score agreement.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
