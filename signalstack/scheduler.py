"""Run independently: python -m signalstack.scheduler (keep process running)."""
from apscheduler.schedulers.blocking import BlockingScheduler
from signalstack.db import rows
from signalstack.jobs import weekly,audit,monitor

def main():
    scheduler=BlockingScheduler(timezone='UTC')
    from apscheduler.events import EVENT_JOB_MISSED, EVENT_JOB_MAX_INSTANCES, EVENT_JOB_ERROR
    from signalstack.db import put
    def failed_event(event):
        if ':' in event.job_id:
            company_id,job=event.job_id.split(':',1)
            put('run',int(company_id),{'job':job,'status':'failed' if event.code==EVENT_JOB_ERROR else 'missed',
                                      'error':str(getattr(event,'exception','Scheduled execution missed or already running'))[:500]})
    scheduler.add_listener(failed_event,EVENT_JOB_MISSED|EVENT_JOB_MAX_INSTANCES|EVENT_JOB_ERROR)
    def refresh():
        wanted=set()
        for company in rows('company'):
            settings=company.get('settings',{})
            if not settings.get('enabled',False): continue
            for name,func,hours in [('monitor',monitor,settings.get('monitor_hours',24)),('refresh_sources',refresh_sources,settings.get('refresh_hours',168))]:
                id=f'{company["id"]}:{name}'
                wanted.add(id)
                signature=str(settings)
                existing=scheduler.get_job(id)
                if not existing or existing.name!=signature:
                    scheduler.add_job(func,'interval',id=id,name=signature,args=[company],hours=int(hours),replace_existing=True,coalesce=True,max_instances=1)
            for name,func,args in [('weekly',weekly,{'day_of_week':'mon'}),('monthly',audit,{'day':1})]:
                id=f'{company["id"]}:{name}'
                wanted.add(id)
                signature=str(settings)
                existing=scheduler.get_job(id)
                if existing and existing.name==signature: continue
                scheduler.add_job(func,'cron',id=id,name=signature,args=[company],replace_existing=True,
                    timezone=settings.get('timezone','Asia/Kolkata'),hour=int(settings.get('hour',8)),minute=0,
                    coalesce=True,max_instances=1,misfire_grace_time=3600,**args)
        for job in scheduler.get_jobs():
            if job.id!='refresh' and job.id not in wanted: scheduler.remove_job(job.id)
    scheduler.add_job(refresh,'interval',seconds=30,id='refresh')
    refresh()
    scheduler.start()

def refresh_sources(company):
    from signalstack.db import put
    from signalstack.pipeline import discover
    company=next((c for c in rows('company') if c['id']==company['id']),company)
    run=put('run',company['id'],{'job':'source_refresh','status':'running'})
    try:
        count=discover(company)
        put('run',company['id'],{'job':'source_refresh','status':'complete','candidates':count},run)
    except Exception as exc:
        put('run',company['id'],{'job':'source_refresh','status':'failed','error':str(exc)[:500]},run)
        raise

if __name__=='__main__': main()
