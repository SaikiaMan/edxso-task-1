# Verification record

## Automated verification

The regression suite covers discovery, query planning, evidence-reference checks,
adaptive interviews, skip/edit/resume behaviour, SQLite persistence, duplicate
collection, upload-to-analysis-to-brief integration, dashboard rendering, visible
provider failures, local-address rejection and scheduler execution.

```powershell
python -B -m unittest discover -s tests -v
python -m signalstack.readiness
python -m signalstack.package
```

The regression suite contains 39 tests. The readiness command reports all eight assignment
data checks met from the local database:

- three complete research profiles;
- 20+ approved MeetUniversity sources and 5–10 competitor profiles;
- 30+ non-synthetic collected records;
- three completed interviews and three qualifying briefs;
- a completed context reassessment and source-health audit.

Mocked provider responses in regression tests are not counted as business
intelligence. Readiness counts exclude synthetic uploads and unsupported signals.

On 20 November 2026, all 39 tests passed. Each of the 56 signals cited across
the three exported reports had a direct source URL and an evidence excerpt that
matched its collected record. The MeetUniversity, PostHog and Patagonia reports
cited 14, 23 and 19 signals respectively. A clean checkout imported the public
demo snapshot and passed all eight readiness checks. Opening it a second time
preserved its 11 historical briefs.

## Live dashboard verification

On 19 November 2026, the Streamlit dashboard served successfully at
`http://127.0.0.1:8501`. Browser inspection selected MeetUniversity and verified the
overview metrics, the Signal Stack evidence/crawl view, and the Monday Morning Brief
with its Markdown download control. The 20 November walkthrough in
`docs/signal-stack-demo.webm` uses a separate copy of the demo database.

The submission builder creates `submission/signal-stack-submission.zip` and a
timestamped `submission/verification-manifest.json`. The archive contains source,
documentation, examples, evidence and demo report samples, while excluding `.env`,
the operational SQLite database, research cache, uploads and generated submission
files.

## Known live-service limits

Gemini and Tavily free-tier availability depends on the configured accounts. Provider
502/503/504 responses are retried with bounded backoff and retained as visible run
failures; a passing regression suite does not certify external quota availability.
No billing status, public deployment, or hosted repository URL is asserted by local
verification.
