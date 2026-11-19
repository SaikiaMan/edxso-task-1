# Cost statement

Python, Streamlit, SQLite, LangGraph, requests, BeautifulSoup, pypdf, openpyxl,
python-dotenv and APScheduler are open-source dependencies. Local execution needs
no paid hosting service.

Gemini and Tavily are external services. This project uses the user's configured
accounts and does not enable billing or purchase credits. The account owner must
confirm those accounts and chosen Gemini model operate within genuinely free
quotas before assignment submission. The code does not establish account billing
status or guarantee zero provider charges. Tavily reports usage for search_web;
its returned credits are available through the discovery helper.

A research run can use up to three Tavily queries and twelve Gemini synthesis
calls, plus query planning. Discovery plans up to nine searches and assesses
candidates in batches of five. Competitor discovery plans two or three searches
and uses a second model call to evaluate candidates. Each newly analysed record
uses one model call for analysis and another for evidence review. A monthly
audit reassesses sources and searches for new ones. Free quotas can therefore
limit how much can be demonstrated in one run. Use manual triggers and inspect
provider usage before enabling schedules. No paid scraping platform is required.
