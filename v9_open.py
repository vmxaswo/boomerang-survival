"""v9 오픈월드 모듈 (v9_open.py)
 - 구역 5개를 이어 붙이지 않고, 월드 전체(기본 160x130 타일)를 하나의 생성기로 한 번에 만든다.
   고도 필드 하나에서 호수·산맥·강이 나오고, 지역은 노이즈로 비틀린 거리로 정해져 경계가 번지듯 바뀐다.
 - 길은 A*로 지형을 따라 휘어 가고, 강을 만나면 다리가 놓이며, 능선은 길이 지나는 고개로 뚫린다.
 - 워프포인트(젤다·원신 방식): E로 활성화 -> M 지도에서 골라 이동
 - 지역별 바닥·벽·나뭇잎 색, 조명, 음악 전환이 경계에서 서서히 바뀐다.
수치는 config.py 의 WORLD 에서 바꾼다. 이 모듈은 install 순서상 가장 마지막에 설치한다."""
import heapq
import json
import math
import os
import random
import threading

import pygame

D = pygame.draw
SC = pygame.SRCALPHA
G = C = W = UI = None
WID = "world"
LEGACY = ("field", "west", "east", "north", "temple")           # 옛 구역 이름으로 오는 이동 요청은 전부 월드로 보낸다
EXTRA = ("style", "regmap", "regw", "warps", "meta")            # 월드 구역 사전에 얹는 추가 키 (ZK 에 등록)
BIOMES = ("field", "west", "east", "temple", "north")
BREG = (0, 1, 2, 5, 3)                                          # 바이옴 -> REGIONS 번호
ANCH = ((0.50, 0.80, 1.10), (0.16, 0.60, 1.00), (0.84, 0.60, 1.00), (0.50, 0.355, 0.85), (0.50, 0.11, 1.00))
WARP_EXTRA = (("황금 언덕", 0.33, 0.70), ("달빛 호숫가", 0.67, 0.70), ("남서 폐허 초소", 0.14, 0.86),
              ("남동 이정표", 0.86, 0.86), ("푸른 옛 터", 0.30, 0.22), ("구름 전망대", 0.72, 0.20))
DEFAULT = dict(width=160, height=130, seed=2026, blend=5.0, warp_cost=0)
_PRE = dict(th=None, z=None)


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def params():
    w = dict(DEFAULT)
    w.update(getattr(C, "WORLD", {}) or {})
    return max(120, int(w["width"])), max(100, int(w["height"])), int(w["seed"]), float(w["blend"])


# ================================================================= 배치 (월드 크기에 비례)
def layout(wt, ht):
    cx = wt // 2
    vcy = int(ht * 0.76)
    vil = (cx - 10, vcy - 6, cx + 9, vcy + 6)                     # 20x13 광장 (안전지대)
    t0 = int(ht * 0.30)
    temple = (cx - 6, t0, cx + 6, t0 + 11)                        # 13x12 중앙 사원
    lw, ly = int(wt * 0.12), int(ht * 0.50)
    ny = int(ht * 0.05) + 1
    # 수호 기계의 방은 모두 문이 남쪽(화면 아래)을 향한다: 쿼터뷰에서 건물 정면이 보이도록 (v9_sites 가 건물로 그린다)
    lairs = dict(west=(lw, ly, lw + 8, ly + 8, "s", 0),
                 east=(wt - 1 - lw - 8, ly, wt - 1 - lw, ly + 8, "s", 1),
                 north=(cx - 4, ny, cx + 4, ny + 8, "s", 2))
    return dict(vil=vil, temple=temple, lairs=lairs)


def front_of(lair):
    x0, y0, x1, y1, side, _ = lair
    mx, my = (x0 + x1) // 2, (y0 + y1) // 2
    return (x1 + 3, my) if side == "e" else (x0 - 3, my) if side == "w" else (mx, y1 + 3)


def warp_list(wt, ht, lay):
    vx0, vy0, _, _ = lay["vil"]
    out = [("home", "마을 광장", (vx0 + 10, vy0 - 3))]
    for key, nm in (("west", "노을빛 회랑 입구"), ("east", "달빛 정원 입구"), ("north", "새벽 유적 입구")):
        x0, y0, x1, y1, side, _ = lay["lairs"][key]
        mx, my = (x0 + x1) // 2, (y0 + y1) // 2
        p = (x1 + 5, my + 3) if side == "e" else (x0 - 5, my + 3) if side == "w" else (mx + 5, y1 + 4)
        out.append((key + "_gate", nm, p))
    tx0, ty0, tx1, ty1 = lay["temple"]
    out.append(("temple", "황혼의 사원 앞", ((tx0 + tx1) // 2 - 9, ty1 + 6)))
    for i, (nm, fx, fy) in enumerate(WARP_EXTRA):
        out.append((f"w{i}", nm, (int(wt * fx), int(ht * fy))))
    return out


def switch_list(wt, ht, lay):
    out = {}
    for key, rel in (("west", ((14, 10), (30, -2), (22, 26))), ("east", ((-14, 10), (-30, -2), (-22, 26))),
                     ("north", ((-18, 14), (18, 14), (0, 17)))):
        x0, y0, x1, y1, _, _ = lay["lairs"][key]
        cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
        out[key] = [(clamp(cx + dx, 12, wt - 13), clamp(cy + dy, 12, ht - 13)) for dx, dy in rel]
    return out


# ================================================================= 월드 생성
def generate(seed, wt, ht, tau):
    T = G.T
    rng = random.Random(seed)
    lay = layout(wt, ht)
    vil, tp = lay["vil"], lay["temple"]
    vx0, vy0, vx1, vy1 = vil
    vcx, vcy = (vx0 + vx1) // 2, (vy0 + vy1) // 2
    tx0, ty0, tx1, ty1 = tp
    tmx = (tx0 + tx1) // 2
    wdef, sdef = warp_list(wt, ht, lay), switch_list(wt, ht, lay)
    xm, ym = wt - 1, ht - 1

    # ---- 보호 구역: 구조물 주변은 평탄하게 (산·물 금지)
    rects = [(vx0 - 2, vy0 - 2, vx1 + 2, vy1 + 2, 8), (tx0 - 6, ty0 - 5, tx1 + 6, ty1 + 14, 8)]
    for key, (x0, y0, x1, y1, side, _) in lay["lairs"].items():
        ex = dict(e=(-5, -5, 14, 5), w=(-14, -5, 5, 5), s=(-5, -5, 5, 14))[side]
        rects.append((x0 + ex[0], y0 + ex[1], x1 + ex[2], y1 + ex[3], 6))
    rects += [(x - 4, y - 4, x + 4, y + 4, 5) for _, _, (x, y) in wdef]
    rects += [(x - 3, y - 3, x + 3, y + 3, 4) for pts in sdef.values() for x, y in pts]
    prot = [[0.0] * wt for _ in range(ht)]
    for x0, y0, x1, y1, m in rects:
        for y in range(max(0, y0 - m), min(ht, y1 + m + 1)):
            dy = max(y0 - y, 0, y - y1)
            row = prot[y]
            for x in range(max(0, x0 - m), min(wt, x1 + m + 1)):
                f = 1 - math.hypot(max(x0 - x, 0, x - x1), dy) / m
                if f > row[x]:
                    row[x] = f

    # ---- 지역(바이옴) 가중치와 고도: 월드 전체에서 한 번에 계산
    nxf, nyf = G.noise2(rng, 16, wt, ht), G.noise2(rng, 16, wt, ht)
    elev, ridn, edgn = G.fractal(rng, 30, 11, wt, ht), G.noise2(rng, 14, wt, ht), G.noise2(rng, 9, wt, ht)
    ancs = [(fx * wt, fy * ht, s) for fx, fy, s in ANCH]
    ik = {}
    regw = [[None] * wt for _ in range(ht)]
    dom = [[0] * wt for _ in range(ht)]
    Ei = [[0.0] * wt for _ in range(ht)]
    Et = [[0.0] * wt for _ in range(ht)]
    EG = [[0.0] * wt for _ in range(ht)]
    for y in range(ht):
        for x in range(wt):
            px, py = clamp(x + (nxf(x, y) - 0.5) * 26, 0, xm), clamp(y + (nyf(x, y) - 0.5) * 26, 0, ym)
            sc = [math.hypot(px - ax, py - ay) / s for ax, ay, s in ancs]
            m = min(sc)
            ws = [math.exp(-(s - m) / tau) for s in sc]
            tot = sum(ws)
            key = tuple(int(w / tot * 8 + 0.5) for w in ws)
            regw[y][x] = ik.setdefault(key, key)
            dom[y][x] = sc.index(m)
            s2 = sorted(sc)[1]
            border = 1 - clamp((s2 - m) / 14, 0, 1)
            r = 1 - abs(2 * ridn(x, y) - 1)
            ei = elev(x, y) * 0.85 + 0.45 * border * r * r
            ed = min(x, y, xm - x, ym - y)
            et = clamp(1 - (ed - 2 - 5 * edgn(x, y)) / 4, 0, 1)
            Ei[y][x], EG[y][x], Et[y][x] = ei, et, ei + 0.7 * et

    vals = sorted(Ei[y][x] for y in range(12, ht - 12) for x in range(12, wt - 12) if prot[y][x] < 0.35)
    thr_m, thr_l = vals[int(len(vals) * 0.90)], vals[int(len(vals) * 0.045)]

    # ---- 호수 · 산맥
    mount, lake = set(), set()
    for y in range(ht):
        for x in range(wt):
            ed = min(x, y, xm - x, ym - y)
            if ed < 3:
                mount.add((x, y))
            elif prot[y][x] >= 0.35:
                continue
            elif EG[y][x] > 0.5 or Ei[y][x] > thr_m:
                mount.add((x, y))
            elif Ei[y][x] < thr_l and ed >= 10:
                lake.add((x, y))
    water = {t for t in lake if sum((t[0] + i, t[1] + j) in lake for i in (-1, 0, 1) for j in (-1, 0, 1)) >= 4}

    def Eat(x, y):
        return Et[int(clamp(y, 0, ym))][int(clamp(x, 0, xm))]

    def paint(x, y, w):
        for j in range(-3, 4):
            for i in range(-3, 4):
                tx, ty = int(x) + i, int(y) + j
                if math.hypot(tx - x, ty - y) <= w and 6 <= tx < wt - 6 and 6 <= ty < ht - 6 and prot[ty][tx] < 0.35:
                    water.add((tx, ty))
                    mount.discard((tx, ty))

    srcs = sorted(((Ei[y][x], x, y) for y in range(16, ht - 16, 3) for x in range(16, wt - 16, 3) if prot[y][x] < 0.1),
                  reverse=True)[:60]
    rng.shuffle(srcs)
    picked = []
    for _, x, y in srcs:                                        # 높은 곳에서 시작해 낮은 곳으로 흐르는 강 (최대 3줄기)
        if len(picked) >= 3:
            break
        if all(math.hypot(x - a, y - b) > 40 for a, b in picked):
            picked.append((x, y))
    for sx, sy in picked:
        x, y, ang, up = float(sx), float(sy), rng.random() * 6.283, 0
        for step in range(520):
            best = None
            for da in (-0.9, -0.6, -0.3, 0, 0.3, 0.6, 0.9):
                a = ang + da
                qx, qy = x + math.cos(a) * 4, y + math.sin(a) * 4
                if not (8 <= qx < wt - 8 and 8 <= qy < ht - 8):
                    continue
                v = Eat(qx, qy) + rng.random() * 0.04 + abs(da) * 0.015
                if best is None or v < best[0]:
                    best = (v, a)
            if best is None:
                break
            if best[0] > Eat(x, y) + 0.02:
                up += 1
                if up > 6:                                       # 막다른 곳에는 연못이 생긴다
                    paint(x, y, 3.0)
                    break
            else:
                up = 0
            ang = best[1]
            x, y = x + math.cos(ang) * 1.2, y + math.sin(ang) * 1.2
            paint(x, y, 1.3 + 0.5 * math.sin(step * 0.15))
            if step > 12 and (int(x), int(y)) in lake:
                break

    ter = [[0] * wt for _ in range(ht)]                         # 0 풀 1 물 2 모래 3 길 4 폐허바닥 6 마을 7 다리 8 산
    for x, y in water:
        ter[y][x] = 1
    for x, y in mount:
        ter[y][x] = 8

    # ---- 구조물 (월드 좌표에 찍는다)
    solid, houses, npcs, pz, portals, deco, keep = set(), {}, [], [], [], [], []
    for x in range(vx0, vx1 + 1):                               # 마을 광장: 불규칙한 타원
        for y in range(vy0, vy1 + 1):
            ter[y][x] = 6
    pn = G.noise2(rng, 5, wt, ht)
    for y in range(vcy - 12, vcy + 13):
        for x in range(vcx - 18, vcx + 19):
            if 3 <= x < wt - 3 and 3 <= y < ht - 3 and ((x - vcx) / 15) ** 2 + ((y - vcy) / 10) ** 2 < 1.0 + 0.6 * (pn(x, y) - 0.5):
                ter[y][x] = 6
    for hx, hy, w, h in ((vx0 + 1, vy0 + 1, 4, 3), (vx0 + 15, vy0 + 1, 4, 3)):
        for x in range(hx, hx + w):
            for y in range(hy, hy + h):
                solid.add((x, y))
                houses[(x, y)] = (y == hy)
    npcs = [("smith", vx0 + 13, vy0 + 5), ("shop", vx0 + 7, vy0 + 5), ("bench", vx0 + 4, vy0 + 9)]
    start = (vx0 + 10, vy0 + 7)
    keep += [(tx, ty) for _, tx, ty in npcs] + [start]
    for k in range(-1, 2):
        keep.append((vcx + k * 2, vy0 - 3))

    modes = dict(west="order", east="all", north="order")
    fronts = {}
    for key, lair in lay["lairs"].items():
        x0, y0, x1, y1, side, mid = lair
        mx, my = (x0 + x1) // 2, (y0 + y1) // 2
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                ter[y][x] = 4
                mount.discard((x, y))
        G.ring_(solid, x0, y0, x1, y1)
        gate = ({(x1, my - 1 + i) for i in range(3)} if side == "e" else
                {(x0, my - 1 + i) for i in range(3)} if side == "w" else {(mx - 1 + i, y1) for i in range(3)})
        portals.append(dict(x=mx * T + 8, y=my * T + 8, to=G.ARENA_OF[mid], at=(17, 26), boss=True))
        pz.append(dict(mode=modes[key], pid=key, next=0, done=False, gate=gate,
                       sw=[dict(x=x * T + 8, y=y * T + 8, on=False, idx=j) for j, (x, y) in enumerate(sdef[key])]))
        fronts[key] = front_of(lair)
        keep += sdef[key] + [fronts[key]]
    for x in range(tx0, tx1 + 1):                               # 중앙 사원
        for y in range(ty0, ty1 + 1):
            ter[y][x] = 4
            mount.discard((x, y))
    G.ring_(solid, *tp)
    tgate = {(tmx - 1 + i, ty1) for i in range(3)}
    solid |= {(x, y) for x in range(tx0 + 1, tx1) for y in range(ty0 + 1, ty1)}
    solid -= {(x, y) for x in range(tmx - 1, tmx + 2) for y in range(ty1 - 4, ty1)}
    portals.append(dict(x=tmx * T + 8, y=(ty1 - 3) * T + 8, to="boss_f", at=(17, 26), boss=True))
    fronts["temple"] = (tmx, ty1 + 3)
    keep.append(fronts["temple"])
    for y in range(ty1 + 1, ty1 + 11):                          # 사원 앞 고대 포석 광장
        for x in range(tmx - 8, tmx + 9):
            if ((x - tmx) / 8.5) ** 2 + ((y - ty1 - 1) / 9.0) ** 2 < 1.0 + 0.5 * (pn(x, y) - 0.5) and (x, y) not in water:
                ter[y][x] = 4
    for dx, dy in ((-4, 2), (4, 2), (-4, 6), (4, 6)):
        deco.append(("statue", (tmx + dx) * T + 8, (ty1 + dy) * T + 8, True))
    for dx, dy in ((-2, 2), (2, 2), (-2, 8), (2, 8)):
        deco.append(("lamp", (tmx + dx) * T + 8, (ty1 + dy) * T + 8, True))
    for k, tl, tt in ((d[0], int(d[1]) // T, int(d[2]) // T) for d in deco):
        solid.add((tl, tt))
    ntile = {(int(d[1]) // T, int(d[2]) // T) for d in deco}

    warps = []
    for wid, nm, (x, y) in wdef:
        warps.append(dict(id=wid, name=nm, tx=x, ty=y, act_t=-99.0))
        keep.append((x, y))
        keep.append((x, y + 2))
        for dxx in range(-1, 2):                                # 받침 주변은 풀밭으로
            for dyy in range(-1, 3):
                if ter[y + dyy][x + dxx] in (1, 8):
                    ter[y + dyy][x + dxx] = 0
                    water.discard((x + dxx, y + dyy))
                    mount.discard((x + dxx, y + dyy))
    for pts in sdef.values():
        for x, y in pts:
            ter[y][x] = 0 if ter[y][x] in (1, 8) else ter[y][x]
            water.discard((x, y))
            mount.discard((x, y))

    # ---- 길: 월드 전체에서 A* (지형 비용 + 노이즈)로 깐다
    cs = 3
    cw, chh = (wt + cs - 1) // cs, (ht + cs - 1) // cs
    cell = [[1.0] * cw for _ in range(chh)]
    for cy in range(chh):
        for cx in range(cw):
            nw = nm_ = 0
            blocked = False
            for y in range(cy * cs, min(ht, cy * cs + cs)):
                for x in range(cx * cs, min(wt, cx * cs + cs)):
                    if (x, y) in solid:
                        blocked = True
                    elif (x, y) in water:
                        nw += 1
                    elif (x, y) in mount:
                        nm_ += 1
            edge = min(cx * cs, cy * cs, xm - cx * cs, ym - cy * cs) < 8
            cell[cy][cx] = None if blocked else 1.0 + 0.9 * nw + 1.3 * nm_ + rng.random() * 0.5 + (8 if edge else 0)
    N8 = ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1))

    def route(a, b):
        s, gl = (a[0] // cs, a[1] // cs), (b[0] // cs, b[1] // cs)
        dist_, prev, cnt, heap = {s: 0.0}, {}, 0, [(0.0, 0, s)]
        while heap:
            f, _, cur = heapq.heappop(heap)
            if cur == gl:
                break
            if f - math.hypot(cur[0] - gl[0], cur[1] - gl[1]) > dist_[cur] + 1e-6:
                continue
            for dx, dy in N8:
                n = (cur[0] + dx, cur[1] + dy)
                if not (0 <= n[0] < cw and 0 <= n[1] < chh):
                    continue
                c = cell[n[1]][n[0]]
                if c is None:
                    if n != gl and n != s:
                        continue
                    c = 1.0
                nd = dist_[cur] + c * (1.4142 if dx and dy else 1.0)
                if nd < dist_.get(n, 1e18):
                    dist_[n], prev[n] = nd, cur
                    cnt += 1
                    heapq.heappush(heap, (nd + math.hypot(n[0] - gl[0], n[1] - gl[1]), cnt, n))
        if gl not in prev and gl != s:
            return None
        path, cur = [gl], gl
        while cur != s:
            cur = prev[cur]
            path.append(cur)
        path.reverse()
        pts = [a] + [(c[0] * cs + 1.5, c[1] * cs + 1.5) for c in path[1:-1]] + [b]
        for _ in range(2):                                      # 모서리 깎기: 각진 격자 길이 부드러운 곡선이 된다
            q = [pts[0]]
            for p, r in zip(pts, pts[1:]):
                q.append((0.75 * p[0] + 0.25 * r[0], 0.75 * p[1] + 0.25 * r[1]))
                q.append((0.25 * p[0] + 0.75 * r[0], 0.25 * p[1] + 0.75 * r[1]))
            q.append(pts[-1])
            pts = q
        return pts

    roadt = set()

    def carve(pts, w=2):
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            L = math.hypot(bx - ax, by - ay) or 1
            n, ph = int(L * 2) + 1, rng.random() * 6.283
            for i in range(n + 1):
                t = i / n
                off = math.sin(t * math.pi) * 1.4 * math.sin(t * 5 + ph)
                x, y = ax + (bx - ax) * t - (by - ay) / L * off, ay + (by - ay) * t + (bx - ax) / L * off
                for ox in range(w):
                    for oy in range(w):
                        tx, ty = int(x) + ox, int(y) + oy
                        if not (2 <= tx < wt - 2 and 2 <= ty < ht - 2) or (tx, ty) in solid or ter[ty][tx] in (4, 6):
                            continue
                        if ter[ty][tx] == 1:
                            ter[ty][tx] = 7
                            water.discard((tx, ty))
                        else:
                            ter[ty][tx] = 3
                            mount.discard((tx, ty))
                        roadt.add((tx, ty))

    vc = (vcx, vcy)
    for a, b in ((vc, fronts["temple"]), (vc, fronts["west"]), (vc, fronts["east"]),
                 (fronts["temple"], fronts["north"]), (fronts["west"], fronts["north"])):
        p = route(a, b)
        if p:
            carve(p)
    spots = [(w["tx"], w["ty"] + 2) for w in warps] + [pt for pts in sdef.values() for pt in pts]
    for sx, sy in spots:                                        # 워프·스위치로 가는 샛길: 가장 가까운 길에서 갈라진다
        near = min(roadt, key=lambda t: (t[0] - sx) ** 2 + (t[1] - sy) ** 2)
        if math.hypot(near[0] - sx, near[1] - sy) > 3:
            p = route((sx, sy), near)
            if p:
                carve(p, 1 if rng.random() < 0.5 else 2)
    add = [(x + i, y + j) for x, y in water for i, j in ((1, 0), (-1, 0), (0, 1), (0, -1))
           if 0 <= x + i < wt and 0 <= y + j < ht and ter[y + j][x + i] == 7]
    for x, y in add:                                            # 다리 폭 넓히기
        ter[y][x] = 7
        water.discard((x, y))
    clear = {(x + i, y + j) for x, y in roadt for i in (-1, 0, 1) for j in (-1, 0, 1)}
    for y in range(1, ht - 1):                                  # 물가 모래
        for x in range(1, wt - 1):
            if ter[y][x] == 0 and any((x + i, y + j) in water for i in (-1, 0, 1) for j in (-1, 0, 1)):
                ter[y][x] = 2
    solid |= water | mount

    # ---- 폐허
    kz = {(x + i, y + j) for x, y in keep for i in range(-2, 3) for j in range(-2, 3)}

    def okt(x, y):
        return (3 <= x <= wt - 4 and 3 <= y <= ht - 4 and ter[y][x] == 0 and (x, y) not in solid and (x, y) not in clear
                and (x, y) not in kz and prot[y][x] < 0.99)
    ruins, rc = [], []
    for _ in range(260):
        if len(ruins) >= 18:
            break
        w_, h_ = rng.randint(5, 8), rng.randint(4, 6)
        x, y = rng.randint(4, wt - w_ - 5), rng.randint(4, ht - h_ - 5)
        pr = (0.35, 0.8, 0.7, 1.0, 1.0)[dom[y][x]]
        if rng.random() > pr or any(math.hypot(x - a, y - b) < 14 for a, b in rc):
            continue
        if not all(okt(i, j) for i in range(x - 1, x + w_ + 1) for j in range(y - 1, y + h_ + 1)):
            continue
        rc.append((x, y))
        ruins.append((x + w_ // 2, y + h_ // 2))
        gap = rng.choice("tblr")
        for i in range(x, x + w_):
            for j in range(y, y + h_):
                ter[j][i] = 4
                edge, corner = i in (x, x + w_ - 1) or j in (y, y + h_ - 1), i in (x, x + w_ - 1) and j in (y, y + h_ - 1)
                if not edge:
                    continue
                gp = ((gap == "t" and j == y) or (gap == "b" and j == y + h_ - 1)) and abs(i - (x + w_ // 2)) <= 1 or \
                     ((gap == "l" and i == x) or (gap == "r" and i == x + w_ - 1)) and abs(j - (y + h_ // 2)) <= 1
                if corner or (not gp and rng.random() < 0.55):
                    solid.add((i, j))
        if rng.random() < 0.6:
            solid.add((x + w_ // 2, y + h_ // 2))

    # ---- 채집물: 지역 가중치 + 노이즈로 숲은 뭉치고 광석은 산자락에, 약초는 물가에 모인다
    nearm = {(x + i, y + j) for x, y in mount if 6 < x < wt - 7 and 6 < y < ht - 7 for i in range(-3, 4) for j in range(-3, 4)}
    nearw = {(x + i, y + j) for x, y in water for i in range(-2, 3) for j in range(-2, 3)}
    free = [(x, y) for y in range(3, ht - 3) for x in range(3, wt - 3) if okt(x, y)]
    occ, nodes = set(), []
    fo = G.fractal(rng, 12, 5, wt, ht)

    def scatter(kind, n, wf):
        cand = [(x, y) for x, y in free if (x, y) not in occ]
        keyed = [(rng.random() ** (1.0 / w), t) for t in cand for w in (wf(*t),) if w > 0]
        for _, t in heapq.nlargest(n, keyed):
            occ.add(t)
            nodes.append(dict(kind=kind, tx=t[0], ty=t[1], hp=G.NODE[kind][0], t=0, alive=True))

    def bw(x, y, vals):
        k = regw[y][x]
        return sum(k[i] * vals[i] for i in range(5)) / (sum(k) or 1)
    nf = len(free)
    scatter("tree", int(nf * 0.034), lambda x, y: bw(x, y, (0.9, 0.8, 1.2, 0.7, 0.85)) * (0.12 + clamp((fo(x, y) - 0.40) / 0.25, 0, 1) ** 1.4 * 2.0))
    scatter("ore", int(nf * 0.0035), lambda x, y: (5.0 if (x, y) in nearm else 0.15) * bw(x, y, (0.5, 1.3, 1.0, 1.0, 1.4)))
    scatter("rock", int(nf * 0.007), lambda x, y: 1.0 + (6.0 if (x, y) in nearm else 0))
    scatter("herb", int(nf * 0.009), lambda x, y: 1.0 + (5.0 if (x, y) in nearw else 0) + (2.0 if ter[y][x] == 2 else 0))
    for nd in nodes:
        if nd["kind"] != "herb":
            ntile.add((nd["tx"], nd["ty"]))
    solid |= ntile

    # ---- 장식: 지역 테마(THEME)를 지역마다 배치
    taken = set()

    def okd(x, y, sol, bi):
        if not (3 <= x < wt - 3 and 3 <= y < ht - 3) or ter[y][x] not in (0, 4) or (x, y) in solid or (x, y) in taken:
            return False
        if (x, y) in kz or (bi is not None and regw[y][x][bi] < 5) or prot[y][x] >= 0.99 and ter[y][x] != 4:
            return False
        if sol and any((x + i, y + j) in solid or (x + i, y + j) in clear for i in (-1, 0, 1) for j in (-1, 0, 1)):
            return False
        return True

    def putd(kind, x, y, sol):
        taken.add((x, y))
        deco.append((kind, x * T + 8, y * T + 8, sol))
        if sol:
            solid.add((x, y))
            ntile.add((x, y))
    for bi, zid in enumerate(BIOMES):
        for kind, n, sol in W.THEME.get(zid, []):
            cnt = tries = 0
            while cnt < int(n * 1.7) and tries < n * 80:
                tries += 1
                x, y = rng.randint(3, wt - 4), rng.randint(3, ht - 4)
                if dom[y][x] == bi and okd(x, y, sol, bi):
                    putd(kind, x, y, sol)
                    cnt += 1
    rl = sorted(roadt)
    lamps = []
    for _ in range(400):                                        # 가로등: 길가
        if len(lamps) >= 64 or not rl:
            break
        x, y = rng.choice(rl)
        dx, dy = rng.choice(((2, 0), (-2, 0), (0, 2), (0, -2)))
        x, y = x + dx, y + dy
        if ter[y][x] == 0 and okd(x, y, False, None) and all(math.hypot(x - a, y - b) > 7 for a, b in lamps):
            putd("lamp", x, y, True)
            lamps.append((x, y))
    for x, y in ((vx0 + 2, vy0 + 2), (vx1 - 2, vy0 + 2), (vx0 + 2, vy1 - 2), (vx1 - 2, vy1 - 2),
                 (vx0 + 9, vy0 + 7), (vx0 + 11, vy0 + 7)):
        if (x, y) not in solid and (x, y) not in kz:
            putd("lamp", x, y, True)
    west_roads = [t for t in rl if dom[t[1]][t[0]] == 1]
    for i in range(0, len(west_roads), 9):                      # 노을 회랑: 길을 따라 늘어선 열주
        x, y = west_roads[i]
        for dx, dy in ((0, -3), (0, 3), (-3, 0), (3, 0)):
            if okd(x + dx, y + dy, True, None):
                putd("pillar", x + dx, y + dy, True)
    for w in warps:                                             # 워프포인트 받침
        putd("warp", w["tx"], w["ty"], True)
        deco.append(("warp_marker", 0, 0, False))
    deco[:] = [d for d in deco if d[0] != "warp_marker"]

    # ---- 도달 가능성 검사: 마을에서 갈 수 없는 목표가 있으면 길을 뚫어 준다
    def flood():
        seen, q = {start}, [start]
        for a, b in q:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (a + dx, b + dy)
                if n not in seen and 0 <= n[0] < wt and 0 <= n[1] < ht and n not in solid:
                    seen.add(n)
                    q.append(n)
        return seen
    reach = flood()
    pois = list(fronts.values()) + [(w["tx"], w["ty"] + 1) for w in warps] + [p for pts in sdef.values() for p in pts]
    fixed = 0
    for px_, py_ in pois:
        if (px_, py_) in reach:
            continue
        fixed += 1
        near = min(reach, key=lambda t: (t[0] - px_) ** 2 + (t[1] - py_) ** 2)
        n = int(math.hypot(near[0] - px_, near[1] - py_) * 2) + 1
        for i in range(n + 1):
            tx, ty = int(px_ + (near[0] - px_) * i / n), int(py_ + (near[1] - py_) * i / n)
            for ox in range(2):
                for oy in range(2):
                    t = (tx + ox, ty + oy)
                    if t in solid and t not in ntile and ter[t[1]][t[0]] not in (1, 8) and t not in water and t not in mount:
                        continue
                    solid.discard(t)
                    ntile.discard(t)
                    water.discard(t)
                    mount.discard(t)
                    ter[t[1]][t[0]] = 3 if ter[t[1]][t[0]] != 1 else 7
        for nd in nodes:
            if (nd["tx"], nd["ty"]) not in solid:
                nd["alive"], nd["t"] = False, 1e9
        deco[:] = [d for d in deco if (int(d[1]) // T, int(d[2]) // T) not in {t for t in ntile} or d[0] == "warp"
                   or (int(d[1]) // T, int(d[2]) // T) in solid]
        reach = flood()
    # ---- 적: 야영지 + 떠돌이. 마을·워프 주변은 안전지대
    mixes = [dict(G.MIX[z]) for z in BIOMES]
    safe = [(vcx, vcy, 17)] + [(w["tx"], w["ty"], 9) for w in warps] + [(f[0], f[1], 8) for f in fronts.values()]
    cands = [t for t in reach if t not in solid and ter[t[1]][t[0]] in (0, 2, 3, 4) and 5 < t[0] < wt - 6 and 5 < t[1] < ht - 6
             and all(math.hypot(t[0] - a, t[1] - b) > r for a, b, r in safe)]
    cands.sort()
    rng.shuffle(cands)

    def pick_kind(x, y):
        k, acc = regw[y][x], {}
        tot = sum(k) or 1
        for i in range(5):
            for kind, wgt in mixes[i].items():
                acc[kind] = acc.get(kind, 0) + k[i] / tot * wgt
        kinds = list(acc)
        return rng.choices(kinds, [acc[q] for q in kinds])[0]
    en, used = [], set()
    centers = []
    for rx, ry in ruins:
        if (rx, ry) in reach and all(math.hypot(rx - a, ry - b) > r for a, b, r in safe) and len(centers) < 9:
            centers.append((rx, ry))
    for t in cands:
        if len(centers) >= 18:
            break
        if all(math.hypot(t[0] - a, t[1] - b) > 15 for a, b in centers):
            centers.append(t)
    for cx_, cy_ in centers:
        n = rng.randint(2, 4)
        around = [t for t in cands if t not in used and math.hypot(t[0] - cx_, t[1] - cy_) <= 4]
        rng.shuffle(around)
        for t in around[:n]:
            used.add(t)
            en.append(G.mk_foe(pick_kind(*t), t[0] * T + 8, t[1] * T + 8))
    singles = [t for t in cands if t not in used and all(math.hypot(t[0] - a, t[1] - b) > 6 for a, b in centers)]
    for t in singles[:26]:
        en.append(G.mk_foe(pick_kind(*t), t[0] * T + 8, t[1] * T + 8))

    sn = G.fractal(rng, 6, 3, wt, ht)
    shade = [[sn(x, y) for x in range(wt)] for y in range(ht)]
    regmap = [[BREG[dom[y][x]] for x in range(wt)] for y in range(ht)]
    style = build_styles(regw, wt, ht, tp)
    spec = G.ZONES[WID]
    meta = dict(vil=vil, temple=tp, lairs=lay["lairs"], fronts=fronts, start=start, ruins=ruins, fixed=fixed,
                tiles_mount=len(mount), tiles_water=len(water))
    return dict(solid=solid, nodes=nodes, ntile=ntile, houses=houses, pz=pz, en=en, ter=ter, water=water, shade=shade,
                rs=[], npcs=npcs, spec=spec, tgate=tgate, core=None, vil=vil, portals=portals, exits=[], wt=wt, ht=ht,
                zreg=0, deco=deco, arena=None, style=style, regmap=regmap, regw=regw, warps=warps, meta=meta)


def build_styles(regw, wt, ht, tp):
    """타일마다 5개 지역 색을 가중 평균한 스타일(바닥·벽·잎). 가중치는 8단계로 양자화해 사전을 공유한다."""
    R, cache = G.REGIONS, {}
    st = [[None] * wt for _ in range(ht)]
    for y in range(ht):
        row, srow = regw[y], st[y]
        for x in range(wt):
            key = row[x]
            s = cache.get(key)
            if s is None:
                tot = sum(key) or 1

                def mix(nm):
                    return tuple(int(sum(key[k] * R[BREG[k]][nm][i] for k in range(5)) / tot) for i in range(3))
                s = dict(name=R[BREG[key.index(max(key))]]["name"], floor=mix("floor"), floor2=mix("floor2"),
                         wall=mix("wall"), leaf=mix("leaf"))
                cache[key] = s
            srow[x] = s
    for y in range(tp[1] + 1, tp[3]):
        for x in range(tp[0] + 1, tp[2]):
            st[y][x] = R[4]
    return st


# ---------------------------------------------------------------- 미리 생성 (타이틀 화면 동안 백그라운드에서)
def start_build():
    if _PRE["th"] is not None or _PRE["z"] is not None:
        return
    wt, ht, seed, tau = params()

    def run():
        try:
            _PRE["z"] = generate(seed, wt, ht, tau)
        except Exception:
            G.v9_log("world-gen")

    _PRE["th"] = threading.Thread(target=run, daemon=True)
    _PRE["th"].start()


def take_world():
    th = _PRE["th"]
    if th is not None:
        th.join()
    z, _PRE["th"], _PRE["z"] = _PRE["z"], None, None
    if z is None:
        wt, ht, seed, tau = params()
        z = generate(seed, wt, ht, tau)
    return z


# ================================================================= 지역·조명 (경계에서 서서히 바뀐다)
def tile_reg(g, tx, ty):
    rm = g.get("regmap")
    if rm is None or not (0 <= ty < len(rm) and 0 <= tx < len(rm[0])):
        return g["zreg"]
    tp = g["meta"]["temple"]
    return 4 if tp[0] < tx < tp[2] and tp[1] < ty < tp[3] else rm[ty][tx]


def tile_style(g, tx, ty):
    st = g.get("style")
    if st is None or not (0 <= ty < len(st) and 0 <= tx < len(st[0])):
        return G.REGIONS[tile_reg(g, tx, ty)]
    return st[ty][tx]


def player_reg(g):
    """경계 위를 오가도 이름·음악이 깜빡이지 않도록, 새 지역에 0.9초 머문 뒤에야 바뀐다"""
    r = tile_reg(g, int(g["x"]) // G.T, int(g["y"]) // G.T)
    if g.get("regmap") is None or r == g["reg"]:
        g["_rc"] = None
        return r
    rc = g.get("_rc")
    if rc is None or rc[0] != r:
        g["_rc"] = (r, g["t"])
        return g["reg"]
    if g["t"] - rc[1] >= 0.9:
        g["_rc"] = None
        return r
    return g["reg"]


def ambient_target(g):
    tx, ty = int(g["x"]) // G.T, int(g["y"]) // G.T
    tx, ty = int(clamp(tx, 0, g["wt"] - 1)), int(clamp(ty, 0, g["ht"] - 1))
    if tile_reg(g, tx, ty) == 4:
        return list(map(float, W.AMBIENT.get(4, (0, 0, 0, 0))))
    k = g["regw"][ty][tx]
    tot = sum(k) or 1
    r = gg = b = a = 0.0
    for i in range(5):
        cr, cg, cb, ca = W.AMBIENT.get(BREG[i], (0, 0, 0, 0))
        w = k[i] / tot
        r, gg, b, a = r + cr * ca * w, gg + cg * ca * w, b + cb * ca * w, a + ca * w
    return [r / a, gg / a, b / a, a] if a > 0.5 else [0.0, 0.0, 0.0, 0.0]


def lighting_wrap(old):
    def f(surf, g, cx, cy):
        if g.get("zid") != WID or not g.get("regw"):
            return old(surf, g, cx, cy)
        tg = ambient_target(g)
        cur = g.get("_amb") or list(tg)
        dt = clamp(g["t"] - g.get("_amb_t", g["t"]), 0.0, 0.2)
        k = 1 - math.exp(-dt * 2.2)
        cur = [c + (t - c) * k for c, t in zip(cur, tg)]
        g["_amb"], g["_amb_t"] = cur, g["t"]
        W.AMBIENT[99] = tuple(int(v) for v in cur)
        sv = g["reg"]
        g["reg"] = 99
        try:
            old(surf, g, cx, cy)
        finally:
            g["reg"] = sv
    return f


# ================================================================= 그리기: 산·사원 정면·워프
def draw_cliff(surf, g, tx, ty, px, py, r):
    """산: 타일마다 줄무늬가 반복되지 않고, 덩어리의 윗면은 밝게·아랫면(절벽)은 어둡게 이어진다"""
    h, ter = G.hsh(tx, ty), g["ter"]
    base = G.adj(r["wall"], int((g["shade"][ty][tx] - 0.5) * 46) + h % 5 - 2)
    surf.fill(base, (px, py, G.T, G.T))
    up = ty == 0 or ter[ty - 1][tx] == 8
    dn = ty + 1 >= g["ht"] or ter[ty + 1][tx] == 8
    lf = tx == 0 or ter[ty][tx - 1] == 8
    if not up:
        surf.fill(G.adj(base, 38), (px, py, G.T, 3))
        surf.fill(G.adj(base, 20), (px, py + 3, G.T, 2))
    if not dn:
        surf.fill(G.adj(base, -44), (px, py + 9, G.T, 7))
        surf.fill(G.adj(base, -72), (px, py + 14, G.T, 2))
    if not lf:
        surf.fill(G.adj(base, 14), (px, py, 1, G.T))
    if h % 3 == 0:
        surf.fill(G.adj(base, -24), (px + 2 + h % 9, py + 4 + h % 6, 5, 1))
    if h % 5 == 0:
        surf.fill(G.adj(base, 22), (px + 4 + h % 6, py + 8, 3, 1))
    if h % 11 == 0:
        surf.fill(G.adj(base, -34), (px + 7, py + 2, 1, 5))


def draw_warps(surf, g, cx, cy):
    t = g["t"]
    for w in g["warps"]:
        x, y = w["tx"] * G.T + 8 - cx, w["ty"] * G.T + 8 - cy
        if x < -40 or x > G.W + 40 or y < -100 or y > G.H + 40:
            continue
        on = w["id"] in g["wact"]
        cy0 = y - 7                                              # 받침 위에 떠 있는 결정의 중심
        if on:
            age = t - w["act_t"]
            grow = 1.0 if age > 1.4 else (age / 1.4) ** 0.6
            hh = int(80 * grow)
            if hh > 2:
                shaft = pygame.Surface((13, hh), SC)
                for yy in range(hh):
                    a = int(120 * (1 - yy / hh) ** 1.4 * (0.78 + 0.22 * math.sin(t * 3 + yy * 0.05)))
                    wd = 3 + int(3 * (1 - yy / hh))
                    shaft.fill((140, 240, 240, a), (6 - wd // 2 - 1, hh - 1 - yy, wd + 2, 1))
                surf.blit(shaft, (x - 6, cy0 - hh))
            for i in range(6):                                   # 받침을 도는 룬 입자
                a = t * 1.8 + i * 1.047
                px_, py_ = x + math.cos(a) * 11, y + 7 + math.sin(a) * 4
                surf.fill((200, 255, 255) if math.sin(a) > 0 else (80, 170, 190), (int(px_), int(py_), 2, 2))
            for i in range(4):
                surf.fill((220, 255, 255), (x - 5 + (i * 7 + int(t * 9)) % 11, int(cy0 - ((t * 22 + i * 13) % 34)), 1, 1))
            D.circle(surf, (230, 255, 255), (x, cy0), 3)
            D.circle(surf, (140, 240, 240), (x, cy0), 5, 1)
            if age < 1.6:
                D.circle(surf, (200, 252, 252), (x, y + 6), int(6 + age * 52), 1)
                D.circle(surf, (120, 232, 232), (x, y + 6), int(4 + age * 36), 1)
        else:
            a = 0.5 + 0.5 * math.sin(t * 1.5 + w["tx"])
            surf.fill(G.lerp_c((70, 80, 110), (110, 150, 190), a), (x - 1, cy0 - 1, 3, 3))


def draw_temple(surf, g, cx, cy):
    tp = g["meta"]["temple"]
    W.draw_facade(surf, g, cx + (24 - tp[0]) * G.T, cy + (14 - tp[1]) * G.T)   # 원본 정면 그림은 (24,14) 기준이라 카메라를 옮겨 그린다


def draw_arena_wrap(old):
    def f(surf, g, cx, cy):
        old(surf, g, cx, cy)
        if g.get("zid") == WID:
            try:
                draw_temple(surf, g, cx, cy)
                draw_warps(surf, g, cx, cy)
            except Exception:
                G.v9_log("open-draw")
    return f


def spr_warp(s):
    s.fill((92, 94, 122), (2, 22, 12, 2))
    s.fill((124, 122, 146), (2, 19, 12, 3))
    s.fill((150, 148, 172), (3, 16, 10, 3))
    s.fill((190, 188, 210), (3, 16, 10, 1))
    for x in (4, 7, 10):
        s.fill((120, 232, 232), (x, 20, 1, 1))
    D.polygon(s, (60, 150, 190), [(8, 2), (12, 9), (8, 16), (4, 9)])
    D.polygon(s, (120, 232, 232), [(8, 3), (11, 9), (8, 14), (5, 9)])
    s.fill((255, 255, 255), (7, 5, 1, 3))


# ================================================================= 지도 (월드 전체)
def mm_base_wrap(old):
    def f(g):
        zid = g["zid"]
        if zid in g["mm"] or zid != WID:
            return old(g)
        wt, ht = g["wt"], g["ht"]
        s = pygame.Surface((wt, ht))
        node_c = dict(tree=(44, 110, 66), rock=(140, 142, 156), ore=(80, 90, 150), herb=(70, 170, 90))
        nk = {(n["tx"], n["ty"]): n["kind"] for n in g["nodes"]}
        pal = {3: (196, 166, 118), 2: (232, 220, 176), 4: (186, 182, 198), 5: (36, 80, 52), 7: (156, 112, 74), 6: (214, 196, 150)}
        for y in range(ht):
            for x in range(wt):
                st = g["style"][y][x]
                if (x, y) in g["houses"]:
                    c = (190, 80, 70)
                elif (x, y) in g["water"]:
                    c = (70, 134, 204)
                elif g["ter"][y][x] == 8:
                    c = G.adj(st["wall"], -26 + int(g["shade"][y][x] * 30))
                elif (x, y) in nk:
                    c = node_c[nk[(x, y)]]
                elif (x, y) in g["solid"]:
                    c = G.adj(st["wall"], -20)
                else:
                    c = pal.get(g["ter"][y][x], st["floor"])
                s.set_at((x, y), c)
        fog = pygame.Surface((wt, ht), SC)
        fog.fill((10, 10, 24, 255))
        g["mm"][zid] = (s, fog, set())
        return g["mm"][zid]
    return f


def active_warps(g):
    return [w for w in g["warps"] if w["id"] in g["wact"]]


def minimap_wrap(old):
    def f(g, vw=60, vh=44):
        s = old(g, vw, vh)
        if g["zid"] != WID:
            return s
        wt, ht = g["wt"], g["ht"]
        aw, ah = min(vw, wt), min(vh, ht)
        tx, ty = int(g["x"]) // G.T, int(g["y"]) // G.T
        wx, wy = max(0, min(wt - aw, tx - aw // 2)), max(0, min(ht - ah, ty - ah // 2))
        ox, oy = (vw - aw) // 2, (vh - ah) // 2
        for w in active_warps(g):
            px, py = ox + w["tx"] - wx, oy + w["ty"] - wy
            if 1 <= px < vw - 1 and 1 <= py < vh - 1:
                s.fill((20, 20, 40), (px - 2, py - 2, 5, 5))
                s.fill((140, 245, 245), (px - 1, py - 1, 3, 3))
        return s
    return f


def draw_map(screen, font, g, u):
    SW, SH = G.W * u, G.H * u
    v = pygame.Surface((SW, SH), SC)
    v.fill((8, 6, 20, 215))
    screen.blit(v, (0, 0))
    pw, ph = int(SW * 0.94), 246 * u
    px, py = (SW - pw) // 2, (SH - ph) // 2
    G.frame(screen, px, py, pw, ph, u)
    G.ribbon(screen, G.bigfont(u), "지도 - 폐허의 대지" if g["zid"] == WID else "지도", px + pw // 2, py - 6 * u, u)
    G.txt(screen, font, "M · ESC 닫기", px + pw - 12 * u - font.size("M · ESC 닫기")[0], py + 9 * u, G.MUTED, u=u)
    if g["zid"] != WID:
        G.txt(screen, font, "이곳에서는 지도를 펼칠 수 없다", SW // 2, SH // 2 - 4 * u, G.CREAM, True, u)
        return
    base, fog, seen = W.mm_base(g)
    wt, ht = g["wt"], g["ht"]
    kx = min((pw / u - 24 - 150) / wt, (ph / u - 38) / ht)
    s2 = base.copy()
    s2.blit(fog, (0, 0))
    big = pygame.transform.scale(s2, (int(wt * kx * u), int(ht * kx * u)))
    mx, my = px + 12 * u, py + 22 * u
    screen.blit(big, (mx, my))
    D.rect(screen, G.INK, (mx - u, my - u, big.get_width() + 2 * u, big.get_height() + 2 * u), u)

    def pt(tx, ty):
        return mx + int((tx + 0.5) * kx * u), my + int((ty + 0.5) * kx * u)

    def vis(tx, ty):
        return (int(tx), int(ty)) in seen
    m = g["meta"]
    tp = m["temple"]
    marks = [("마을", ((m["vil"][0] + m["vil"][2]) // 2, (m["vil"][1] + m["vil"][3]) // 2), G.GOLD),
             ("중앙 사원", ((tp[0] + tp[2]) // 2, (tp[1] + tp[3]) // 2), G.GOLD)]
    for key, lr in m["lairs"].items():
        marks.append(("수호 기계의 방", ((lr[0] + lr[2]) // 2, (lr[1] + lr[3]) // 2), (255, 110, 100)))
    for label, (tx, ty), col in marks:
        if vis(tx, ty):
            D.rect(screen, G.INK, (*pt(tx, ty), 5 * u, 5 * u))
            D.rect(screen, col, (pt(tx, ty)[0] + u, pt(tx, ty)[1] + u, 3 * u, 3 * u))
            G.txt(screen, font, label, pt(tx, ty)[0] + 6 * u, pt(tx, ty)[1] - 2 * u, G.CREAM, u=u)
    act = active_warps(g)
    cur = int(clamp(g.get("wcur", 0), 0, max(0, len(act) - 1)))
    for w in g["warps"]:
        on, p = w["id"] in g["wact"], pt(w["tx"], w["ty"])
        if on:
            sel = act and act[cur] is w
            G.diamond(screen, p[0], p[1], (4 if sel else 3) * u, G.INK)
            G.diamond(screen, p[0], p[1], (3 if sel else 2) * u, (255, 255, 255) if sel else G.CYAN)
            if sel:
                D.circle(screen, G.CYAN, p, int((6 + 1.5 * math.sin(g["t"] * 6)) * u), u)
                G.txt(screen, font, w["name"], p[0] + 7 * u, p[1] - 4 * u, (255, 255, 255), u=u)
        elif vis(w["tx"], w["ty"]):
            G.diamond(screen, p[0], p[1], 2 * u, (110, 116, 140))
    pxp, pyp = pt(int(g["x"]) // G.T, int(g["y"]) // G.T)
    D.circle(screen, G.INK, (pxp, pyp), 4 * u)
    D.circle(screen, (255, 255, 255) if int(g["t"] * 3) % 2 else (255, 90, 90), (pxp, pyp), 3 * u)
    sx = px + pw - 150 * u                                       # 오른쪽: 활성화된 워프포인트 목록
    G.txt(screen, font, f"워프포인트  {len(act)}/{len(g['warps'])}", sx, py + 22 * u, G.GOLD, u=u)
    for i, w in enumerate(act):
        ry = py + (34 + i * 12) * u
        if i == cur:
            D.rect(screen, (58, 78, 128), (sx - 3 * u, ry - u, 142 * u, 11 * u))
            D.rect(screen, G.CYAN, (sx - 3 * u, ry - u, 142 * u, 11 * u), u)
        G.diamond(screen, sx + 3 * u, ry + 4 * u, 2 * u, G.CYAN)
        G.txt(screen, font, w["name"], sx + 9 * u, ry, G.CREAM if i == cur else G.MUTED, u=u)
    hy = py + ph - 36 * u
    for i, s in enumerate(("W/S 선택  ·  Enter 이동", "워프포인트는 가까이서 E로 켠다", "근처에 적이 있으면 이동할 수 없다")):
        G.txt(screen, font, s, sx, hy + i * 9 * u, G.MUTED, u=u)


# ================================================================= 워프 상호작용
def near_warp(g):
    for w in g.get("warps") or ():
        if G.dist(g["x"], g["y"], w["tx"] * G.T + 8, w["ty"] * G.T + 8) < 30:
            return w
    return None


def activate(g, w):
    g["wact"].add(w["id"])
    w["act_t"] = g["t"]
    x, y = w["tx"] * G.T + 8, w["ty"] * G.T + 8
    g["rings"].append([x, y, 0.0, 60, (120, 232, 232)])
    G.spark(g, x, y - 6, (150, 250, 250), 24)
    g["shake"] = 0.25
    G.play("up")
    G.play("portal")
    G.toast(g, f"워프포인트 활성화: {w['name']}", 3.0)
    if C.FX.get("autosave") and g.get("autosave_ok"):
        UI.save_game(g, quiet=True)


def do_warp(g):
    act = active_warps(g)
    if not act:
        return
    w = act[int(clamp(g.get("wcur", 0), 0, len(act) - 1))]
    x, y = w["tx"] * G.T + 8, w["ty"] * G.T + 8
    if G.dist(g["x"], g["y"], x, y) < 40:
        G.toast(g, "이미 이 워프포인트 곁에 있다", 1.8)
        G.play("deny")
        return
    if any(e["ag"] and e["hp"] > 0 and G.dist(g["x"], g["y"], e["x"], e["y"]) < 170 for e in g["en"]):
        G.toast(g, "근처에 적이 있어 이동할 수 없다", 2.0)
        G.play("deny")
        return
    cost = int((getattr(C, "WORLD", {}) or {}).get("warp_cost", DEFAULT["warp_cost"]))
    if cost and g["inv"]["gold"] < cost:
        G.toast(g, f"이동에는 {cost}G가 필요하다", 2.0)
        G.play("deny")
        return
    g["inv"]["gold"] -= cost
    G.play("portal")
    G.toast(g, f"워프: {w['name']}", 2.0)
    G.start_travel(g, WID, w["tx"], w["ty"] + 2)


def on_key_wrap(old):
    def f(g, k):
        if g is not None and g["mode"] == "play" and not g["tr"]:
            ui, inworld = g["ui"], g["zid"] == WID
            if k == pygame.K_m and ui is None and not inworld:
                G.toast(g, "이곳에서는 지도를 펼칠 수 없다", 1.8)
                G.play("deny")
                return g
            if inworld and ui == "map":
                n = len(active_warps(g))
                if k in (pygame.K_UP, pygame.K_w) and n:
                    g["wcur"] = (g.get("wcur", 0) - 1) % n
                    G.play("ui")
                    return g
                if k in (pygame.K_DOWN, pygame.K_s) and n:
                    g["wcur"] = (g.get("wcur", 0) + 1) % n
                    G.play("ui")
                    return g
                if k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    do_warp(g)
                    return g
            elif inworld and ui is None and k == pygame.K_e and not G.near_npc(g):
                w = near_warp(g)
                if w:
                    if w["id"] not in g["wact"]:
                        activate(g, w)
                    else:
                        act = active_warps(g)
                        g["wcur"], g["ui"] = act.index(w), "map"
                        G.play("ui")
                    return g
        return old(g, k)
    return f


def hud_wrap(old):
    def f(screen, font, g, u):
        old(screen, font, g, u)
        if g["zid"] == WID and g["ui"] is None and g["mode"] == "play":
            w = near_warp(g)
            if w:
                s = "[E] 워프포인트 활성화" if w["id"] not in g["wact"] else "[E] 지도 열기 · 워프 이동"
                hw = font.size(s)[0] + 18 * u
                SW, SH = G.W * u, G.H * u
                G.plate(screen, (SW - hw) // 2, SH - 25 * u, hw, 11 * u, u)
                G.txt(screen, font, s, SW // 2, SH - 24 * u, (150, 245, 245), True, u)
    return f


# ================================================================= 저장 / 불러오기 / 목표
def restore(g, d):
    g["wact"] = set(d.get("warps", [])) | {"home"}
    arena = dict(west="boss_w", east="boss_e", north="boss_n")
    for z in g["pz"]:                                           # 푸리고 열린 방(옛 저장은 구역 이름으로 기록)은 다시 연다
        if z["pid"] in g["solved"] or arena[z["pid"]] in g["cleared"]:
            z["done"] = True
            for s in z["sw"]:
                s["on"] = True
            g["solid"] -= z["gate"]
    if g["topen"]:
        g["solid"] -= g["tgate"]


def save_wrap(old):
    def f(g, quiet=False):
        if quiet and not g.get("autosave_ok"):
            return
        old(g, quiet)
        try:
            with open(UI.SAVE, encoding="utf-8") as fh:
                d = json.load(fh)
            d["warps"] = sorted(g.get("wact", ()))
            with open(UI.SAVE, "w", encoding="utf-8") as fh:
                json.dump(d, fh, ensure_ascii=False)
        except (OSError, ValueError):
            pass
    return f


def load_wrap(old):
    def f():
        g = old()
        d = {}
        try:
            with open(UI.SAVE, encoding="utf-8") as fh:
                d = json.load(fh)
        except (OSError, ValueError):
            pass
        restore(g, d)
        return g
    return f


def objective_wrap(old):
    def f(g):
        if g["zid"] != WID:
            return old(g)
        keys, zn = g["keys"], G.ZONES
        if keys >= 3:
            return ("열린 문으로 들어가 전송문을 타라" if g["reg"] in (4,) else
                    "사원의 문이 열렸다! 월드 중앙의 황혼의 사원으로 가서 핵에 맞서라")
        for pid, arena in (("west", "boss_w"), ("east", "boss_e"), ("north", "boss_n")):
            if arena in g["cleared"]:
                continue
            z = next((q for q in g["pz"] if q["pid"] == pid), None)
            if z and not z["done"]:
                return f"{zn[pid]['name']}의 스위치 퍼즐을 풀어 수호 기계의 방을 열어라 (열쇠 {keys}/3)"
            return f"{zn[pid]['name']}의 수호 기계를 쓰러뜨려라 (열쇠 {keys}/3)"
        return "사원으로 가라"
    return f


# ================================================================= 설치
def install(g_mod, cfg, boss_mod, world_mod, ui_mod):
    global G, C, W, UI
    G, C, W, UI = g_mod, cfg, world_mod, ui_mod
    wt, ht, _, _ = params()
    lay = layout(wt, ht)
    Z = G.ZONES
    Z[WID] = dict(name="폐허의 대지", reg=0, size=(wt, ht), npcs=[], roads=[], exits=[], river=None, portals=[], n={})
    Z["field"]["start"] = (lay["vil"][0] + 10, lay["vil"][1] + 7)
    for k in ("west", "east", "north"):                         # 보스방 클리어 후 돌아올 좌표 = 월드 좌표의 수호 기계의 방
        Z[k]["lair"] = lay["lairs"][k]
    Z["temple"]["temple"] = lay["temple"]
    W.SPRITES["warp"] = (16, 24, spr_warp)
    W.LIGHT_COL["warp"] = ((120, 232, 232), 42)
    G.ZK = tuple(G.ZK) + tuple(k for k in EXTRA if k not in G.ZK)
    G.tile_reg, G.tile_style, G.player_reg, G.draw_cliff = tile_reg, tile_style, player_reg, draw_cliff

    old_build, old_load, old_arena = G.build_zone, G.load_zone, G.draw_arena

    def build_zone(zid):
        if zid == WID or zid in LEGACY:
            return take_world()
        return old_build(zid)

    def load_zone(g, zid, tx, ty):
        if zid in LEGACY:
            zid = WID
        g.setdefault("wact", {"home"})
        g.setdefault("wcur", 0)
        old_load(g, zid, tx, ty)
        z = g["zones"].get(g["zid"]) or {}
        for k in EXTRA:
            g[k] = z.get(k)
        g["_rc"], g["_amb"] = None, None
        if g["zid"] == WID and g["topen"]:
            g["solid"] -= g["tgate"]

    def hit_switch(g, z, s):
        old_sw(g, z, s)
        if z["done"] and z.get("pid"):
            g["solved"].discard(WID)
            g["solved"].add(z["pid"])

    old_sw = G.hit_switch
    G.build_zone, G.load_zone, G.hit_switch = build_zone, load_zone, hit_switch
    G.draw_arena = draw_arena_wrap(old_arena)
    W.lighting = lighting_wrap(W.lighting)
    W.mm_base = G.mm_base = mm_base_wrap(W.mm_base)
    G.on_key = on_key_wrap(G.on_key)
    G.hud = hud_wrap(G.hud)
    UI.draw_map = draw_map
    UI.minimap_surface = minimap_wrap(UI.minimap_surface)
    UI.objective = objective_wrap(UI.objective)
    UI.save_game = save_wrap(UI.save_game)
    UI.load_game = load_wrap(UI.load_game)
    G.save_game, G.load_game = UI.save_game, UI.load_game
    W.V["save"] = UI.save_game
    old_title = UI.draw_title

    def draw_title(screen, font, u, t, sel, items, help_on):
        old_title(screen, font, u, t, sel, items, help_on)
        start_build()                                           # 타이틀에 있는 동안 다음 월드를 미리 만들어 둔다
        th = _PRE["th"]
        if th is not None and th.is_alive():
            G.txt(screen, font, "세계를 만드는 중" + "." * (int(t * 2) % 4), G.W * u // 2, G.H * u - 24 * u, G.GOLD, True, u)
    UI.draw_title = G.draw_title = draw_title
    start_build()