from signalstack.db import rows,put
from datetime import datetime,timezone
from datetime import timedelta

def generate_brief(company, days=7):
    cutoff=(datetime.now(timezone.utc)-timedelta(days=days)).isoformat()[:19]
    signals=sorted([s for s in rows('signal',company['id']) if not s.get('superseded') and not s.get('synthetic') and s.get('support_review')=='passed' and s.get('created','')[:19]>=cutoff],key=lambda s:s['score'],reverse=True)
    if not signals: raise ValueError('Collect and analyse real evidence before generating a brief')
    parts=[f"# {company['name']} — Monday Morning Brief",datetime.now(timezone.utc).isoformat(),f'Coverage: evidence analysed during the last {days} days. Discovery date does not establish publication date. Source claims have not been independently corroborated.','## Executive Summary']
    if company.get('founder_context',{}).get('source')=='demonstration_assumptions':
        parts.insert(2,'Business priorities in this demonstration are hypothetical exercise assumptions, not statements supplied by this company. External developments below come from collected sources.')
    if len(signals)<5: parts.append(f'Only {len(signals)} analysed signals are available. This report does not yet meet the five-development demonstration target.')
    for s in signals[:5]: parts.append(f"- [{s.get('signal_type','unclassified')}] {s['development']} [Evidence {s['id']}]({s['url']}) — {s['interpretation']}")
    for category,heading in [('Customers','Customer Signals'),('Competitors','Competitor Intelligence'),('Market','Market Intelligence'),('Internal','Internal Business Intelligence')]:
        parts.append('## '+heading)
        selected=[s for s in signals if s['category']==category][:10]
        if not selected: parts.append('No meaningful development established from collected evidence in this category.')
        for s in selected: parts.append(f"### {s['title']}\n{s['development']}\n\nEvidence: {s['evidence_snippet']}\n\nInterpretation: {s['interpretation']}\n\n[Original source]({s['url']}) | Score {s['score']} | Verification: {s['verification']}")
    for title,kind in [('Opportunities Identified','opportunity'),('Risks & Threats','threat')]:
        parts.append('## '+title)
        selected=[s for s in signals if s['kind']==kind][:5]
        if not selected: parts.append('No meaningful '+('opportunity' if kind=='opportunity' else 'risk or threat')+' established from collected evidence.')
        if kind=='opportunity' and len(selected)<3: parts.append(f'Only {len(selected)} evidence-backed opportunities identified; the three-opportunity demonstration target is not yet met.')
        for priority,s in enumerate(selected,1):
            parts.append(f"{priority}. {s['interpretation']} Impact {s['impact']}/100, urgency {s['urgency']}/100. Next step: {s['action']}. [Evidence]({s['url']})")
    parts.append('## Recommended Actions for This Week')
    for s in signals[:5]:
        parts.append(f"- {s['action']} Suggested owner: {s['owner']}. Reason: {s['interpretation']}")
        if not any(a.get('signal_id')==s['id'] for a in rows('action',company['id'])): put('action',company['id'],{'signal_id':s['id'],'action':s['action'],'owner':s['owner'],'done':False})
    parts.append('## What We Should Watch')
    if not any(s['evidence_strength']<60 for s in signals): parts.append('No additional low-evidence developments identified for the watch list.')
    parts.extend(f"- {s['development']} — {s['interpretation']}" for s in signals if s['evidence_strength']<60)
    parts.append('## Source Appendix')
    for s in signals: parts.append(f"- [{s['title']}]({s['url']}) | Published: {s.get('publication_date') or 'unknown'} | Discovered: {s.get('discovery_date') or s['created']} | {s['verification']} | Reliability {s['source_reliability']}; evidence strength {s['evidence_strength']}\n  Evidence: {s['evidence_snippet']}")
    report='\n\n'.join(parts)
    put('brief',company['id'],{'markdown':report,'signal_ids':[s['id'] for s in signals]})
    return report
