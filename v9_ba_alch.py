"""공장장 알케미스트 - 반응로 플라스크 몸체의 다관절 제련사 (v9_ba_alch.py)  3D 리그 버전 (v9_ba_r3, 최종 크기 1:1 도트)
 공중에 뜬 거대 유리 반응로(액체 색이 페이즈를 알린다: 녹색 -> 호박색 -> 붉은 용융 -> 금 간 유리) + 황동 목·머리 + 어깨 굴뚝 두 개
 + 머리를 도는 톱니 후광 + 관절 팔(1페이즈 2개, 2~4페이즈 4개: 플라스크·집게·용접기·렌치). 몸은 플레이어 쪽으로 돌아선다.
 패턴 연기: cast = 팔을 번쩍 들고 눈이 하얗게 타오르며 불꽃 고리, 4페이즈 = 금 간 유리에서 열기, 끓어 넘치는 용융물"""
import math

import pygame

import v9_ba_kit as K
import v9_ba_r3 as R3
from v9_ba_kit import D, OUT, TAU, drk, lit, mix

METAL, BRASS, STEEL = (112, 122, 152), (216, 170, 86), (166, 174, 196)
RF = 22.0                                                     # 플라스크 반지름
FZ = 40.0                                                     # 플라스크 중심 높이


def _tool(sc, k, hand, ang, sg, t, liq, ph):
    """hand = 손 좌표(모델), ang = 팔이 향한 바깥 각도"""
    hx, hy, hz = hand
    ox, oy = math.cos(ang), math.sin(ang)
    if k == 0:                                                   # 플라스크
        sc.ball((hx + ox * 2, hy + oy * 2, hz + 1), 5.2, (206, 228, 240), bias=0.5)
        sc.ball((hx + ox * 2, hy + oy * 2, hz - 0.5), 3.6, liq, bias=0.55)
        sc.caps((hx + ox * 2, hy + oy * 2, hz + 4), (hx + ox * 2, hy + oy * 2, hz + 7), 2.0, 2.0, (206, 228, 240), bias=0.5)
        if int(t * 5) % 2:
            sc.fn((hx + ox * 2, hy + oy * 2, hz + 9), lambda cv, x, y: cv.fill(lit(liq, 0.5), (int(x), int(y - int(t * 6) % 4), 1, 1)), bias=1)
    elif k == 1:                                                 # 집게
        op = 1.8 + math.sin(t * 6) * 1.2
        for s_ in (-1, 1):
            sc.caps((hx, hy, hz), (hx + ox * 7 - oy * s_ * op, hy + oy * 7 + ox * s_ * op, hz), 2.2, 1.2, STEEL, bias=0.5)
        sc.ball(hand, 2.2, METAL, bias=0.5)
    elif k == 2:                                                 # 용접기
        sc.ball(hand, 3.0, (255, 176, 76) if ph >= 3 else STEEL, bias=0.5)
        tip = (hx + ox * 6, hy + oy * 6, hz + 0.5)
        sc.caps(hand, tip, 2.6, 1.6, METAL, bias=0.5)
        if int(t * 18) % 3:
            sc.fn(tip, lambda cv, x, y: (K.glow(cv, x, y, 8, (255, 250, 210), 220),
                                         cv.fill((255, 255, 220), (int(x + math.sin(t * 40) * 2), int(y + math.cos(t * 33) * 2), 2, 2))), bias=1)
    else:                                                        # 렌치
        tip = (hx + ox * 7, hy + oy * 7, hz + 3)
        sc.caps((hx - ox, hy - oy, hz), tip, 3.0, 2.4, (226, 180, 96), bias=0.5)
        sc.fn(tip, lambda cv, x, y: (D.circle(cv, OUT, (int(x), int(y)), 4), D.circle(cv, (226, 180, 96), (int(x), int(y)), 3, 2)), bias=0.6)


def _flask(cv, x, y, t, liq, ph, hot):
    R = int(RF)
    D.circle(cv, OUT, (int(x), int(y)), R + 1)
    D.circle(cv, (34, 50, 64), (int(x), int(y)), R)
    lvl = 3 + math.sin(t * 4) * 1.4                                  # 액면 (구 중심 기준 아래쪽 +)

    def liquid(layer, lx, ly):
        top = int(ly + lvl)
        D.rect(layer, drk(liq, 0.42), (0, top, 2 * R + 4, 2 * R))
        D.rect(layer, mix(liq, (20, 40, 30), 0.2), (0, top + 2, 2 * R + 4, 2 * R))
        D.rect(layer, lit(liq, 0.55), (0, top, 2 * R + 4, 1))
        for i in range(8):                                           # 기포
            f = (t * 0.7 + i * 0.125) % 1.0
            by = ly + R - 3 - f * (R * 1.0)
            if by > top:
                bx = lx - R * 0.6 + i * (R * 0.17) + math.sin(f * 9 + i) * 2
                D.circle(layer, lit(liq, 0.65), (int(bx), int(by)), 1 + (i % 2))
        if hot:
            for i in range(5):
                bx = lx - R * 0.5 + i * (R * 0.25)
                D.circle(layer, lit(liq, 0.4), (int(bx), int(top - 1 - abs(math.sin(t * 6 + i)) * 2)), 2)
    K.clip_circle(cv, x, y, R - 1, liquid)
    D.circle(cv, (210, 238, 250), (int(x - R * 0.55), int(y - R * 0.5)), 2)
    D.arc(cv, (226, 244, 252), pygame.Rect(int(x - R + 3), int(y - R + 3), 2 * R - 6, 2 * R - 6), 2.6, 3.4, 2)
    D.circle(cv, (150, 190, 210), (int(x), int(y)), R, 1)
    if ph == 4:                                                      # 금 간 유리
        for ax_, ay_, bx_, by_ in ((5, -21, 2, -11), (2, -11, 8, -4), (8, -4, 6, 4), (-9, -18, -4, -10), (-4, -10, -11, -3)):
            D.line(cv, (255, 232, 176), (int(x + ax_), int(y + ay_)), (int(x + bx_), int(y + by_)), 1)
        K.glow(cv, x, y, R + 8, (255, 100, 60), 90)
    for a0, a1 in ((3.95, 5.45), (0.75, 2.25)):                       # 황동 띠
        D.arc(cv, OUT, pygame.Rect(int(x - R - 1), int(y - R - 1), 2 * R + 2, 2 * R + 2), a0, a1, 4)
        D.arc(cv, BRASS, pygame.Rect(int(x - R), int(y - R), 2 * R, 2 * R), a0, a1, 2)


def draw(e):
    ph, t = e["phase"], e["an"]
    cast = e["st"] == "cast"
    st, dt = R3.anim(e, "_r3")
    R3.turn_toward(st, e.get("fa2", e.get("fa", 0.0)), dt, 4.0)
    hd = st["hd"]
    liq = ((120, 255, 140), (120, 255, 140), (255, 176, 80), (255, 92, 64))[ph - 1]
    hot = ph >= 3
    cv = R3.canvas("alch")
    K.shadow_at(cv, R3.R3X, R3.R3Y, 24, 6, 70)
    hover = 10.0 + math.sin(t * 2) * 1.6
    sc = R3.Scene(cv, hd, z0=hover)

    # ---- 하부 분사 + 받침
    sc.fn((0, 0, -1), lambda c_, x, y: (K.glow(c_, x, y, 20, (80, 230, 190) if ph < 4 else (255, 130, 70), 110), [
        D.ellipse(c_, c, (int(x - w), int(y - 2), int(w * 2), max(2, int((12 - k * 3) * (0.8 + 0.2 * math.sin(t * 20 + k)))))) for k, (c, w) in enumerate(
            (((50, 190, 160) if ph < 4 else (255, 110, 60), 9), ((130, 250, 210) if ph < 4 else (255, 190, 100), 6), ((255, 255, 255), 3)))]), bias=-6)
    def pedestal(c_, x, y):                                              # 원형 받침 (어느 방향에서도 같은 모양)
        for dz, rx, ry, col in ((5, 12, 5, drk(METAL, 0.3)), (3, 13, 5.5, METAL), (1, 13.5, 5.5, BRASS), (-1, 12.5, 5, drk(METAL, 0.4))):
            D.ellipse(c_, OUT, (int(x - rx - 1), int(y - ry - dz * 0.4 - 1), int(rx * 2 + 2), int(ry * 2 + 2)))
            D.ellipse(c_, col, (int(x - rx), int(y - ry - dz * 0.4), int(rx * 2), int(ry * 2)))
        D.ellipse(c_, lit(METAL, 0.25), (int(x - 9), int(y - 7), 18, 5))
        for k in range(6):
            ang = k * TAU / 6 + t * 0.4
            c_.fill(lit(METAL, 0.6), (int(x + math.cos(ang) * 11), int(y - 2 + math.sin(ang) * 4), 2, 2))
    sc.fn((0, 0, 3), pedestal, bias=-2)

    # ---- 어깨 굴뚝 + 증기
    for sg in (-1, 1):
        px, py = -5.0, sg * 15.0
        sc.caps((px, py, 30), (px, py, 66), 6.0, 6.0, drk(METAL, 0.08), bias=-0.2)
        sc.caps((px, py, 66), (px, py, 70), 9.0, 9.0, METAL, bias=0.3)
        sc.caps((px, py, 68), (px, py, 69), 9.4, 9.4, BRASS, bias=0.35)
        sc.fn((px, py, 72), lambda c_, x, y, sg=sg: K.puff(c_, x, y, t, (216, 224, 234) if not hot else (236, 170, 140), 3, 14, 1.0, sg, 2), bias=1.0)

    # ---- 반응로
    sc.fn((0, 0, FZ), lambda c_, x, y: _flask(c_, x, y, t, liq, ph, hot), bias=0.0)
    # ---- 목 + 머리
    sc.caps((0, 0, FZ + RF - 2), (0, 0, FZ + RF + 5), 12.0, 12.0, METAL, bias=0.6)
    sc.caps((0, 0, FZ + RF + 2), (0, 0, FZ + RF + 3.5), 12.8, 12.8, BRASS, bias=0.65)
    hz = FZ + RF + 15
    sc.ball((0, 0, hz), 9.5, METAL, bias=0.7)
    ec = (255, 255, 210) if cast else (255, 90, 60)
    sc.box(7.0, 10.6, -6.4, 6.4, hz - 3.2, hz + 1.8, (24, 18, 34), bias=0.9)
    sw = math.sin(t * 2) * 1.2
    for yy in (-3.6, 1.2):
        sc.box(10.7, 10.9, yy + sw * 0.4, yy + 2.4 + sw * 0.4, hz - 1.7, hz + 0.1, ec, bias=1.0)
    sc.fn((10.6, 0, hz - 0.8), lambda c_, x, y: K.glow(c_, x, y, 11, ec, 120), bias=1.1)
    sc.caps((0, 0, hz + 8), (3, 0, hz + 19), 2.2, 1.6, (190, 196, 216), bias=0.8)
    blink = int(t * 3) % 2
    sc.ball((3, 0, hz + 20.5), 2.6, (255, 90, 60) if blink else (130, 44, 44), bias=0.85)
    if blink:
        sc.fn((3, 0, hz + 20.5), lambda c_, x, y: K.glow(c_, x, y, 8, (255, 90, 60), 140), bias=0.9)

    # ---- 톱니 후광
    for k in range(6):
        ang = t * (1.5 if ph < 4 else 3.2) + k * TAU / 6
        gp = (math.cos(ang) * 17, math.sin(ang) * 17, hz - 3 + math.sin(ang * 2) * 1.5)
        sc.fn(gp, lambda c_, x, y, ang=ang: K.gear(c_, x, y, 4.2 + 0.6 * math.sin(ang), ang * 2, (200, 206, 224), 6), bias=2.0)

    # ---- 팔
    n = 2 if ph < 2 else 4
    for k in range(n):
        sg = -1 if k % 2 == 0 else 1
        row = k // 2
        sh = (-1.0 - row * 6.0, sg * (RF - 1.5), FZ + 6 - row * 10)
        sw_ = math.sin(t * 3 + k * 1.7)
        if cast:
            hand = (3 + row * 2, sg * (32 + row * 3), FZ + 30 + sw_ * 2)
        else:
            hand = (4 - row * 4, sg * (33 + sw_ * 2), FZ - 12 - row * 4 + sw_ * 3)
        elb = ((sh[0] + hand[0]) / 2 + 3, (sh[1] + hand[1]) / 2 + sg * 4, (sh[2] + hand[2]) / 2 + 6)
        sc.caps(sh, elb, 5.6, 4.8, STEEL, bias=0.8)
        sc.caps(elb, hand, 4.8, 4.0, STEEL, bias=0.8)
        sc.ball(elb, 3.4, BRASS, bias=0.85)
        sc.ball(sh, 4.8, METAL, bias=0.82)
        _tool(sc, k, hand, math.atan2(hand[1] - elb[1], hand[0] - elb[0]), sg, t, liq, ph)
    if cast:
        sc.fn((0, 0, hz), lambda c_, x, y: K.sparks(c_, x, y, t, (255, 255, 200), 7, 24, 5, 0, 2), bias=3)
    if ph == 4:                                                          # 끓어 넘치는 용융물
        for i in range(4):
            f = (t * 0.9 + i * 0.27) % 1.0
            sc.fn((-10 + i * 7, 8, FZ - RF + 2 - f * 12), lambda c_, x, y, f=f: D.circle(c_, (255, 120, 70), (int(x), int(y)), max(1, int(2.2 * (1 - f)))), bias=2)
    sc.flush()
    if e["fl"] > 0:
        K.flash(cv)
    return cv
