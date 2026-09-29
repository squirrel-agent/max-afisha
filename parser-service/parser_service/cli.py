from __future__ import annotations
import argparse, asyncio, os
import httpx
from parser_service.browser import Browser
from parser_service.sources.web import WebSource

SOURCES=['yandex_afisha','afisha_ru','vk_events']
async def run(args):
 browser=Browser()
 result={'status':'ok','city':args.city,'sources':[],'parsed':0,'ingested':0,'errors':[],'warnings':[]}
 try:
  names=SOURCES if args.source=='all' else [args.source]
  for name in names:
   print(f'[{name}] discovering...',flush=True)
   source_result={'source':name,'parsed':0,'ingested':0,'errors':[]}
   result['sources'].append(source_result)
   try:
    events=await WebSource(name,browser).crawl(args.city,args.limit)
   except Exception as exc:
    error=f'{type(exc).__name__}: {exc}'
    source_result['errors'].append(error); result['errors'].append(f'{name}: {error}')
    print(f'[{name}] crawl failed: {error}',flush=True)
    continue
   source_result['parsed']=len(events); result['parsed']+=len(events)
   print(f'[{name}] parsed {len(events)} events',flush=True)
   if not events:
    error='No events parsed; the listing structure may have changed or returned no event cards.'
    source_result['errors'].append(error); result['errors'].append(f'{name}: {error}')
    continue
   if args.dry_run: continue
   backend=os.getenv('BACKEND_URL','http://backend:8000'); token=os.getenv('ADMIN_TOKEN','change-me-local-admin')
   async with httpx.AsyncClient(timeout=120) as client:
    for i in range(0,len(events),100):
     batch=events[i:i+100]
     try:
      r=await client.post(f'{backend}/api/admin/ingest',headers={'Authorization':f'Bearer {token}'},json={'events':[e.model_dump(mode='json') for e in batch]})
      r.raise_for_status(); payload=r.json()
      source_result['ingested']+=int(payload.get('created',0))+int(payload.get('updated',0))
      if payload.get('embedding_error'):
       warning=f'{name}: events saved, embeddings failed: {payload["embedding_error"]}'
       result['warnings'].append(warning)
       source_result.setdefault('warnings',[]).append(warning)
      if payload.get('errors'):
       errors=payload['errors']
       source_result['errors'].extend(errors); result['errors'].extend(f'{name}: {error}' for error in errors)
      print('ingest',payload,flush=True)
     except Exception as exc:
      error=f'{type(exc).__name__}: {exc}'
      source_result['errors'].append(error); result['errors'].append(f'{name} ingest: {error}')
      print(f'[{name}] ingest failed: {error}',flush=True)
   result['ingested']+=source_result['ingested']
 finally: await browser.close()
 result['status']='partial' if result['errors'] and result['ingested'] else 'error' if result['errors'] else 'ok'
 if args.dry_run: print(f'dry-run parsed={result["parsed"]} errors={len(result["errors"])}',flush=True)
 return result

def main():
 p=argparse.ArgumentParser(); p.add_argument('command',choices=['sync']); p.add_argument('--source',default='all',choices=['all',*SOURCES]); p.add_argument('--city',default='moscow'); p.add_argument('--limit',type=int,default=500); p.add_argument('--dry-run',action='store_true'); args=p.parse_args(); asyncio.run(run(args))
if __name__=='__main__': main()
