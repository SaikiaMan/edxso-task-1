"""Second-pass support and time checks; this is not independent fact verification."""
import json
from datetime import datetime,timezone
from signalstack.llm import generate_json
from signalstack.db import put,rows

def review_signal(company,signal):
    from signalstack.pipeline import company_context
    props={k:{'type':'string'} for k in ('development','interpretation','action')}
    props['supported']={'type':'boolean'}
    props['timeliness']={'type':'string','enum':['recent','historical','unknown']}
    props['signal_type']={'type':'string','enum':['development','baseline','customer_feedback','internal_feedback']}
    schema={'type':'object','properties':props,'required':list(props),'additionalProperties':False}
    result=json.loads(generate_json(
        'Review a proposed business intelligence signal. ONLY the evidence_snippet is evidence for the factual development; the proposed summary is not evidence. '
        'Rewrite development to the narrow factual claim directly established by that excerpt. Do not add names, dates, amounts, products or features absent from the excerpt. '
        'If no meaningful claim can be supported, set supported=false. Interpretations must be conditional business implications, not new facts. '
        'Use the provided current date: never describe past dates as upcoming deadlines. For old regulations, recommend checking current applicability and existing compliance, not joining by a deadline that has already passed. '
        'For regulatory or legal claims from secondary sources, require confirmation with the responsible authority before acting. '
        'Classify ordinary product descriptions as baseline, not a new launch. A source claim is not independent verification. '
        +json.dumps({'as_of_utc':datetime.now(timezone.utc).isoformat(),'company':company_context(company),
                    'source_title':signal['title'],'publication_date':signal.get('publication_date'),
                    'evidence_snippet':signal['evidence_snippet'],
                    'proposed':{k:signal[k] for k in ('development','interpretation','action')}}),schema))
    signal.update({k:v for k,v in result.items() if k!='supported'})
    signal['support_review']='passed' if result['supported'] else 'withheld'
    published=signal.get('publication_date')
    if published:
        try:
            date=datetime.fromisoformat(published.replace('Z','+00:00'))
            if date.tzinfo is None: date=date.replace(tzinfo=timezone.utc)
            age=(datetime.now(timezone.utc)-date).days
            signal['recency']=min(signal['recency'],100 if 0<=age<=7 else 70 if 0<=age<=30 else 40 if 0<=age<=90 else 10 if age>90 else 0)
        except ValueError: signal['recency']=min(signal['recency'],25)
    if result['timeliness']=='historical': signal['urgency']=min(signal['urgency'],40)
    if result['signal_type']=='baseline': signal['novelty']=min(signal['novelty'],10)
    signal['score']=round(sum(signal[k]*w for k,w in [('relevance',.25),('impact',.25),('urgency',.15),('source_reliability',.1),('recency',.1),('novelty',.15)]),1)
    return signal

def review_saved(company):
    count=0
    for signal in rows('signal',company['id']):
        if signal.get('superseded') or signal.get('support_review'): continue
        result=review_signal(company,signal)
        put('signal',company['id'],result,signal['id'])
        count+=1
        print(company['name'],'reviewed signal',signal['id'],result['support_review'],flush=True)
    return count
