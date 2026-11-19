"""Live interview test using explicitly hypothetical business contexts.

Never represents these answers as company-provided information or public evidence.
"""
import argparse
from signalstack.db import rows,put
from signalstack.interview import new_session,ask_next_question,save_turn,build_interview_profile

SCENARIOS={
 'MeetUniversity':{
  'segment':'Indian students comparing postgraduate programmes in Germany and the UK',
  'growth':'improving Germany admissions guidance and transparent funding information',
  'problem':'uncertainty about total costs, funding documentation and visa timelines',
  'product':'personalized counseling, course selection and application guidance',
 },
 'PostHog':{
  'segment':'small software product teams evaluating product analytics and feature experimentation',
  'growth':'improving onboarding for privacy-conscious engineering teams',
  'problem':'difficulty combining reliable analytics, transparent pricing and privacy requirements',
  'product':'product analytics, session replay, experimentation and feature flags',
 },
 'Patagonia':{
  'segment':'outdoor customers comparing durable clothing, repair services and environmental claims',
  'growth':'helping customers make informed repair-versus-replacement decisions',
  'problem':'uncertainty about product durability, repair accessibility and the evidence behind environmental claims',
  'product':'outdoor clothing, repair and product-care services',
 },
}

def run(company):
    scenario=SCENARIOS[company['name']]
    previous=[r for r in rows('interview',company['id']) if r['session'].get('demonstration')]
    session=previous[0]['session'] if previous else new_session(company['profile'])
    session['demonstration']=True
    id=previous[0]['id'] if previous else None
    while not build_interview_profile(session)['complete']:
        q=ask_next_question(session)
        id=put('interview',company['id'],{'session':session},id)
        print(f"{company['name']} {len(session['turns'])}/10: {q['question']}",flush=True)
        words=(q['topic']+' '+q['question']).lower()
        if any(word in words for word in ('revenue','margin','lost deal','crm','internal report','sales volume')):
            save_turn(session,q,None,True)
        else:
            if any(word in words for word in ('segment','audience','customer type','who are')): answer=scenario['segment']
            elif any(word in words for word in ('priority','growth','expand','next 6','next 12','focus')): answer=scenario['growth']
            elif any(word in words for word in ('service','product','offer','different')): answer=scenario['product']
            else: answer=scenario['problem']
            save_turn(session,q,'Hypothetical demonstration assumption: '+answer+'. No private company metrics are supplied.',False)
        put('interview',company['id'],{'session':session},id)
    company['founder_context']=build_interview_profile(session)
    put('company',0,company,company['id'])
    return session

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('company')
    args=parser.parse_args()
    company=next(c for c in rows('company') if c['name']==args.company)
    if len(company.get('profile',{}))!=12: raise SystemExit('Complete company research first')
    run(company)
