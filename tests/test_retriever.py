import tempfile,unittest,json
from pathlib import Path
from hfmr.retriever import address_where,collect,run,verify
class RetrievalTests(unittest.TestCase):
 def test_query(self):
  self.assertIn("1546",address_where(1546,"HIGH",2000,2010,"ISSUED_YEAR"))
  with self.assertRaises(ValueError):address_where(1546,"HIGH' OR 1=1",2000,2010,"ISSUED_YEAR")
 def test_collect(self):
  def fake(url):
   if "?f=json" in url:return {"fields":[{"name":x} for x in ("SITE_ADDRESS","OBJECTID","ISSUED_YEAR")]},"hash"
   return {"features":[{"attributes":{"OBJECTID":1,"SITE_ADDRESS":"1546 N HIGH ST"}}]},"pagehash"
  result=collect("building",1546,"HIGH",2000,2010,fetch=fake)
  self.assertEqual(len(result["records"]),1)
 def test_manifest_and_integrity(self):
  def fake(layer,*args):
   return {"records":[{"OBJECTID":1}],"pages":[],"truncated":False}
  with tempfile.TemporaryDirectory() as d:
   r=run(d,collector=fake)
   self.assertTrue(r["complete"]);self.assertEqual(verify(d),[])
   p=Path(d)/r["files"][0]["name"];p.write_text("tampered")
   self.assertEqual(verify(d),[p.name])
 def test_failure_not_empty(self):
  def bad(layer,*args):raise ConnectionError("offline")
  with tempfile.TemporaryDirectory() as d:
   r=run(d,collector=bad)
   self.assertFalse(r["complete"]);self.assertEqual(len(r["errors"]),2)
