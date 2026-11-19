# Demonstration and submission checklist

1. Start the dashboard and select MeetUniversity. Research the company and inspect
   evidence-backed profile fields and unknowns.
2. Complete the founder interview with actual answers, demonstrating a follow-up,
   a confidential skip and an edit.
3. Discover sources and competitors. Review relevance and website access terms,
   then approve at least 20 relevant MeetUniversity sources.
4. Run the monitoring workflow. Show collected records, duplicates, crawl failures,
   classifications, rankings and original evidence.
5. Read the full brief, download Markdown and update an action's status.
6. Upload a permitted internal sample and analyse it; label synthetic test inputs
   explicitly and do not count them as actual external developments.
7. Repeat with PostHog and Patagonia, or two other different-industry companies.
   Collect at least 30 actual records overall and export three complete reports.
8. Change one company's context and run source reassessment. Show recommendations
   and additions, then approve/remove sources as appropriate.
9. Enable schedules, keep the scheduler process running, and demonstrate the
   monthly audit and job history. Record a 5–10 minute screen demo.

The included live discovery runner is `python -m signalstack.demo`. It creates the
three configurations and records actual failures in `data/demo/status.json`.
It leaves candidate sources unapproved for review. It does not fabricate founder
answers, approve unseen sources, claim target counts were reached, or record a demo.

## Reproduce the submitted examples

Install the dependencies from the README and run `python -m signalstack.demo_workspace`.
The first launch imports the public demonstration snapshot into
`data/assignment-demo.db`. Later launches retain local edits. Select each company
and open Monday brief to inspect its saved reports. The snapshot preserves original
record IDs, dates and selected evidence excerpts. New live crawls retain the full
extracted text up to the collection limit. The regular launcher uses a separate
database for new companies.

The exported Markdown reports and company counts are in `data/demo/`. The
captioned [dashboard walkthrough](signal-stack-demo.webm) follows the saved
MeetUniversity run and shows the reports for both additional companies.
