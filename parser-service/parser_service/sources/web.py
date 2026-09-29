from __future__ import annotations
from urllib.parse import urljoin, urlparse
from selectolax.parser import HTMLParser
from parser_service.browser import Browser, polite_pause
from parser_service.sources.common import event_ld, fallback, from_ld, page_has_city, text

CONFIG={
 'yandex_afisha': {'base':'https://afisha.yandex.ru','city_paths':{'moscow':'/moscow','saint-petersburg':'/saint-petersburg'},'sections':['','concert','theatre','excursions','exhibitions','sport','standup','kids','cinema','art','festival','show','quest','circus_show'],'hosts':{'afisha.yandex.ru'}},
 'afisha_ru': {'base':'https://www.afisha.ru','city_paths':{'moscow':'/msk','saint-petersburg':'/spb'},'sections':['','schedule_concert','schedule_exhibition','schedule_theatre','schedule_sport','schedule_cinema'],'hosts':{'afisha.ru','www.afisha.ru'},'parts':('/concert/','/performance/','/exhibition/','/sport/','/movie/','/event/')},
 'vk_events': {'base':'https://vk.com','city_ids':{'moscow':'1','saint-petersburg':'2'},'hosts':{'vk.com','www.vk.com'},'parts':('/event','/club')},
}

class WebSource:
 def __init__(self,name,browser:Browser): self.name=name; self.browser=browser; self.cfg=CONFIG[name]
 def listing_paths(self,city):
  if self.name=='vk_events':
   city_id=self.cfg['city_ids'].get(city)
   if not city_id: raise ValueError(f'Unsupported city for VK Events: {city}')
   return [f'/afisha?city={city_id}',f'/search?c%5Bcity%5D={city_id}&c%5Bsection%5D=events']
  city_path=self.cfg['city_paths'].get(city)
  if not city_path: raise ValueError(f'Unsupported city: {city}')
  paths=[]
  for section in self.cfg['sections']:
   path=f'{city_path}/{section}'.rstrip('/')+'/'
   paths.append(path)
  return paths
 def is_event_url(self,url,city):
  path=urlparse(url).path.rstrip('/')+'/'
  if self.name=='yandex_afisha':
   city_path=self.cfg['city_paths'].get(city,'')+'/'
   parts=path.strip('/').split('/')
   return path.startswith(city_path) and len(parts)>=3 and parts[1] in self.cfg['sections'][1:]
  if self.name=='afisha_ru':
   parts=path.strip('/').split('/')
   # Afisha.ru detail routes are global (/concert/..., /exhibition/...),
   # while their listings are city-scoped (/msk or /spb). Keep detail links
   # discoverable for either city; the page payload carries the actual city.
   return len(parts)>=2 and any(parts[0]==part.strip('/') for part in self.cfg['parts'])
  return any(part in path for part in self.cfg['parts'])
 def _collect_links(self,html,city,found,limit):
  tree=HTMLParser(html)
  for a in tree.css('a[href]'):
   href=a.attributes.get('href'); url=urljoin(self.cfg['base'],href or ''); parsed=urlparse(url)
   if parsed.netloc not in self.cfg['hosts'] or not self.is_event_url(url,city): continue
   clean=url.split('?')[0] if self.name!='vk_events' else url
   found.setdefault(clean,text(a.text(separator=' ',strip=True)))
   if len(found)>=limit:return True
  return False
 async def discover(self,city,limit):
  found={}
  base_paths=self.listing_paths(city)
  listing_paths=list(base_paths)
  city_path=self.cfg.get('city_paths',{}).get(city)
  for path in base_paths:
   if self.name!='vk_events' and path.rstrip('/')!=city_path:
    sep='&' if '?' in path else '?'
    listing_paths.extend([f'{path}{sep}page={n}' for n in range(2,6)])
  for path in listing_paths:
   url=urljoin(self.cfg['base'],path)
   try:
    html=await self.browser.get(url,dynamic=self.name=='vk_events')
   except Exception as exc:
    print(f'[{self.name}] listing error {path}: {type(exc).__name__}: {exc}',flush=True)
    continue
   before=len(found)
   if self._collect_links(html,city,found,limit):return list(found.items())
   # Some catalogue pages return a full-size anti-bot/SSR shell with no event
   # anchors. Retry those pages once in Chromium before giving up.
   if self.name!='vk_events' and len(found)==before:
    try:
     dynamic_html=await self.browser.get(url,dynamic=True)
     if dynamic_html != html and self._collect_links(dynamic_html,city,found,limit):
      return list(found.items())
    except Exception as exc:
     print(f'[{self.name}] dynamic listing error {path}: {type(exc).__name__}: {exc}',flush=True)
  return list(found.items())
 async def fetch(self,url,title_hint,city):
  html=await self.browser.get(url,dynamic=self.name=='vk_events')
  if self.name=='afisha_ru' and not page_has_city(html,city):return None
  data=event_ld(html)
  return from_ld(self.name,url,city,data,title_hint,html) if data else fallback(self.name,url,city,html,title_hint)
 async def crawl(self,city,limit):
  items=await self.discover(city,limit); out=[]
  print(f'[{self.name}] discovered {len(items)} candidate links',flush=True)
  for i,(url,hint) in enumerate(items,1):
   try:
    e=await self.fetch(url,hint,city)
    if e: out.append(e)
   except Exception as exc: print(f'[{self.name}] detail error {url}: {exc}',flush=True)
   await polite_pause()
  return out
