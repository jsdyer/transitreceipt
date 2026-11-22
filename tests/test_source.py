import sys,unittest
from pathlib import Path
from datetime import datetime,timezone
from google.transit import gtfs_realtime_pb2 as g
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from collect import predictions,encounters,feed
class TransitTests(unittest.TestCase):
    def setUp(self):
        self.now=datetime(2026,11,22,12,tzinfo=timezone.utc);self.ts=int(self.now.timestamp());self.stops={'10':{'name':'Test stop','lat':44.6,'lon':-63.5}}
    def trip(self,obj):
        obj.trip_id='trip';obj.start_date='20261122';obj.route_id='1'
    def message(self):
        f=g.FeedMessage();f.header.gtfs_realtime_version='2.0';f.header.timestamp=self.ts;return f
    def test_future_explicit_arrivals_only_and_cancelled_trips_excluded(self):
        f=self.message();e=f.entity.add();e.id='1';self.trip(e.trip_update.trip);s=e.trip_update.stop_time_update.add();s.stop_id='10';s.stop_sequence=2;s.arrival.time=self.ts+300
        self.assertEqual(len(predictions(f,self.stops,self.now,'America/Halifax')['10']),1)
        e.trip_update.trip.schedule_relationship=3;self.assertEqual(predictions(f,self.stops,self.now,'America/Halifax'),{})
    def test_no_speed_or_status_does_not_imply_arrival(self):
        f=self.message();e=f.entity.add();e.id='1';v=e.vehicle;self.trip(v.trip);v.stop_id='10';v.current_stop_sequence=2;v.timestamp=self.ts;v.position.latitude=44.6;v.position.longitude=-63.5
        self.assertEqual(encounters(f,self.stops,self.now,'America/Halifax'),{})
        v.position.speed=0;self.assertEqual(encounters(f,self.stops,self.now,'America/Halifax')['10'][0]['method'],'GPS encounter')
        v.position.latitude=45;self.assertEqual(encounters(f,self.stops,self.now,'America/Halifax'),{})
    def test_explicit_stopped_status_and_stale_report_handling(self):
        f=self.message();e=f.entity.add();e.id='1';v=e.vehicle;self.trip(v.trip);v.stop_id='10';v.current_stop_sequence=2;v.timestamp=self.ts;v.current_status=g.VehiclePosition.STOPPED_AT
        self.assertEqual(encounters(f,self.stops,self.now,'America/Halifax')['10'][0]['method'],'Reported at stop')
        v.timestamp=self.ts-121;self.assertEqual(encounters(f,self.stops,self.now,'America/Halifax'),{})
    def test_stale_feed_rejected(self):
        f=self.message();f.header.timestamp=self.ts-301
        with self.assertRaises(ValueError):feed(f.SerializeToString(),self.now)
    def test_missing_service_day_cannot_join_different_days(self):
        f=self.message();e=f.entity.add();e.id='1';v=e.vehicle;self.trip(v.trip);v.trip.ClearField('start_date');v.stop_id='10';v.current_stop_sequence=2;v.timestamp=self.ts;v.current_status=g.VehiclePosition.STOPPED_AT
        self.assertEqual(encounters(f,self.stops,self.now,'America/Halifax'),{})
