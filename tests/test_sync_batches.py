import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from lib.database import Database
from lib.sync import SyncEngine

class SyncBatchTests(unittest.TestCase):
    def test_atomic_updates_preserve_values_and_input(self):
        with tempfile.TemporaryDirectory() as directory:
            db=Database(str(Path(directory)/'test.db'))
            rows=[{'agent_id':'a1','hostname':'before','raw_json':{'extra':[1,2]},'new_api_field':'ignored'}]
            original=copy.deepcopy(rows)
            db.upsert_records('agents','agent_id',rows)
            self.assertEqual(rows,original)
            saved=db.get_records('agents')[0]
            self.assertEqual(json.loads(saved['raw_json']),{'extra':[1,2]})
            db.upsert_records('agents','agent_id',[{'agent_id':'a1','hostname':'after'}])
            self.assertEqual(db.get_records('agents')[0]['hostname'],'after')
            with self.assertRaises(ValueError):
                db.upsert_records('agents','agent_id',[{'agent_id':'a2','hostname':'rollback'},{'hostname':'missing id'}])
            self.assertEqual(len(db.get_records('agents')),1)
    def test_sync_uses_bounded_batches_and_reports_committed_progress(self):
        db=Mock();engine=SyncEngine(Mock(),db);progress=Mock()
        rows=[{'audit_id':f'a{i}'} for i in range(1201)]
        engine._store_source_data('audits',rows,progress)
        self.assertEqual([len(c.args[2]) for c in db.upsert_records.call_args_list],[500,500,201])
        self.assertEqual([c.args[1] for c in progress.call_args_list],[500,1000,1201])
        self.assertEqual(rows[0],{'audit_id':'a0'})
if __name__=='__main__':unittest.main()
