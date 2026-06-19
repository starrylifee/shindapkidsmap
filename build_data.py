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
    # 청량꿈숲(4곳 전부 동일 위치로 통일)
    9:   ("서울특별시 동대문구 답십리동 544-2",          "서울특별시 동대문구 답십리동 544-2"),
    22:  ("서울특별시 동대문구 답십리동 544-2",          "서울특별시 동대문구 답십리동 544-2"),
    104: ("서울특별시 동대문구 답십리동 544-2",          "서울특별시 동대문구 답십리동 544-2"),
    115: ("서울특별시 동대문구 답십리동 544-2",          "서울특별시 동대문구 답십리동 544-2"),
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
# ── 좌표 직접지정 (id: (위도, 경도)) — 산 등 넓게 잡히는 곳 정밀 고정 ──
COORD_OVERRIDE = {
    17:  (37.581112, 127.063859),   # 배봉산 (구글맵 핀: H3J7+CGX)
    174: (37.581112, 127.063859),   # 배봉산둘레길
    54:  (37.590783, 127.0435458),  # 세종대왕기념관 (구글맵 핀)
    94:  (37.5918467, 127.0451893), # 천장산 하늘길 입구 (구글맵 핀)
    20:  (37.572637, 127.043109),   # 천호대로 힐링산책길 (구글맵 핀: H2FV+365)
}
for d in data:
    if d["id"] in ADDR_OVERRIDE:
        d["address"], d["query"] = ADDR_OVERRIDE[d["id"]]
    if d["id"] in QUERY_OVERRIDE:
        d["query"] = QUERY_OVERRIDE[d["id"]]
    if d["id"] in COORD_OVERRIDE:
        d["lat"], d["lng"] = COORD_OVERRIDE[d["id"]]

# ── 태그 자동 발굴 ──────────────────────────────────────────────
# 장소명+추천이유 텍스트에서 키워드를 찾아 검색·필터용 태그를 부여한다.
# (순서 = 태그 노출 우선순위. 한 장소에 여러 태그가 붙을 수 있다.)
TAG_RULES = [
    ("도서관",      ["도서관", "북카페", "책마당", "열람실", "책을 읽", "독서", "어린이실"]),
    ("공원",        ["공원", "근린공원", "수변공원", "어린이공원", "잔디밭", "팔각정"]),
    ("숲·산",       ["숲", "배봉산", "천장산", "둘레길", "수목원", "산림", "홍릉", "마로니에",
                     "자연을 느", "백송", "소나무"]),
    ("산책",        ["산책", "산책로", "걷는길", "걸으며"]),
    ("놀이터",      ["놀이터", "놀이시설", "미끄럼틀", "그네", "시소", "모래놀이", "흔들그네"]),
    ("물놀이",      ["물놀이", "수영장", "눈썰매", "썰매", "수상스포츠"]),
    ("맛집",        ["돈까스", "돈가스", "쌀국수", "칼국수", "칼국시", "통닭", "순대", "마라탕", "마라",
                     "갈비", "카레", "한우", "쭈꾸미", "불고기", "중국집", "김밥", "햄버거", "버거",
                     "음식을 파는", "맛있는 음식", "식당", "전여사", "김치전"]),
    ("분식",        ["분식"]),
    ("카페·디저트", ["카페", "커피", "베이글", "와플", "도넛", "도너츠", "빙수", "빵집", "베이커리",
                     "디저트", "음료", "쿠키", "간식을 사", "간식을 먹"]),
    ("시장",        ["시장", "먹자골목", "장을 보", "벼룩시장", "만물시장", "청과물"]),
    ("박물관·전시", ["박물관", "전시", "자연사", "DDP", "미디어아트", "관람"]),
    ("역사·문화",   ["역사", "문화관", "문화공원", "선농단", "세종대왕", "한글", "영휘원", "숭인원",
                     "현진건", "한방", "한의", "유산", "기념관", "절이지만", "법사당"]),
    ("체험·교육",   ["체험", "공방", "천문", "교육", "프로그램", "관찰", "곤충 채집", "채집",
                     "축제", "행사", "청소년"]),
    ("진로·직업",   ["진로", "직업"]),
    ("운동·스포츠", ["롤러", "스케이트", "클라이밍", "인라인", "자전거", "농구", "축구", "운동장",
                     "BMX", "암벽", "스포츠", "체육", "수영", "줄넘기", "킥보드", "골프", "운동기구",
                     "운동까지"]),
    ("실내놀이",    ["키즈카페", "인형뽑기", "뽑기", "오락실", "오락", "보드게임", "방탈출",
                     "노래방", "게임"]),
    # 주의: "문구"는 "동대문구"에 잘못 매칭되므로 가게명/문맥 키워드로 한정
    ("문구점",      ["문구야", "우일문구", "뉴띵문구", "뉴띵문고", "문구로 가득", "문구류",
                     "문구점", "문방구", "학용품", "준비물"]),
    ("대학교",      ["대학교", "대학", "경희대", "시립대", "교정"]),
    ("생활편의",    ["미용실", "헤어", "염색", "어린이집", "복지", "가족센터", "센터 내 북카페"]),
    ("무료",        ["무료"]),
]
# ── 맥락상 잘못 붙은 태그 제거 (그 장소가 아닌 '옆/근처/가는 길' 언급에서 비롯) ──
TAG_REMOVE = {
    13:  ["시장"],          # 공원 — "청과물시장과 가까워"
    128: ["시장"],          # 공원 — 동상
    40:  ["맛집"],          # 박물관 — "박물관 옆에 돼지갈비 맛집도"
    57:  ["도서관"],        # 근린공원 — "입구쪽에 배봉산 도서관있고"
    65:  ["실내놀이"],      # 복합문화공간 — 게임은 리뉴얼로 종료, "지금은 전시만"
    72:  ["도서관"],        # 풍물시장 — "동대문도서관 바로 옆"
    73:  ["대학교"],        # 작은도서관 — "대학생들인 경동시장서포터즈"
    83:  ["도서관"],        # 꽃밭 — "도서관 들어설 부지" (아직 도서관 아님)
    90:  ["공원", "놀이터"],# 기념도서관 — "바로 앞에 놀이터로 이뤄진 공원도"
    92:  ["도서관", "숲·산"],# 자연사박물관 — "이문어린이도서관쪽으로/천장산길로" (가는 길)
    94:  ["도서관"],        # 천장산 하늘길 — "이문어린이도서관까지 넘어가는 길"
    96:  ["도서관"],        # 이마트 놀이터 — "바로 작은도서관도 있어서"
    112: ["숲·산"],         # 홍릉갈비 — 가게 이름의 '홍릉'
    140: ["카페·디저트"],   # 미용실 — "쿠키와 음료도 주셔서"
    157: ["도서관"],        # 꽃밭 — "도서관 부지로 지금은 공원으로"
    172: ["대학교"],        # 고교 천문교실 — '동국대학교사범대학부속고등학교'
}
for d in data:
    text = (d["name"] or "") + " " + (d["reason"] or "")
    tags = []
    for tag, kws in TAG_RULES:
        if any(k in text for k in kws):
            tags.append(tag)
    drop = set(TAG_REMOVE.get(d["id"], []))
    d["tags"] = [t for t in tags if t not in drop]

untagged = [d for d in data if not d["tags"]]

print("추출:", len(data), "/ 스킵:", len(skipped))
print("주소있음:", sum(1 for d in data if d["address"]), "/ 사진있음:", sum(1 for d in data if d["image"]))
print("학년분포:", dict(Counter(d["grade"] for d in data)))
print("태그분포:", dict(Counter(t for d in data for t in d["tags"]).most_common()))
print("태그없음:", len(untagged))
for d in untagged: print("   ", d["id"], d["name"])
print("\n남은 이름이상치(>25자):")
for d in data:
    if len(d["name"]) > 25: print("  ", d["id"], repr(d["name"])[:60])
json.dump(data, open("data.json","w",encoding="utf-8"), ensure_ascii=False, indent=1)
print("\n검수 샘플(주소없던 것들):")
for d in data:
    if d["id"] in (103,118,49,7,136): print(" ", d["id"], "name=",repr(d["name"]), "| query=",repr(d["query"]))
