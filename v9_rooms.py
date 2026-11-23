"""v9 보스방 내부 모듈 (v9_rooms.py) - 보스방 안을 바깥 건물과 같은 테마로 꾸민다
 - 수문장의 성문 (boss_w) : 큰 판석 바닥, 문에서 이어지는 붉은 융단, 북쪽 벽의 깃발, 벽 횃불, 석조 기둥
 - 연금 제련소 (boss_e)   : 리벳 철판 바닥, 가장자리 경고 줄무늬, 초록빛 배수구, 벽 파이프, 기계 기둥, 모서리 약품 탱크
 - 과열 보일러실 (boss_n) : 왼쪽은 달아오른 균열, 오른쪽은 성에 낀 철판, 벽 보일러관, 보일러 탱크 기둥, 모서리 불·얼음
 바닥·벽은 처음 그릴 때 방 전체를 한 장으로 만들어 두고(캐시), 움직이는 빛만 매 프레임 그린다.
 전투 판정은 건드리지 않는다 (막힌 칸·열린 칸은 그대로, 그림만 바뀐다).
game_v9.build() 에서 v9_sites 다음에 설치한다."""
import math
import random

import pygame

D = pygame.draw
SC = pygame.SRCALPHA
G = W = None
ROOM = dict(boss_w="fort", boss_e="factory", boss_n="boiler")
AMB = {"fort": (70, 30, 20, 60), "factory": (10, 40, 20, 85), "boiler": (24, 12, 40, 100)}
PILLARS = ((8, 7), (25, 7), (8, 15), (25, 15))
CORNERS = ((4, 4), (29, 4), (4, 19), (29, 19))                      # topdown_rpg.build_arena 의 모서리 화로 자리
_C = {}


def props_for(kind):
    """화로 대신 놓이는 테마 소품: 공장 = 네 모서리 약품 탱크, 보일러 = 오른쪽 두 모서리 얼음 결정"""
    if kind == "factory":
        return [("rvat", x, y) for x, y in CORNERS]
    if kind == "boiler":
        return [("rice", x, y) for x, y in CORNERS if x > 16]
    return []


def lerp(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def adj(c, d):
    return tuple(max(0, min(255, v + d)) for v in c)


# ================================================================= 바닥 · 벽 (한 장으로)
def _floor_fort(s, x, y, h):
    base = (148, 136, 140) if ((x // 2) + (y // 2)) % 2 else (138, 126, 132)
    s.fill(adj(base, h % 7 - 3), (x * 16, y * 16, 16, 16))
    if x % 2 == 0:
        s.fill((96, 86, 94), (x * 16, y * 16, 1, 16))
    if y % 2 == 0:
        s.fill((96, 86, 94), (x * 16, y * 16, 16, 1))
    if h % 11 == 0:
        D.line(s, (110, 100, 108), (x * 16 + 3, y * 16 + 4), (x * 16 + 11, y * 16 + 12), 1)


def _floor_factory(s, x, y, h):
    s.fill(adj((92, 96, 108), h % 5 - 2), (x * 16, y * 16, 16, 16))
    s.fill((70, 72, 86), (x * 16, y * 16 + 15, 16, 1))
    s.fill((70, 72, 86), (x * 16 + 15, y * 16, 1, 16))
    s.fill((122, 126, 140), (x * 16, y * 16, 16, 1))
    if (x + y) % 2 == 0:
        for px, py in ((2, 2), (13, 2), (2, 13), (13, 13)):
            s.fill((140, 144, 160), (x * 16 + px, y * 16 + py, 1, 1))


def _floor_boiler(s, x, y, h, wt):
    f = x / max(1, wt - 1)
    base = lerp((92, 66, 62), (78, 92, 116), f)
    s.fill(adj(base, h % 5 - 2), (x * 16, y * 16, 16, 16))
    s.fill(adj(base, -22), (x * 16, y * 16 + 15, 16, 1))
    s.fill(adj(base, -22), (x * 16 + 15, y * 16, 1, 16))
    if f > 0.55 and h % 3 == 0:                                     # 성에
        for i in range(3):
            s.fill((210, 230, 250), (x * 16 + (h >> i) % 13, y * 16 + (h >> (i + 2)) % 13, 2, 1))


def _wall(s, kind, x, y, h):
    px, py = x * 16, y * 16
    if kind == "fort":
        s.fill((96, 86, 98), (px, py, 16, 16))
        for j, yy in enumerate((0, 8)):
            s.fill((70, 62, 74), (px, py + yy, 16, 1))
            s.fill((70, 62, 74), (px + (0 if j else 8), py + yy, 1, 8))
        s.fill((124, 114, 126), (px, py + 1, 16, 1))
    elif kind == "factory":
        s.fill((120, 62, 52), (px, py, 16, 16))
        for j, yy in enumerate((0, 5, 10)):
            s.fill((82, 40, 38), (px, py + yy, 16, 1))
            s.fill((82, 40, 38), (px + (4 if j % 2 else 10), py + yy, 1, 5))
    else:
        s.fill((56, 54, 72), (px, py, 16, 16))
        s.fill((40, 38, 52), (px, py + 15, 16, 1))
        s.fill((80, 78, 98), (px, py, 16, 1))
        s.fill((150, 146, 168), (px + 3, py + 3, 1, 1))
        s.fill((150, 146, 168), (px + 12, py + 3, 1, 1))
    if h % 9 == 0:
        s.fill((60, 56, 70), (px + 4, py + 9, 6, 1))


def _pillar(s, kind, px, py):
    """2x2 기둥 (32x32) 윗면"""
    if kind == "fort":
        D.rect(s, (70, 62, 74), (px, py, 32, 32))
        D.rect(s, (150, 142, 168), (px + 2, py + 2, 28, 28))
        D.rect(s, (190, 182, 206), (px + 2, py + 2, 28, 4))
        s.fill((214, 170, 86), (px + 2, py + 20, 28, 2))
        D.polygon(s, (140, 44, 38), [(px + 11, py + 8), (px + 21, py + 8), (px + 21, py + 18), (px + 16, py + 15), (px + 11, py + 18)])
    elif kind == "factory":
        D.rect(s, (34, 32, 44), (px, py, 32, 32))
        D.rect(s, (84, 82, 100), (px + 2, py + 2, 28, 28))
        D.rect(s, (120, 118, 138), (px + 2, py + 2, 28, 3))
        D.rect(s, (20, 40, 30), (px + 7, py + 9, 18, 10))
        s.fill((214, 170, 86), (px + 2, py + 26, 28, 2))
    else:
        D.rect(s, (34, 32, 44), (px, py, 32, 32))
        D.circle(s, (110, 104, 128), (px + 16, py + 16), 14)
        D.circle(s, (150, 144, 168), (px + 13, py + 12), 6)
        for a in range(8):
            r = a * 0.785
            s.fill((214, 170, 86), (px + 16 + int(math.cos(r) * 13), py + 16 + int(math.sin(r) * 13), 2, 2))
        D.circle(s, (230, 226, 210), (px + 16, py + 16), 4)
        D.line(s, (200, 40, 40), (px + 16, py + 16), (px + 18, py + 13), 1)


def room_surface(g, kind):
    key = ("room", g["zid"])
    if key in _C:
        return _C[key]
    wt, ht, T = g["wt"], g["ht"], G.T
    s = pygame.Surface((wt * T, ht * T), SC)
    solid, door = g["solid"], set(G.ARENA_DOOR)
    ptiles = {(px + i, py + j) for px, py in PILLARS for i in (0, 1) for j in (0, 1)}
    props = [d for d in g["deco"] if d[0] == "brazier"] + props_for(kind)
    btiles = {(int(d[1]), int(d[2])) for d in props}
    for y in range(ht):
        for x in range(wt):
            h = G.hsh(x, y)
            if (x, y) in door:                                      # 보스방 문은 원래 그림(봉인 문)을 그대로 보인다
                continue
            if (x, y) in solid and (x, y) not in ptiles and (x, y) not in btiles:
                _wall(s, kind, x, y, h)
                continue
            if kind == "fort":
                _floor_fort(s, x, y, h)
            elif kind == "factory":
                _floor_factory(s, x, y, h)
            else:
                _floor_boiler(s, x, y, h, wt)
    if kind == "fort":                                              # 붉은 융단: 문에서 보스 자리까지
        x0, x1 = 15 * T + 4, 20 * T - 4
        s.fill((96, 24, 28), (x0, 3 * T, x1 - x0, 25 * T - 3 * T))
        s.fill((150, 40, 40), (x0 + 3, 3 * T, x1 - x0 - 6, 22 * T))
        s.fill((214, 170, 86), (x0 + 1, 3 * T, 2, 22 * T))
        s.fill((214, 170, 86), (x1 - 3, 3 * T, 2, 22 * T))
        for yy in range(3 * T + 8, 25 * T, 24):
            D.polygon(s, (214, 170, 86), [(17 * T + 8, yy - 4), (17 * T + 12, yy), (17 * T + 8, yy + 4), (17 * T + 4, yy)])
        for bx in range(3, wt - 3, 4):                              # 북쪽 벽 깃발
            px = bx * T + 2
            D.polygon(s, (120, 36, 32), [(px, 2), (px + 12, 2), (px + 12, 26), (px + 6, 21), (px, 26)])
            D.polygon(s, (170, 58, 48), [(px, 2), (px + 5, 2), (px + 5, 23), (px, 26)])
            s.fill((214, 170, 86), (px - 1, 1, 14, 2))
            D.circle(s, (214, 170, 86), (px + 6, 11), 3, 1)
    elif kind == "factory":                                         # 가장자리 경고 줄무늬 + 북쪽 벽 파이프 + 배수구
        for x in range(1, wt - 1):
            for y in (1, 22):
                for i in range(0, 16, 8):
                    D.polygon(s, (220, 180, 40), [(x * T + i, y * T + (12 if y == 1 else 0)), (x * T + i + 4, y * T + (12 if y == 1 else 0)),
                                                  (x * T + i + 8, y * T + (16 if y == 1 else 4)), (x * T + i + 4, y * T + (16 if y == 1 else 4))])
        for yy, c in ((3, (70, 68, 86)), (9, (96, 92, 110))):
            s.fill(c, (T, yy, (wt - 2) * T, 5))
            s.fill(adj(c, 30), (T, yy, (wt - 2) * T, 1))
        for x in range(2, wt - 2, 5):
            s.fill((150, 108, 56), (x * T, 1, 4, 14))
            D.circle(s, (180, 60, 50), (x * T + 10, 6), 4, 1)
        for gx, gy in ((5, 11), (28, 11), (17, 19), (12, 5), (22, 5)):
            D.rect(s, (20, 22, 26), (gx * T + 2, gy * T + 2, 12, 12))
            for i in range(4, 14, 3):
                s.fill((60, 160, 90), (gx * T + i, gy * T + 4, 1, 8))
    else:                                                           # 보일러: 가운데 이음매 + 벽 관 (왼쪽 달아오름, 오른쪽 고드름)
        s.fill((40, 38, 52), (wt * T // 2 - 1, T, 2, 22 * T))
        s.fill((150, 70, 50), (T, 4, (wt // 2 - 1) * T, 6))
        s.fill((255, 150, 90), (T, 4, (wt // 2 - 1) * T, 1))
        s.fill((120, 160, 210), (wt * T // 2, 4, (wt // 2 - 1) * T, 6))
        s.fill((230, 245, 255), (wt * T // 2, 4, (wt // 2 - 1) * T, 1))
        for x in range(wt * T // 2, (wt - 1) * T, 7):
            D.polygon(s, (220, 240, 255), [(x, 10), (x + 3, 10), (x + 1, 15 + (x % 5))])
        D.circle(s, (40, 38, 52), (17 * T + 8, 11 * T + 8), 40, 3)        # 가운데 화실 쇠살대
        for i in range(-32, 33, 8):
            s.fill((40, 38, 52), (17 * T + 8 + i - 1, 11 * T + 8 - 30, 2, 60))
    for px, py in PILLARS:
        _pillar(s, kind, px * T, py * T)
    for d in props:                                                 # 모서리: 화로 받침 / 약품 탱크 / 얼음 결정
        x, y = int(d[1]) * T, int(d[2]) * T
        if d[0] == "rvat":
            s.fill((60, 58, 76), (x + 1, y + 1, 14, 15))
            s.fill((70, 200, 110), (x + 3, y + 4, 10, 10))
            s.fill((180, 255, 210), (x + 4, y + 5, 1, 8))
            s.fill((214, 170, 86), (x + 1, y + 2, 14, 1))
        elif d[0] == "rice":
            D.polygon(s, (150, 210, 255), [(x + 2, y + 15), (x + 5, y + 4), (x + 8, y), (x + 11, y + 4), (x + 14, y + 15)])
            D.polygon(s, (220, 240, 255), [(x + 8, y), (x + 11, y + 4), (x + 14, y + 15), (x + 8, y + 15)])
        else:
            s.fill((70, 62, 74), (x + 2, y + 6, 12, 10))
            s.fill((150, 108, 56), (x + 1, y + 5, 14, 3))
            s.fill((214, 170, 86), (x + 1, y + 5, 14, 1))
    _C[key] = s
    return s


def draw_room(surf, g, cx, cy):
    kind = ROOM.get(g.get("zid"))
    if not kind:
        return
    surf.blit(room_surface(g, kind), (-cx, -cy))
    t, T = g["t"], G.T
    if kind == "boiler":                                            # 왼쪽 바닥 균열이 숨 쉬듯 달아오른다
        p = 0.5 + 0.5 * math.sin(t * 2.2)
        rng = random.Random(7)
        for _ in range(26):
            x, y = rng.randint(2, 15), rng.randint(2, 21)
            px, py = x * T + rng.randint(0, 10) - cx, y * T + rng.randint(0, 10) - cy
            c = lerp((120, 40, 30), (255, 150, 70), p * rng.random())
            D.line(surf, c, (px, py), (px + rng.randint(-6, 6), py + rng.randint(2, 8)), 1)
    elif kind == "factory":                                         # 배수구 초록빛
        for gx, gy in ((5, 11), (28, 11), (17, 19), (12, 5), (22, 5)):
            a = int(60 + 50 * math.sin(t * 2 + gx))
            gl = pygame.Surface((20, 20), SC)
            D.circle(gl, (90, 255, 140, a), (10, 10), 9)
            surf.blit(gl, (gx * T - 2 - cx, gy * T - 2 - cy))
    elif kind == "fort":                                            # 벽 횃불
        for y in (5, 11, 17):
            for x in (1, 32):
                px, py = x * T + 8 - cx, y * T + 4 - cy
                fl = int(math.sin(t * 11 + y + x) * 1.5)
                D.circle(surf, (255, 120, 50), (px, py), 3 + fl)
                D.circle(surf, (255, 210, 110), (px, py), 1)
    for d in props_for(kind):                                       # 모서리 탱크 거품 / 얼음 반짝임
        if d[0] == "rvat":
            x, y = int(d[1]) * T - cx, int(d[2]) * T - cy
            f = (t * 0.9 + d[1]) % 1.0
            surf.fill((220, 255, 220), (x + 6, y + 12 - int(f * 8), 1, 1))
        elif d[0] == "rice" and int(t * 2 + d[1]) % 4 == 0:
            surf.fill((255, 255, 255), (int(d[1]) * T + 8 - cx, int(d[2]) * T + 3 - cy, 1, 2))


def build_wrap(old):
    def f(zid):
        z = old(zid)
        kind = ROOM.get(zid)
        if kind:                                                    # 모서리 화로 중 테마 소품으로 바뀌는 것은 화로 목록에서 뺀다
            swap = {(p[1], p[2]) for p in props_for(kind)}
            z["deco"] = [d for d in z["deco"] if not (d[0] == "brazier" and (d[1], d[2]) in swap)]
        return z
    return f


def draw_arena_wrap(old):
    def f(surf, g, cx, cy):
        if ROOM.get(g.get("zid")):
            try:
                draw_room(surf, g, cx, cy)
            except Exception:
                G.v9_log("rooms-draw")
        old(surf, g, cx, cy)
    return f


def install(g_mod, world_mod):
    global G, W
    G, W = g_mod, world_mod
    for zid, kind in ROOM.items():
        z = G.ZONES[zid]
        z["arena"] = kind                                           # 옛 보스(눈·덩굴·중력) 바닥 문양과 덩굴을 끈다
        W.AMBIENT[z["reg"]] = AMB[kind]
    G.build_zone = build_wrap(G.build_zone)
    G.draw_arena = draw_arena_wrap(G.draw_arena)
