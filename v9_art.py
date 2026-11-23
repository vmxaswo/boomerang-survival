"""v9 아트 패스 모듈 (v9_art.py)
 - 장식 스프라이트(오벨리스크·석상·톱니·가로등·결정·잔해·기둥·워프 받침)를 명암·이끼·룬 빛이 있는 그림으로 교체
 - 중앙 사원 정면: 돌 블록 질감, 위쪽 빛, 아래쪽 이끼, 늘어진 덩굴
 - 산(절벽): 지층 줄무늬, 윗면 풀 가장자리, 아래쪽 그림자
 - 월드 지도: 점 대신 핀(마커) 모양으로 표시
 - 화면 전체: 가장자리가 어두워지는 비네팅
이 모듈은 v9_open.install 뒤, 가장 마지막에 설치한다.
    import v9_art
    v9_art.install(G, C, v9_world, v9_open, v9_ui)
"""
import math

import pygame

D = pygame.draw
SC = pygame.SRCALPHA
G = C = W = O = UI = None
_CACHE = {}


def sh(c, d):
    return tuple(max(0, min(255, v + d)) for v in c)


def mixc(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def hn(x, y):
    return ((x * 73856093) ^ (y * 19349663)) & 255


# ================================================================= 장식 스프라이트
STONE = (128, 128, 156)
CYAN, CYAN_D = (130, 240, 240), (70, 170, 190)
GOLD, GOLD_D = (232, 190, 96), (160, 116, 50)
MOSS, MOSS_D = (92, 150, 82), (60, 106, 62)


def _obelisk(s):
    D.polygon(s, sh(STONE, 30), [(3, 31), (5, 7), (8, 1), (8, 31)])
    D.polygon(s, sh(STONE, -34), [(8, 1), (11, 7), (13, 31), (8, 31)])
    D.line(s, sh(STONE, 60), (8, 1), (5, 7))
    D.polygon(s, GOLD, [(8, 0), (10, 4), (6, 4)])
    D.polygon(s, GOLD_D, [(8, 0), (10, 4), (8, 4)])
    s.fill(sh(STONE, -50), (1, 28, 14, 4))
    s.fill(sh(STONE, 10), (1, 28, 14, 1))
    for y in (10, 15, 20, 25):                                  # 빛나는 룬
        s.fill(CYAN, (6, y, 1, 3))
        s.fill(CYAN_D, (9, y + 1, 1, 2))
        s.fill((255, 255, 255), (6, y, 1, 1))
    s.fill(sh(STONE, -60), (10, 12, 1, 4))                      # 금
    s.fill(sh(STONE, -60), (9, 16, 1, 2))
    s.fill(MOSS, (2, 26, 5, 2))
    s.fill(MOSS_D, (2, 27, 3, 1))
    s.fill(MOSS, (11, 25, 2, 3))


def _statue(s):
    s.fill(sh(STONE, -40), (2, 27, 12, 4))
    s.fill(sh(STONE, 0), (3, 25, 10, 3))
    s.fill(sh(STONE, 30), (3, 25, 10, 1))
    D.polygon(s, sh(STONE, 24), [(5, 26), (6, 13), (8, 13), (8, 26)])
    D.polygon(s, sh(STONE, -22), [(8, 13), (10, 13), (11, 26), (8, 26)])
    D.circle(s, sh(STONE, 30), (8, 9), 4)
    D.circle(s, sh(STONE, -10), (9, 10), 3)
    s.fill(GOLD, (6, 8, 4, 1))                                  # 눈가리개 장식
    D.line(s, sh(STONE, 6), (10, 15), (13, 10), 2)              # 들어 올린 팔
    D.circle(s, CYAN_D, (13, 7), 3)
    D.circle(s, CYAN, (13, 7), 2)
    s.fill((255, 255, 255), (13, 6, 1, 1))
    s.fill(CYAN, (7, 17, 2, 3))
    s.fill(MOSS, (3, 26, 3, 2))


def _gear(s):
    rim, body = (170, 164, 150), (112, 104, 112)
    for i in range(10):
        a = i * 0.6283
        D.circle(s, sh(rim, -20), (11 + int(math.cos(a) * 10), 11 + int(math.sin(a) * 10)), 2)
    D.circle(s, sh(body, -30), (11, 11), 9)
    D.circle(s, rim, (11, 11), 8)
    D.circle(s, body, (11, 11), 6)
    for i in range(4):
        a = i * 1.5708 + 0.4
        D.line(s, sh(rim, -10), (11, 11), (11 + int(math.cos(a) * 7), 11 + int(math.sin(a) * 7)), 2)
    D.circle(s, (60, 56, 76), (11, 11), 3)
    D.circle(s, CYAN, (11, 11), 1)
    s.fill((196, 120, 70), (4, 15, 3, 2))                       # 녹
    s.fill(MOSS, (14, 4, 3, 2))


def _lamp(s):
    iron = (62, 58, 82)
    s.fill(iron, (4, 9, 2, 14))
    s.fill(sh(iron, 30), (4, 9, 1, 14))
    s.fill(sh(iron, -10), (2, 21, 6, 3))
    s.fill(sh(iron, 20), (3, 20, 4, 1))
    D.polygon(s, GOLD, [(0, 4), (5, 0), (10, 4)])
    D.polygon(s, GOLD_D, [(5, 0), (10, 4), (5, 4)])
    s.fill((255, 226, 150), (1, 4, 8, 6))
    s.fill((255, 248, 214), (3, 5, 4, 4))
    D.rect(s, GOLD_D, (0, 4, 10, 7), 1)
    s.fill(GOLD_D, (4, 4, 1, 7))


def _crystal(s):
    s.fill((70, 70, 104), (1, 21, 14, 3))
    s.fill((100, 100, 134), (2, 20, 12, 1))
    D.polygon(s, (70, 110, 210), [(1, 22), (2, 13), (4, 10), (6, 14), (6, 22)])
    D.polygon(s, (170, 130, 240), [(10, 22), (11, 12), (13, 9), (15, 13), (15, 22)])
    D.polygon(s, (86, 150, 236), [(4, 22), (6, 8), (9, 1), (12, 8), (12, 22)])
    D.polygon(s, (160, 214, 255), [(9, 1), (12, 8), (12, 22), (9, 22)])
    D.polygon(s, (220, 244, 255), [(9, 1), (10, 6), (9, 6)])
    s.fill((255, 255, 255), (7, 8, 1, 5))


def _husk(s):
    metal = (104, 108, 132)
    s.fill(sh(metal, -30), (2, 8, 11, 5))
    s.fill(metal, (1, 4, 12, 6))
    s.fill(sh(metal, 36), (1, 4, 12, 1))
    D.circle(s, sh(metal, -20), (10, 5), 3)
    s.fill((230, 70, 70), (10, 4, 2, 1))                        # 꺼져 가는 눈
    s.fill((60, 64, 90), (3, 10, 2, 3))
    s.fill(sh(metal, 40), (5, 1, 3, 3))
    D.line(s, (200, 70, 70), (3, 5), (1, 9))                    # 끊어진 선
    s.fill((255, 226, 100), (1, 9, 1, 1))
    s.fill(MOSS, (7, 9, 4, 2))


def _pillar(s):
    st = (170, 164, 186)
    s.fill(sh(st, -50), (2, 26, 12, 4))
    s.fill(sh(st, -20), (3, 24, 10, 2))
    s.fill(st, (4, 8, 8, 17))
    s.fill(sh(st, 34), (4, 8, 3, 17))
    s.fill(sh(st, -34), (10, 8, 2, 17))
    for fx in (7, 9):
        s.fill(sh(st, -14), (fx, 9, 1, 15))
    s.fill(sh(st, 20), (2, 5, 12, 3))
    s.fill(sh(st, -20), (2, 7, 12, 1))
    D.polygon(s, st, [(3, 5), (5, 1), (8, 3), (10, 0), (13, 5)])  # 부서진 윗부분
    D.polygon(s, sh(st, -30), [(8, 3), (10, 0), (13, 5), (9, 5)])
    s.fill(CYAN, (7, 13, 2, 4))
    s.fill(CYAN_D, (7, 18, 2, 1))
    for y in (11, 15, 19, 23):                                  # 덩굴
        s.fill(MOSS, (4, y, 2, 2))
    s.fill(MOSS_D, (4, 12, 1, 12))


def _warp(s):
    st = (150, 148, 176)
    s.fill(sh(st, -60), (1, 21, 14, 3))
    s.fill(sh(st, -34), (2, 18, 12, 3))
    s.fill(sh(st, 0), (3, 15, 10, 3))
    s.fill(sh(st, 34), (3, 15, 10, 1))
    D.ellipse(s, CYAN_D, (3, 17, 10, 4), 1)                     # 새겨진 룬 고리
    for x in (4, 7, 10):
        s.fill(CYAN, (x, 20, 1, 1))
    s.fill(sh(st, -20), (6, 12, 4, 3))
    s.fill(CYAN, (7, 12, 2, 1))


def _tex_facade(old):
    def f():
        s = old()
        w, h = s.get_size()
        for y in range(h):
            for x in range(w):
                r, g, b, a = s.get_at((x, y))
                if a == 0 or (76 <= x < 132 and 106 <= y < 192):
                    continue
                n = hn(x // 2, y // 2) % 9 - 4
                d = n + int((1 - y / h) * 14) - 4              # 위쪽이 밝다
                if (x + (y // 12 % 2) * 14) % 28 == 0 and y % 12:
                    d -= 20                                    # 엇갈린 돌 이음새
                if y > 150 and hn(x // 3, y // 3) > 190:       # 아래쪽 이끼
                    s.set_at((x, y), (*mixc((r, g, b), MOSS, 0.7), a))
                    continue
                s.set_at((x, y), (max(0, min(255, r + d)), max(0, min(255, g + d)), max(0, min(255, b + d)), a))
        for vx, ln in ((36, 48), (62, 30), (146, 44), (172, 26), (6, 60), (196, 56)):   # 늘어진 덩굴
            for i in range(ln):
                y = 60 + i
                if 76 <= vx < 132 and y > 106:
                    break
                s.fill(MOSS_D if i % 5 else MOSS, (vx + int(math.sin(i * 0.4) * 1.5), y, 1, 1))
                if i % 6 == 3:
                    s.fill(MOSS, (vx - 1, y, 3, 1))
        return s
    return f


# ================================================================= 산(절벽)
def draw_cliff(surf, g, tx, ty, px, py, r):
    h, ter = G.hsh(tx, ty), g["ter"]
    base = G.adj(r["wall"], int((g["shade"][ty][tx] - 0.5) * 46) + h % 5 - 2)
    surf.fill(base, (px, py, G.T, G.T))
    up = ty == 0 or ter[ty - 1][tx] == 8
    dn = ty + 1 >= g["ht"] or ter[ty + 1][tx] == 8
    lf = tx == 0 or ter[ty][tx - 1] == 8
    rt = tx + 1 >= g["wt"] or ter[ty][tx + 1] == 8
    for i in range(4):                                          # 지층: 가로로 흐르는 띠
        yy = py + 2 + i * 4 + (hn(tx, ty + i) % 3 - 1)
        surf.fill(G.adj(base, -10 if i % 2 else 8), (px, yy, G.T, 2))
    if not up:                                                  # 윗면: 빛 + 풀 가장자리
        surf.fill(G.adj(base, 42), (px, py, G.T, 3))
        leaf = r["leaf"]
        for i in range(0, G.T, 2):
            surf.fill(G.adj(leaf, -10 + hn(tx * 16 + i, ty) % 24), (px + i, py, 2, 1 + hn(tx + i, ty) % 3))
    if not dn:                                                  # 아랫면: 절벽 그림자
        surf.fill(G.adj(base, -46), (px, py + 9, G.T, 7))
        surf.fill(G.adj(base, -76), (px, py + 14, G.T, 2))
    if not lf:
        surf.fill(G.adj(base, 20), (px, py, 1, G.T))
    if not rt:
        surf.fill(G.adj(base, -30), (px + G.T - 1, py, 1, G.T))
    if h % 4 == 0:
        surf.fill(G.adj(base, -40), (px + 3 + h % 8, py + 5 + h % 5, 1, 5))   # 갈라진 금
    if h % 6 == 1:
        surf.fill(G.adj(base, 28), (px + 5 + h % 6, py + 7, 3, 2))             # 반짝이는 돌 조각
    if h % 9 == 2 and not dn:
        surf.fill((*G.adj(r["leaf"], -20),), (px + 2 + h % 10, py + 10, 3, 2))  # 바위 위 이끼


# ================================================================= 지도 마커(핀)
def pin(screen, x, y, u, col, inner=(255, 255, 255), size=1.0):
    k = max(1, int(u * size))
    D.polygon(screen, G.INK, [(x - 3 * k, y - 5 * k), (x + 3 * k, y - 5 * k), (x, y)])
    D.circle(screen, G.INK, (x, y - 6 * k), int(4.4 * k))
    D.polygon(screen, col, [(x - 2 * k, y - 5 * k), (x + 2 * k, y - 5 * k), (x, y - u)])
    D.circle(screen, col, (x, y - 6 * k), int(3.4 * k))
    D.circle(screen, sh(col, 70), (x - k, y - 7 * k), max(1, k))
    D.circle(screen, inner, (x, y - 6 * k), max(1, int(1.3 * k)))


def map_wrap(old):
    def f(screen, font, g, u):
        old(screen, font, g, u)
        if g["zid"] != O.WID:
            return
        try:
            SW, SH = G.W * u, G.H * u
            pw, ph = int(SW * 0.94), 246 * u
            px, py = (SW - pw) // 2, (SH - ph) // 2
            wt, ht = g["wt"], g["ht"]
            kx = min((pw / u - 24 - 150) / wt, (ph / u - 38) / ht)
            mx, my = px + 12 * u, py + 22 * u
            seen = W.mm_base(g)[2]

            def pt(tx, ty):
                return mx + int((tx + 0.5) * kx * u), my + int((ty + 0.5) * kx * u)
            m, tp = g["meta"], g["meta"]["temple"]
            for (tx, ty), col, size in ((((m["vil"][0] + m["vil"][2]) // 2, (m["vil"][1] + m["vil"][3]) // 2), (255, 206, 90), 1.2),
                                        (((tp[0] + tp[2]) // 2, (tp[1] + tp[3]) // 2), (255, 170, 60), 1.3)):
                if (tx, ty) in seen:
                    pin(screen, *pt(tx, ty), u, col, size=size)
            for lr in m["lairs"].values():
                tx, ty = (lr[0] + lr[2]) // 2, (lr[1] + lr[3]) // 2
                if (tx, ty) in seen:
                    pin(screen, *pt(tx, ty), u, (235, 80, 80), (60, 10, 20))
            act = O.active_warps(g)
            cur = int(max(0, min(g.get("wcur", 0), max(0, len(act) - 1))))
            for w in g["warps"]:
                p = pt(w["tx"], w["ty"])
                if w["id"] in g["wact"]:
                    sel = bool(act) and act[cur] is w
                    pin(screen, *p, u, (255, 255, 255) if sel else (90, 220, 230), (20, 80, 100), 1.0 if sel else 0.8)
                elif (w["tx"], w["ty"]) in seen:
                    pin(screen, *p, u, (110, 116, 140), (60, 64, 84), 0.6)
        except Exception:
            G.v9_log("art-map")
    return f


# ================================================================= 분위기: 비네팅
def vignette():
    if "v" not in _CACHE:
        sw, sh_ = 64, 36
        s = pygame.Surface((sw, sh_), SC)
        for y in range(sh_):
            for x in range(sw):
                d = math.hypot((x / sw - 0.5) * 1.25, (y / sh_ - 0.5) * 1.5)
                s.set_at((x, y), (10, 6, 24, int(max(0.0, min(1.0, (d - 0.38) / 0.5)) * 120)))
        _CACHE["v"] = pygame.transform.smoothscale(s, (G.W, G.H))
    return _CACHE["v"]


def draw_wrap(old):
    def f(surf, g):
        old(surf, g)
        try:
            if g.get("mode") == "play":
                surf.blit(vignette(), (0, 0))
        except Exception:
            G.v9_log("art-vignette")
    return f


# ================================================================= 설치
def install(g_mod, cfg, world_mod, open_mod, ui_mod):
    global G, C, W, O, UI
    G, C, W, O, UI = g_mod, cfg, world_mod, open_mod, ui_mod
    for k, (w, h, fn) in dict(obelisk=(16, 32, _obelisk), statue=(16, 32, _statue), gear=(22, 22, _gear),
                              lamp=(10, 24, _lamp), crystal=(16, 24, _crystal), husk=(14, 14, _husk),
                              pillar=(16, 30, _pillar), warp=(16, 24, _warp)).items():
        W.SPRITES[k] = (w, h, fn)
    W._SPC.clear()
    W.LIGHT_COL["pillar"] = ((120, 232, 232), 16)
    W._FAC.clear()
    W._FAC["f"] = _tex_facade(W.make_facade)()                  # 질감 입힌 사원 정면을 미리 만들어 캐시에 넣는다
    G.draw_cliff = draw_cliff
    UI.draw_map = map_wrap(UI.draw_map)
    G.draw = draw_wrap(G.draw)