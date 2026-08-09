"""원본 지면을 보면서 번역을 직접 고치는 로컬 교정 도구.

    python3 JACAR_독단전행/pipeline/proofread_server.py [포트, 기본 8934]

브라우저로 http://localhost:8934/ 를 연다. 배포용이 아니라 **이 컴퓨터에서만
돈다** — 저장은 곧바로 `tr/<코드>.json`을 덮어쓴다. 표준 라이브러리만 쓴다
(외부 패키지 설치 없이 바로 돌아간다).

## 왜 필요한가

에이전트가 지면을 읽어 옮긴 게 `tr/*.json`이다. 사람이 원본과 대조하며
틀린 곳을 고치려면, 지면 이미지와 그 문서의 `ja`(원문)·`ko`(번역)를 나란히
놓고 봐야 한다. 이 서버가 그 화면을 띄운다.

## API

    GET  /api/docs          문서 목록 (사건·진행 상태 포함)
    GET  /api/doc/<ref>     문서 하나의 전체 필드 + 지면 목록
    POST /api/doc/<ref>     수정한 필드를 저장 (tr/<ref>.json 덮어씀)

정적 파일(`/pages/…jpg`, `/thumbs/…jpg`)은 문서철 루트를 그대로 내준다.
"""
import http.server
import json
import os
import re
import socketserver
import sys
import glob

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                       # JACAR_독단전행/
TR = os.path.join(ROOT, "tr")
PAGES = os.path.join(ROOT, "pages")
DOCLIST_PATH = os.path.join(HERE, "문서목록.json")
UI_PATH = os.path.join(HERE, "proofread.html")

EVENT_LABEL = {
    "changtsolin-1928": "장쭤린 폭살 · 1928",
    "manchurian-1931": "만주사변 · 1931",
    "jehol-1933": "러허 작전 · 1933",
    "marcopolo-1937": "노구교 사건 · 1937",
    "taiyuan-1937": "태원작전(산서성) · 1937",
    "nomonhan-1939": "노몬한 사건 · 1939",
}


def load_doclist():
    return json.load(open(DOCLIST_PATH, encoding="utf-8"))


def pages_of(ref):
    files = sorted(glob.glob(os.path.join(PAGES, f"{ref}-*.jpg")))
    return [os.path.splitext(os.path.basename(f))[0] for f in files]


def list_docs():
    doclist = load_doclist()
    out = []
    for ev in doclist["events"]:
        for d in ev["docs"]:
            ref = d["ref"]
            tr_path = os.path.join(TR, f"{ref}.json")
            entry = {
                "ref": ref,
                "event": ev["key"],
                "event_title": ev.get("title") or EVENT_LABEL.get(ev["key"], ev["key"]),
                "archive": ev.get("archive"),
                "title": d["title"],
                "pages_planned": d.get("pages"),
                "pages_have": len(pages_of(ref)),
                "has_tr": os.path.exists(tr_path),
            }
            if entry["has_tr"]:
                try:
                    t = json.load(open(tr_path, encoding="utf-8"))
                    entry["confidence"] = t.get("confidence")
                    entry["title_ko"] = t.get("title_ko")
                    entry["unread"] = (t.get("ja") or "").count("判読不可")
                except Exception as e:
                    entry["error"] = str(e)
            out.append(entry)
    return out


def load_doc(ref):
    pages = pages_of(ref)
    tr_path = os.path.join(TR, f"{ref}.json")
    if os.path.exists(tr_path):
        doc = json.load(open(tr_path, encoding="utf-8"))
    else:
        doc = {"ref": ref}
    doc["pages"] = pages or doc.get("pages") or []
    return doc


def save_doc(ref, body):
    if not re.fullmatch(r"[A-Za-z0-9]+", ref):
        raise ValueError("잘못된 문서 코드")
    body["ref"] = ref
    tr_path = os.path.join(TR, f"{ref}.json")
    os.makedirs(TR, exist_ok=True)
    json.dump(body, open(tr_path, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    return body


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def log_message(self, fmt, *args):
        pass  # 조용히

    def _json(self, obj, status=200):
        data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/", "/proofread", "/proofread.html"):
            html = open(UI_PATH, encoding="utf-8").read().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(html)))
            self.end_headers()
            self.wfile.write(html)
            return
        if self.path == "/api/docs":
            return self._json(list_docs())
        if self.path.startswith("/api/doc/"):
            ref = self.path[len("/api/doc/"):]
            return self._json(load_doc(ref))
        return super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/doc/"):
            ref = self.path[len("/api/doc/"):]
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length).decode("utf-8"))
            try:
                saved = save_doc(ref, body)
            except Exception as e:
                return self._json({"ok": False, "error": str(e)}, 400)
            return self._json({"ok": True, "doc": saved})
        self.send_error(404)


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8934
    with socketserver.TCPServer(("127.0.0.1", port), Handler) as httpd:
        print(f"교정 화면 → http://localhost:{port}/   (Ctrl+C로 멈춘다)")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n멈췄다.")


if __name__ == "__main__":
    main()
