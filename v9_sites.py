"""v9 랜드마크 구역 모듈 (v9_sites.py) - 보스 사원과 중앙 사원을 '장소'로 만든다
 보스 성역 (서쪽·동쪽·북쪽 수호 기계의 방)
  - 절벽으로 둘러싼 고원 안뜰. 들어가는 길은 화로·석상이 늘어선 넓은 참배로 하나 (기존 길·스위치·워프 자리는 틈으로 남긴다)
  - 참배로가 절벽을 지나는 곳에 성문 탑 두 개 (보스 색 룬, 처치하면 금빛)
  - 보스마다 다른 안뜰 테마: 벌크스틸 = 요새(깃발·바리케이드·대포) / 알케미스트 = 공장(굴뚝 연기·약품 탱크·파이프) /
    오버히트 = 보일러실(증기 배출구·얼음 결정·화로)
 중앙 사원
  - 사원 뒤와 양옆을 절벽으로 감싸 산에 새겨진 신전처럼, 앞에는 폐허 도시 블록과 넓은 돌길
 전체
  - v9_art 의 입체 절벽 그림(draw_cliff)을 실제로 쓴다 (전에는 연결되어 있지 않아 산이 줄무늬 벽으로 보였다)
  - 지역마다 고르게 흩뿌려진 기둥·오벨리스크 같은 큰 장식은 길에서 먼 것을 절반쯤 걷어 낸다
 끝으로 마을에서 모든 목표(사원 앞·워프·스위치)에 갈 수 있는지 검사하고, 막혔으면 이 모듈이 세운 벽만 허문다.
월드가 만들어질 때 한 번 적용된다 (같은 시드면 항상 같은 결과). game_v9.build() 에서 v9_kaiju 다음에 설치한다."""
import math
import random

import pygame

D = pygame.draw
SC = pygame.SRCALPHA
G = C = W = O = L = None
ACC = {0: (250, 150, 100), 1: (130, 230, 140), 2: (180, 150, 255)}      # 벌크스틸 / 알케미스트 / 오버히트
DONE = (255, 226, 120)
THEME = dict(west=(("banner", 5, True), ("barricade", 4, True), ("cannon", 3, True), ("torch", 2, True)),
             east=(("chimney", 3, True), ("vat", 4, True), ("pipe", 4, True), ("torch", 1, True)),
             north=(("vent", 5, False), ("crystal", 4, True), ("torch", 3, True)))
def lerp(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


TALL = ("pillar", "obelisk", "crystal", "statue", "gear")
REAR, HALL = 3, 8                # 보스 건물 뒤채 깊이(타일) / 중앙 사원 본당 높이(타일)


# ================================================================= 스프라이트 (도트)
def _brazier(s):
    s.fill((60, 56, 78), (2, 19, 10, 3))
    s.fill((86, 80, 104), (4, 11, 6, 9))
    s.fill((124, 118, 142), (4, 11, 2, 9))
    D.polygon(s, (150, 108, 56), [(0, 6), (13, 6), (11, 11), (2, 11)])
    s.fill((214, 170, 86), (0, 6, 14, 1))
    s.fill((40, 24, 20), (2, 7, 10, 2))


def _banner(s):
    s.fill((70, 56, 44), (1, 2, 2, 30))
    s.fill((120, 96, 70), (1, 2, 1, 30))
    D.circle(s, (214, 170, 86), (2, 2), 2)
    D.polygon(s, (130, 44, 38), [(3, 4), (12, 4), (12, 22), (8, 18), (3, 22)])
    D.polygon(s, (170, 64, 50), [(3, 4), (7, 4), (7, 19), (3, 22)])
    s.fill((214, 170, 86), (3, 6, 9, 1))
    D.circle(s, (214, 170, 86), (8, 12), 2, 1)
    s.fill((214, 170, 86), (7, 11, 2, 2))


def _barricade(s):
    for x0, x1 in ((1, 15), (15, 1)):
        D.line(s, (60, 42, 30), (x0, 13), (x1, 3), 3)
        D.line(s, (130, 94, 62), (x0, 12), (x1, 2), 1)
    s.fill((90, 66, 46), (0, 9, 18, 3))
    s.fill((140, 104, 70), (0, 9, 18, 1))
    for x in (3, 9, 15):
        D.polygon(s, (170, 170, 186), [(x - 1, 9), (x + 1, 9), (x, 5)])


def _cannon(s):
    D.line(s, (34, 30, 42), (4, 9), (17, 3), 6)
    D.line(s, (84, 70, 64), (4, 8), (17, 2), 3)
    D.line(s, (150, 90, 60), (5, 7), (16, 2), 1)
    D.circle(s, (18, 14, 24), (17, 3), 2)
    for x in (4, 11):
        D.circle(s, (70, 52, 36), (x, 11), 3)
        D.circle(s, (130, 96, 60), (x, 11), 3, 1)
        s.fill((40, 30, 24), (x, 11, 1, 1))


def _chimney(s):
    s.fill((60, 40, 40), (2, 4, 12, 32))
    for y in range(6, 36, 4):
        s.fill((120, 64, 54) if (y // 4) % 2 else (140, 78, 62), (3, y, 10, 3))
        s.fill((76, 44, 40), (3 + (y // 4 % 2) * 4, y, 1, 3))
    s.fill((96, 92, 110), (1, 2, 14, 4))
    s.fill((140, 136, 156), (1, 2, 14, 1))
    s.fill((20, 16, 24), (4, 3, 8, 2))


def _vat(s):
    s.fill((70, 66, 86), (1, 20, 14, 4))
    s.fill((96, 92, 112), (2, 2, 12, 19))
    s.fill((150, 230, 170), (4, 4, 8, 15))
    s.fill((70, 200, 110), (4, 9, 8, 10))
    s.fill((40, 140, 80), (4, 16, 8, 3))
    s.fill((230, 255, 235), (5, 5, 1, 9))
    for y in (2, 11, 20):
        s.fill((214, 170, 86), (1, y, 14, 1))
    s.fill((60, 56, 76), (13, 6, 3, 2))


def _pipe(s):
    s.fill((60, 58, 76), (0, 3, 16, 6))
    s.fill((120, 116, 138), (0, 3, 16, 2))
    s.fill((84, 80, 100), (0, 7, 16, 2))
    for x in (1, 12):
        s.fill((150, 108, 56), (x, 2, 3, 8))
        s.fill((214, 170, 86), (x, 2, 1, 8))
    D.circle(s, (180, 60, 50), (8, 3), 3, 1)
    s.fill((180, 60, 50), (7, 0, 2, 3))


def _vent(s):
    s.fill((40, 38, 52), (0, 0, 14, 8))
    s.fill((84, 80, 100), (1, 1, 12, 6))
    for x in range(2, 13, 3):
        s.fill((24, 20, 32), (x, 2, 2, 4))
    s.fill((214, 170, 86), (0, 0, 14, 1))


def _tower(acc):
    def f(s):
        s.fill((84, 78, 104), (2, 14, 22, 34))
        s.fill((150, 142, 168), (4, 14, 18, 34))
        s.fill((204, 196, 220), (4, 14, 3, 34))
        s.fill((98, 90, 118), (19, 14, 3, 34))
        for y in range(20, 46, 6):
            s.fill((110, 102, 130), (4, y, 18, 1))
        for y in (16, 44):
            s.fill((214, 170, 86), (2, y, 22, 2))
            s.fill((150, 108, 56), (2, y + 2, 22, 1))
        s.fill((18, 14, 34), (10, 22, 6, 12))
        s.fill(acc, (11, 25, 4, 6))
        for x, w in ((1, 6), (10, 6), (19, 6)):
            s.fill((204, 196, 220), (x, 9, w, 5))
            s.fill((150, 142, 168), (x, 12, w, 2))
        s.fill((60, 56, 80), (1, 47, 24, 1))
    return f


SPRITES = dict(torch=(14, 22, _brazier), banner=(14, 32, _banner), barricade=(18, 14, _barricade),
               cannon=(20, 14, _cannon), chimney=(16, 36, _chimney), vat=(16, 24, _vat), pipe=(16, 10, _pipe),
               vent=(14, 8, _vent))
for _i, _c in ACC.items():
    SPRITES[f"gtower{_i}"] = (26, 48, _tower(_c))


# ================================================================= 보스 건물 (9 x 12 타일 = 144 x 192, 문은 아래 가운데)
GOLD, GOLD_D, GOLD_L = (214, 170, 86), (150, 108, 56), (250, 226, 150)
DOOR = pygame.Rect(48, 118, 48, 74)               # 문 구멍 (위는 반원 아치: 중심 (72,118) 반지름 24)
BW, BH = 144, 192


def _bricks(s, rect, base, mortar, bw=12, bh=6):
    x0, y0, w, h = rect
    s.fill(base, rect)
    for j, y in enumerate(range(y0, y0 + h, bh)):
        s.fill(mortar, (x0, y, w, 1))
        off = (bw // 2) * (j % 2)
        for x in range(x0 + off, x0 + w, bw):
            s.fill(mortar, (x, y, 1, bh))


def _arch(s, col, grow=0):
    D.rect(s, col, (DOOR.x - grow, DOOR.y, DOOR.w + grow * 2, DOOR.h))
    D.circle(s, col, (72, DOOR.y), 24 + grow)


def _bld_west(s):
    """수문장의 성문: 양쪽 원뿔 지붕 탑 + 성가퀴 본성 + 쇠창살 문"""
    ST, DK, LT, MO = (150, 142, 168), (88, 80, 108), (204, 196, 220), (118, 110, 138)
    s.fill((58, 52, 74), (14, 18, 116, 50))                     # 본성 윗면 (안마당 지붕)
    for y in range(22, 68, 6):
        s.fill((70, 64, 88), (14, y, 116, 1))
    D.rect(s, DK, (20, 54, 104, 138))
    _bricks(s, (22, 58, 100, 134), ST, MO)
    for x in range(20, 124, 10):                                # 성가퀴
        s.fill(DK, (x, 44, 8, 12))
        s.fill(LT, (x + 1, 44, 6, 9))
    s.fill(DK, (20, 56, 104, 2))
    for tx in (0, 108):                                         # 양쪽 탑
        D.rect(s, DK, (tx, 34, 36, 158))
        _bricks(s, (tx + 2, 36, 32, 156), ST, MO, 10, 6)
        s.fill(LT, (tx + 2, 36, 3, 156))
        s.fill(DK, (tx + 31, 36, 3, 156))
        D.polygon(s, (60, 26, 30), [(tx - 3, 36), (tx + 18, 0), (tx + 39, 36)])
        D.polygon(s, (120, 48, 44), [(tx, 35), (tx + 18, 3), (tx + 26, 35)])
        D.line(s, (160, 70, 60), (tx + 18, 3), (tx + 6, 34))
        s.fill(GOLD, (tx + 17, 0, 3, 4))
        for y in (66, 112):
            s.fill((18, 14, 34), (tx + 16, y, 4, 14))
        s.fill(GOLD, (tx, 150, 36, 3))
        s.fill(GOLD_D, (tx, 153, 36, 1))
    for bx in (36, 98):                                         # 녹슨 붉은 깃발
        D.polygon(s, (110, 36, 32), [(bx, 64), (bx + 10, 64), (bx + 10, 112), (bx + 5, 104), (bx, 112)])
        D.polygon(s, (160, 58, 46), [(bx, 64), (bx + 4, 64), (bx + 4, 108), (bx, 112)])
        s.fill(GOLD, (bx - 1, 62, 12, 2))
        D.circle(s, GOLD, (bx + 5, 80), 3, 1)
    _arch(s, DK, 6)                                             # 아치 테두리
    _arch(s, LT, 4)
    _arch(s, MO, 2)
    for a in range(0, 181, 20):                                 # 아치 돌
        r = math.radians(180 + a)
        D.line(s, DK, (72 + int(math.cos(r) * 24), DOOR.y + int(math.sin(r) * 24)),
               (72 + int(math.cos(r) * 30), DOOR.y + int(math.sin(r) * 30)), 1)


def _bld_east(s):
    """연금 제련소: 톱니 지붕 공장 + 굴뚝 두 개 + 초록빛 창 + 파이프"""
    BR, MO = (128, 64, 52), (84, 40, 38)
    for cx in (22, 122):                                        # 굴뚝 (뒤)
        _bricks(s, (cx - 8, 0, 16, 80), BR, MO, 8, 5)
        s.fill((96, 92, 110), (cx - 10, 0, 20, 5))
        s.fill((20, 16, 24), (cx - 6, 1, 12, 3))
    for i in range(4):                                          # 톱니 지붕 (유리면이 빛난다)
        x = 4 + i * 34
        D.polygon(s, (66, 62, 82), [(x, 76), (x + 26, 34), (x + 34, 34), (x + 34, 76)])
        D.polygon(s, (86, 82, 104), [(x, 76), (x + 26, 34), (x + 28, 34), (x + 4, 76)])
        s.fill((120, 200, 170), (x + 27, 36, 6, 40))
        s.fill((190, 250, 220), (x + 28, 38, 1, 36))
    s.fill((44, 40, 56), (0, 74, 144, 4))
    _bricks(s, (0, 78, 144, 114), BR, MO)
    s.fill((60, 58, 76), (0, 86, 144, 6))                       # 가로 파이프
    s.fill((120, 116, 138), (0, 86, 144, 2))
    for x in (10, 60, 126):
        s.fill(GOLD_D, (x, 84, 4, 10))
    s.fill((60, 58, 76), (136, 86, 6, 106))
    for wx in (8, 104):                                         # 아치 창
        D.rect(s, (44, 40, 56), (wx, 104, 32, 52))
        D.circle(s, (44, 40, 56), (wx + 16, 106), 16)
        D.rect(s, (70, 200, 120), (wx + 3, 108, 26, 46))
        D.circle(s, (70, 200, 120), (wx + 16, 108), 13)
        s.fill((170, 255, 200), (wx + 5, 104, 3, 48))
        for k in (wx + 11, wx + 20):
            s.fill((44, 40, 56), (k, 96, 2, 58))
        s.fill((44, 40, 56), (wx + 3, 128, 26, 2))
    for i in range(0, 64, 8):                                   # 문 위 경고 줄무늬
        D.polygon(s, (230, 190, 40) if (i // 8) % 2 else (30, 26, 34),
                  [(40 + i, 96), (48 + i, 96), (44 + i, 104), (36 + i, 104)])
    _arch(s, (44, 40, 56), 6)
    _arch(s, (96, 92, 112), 3)


def _bld_north(s):
    """과열 보일러실: 지붕 위 거대 보일러 통 + 왼쪽은 달아오르고 오른쪽은 얼어붙은 철판 벽"""
    s.fill((40, 38, 52), (8, 10, 128, 70))                      # 보일러 통 (가로 원통)
    for x in range(10, 134):
        f = (x - 10) / 124
        base = lerp((170, 84, 60), (120, 150, 190), f)
        for y in range(12, 78):
            k = 1 - abs((y - 45) / 33) ** 2 * 0.55
            s.set_at((x, y), lerp((20, 18, 28), base, k))
    for x in range(22, 130, 22):
        s.fill(GOLD_D, (x, 12, 3, 66))
        s.fill(GOLD, (x, 12, 1, 66))
    s.fill((255, 255, 255), (14, 26, 116, 1))
    for vx in (34, 72, 110):                                    # 안전 밸브
        s.fill((70, 66, 86), (vx - 3, 0, 6, 14))
        s.fill(GOLD, (vx - 4, 0, 8, 3))
    for x in range(6, 138):                                     # 철판 벽: 왼쪽 열기 / 오른쪽 냉기
        f = (x - 6) / 132
        c = lerp((96, 60, 54), (70, 88, 118), f)
        s.fill(c, (x, 80, 1, 112))
    for y in range(80, 192, 14):
        s.fill((40, 38, 52), (6, y, 132, 1))
        for x in range(10, 136, 12):
            s.fill((150, 146, 168), (x, y + 3, 1, 1))
    s.fill((40, 38, 52), (72, 80, 1, 112))
    for i in range(0, 60, 6):                                   # 오른쪽 위 고드름 / 왼쪽 아래 그을음
        D.polygon(s, (220, 240, 255), [(78 + i, 80), (82 + i, 80), (80 + i, 86 + (i * 7) % 7)])
    s.fill((236, 246, 255), (76, 80, 62, 2))
    for i in range(10):
        s.fill((50, 30, 30), (8 + i * 6, 184 - (i * 5) % 9, 4, 8))
    for gx, gy in ((26, 112), (118, 112)):                      # 압력계
        D.circle(s, (40, 38, 52), (gx, gy), 9)
        D.circle(s, (230, 226, 210), (gx, gy), 7)
        D.line(s, (200, 40, 40), (gx, gy), (gx + 4, gy - 4), 1)
    _arch(s, (40, 38, 52), 6)
    _arch(s, (110, 104, 128), 3)


BUILD = {0: _bld_west, 1: _bld_east, 2: _bld_north}


def building(mid):
    k = ("bld", mid)
    if k not in _CACHE:
        s = pygame.Surface((BW, BH), SC)
        BUILD[mid](s)
        s.fill((0, 0, 0, 0), DOOR)                              # 문 구멍은 비워 두고 따로 그린다
        D.circle(s, (0, 0, 0, 0), (72, DOOR.y), 24)
        _CACHE[k] = s
    return _CACHE[k]


_CACHE = {}


def draw_door(surf, x, y, mid, state, lit, t):
    """문: closed = 테마별 닫힌 문 / open = 안에서 보스 색 빛 / done = 금빛. lit = 켜진 퍼즐 스위치 수"""
    acc = DONE if state == "done" else ACC[mid]
    dr = DOOR.move(x, y)
    cx, cy = x + 72, y + DOOR.y
    D.rect(surf, (14, 10, 24), dr)
    D.circle(surf, (14, 10, 24), (cx, cy), 24)
    if state == "closed":
        if mid == 0:                                            # 쇠창살
            for i in range(dr.x + 4, dr.right, 8):
                surf.fill((60, 58, 74), (i, cy - 22, 3, dr.bottom - cy + 22))
                surf.fill((110, 106, 128), (i, cy - 22, 1, dr.bottom - cy + 22))
            for j in range(cy - 10, dr.bottom, 14):
                surf.fill((60, 58, 74), (dr.x, j, dr.w, 3))
        elif mid == 1:                                          # 셔터
            for j in range(cy - 4, dr.bottom - 8, 5):
                surf.fill((120, 118, 136), (dr.x, j, dr.w, 4))
                surf.fill((80, 78, 96), (dr.x, j + 3, dr.w, 1))
            for i in range(0, dr.w, 8):
                D.polygon(surf, (230, 190, 40) if (i // 8) % 2 else (30, 26, 34),
                          [(dr.x + i, dr.bottom - 8), (dr.x + i + 8, dr.bottom - 8), (dr.x + i + 4, dr.bottom), (dr.x + i - 4, dr.bottom)])
        else:                                                   # 쇠 해치 + 손잡이 바퀴
            D.rect(surf, (70, 66, 86), dr)
            D.circle(surf, (70, 66, 86), (cx, cy), 24)
            D.circle(surf, (150, 146, 168), (cx, cy + 28), 11, 2)
            for a in range(4):
                r = t * 0.3 + a * 1.5708
                D.line(surf, (150, 146, 168), (cx, cy + 28), (cx + int(math.cos(r) * 10), cy + 28 + int(math.sin(r) * 10)), 2)
        pulse = 0.5 + 0.5 * math.sin(t * 3)                     # 가운데 봉인 룬
        D.circle(surf, lerp((40, 30, 60), acc, 0.3 + 0.4 * pulse), (cx, cy + 6), 7, 2)
    else:
        for i in range(10):                                     # 안에서 새어 나오는 빛
            k = i / 9
            c = lerp((14, 10, 24), acc, k * (0.75 + 0.25 * math.sin(t * 2.5)))
            r = int(24 - k * 18)
            D.circle(surf, c, (cx, cy + 30), max(2, r))
        for i in range(6):
            yy = (t * 18 + i * 11) % 60
            surf.fill(lerp(acc, (255, 255, 255), 0.5), (cx - 14 + i * 6, int(dr.bottom - yy), 1, 2))
        gl = pygame.Surface((80, 30), SC)                       # 땅에 비친 빛
        D.ellipse(gl, acc + (50,), (0, 0, 80, 30))
        surf.blit(gl, (cx - 40, dr.bottom - 8))
    for i in range(3):                                          # 문 위 퍼즐 표시등 3개
        lx, ly = cx - 12 + i * 12, y + DOOR.y - 36
        on = state != "closed" or i < lit
        D.circle(surf, (20, 16, 30), (lx, ly), 4)
        D.circle(surf, acc if on else (60, 56, 80), (lx, ly), 3)
        if on:
            surf.fill((255, 255, 255), (lx - 1, ly - 2, 1, 1))


def draw_buildings(surf, g, cx, cy):
    T, t = G.T, g["t"]
    for key, (x0, y0, x1, y1, side, mid) in g["meta"]["lairs"].items():
        x, y = x0 * T - cx, (y0 - REAR) * T - cy
        if x > G.W or x + BW < 0 or y > G.H or y + BH < 0:
            continue
        q = next((q for q in g["pz"] if q["pid"] == key), None)
        state = "done" if G.ARENA_OF[mid] in g["cleared"] else ("open" if q and q["done"] else "closed")
        lit = sum(1 for s in q["sw"] if s["on"]) if q else 0
        sh = pygame.Surface((BW + 12, 14), SC)
        D.ellipse(sh, (0, 0, 0, 70), (0, 0, BW + 12, 14))
        surf.blit(sh, (x - 6, y + BH - 6))
        draw_door(surf, x, y, mid, state, lit, t)
        surf.blit(building(mid), (x, y))
        if mid == 1:                                            # 굴뚝 연기
            for chx in (22, 122):
                for i in range(6):
                    f = (t * 0.35 + i / 6 + chx / 50) % 1.0
                    r = 3 + int(f * 7)
                    sm = pygame.Surface((r * 2, r * 2), SC)
                    c = int(100 + 70 * f)
                    D.circle(sm, (c, c, c + 10, int(160 * (1 - f))), (r, r), r)
                    surf.blit(sm, (x + chx - r + int(math.sin(f * 5 + chx) * 4 + f * 12), y - int(f * 46) - r))
        elif mid == 2:                                          # 밸브 증기 + 왼쪽 열기
            for vx in (34, 72, 110):
                if int(t * 0.8 + vx) % 3 == 0:
                    continue
                for i in range(4):
                    f = (t * 1.1 + i / 4 + vx / 40) % 1.0
                    r = 2 + int(f * 5)
                    sm = pygame.Surface((r * 2, r * 2), SC)
                    D.circle(sm, (235, 240, 250, int(150 * (1 - f))), (r, r), r)
                    surf.blit(sm, (x + vx - r, y - int(f * 30) - r))
            surf.blit(W.glow(30, (255, 120, 60), 40), (x + 20 - 30, y + 150 - 30))
        else:                                                   # 탑 꼭대기 화로
            for tx_ in (18, 126):
                fl = int(math.sin(t * 12 + tx_) * 2)
                D.circle(surf, (255, 120, 50), (x + tx_, y - 4), 4 + fl)
                D.circle(surf, (255, 210, 100), (x + tx_, y - 4), 2)


# ================================================================= 중앙 사원 본당 (정면 뒤로 솟은 대성당 + 도시의 심장)
HW, HH = 208, HALL * 16 + 8


def _hall():
    k = "hall"
    if k in _CACHE:
        return _CACHE[k]
    s = pygame.Surface((HW, HH), SC)
    ST, DK, LT, MO = (150, 142, 168), (88, 80, 108), (204, 196, 220), (118, 110, 138)
    for sx in (6, 166):                                         # 양쪽 첨탑
        D.rect(s, DK, (sx, 40, 36, HH - 40))
        _bricks(s, (sx + 2, 42, 32, HH - 42), ST, MO, 10, 6)
        D.polygon(s, DK, [(sx - 2, 42), (sx + 18, 0), (sx + 38, 42)])
        D.polygon(s, (110, 100, 136), [(sx + 1, 41), (sx + 18, 4), (sx + 26, 41)])
        s.fill(GOLD, (sx + 17, 0, 3, 5))
        D.rect(s, (40, 60, 110), (sx + 12, 70, 12, 26))
        D.circle(s, (40, 60, 110), (sx + 18, 70), 6)
    D.rect(s, DK, (36, 62, 136, HH - 62))                       # 본당
    _bricks(s, (38, 64, 132, HH - 64), ST, MO)
    D.polygon(s, DK, [(32, 64), (104, 30), (176, 64)])
    D.polygon(s, (96, 88, 120), [(40, 62), (104, 34), (168, 62)])
    for bx in (50, 74, 134, 158):                               # 스테인드글라스 긴 창
        D.rect(s, DK, (bx - 6, 78, 12, 50))
        D.circle(s, DK, (bx, 78), 6)
        for j in range(5):
            c = ((120, 232, 232), (180, 150, 255), (255, 200, 120))[(j + bx) % 3]
            s.fill(c, (bx - 4, 80 + j * 9, 8, 8))
        s.fill(DK, (bx - 1, 76, 2, 52))
    D.rect(s, DK, (82, 6, 44, HH - 6))                          # 가운데 심장 탑
    _bricks(s, (84, 8, 40, HH - 8), (166, 158, 186), MO, 10, 6)
    s.fill(LT, (84, 8, 3, HH - 8))
    for y in (52, 100):
        s.fill(GOLD, (82, y, 44, 3))
        s.fill(GOLD_D, (82, y + 3, 44, 1))
    _CACHE[k] = s
    return s


def draw_hall(surf, g, cx, cy):
    tx0, ty0, tx1, ty1 = g["meta"]["temple"]
    T, t = G.T, g["t"]
    x, y = tx0 * T - cx, (ty0 - HALL) * T - cy
    if x > G.W or x + HW < 0 or y > G.H or y + HH < 0:
        return
    surf.blit(_hall(), (x, y))
    hx, hy = x + 104, y + 28                                    # 도시의 심장: 열쇠를 모을수록 강하게 뛴다
    k = 1.0 if g["topen"] else 0.35 + 0.2 * g["keys"]
    beat = max(0.0, math.sin(t * 3.2)) ** 6 + 0.6 * max(0.0, math.sin(t * 3.2 - 0.9)) ** 8
    surf.blit(W.glow(40, (255, 80, 90), int(40 + 60 * k * (0.5 + beat))), (hx - 40, hy - 40))
    for i in range(12):                                         # 도는 톱니 고리
        a = t * 0.5 + i * 0.5236
        D.circle(surf, GOLD_L, (hx + int(math.cos(a) * 19), hy + int(math.sin(a) * 19)), 2)
    D.circle(surf, (60, 40, 30), (hx, hy), 16, 2)
    r = int(8 + 2 * beat * k)
    D.circle(surf, lerp((80, 20, 30), (255, 70, 80), k), (hx, hy), r)
    D.circle(surf, lerp((120, 40, 50), (255, 190, 190), k), (hx - 2, hy - 2), max(2, r // 3))


def draw_portal_wrap(old):
    def f(surf, p, cx, cy, t):
        if p.get("hidden"):                                     # 건물 안 전송문은 그리지 않는다 (문에서 빛만 샌다)
            return
        return old(surf, p, cx, cy, t)
    return f


# ================================================================= 월드 후처리
def build_sites(z):
    T = G.T
    meta, ter, solid, ntile, water = z["meta"], z["ter"], z["solid"], z["ntile"], z["water"]
    wt, ht = z["wt"], z["ht"]
    rng = random.Random(9091)
    roads = {(x, y) for y in range(ht) for x in range(wt) if ter[y][x] in (3, 7)}

    def inside(x, y, m=3):
        return m <= x < wt - m and m <= y < ht - m
    keep = set()
    for w in z["warps"]:
        keep |= {(w["tx"] + i, w["ty"] + j) for i in range(-2, 3) for j in range(-2, 4)}
    for q in z["pz"]:
        for s in q["sw"]:
            sx, sy = int(s["x"]) // T, int(s["y"]) // T
            keep |= {(sx + i, sy + j) for i in range(-2, 3) for j in range(-2, 3)}
    for f in meta["fronts"].values():
        keep |= {(f[0] + i, f[1] + j) for i in range(-1, 2) for j in range(-1, 2)}
    for _, nx, ny in z["npcs"]:
        keep.add((nx, ny))
    if meta.get("dragon"):
        dx_, dy_ = meta["dragon"]
        keep |= {(dx_ + i, dy_ + j) for i in range(-4, 5) for j in range(-4, 5)}
    lairbox = set()
    for x0, y0, x1, y1, _, _ in meta["lairs"].values():
        lairbox |= {(x, y) for x in range(x0 - 1, x1 + 2) for y in range(y0 - 1 - REAR, y1 + 2)}
    tx0, ty0, tx1, ty1 = meta["temple"]
    tbox = {(x, y) for x in range(tx0, tx1 + 1) for y in range(ty0, ty1 + 1)}
    clear, mine, bld = set(), set(), set()           # 장식을 걷어 낼 칸 / 이 모듈이 세운 벽(막히면 허문다) / 건물 자리
    for x0, y0, x1, y1, _, _ in meta["lairs"].values():
        bld |= {(x, y) for x in range(x0, x1 + 1) for y in range(y0 - REAR, y1 + 1)}
    bld |= {(x, y) for x in range(tx0, tx1 + 1) for y in range(ty0 - HALL, ty0)}

    # ---- 0) 수호 기계의 방 = 건물: 안은 막고, 문(퍼즐 문) 바로 안쪽에 보이지 않는 전송문을 둔다
    for key, (x0, y0, x1, y1, side, mid) in meta["lairs"].items():
        mx = (x0 + x1) // 2
        gate = next((q["gate"] for q in z["pz"] if q["pid"] == key), set())
        walk = {(mx + i, y1 - 1) for i in (-1, 0, 1)}
        for x in range(x0, x1 + 1):
            for y in range(y0 - REAR, y1 + 1):
                if not inside(x, y, 1):
                    continue
                clear.add((x, y))
                if (x, y) in gate:
                    continue
                ter[y][x] = 4
                water.discard((x, y))
                if (x, y) in walk:
                    solid.discard((x, y))
                    ntile.discard((x, y))
                else:
                    solid.add((x, y))
                    ntile.discard((x, y))
                    if y < y0:
                        mine.add((x, y))                          # 뒤채는 길을 막으면 허물 수 있게
        for pt in z["portals"]:
            if pt.get("to") == G.ARENA_OF[mid]:
                pt.update(x=mx * T + 8, y=(y1 - 1) * T + 8, hidden=True)
        G.ZONES[key]["lair"] = (mx, y1 + 1, mx, y1 + 1, "s", mid)  # 보스를 쓰러뜨리고 돌아오는 자리 = 문 앞
    for pt in z["portals"]:                                       # 중앙 사원 전송문도 문 안쪽에 숨긴다
        if pt.get("to") == "boss_f":
            pt["hidden"] = True

    def floor(x, y):
        if (x, y) in water:
            ter[y][x] = 7
            water.discard((x, y))
            solid.discard((x, y))
        elif ter[y][x] in (0, 2, 3, 5):
            ter[y][x] = 4
        clear.add((x, y))

    def cliff(x, y):
        if (x, y) in keep or (x, y) in roads or (x, y) in lairbox or (x, y) in tbox or (x, y) in water:
            return
        if ter[y][x] == 8:
            return
        ter[y][x] = 8
        solid.add((x, y))
        ntile.discard((x, y))
        clear.add((x, y))
        mine.add((x, y))

    # ---- 1) 보스 성역
    plans = []
    for key, (x0, y0, x1, y1, side, mid) in meta["lairs"].items():
        mx, my = (x0 + x1) // 2, (y0 + y1) // 2
        d = {"e": (1, 0), "w": (-1, 0), "s": (0, 1)}[side]
        p = (d[1], d[0])
        gx, gy = {"e": (x1, my), "w": (x0, my), "s": (mx, y1)}[side]
        cx_, cy_ = mx + d[0] * 4, my + d[1] * 4
        A, B = (11.0, 10.0) if key == "north" else (14.0, 11.0)     # 북쪽은 중앙 사원과 가까워 조금 작게

        def nrm(x, y, cx_=cx_, cy_=cy_, d=d, p=p, A=A, B=B):          # 기본값으로 묶어 둔다 (나중에 다시 쓴다)
            du = (x - cx_) * d[0] + (y - cy_) * d[1]
            dv = (x - cx_) * p[0] + (y - cy_) * p[1]
            return math.hypot(du / A, dv / B) + ((G.hsh(x, y) % 7) - 3) * 0.012

        def av(x, y, gx=gx, gy=gy, d=d, p=p):
            return (x - gx) * d[0] + (y - gy) * d[1], (x - gx) * p[0] + (y - gy) * p[1]
        for y in range(cy_ - 22, cy_ + 23):
            for x in range(cx_ - 22, cx_ + 23):
                if not inside(x, y) or (x, y) in lairbox:
                    continue
                n = nrm(x, y)
                ua, va = av(x, y)
                on_av = 1 <= ua <= A + 6 and abs(va) <= 2                  # 참배로: 폭 5칸, 절벽 문 조금 밖까지
                if on_av:
                    floor(x, y)
                elif n < 1.0:
                    clear.add((x, y))
                    if n < 0.86 and ter[y][x] in (0, 2, 3, 5):
                        ter[y][x] = 4
                elif n < 1.3 and not (ua > 0 and abs(va) <= 2):
                    cliff(x, y)
        plans.append((key, mid, gx, gy, d, p, A, nrm, av))

    # ---- 2) 중앙 사원: 뒤·양옆 절벽 + 앞 돌길 + 폐허 도시
    tmx = (tx0 + tx1) // 2
    tcy = ty0 + 3
    for y in range(ty0 - 14, ty1):
        for x in range(tx0 - 26, tx1 + 27):
            if not inside(x, y) or (x, y) in tbox:
                continue
            n = math.hypot((x - tmx) / 21.0, (y - tcy) / 10.5) + ((G.hsh(x, y) % 9) - 4) * 0.02
            if n < 1.0 and abs(x - tmx) > 7 or n < 0.78:
                cliff(x, y)
    for x in range(tx0, tx1 + 1):                                 # 사원 본당 자리 (정면 뒤): 막아 두고 그 위에 본당을 그린다
        for y in range(ty0 - HALL, ty0):
            if inside(x, y, 1) and (x, y) not in keep and (x, y) not in roads:
                ter[y][x] = 8
                solid.add((x, y))
                ntile.discard((x, y))
                water.discard((x, y))
                clear.add((x, y))
                mine.add((x, y))
    vx0, vy0, vx1, vy1 = meta["vil"]
    avenue = [(x, y) for (x, y) in roads if abs(x - tmx) <= 14 and ty1 + 6 <= y < vy0 - 1]
    for x, y in avenue:                                           # 마을 -> 사원 큰길: 폭 4 돌길
        for i in range(-1, 3):
            for j in range(-1, 2):
                if inside(x + i, y + j) and (x + i, y + j) not in solid and (x + i, y + j) not in keep:
                    floor(x + i, y + j)
    near_road = {(x + i, y + j) for x, y in roads for i in range(-1, 2) for j in range(-1, 2)}
    blocks, tries = [], 0
    while len(blocks) < 8 and tries < 3000:                       # 폐허 도시 블록
        tries += 1
        w_, h_ = rng.randint(5, 8), rng.randint(4, 6)
        x, y = rng.randint(tmx - 28, tmx + 28 - w_), rng.randint(ty1 - 8, ty1 + 26)
        if abs(x + w_ / 2 - tmx) < 12 or any(math.hypot(x - a, y - b) < 9 for a, b in blocks):
            continue
        if any(math.hypot(x - (l[0] + l[2]) / 2, y - (l[1] + l[3]) / 2) < 26 for l in meta["lairs"].values()):
            continue                                              # 보스 성역 근처는 비워 둔다
        area = [(i, j) for i in range(x - 1, x + w_ + 1) for j in range(y - 1, y + h_ + 1)]
        if not all(inside(i, j) and ter[j][i] in (0, 2, 4, 5) and ((i, j) not in solid or (i, j) in ntile)
                   and (i, j) not in keep and (i, j) not in near_road and (i, j) not in water
                   and (i, j) not in mine for i, j in area):
            continue
        blocks.append((x, y))
        gap = rng.choice("tblr")
        for i, j in area:
            floor(i, j)
        for i in range(x, x + w_):
            for j in range(y, y + h_):
                edge = i in (x, x + w_ - 1) or j in (y, y + h_ - 1)
                corner = i in (x, x + w_ - 1) and j in (y, y + h_ - 1)
                gp = (gap == "t" and j == y or gap == "b" and j == y + h_ - 1) and abs(i - (x + w_ // 2)) <= 1 or \
                     (gap == "l" and i == x or gap == "r" and i == x + w_ - 1) and abs(j - (y + h_ // 2)) <= 1
                if edge and (corner or (not gp and rng.random() < 0.7)):
                    solid.add((i, j))
                    ntile.discard((i, j))
                    mine.add((i, j))

    # ---- 3) 걷어 내기: 새 절벽·돌길·안뜰 위의 장식·채집물·적, 길에서 먼 큰 장식 절반
    road3 = {(x + i, y + j) for x, y in roads for i in range(-3, 4) for j in range(-3, 4)}
    keepd = []
    for dd in z["deco"]:
        t = (int(dd[1]) // T, int(dd[2]) // T)
        drop = (t in clear and dd[0] != "warp") or (dd[0] in TALL and t not in road3 and t not in tbox
                                                     and G.hsh(t[0] * 7, t[1] * 3) % 2 == 0)
        if drop:
            if dd[3] and t not in mine and t not in bld:
                solid.discard(t)
                ntile.discard(t)
            continue
        keepd.append(dd)
    z["deco"][:] = keepd
    for nd in z["nodes"]:
        t = (nd["tx"], nd["ty"])
        if nd["alive"] and t in clear:
            nd["alive"], nd["t"] = False, 1e9
            if t not in mine and t not in bld and nd["kind"] != "herb":
                solid.discard(t)
                ntile.discard(t)
    z["en"][:] = [e for e in z["en"] if e["kind"] in ("kaiju", "dragon")
                  or ((int(e["x"]) // T, int(e["y"]) // T) not in solid and (int(e["x"]) // T, int(e["y"]) // T) not in clear)]

    # ---- 4) 새 장식: 참배로 화로·석상, 성문 탑, 안뜰 테마 소품
    taken = set()

    def place(kind, x, y, sol=True):
        if not inside(x, y) or (x, y) in solid or (x, y) in keep or (x, y) in taken or ter[y][x] not in (0, 2, 4):
            return False
        taken.add((x, y))
        z["deco"].append((kind, x * T + 8, y * T + 8, sol))
        if sol:
            solid.add((x, y))
            ntile.add((x, y))
        return True
    for key, mid, gx, gy, d, p, A, nrm, av in plans:
        for ua in range(3, int(A) + 6, 3):
            for sg in (-1, 1):
                x, y = gx + d[0] * ua + p[0] * 4 * sg, gy + d[1] * ua + p[1] * 4 * sg
                place("torch" if (ua // 3) % 2 else "statue", x, y)
        ring_u = int(A * 1.12)
        for sg in (-1, 1):
            x, y = gx + d[0] * ring_u + p[0] * 3 * sg, gy + d[1] * ring_u + p[1] * 3 * sg
            if (x, y) in mine:
                solid.discard((x, y))
                mine.discard((x, y))
                ter[y][x] = 4
            place(f"gtower{mid}", x, y)
        cand = []
        for y in range(gy - 24, gy + 25):
            for x in range(gx - 24, gx + 25):
                if not inside(x, y) or (x, y) in lairbox:
                    continue
                ua, va = av(x, y)
                n = nrm(x, y)
                if 0.42 < n < 0.92 and not (ua >= 0 and abs(va) <= 4):
                    cand.append((x, y))
        rng.shuffle(cand)
        used = []
        for kind, cnt, sol in THEME[key]:
            k = 0
            for x, y in cand:
                if k >= cnt:
                    break
                if any(abs(x - a) + abs(y - b) < 4 for a, b in used):
                    continue
                if place(kind, x, y, sol):
                    used.append((x, y))
                    k += 1

    # ---- 5) 도달 검사: 막힌 목표가 있으면 이 모듈이 세운 벽만 허물어 길을 낸다
    start = tuple(meta["start"])

    def flood():
        seen, q = {start}, [start]
        for a, b in q:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (a + dx, b + dy)
                if n not in seen and 0 <= n[0] < wt and 0 <= n[1] < ht and n not in solid:
                    seen.add(n)
                    q.append(n)
        return seen
    pois = list(meta["fronts"].values()) + [(w["tx"], w["ty"] + 1) for w in z["warps"]]
    pois += [(int(s["x"]) // T, int(s["y"]) // T) for q in z["pz"] for s in q["sw"]]
    reach, opened = flood(), 0
    for poi in pois:
        poi = tuple(poi)
        if poi in reach:
            continue
        prev, q = {poi: None}, [poi]
        hit = None
        for cur in q:
            if cur in reach:
                hit = cur
                break
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (cur[0] + dx, cur[1] + dy)
                if n in prev or not inside(n[0], n[1], 1):
                    continue
                if n in solid and n not in mine:
                    continue
                prev[n] = cur
                q.append(n)
        while hit is not None:
            if hit in mine:
                solid.discard(hit)
                mine.discard(hit)
                ter[hit[1]][hit[0]] = 4
                opened += 1
            hit = prev[hit]
        reach = flood()
    meta["sites"] = dict(opened=opened, blocks=len(blocks), cliffs=sum(1 for t in mine if ter[t[1]][t[0]] == 8))
    z["_sites"] = True


# ================================================================= 그리기
def draw_cliffs(surf, g, cx, cy):
    """산 타일을 입체 절벽으로 다시 그린다 (바닥 그림 위, 다른 것들 아래)"""
    ter, T = g["ter"], G.T
    tx0, ty0 = cx // T, cy // T
    for ty in range(max(0, ty0), min(g["ht"], ty0 + G.H // T + 2)):
        row = ter[ty]
        for tx in range(max(0, tx0), min(g["wt"], tx0 + G.W // T + 2)):
            if row[tx] == 8:
                G.draw_cliff(surf, g, tx, ty, tx * T - cx, ty * T - cy, G.REGIONS[G.tile_reg(g, tx, ty)])


def draw_anim(surf, g, cx, cy):
    """소품 위의 움직이는 것들: 화로 불꽃, 굴뚝 연기, 탱크 거품, 증기, 성문 탑 룬"""
    t = g["t"]
    for dd in g["deco"]:
        k = dd[0]
        if k not in ("torch", "chimney", "vat", "vent") and not k.startswith("gtower"):
            continue
        x, y = int(dd[1]) - cx, int(dd[2]) - cy
        if x < -40 or x > G.W + 40 or y < -60 or y > G.H + 60:
            continue
        h = (int(dd[1]) * 7 + int(dd[2]) * 3) % 100
        if k == "torch":
            fy = y - 8
            surf.blit(W.glow(22, (255, 160, 70), 60), (x - 22, fy - 22))
            fl = int(math.sin(t * 13 + h) * 1.5)
            D.circle(surf, (255, 110, 40), (x, fy), 4 + fl)
            D.circle(surf, (255, 200, 90), (x, fy + 1), 2)
            surf.fill((255, 250, 210), (x - 1, fy, 2, 2))
            for i in range(2):
                yy = (t * 14 + i * 7 + h) % 12
                surf.fill((255, 190, 90), (x - 1 + int(math.sin(t * 5 + i) * 2), int(fy - 4 - yy), 1, 1))
        elif k == "chimney":
            for i in range(6):
                f = ((t * 0.35 + i / 6 + h / 100) % 1.0)
                r = 2 + int(f * 6)
                sx = x + int(math.sin(f * 6 + h) * 3 + f * 10)
                sy = y - 30 - int(f * 40)
                c = int(110 + 60 * f)
                sm = pygame.Surface((r * 2, r * 2), SC)
                D.circle(sm, (c, c, c + 10, int(150 * (1 - f))), (r, r), r)
                surf.blit(sm, (sx - r, sy - r))
        elif k == "vat":
            for i in range(3):
                f = (t * 0.8 + i * 0.33 + h / 50) % 1.0
                surf.fill((220, 255, 220), (x - 3 + i * 3, y - 2 - int(f * 12), 1, 1))
            surf.blit(W.glow(14, (90, 255, 140), 40), (x - 14, y - 22))
        elif k == "vent":
            if int(t * 0.7 + h) % 3 != 0:
                for i in range(5):
                    f = (t * 0.9 + i / 5 + h / 30) % 1.0
                    r = 2 + int(f * 4)
                    sm = pygame.Surface((r * 2, r * 2), SC)
                    D.circle(sm, (230, 236, 250, int(140 * (1 - f))), (r, r), r)
                    surf.blit(sm, (x - r + int(math.sin(f * 8 + i) * 3), y - 2 - int(f * 26) - r))
        else:
            mid = int(k[-1])
            arena = G.ARENA_OF[mid]
            acc = DONE if arena in g["cleared"] else ACC[mid]
            pulse = 0.5 + 0.5 * math.sin(t * 2.4 + h)
            surf.fill(G.lerp_c((40, 30, 60), acc, 0.5 + 0.5 * pulse), (x - 2, y + 8 - 48 + 25, 4, 6))
            fy = y + 8 - 48 + 6
            surf.blit(W.glow(26, (255, 170, 80), 55), (x - 26, fy - 26))
            fl = int(math.sin(t * 12 + h) * 2)
            D.circle(surf, (255, 120, 50), (x, fy), 4 + fl)
            D.circle(surf, (255, 205, 100), (x, fy), 2)


def draw_arena_wrap(old):
    def f(surf, g, cx, cy):
        world = g.get("zid") == O.WID and g.get("meta")
        if world and g.get("shade"):
            try:
                draw_cliffs(surf, g, cx, cy)
                draw_hall(surf, g, cx, cy)                      # 본당은 사원 정면보다 먼저 (정면이 앞을 덮는다)
            except Exception:
                G.v9_log("sites-cliff")
        old(surf, g, cx, cy)
        if world:
            try:
                draw_buildings(surf, g, cx, cy)
                draw_anim(surf, g, cx, cy)
            except Exception:
                G.v9_log("sites-anim")
    return f


# ================================================================= 설치
def install(g_mod, cfg, world_mod, open_mod):
    global G, C, W, O
    G, C, W, O = g_mod, cfg, world_mod, open_mod
    for k, v in SPRITES.items():
        W.SPRITES[k] = v
    W._SPC.clear()
    W.LIGHT_COL["torch"] = ((255, 170, 80), 40)
    W.LIGHT_COL["vat"] = ((110, 255, 150), 30)
    for i in ACC:
        W.LIGHT_COL[f"gtower{i}"] = ((255, 170, 80), 44)
    old_build = G.build_zone

    def build_zone(zid):
        z = old_build(zid)
        if (zid == O.WID or zid in O.LEGACY) and z.get("meta") and not z.get("_sites"):
            try:
                build_sites(z)
            except Exception:
                G.v9_log("sites-build")
        return z
    G.build_zone = build_zone
    G.draw_arena = draw_arena_wrap(G.draw_arena)
    G.draw_portal = draw_portal_wrap(G.draw_portal)
    import v9_lair                                              # 옛 '포탈 울타리' 그림(룬 카펫·마법진·모서리 탑)은 건물이 대신한다
    v9_lair.draw_lairs = lambda *a, **k: None
