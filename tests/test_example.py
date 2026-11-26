from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from build import stop_example


class StopExample(unittest.TestCase):
    def test_only_observations_after_capture_are_featured(self):
        receipt = {'id':'abc','entity':'agency:1','label':'One & Two','captured_at':'2026-01-01T00:00:00Z',
                   'file':'archive/prediction.json.gz','items':[{'target':'trip','value':1767225660}]}
        seen = {'value':1767225600,'file':'archive/observation.json.gz'}
        data = {'receipts':[receipt],'observations':{'agency:1|trip':seen}}
        pending = stop_example(data, {})
        self.assertIn('No matching sighting', pending)
        self.assertNotIn('observation.json.gz', pending)
        seen['value'] += 15
        matched = stop_example(data, {})
        self.assertIn('45 sec earlier', matched)
        self.assertIn('One &amp; Two', matched)
        self.assertIn('observation.json.gz', matched)
