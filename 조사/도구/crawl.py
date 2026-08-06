import re,urllib.request,json,sys,concurrent.futures as cf
UA={"User-Agent":"Mozilla/5.0 (research)"}
def get(lid):
    url=f"https://db.history.go.kr/diachronic/level.do?levelId={lid}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers=UA),timeout=30) as r:
            s=r.read().decode('utf-8','replace')
    except Exception as e:
        return lid,None,None
    if 'levelId' not in s or len(s)<20000: return lid,None,None
    t=re.sub(r'<script.*?</script>','',s,flags=re.S)
    t=re.sub(r'<[^>]+>',' ',t); t=re.sub(r'\s+',' ',t)
    m=re.search(r'자료대한민국사 제\d+권 (\d{4})년 \1?년? ?(\d{1,2})월 .{0,30}?일 (.+?) HOI',t)
    title=m.group(3).strip() if m else None
    if not title:
        m2=re.search(r'일 (.{3,80}?) HOI',t)
        title=m2.group(1).strip() if m2 else None
    return lid,title,len(t)
jobs=[]
for vol in ('dh_012','dh_013'):
    for md in [('06',d) for d in range(26,31)]+[('07',d) for d in range(1,32)]+[('08',d) for d in range(1,32)]:
        for n in range(1,26):
            jobs.append(f"{vol}_1949_{md[0]}_{md[1]:02d}_{n*10:04d}")
res=[]
with cf.ThreadPoolExecutor(16) as ex:
    for lid,title,_ in ex.map(get,jobs):
        if title: res.append((lid,title))
res.sort()
json.dump(res,open('dh_index.json','w'),ensure_ascii=False,indent=1)
print(len(res))
for lid,t in res:
    if re.search(r'金九|김구|安斗熙|안두희|京橋莊|국민장|國民葬|韓國獨立黨|한독당',t): print(lid,t)
