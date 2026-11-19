"""Public-page collection with robots checks, address checks and crawl history."""
import hashlib
import ipaddress
import socket
import time
import io
from urllib.parse import urlsplit, urljoin
from urllib.robotparser import RobotFileParser
import requests
from bs4 import BeautifulSoup
from signalstack.db import rows, put

AGENT = 'SignalStackResearch/1.0'

def public_url(url):
    p = urlsplit(url)
    if p.scheme not in ('https', 'http') or not p.hostname or p.username or p.password or p.port not in (None,80,443):
        raise ValueError('Only public HTTP(S) URLs without credentials are supported')
    addresses = socket.getaddrinfo(p.hostname, p.port or 443)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError('Private and local addresses are not allowed')
    return url

def request(url, respect_robots=False, binary=False):
    for _ in range(5):
        public_url(url)
        if respect_robots:
            check_robots(url)
        response = requests.get(url, timeout=25, headers={'User-Agent':AGENT}, allow_redirects=False, stream=True)
        if response.is_redirect:
            url = urljoin(url,response.headers['Location'])
            response.close()
            continue
        try:
            response.raise_for_status()
        except Exception:
            response.close()
            raise
        chunks=[]
        size=0
        for chunk in response.iter_content(65536):
            size += len(chunk)
            if size > 2_000_000:
                response.close()
                raise ValueError('Page exceeds 2 MB limit')
            chunks.append(chunk)
        response.close()
        content=b''.join(chunks)
        if not binary:
            content=content.decode(response.encoding if 'charset=' in response.headers.get('Content-Type','').lower() else 'utf-8',errors='replace')
        return content, response.headers, url
    raise ValueError('Too many redirects')

def check_robots(url):
    p=urlsplit(public_url(url))
    robots_url=f'{p.scheme}://{p.netloc}/robots.txt'
    robot=RobotFileParser()
    try:
        text,_,_=request(robots_url)
        robot.parse(text.splitlines())
        if not robot.can_fetch(AGENT,url):
            raise ValueError('Collection disallowed by robots.txt')
        delay=robot.crawl_delay(AGENT) or robot.crawl_delay('*') or 1
        if delay>30:
            raise ValueError('Source crawl delay exceeds supported run budget')
        time.sleep(max(1,delay))
    except requests.HTTPError as exc:
        if exc.response.status_code not in (404,410):
            raise


def fetch_page(url):
    html,headers,final=request(url,respect_robots=True,binary=True)
    if 'application/pdf' in headers.get('Content-Type',''):
        from pypdf import PdfReader
        pdf=PdfReader(io.BytesIO(html))
        text=' '.join(' '.join(page.extract_text() or '' for page in pdf.pages).split())
        if len(text)<80: raise ValueError('PDF has insufficient extractable text')
        return {'url':url,'final_url':final,'title':str((pdf.metadata or {}).get('/Title') or final),
                'text':text[:60000],'publication_date':None,'hash':hashlib.sha256(text.encode()).hexdigest()}
    if 'html' not in headers.get('Content-Type',''):
        raise ValueError('Only public HTML and PDF sources are supported')
    soup=BeautifulSoup(html,'html.parser')
    title=soup.title.get_text(' ',strip=True) if soup.title else final
    if any(block in title.casefold() for block in ('access denied','just a moment','attention required','verify you are human','captcha')):
        raise ValueError('Source returned an access challenge; no content collected')
    published=soup.find('meta',property='article:published_time') or soup.find('meta',attrs={'name':'date'})
    published=published.get('content') if published else None
    for tag in soup(['script','style','nav','footer','header','form']): tag.decompose()
    text=' '.join(soup.get_text(' ',strip=True).split())
    if len(text)<80: raise ValueError('Insufficient readable content')
    return {'url':url,'final_url':final,'title':title,'text':text[:60000], 'publication_date':published,
            'hash':hashlib.sha256(text.encode()).hexdigest()}

def crawl(company, source):
    try:
        page=fetch_page(source['url'])
        previous=rows('record',company)
        duplicate=next((r for r in previous if r.get('hash')==page['hash']),None)
        if duplicate:
            put('crawl',company,{'source_id':source['id'],'status':'unchanged_or_duplicate','duplicate_of':duplicate['id']})
            return None
        page.update(category=source['category'],source_id=source['id'],reason=source.get('reason',''),
                    change='changed' if any(r.get('source_id')==source['id'] for r in previous) else 'first_observed')
        id=put('record',company,page)
        put('crawl',company,{'source_id':source['id'],'status':'collected','record_id':id})
        return dict(page,id=id)
    except Exception as exc:
        put('crawl',company,{'source_id':source['id'],'status':'failed','error':str(exc)[:500]})
        return None
