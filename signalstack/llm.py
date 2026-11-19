"""Lazy Gemini REST client: importing this module makes no network calls."""

import json
import os
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


class GeminiError(RuntimeError):
    """Configuration, transport, or incomplete Gemini response."""


def generate_json(prompt: str, schema: dict) -> str:
    """Generate one bounded JSON response; caller validates its semantics."""
    key = os.getenv("GEMINI_API_KEY", "").strip()
    model = os.getenv("GEMINI_MODEL_ID", "").strip()
    if not key or not model:
        raise GeminiError("GEMINI_API_KEY and GEMINI_MODEL_ID are required")
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "candidateCount": 1,
            "maxOutputTokens": 2048,
            "responseMimeType": "application/json",
            "responseJsonSchema": schema,
        },
    }
    request = Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{quote(model, safe='')}:generateContent",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
        method="POST",
    )
    for attempt in range(3):
        try:
            with urlopen(request, timeout=30) as response:
                result = json.load(response)
            break
        except HTTPError as exc:
            code=exc.code
            details={}
            if code==429:
                try: details=json.loads(exc.read()).get('error',{})
                except (ValueError,OSError): pass
            exc.close()
            if code==429:
                quota_ids=[]
                retry=None
                for detail in details.get('details',[]):
                    for violation in detail.get('violations',[]):
                        quota_ids.append(violation.get('quotaId',violation.get('quotaMetric','unknown')))
                    if 'retryDelay' in detail:
                        try: retry=float(detail['retryDelay'].rstrip('s'))
                        except (ValueError,TypeError): pass
                daily=any('perday' in q.casefold() for q in quota_ids)
                if retry is not None and 0<retry<=60 and not daily and attempt<2:
                    time.sleep(retry)
                    continue
                suffix='; quota='+','.join(quota_ids) if quota_ids else ''
                if retry is not None: suffix+=f'; retry after {retry:g}s'
                raise GeminiError('Gemini quota/rate limit reached (HTTP 429)'+suffix) from None
            if code in (502,503,504) and attempt<2:
                time.sleep(2**(attempt+1))
                continue
            raise GeminiError(f"Gemini request failed (HTTP {code})") from None
        except (URLError, OSError, TimeoutError):
            raise GeminiError("Gemini connection failed") from None
        except (ValueError, UnicodeError):
            raise GeminiError("Gemini returned invalid response JSON") from None
    try:
        candidates = result["candidates"]
        if len(candidates) != 1 or candidates[0]["finishReason"] != "STOP":
            raise ValueError
        parts = candidates[0]["content"]["parts"]
        text = "".join(part["text"] for part in parts if not part.get("thought", False))
        if not text.strip():
            raise ValueError
    except (KeyError, IndexError, TypeError, ValueError, AttributeError):
        raise GeminiError("Gemini returned an incomplete, blocked, or malformed response") from None
    from jsonschema import validate, ValidationError
    try:
        validate(json.loads(text), schema)
    except (ValueError, ValidationError):
        raise GeminiError('Gemini response does not match the requested JSON schema') from None
    return text
