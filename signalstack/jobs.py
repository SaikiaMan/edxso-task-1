from signalstack.db import rows,put,patch
from signalstack.crawler import crawl,fetch_page
from signalstack.analysis import analyse
from signalstack.brief import generate_brief

def monitor(company):
    company=next((c for c in rows('company') if c['id']==company['id']),company)
    run=put('run',company['id'],{'job':'monitor','status':'running'})
    try:
        failures=0
        for source in rows('source',company['id']):
            if source.get('approved') and source.get('active'):
                crawl(company['id'],source)
                failures += rows('crawl',company['id'])[0]['status']=='failed'
        put('run',company['id'],{'job':'monitor','status':'partial' if failures else 'complete','failures':failures},run)
    except Exception as exc:
        put('run',company['id'],{'job':'monitor','status':'failed','error':str(exc)[:500]},run)
        raise

def weekly(company):
    company=next((c for c in rows('company') if c['id']==company['id']),company)
    run=put('run',company['id'],{'job':'weekly','status':'running'})
    errors=[]
    try:
        before=len(rows('crawl',company['id']))
        for source in rows('source',company['id']):
            if source.get('approved') and source.get('active'): crawl(company['id'],source)
        for entry in rows('crawl',company['id'])[:len(rows('crawl',company['id']))-before]:
            if entry['status']=='failed': errors.append(entry)
        from signalstack.pipeline import context_fingerprint
        fingerprint=context_fingerprint(company)
        analysed={s['record_id'] for s in rows('signal',company['id']) if not s.get('superseded') and s.get('context_fingerprint')==fingerprint}
        for record in rows('record',company['id']):
            if record['id'] not in analysed:
                try: analyse(company,record)
                except Exception as exc: errors.append({'record_id':record['id'],'error':str(exc)[:500]})
        generate_brief(company)
        put('run',company['id'],{'job':'weekly','status':'partial' if errors else 'complete','errors':errors},run)
    except Exception as exc:
        put('run',company['id'],{'job':'weekly','status':'failed','error':str(exc)[:500],'errors':errors},run)
        raise

def audit(company):
    company=next((c for c in rows('company') if c['id']==company['id']),company)
    run=put('run',company['id'],{'job':'monthly','status':'running'})
    results=[]
    try:
        seen=set()
        for source in rows('source',company['id']):
            item={'source_id':source['id'],'url':source['url']}
            history=[h for h in rows('crawl',company['id']) if h.get('source_id')==source['id']]
            item['recent_failures']=sum(h.get('status')=='failed' for h in history[:5])
            item['recent_unchanged_checks']=sum(h.get('status')=='unchanged_or_duplicate' for h in history[:5])
            item['enabled']=source.get('active',True)
            if source['url'] in seen: item['recommendation']='Remove duplicate'
            elif not source.get('approved') or not item['enabled']:
                item.update(health='not checked',recommendation='Review before enabling monitoring')
            else:
                try:
                    fetch_page(source['url'])
                    item['health']='reachable'
                    item['recommendation']='Review relevance against updated founder context'
                except Exception as exc: item.update(health='unavailable',recommendation='Review removal',error=str(exc)[:300])
            seen.add(source['url'])
            if item['recent_unchanged_checks']>=5:
                item['activity']='No content changes in the last five checks; review monitoring frequency'
            if not item['enabled']: item['activity']='Source is inactive in this workspace'
            patch('source',company['id'],source['id'],{'health':item.get('health','duplicate')})
            results.append(item)
        audit_id=put('audit',company['id'],{'sources':results,'relevance_status':'pending'})
        from signalstack.pipeline import reassess,context_fingerprint
        recent=rows('reassessment',company['id'])
        from datetime import datetime,timezone,timedelta
        cutoff=(datetime.now(timezone.utc)-timedelta(days=1)).isoformat()[:19]
        if recent and recent[0].get('status')=='complete' and recent[0].get('context_fingerprint')==context_fingerprint(company) and recent[0]['created'][:19]>=cutoff:
            changes=recent[0]['changes']
        else:
            changes=reassess(company)
        candidates=rows('source',company['id'])
        candidates=[{'source_id':s['id'],'url':s['url'],'reason':s.get('reason','')} for s in candidates
                    if not s.get('approved') and s.get('active',True)]
        put('audit',company['id'],{'sources':results,'relevance_changes':changes,'candidates_for_approval':candidates,'relevance_status':'complete'},audit_id)
        put('run',company['id'],{'job':'monthly','status':'complete'},run)
    except Exception as exc:
        put('run',company['id'],{'job':'monthly','status':'failed','error':str(exc)[:500]},run)
        raise
