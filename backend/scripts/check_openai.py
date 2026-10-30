"""Make one small synthetic summary request to check configured OpenAI access."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from openai import OpenAI
from app.core.config import settings
from app.services.analyzer import analysis_error_message
from app.services.provider_errors import provider_error_details


def main():
    if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY.startswith("your_"):
        print("Missing OPENAI_API_KEY in backend/.env.")
        return 1

    model = settings.OPENAI_SUMMARY_MODEL or settings.OPENAI_MODEL
    print(f"Testing {model}: one synthetic request, at most 200 output tokens, no retries.")
    try:
        with OpenAI(api_key=settings.OPENAI_API_KEY, timeout=15, max_retries=0) as client:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "Summarize sales evidence in at most 50 words. Preserve conditions and unknowns. Do not invent facts."},
                    {"role": "user", "content": "Buyer: We like the product, but our budget is not approved. Please send pricing. We will decide next month only if finance approves."},
                ],
                max_completion_tokens=200,
            )
    except Exception as error:
        print(f"FAILED ({type(error).__name__}): {analysis_error_message(error)}")
        for name, value in provider_error_details(error).items():
            print(f"  {name}: {value}")
        return 1

    print("SUCCESS: OpenAI accepted the configured credentials and returned a response.")
    summary = response.choices[0].message.content if response.choices else None
    if summary:
        print(f"Summary: {summary}")
    else:
        print("No summary text returned; connection succeeded but summary generation was not verified.")
    if response.usage:
        print(f"Reported tokens: input={response.usage.prompt_tokens}, output={response.usage.completion_tokens}")
    if not summary or response.choices[0].finish_reason != "stop":
        print("Summary incomplete; no automatic retry was made.")
        return 2
    if len(summary.split()) > 50:
        print("Summary exceeded the 50-word target; no automatic retry was made.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
