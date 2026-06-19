# -*- coding: utf-8 -*-
import csv, json, re, sys, os
from collections import Counter
sys.stdout.reconfigure(encoding="utf-8")

src = r"C:\Users\forin\Documents\카카오톡 받은 파일\Padlet -      -    .csv"
rows = list(csv.DictReader(open(src, encoding="utf-8-sig", newline="")))

# 개인정보 익명화 치환 목록 (이름 등) — 깃에 올리지 않는 별도 파일에서 로드
REDACT = {}
if os.path.exists("pii_redactions.json"):
    REDACT = json.load(open("pii_redactions.json", encoding="utf-8"))

def clean(s): return (s or "").strip()
ADDR_RE = re.compile(r"(서울[특별시]*\s*[가-힣]*구[^\n,]*)")

def extract_address(block):
    if not block: return ""
    for line in block.split("\n"):
        m = ADDR_RE.search(line.strip())
        if m: return m.group(1).strip()
    m = ADDR_RE.search(block.replace("\n", " "))
    return m.group(1).strip() if m else ""

def name_from_title(title):
    if not title: return ""
    m = re.search(r"\(([^)]+)\)", title)
    if m: return m.group(1).strip()
    # 괄호 없음: 학급/학생이름 접두 제거
    t = re.sub(r"^\s*(\d\s*학년\s*\d\s*반|\d\s*-\s*\d\s*반?)\s*", "", title)
    parts = t.split()
    if parts and re.fullmatch(r"[가-힣]{2,4}", parts[0]):
        parts = parts[1:]  # 학생 이름 제거
    return " ".join(parts).strip()

def parse_body(body):
    if not body or body == "데이터 없음": return "", "", False
    if "이유" not in body and "장소" not in body:
        return "", body.strip(), True  # 자유서술
    parts = re.split(r"이유\s*:", body, maxsplit=1)
    reason = parts[1].strip() if len(parts) > 1 else ""
    head = re.sub(r"^.*?장소\s*:", "", parts[0], count=1, flags=re.S).strip()
    return head, reason, False

def get_class(title):
    m = re.match(r"\s*(\d)\s*(?:학년\s*)?-?\s*(\d)\s*반?", title or "")
    return f"{m.group(1)}-{m.group(2)}" if m else ""

data, skipped = [], []
for r in rows:
    title, body, section = clean(r["제목"]), clean(r["본문"]), clean(r["섹션"])
    if section == "안내사항" or title in ("데이터 없음", "ㅎㅎ"):
        skipped.append(title); continue
    block, reason, freeform = parse_body(body)
    name = name_from_title(title) if (freeform or not block) else (name_from_title(title) or block.split("\n")[0].strip())
    if not name: name = name_from_title(title)
    addr = "" if freeform else extract_address(block)
    if not name and not addr:
        skipped.append(title); continue
    img = ""  # 개인정보 보호: 사진 링크 제외
    # 개인정보 보호: 본문 속 학생 이름 익명화 (목록은 pii_redactions.json)
    for _bad, _good in REDACT.items():
        reason = reason.replace(_bad, _good)
    # 지오코딩 힌트: 주소 우선, 없으면 장소명+동대문구
    query = addr if addr else (name + " 동대문구" if "동대문" not in name else name)
    data.append({
        # 개인정보 보호: 반(class) 정보 제외 — 학년만 유지
        "id": int(r["게시물 번호"]), "grade": section,
        "name": name, "address": addr, "reason": reason, "query": query,
        "image": img,
    })

# ── 삭제할 게시물 (코스 안내 등 지도에 부적합) ──
DROP_IDS = {85}
data = [d for d in data if d["id"] not in DROP_IDS]

# ── 주소를 직접 보완한 장소: (표시용 주소, 검색용 주소) ──
ADDR_OVERRIDE = {
    105: ("서울 동대문구 천호대로45나길 52",            "서울 동대문구 천호대로45나길 52"),  # 백억(100억)분식
    137: ("서울 동대문구 천호대로45나길 52",            "서울 동대문구 천호대로45나길 52"),
    104: ("서울특별시 동대문구 답십리동 544-2",          "서울특별시 동대문구 답십리동 544-2"),  # 청량꿈숲
    119: ("서울 동대문구 답십리로1길 10 힐스에비뉴 125호", "서울 동대문구 답십리로1길 10"),       # 더 베이글 숍(위클리베이글)
    129: ("서울 동대문구 고산자로32길 78 103동",         "서울 동대문구 고산자로32길 78"),      # 그라시엘 어린이집
}
# ── 지오코딩이 실패한 장소: 검색용 별칭(query) 지정 ──
QUERY_OVERRIDE = {
    10:  "청계한신휴플러스아파트",     # 단지 내 놀이터 → 아파트로 검색
    23:  "청계한신휴플러스아파트",
    102: "힐스테이트청계아파트",       # 103동 앞 놀이터 → 아파트로 검색
    175: "이문어린이도서관",          # 군더더기 제거
}
# ── 그래도 안 잡히면 좌표 직접지정 (id: (위도, 경도)) ──
COORD_OVERRIDE = {
    # 예) 105: (37.5701, 127.0568),
}
for d in data:
    if d["id"] in ADDR_OVERRIDE:
        d["address"], d["query"] = ADDR_OVERRIDE[d["id"]]
    if d["id"] in QUERY_OVERRIDE:
        d["query"] = QUERY_OVERRIDE[d["id"]]
    if d["id"] in COORD_OVERRIDE:
        d["lat"], d["lng"] = COORD_OVERRIDE[d["id"]]

print("추출:", len(data), "/ 스킵:", len(skipped))
print("주소있음:", sum(1 for d in data if d["address"]), "/ 사진있음:", sum(1 for d in data if d["image"]))
print("학년분포:", dict(Counter(d["grade"] for d in data)))
print("\n남은 이름이상치(>25자):")
for d in data:
    if len(d["name"]) > 25: print("  ", d["id"], repr(d["name"])[:60])
json.dump(data, open("data.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
print("\n검수 샘플(주소없던 것들):")
for d in data:
    if d["id"] in (103,118,49,7,136): print(" ", d["id"], "name=",repr(d["name"]), "| query=",repr(d["query"]))
