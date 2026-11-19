# Signal Stack

A local company-intelligence workspace that connects company research, an adaptive
founder interview, source approval, public-source monitoring, evidence-based
analysis and executive briefing. The application uses real collected information;
provider failures and missing evidence remain visible.

[Watch the 5-minute dashboard demo](docs/signal-stack-demo.webm) or read the
sample briefs for [MeetUniversity](data/demo/meetuniversity-brief.md),
[PostHog](data/demo/posthog-brief.md) and [Patagonia](data/demo/patagonia-brief.md).

## Quick start

Python 3.11 or newer is required (Python 3.12 is recommended for deployment).
Run these commands in the `signal-stack` folder:

```powershell
python -m pip install -r requirements.txt
python -m signalstack
```

Open http://127.0.0.1:8501. The launcher starts both the UI and independent
scheduler; Ctrl+C stops both. The local dashboard is intended for a single user.
To inspect the submitted examples immediately after installing the dependencies, run
`python -m signalstack.demo_workspace` instead. Select MeetUniversity, PostHog or
Patagonia in the sidebar. This opens a separate local database with the saved
interviews, public evidence excerpts, source decisions, crawl history and briefs.
Reading those results requires no provider keys. Live discovery and analysis
use the credentials described below.
For separate processes:

```powershell
python -m streamlit run app.py --server.address 127.0.0.1
python -m signalstack.scheduler
```

Create `.env` here or in the parent workspace with:

```dotenv
GEMINI_API_KEY=your_key
GEMINI_MODEL_ID=your_available_structured_output_model
TAVILY_API_KEY=your_key
```

The application loads those files automatically. Use genuinely free service tiers
and check your provider quota settings; no paid model fallback or billing activation
is implemented. Never commit `.env`. See [costs and limitations](docs/COSTS.md).

## Workflow

1. Create a company with its name and public website.
2. Run company research. Inspect findings, assumptions, unknowns and original evidence.
   Interrupted synthesis resumes from saved fields. Use Refresh research to collect
   new evidence instead of resuming the saved bundle.
3. Complete the ten-question interview. Follow-ups and skipped questions each count.
   Answers and summaries can be edited; confidential-topic exclusions are retained.
4. Discover and review Customers, Competitors and Market sources. Approve sources
   you want monitored. Internal evidence enters through CSV, XLSX, PDF or TXT uploads.
5. Run monitoring and generate a brief. The collector checks robots rules, detects
   changes and duplicate content, and saves both successful and failed checks.
6. Review ranked signals and original excerpts, download the executive brief, and
   mark recommended actions complete.
7. Configure your time zone, weekly briefing hour, monitoring interval and discovery
   interval. The scheduler must remain running. Monthly health audits check source
   availability, repeated failures, inactivity, duplication and relevance.
8. Edit business context and reassess sources. Review the before/after reasons and
   recommended additions/removals. Approval changes remain under user control.

## Evidence and demonstration

The configured demonstration companies are MeetUniversity, PostHog and Patagonia.
Their founder interviews use **explicitly hypothetical demonstration assumptions**,
not private company information. Collected external records are real public-source
material. Synthetic internal test inputs are excluded from report and record targets.

The dashboard's assignment-progress panel and this command show actual database
counts rather than treating test fixtures as completed deliverables:

```powershell
python -m signalstack.readiness
```

Reports and verification outputs are under `data/demo/`. The generated submission
package contains code, documentation, report samples and a verification manifest;
it excludes API keys, private uploads and the local operational database.

## Reliability and limits

- Research evidence and analysis excerpts retain their source URLs and original text.
- Analysis selects an excerpt ID; Python retrieves the exact short quote. A second
  model pass checks claim support and dates. Neither pass independently proves a
  source claim true; verification labels and reliability scores stay separate.
- Content marked unsupported or synthetic is withheld from executive reports.
- Publication dates can be unknown. Historical material and product baselines must
  not be mistaken for fresh news. Briefs cover signals analysed in the last seven days.
- Public collection is limited to HTML and text-bearing PDF, up to 2 MB per response.
  Internal uploads allow 10 MB. Extraction stores up to 60,000 characters and analysis
  examines the first 24,000. Scanned PDFs require external OCR.
- Authentication challenges, robots exclusions, inaccessible sources and free-tier
  errors are logged. No access restrictions are bypassed.
- Gemini 502/503/504 errors have bounded retries. Temporary 429 errors may be retried
  when the provider supplies a short retry delay; daily quota exhaustion is surfaced.
- SQLite data is stored in `data/signalstack.db`. Set `SIGNALSTACK_DB` to override it.
- The local server has no multi-user authentication. Public hosting requires an
  authenticated deployment configuration; local setup is supported by the assignment.

## Verification and packaging

```powershell
python -B -m unittest discover -s tests -v
python -m signalstack.package
```

Tests cover provider adapters, evidence validation, interviews, resume behaviour,
actual PDF/XLSX parsing, duplicate collection, scheduler execution, visible failures,
and the UI setup/interview/edit flow. Mocked provider outputs are test evidence,
not collected business developments. See [verification](docs/VERIFICATION.md),
[architecture](docs/TECHNICAL.md), and [demo instructions](docs/DEMO.md).

Optional container deployment uses `docker compose up --build` after creating a
project-local `.env`. Both services share `./data`; the UI port binds only to localhost.
The container configuration is provided for reproducibility and must be tested in
an environment with Docker before claiming a verified container deployment.
