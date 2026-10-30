"""Small, allowlisted diagnostics; never expose provider messages or credentials."""
import re


def provider_error_details(error):
    details = {}
    body = getattr(error, "body", None)
    body = body if isinstance(body, dict) else {}
    if isinstance(body.get("error"), dict):
        body = body["error"]
    for name in ("code", "type"):
        value = getattr(error, name, None) or body.get(name)
        if isinstance(value, str) and re.fullmatch(r"[a-z_]{1,80}", value):
            details[name] = value
    status = getattr(error, "status_code", None)
    if type(status) is int:
        details["http_status"] = status
    response = getattr(error, "response", None)
    headers = getattr(response, "headers", {})
    for name in ("retry-after", "x-ratelimit-limit-requests", "x-ratelimit-limit-tokens",
                 "x-ratelimit-remaining-requests", "x-ratelimit-remaining-tokens",
                 "x-ratelimit-reset-requests", "x-ratelimit-reset-tokens"):
        value = headers.get(name)
        if isinstance(value, str) and re.fullmatch(r"[0-9.smhd]{1,40}", value):
            details[name] = value
    return details
