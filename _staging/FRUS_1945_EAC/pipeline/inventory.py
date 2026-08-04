"""FRUS 1945 제3권에서 고를 후보를 뽑는다.

    python3 inventory.py

권 전체는 1,206건이다. 전부 옮길 수는 없고, 그렇다고 「분할」이라는 낱말이 든
문서만 추리면 왜 그렇게 그었는지가 빠진다. 그래서 **선이 움직인 날**과 그 앞뒤를
함께 볼 수 있도록, 문서마다 날짜·제목·발신·분량과 함께 **무엇을 말하는 문서인지**
표시를 붙여 목록으로 낸다. 고르는 것은 그 목록을 보고 한다.
"""
import os, re, json, html

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
XML = os.path.join(ROOT, "raw", "frus1945v03.xml")

# 무엇을 말하는 문서인가 — 겹쳐서 붙어도 된다
TAGS = [
    ("지대",   r"\bzone[sd]?\b|zonal|boundar|demarcation|frontier"),
    ("분할",   r"dismember|partition|dividing Germany|division of Germany"),
    ("베를린", r"\bBerlin\b|Greater Berlin"),
    ("항복문서", r"Instrument of Surrender|surrender document|unconditional surrender"),
    ("통제기구", r"control machinery|Control Council|Control Commission|Kommandatura"),
    ("프랑스몫", r"\bFrench\b.{0,40}\bzone\b|France.{0,40}zone"),
    ("소련",   r"Soviet|U\.S\.S\.R|Russian"),
    ("철수",   r"withdraw|evacuat"),
]


def txt(x):
    return html.unescape(re.sub(r"\s+", " ", re.sub("<[^>]+>", " ", x))).strip()


def main():
    s = open(XML, encoding="utf-8").read()
    # 절 경계 — 문서마다 어느 절에 속하는지 붙여 둔다
    secs = []
    for m in re.finditer(r"<head>(.*?)</head>", s, re.S):
        h = txt(m.group(1))
        if re.match(r"^(I{1,3}V?|IV)\.\s", h) or (30 < len(h) < 200 and re.search(
                r"Tripartite warning|prisoners of war be left|surrender of Germany"
                r"|Control Council for Germany|Soviet occupation zone|dissolution", h)):
            secs.append((m.start(), h))
    secs.sort()

    def sec_of(pos):
        cur = ""
        for p, h in secs:
            if p > pos:
                break
            cur = h
        return cur

    docs = []
    for m in re.finditer(r'<div[^>]*type="document"[^>]*>', s):
        a = m.end()
        b = s.find('<div', a + 1)
        seg = s[m.start():b if b > 0 else m.start() + 40000]
        did = (re.search(r'\bxml:id="([^"]+)"', m.group(0)) or [None, ""])[1]
        j = seg.find("</head>")
        head = txt(seg[seg.find("<head>") + 6:j]) if j > 0 else ""
        dm = re.search(r'when="(\d{4}-\d{2}-\d{2})', seg)
        body = txt(seg)
        tags = [t for t, pat in TAGS if re.search(pat, body, re.I)]
        docs.append({"id": did, "date": dm.group(1) if dm else "",
                     "head": head[:150], "chars": len(body),
                     "sec": sec_of(m.start())[:60], "tags": tags})
    docs = [d for d in docs if d["id"]]
    json.dump(docs, open(os.path.join(ROOT, "raw", "inventory.json"), "w"),
              ensure_ascii=False, indent=1)
    print(f"문서 {len(docs)}건 · {sum(d['chars'] for d in docs):,}자")
    from collections import Counter
    c = Counter(t for d in docs for t in d["tags"])
    print("표시:", dict(c))


if __name__ == "__main__":
    main()
