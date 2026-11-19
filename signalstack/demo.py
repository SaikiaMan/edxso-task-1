"""Real-data demonstration runner; records failures without substituting mock data."""
import json
from pathlib import Path
from signalstack.db import rows,put,ROOT
from signalstack.pipeline import research,discover,competitors
from signalstack.jobs import weekly

def main():
    output=ROOT/'data'/'demo'
    output.mkdir(parents=True,exist_ok=True)
    companies=[('MeetUniversity','https://www.meetuniversity.com'),('PostHog','https://posthog.com'),('Patagonia','https://www.patagonia.com')]
    summary=[]
    for name,website in companies:
        company=next((c for c in rows('company') if c['name']==name),None)
        if company is None:
            id=put('company',0,{'name':name,'website':website,'profile':{}})
            company=next(c for c in rows('company') if c['id']==id)
        print('Company:',name,flush=True)
        failures=[]
        for label,func in [('research',research),('discovery',discover),('competitors',competitors)]:
            print(label,flush=True)
            try:
                func(company)
                company=next(c for c in rows('company') if c['id']==company['id'])
            except Exception as exc:
                failures.append({'step':label,'error':str(exc)[:300]})
                print(label,'failed:',str(exc)[:300],flush=True)
        # Candidates remain unapproved for explicit relevance/access review in UI.
        summary.append({'company':name,'sources':len(rows('source',company['id'])),'failures':failures})
        (output/'status.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))

if __name__=='__main__': main()
