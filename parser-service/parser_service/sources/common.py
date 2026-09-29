from __future__ import annotations
import json, re
from datetime import datetime
from hashlib import sha1
from urllib.parse import urljoin, urlparse
from selectolax.parser import HTMLParser
from dateparser import parse as date_parse
from parser_service.models import EventPayload

def text(v):
    return re.sub(r"\s+", " ", v or "").strip() or None

def source_id(url):
    path=urlparse(url).path.rstrip('/')
    return path.split('/')[-1] if path else sha1(url.encode('utf-8')).hexdigest()[:20]

def jsonlds(html):
    tree=HTMLParser(html); out=[]
    for node in tree.css('script[type="application/ld+json"]'):
        try:
            data=json.loads(node.text())
            if isinstance(data,list): out.extend(data)
            elif isinstance(data,dict) and isinstance(data.get('@graph'),list): out.extend(data['@graph'])
            elif isinstance(data,dict): out.append(data)
        except Exception: pass
    return out

def event_ld(html):
    for x in jsonlds(html):
        typ=x.get('@type')
        types=typ if isinstance(typ,list) else [typ]
        if any(isinstance(value,str) and value.rsplit('/',1)[-1].endswith('Event') for value in types): return x
    return None

def dt(v):
    if not v:return None
    try: return datetime.fromisoformat(str(v).replace('Z','+00:00'))
    except Exception: return date_parse(str(v), languages=['ru'])

def price(v):
    if v is None:return None
    m=re.search(r'\d[\d\s]*',str(v).replace('\xa0',' '))
    return int(re.sub(r'\D','',m.group())) if m else None

def price_from_html(html, body='', city=None):
    """Extract a price from visible text or Afisha's embedded schedule data.

    Afisha.ru often omits JSON-LD offers and stores the human-readable range
    in ``PriceInterval`` (for example ``450–900 р.``).  Restrict matching to
    known currency markers so unrelated numbers in dates and IDs are ignored.
    """
    source = html or ''
    embedded = re.search(r'window\.__nrpBoot.*?(\{.*\})\s*</script>', source, re.S)
    if embedded:
        try:
            payload=json.loads(embedded.group(1))
            for marker in re.finditer(r'"MinPriceFormatted"\s*:\s*"(\d[\d\s]*)"', embedded.group(1), re.I):
                preceding=embedded.group(1)[:marker.start()]
                city_matches=list(re.finditer(r'"ShortName"\s*:\s*"(msk|spb)"', preceding, re.I))
                nearby_city={'msk':'moscow','spb':'saint-petersburg'}.get(city_matches[-1].group(1).lower()) if city_matches else None
                if city is None or nearby_city==city:
                    parsed=price(marker.group(1))
                    if parsed is not None:return parsed
        except (json.JSONDecodeError, TypeError):
            pass
    interval = re.search(r'\"PriceInterval\"\s*:\s*\"([^\"]*)', source, re.I)
    candidates = [interval.group(1)] if interval and interval.group(1) else []
    candidates.append(body or '')
    pattern = re.compile(r'(?:от\s*)?(\d[\d\s\xa0]{0,8})(?:[–—-]\d[\d\s\xa0]{0,8})?\s*(?:₽|руб(?:лей|ля)?|р\.)', re.I)
    for value in candidates:
        match = pattern.search(value)
        if match:
            return price(match.group(1))
    return None

def page_has_city(html, city):
    slug={'moscow':'msk','saint-petersburg':'spb'}.get(city)
    if not slug:
        return False
    return bool(re.search(r'"ShortName"\s*:\s*"'+re.escape(slug)+r'"', html or '', re.I))


def infer_category(*values):
    s=" ".join(str(v or "").lower() for v in values)
    rules=[("concert",("concert","music","концерт","музык")),("exhibition",("exhibition","выстав","museum","музей","art")),("theatre",("theatre","theater","performance","спектак","театр")),("cinema",("movie","cinema","film","кино")),("sport",("sport","спорт","match","матч")),("lecture",("lecture","лекци","education")),("festival",("festival","фестив")),("standup",("standup","stand-up","стендап")),("kids",("kids","children","дет")),("show",("show","шоу","circus","цирк")),("quest",("quest","квест")),("excursion",("excursion","экскурс"))]
    return next((name for name,keys in rules if any(k in s for k in keys)),"other")

def from_ld(source,url,city,data,title_hint=None,html=''):
    title=text(data.get('name')) or title_hint
    if not title:return None
    loc=data.get('location') or {}; loc=loc if isinstance(loc,dict) else {}
    addr=loc.get('address') or {}; addr=addr if isinstance(addr,dict) else {}
    geo=loc.get('geo') or {}; geo=geo if isinstance(geo,dict) else {}
    offers=data.get('offers') or []; offers=offers if isinstance(offers,list) else [offers]
    prices=[price(x.get('lowPrice') or x.get('price')) for x in offers if isinstance(x,dict)]; prices=[x for x in prices if x is not None]
    if not prices:
        embedded_price=price_from_html(html, city=city)
        if embedded_price is not None: prices=[embedded_price]
    image=data.get('image'); image=image[0] if isinstance(image,list) and image else image; image=image.get('url') if isinstance(image,dict) else image
    desc=text(data.get('description'))
    age=None; m=re.search(r'(\d{1,2})\+', str(data.get('typicalAgeRange') or '') ); age=int(m.group(1)) if m else None
    free_hint=data.get('isAccessibleForFree') is True or bool(re.search(r'бесплатн\w*|free admission', html or '', re.I))
    is_free=free_hint or bool(prices and min(prices)==0)
    return EventPayload(source=source,source_event_id=source_id(url),source_url=url,city=city,title=title,description=desc,
      category=infer_category(url,data.get('eventType'),data.get('@type'),data.get('name')),venue_name=text(loc.get('name')),address=text(addr.get('streetAddress')),
      lat=float(geo['latitude']) if geo.get('latitude') else None,lon=float(geo['longitude']) if geo.get('longitude') else None,
      start_at=dt(data.get('startDate')),end_at=dt(data.get('endDate')),price_min=min(prices) if prices else (0 if is_free else None),price_max=max(prices) if prices else (0 if is_free else None),
      is_free=is_free,age_min=age,image_url=urljoin(url,image) if image else None,ticket_url=next((urljoin(url,x['url']) for x in offers if isinstance(x,dict) and x.get('url')),url),raw_payload={'jsonld':data})

def fallback(source,url,city,html,title_hint=None):
    t=HTMLParser(html); h=t.css_first('h1'); title=text(h.text(separator=' ',strip=True) if h else '') or title_hint
    if not title:return None
    desc=t.css_first('meta[name="description"]'); img=t.css_first('meta[property="og:image"]'); body=text(t.body.text(separator=' ',strip=True) if t.body else '') or ''
    pm=price_from_html(html, body, city); am=re.search(r'(?<!\d)(\d{1,2})\+',body)
    is_free=bool(re.search(r'бесплатн\w*|free admission',body,re.I))
    return EventPayload(source=source,source_event_id=source_id(url),source_url=url,city=city,title=title,
      description=text(desc.attributes.get('content') if desc else None),category=infer_category(url,title,body),price_min=pm if pm is not None else (0 if is_free else None),
      price_max=pm if pm is not None else (0 if is_free else None),is_free=is_free,age_min=int(am.group(1)) if am else None,
      image_url=urljoin(url,img.attributes.get('content')) if img and img.attributes.get('content') else None,ticket_url=url,raw_payload={'fallback':True})
