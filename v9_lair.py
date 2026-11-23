"""v9 수호 기계의 방 꾸미기 모듈 (v9_lair.py)
 중간보스 3기의 전송문이 있는 '수호 기계의 방'을 중앙 사원처럼 꾸민다.
 - 방 앞 고대 포석 광장 + 입구를 지키는 석상 / 가로등
 - 방 모서리의 황동 탑(불타는 화로), 벽을 두르는 황동 띠와 룬, 입구 양옆 기둥
 - 입구에서 전송문까지 이어지는 룬 카펫(방 밖으로도 이어진다), 전송문 둘레의 마법진
 - 방 안쪽 모서리 석상. 보스마다 포인트 색이 다르고, 수호 기계를 쓰러뜨리면 금빛으로 바뀐다
 - 덤: 나무·바위·광석·약초 그림도 새로 그린다 (topdown_rpg.py 의 draw_node 교체)
v9_open.install 뒤에 설치한다:
    import v9_lair
    v9_lair.install(G, C, v9_world, v9_open)
"""
import math

import pygame

D = pygame.draw
SC = pygame.SRCALPHA
G = C = W = O = None
ST, DK, LT = (150, 142, 168), (98, 90, 118), (204, 196, 220)
GOLD, GOLD_D, GOLD_L = (214, 170, 86), (150, 108, 56), (250, 226, 150)
ACC = {0: (250, 214, 150), 1: (130, 230, 140), 2: (180, 150, 255)}      # 서쪽(눈) / 동쪽(덩굴) / 북쪽(중력)
DONE = (255, 226, 120)
_C = {}


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


# ================================================================= 월드 생성 후처리: 광장 · 석상 · 가로등
def decorate(z):
    T = G.T
    ter, solid, ntile, wt, ht = z["ter"], z["solid"], z["ntile"], z["wt"], z["ht"]
    wtiles = {(w["tx"], w["ty"]) for w in z["warps"]}
    stiles = {(int(s["x"]) // T, int(s["y"]) // T) for q in z["pz"] for s in q["sw"]}
    plaza = set()
    for key, (x0, y0, x1, y1, side, mid) in z["meta"]["lairs"].items():
        mx, my = (x0 + x1) // 2, (y0 + y1) // 2
        d, p, gx, gy = {"e": ((1, 0), (0, 1), x1, my), "w": ((-1, 0), (0, 1), x0, my), "s": ((0, 1), (1, 0), mx, y1)}[side]
        for u in range(1, 10):
            for v in range(-4, 5):
                x, y = gx + d[0] * u + p[0] * v, gy + d[1] * u + p[1] * v
                r = (u / 9.0) ** 2 + (v / 4.5) ** 2
                if r < 1.0 + 0.3 * ((G.hsh(x, y) % 10) / 10 - 0.5) and 3 <= x < wt - 3 and 3 <= y < ht - 3:
                    if ter[y][x] in (0, 2, 3, 5):
                        ter[y][x] = 4
                        plaza.add((x, y))
                    elif ter[y][x] == 4:
                        plaza.add((x, y))
    for nd in z["nodes"]:                                        # 광장 위의 나무·바위는 치운다
        if nd["alive"] and (nd["tx"], nd["ty"]) in plaza:
            nd["alive"], nd["t"] = False, 1e9
            if nd["kind"] != "herb":
                solid.discard((nd["tx"], nd["ty"]))
                ntile.discard((nd["tx"], nd["ty"]))
    keep = []
    for d_ in z["deco"]:
        t = (int(d_[1]) // T, int(d_[2]) // T)
        if t in plaza and d_[0] != "warp":
            if d_[3]:
                solid.discard(t)
                ntile.discard(t)
            continue
        keep.append(d_)
    z["deco"][:] = keep
    z["en"][:] = [e for e in z["en"] if (int(e["x"]) // T, int(e["y"]) // T) not in plaza]

    def place(kind, x, y):
        if not (3 <= x < wt - 3 and 3 <= y < ht - 3) or (x, y) in solid or ter[y][x] in (1, 7, 8):
            return
        if any(abs(x - a) <= 1 and abs(y - b) <= 1 for a, b in wtiles) or any(abs(x - a) <= 2 and abs(y - b) <= 2 for a, b in stiles):
            return
        z["deco"].append((kind, x * T + 8, y * T + 8, True))
        solid.add((x, y))
        ntile.add((x, y))
    for key, (x0, y0, x1, y1, side, mid) in z["meta"]["lairs"].items():
        mx, my = (x0 + x1) // 2, (y0 + y1) // 2
        d, p, gx, gy = {"e": ((1, 0), (0, 1), x1, my), "w": ((-1, 0), (0, 1), x0, my), "s": ((0, 1), (1, 0), mx, y1)}[side]
        for kind, u, v in (("statue", 2, 3), ("statue", 2, -3), ("lamp", 7, 3), ("lamp", 7, -3)):
            place(kind, gx + d[0] * u + p[0] * v, gy + d[1] * u + p[1] * v)
        for x, y in ((x0 + 2, y0 + 2), (x1 - 2, y0 + 2), (x0 + 2, y1 - 2), (x1 - 2, y1 - 2)):
            place("statue", x, y)
    z["_lair"] = True


# ================================================================= 그리기
def tower(acc):
    key = ("tw", acc)
    if key not in _C:
        s = pygame.Surface((24, 34), SC)
        s.fill(DK, (2, 12, 20, 22))
        s.fill(ST, (4, 12, 16, 22))
        s.fill(LT, (4, 12, 3, 22))
        s.fill(DK, (17, 12, 3, 22))
        for y in (18, 24, 30):
            s.fill(DK, (4, y, 16, 1))
        s.fill(GOLD, (2, 14, 20, 2))
        s.fill(GOLD_D, (2, 16, 20, 1))
        s.fill(GOLD, (2, 31, 20, 2))
        s.fill((18, 14, 34), (10, 19, 4, 7))
        s.fill(acc, (10, 21, 4, 3))
        for x, w in ((2, 5), (9, 6), (17, 5)):                   # 성가퀴
            s.fill(LT, (x, 9, w, 4))
            s.fill(ST, (x, 11, w, 2))
        D.polygon(s, DK, [(5, 9), (19, 9), (16, 5), (8, 5)])
        s.fill(GOLD, (5, 8, 14, 2))
        s.fill(DK, (1, 33, 22, 1))
        _C[key] = s
    return _C[key]


def carpet(surf, rect, horiz, t, acc):
    r = pygame.Rect(rect)
    if r.w <= 0 or r.h <= 0:
        return
    surf.fill((46, 38, 88), r)
    if horiz:
        for yy, c in ((r.y, GOLD), (r.bottom - 1, GOLD), (r.y + 2, GOLD_D), (r.bottom - 3, GOLD_D)):
            surf.fill(c, (r.x, yy, r.w, 1))
        for i in range(r.x + 6, r.right - 3, 12):
            c = lerp((60, 54, 110), acc, 0.4 + 0.4 * math.sin(t * 2 + i * 0.2))
            surf.fill(c, (i, r.centery - 1, 3, 3))
            surf.fill(c, (i + 1, r.centery - 2, 1, 5))
    else:
        for xx, c in ((r.x, GOLD), (r.right - 1, GOLD), (r.x + 2, GOLD_D), (r.right - 3, GOLD_D)):
            surf.fill(c, (xx, r.y, 1, r.h))
        for i in range(r.y + 6, r.bottom - 3, 12):
            c = lerp((60, 54, 110), acc, 0.4 + 0.4 * math.sin(t * 2 + i * 0.2))
            surf.fill(c, (r.centerx - 1, i, 3, 3))
            surf.fill(c, (r.centerx - 2, i + 1, 5, 1))


def draw_lairs(surf, g, cx, cy):
    T, t, meta = G.T, g["t"], g.get("meta")
    if not meta:
        return
    solid = g["solid"]
    for key, (x0, y0, x1, y1, side, mid) in meta["lairs"].items():
        if (x1 + 12) * T - cx < 0 or (x0 - 12) * T - cx > G.W or (y1 + 12) * T - cy < 0 or (y0 - 12) * T - cy > G.H:
            continue
        acc = DONE if G.ARENA_OF[mid] in g["cleared"] else ACC[mid]
        mx, my = (x0 + x1) // 2, (y0 + y1) // 2
        pxc, pyc = mx * T + 8 - cx, my * T + 8 - cy
        # ---- 룬 카펫: 입구 바깥 광장에서 전송문까지
        if side == "e":
            carpet(surf, (mx * T + 8 - cx, pyc - 9, (x1 - mx) * T - 8, 18), True, t, acc)
            carpet(surf, ((x1 + 1) * T - cx, pyc - 9, 8 * T, 18), True, t, acc)
            gate = [(x1, my - 1 + i) for i in range(3)]
        elif side == "w":
            carpet(surf, ((x0 + 1) * T - cx, pyc - 9, (mx - x0) * T - 8, 18), True, t, acc)
            carpet(surf, ((x0 - 8) * T - cx, pyc - 9, 8 * T, 18), True, t, acc)
            gate = [(x0, my - 1 + i) for i in range(3)]
        else:
            carpet(surf, (pxc - 9, my * T + 8 - cy, 18, (y1 - my) * T - 8), False, t, acc)
            carpet(surf, (pxc - 9, (y1 + 1) * T - cy, 18, 8 * T), False, t, acc)
            gate = [(mx - 1 + i, y1) for i in range(3)]
        # ---- 전송문 둘레 마법진
        D.circle(surf, (36, 30, 64), (pxc, pyc), 25)
        pulse = 0.5 + 0.5 * math.sin(t * 2.5)
        c1 = lerp((70, 64, 120), acc, 0.4 + 0.4 * pulse)
        D.circle(surf, c1, (pxc, pyc), 25, 1)
        D.circle(surf, c1, (pxc, pyc), 18, 1)
        for i in range(12):
            a = t * 0.5 + i * 0.5236
            surf.fill(acc if i % 3 == 0 else c1, (pxc + int(math.cos(a) * 21), pyc + int(math.sin(a) * 21), 2, 2))
        # ---- 벽: 황동 띠와 룬
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                edge = x in (x0, x1) or y in (y0, y1)
                if not edge or (x, y) not in solid or (x, y) in gate or (x in (x0, x1) and y in (y0, y1)):
                    continue
                px, py = x * T - cx, y * T - cy
                surf.fill(GOLD, (px, py + 2, T, 1))
                surf.fill(GOLD_D, (px, py + 3, T, 1))
                surf.fill(DK, (px, py + 9, T, 1))
                if (x + y) % 3 == 0:
                    c = lerp((60, 54, 110), acc, 0.45 + 0.4 * math.sin(t * 2 + x + y))
                    D.polygon(surf, c, [(px + 8, py + 5), (px + 11, py + 8), (px + 8, py + 11), (px + 5, py + 8)])
        # ---- 입구 양옆 기둥
        gs = sorted(gate)
        a_, b_ = gs[0], gs[-1]
        posts = [(a_[0], a_[1] - 1), (b_[0], b_[1] + 1)] if side in ("e", "w") else [(a_[0] - 1, a_[1]), (b_[0] + 1, b_[1])]
        pil = W.sprite("pillar")
        for x, y in posts:
            surf.blit(pil, (x * T - cx, y * T + 16 - pil.get_height() - cy))
        # ---- 모서리 탑 + 화로 불꽃
        tw = tower(acc)
        for x, y in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
            px, py = x * T - cx, y * T - cy
            surf.blit(tw, (px + 8 - 12, py + 16 - 34))
            fx, fy = px + 8, py - 12
            surf.blit(W.glow(26, (255, 170, 80), 55), (fx - 26, fy - 26))
            fl = int(math.sin(t * 12 + x) * 2)
            D.circle(surf, (255, 120, 50), (fx, fy), 4 + fl)
            D.circle(surf, (255, 205, 100), (fx, fy), 2)
            surf.fill((255, 250, 210), (fx - 1, fy - 1, 2, 2))


def draw_arena_wrap(old):
    def f(surf, g, cx, cy):
        old(surf, g, cx, cy)
        if g.get("zid") == O.WID:
            try:
                draw_lairs(surf, g, cx, cy)
            except Exception:
                G.v9_log("lair-draw")
    return f


# ================================================================= 채집물 그림
_SH = {}


def shadow(w, h):
    if (w, h) not in _SH:
        s = pygame.Surface((w, h), SC)
        D.ellipse(s, (0, 0, 0, 70), (0, 0, w, h))
        _SH[(w, h)] = s
    return _SH[(w, h)]


def draw_node(surf, n, px, py, reg):
    k, h = n["kind"], G.hsh(n["tx"], n["ty"])
    v, tick = h % 3, pygame.time.get_ticks() / 1000.0
    if k == "tree":
        leaf = G.adj(G.REGIONS[reg]["leaf"], (v - 1) * 10)
        surf.blit(shadow(20, 7), (px - 2, py + 10))
        surf.fill((84, 58, 42), (px + 6, py + 8, 4, 7))
        surf.fill((128, 92, 62), (px + 6, py + 8, 1, 7))
        surf.fill((60, 40, 32), (px + 9, py + 9, 1, 6))
        surf.fill((96, 68, 48), (px + 4, py + 13, 8, 2))
        if reg == 3 or (reg == 2 and v == 0):                    # 침엽수
            for i, (top, base, hw) in enumerate(((0, 9, 8), (-4, 5, 7), (-8, 1, 5))):
                col = G.adj(leaf, -30 + i * 14)
                D.polygon(surf, col, [(px + 8, py + top), (px + 8 + hw, py + base), (px + 8 - hw, py + base)])
                D.line(surf, G.adj(col, 32), (px + 8, py + top), (px + 8 - hw, py + base))
                surf.fill(G.adj(col, -28), (px + 8 - hw + 1, py + base, hw * 2 - 1, 1))
        else:                                                    # 활엽수: 잎 덩어리 4겹
            D.circle(surf, G.adj(leaf, -34), (px + 8, py + 5), 8)
            D.circle(surf, G.adj(leaf, -12), (px + 5, py + 3), 5)
            D.circle(surf, G.adj(leaf, -12), (px + 11, py + 3), 5)
            D.circle(surf, leaf, (px + 8, py + 1), 6)
            D.circle(surf, G.adj(leaf, 34), (px + 6, py - 1), 3)
            for i in range(5):
                bx, by = px + 2 + (h >> i) % 12, py - 2 + (h >> (i + 2)) % 9
                surf.fill(G.adj(leaf, 46 if i % 2 else -48), (bx, by, 1, 1))
    elif k == "rock":
        base = (142, 144, 160)
        surf.blit(shadow(18, 6), (px - 1, py + 11))
        D.polygon(surf, G.adj(base, -34), [(px + 1, py + 14), (px + 2, py + 7), (px + 7, py + 3), (px + 13, py + 5), (px + 15, py + 14)])
        D.polygon(surf, base, [(px + 2, py + 13), (px + 3, py + 7), (px + 7, py + 4), (px + 10, py + 5), (px + 9, py + 13)])
        D.polygon(surf, G.adj(base, 40), [(px + 4, py + 7), (px + 7, py + 4), (px + 10, py + 5), (px + 8, py + 8)])
        surf.fill(G.adj(base, 64), (px + 6, py + 5, 2, 1))
        if v != 1:
            surf.fill((96, 150, 82), (px + 3, py + 12, 4, 2))
        surf.fill(G.adj(base, -20), (px + 12, py + 13, 3, 2))
    elif k == "ore":
        base = (80, 84, 112)
        surf.blit(shadow(18, 6), (px - 1, py + 11))
        D.polygon(surf, G.adj(base, -30), [(px + 1, py + 14), (px + 2, py + 7), (px + 7, py + 3), (px + 13, py + 5), (px + 15, py + 14)])
        D.polygon(surf, base, [(px + 2, py + 13), (px + 3, py + 7), (px + 7, py + 4), (px + 10, py + 5), (px + 9, py + 13)])
        for i, (sx, sy, sh) in enumerate(((5, 11, 5), (9, 9, 6), (12, 12, 4))):    # 빛나는 결정
            D.polygon(surf, (70, 170, 200), [(px + sx, py + sy - sh), (px + sx + 2, py + sy - sh + 3), (px + sx + 1, py + sy), (px + sx - 1, py + sy)])
            surf.fill((150, 245, 250), (px + sx, py + sy - sh + 1, 1, sh - 2))
            if int(tick * 2 + h + i * 2) % 6 == 0:
                surf.fill((255, 255, 255), (px + sx, py + sy - sh - 1, 1, 1))
    else:                                                        # 약초
        fc = ((250, 150, 190), (255, 240, 150), (170, 190, 255))[v]
        D.line(surf, (50, 120, 70), (px + 8, py + 13), (px + 8, py + 7))
        D.ellipse(surf, (60, 150, 80), (px + 2, py + 8, 6, 4))
        D.ellipse(surf, (96, 190, 108), (px + 8, py + 7, 6, 4))
        D.ellipse(surf, (80, 170, 96), (px + 5, py + 11, 6, 3))
        D.circle(surf, fc, (px + 8, py + 6), 2)
        surf.fill((255, 230, 100), (px + 8, py + 6, 1, 1))
        if reg == 2:                                             # 밤 정원의 약초는 은은하게 빛난다
            D.circle(surf, G.lerp_c((40, 60, 90), fc, 0.5 + 0.4 * math.sin(tick * 3 + h)), (px + 8, py + 6), 4, 1)


# ================================================================= 설치
def install(g_mod, cfg, world_mod, open_mod):
    global G, C, W, O
    G, C, W, O = g_mod, cfg, world_mod, open_mod
    old_build = G.build_zone

    def build_zone(zid):
        z = old_build(zid)
        if (zid == O.WID or zid in O.LEGACY) and z.get("meta") and not z.get("_lair"):
            try:
                decorate(z)
            except Exception:
                G.v9_log("lair-decorate")
        return z
    G.build_zone = build_zone
    G.draw_arena = draw_arena_wrap(G.draw_arena)
    G.draw_node = draw_node