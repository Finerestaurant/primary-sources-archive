import urllib.request,json,concurrent.futures as cf
UA={"User-Agent":"Mozilla/5.0 (research)"}
def lab(pid):
    try:
        with urllib.request.urlopen(urllib.request.Request(f"https://dl.ndl.go.jp/api/iiif/{pid}/manifest.json",headers=UA),timeout=25) as r:
            m=json.load(r)
        md={x["label"]:x["value"] for x in m.get("metadata",[])}
        return pid,m.get("label"),len(m["sequences"][0]["canvases"]),md.get("Publication Date",""),md.get("Series Title","")[:90],md.get("Access Restrictions")
    except Exception:
        return None
out=[]
with cf.ThreadPoolExecutor(16) as ex:
    for r in ex.map(lab,range(9850200,9850800)):
        if r: out.append(r)
json.dump(out,open('ndl_sweep.json','w'),ensure_ascii=False,indent=1)
print(len(out),"items")
for pid,l,n,d,s,acc in out:
    if l and ("Korea" in l or "Korea" in s) and ("1949" in str(d) or "1948" in str(d)):
        print(pid,"|",l,"|",n,"|",d,"|",acc,"|",s)
