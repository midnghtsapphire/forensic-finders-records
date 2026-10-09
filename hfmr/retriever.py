"""Case 001 public-records acquisition: stdlib-only CLI with immutable snapshots."""
import argparse, datetime, hashlib, json, pathlib, re, time, urllib.parse, urllib.request, urllib.error
LAYERS={"building":5,"engineering":22}
BASE="https://gis.columbus.gov/arcgis/rest/services/Schemas/BuildingZoning/MapServer"
def sha(data): return hashlib.sha256(data).hexdigest()
def get(url,retries=3):
    p=urllib.parse.urlsplit(url)
    if p.scheme!="https" or p.hostname!="gis.columbus.gov" or not p.path.startswith("/arcgis/rest/services/Schemas/BuildingZoning/MapServer/"):
        raise ValueError("Unapproved API URL")
    last=None
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"ForensicFinders/1.0 public research"}),timeout=25) as r:
                if urllib.parse.urlsplit(r.geturl()).hostname!="gis.columbus.gov": raise ValueError("Unexpected redirect")
                raw=r.read(6000001)
            if len(raw)>6000000:raise ValueError("Response exceeds size cap")
            obj=json.loads(raw)
            if "error" in obj:raise RuntimeError(str(obj["error"]))
            return obj,sha(raw)
        except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError) as exc:
            last=exc
            if isinstance(exc,urllib.error.HTTPError) and exc.code not in (429,500,502,503,504):raise
            if attempt<retries-1:time.sleep(2**attempt)
    raise last
def address_where(number,street,start,end,yearfield):
    if not (1<=number<=99999 and re.fullmatch("[A-Z]{2,25}",street) and 1800<=start<=end<=2100):raise ValueError("Invalid search input")
    # Flexible substring query; individual records still require address validation.
    return f"SITE_ADDRESS LIKE '%{number}%{street}%' AND {yearfield} >= {start} AND {yearfield} <= {end}"
def collect(layer,number,street,start,end,fetch=get):
    url=f"{BASE}/{LAYERS[layer]}"
    meta,metahash=fetch(url+"?f=json")
    fields={f["name"] for f in meta.get("fields",[])}
    yearfield="ISSUED_YEAR" if layer=="building" else "FILED_YEAR"
    needed={"SITE_ADDRESS","OBJECTID",yearfield}
    if not needed<=fields:raise ValueError(f"Schema changed: missing {sorted(needed-fields)}")
    where=address_where(number,street,start,end,yearfield)
    records=[];pages=[];offset=0;limit=1000
    while offset<limit:
        n=min(100,limit-offset)
        query=urllib.parse.urlencode({"f":"json","where":where,"outFields":"*","returnGeometry":"false","orderByFields":"OBJECTID ASC","resultOffset":offset,"resultRecordCount":n})
        payload,digest=fetch(url+"/query?"+query)
        batch=[f["attributes"] for f in payload.get("features",[])]
        pages.append({"offset":offset,"count":len(batch),"sha256":digest})
        records.extend(batch)
        if not batch or (len(batch)<n and not payload.get("exceededTransferLimit")):break
        offset+=len(batch)
    return {"layer":layer,"source":url,"schema_sha256":metahash,"where":where,"records":records,"pages":pages,"truncated":len(records)>=limit}
def run(output,number=1546,street="HIGH",start=2000,end=2010,collector=collect):
    folder=pathlib.Path(output);folder.mkdir(parents=True,exist_ok=True)
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    report={"run_id":stamp,"started_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"files":[],"errors":[],"complete":False}
    for layer in LAYERS:
        try:
            result=collector(layer,number,street,start,end)
            raw=json.dumps(result,sort_keys=True,indent=2).encode()
            filename=f"{stamp}_{layer}.json"
            (folder/filename).write_bytes(raw)
            report["files"].append({"name":filename,"sha256":sha(raw),"records":len(result["records"]),"truncated":result["truncated"]})
        except Exception as exc:
            report["errors"].append({"layer":layer,"type":type(exc).__name__,"detail":str(exc)})
    report["complete"]=not report["errors"] and not any(f["truncated"] for f in report["files"])
    report["warning"]="Addresses and historical parcels require independent validation; no record does not prove no construction."
    (folder/"manifest.json").write_text(json.dumps(report,indent=2))
    return report
def verify(folder):
    folder=pathlib.Path(folder);report=json.loads((folder/"manifest.json").read_text())
    failures=[f["name"] for f in report["files"] if not (folder/f["name"]).is_file() or sha((folder/f["name"]).read_bytes())!=f["sha256"]]
    return failures
def main():
    p=argparse.ArgumentParser();p.add_argument("--output",default="evidence");p.add_argument("--verify")
    p.add_argument("--number",type=int,default=1546);p.add_argument("--street",default="HIGH")
    p.add_argument("--start",type=int,default=2000);p.add_argument("--end",type=int,default=2010)
    a=p.parse_args()
    if a.verify:
        bad=verify(a.verify);print(json.dumps({"integrity_failures":bad}));raise SystemExit(1 if bad else 0)
    result=run(a.output,a.number,a.street,a.start,a.end)
    print(json.dumps(result,indent=2));raise SystemExit(0 if result["complete"] else 1)
if __name__=="__main__":main()
