"""Optional live query-planning -> Tavily handoff check."""

import json
import os

from signalstack.discovery import search_web
from signalstack.research import plan_searches


def run_check() -> None:
    # Complete plan validation before the first Tavily request.
    queries = plan_searches("MeetUniversity", "https://www.meetuniversity.com")
    print(json.dumps({"queries": queries}))
    for query in queries:
        result = search_web(query)
        print(json.dumps({
            "query": query,
            "urls": [item["url"] for item in result["results"]],
            "credits_used": result["credits_used"],
        }))


def main() -> None:
    if not all(os.getenv(name, "").strip() for name in ("GEMINI_API_KEY", "TAVILY_API_KEY")):
        print("Live check skipped: GEMINI_API_KEY and TAVILY_API_KEY are both required.")
        return
    run_check()


if __name__ == "__main__":
    main()
