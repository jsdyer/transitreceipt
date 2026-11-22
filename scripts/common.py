"""Dated source receipts: immutable files, bounded downloads, no secrets in output."""
from datetime import datetime, timezone
import gzip, hashlib, json, math, os, re, time
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
UTC = timezone.utc

def now(): return datetime.now(UTC).replace(microsecond=0)
def iso(value): return value.astimezone(UTC).isoformat().replace('+00:00','Z')
def date(value): return datetime.fromisoformat(value.replace('Z','+00:00')).astimezone(UTC)
def digest(raw): return hashlib.sha256(raw).hexdigest()
def download(url, limit=30_000_000):
    # Exceptions deliberately omit URLs: a provider URL may contain an API key.
    for attempt in range(3):
        try:
            req=Request(url,headers={'User-Agent':'CoolCode-Receipts/1.0 (+https://coolcode.ca/)','Cache-Control':'no-cache'})
            with urlopen(req,timeout=45) as response: raw=response.read(limit+1)
            if len(raw)>limit: raise ValueError('Source exceeded download limit')
            return raw
        except Exception:
            if attempt==2: raise RuntimeError('Source download failed after three attempts') from None
            time.sleep(2*(attempt+1))

def validate(receipt):
    if receipt.get('schema')!=1 or receipt.get('kind') not in ('forecast','observation'): raise ValueError('Invalid receipt kind')
    if not receipt.get('entity') or not receipt.get('items'): raise ValueError('Empty source receipt')
    captured=date(receipt['captured_at'])
    if not re.fullmatch(r'[a-f0-9]{64}',receipt['source_sha256']): raise ValueError('Missing source checksum')
    url=receipt['source_url']
    if not url.startswith('https://') or 'apikey=' in url.lower(): raise ValueError('Unsafe source URL')
    seen=set()
    for item in receipt['items']:
        if not isinstance(item.get('value'),(int,float)) or isinstance(item['value'],bool) or not math.isfinite(item['value']): raise ValueError('Non-finite value')
        if not item.get('target') or item['target'] in seen: raise ValueError('Missing or duplicate target')
        seen.add(item['target'])
        if receipt['kind']=='forecast':
            target=date(item.get('target_time',item['target']))
            origin=date(receipt['issued_at']) if receipt.get('provenance')=='published_archive' else captured
            if target<=origin: raise ValueError('Forecast was not issued/captured before target')
    return receipt

def save(receipt,root=ROOT):
    validate(receipt)
    # Same source content and selected targets must not generate duplicate receipts.
    identity={k:receipt.get(k) for k in ('kind','entity','source_sha256','items','provenance')}
    uid=digest(json.dumps(identity,sort_keys=True,separators=(',',':')).encode())[:20]
    directory=root/'archive'/receipt['captured_at'][:7]
    directory.mkdir(parents=True,exist_ok=True)
    existing=list((root/'archive').glob(f'*/*-{uid}.json.gz'))
    if existing: return existing[0]
    path=directory/(receipt['captured_at'].replace(':','').replace('-','')+'-'+uid+'.json.gz')
    receipt=dict(receipt,id=uid)
    payload=gzip.compress((json.dumps(receipt,ensure_ascii=False,separators=(',',':'))+'\n').encode(),mtime=0)
    with path.open('xb') as output: output.write(payload)
    return path

def record(kind,entity,label,source,raw,items,**extra):
    return dict(dict(schema=1,kind=kind,entity=entity,label=label,captured_at=iso(now()),source_url=source,source_sha256=digest(raw),items=items),**extra)

def status(provider_states,root=ROOT):
    target=root/'collection-status.json'
    target.write_text(json.dumps({'checked_at':iso(now()),'providers':provider_states},indent=2)+'\n')
