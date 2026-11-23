"""최종 보스 도시의 심장, 빅 브라더 Ω - 감시하는 기계 심장 (v9_ba_core.py)  3D 리그 버전 (v9_ba_r3, 최종 크기 1:1 도트)
 좌·우심실, 심첨, 두 심방을 겹친 구체로 쌓고 대동맥궁·폐동맥·정맥을 3D 관으로 이었다. 앞면에는 거대한 감시의 눈이 박혀 있고
 몸 전체가 플레이어 쪽으로 돌아서며 눈은 시선을 따라간다. 박동(쿵-쿵)에 맞춰 몸이 부풀고 관상동맥이 맥동한다.
 1 외곽 시스템(차가운 강철 + 보호막) / 2 본체 노출(붉은 살·푸른 정맥·파편 궤도) / 3 시스템 해킹(곁눈·글리치·붉은 잔상 홍채) /
 4 멸망 프로토콜(창백한 뼈색, 균열에서 새는 빛, 전기 호)"""
import math

import pygame

import v9_ba_kit as K
import v9_ba_r3 as R3
from v9_ba_kit import D, OUT, TAU, drk, lit, mix

RATES = (1.0, 1.3, 1.8, 3.2)
# 심실, 심방, 대동맥, 정맥, 폐동맥
HC = {1: ((112, 120, 146), (98, 106, 132), (136, 144, 166), (92, 108, 140), (96, 118, 150)),
      2: ((166, 66, 84), (134, 56, 88), (214, 66, 72), (62, 92, 176), (74, 112, 190)),
      3: ((190, 50, 56), (156, 42, 66), (238, 74, 60), (68, 86, 176), (80, 102, 200)),
      4: ((218, 184, 170), (198, 160, 156), (246, 218, 198), (190, 204, 234), (204, 218, 240))}
COL = ((120, 232, 232), (255, 190, 90), (255, 90, 110), (255, 255, 255))
HOVER = 14.0
LV = (0.0, 4.0, 25.0, 14.5)          # 좌심실 (x, y, z, r)
RVE = (1.5, -8.5, 24.0, 12.5)         # 우심실
APX = (3.5, 2.0, 12.5, 8.5)           # 심첨
ATL = (-5.0, 7.5, 36.0, 8.0)          # 좌심방
ATR = (-4.0, -9.0, 34.0, 7.0)         # 우심방
EYE = (11.5, 0.0, 26.0)               # 눈 중심 (앞면)


def beat(t, rate):
    f = (t * rate) % 1.0
    return max(max(0.0, 1 - abs(f - 0.06) / 0.09), 0.65 * max(0.0, 1 - abs(f - 0.26) / 0.09))


def _tube(sc, pts, w, c, bias=0.0):
    for a, b in zip(pts, pts[1:]):
        sc.caps(a, b, w, w, c, bias=bias)


def _eye(cv, e, x, y, col, ph, bt, an, hd, front):
    """앞면의 눈. front = 눈이 보는 쪽을 향한 정도(0~1)"""
    if front <= 0.05:
        return
    W, H = 17.0, 12.0 * max(0.35, front)
    if ph == 1:
        glance = (an * 0.7) % 4.0
        target = 0.28 if 3.0 < glance < 3.5 else 0.0
    else:
        target = 1.0 if ph < 4 else 0.85
    lid = e["_lid"] = e.get("_lid", 0.0) + (target - e.get("_lid", 0.0)) * 0.12
    D.ellipse(cv, OUT, (int(x - W - 1), int(y - H - 1), int(2 * W + 2), int(2 * H + 2)))
    D.ellipse(cv, (16, 14, 30), (int(x - W), int(y - H), int(2 * W), int(2 * H)))
    look = e.get("lk", 0.0)
    jit = int(math.sin(an * 37) * 2) if ph == 3 else 0
    ix, iy = x + math.cos(look - hd) * 3.0 * front + jit, y + math.sin(look) * 1.5
    old = cv.get_clip()
    cv.set_clip(old.clip(pygame.Rect(int(x - W), int(y - H), int(2 * W), int(2 * H))))
    if ph == 3:
        D.circle(cv, (255, 70, 90), (int(ix - 3 - jit), int(iy + 1)), 6)
    D.circle(cv, drk(col, 0.45), (int(ix), int(iy)), 7)
    D.circle(cv, col, (int(ix), int(iy)), 6)
    for k in range(12):                                          # 홍채 결
        a = k * TAU / 12 + an * (0.3 if ph < 4 else 1.4)
        D.line(cv, lit(col, 0.3 + 0.3 * (k % 2)), (ix + math.cos(a) * 3, iy + math.sin(a) * 3), (ix + math.cos(a) * 6, iy + math.sin(a) * 6), 1)
    pr = 1 + int(bt * 2) + (2 if ph == 4 else 0)
    D.circle(cv, (255, 40, 50) if ph == 4 else (10, 8, 20), (int(ix), int(iy)), pr)
    cv.fill((255, 255, 255), (int(ix) - 3, int(iy) - 3, 2, 2))
    if ph == 4:
        for ax_, ay_, bx_, by_ in ((-12, -5, -1, 0), (-1, 0, 5, -8), (5, -8, 13, -6), (-2, 1, 4, 9), (4, 9, 12, 7)):
            D.line(cv, (255, 255, 255), (x + ax_, y + ay_ * front), (x + bx_, y + by_ * front), 1)
    if lid < 0.99:                                               # 금속 눈꺼풀
        h = int((1 - lid) * H) + 1
        for top in (True, False):
            if top:
                cv.set_clip(old.clip(pygame.Rect(int(x - W - 1), int(y - H - 1), int(2 * W + 2), h + 1)))
            else:
                cv.set_clip(old.clip(pygame.Rect(int(x - W - 1), int(y + H - h), int(2 * W + 2), h + 2)))
            D.ellipse(cv, (122, 130, 158), (int(x - W), int(y - H), int(2 * W), int(2 * H)))
        cv.set_clip(old.clip(pygame.Rect(int(x - W), int(y - 1), int(2 * W), 2)))
        if lid < 0.1:
            cv.fill(mix(col, (255, 255, 255), 0.4 * bt), (int(x - W + 2), int(y), int(2 * W - 4), 1))
    cv.set_clip(old)
    D.ellipse(cv, drk((122, 130, 158), 0.2), (int(x - W - 1), int(y - H - 1), int(2 * W + 2), int(2 * H + 2)), 1)
    for i in range(8):                                           # 눈 둘레 표시등
        a = an * (0.5 if ph < 3 else 1.6) + i * TAU / 8
        cv.fill(col if int(a * 2) % 2 else drk(col, 0.5), (int(x + math.cos(a) * (W + 3)), int(y + math.sin(a) * (H + 3)), 2, 2))


def _surface_curve(sc, ball_, pts_uv, col, w=1, bias=0.0):
    """구체 표면 위의 곡선 (u: 가로각, v: 세로각)을 보이는 부분만 선으로 그린다"""
    cx, cy, cz, r = ball_
    prev = None
    for u, v in pts_uv:
        n = (math.cos(v) * math.cos(u), math.cos(v) * math.sin(u), math.sin(v))
        vis = R3.visible(sc, n)
        p = (cx + n[0] * r * 1.01, cy + n[1] * r * 1.01, cz + n[2] * r * 1.01)
        if prev is not None and vis and prev[1]:
            sc.line(prev[0], p, col, w, bias=bias)
        prev = (p, vis)


def _on(b_, u, v):
    n = (math.cos(v) * math.cos(u), math.cos(v) * math.sin(u), math.sin(v))
    return n, (b_[0] + n[0] * b_[3], b_[1] + n[1] * b_[3], b_[2] + n[2] * b_[3])


def draw(e):
    ph, an = e["phase"], e["an"]
    col = COL[ph - 1]
    rate = RATES[ph - 1]
    bt = beat(an, rate)
    k = 1.0 + 0.09 * bt
    st, dt = R3.anim(e, "_r3")
    R3.turn_toward(st, e.get("fa2", e.get("lk", 0.0)), dt, 3.5)
    hd = st["hd"]
    ven, atr, aor, vei, pul = HC[ph]
    cv = R3.canvas("core")
    bob = math.sin(an * 2) * 1.6
    shake = math.sin(an * 60) * 0.9 if ph == 4 else 0.0
    K.shadow_at(cv, R3.R3X, R3.R3Y, 26, 7, 80)
    sc = R3.Scene(cv, hd, z0=HOVER + bob, k=1.7)
    sc.fn((0, 0, 24), lambda c_, x, y: K.glow(c_, x, y, 70, col, 46 + int(bt * 40)), bias=-20)
    sp = 0.8 if ph == 2 else 1.9

    def B(b):
        return (b[0] + shake, b[1], b[2], b[3] * k)

    # ---- 장갑 파편 (2~3페이즈 궤도)
    if 2 <= ph <= 3:
        for i in range(4):
            a = an * sp + i * TAU / 4
            px, py = math.cos(a) * 36, math.sin(a) * 36
            sc.box(px - 5, px + 5, py - 3, py + 3, 22 + math.sin(a * 2) * 3, 26 + math.sin(a * 2) * 3, (130, 138, 166), bias=2)

    # ---- 혈관 (뒤쪽)
    _tube(sc, [(-6, -10, 40), (-6, -11, 48), (-5, -11, 56)], 6.0, vei, bias=-0.5)
    arch = [(-1, 3, 42), (-1, 5, 52), (0, 9, 58), (1, 13, 55), (1, 14, 48), (1, 14, 42)]
    _tube(sc, arch, 6.4, aor, bias=-0.4)
    tips = []
    for a0, a1 in (((-1, 5, 53), (-1, 4, 63)), ((0, 9, 58), (0, 9, 67)), ((1, 12, 57), (1, 15, 65))):
        sc.caps(a0, a1, 3.4, 3.0, aor, bias=-0.3)
        tips.append(a1)
    # ---- 심방·심실·심첨
    sc.caps((1.5, 3.0, 20.0), (5.5, 3.0, 3.5), 26.0, 5.0, ven, bias=-0.1)
    for b_, c_ in ((ATL, atr), (ATR, atr), (LV, ven), (RVE, mix(ven, (50, 36, 90), 0.28))):
        bb = B(b_)
        sc.ball((bb[0], bb[1], bb[2]), bb[3], c_, bias=0.0)
    _tube(sc, [(2, -3, 43), (4, -7, 49), (5, -12, 52), (5, -15, 49)], 6.0, pul, bias=0.2)
    # ---- 표면 문양
    if ph == 1:
        seam = drk(ven, 0.5)
        for a0 in (0.2, 0.9, 1.6):
            _surface_curve(sc, LV, [(a0 + 0.9 * (i / 6), 1.1 - i * 0.28) for i in range(7)], seam, 1, 0.3)
        for u, v, bb in ((0.5, 0.4, LV), (1.2, 0.1, LV), (0.3, 0.2, RVE), (0.9, -0.3, RVE)):
            n, q = _on(bb, u, v)
            if R3.visible(sc, n):
                sc.line(q, q, lit(ven, 0.6), 2, bias=0.4)
    else:
        vc = mix(drk(col, 0.55), col, 0.35 + 0.65 * bt)
        for a0 in (0.1, 0.7, 1.3, 1.9):
            _surface_curve(sc, LV, [(a0 + 0.6 * (i / 7), 1.2 - i * 0.26) for i in range(8)], vc, 2, 0.3)
        for a0 in (0.0, 0.8):
            _surface_curve(sc, RVE, [(a0 + 0.6 * (i / 7), 1.0 - i * 0.24) for i in range(8)], vc, 1, 0.3)
        if ph == 4:
            for a0 in (0.3, 1.0, 1.7):
                crack = [(a0 + 0.3 * math.sin(i), 1.0 - i * 0.22) for i in range(9)]
                _surface_curve(sc, LV, crack, (255, 250, 230), 3, 0.35)
                _surface_curve(sc, LV, crack, (255, 120, 90), 1, 0.4)
    # ---- 서브 코어 연결구
    alive = e.get("_alive", 4 if ph == 1 else 0)
    for i, (u, v, bb) in enumerate(((0.6, 0.9, ATL), (-0.4, 0.8, ATR), (0.9, -0.2, LV), (-0.9, -0.1, RVE))):
        on = (i < alive) if ph == 1 else ph >= 2
        n, q = _on(bb, u, v)
        sc.ball(q, 2.8, mix(col, (255, 255, 255), 0.5 * bt) if on else (46, 48, 68), bias=0.6)
    # ---- 혈관 끝 증기/불꽃
    for i, tp in enumerate(tips + [(-5, -11, 58)]):
        def vent(c_, x, y, i=i):
            if ph == 4:
                if int(an * 30 + i) % 2:
                    c_.fill((255, 240, 180), (int(x + math.sin(an * 50 + i) * 2), int(y - 4), 2, 2))
            else:
                K.puff(c_, x, y, an, (216, 224, 238) if ph < 3 else (234, 152, 122), 3, 10, 1.0 + bt, i, 2)
        sc.fn(tp, vent, bias=3)
    # ---- 눈 (앞면)
    front = max(0.0, min(1.0, math.sin(hd) * R3.CE + 0.35))        # 몸의 앞이 화면을 향할수록 크게 보인다
    sc.fn(EYE, lambda c_, x, y: _eye(c_, e, x, y, col, ph, bt, an, hd, front), bias=1.5)
    sc.fn(EYE, lambda c_, x, y: K.glow(c_, x, y, 28, col, 30 + int(bt * 50)), bias=1.4)
    if ph == 3:
        for i, (u, v, bb) in enumerate(((1.4, 0.2, LV), (-1.2, 0.3, RVE), (0.9, -0.6, LV), (-0.8, -0.6, RVE))):
            n, q = _on(bb, u, v)
            if R3.visible(sc, n) and int(an * 3 + i * 1.7) % 3:
                sc.fn(q, lambda c_, x, y: (D.ellipse(c_, OUT, (int(x) - 3, int(y) - 2, 6, 4)), c_.fill((255, 70, 90), (int(x) - 1, int(y) - 1, 2, 1))), bias=1.6)
    if ph == 4:
        for i in range(3):
            a = an * 9 + i * 2.1
            sc.line((math.cos(a) * 18, math.sin(a) * 18, 24 + math.sin(a * 2) * 6), (math.cos(a + 0.4) * 38, math.sin(a - 0.3) * 38, 24 + math.cos(a) * 12),
                    (255, 255, 255), 1, bias=3)
    sc.flush()
    if e["fl"] > 0 or (e["inv"] > 0 and int(an * 20) % 2 == 1):
        K.flash(cv)
    return cv


def cables(surf, e, cx, cy):
    """1페이즈: 서브 코어(파일론)와 심장을 잇는 에너지 케이블. 화면에 직접 그린다 (파일론이 도화지보다 멀리 있다)"""
    if e["phase"] != 1:
        return 0
    an = e["an"]
    rate = RATES[0]
    x, y = int(e["x"]) - cx, int(e["y"]) - cy - 6
    alive = 0
    for c in e.get("cores", []):
        if c["hp"] <= 0:
            continue
        alive += 1
        px, py = int(c["x"]) - cx, int(c["y"]) - cy
        D.line(surf, (40, 90, 120), (x, y), (px, py - 8), 3)
        D.line(surf, (150, 236, 240), (x, y), (px, py - 8), 1)
        for i in range(3):
            f = (an * rate * 0.5 + i / 3 + alive * 0.17) % 1.0
            D.circle(surf, (255, 255, 255), (int(x + (px - x) * f), int(y + (py - 8 - y) * f)), 2)
    e["_alive"] = alive
    return alive
