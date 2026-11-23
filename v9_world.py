"""v9 월드 모듈
 - 고대 기계 문명 컨셉의 지형 장식(오벨리스크·톱니 기념비·기둥열·석상·가로등·결정·잔해)
 - 중앙 사원 정면(파사드)과 계단, 닫힌 기계 문, 보스방으로 이어지는 전송문
 - 지역별 조명(밤 지역은 어둡고 빛나는 것만 밝다)·색조·환경 입자
 - 드랍 픽업(코인·재료·회복 구슬이 날아와 빨려든다), 안개가 걷히는 지도 데이터"""
import math
import random

import pygame

D = pygame.draw
G = C = None
SC = pygame.SRCALPHA
AMBIENT = {0: (0, 0, 0, 0), 1: (255, 150, 70, 34), 2: (12, 12, 50, 150), 3: (110, 160, 255, 30), 4: (0, 0, 0, 0),
           5: (150, 70, 120, 52), 6: (60, 24, 60, 80), 7: (4, 28, 16, 100), 8: (8, 6, 36, 125), 9: (6, 4, 22, 135)}
THEME = dict(field=[("gear", 6, True), ("flower", 46, False)],
             west=[("pillar", 44, True), ("husk", 16, False), ("gear", 6, True)],
             east=[("crystal", 26, True), ("flower", 70, False), ("husk", 8, False)],
             north=[("obelisk", 16, True), ("crystal", 16, True), ("husk", 10, False)],
             temple=[("statue", 10, True), ("obelisk", 8, True), ("husk", 8, False)])
LAMPS = dict(field=8, west=10, east=14, north=10, temple=14)


# ---------------------------------------------------------------- 장식 스프라이트
def _spr(w, h, fn):
    s = pygame.Surface((w, h), SC)
    fn(s)
    return s


def _obelisk(s):
    D.polygon(s, (90, 92, 120), [(3, 31), (5, 6), (8, 0), (11, 6), (13, 31)])
    D.polygon(s, (130, 134, 168), [(8, 0), (11, 6), (13, 31), (8, 31)])
    s.fill((60, 64, 90), (2, 28, 12, 4))
    for y in (10, 16, 22):
        s.fill((120, 232, 232), (7, y, 2, 3))


def _statue(s):
    s.fill((120, 118, 140), (3, 26, 10, 5))
    s.fill((150, 148, 170), (4, 12, 8, 14))
    D.circle(s, (160, 158, 180), (8, 8), 5)
    s.fill((150, 148, 170), (1, 14, 3, 8))
    s.fill((150, 148, 170), (12, 12, 3, 10))
    s.fill((214, 170, 86), (6, 6, 4, 1))
    s.fill((120, 232, 232), (7, 17, 2, 3))


def _gear(s):
    c = (150, 154, 176)
    for i in range(8):
        a = i * 0.785
        D.circle(s, c, (11 + int(math.cos(a) * 10), 11 + int(math.sin(a) * 10)), 2)
    D.circle(s, (104, 108, 132), (11, 11), 9)
    D.circle(s, c, (11, 11), 8)
    D.circle(s, (70, 74, 100), (11, 11), 3)
    D.circle(s, (120, 232, 232), (11, 11), 1)


def _lamp(s):
    s.fill((70, 66, 90), (4, 8, 2, 14))
    s.fill((60, 56, 80), (2, 21, 6, 3))
    D.rect(s, (214, 170, 86), (1, 2, 8, 7), 1)
    s.fill((255, 226, 140), (2, 3, 6, 5))


def _crystal(s):
    D.polygon(s, (90, 150, 230), [(2, 22), (4, 8), (7, 2), (10, 8), (13, 22)])
    D.polygon(s, (150, 210, 255), [(7, 2), (10, 8), (13, 22), (7, 22)])
    s.fill((255, 255, 255), (6, 6, 1, 4))
    s.fill((70, 70, 104), (1, 21, 14, 3))


def _husk(s):
    s.fill((96, 100, 124), (1, 4, 12, 6))
    s.fill((130, 134, 160), (1, 4, 12, 1))
    D.circle(s, (70, 74, 100), (11, 5), 3)
    s.fill((200, 70, 70), (11, 4, 1, 1))
    s.fill((60, 64, 90), (3, 10, 2, 3))
    s.fill((150, 154, 176), (6, 1, 3, 3))


def _pillar(s):
    s.fill((150, 144, 168), (3, 6, 10, 20))
    s.fill((190, 184, 206), (3, 6, 3, 20))
    s.fill((110, 104, 128), (10, 6, 3, 20))
    s.fill((190, 184, 206), (2, 3, 12, 4))
    s.fill((120, 114, 138), (2, 25, 12, 4))
    D.polygon(s, (0, 0, 0, 0), [(3, 2), (8, 6), (3, 8)])
    s.fill((120, 232, 232), (7, 13, 2, 4))


SPRITES = dict(obelisk=(16, 32, _obelisk), statue=(16, 32, _statue), gear=(22, 22, _gear), lamp=(10, 24, _lamp),
               crystal=(16, 24, _crystal), husk=(14, 14, _husk), pillar=(16, 30, _pillar))
_SPC = {}
LIGHT_COL = dict(lamp=((255, 210, 120), 38), crystal=((120, 190, 255), 34), obelisk=((120, 232, 232), 26),
                 statue=((120, 232, 232), 20), flower=((190, 140, 255), 14))


def sprite(k):
    if k not in _SPC:
        w, h, fn = SPRITES[k]
        _SPC[k] = _spr(w, h, fn)
    return _SPC[k]


def make_facade():
    """중앙 사원 정면 (13x12 타일). 문은 따로 움직이게 그리므로 문틀만 새겨 둔다."""
    s = pygame.Surface((208, 192), SC)
    st, dk, lt, gd = (150, 142, 168), (98, 90, 118), (204, 196, 220), (214, 170, 86)
    for x0 in (0, 180):                                         # 양옆 탑
        D.rect(s, dk, (x0, 36, 28, 156))
        D.rect(s, st, (x0 + 2, 38, 24, 152))
        for i in range(0, 28, 7):
            s.fill(lt, (x0 + i, 30, 5, 7))
        for y in range(46, 190, 12):
            s.fill(dk, (x0 + 2, y, 24, 1))
        D.rect(s, gd, (x0 + 8, 74, 12, 18), 1)
    D.polygon(s, dk, [(20, 56), (104, 4), (188, 56)])
    D.polygon(s, st, [(30, 54), (104, 10), (178, 54)])
    D.polygon(s, lt, [(20, 56), (104, 4), (188, 56)], 2)
    D.rect(s, lt, (20, 54, 168, 7))
    D.rect(s, dk, (20, 60, 168, 3))
    D.rect(s, st, (28, 63, 152, 129))
    for y in range(68, 190, 12):
        s.fill(dk, (28, y, 152, 1))
    for x in (40, 64, 130, 154):                                # 기둥
        D.rect(s, lt, (x - 2, 64, 16, 5))
        D.rect(s, (190, 184, 206), (x, 69, 12, 100))
        s.fill((120, 114, 138), (x + 8, 69, 4, 100))
        for fx in (x + 3, x + 6):
            s.fill((150, 144, 168), (fx, 72, 1, 94))
        D.rect(s, lt, (x - 2, 168, 16, 6))
    D.rect(s, gd, (76, 108, 56, 84), 2)                         # 문틀
    D.circle(s, gd, (104, 112), 28, 2)
    D.rect(s, (18, 14, 34), (80, 112, 48, 80))
    D.circle(s, (18, 14, 34), (104, 112), 24)
    D.rect(s, lt, (0, 176, 208, 8))                             # 계단
    D.rect(s, dk, (0, 184, 208, 8))
    for x in range(0, 208, 16):
        s.fill(st, (x, 177, 2, 6))
    return s


_FAC = {}


def draw_facade(surf, g, cx, cy):
    ox, oy = 24 * G.T - cx, 14 * G.T - cy
    if "f" not in _FAC:
        _FAC["f"] = make_facade()
    surf.blit(_FAC["f"], (ox, oy))
    t = g["t"]
    gx, gy = ox + 104, oy + 34                                  # 돌아가는 톱니 문장
    D.circle(surf, (214, 170, 86), (gx, gy), 17)
    D.circle(surf, (96, 70, 40), (gx, gy), 13)
    for i in range(12):
        a = t * 0.6 + i * 0.5236
        D.circle(surf, (250, 226, 150), (gx + int(math.cos(a) * 18), gy + int(math.sin(a) * 18)), 2)
    D.circle(surf, (120, 232, 232), (gx, gy), 6, 1)
    D.circle(surf, (255, 255, 255), (gx, gy), 2)
    for i in range(14):                                         # 처마의 룬
        rc = G.lerp_c((60, 150, 160), (150, 255, 255), 0.5 + 0.5 * math.sin(t * 3 + i))
        s2 = ox + 26 + i * 11
        surf.fill(rc, (s2, oy + 57, 5, 2))
    for bx in (ox + 14, ox + 194):                              # 탑 위 화로
        fl = int(math.sin(t * 12 + bx) * 2)
        D.circle(surf, (255, 120, 50), (bx, oy + 24), 6 + fl)
        D.circle(surf, (255, 210, 100), (bx, oy + 24), 3)
    dx0, dy0 = ox + 80, oy + 112
    if g["topen"]:                                              # 열린 문: 안쪽에서 새어 나오는 빛
        for i in range(6):
            c = G.lerp_c((18, 14, 34), (210, 180, 255), i / 5 * 0.8)
            D.rect(surf, c, (dx0 + 4 + i * 2, dy0 + 6 + i * 3, 40 - i * 4, 74 - i * 3), 1)
    else:                                                       # 닫힌 문: 톱니가 새겨진 황동 문
        D.rect(surf, (120, 90, 50), (dx0, dy0, 48, 80))
        D.rect(surf, (214, 170, 86), (dx0, dy0, 48, 80), 2)
        D.line(surf, (70, 50, 30), (dx0 + 24, dy0), (dx0 + 24, dy0 + 80), 2)
        for gy2 in (dy0 + 22, dy0 + 52):
            for sx in (dx0 + 12, dx0 + 36):
                D.circle(surf, (250, 226, 150), (sx, gy2), 6, 1)
                D.circle(surf, (250, 226, 150), (sx, gy2), 2)
        for i in range(3):                                      # 열쇠 조각 칸
            col = (120, 232, 232) if i < g["keys"] else (50, 54, 80)
            D.polygon(surf, col, [(dx0 + 14 + i * 10, dy0 - 8), (dx0 + 18 + i * 10, dy0 - 4),
                                  (dx0 + 14 + i * 10, dy0), (dx0 + 10 + i * 10, dy0 - 4)])
    for i in range(10):                                         # 문 앞 룬 카펫
        ry = oy + 192 + i * 16
        c = G.lerp_c((40, 60, 90), (120, 232, 232), 0.35 + 0.35 * math.sin(t * 2 + i * 0.7))
        D.rect(surf, c, (ox + 80, ry, 48, 14), 1)
        surf.fill(c, (ox + 102, ry + 4, 4, 6))


def zone_deco(zid, z):
    """지형 장식 배치. 길·출구·퍼즐·NPC 근처는 비워 둔다."""
    rng = random.Random(sum(ord(c) for c in zid) * 13 + 5)
    ter, solid, wt, ht = z["ter"], z["solid"], z["wt"], z["ht"]
    near = [(tx, ty) for _, tx, ty in z["npcs"]] + [tuple(e["at"]) for e in z["exits"]]
    near += [(int(p["x"]) // G.T, int(p["y"]) // G.T) for p in z["portals"]]
    for pz in z["pz"]:
        near += [(int(s["x"]) // G.T, int(s["y"]) // G.T) for s in pz["sw"]]
    sp = G.ZONES[zid]
    rects = [z["vil"]] if z["vil"] else []
    if sp.get("temple"):
        x0, y0, x1, y1 = sp["temple"]
        rects.append((x0 - 4, y0 - 3, x1 + 4, y1 + 12))
    if sp.get("lair"):
        x0, y0, x1, y1 = sp["lair"][:4]
        rects.append((x0 - 3, y0 - 3, x1 + 3, y1 + 3))
    taken = set()

    def ok(x, y, sol):
        if not (3 <= x < wt - 3 and 3 <= y < ht - 3) or ter[y][x] not in (0, 4) or (x, y) in solid or (x, y) in taken:
            return False
        if any(G.inrect(x, y, r) for r in rects) or any(abs(x - a) < 3 and abs(y - b) < 3 for a, b in near):
            return False
        if sol and any(0 <= y + j < ht and 0 <= x + i < wt and (ter[y + j][x + i] in (3, 7) or (x + i, y + j) in solid)
                       for i in (-1, 0, 1) for j in (-1, 0, 1)):
            return False
        return True
    out = []

    def put(kind, x, y, sol):
        taken.add((x, y))
        out.append((kind, x * G.T + 8, y * G.T + 8, sol))
        if sol:
            solid.add((x, y))
            z["ntile"].add((x, y))
    for kind, n, sol in THEME.get(zid, []):
        cnt, tries = 0, 0
        while cnt < n and tries < n * 40:
            tries += 1
            x, y = rng.randint(3, wt - 4), rng.randint(3, ht - 4)
            if ok(x, y, sol):
                put(kind, x, y, sol)
                cnt += 1
    cnt, tries = 0, 0
    while cnt < LAMPS.get(zid, 0) and tries < 600:             # 가로등: 길가에 놓는다
        tries += 1
        x, y = rng.randint(3, wt - 4), rng.randint(3, ht - 4)
        if ter[y][x] in (0, 4) and any(0 <= y + j < ht and 0 <= x + i < wt and ter[y + j][x + i] == 3
                                       for i in (-2, 2, 0) for j in (-2, 2, 0)) and ok(x, y, False):
            put("lamp", x, y, True)
            cnt += 1
    if z["vil"]:                                                # 마을 광장 가로등
        x0, y0, x1, y1 = z["vil"]
        for x, y in ((x0 + 2, y0 + 2), (x1 - 2, y0 + 2), (x0 + 2, y1 - 2), (x1 - 2, y1 - 2), (39, y0 + 7), (41, y0 + 7)):
            if (x, y) not in solid and (x, y) not in near:
                put("lamp", x, y, True)
    if zid == "west":                                           # 노을 회랑: 길을 따라 늘어선 열주
        roads = [(x, y) for y in range(ht) for x in range(wt) if ter[y][x] == 3]
        for i in range(0, len(roads), 9):
            x, y = roads[i]
            for dx, dy in ((0, -3), (0, 3), (-3, 0), (3, 0)):
                if ok(x + dx, y + dy, True):
                    put("pillar", x + dx, y + dy, True)
    z["deco"] = list(z.get("deco") or []) + out


def decorate(zid, z):
    zone_deco(zid, z)
    if zid != "temple":
        return
    x0, y0, x1, y1 = G.ZONES["temple"]["temple"]               # 사원: 안쪽은 막고 문에서 이어지는 통로와 전송문만 남긴다
    z["solid"] |= {(x, y) for x in range(x0 + 1, x1) for y in range(y0 + 1, y1)}
    z["solid"] -= {(x, y) for x in range(29, 32) for y in range(21, 25)}
    z["core"] = None
    z["portals"].append(dict(x=30 * G.T + 8, y=22 * G.T + 8, to="boss_f", at=(17, 26), boss=True))
    for tx, ty in ((26, 27), (34, 27), (26, 31), (34, 31)):
        if (tx, ty) not in z["solid"]:
            z["solid"].add((tx, ty))
            z["ntile"].add((tx, ty))
            z["deco"].append(("statue", tx * G.T + 8, ty * G.T + 8, True))
    for tx, ty in ((28, 27), (32, 27), (28, 33), (32, 33)):
        z["solid"].add((tx, ty))
        z["ntile"].add((tx, ty))
        z["deco"].append(("lamp", tx * G.T + 8, ty * G.T + 8, True))


# ---------------------------------------------------------------- 그리기 훅
def draw_deco(surf, g, cx, cy):
    rect = pygame.Rect(-30, -40, G.W + 60, G.H + 80)
    t = g["t"]
    for d in g["deco"]:
        if d[0] in ("brazier", "vine", "socket"):
            continue
        k, x, y = d[0], int(d[1]) - cx, int(d[2]) - cy
        if not rect.collidepoint(x, y):
            continue
        if k == "flower":                                       # 밤에는 은은하게 빛나는 꽃
            glow = g["zreg"] in (2, 7)
            for i, (ox, oy) in enumerate(((-3, 2), (2, -1), (4, 3))):
                c = G.lerp_c((120, 90, 200), (220, 170, 255), 0.5 + 0.5 * math.sin(t * 2 + x + i)) if glow else \
                    ((250, 240, 150), (250, 150, 190), (255, 255, 255))[(i + int(d[1])) % 3]
                surf.fill((70, 150, 90), (x + ox, y + oy + 1, 1, 3))
                surf.fill(c, (x + ox - 1, y + oy - 1, 3, 3))
            continue
        spr = sprite(k)
        surf.blit(G.SHADOW, (x - 6, y + 4))
        surf.blit(spr, (x - spr.get_width() // 2, y + 8 - spr.get_height()))
        if k == "crystal":
            surf.fill(G.lerp_c((150, 210, 255), (255, 255, 255), 0.5 + 0.5 * math.sin(t * 3 + x)), (x - 1, y - 8, 2, 2))
        elif k == "lamp":
            surf.fill((255, 244, 190), (x - 2, y - 11, 4, 3))


def draw_pk(surf, g, cx, cy):
    for p in g["pk"]:
        x, y = int(p[0]) - cx, int(p[1]) - cy - int(abs(math.sin(p[7] * 6)) * 3 if p[6] < 0.5 else 0)
        k = p[4]
        if k == "gold":
            w = max(1, int(abs(math.cos(p[7] * 7)) * 4))
            surf.fill((170, 110, 30), (x - w // 2 - 1, y - 2, w + 2, 5))
            surf.fill((255, 214, 80), (x - w // 2, y - 1, w, 3))
        elif k == "heart":
            surf.blit(G.icon("heart", 1), (x - 4, y - 5))
        else:
            surf.blit(G.icon("part", 1), (x - 4, y - 4))


def draw_arena_hook(old):
    def f(surf, g, cx, cy):
        old(surf, g, cx, cy)
        if g["arena"] == "final":
            V["boss"].draw_final_floor(surf, g, cx, cy)
        if g["zid"] == "temple":
            draw_facade(surf, g, cx, cy)
        draw_deco(surf, g, cx, cy)
        draw_pk(surf, g, cx, cy)
        V["boss"].draw_hz(surf, g, cx, cy)
    return f


# ---------------------------------------------------------------- 조명 / 환경 입자
_HOLE = {}
_WHITE = {}

def _radial(r, rgb):
    """r 반경 원형 그라데이션. rgb는 모든 픽셀의 색, 알파만 중심→가장자리로 줄어든다."""
    n = 128
    b = pygame.Surface((n, n), SC)
    for y in range(n):
        for x in range(n):
            d = math.hypot(x - 63.5, y - 63.5) / 64
            a = int(255 * max(0.0, 1 - d) ** 1.4) if d < 1 else 0
            b.set_at((x, y), rgb + (a,))
    return b if r == 64 else pygame.transform.smoothscale(b, (r * 2, r * 2))

def hole(r):
    """어둠을 뚫는 마스크: RGB=0 이라 SUB 해도 알파만 줄어든다 (사각형 흔적 없음)"""
    if r not in _HOLE:
        _HOLE[r] = _radial(r, (0, 0, 0))
    return _HOLE[r]


def glow(r, col, a):
    key = (r, col, a)
    if key not in _WHITE:
        s = _radial(r, (255, 255, 255))
        s.fill(col + (a,), special_flags=pygame.BLEND_RGBA_MULT)
        _WHITE[key] = s
    return _WHITE[key]


def lights(g, cx, cy):
    L = [(g["x"], g["y"], 58, (255, 220, 160))]
    for b in g["booms"]:
        L.append((b["x"], b["y"], 24, (255, 220, 110)))
    for d in g["deco"]:
        if d[0] in LIGHT_COL and (d[0] != "flower" or g["zreg"] in (2, 7)):
            L.append((d[1], d[2] - 8, LIGHT_COL[d[0]][1], LIGHT_COL[d[0]][0]))
        elif d[0] == "brazier":
            L.append((d[1] * G.T + 8, d[2] * G.T, 50, (255, 160, 80)))
        elif d[0] == "socket":
            L.append((d[1] * G.T + 8, d[2] * G.T + 8, 28, (120, 232, 232)))
    for p in g["portals"]:
        L.append((p["x"], p["y"], 40, (255, 120, 100) if p.get("boss") else (120, 210, 255)))
    for z in g["pz"]:
        for s in z["sw"]:
            L.append((s["x"], s["y"], 34, (250, 220, 110) if s["on"] else (120, 170, 230)))
    for e in g["en"]:
        if e["kind"] in ("mid", "final"):
            L.append((e["x"], e["y"], 56, (255, 140, 120)))
        elif e["kind"] == "pylon":
            L.append((e["x"], e["y"], 30, (120, 232, 232)))
    for s in g["shots"][:40]:
        L.append((s[0], s[1], 12, (255, 150, 110)))
    for h in g["hz"]:
        if h["kind"] == "well":
            L.append((h["x"], h["y"], 40, (180, 130, 255)))
    return [(x - cx, y - cy, r, c) for x, y, r, c in L if -70 < x - cx < G.W + 70 and -70 < y - cy < G.H + 70][:70]


def lighting(surf, g, cx, cy):
    if not C.FX["lighting"]:
        return
    r, gg, b, a = AMBIENT.get(g["reg"], (0, 0, 0, 0))
    e = next((o for o in g["en"] if o["kind"] == "final"), None)
    if e and e["phase"] >= 4:
        r, gg, b, a = 40, 6, 10, 120
    if a <= 0:
        return
    if a < 70:                                                  # 낮 시간대: 가벼운 색조만 입힌다
        v = pygame.Surface((G.W, G.H))
        v.fill((r, gg, b))
        v.set_alpha(a)
        surf.blit(v, (0, 0))
        return
    dark = pygame.Surface((G.W, G.H), SC)
    dark.fill((r, gg, b, a))
    Ls = lights(g, cx, cy)
    for x, y, rad, c in Ls:
        dark.blit(hole(rad), (int(x) - rad, int(y) - rad), special_flags=pygame.BLEND_RGBA_SUB)
    surf.blit(dark, (0, 0))
    for x, y, rad, c in Ls:
        surf.blit(glow(rad, c, 70), (int(x) - rad, int(y) - rad))


AMB_KIND = {0: ((250, 200, 220), 0.4, 6, -4), 1: ((255, 160, 80), -0.9, 8, -10), 2: ((220, 255, 130), 0.2, 4, -3),
            3: ((230, 245, 255), 0.5, 10, 8), 5: ((255, 220, 140), -0.3, 6, -5), 6: ((255, 170, 90), -0.8, 6, -8),
            7: ((150, 255, 170), 0.2, 4, -3), 8: ((190, 170, 255), -0.2, 5, -4), 9: ((120, 232, 232), -0.4, 6, -6)}


def ambient_update(g, dt):
    if not C.FX["ambient"]:
        return
    cx, cy = G.camera(g)
    k = AMB_KIND.get(g["reg"])
    if not k:
        return
    if len(g["amb"]) < 30 and random.random() < 0.5:
        g["amb"].append([cx + random.random() * G.W, cy + random.random() * G.H, random.uniform(-6, 6) + k[3],
                         random.uniform(-6, 6) + k[2] * k[1], random.uniform(2.5, 5.0), random.random() * 6.283])
    for p in g["amb"]:
        p[0] += p[2] * dt
        p[1] += p[3] * dt
        p[4] -= dt
        p[5] += dt * 2
    g["amb"] = [p for p in g["amb"] if p[4] > 0 and cx - 20 < p[0] < cx + G.W + 20 and cy - 20 < p[1] < cy + G.H + 20]


def ambient_draw(surf, g, cx, cy):
    k = AMB_KIND.get(g["reg"])
    if not k or not C.FX["ambient"]:
        return
    for p in g["amb"]:
        a = min(1.0, p[4])
        if g["reg"] in (2, 7):                                  # 반딧불은 깜빡인다
            a *= 0.5 + 0.5 * math.sin(p[5] * 2)
        c = G.lerp_c((0, 0, 0), k[0], max(0.0, a))
        surf.fill(c, (int(p[0]) - cx, int(p[1]) - cy, 2, 2))


# ---------------------------------------------------------------- 드랍 픽업
def spawn_loot(g, x, y, gold=0, parts=0, heart=False):
    coins = min(7, max(1, gold // 3)) if gold else 0
    left = gold
    for i in range(coins):
        v = left // (coins - i)
        left -= v
        g["pk"].append([x, y, random.uniform(-45, 45), random.uniform(-70, -20), "gold", v, 0.0, random.random() * 5])
    for _ in range(parts):
        g["pk"].append([x, y, random.uniform(-45, 45), random.uniform(-70, -20), "part", 1, 0.0, random.random() * 5])
    if heart:
        g["pk"].append([x, y, random.uniform(-30, 30), random.uniform(-60, -30), "heart", 1, 0.0, random.random() * 5])


def update_pk(g, dt):
    mag = C.FX["coin_magnet"]
    for p in g["pk"][:]:
        p[6] += dt
        p[7] += dt
        d = G.dist(p[0], p[1], g["x"], g["y"])
        if p[6] > 0.35 and d < mag:
            sp = 150 + (mag - d) * 3
            p[2], p[3] = (g["x"] - p[0]) / (d or 1) * sp, (g["y"] - p[1]) / (d or 1) * sp
        else:
            p[2] *= 0.94
            p[3] = p[3] * 0.94 + 90 * dt * (1 if p[6] < 0.5 else 0)
        p[0] += p[2] * dt
        p[1] += p[3] * dt
        if p[6] > 0.2 and d < 8:
            k = p[4]
            g["pk"].remove(p)
            if k == "gold":
                g["inv"]["gold"] += p[5]
                g["acc"][0] += p[5]
                g["acc"][1] = 0.5
                G.play("pickup")
            elif k == "part":
                g["inv"]["part"] += 1
                G.ftext(g, "+1 부품", g["x"], g["y"] - 12, (200, 220, 255))
                G.play("pickup")
            elif g["hp"] < g["mhp"]:
                g["hp"] += 1
                G.ftext(g, "+1 HP", g["x"], g["y"] - 12, (255, 140, 140))
                G.play("potion")
            else:
                g["inv"]["potion"] = min(9, g["inv"]["potion"] + (1 if random.random() < 0.3 else 0))
    if g["acc"][0]:
        g["acc"][1] -= dt
        if g["acc"][1] <= 0:
            G.ftext(g, f"+{g['acc'][0]}G", g["x"], g["y"] - 14, (255, 230, 120))
            g["acc"][0] = 0


# ---------------------------------------------------------------- 지도 데이터 (안개)
def mm_base(g):
    zid = g["zid"]
    if zid in g["mm"]:
        return g["mm"][zid]
    wt, ht = g["wt"], g["ht"]
    s = pygame.Surface((wt, ht))
    reg = G.REGIONS[g["zreg"]]
    node_c = dict(tree=(44, 110, 66), rock=(140, 142, 156), ore=(80, 90, 150), herb=(70, 170, 90))
    ntile = {(n["tx"], n["ty"]): n["kind"] for n in g["nodes"]}
    for y in range(ht):
        for x in range(wt):
            t = g["ter"][y][x]
            if (x, y) in g["houses"]:
                c = (190, 80, 70)
            elif (x, y) in g["water"]:
                c = (70, 134, 204)
            elif (x, y) in ntile:
                c = node_c[ntile[(x, y)]]
            elif (x, y) in g["solid"]:
                c = G.adj(reg["wall"], -20)
            elif g["vil"] and G.inrect(x, y, g["vil"]):
                c = (214, 196, 150)
            else:
                c = {3: (196, 166, 118), 2: (232, 220, 176), 4: (186, 182, 198), 5: (36, 80, 52), 7: (156, 112, 74)}.get(t, reg["floor"])
            s.set_at((x, y), c)
    fog = pygame.Surface((wt, ht), SC)
    fog.fill((10, 10, 24, 255))
    g["mm"][zid] = (s, fog, set())
    return g["mm"][zid]


def reveal(g):
    s, fog, seen = mm_base(g)
    tx, ty = int(g["x"]) // G.T, int(g["y"]) // G.T
    if g.get("_rv") == (g["zid"], tx, ty):
        return
    g["_rv"] = (g["zid"], tx, ty)
    R = 10
    for y in range(max(0, ty - R), min(g["ht"], ty + R + 1)):
        for x in range(max(0, tx - R), min(g["wt"], tx + R + 1)):
            if (x - tx) ** 2 + (y - ty) ** 2 <= R * R and (x, y) not in seen:
                seen.add((x, y))
                fog.set_at((x, y), (0, 0, 0, 0))


# ---------------------------------------------------------------- 설치
V = {}


def install(g_mod, cfg, boss_mod):
    global G, C
    G, C = g_mod, cfg
    V["boss"] = boss_mod
    E, EC = cfg.ENEMY, cfg.ECONOMY
    G.FOE_HP.update(E["hp"])
    G.EXP.update(E["exp"])
    for k in E["hp"]:
        G.DROP[k] = (E["gold"][k], E["part_chance"][k])
    G.CART_PRICE, G.ENH_MAX, G.ENH_RATE, G.LV_MAX = EC["cart_price"], EC["enh_max"], tuple(EC["enh_rate"]), EC["level_max"]
    G.MAXD = cfg.PLAYER["boom_range"]
    G.SELL = tuple(EC["sell_price"].items())
    old_new, old_load, old_zone, old_arena = G.new_state, G.load_zone, G.build_zone, G.draw_arena
    old_draw, old_update, old_hurt, old_sw, old_clear = G.draw, G.update, G.hurt, G.hit_switch, G.clear_arena
    old_track, old_pot = G.make_track, G.shop_items

    def init_keys(g):
        for k, v in (("hz", []), ("pk", []), ("amb", []), ("mm", {}), ("solved", set()), ("hurt_t", 0.0),
                     ("acc", [0, 0.0]), ("pm", 0), ("autosave_ok", False)):
            g.setdefault(k, v)

    def new_state():
        g = old_new()
        init_keys(g)
        sh = cfg.PLAYER["start_hp"]
        if g["lvl"] == 1 and g["mhp"] != sh and not g["lv"]["hp"]:
            g["mhp"] = g["hp"] = sh
        return g

    def load_zone(g, zid, tx, ty):
        init_keys(g)
        old_load(g, zid, tx, ty)
        g.update(hz=[], pk=[], amb=[])
        for z in g["pz"]:                                       # 저장된 퍼즐 해결 상태 복원
            if zid in g["solved"] and not z["done"]:
                z["done"] = True
                for s in z["sw"]:
                    s["on"] = True
                g["solid"] -= z["gate"]
        if g["arena"] and zid in g["cleared"]:                  # 이미 깬 보스방은 보스 없이 열어 둔다
            g["en"] = [e for e in g["en"] if e["kind"] not in ("mid", "final")]
            if not g["portals"] and G.ZONES[zid].get("origin"):
                g["lock"] = False
                x0, y0, x1, y1 = G.ZONES[G.ZONES[zid]["origin"]]["lair"][:4]
                g["portals"].append(dict(x=17 * G.T + 8, y=11 * G.T + 8, to=G.ZONES[zid]["origin"],
                                         at=((x0 + x1) // 2, (y0 + y1) // 2 + 2), boss=False))
        reveal(g)
        if zid == "field" and cfg.FX["autosave"] and g["autosave_ok"] and g["mode"] == "play" and V.get("save"):
            V["save"](g, quiet=True)

    def build_zone(zid):
        z = old_zone(zid)
        if not G.ZONES[zid].get("arena"):
            try:
                decorate(zid, z)
            except Exception:
                G.v9_log("decorate")
        return z

    def draw(surf, g):
        old_draw(surf, g)
        cx, cy = G.camera(g)
        try:
            lighting(surf, g, cx, cy)
            ambient_draw(surf, g, cx, cy)
        except Exception:
            G.v9_log("lighting")

    def update(g, inp, dt):
        old_update(g, inp, dt)
        if g["mode"] != "play" or g["tr"]:
            return
        try:
            g["hurt_t"] = max(0.0, g["hurt_t"] - dt)
            V["boss"].update_hz(g, dt)
            update_pk(g, dt)
            ambient_update(g, dt)
            reveal(g)
        except Exception:
            G.v9_log("ext-update")

    def hurt(g, n=1):
        old_hurt(g, n)
        g["hurt_t"] = 0.45
        if cfg.FX["screen_shake"]:
            g["shake"] = max(g["shake"], 0.2)

    def hit_switch(g, z, s):
        old_sw(g, z, s)
        if z["done"]:
            g["solved"].add(g["zid"])

    def clear_arena(g):
        old_clear(g)
        g["hz"] = []
        if cfg.FX["autosave"] and V.get("save"):
            V["save"](g, quiet=True)

    def make_track(reg):
        return old_track(reg if reg < 9 else 5)

    def kill(g, e):
        k = e["kind"]
        G.spark(g, e["x"], e["y"], (160, 230, 160) if k in ("illu", "seed") else (235, 70, 70), 10)
        if k in ("illu", "seed"):
            G.play("hit")
            return
        if k == "pylon":
            G.play("boom")
            g["rings"].append([e["x"], e["y"], 0.0, 40, (120, 232, 232)])
            return
        if k == "final":
            F = cfg.FINAL_BOSS
            g.update(mode="ending", en=[], shots=[], hz=[], met=[], pk=[])
            g["shake"] = 1.0
            g["rings"].append([e["x"], e["y"], 0.0, 200, (255, 240, 180)])
            G.spark(g, e["x"], e["y"], (255, 240, 180), 40)
            g["inv"]["gold"] += F["gold"]
            G.gain_exp(g, F["exp"], e["x"], e["y"] - 24)
            G.play("boss")
            if cfg.FX["autosave"] and V.get("save"):
                V["save"](g, quiet=True)
            return
        if k in G.DROP and e["hx"] is not None:
            g["rs"].append([E["respawn_sec"], e["hx"], e["hy"], k])
        if e.get("nodrop"):
            return
        G.play("kill")
        heart = random.random() < E["heart_chance"]
        if k in G.DROP:
            (lo, hi), pc = G.DROP[k]
            spawn_loot(g, e["x"], e["y"], random.randint(lo, hi), 1 if random.random() < pc else 0, heart)
        else:
            spawn_loot(g, e["x"], e["y"], M["gold"], M["parts"], True)
            g["keys"] += 1
            G.toast(g, f"열쇠 조각 획득! ({g['keys']}/3)")
            G.play("up")
            if g["spec"].get("arena"):
                G.clear_arena(g)
        G.gain_exp(g, M["exp"] if k not in G.DROP else G.EXP.get(k, 0), e["x"], e["y"] - 24)

    M = cfg.MID_BOSS
    G.new_state, G.load_zone, G.build_zone, G.draw, G.update, G.hurt = new_state, load_zone, build_zone, draw, update, hurt
    G.hit_switch, G.clear_arena, G.make_track, G.kill = hit_switch, clear_arena, make_track, kill
    G.draw_arena = draw_arena_hook(old_arena)
    G.spawn_loot, G.mm_base, G.reveal = spawn_loot, mm_base, reveal