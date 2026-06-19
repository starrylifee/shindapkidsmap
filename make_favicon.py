# -*- coding: utf-8 -*-
"""지도 핀 모양 파비콘 생성 (favicon.png)"""
from PIL import Image, ImageDraw

S = 512
SS = S * 4  # 슈퍼샘플링(4배)
img = Image.new("RGBA", (SS, SS), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

NAVY = (43, 43, 64, 255)     # 사이트 헤더색
ORANGE = (245, 130, 49, 255) # 포인트색
WHITE = (255, 255, 255, 255)

# 1) 둥근 사각 배경
pad = 24 * 4
r = 110 * 4
d.rounded_rectangle([pad, pad, SS - pad, SS - pad], radius=r, fill=NAVY)

# 2) 흰색 지도 핀 (원 + 아래 삼각)
cx = SS // 2
head_cy = int(SS * 0.40)
head_r = int(SS * 0.20)
tip_y = int(SS * 0.80)
# 핀 머리(원)
d.ellipse([cx - head_r, head_cy - head_r, cx + head_r, head_cy + head_r], fill=WHITE)
# 핀 꼬리(삼각형) — 원 좌우 접점에서 아래 꼭짓점으로
import math
ang = math.radians(48)
lx = cx - int(head_r * math.sin(ang)); ly = head_cy + int(head_r * math.cos(ang))
rx = cx + int(head_r * math.sin(ang)); ry = head_cy + int(head_r * math.cos(ang))
d.polygon([(lx, ly), (rx, ry), (cx, tip_y)], fill=WHITE)

# 3) 핀 가운데 구멍(포인트색)
hole_r = int(head_r * 0.42)
d.ellipse([cx - hole_r, head_cy - hole_r, cx + hole_r, head_cy + hole_r], fill=ORANGE)

# 축소(안티앨리어싱)
img = img.resize((S, S), Image.LANCZOS)
img.save("favicon.png")

# 멀티사이즈 .ico 도 함께 (탭/북마크 호환성)
img.save("favicon.ico", sizes=[(16,16),(32,32),(48,48),(64,64),(128,128)])
print("favicon.png / favicon.ico 생성 완료")
