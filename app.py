import json
import streamlit as st
from signalstack.db import rows,put,remove,patch
from signalstack.pipeline import research,discover,reassess,competitors,CATEGORIES
from signalstack.interview import new_session,ask_next_question,save_turn,build_interview_profile,edit_turn,edit_summary
from signalstack.jobs import weekly,audit
from signalstack.uploads import ingest

st.set_page_config(page_title='Signal Stack',page_icon='◈',layout='wide')
st.markdown('<style>.stApp{background:#0c1423}h1,h2,h3{letter-spacing:-.035em}section[data-testid="stSidebar"]{background:#111e32}.stButton>button{border-radius:10px}</style>',unsafe_allow_html=True)
st.sidebar.title('◈ Signal Stack')
st.sidebar.caption('Company intelligence workspace')
companies=rows('company')
pending_company=st.session_state.pop('pending_company',None)
if pending_company:
    st.session_state['company_choice']=pending_company
choice=st.sidebar.selectbox('Company',['Create company']+[f"{c['id']} · {c['name']}" for c in companies],key='company_choice')
if choice=='Create company':
    st.title('Understand your next move.')
    st.caption('Research your business, follow meaningful signals, and turn evidence into decisions.')
    with st.form('setup'):
        name=st.text_input('Company name')
        website=st.text_input('Official website',placeholder='https://example.com')
        submitted=st.form_submit_button('Create workspace',type='primary')
    if submitted:
        if not name.strip() or not website.startswith(('https://','http://')): st.error('Enter a company name and HTTP(S) website.')
        else:
            new_id=put('company',0,{'name':name.strip(),'website':website,'profile':{}})
            st.session_state['pending_company']=f'{new_id} · {name.strip()}'
            st.rerun()
    st.stop()
company=next(c for c in companies if c['id']==int(choice.split(' · ')[0]))
cid=company['id']
page=st.sidebar.radio('Workspace',['Overview','Company & interview','Signal Stack','Intelligence','Monday brief','Internal uploads','Settings & runs'])
st.title(company['name'])
st.caption(company['website']+'  /  '+page)

def run(label,fn):
    try:
        with st.spinner(label): result=fn()
        st.success('Completed')
        return result
    except Exception as exc:
        put('operation_error',cid,{'operation':label,'error':str(exc)[:500]})
        st.error(str(exc))
        return None

if page=='Overview':
    cols=st.columns(4)
    for col,kind,label in zip(cols,['source','record','signal','brief'],['Sources','Collected records','Analysed signals','Saved briefs']): col.metric(label,len(rows(kind,cid)))
    st.subheader('From evidence to decisions')
    st.write('1. Research your company and complete the interview. 2. Discover and approve sources. 3. Run monitoring and generate your brief.')
    if st.button('Run monitoring and generate brief',type='primary'): run('Collecting and analysing public evidence…',lambda:weekly(company))
    st.subheader('Recent runs')
    st.dataframe(rows('run',cid),width='stretch')
    with st.expander('Assignment demonstration progress'):
        from signalstack.readiness import readiness
        status=readiness()
        for requirement,met in status['checks'].items():
            st.write(('✓ ' if met else '○ ')+requirement)
        st.caption(status['note'])
elif page=='Company & interview':
    if st.button('Research company website and public sources'):
        if run('Researching company…',lambda:research(company)) is not None: st.rerun()
    if st.button('Refresh research with new evidence'):
        if run('Collecting fresh research…',lambda:research(company,refresh=True)) is not None: st.rerun()
    for bundle in rows('research_bundle',cid)[:1]:
        with st.expander('Research evidence and collection date'):
            st.caption(bundle['created'])
            for item in bundle['evidence']:
                st.write(item['title']); st.write(item['url']); st.text(item['excerpt'])
    profile_data=company.get('profile',{})
    with st.expander('Company profile',expanded=True):
        if not profile_data: st.info('Run company research to build an evidence-backed profile.')
        for field,section in profile_data.items():
            st.markdown('**'+field.replace('_',' ').title()+'**')
            if isinstance(section,dict):
                for finding in section.get('findings',[]):
                    st.write(finding.get('value',''))
                    st.caption('Evidence-backed source claim' if finding.get('status')=='verified' else 'Assumption or founder-provided context')
                    for evidence in finding.get('evidence',[]): st.write(evidence['source_url'])
                for unknown in section.get('unknowns',[]): st.caption('Unknown: '+unknown)
            else: st.write(section)
    if profile_data:
        with st.expander('Edit company context'):
            field=st.selectbox('Profile field',list(profile_data))
            replacement=st.text_area('Updated business context',key='profile_replacement')
            st.caption('Edits are recorded as assumptions or founder-provided context, not verified public evidence.')
            if st.button('Save profile changes'):
                def update():
                    if not replacement.strip(): raise ValueError('Enter updated context')
                    put('profile_history',cid,{'profile':company['profile']})
                    company['profile'][field]={'findings':[{'value':replacement.strip(),'status':'assumption','evidence':[]}],'unknowns':[]}
                    if field=='interview_gaps': company['profile'][field]['questions']=[]
                    put('company',0,company,cid)
                    for source in rows('source',cid):
                        source['needs_reassessment']=True
                        put('source',cid,source,source['id'])
                run('Saving?',update)
    stored=rows('interview',cid)
    session=stored[0]['session'] if stored else new_session(company.get('profile') or {'company_name':company['name']})
    sid=stored[0]['id'] if stored else None
    def persist():
        put('interview',cid,{'session':session},sid)
        company['founder_context']=build_interview_profile(session)
        put('company',0,company,cid)
        for source in rows('source',cid):
            source['needs_reassessment']=True
            put('source',cid,source,source['id'])
    st.subheader('Founder interview')
    if session.get('demonstration'):
        st.info('This saved interview uses hypothetical demonstration answers, not company-provided information.')
    if st.button('Start a new interview'):
        put('interview',cid,{'session':new_session(company.get('profile',{}))})
        st.rerun()
    st.progress(len(session['turns'])/10)
    if not profile_data:
        st.info('Run company research above to tailor the interview to this business.')
    if st.button('Show next question',disabled=not bool(profile_data)):
        session['profile']=profile_data
        question=run('Preparing your question…',lambda:ask_next_question(session))
        if question: persist()
    if session['turns']:
        turn=session['turns'][-1]
        st.write(f"**{len(session['turns'])}/10 — {turn['question']}**")
        answer=st.text_area('Your answer')
        a,b=st.columns(2)
        if a.button('Save answer'):
            def answer_save():
                save_turn(session,{k:turn[k] for k in ['topic','question']},answer,False)
                persist()
            run('Saving…',answer_save)
        if b.button('Skip confidential question'):
            def skip():
                save_turn(session,{k:turn[k] for k in ['topic','question']},None,True)
                persist()
            run('Saving…',skip)
        with st.expander('Edit an earlier answer'):
            index=st.number_input('Question number',1,len(session['turns']),1)
            replacement=st.text_area('Updated answer')
            confidential=st.checkbox('Mark this answer confidential / skipped')
            if st.button('Update answer'):
                def edit():
                    edit_turn(session,index-1,None if confidential else replacement,confidential)
                    persist()
                run('Updating…',edit)
        topics=list(build_interview_profile(session)['topics'])
        if topics:
            with st.expander('Edit founder summary'):
                topic=st.selectbox('Answered topic',topics)
                summary=st.text_area('Summary for this topic')
                if st.button('Save summary'):
                    def summary_save():
                        edit_summary(session,topic,summary)
                        persist()
                    run('Saving…',summary_save)
    context=build_interview_profile(session)
    with st.expander('Founder priorities and business context'):
        for topic,turns in context['topics'].items():
            st.markdown('**'+topic.replace('_',' ').title()+'**')
            if topic in context['summary_edits']: st.write(context['summary_edits'][topic])
            for turn in turns: st.write(turn['answer'])
        st.caption('Skipped topics: '+(', '.join(context['skipped_topics']) or 'None'))
elif page=='Signal Stack':
    if st.button('Discover relevant sources'): run('Discovering and justifying candidate sources…',lambda:discover(company))
    if st.button('Reassess sources after a context change'): run('Reassessing relevance and discovering alternatives…',lambda:reassess(company))
    if st.button('Discover competitor profiles'): run('Finding evidence-backed competitor candidates…',lambda:competitors(company))
    with st.expander('Competitor profiles'):
        st.dataframe(rows('competitor',cid),width='stretch')
    with st.expander('Context change history'):
        for change in rows('reassessment',cid): st.json(change)
    with st.expander('Add a source manually'):
        url=st.text_input('Source URL')
        category=st.selectbox('Category',CATEGORIES[:3])
        reason=st.text_input('Why monitor this source?')
        if st.button('Add source') and url and reason:
            put('source',cid,{'url':url,'title':url,'category':category,'reason':reason,'approved':False,'active':True})
            st.rerun()
    for category in CATEGORIES:
        st.subheader(category)
        if category=='Internal': st.caption('Upload internal evidence through Internal uploads.')
        for source in [s for s in rows('source',cid) if s['category']==category]:
            with st.expander(source.get('title',source['url'])):
                st.write(source['url']);st.write(source['reason'])
                st.caption('Credibility: '+source.get('credibility','Not yet assessed'))
                st.caption('Health: '+source.get('health','Not checked'))
                if source.get('needs_reassessment'): st.warning('Company context changed: reassess this source.')
                approved=st.checkbox('Approved for monitoring',source.get('approved',False),key=f"approve{source['id']}")
                if approved!=source.get('approved'):
                    patch('source',cid,source['id'],{'approved':approved})
                active=st.checkbox('Active',source.get('active',True),key=f"active{source['id']}")
                if active!=source.get('active'):
                    patch('source',cid,source['id'],{'active':active})
                if st.button('Remove source',key=f"delete{source['id']}"): remove('source',cid,source['id']);st.rerun()
    st.subheader('Crawl history and duplicates');st.dataframe(rows('crawl',cid),width='stretch')
elif page=='Intelligence':
    category=st.selectbox('Category',['All']+CATEGORIES)
    minimum=st.slider('Minimum relevance',0,100,0)
    impact=st.slider('Minimum impact',0,100,0)
    term=st.text_input('Competitor or keyword')
    after=st.text_input('Discovered on or after (YYYY-MM-DD)',placeholder='2026-01-01')
    verification=st.text_input('Verification status contains')
    def discovery_time(signal):
        return signal.get('discovery_date') or signal['created']
    for signal in sorted(rows('signal',cid),key=discovery_time,reverse=True):
        if signal.get('superseded'): continue
        if ((category=='All' or signal['category']==category) and signal['relevance']>=minimum and signal['impact']>=impact
            and term.casefold() in json.dumps(signal).casefold() and discovery_time(signal)[:10]>=after
            and verification.casefold() in signal['verification'].casefold()):
            with st.expander(f"{signal['score']} · {signal['development']}"):
                st.write(signal['interpretation']);st.write(signal['action']);st.json(signal)
elif page=='Monday brief':
    if st.button('Generate fresh brief from approved sources'): run('Running intelligence workflow…',lambda:weekly(company))
    reports=rows('brief',cid)
    if reports:
        selected=st.selectbox('Report history',reports,format_func=lambda r:r['created'])
        st.download_button('Download email-ready Markdown',selected['markdown'],f"brief-{cid}.md")
        st.markdown(selected['markdown'])
    else: st.info('Your first brief will appear after real evidence has been collected and analysed.')
    st.subheader('Action tracking')
    for action in rows('action',cid):
        done=st.checkbox(action['action']+' — '+action['owner'],action['done'],key=f"action{action['id']}")
        if done!=action['done']: action['done']=done;put('action',cid,action,action['id'])
elif page=='Internal uploads':
    st.caption('Uploaded text is sent to your configured Gemini service when analysed.')
    upload=st.file_uploader('Customer feedback, CRM exports, transcripts, or reports',type=['csv','xlsx','pdf','txt'])
    synthetic=st.checkbox('This is synthetic test data (exclude from executive reports and demonstration record counts)')
    if upload and st.button('Import evidence'): run('Extracting document…',lambda:ingest(cid,upload.name,upload.getvalue(),synthetic=synthetic))
    for record in [r for r in rows('record',cid) if r['category']=='Internal']:
        with st.expander(record['title']):
            st.caption('Synthetic test input' if record.get('synthetic') else 'Uploaded business evidence')
            st.text(record['text'][:5000])
            if record.get('attachment'):
                from signalstack.db import data_directory
                path=(data_directory()/record['attachment']).resolve()
                if path.is_relative_to((data_directory()/'uploads').resolve()) and path.is_file():
                    st.download_button('Download original',path.read_bytes(),record['title'],key=f"file{record['id']}")
else:
    settings=company.get('settings',{})
    enabled=st.checkbox('Enable scheduled weekly brief and monthly audit',settings.get('enabled',False))
    zone=st.text_input('Time zone',settings.get('timezone','Asia/Kolkata'))
    hour=st.number_input('Briefing hour (0–23)',0,23,settings.get('hour',8))
    monitoring=st.number_input('Monitor approved sources every (hours)',1,720,settings.get('monitor_hours',24))
    refreshing=st.number_input('Discover fresh sources every (hours)',24,2160,settings.get('refresh_hours',168))
    if st.button('Save schedule'):
        def settings_save():
            from zoneinfo import ZoneInfo
            ZoneInfo(zone)
            company['settings']={'enabled':enabled,'timezone':zone,'hour':hour,'monitor_hours':monitoring,'refresh_hours':refreshing}
            put('company',0,company,cid)
        run('Saving…',settings_save)
    st.info('Keep the scheduler process running: python -m signalstack.scheduler')
    if st.button('Run source-health audit now'): run('Checking sources…',lambda:audit(company))
    st.dataframe(rows('run',cid),width='stretch')
    for report in rows('audit',cid): st.json(report)
    with st.expander('Research and operation failures'):
        st.json(rows('operation_error',cid)+rows('research_error',cid)+rows('discovery_error',cid)+rows('competitor_error',cid))
