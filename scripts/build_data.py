"""Build a recent dashboard while keeping every receipt downloadable."""
import gzip,json,shutil
from datetime import timedelta
from pathlib import Path
from common import date,validate

def assemble(root,output):
    receipts=[]; manifest=[]
    for path in sorted((root/'archive').glob('*/*.json.gz')):
        item=validate(json.loads(gzip.decompress(path.read_bytes())))
        relative=path.relative_to(root).as_posix()
        item['file']=relative
        manifest.append({k:item.get(k) for k in ['id','kind','entity','label','captured_at','issued_at','provenance','source_url','source_sha256','file']})
        receipts.append(item)
    if not receipts: raise ValueError('No real source receipts; collect before building')
    latest=max(date(r['captured_at']) for r in receipts)
    cutoff=latest-timedelta(days=14)
    recent=[r for r in receipts if date(r['captured_at'])>=cutoff]
    predictions=[]; observations={}
    for r in recent:
        if r['kind']=='forecast': predictions.append(r)
        else:
            for p in r['items']:
                key=r['entity']+'|'+p['target']
                obs=dict(p,captured_at=r['captured_at'],source_url=r['source_url'],file=r['file'])
                if key not in observations or (r.get('measurement')=='stop-encounter' and p['value']<observations[key]['value']) or (r.get('measurement')!='stop-encounter' and r['captured_at']>observations[key]['captured_at']): observations[key]=obs
    data={'schema':1,'last_capture':max(r['captured_at'] for r in receipts),'archive_began':min(r['captured_at'] for r in receipts),'archive_count':len(receipts),'receipts':sorted(predictions,key=lambda r:r['captured_at'],reverse=True),'observations':observations,'collection':json.loads((root/'collection-status.json').read_text())}
    (output/'data').mkdir(exist_ok=True)
    (output/'data/index.json').write_text(json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n')
    (output/'data/archive.json').write_text(json.dumps(manifest,ensure_ascii=False,separators=(',',':'))+'\n')
    shutil.copytree(root/'archive',output/'archive')
