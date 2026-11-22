#!/usr/bin/env python3
"""Sample GTFS estimates and later labelled stop encounters; never invent arrivals."""
import argparse,csv,io,json,math,os,time,zipfile
from datetime import datetime,timedelta
from urllib.parse import urlencode
from zoneinfo import ZoneInfo
from google.transit import gtfs_realtime_pb2 as gtfs
from common import ROOT,download,now,iso,date,digest,record,save,status

def distance(a,b):
    lat1,lon1,lat2,lon2=map(math.radians,[a[0],a[1],b[0],b[1]])
    q=math.sin((lat2-lat1)/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
    return 6371000*2*math.asin(min(1,math.sqrt(q)))

def stop_metadata(agency,config):
    cache=ROOT/'.cache'/f'{agency}.zip';cache.parent.mkdir(exist_ok=True)
    if not cache.exists() or time.time()-cache.stat().st_mtime>7*86400:
        raw=download(config['static']);cache.write_bytes(raw)
    with zipfile.ZipFile(cache) as z:
        stops=list(csv.DictReader(io.TextIOWrapper(z.open('stops.txt'),encoding='utf-8-sig')))
    selected={}
    for s in stops:
        if s.get('location_type','') not in ('','0'):continue
        if s['stop_id'] in config.get('stop_ids',[]) or any(q in s['stop_name'].lower() for q in config.get('stop_name_contains',[])):
            selected[s['stop_id']]={'name':s['stop_name'],'lat':float(s['stop_lat']),'lon':float(s['stop_lon'])}
    if not selected:raise ValueError('No configured stops match the current static feed')
    return selected

def feed(raw,captured):
    result=gtfs.FeedMessage();result.ParseFromString(raw)
    if not result.HasField('header') or not result.header.HasField('timestamp'):raise ValueError('Feed missing timestamp')
    age=captured.timestamp()-result.header.timestamp
    if not -60<=age<=300:raise ValueError('Stale or future GTFS feed')
    if result.header.incrementality!=0:raise ValueError('Differential feeds are unsupported')
    return result

def event_key(trip,stop_id,sequence,timezone_name,captured):
    # Never infer an absent service date: IDs can repeat across operating days.
    if not trip.trip_id or not trip.start_date or not sequence:return None
    if not trip.start_date.isdigit() or len(trip.start_date)!=8:return None
    return '|'.join([trip.trip_id,trip.start_date,trip.start_time,stop_id,str(sequence)])

def predictions(message,stops,captured,timezone_name):
    result={}
    for entity in message.entity:
        if not entity.HasField('trip_update'):continue
        t=entity.trip_update
        if t.trip.schedule_relationship in (3,6):continue
        if t.HasField('timestamp') and not -60<=captured.timestamp()-t.timestamp<=300:continue
        for s in t.stop_time_update:
            if s.stop_id not in stops or s.schedule_relationship in (1,2):continue
            if not s.HasField('arrival') or not s.arrival.HasField('time'):continue
            target=s.arrival.time
            if not 30<target-captured.timestamp()<=1800:continue
            key=event_key(t.trip,s.stop_id,s.stop_sequence,timezone_name,captured)
            if not key:continue
            p={'target':key,'target_time':iso(datetime.fromtimestamp(target,captured.tzinfo)),'value':target,'label':f'Route {t.trip.route_id or "unknown"} · trip {t.trip.trip_id}','route':t.trip.route_id,'trip':t.trip.trip_id,'sequence':s.stop_sequence}
            result.setdefault(s.stop_id,{})[key]=p
    return {k:sorted(v.values(),key=lambda p:p['value']) for k,v in result.items()}

def encounters(message,stops,captured,timezone_name):
    result={}
    for entity in message.entity:
        if not entity.HasField('vehicle'):continue
        v=entity.vehicle
        if v.stop_id not in stops or not v.HasField('timestamp') or not -30<=captured.timestamp()-v.timestamp<=120:continue
        if v.trip.schedule_relationship in (3,6):continue
        key=event_key(v.trip,v.stop_id,v.current_stop_sequence,timezone_name,captured)
        if not key:continue
        method=None
        if v.HasField('current_status') and v.current_status==gtfs.VehiclePosition.STOPPED_AT:method='Reported at stop'
        elif v.HasField('position') and v.position.HasField('speed') and 0<=v.position.speed<=1.5:
            stop=stops[v.stop_id]
            if distance((v.position.latitude,v.position.longitude),(stop['lat'],stop['lon']))<=60:method='GPS encounter'
        if method:
            point={'target':key,'value':v.timestamp,'target_time':iso(datetime.fromtimestamp(v.timestamp,captured.tzinfo)),'method':method,'vehicle':v.vehicle.id,'route':v.trip.route_id}
            existing=result.setdefault(v.stop_id,{}).get(key)
            if existing is None or point['value']<existing['value']:result[v.stop_id][key]=point
    return {k:list(v.values()) for k,v in result.items()}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--samples',type=int,default=1);parser.add_argument('--interval',type=int,default=60);args=parser.parse_args()
    if not 1<=args.samples<=15 or not 30<=args.interval<=300:parser.error('Use 1–15 samples, 30–300 seconds apart')
    configs=json.loads((ROOT/'config.json').read_text());metadata={};states=[];active={}
    for agency,config in configs.items():
        key=os.environ.get(config.get('key_env',''),'')
        if config.get('key_env') and not key:
            states.append({'name':config['name'],'status':'awaiting API key'});continue
        metadata[agency]=stop_metadata(agency,config);active[agency]=(config,key)
    if not active:raise ValueError('No transit sources configured')
    for sample in range(args.samples):
        records=[]
        for agency,(config,key) in active.items():
            for kind,field,parser_func in [('forecast','trips',predictions),('observation','vehicles',encounters)]:
                source=config[field];url=source+('?'+urlencode({'apikey':key}) if key else '')
                raw=download(url,limit=8_000_000);captured=now();message=feed(raw,captured)
                groups=parser_func(message,metadata[agency],captured,config['timezone'])
                for stop,points in groups.items():
                    label=config['name']+' · '+metadata[agency][stop]['name']
                    records.append(record(kind,agency+':'+stop,label,source,raw,points,captured_at=iso(captured),issued_at=iso(datetime.fromtimestamp(message.header.timestamp,captured.tzinfo)),provenance='prospective' if kind=='forecast' else 'observed',measurement='stop-encounter',units='unix seconds',stop=metadata[agency][stop]))
        for receipt in records:save(receipt)
        print(f'Sample {sample+1}/{args.samples}: {len(records)} stop receipts',flush=True)
        if sample+1<args.samples:time.sleep(args.interval)
    states += [{'name':c['name'],'status':'collected'} for c,k in active.values()]
    status(states)
if __name__=='__main__':main()
