# Signal Stack architecture and operation

## Runtime

The locally runnable application uses Streamlit for the dashboard, SQLite for
persistence, Gemini for structured analysis, Tavily for candidate discovery,
requests/BeautifulSoup for public HTML collection, and APScheduler for background
jobs. Start the UI and scheduler as separate processes. Credentials are loaded
from the project `.env` or its parent `.env`; secrets are never sent to the browser.
The local UI has no authentication and must not be exposed publicly as-is.

## Company research and interview

Gemini plans up to three search queries. Tavily supplies candidate URLs. The
collector checks robots rules and reads permitted public pages. Evidence records
retain source metadata and excerpts. Synthesis runs once per profile field, validates
evidence references, resolves original URLs in Python, and passes the resulting
profile through the LangGraph validator. Unknown fields remain explicitly unknown.
The interview reserves displayed question slots before receiving answers, counts
skips/follow-ups toward ten questions, and retains confidential-topic exclusions.
Founder answers remain self-reported context. Profile changes flag sources for
reassessment; reassessment recommends changes and discovers new candidates.

## Discovery and monitoring

Discovery generates company-specific searches across Customers, Competitors and
Market. Candidate inclusion reasons and credibility assessments are shown for
approval. Competitor candidates cite exact snippets returned by search. Source
approval is explicit; discovery never automatically authorizes collection.
The collector rejects private addresses, credentials, unsupported schemes and large
responses. It respects robots denial, applies a delay, follows bounded redirects,
and logs failures. Content hashes prevent repeated analysis of identical pages.
First observation is distinguished from a changed page; neither automatically
establishes a recent publication. Website terms still require source-specific review.

## Analysis and reports

Gemini receives company context and collected text. Each signal must contain an
exact evidence snippet present in that text. Scores remain separate for source
reliability, evidence strength and company relevance. Ranking combines relevance
25%, impact 25%, urgency 15%, reliability 10%, recency 10%, novelty 15%.
Reports include evidence, strategic interpretation, opportunities, risks, actions,
owners and a source appendix. Insufficient opportunities are disclosed explicitly.
The brief is rendered deterministically from saved analysis rather than asking a
second model to invent supporting details. Actions can be marked complete.

## Persistence and scheduling

SQLite stores company profiles, interviews, sources, records, analyses, crawl logs,
job logs, audits, reports and action states in indexed JSON records. Connection
contexts commit and close. Weekly and monthly jobs are independent, configurable
by time zone/hour, coalesce missed invocations while the process runs, and record
errors. Scheduler configuration refreshes every 30 seconds. The local scheduler
must stay running; an offline computer cannot execute jobs. Install it under a
process supervisor for unattended deployment.

## Uploads and reliability

CSV/TXT, XLSX and text-bearing PDF uploads become Internal records. Limits are
10 MB per file and 60,000 extracted characters per record. Scanned PDFs need OCR
outside this initial implementation. Uploaded text goes to the configured Gemini
service when analysed. Tests cover interviews, evidence references, duplicate
collection, upload-to-brief flow and dashboard rendering with mocked providers.
Live provider runs are separate and may fail due to access restrictions, quotas,
model errors or unavailable sources. Scores never independently verify claims.
