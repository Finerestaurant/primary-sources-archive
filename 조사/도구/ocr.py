import glob,os,sys
from ocrmac import ocrmac
src=sys.argv[1]; out=src+"_ocr"; os.makedirs(out,exist_ok=True)
for p in sorted(glob.glob(os.path.join(src,"*.jpg"))):
    stem=os.path.splitext(os.path.basename(p))[0]
    t=os.path.join(out,stem+".txt")
    if os.path.exists(t): continue
    b=ocrmac.OCR(p,language_preference=["en-US"]).recognize()
    items=[(bb[1],bb[0],tx) for tx,c,bb in b if c>=0.3 and tx.strip()]
    items.sort(key=lambda r:(-r[0],r[1]))
    open(t,'w').write("\n".join(x[2] for x in items))
print("done")
