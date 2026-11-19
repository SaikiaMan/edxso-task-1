"""Report actual demonstration counts without treating mocks as delivered work."""
from signalstack.db import rows
from signalstack.interview import build_interview_profile

def readiness():
    companies=rows('company')
    primary=next((c for c in companies if c['name'].casefold()=='meetuniversity'),None)
    details=[]
    for company in companies:
        id=company['id']
        reviewed={s['id']:s for s in rows('signal',id) if not s.get('synthetic') and s.get('support_review')=='passed'}
        signals=[s for s in reviewed.values() if not s.get('superseded')]
        briefs=rows('brief',id)
        qualifying=0
        for brief in briefs:
            cited=[reviewed[key] for key in set(brief.get('signal_ids', [])) if key in reviewed]
            if brief.get('markdown') and len(cited)>=5 and sum(s['kind']=='opportunity' for s in cited)>=3:
                qualifying+=1
        interviews=rows('interview',id)
        details.append({'company':company['name'],'profile_fields':len(company.get('profile',{})),
                        'approved_sources':sum(bool(s.get('approved')) for s in rows('source',id)),
                        'competitors':len(rows('competitor',id)),
                        'actual_records':sum(not r.get('synthetic',False) for r in rows('record',id)),
                        'signals':len(signals),'opportunities':sum(s['kind']=='opportunity' for s in signals),
                        'briefs':len(briefs),'qualifying_briefs':qualifying,
                        'interview_complete':any(build_interview_profile(i['session'])['complete'] for i in interviews),
                        'context_reassessments':sum(r.get('status')=='complete' for r in rows('reassessment',id)),
                        'audits':sum(a.get('relevance_status')=='complete' for a in rows('audit',id))})
    primary_detail=next((d for d in details if primary and d['company']==primary['name']),{})
    checks={
        'Three complete research profiles':sum(d['profile_fields']==12 for d in details)>=3,
        'MeetUniversity has at least 20 approved sources':primary_detail.get('approved_sources',0)>=20,
        'MeetUniversity has 5–10 competitor profiles':5<=primary_detail.get('competitors',0)<=10,
        'At least 30 actual collected records':sum(d['actual_records'] for d in details)>=30,
        'Three completed interviews':sum(d['interview_complete'] for d in details)>=3,
        'Three reports with at least five signals and three opportunities':sum(d['qualifying_briefs']>0 for d in details)>=3,
        'Context change reassessment demonstrated':any(d['context_reassessments']>0 for d in details),
        'Source health audit demonstrated':any(d['audits']>0 for d in details),
    }
    return {'checks':checks,'companies':details,'data_targets_met':all(checks.values()),
            'note':'Counts do not independently certify content quality, provider free-tier billing, visual QA, repository publication, or a recorded screen demo.'}

if __name__=='__main__':
    import json
    print(json.dumps(readiness(),indent=2))
