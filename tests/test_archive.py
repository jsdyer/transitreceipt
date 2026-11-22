import copy,gzip,json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from common import save,validate
class ArchiveTests(unittest.TestCase):
    def example(self):
        return {'schema':1,'kind':'forecast','entity':'gauge','label':'Gauge','captured_at':'2026-11-22T00:00:00Z','source_url':'https://example.org/data','source_sha256':'a'*64,'provenance':'prospective','items':[{'target':'2026-11-22T01:00:00Z','value':2}]}
    def test_saved_receipt_is_immutable_and_repeat_deduplicates(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);r=self.example();first=save(r,root);original=first.read_bytes();r['captured_at']='2026-11-22T00:01:00Z';self.assertEqual(save(r,root),first);self.assertEqual(first.read_bytes(),original)
            r['items'][0]['value']=3;self.assertNotEqual(save(r,root),first);self.assertEqual(len(list(root.glob('archive/*/*.gz'))),2)
    def test_hindsight_and_duplicate_targets_are_rejected(self):
        r=self.example();r['items'][0]['target']=r['captured_at']
        with self.assertRaisesRegex(ValueError,'before target'):validate(r)
        r=self.example();r['items']*=2
        with self.assertRaises(ValueError):validate(r)
    def test_secrets_and_nonfinite_values_cannot_enter_archive(self):
        r=self.example();r['source_url']='https://example.org/?apikey=secret'
        with self.assertRaises(ValueError):validate(r)
        r=self.example();r['items'][0]['value']=float('nan')
        with self.assertRaises(ValueError):validate(r)
