import re,urllib.request,json,concurrent.futures as cf
UA={"User-Agent":"Mozilla/5.0 (research)"}
def get(lid):
    url=f"https://db.history.go.kr/diachronic/level.do?levelId={lid}"
    for _ in range(2):
        try:
            with urllib.request.urlopen(urllib.request.Request(url,headers=UA),timeout=40) as r:
                s=r.read().decode('utf-8','replace')
            break
        except Exception as e:
            s=None
    if not s or len(s)<20000: return lid,None
    t=re.sub(r'<script.*?</script>','',s,flags=re.S); t=re.sub(r'<[^>]+>',' ',t); t=re.sub(r'\s+',' ',t)
    m=re.search(r'일 (.{3,90}?) HOI',t)
    return lid,(m.group(1).strip() if m else None)
jobs=[]
for md,days in (('07',31),('08',31),('09',30),('10',31),('11',30),('12',31)):
    for d in range(1,days+1):
        for n in range(1,26):
            jobs.append(f"dh_013_1949_{md}_{d:02d}_{n*10:04d}")
res=[]
with cf.ThreadPoolExecutor(20) as ex:
    for lid,t in ex.map(get,jobs):
        if t: res.append((lid,t))
res.sort()
json.dump(res,open('dh013_index.json','w'),ensure_ascii=False,indent=1)
print("total items",len(res))
for lid,t in res:
    if re.search(r'金九|김구|安斗熙|안두희|京橋莊|국민장|國民葬|韓國獨立黨|한독당|金學奎|白凡',t): print(lid,t)
