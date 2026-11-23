"""수문장 벌크스틸 - 네 발 이동식 성문 요새 (v9_ba_bulk.py)  3D 리그 버전 (v9_ba_r3 사용, 최종 크기 1:1 도트)
 몸통은 아래가 넓은 절두체 성벽, 다리 네 개는 2본 IK + 유압 피스톤(대각선 걸음), 진행 방향 드릴, 앞면 성문과 외눈.
 1 녹슨 철벽(깃발·녹·성문 방패) / 2 요새화 거포 모드(등 포탑·배기 증기·말뚝 발) / 3 제한 해제(장갑 분리·코어·후방 분사)
 패턴 연기: wind = 웅크리고 드릴이 길게 뻗으며 붉게 달아오름, dash = 몸을 낮춰 질주(먼지·속도선), turret = 포신 반동,
           stun = 주저앉아 증기·불꽃, 몸은 항상 플레이어 쪽으로 천천히 돌아선다"""
import math

import pygame

import v9_ba_kit as K
import v9_ba_r3 as R3
from v9_ba_kit import D, OUT, TAU, drk, lit, mix

PAL = (dict(base=(176, 118, 82), trim=(104, 76, 64), steel=(170, 174, 192), glow=(255, 84, 56)),
       dict(base=(122, 134, 170), trim=(68, 78, 110), steel=(190, 196, 216), glow=(255, 96, 60)),
       dict(base=(204, 210, 228), trim=(58, 62, 90), steel=(224, 230, 244), glow=(255, 176, 66)))
HIP = ((16, 13), (16, -13), (-16, 13), (-16, -13))          # (x, y), 앞오른쪽·앞왼쪽·뒤오른쪽·뒤왼쪽
PHASE_OFF = (0.0, 0.5, 0.5, 0.0)                              # 대각선 걸음


def draw(e):
    ph, t, stt = e["phase"], e["an"], e["st"]
    p = PAL[ph - 1]
    base, trim, steel, glowc = p["base"], p["trim"], p["steel"], p["glow"]
    st, dt = R3.anim(e, "_r3")
    R3.turn_toward(st, e["fa"], dt, 8.0 if stt == "dash" else 5.0)
    hd = st["hd"]
    stun, wind, dash = stt == "stun", stt == "wind", stt == "dash"
    moving = e["mv"] or dash
    vf = st["vx"] * math.cos(hd) + st["vy"] * math.sin(hd)
    st["g"] += 0.6 * vf * dt / 12.0
    amp = min(1.0, st["sp"] / 24.0)
    g = st["g"]
    pulse = 0.5 + 0.5 * math.sin(t * 7)
    cv = R3.canvas("bulk")
    K.shadow_at(cv, R3.R3X, R3.R3Y, 34, 9, 80)
    crouch = 4.0 if wind else 0.0
    sag = (6.0 if stun else (3.0 if ph == 2 else 0.0)) + crouch
    bob = (math.sin(g * 12.566) * 1.2 * amp) if moving else math.sin(t * 2.5) * 0.7
    sc = R3.Scene(cv, hd, z0=0.0)
    wd = 1.18 if ph == 2 else 1.0                                      # 2페이즈: 다리를 벌려 자세를 낮춘다
    hz = 19.0 - sag * 0.5 + bob                                         # 엉덩이 높이

    # ---- 다리
    for i, (hx, hy) in enumerate(HIP):
        front = hx > 0
        sgn = 1 if hy > 0 else -1
        ph_ = (g + PHASE_OFF[i]) % 1.0
        if ph_ < 0.65:
            fxs, lift = 0.5 - ph_ / 0.65, 0.0
        else:
            u = (ph_ - 0.65) / 0.35
            fxs, lift = -0.5 + u, math.sin(math.pi * u)
        stride = 9.0 * amp
        fx_ = hx + fxs * stride + (6 if (dash and front) else 0)
        fy_ = hy + sgn * (9.0 * wd + (3 if stun else 0))
        fz_ = lift * (3.2 + stride * 0.3) + (0.0 if True else 0.0)
        hip = (hx, hy * 0.85, hz)
        foot = (fx_, fy_, fz_)
        knee, foot = R3.leg_ik(hip, foot, 12.0, 12.5, (0.15 * (1 if front else -1), sgn * 1.0, 0.7))
        far = (hy * math.sin(hd) + hx * math.sin(hd + 0) * 0) * 0 < 0                # (깊이 정렬은 Scene 이 한다)
        c = drk(base, 0.18 if i % 2 == 0 else 0.3)
        b = -2.0
        sc.caps(hip, knee, 6.5, 5.5, c, bias=b)
        sc.caps(knee, foot, 5.0, 3.6, drk(c, 0.15), bias=b)
        sc.caps((hip[0] - 1.5, hip[1] + sgn * 2.2, hip[2] - 2), (knee[0] - 0.5, knee[1] + sgn * 1.8, knee[2] + 1), 2.4, 2.4, steel, bias=b + 0.3)
        sc.ball(knee, 3.4, (255, 170, 64) if ph == 3 else trim, bias=b + 0.2)
        sc.box(foot[0] - 4.5, foot[0] + 5.5, foot[1] - 3.5, foot[1] + 3.5, foot[2] - 0.5, foot[2] + 2.2, drk(trim, 0.1), bias=b)
        if ph == 2:
            for dx in (-2.5, 3.0):
                sc.poly(((foot[0] + dx, foot[1] - 1.5, foot[2]), (foot[0] + dx, foot[1] + 1.5, foot[2]), (foot[0] + dx + 0.5, foot[1], foot[2] - 4.5)),
                        OUT, bias=b)

    # ---- 선체
    hb, ht = hz + 2.0, hz + 21.0 - sag * 0.3
    body_c = drk(base, 0.62) if ph == 3 else base
    sc.frustum(25, 16, 17, 10.5, hb, ht, body_c)
    hc = (0, 0, (hb + ht) / 2)
    # 하단 띠, 상단 띠 (얇은 상자로 면을 덮는다)
    sc.frustum(25.6, 16.6, 24.2, 15.6, hb, hb + 4, drk(trim, 0.0), bias=0.4)
    if ph != 3:
        sc.frustum(17.8, 11.3, 17.0, 10.5, ht - 3, ht, trim, bias=0.4)
        for i in range(7):                                                # 성벽 총안 (윗면 가장자리)
            if ph == 1 and i == 4:
                continue
            xx = -15 + i * 5.0
            for yy in (-9.5, 9.5):
                sc.box(xx - 1.4, xx + 1.4, yy - 1.3, yy + 1.3, ht, ht + 3.4, lit(base, 0.12), bias=0.5)
        for xx in (-15.5, 15.5):
            for yy in (-5, 0, 5):
                sc.box(xx - 1.2, xx + 1.2, yy - 1.3, yy + 1.3, ht, ht + 3.0, lit(base, 0.12), bias=0.5)
        # 어깨 방패
        for sgn in (-1, 1):
            sc.frustum(0.1, 0.1, 0.1, 0.1, 0, 0, base) if False else None
            y0 = 17.5 * sgn
            sc.box(-13, 13, min(y0, y0 + 3 * sgn), max(y0, y0 + 3 * sgn), hb + 5, ht - 2, trim, bias=0.6)
            if ph == 2:
                sc.poly(((13, y0, hb + 6), (21, y0 + 2 * sgn, hb + 9), (13, y0, hb + 12)), steel, bias=0.7)
    else:
        for ax_, az_ in ((1, 1), (-1, 1)):                                # 골조의 X 보강재 (옆면)
            for sgn in (-1, 1):
                sc.line((-23 * ax_, 16.2 * sgn, hb + 1), (17 * ax_, 10.8 * sgn, ht - 1), lit(body_c, 0.35), 2, bias=0.8)
        cz = (hb + ht) / 2 + 4
        sc.fn((0, 0, ht + 1), lambda cv_, x, y: (K.glow(cv_, x, y - 2, 18 + pulse * 4, glowc, 130),
                                                   K.ball(cv_, x, y - 2, 6, drk(glowc, 0.5)),
                                                   D.circle(cv_, mix(glowc, (255, 255, 255), pulse * 0.5), (int(x), int(y - 2)), 4 + int(pulse)),
                                                   D.circle(cv_, (255, 255, 255), (int(x), int(y - 2)), 2)), bias=1.5)
        for k in range(6):                                                # 떨어져 나온 장갑판이 궤도를 돈다
            ang = t * 1.5 + k * TAU / 6
            px, py = math.cos(ang) * 29, math.sin(ang) * 22
            sc.box(px - 4, px + 4, py - 2.5, py + 2.5, ht + 3 + math.sin(ang * 2) * 2, ht + 5.5 + math.sin(ang * 2) * 2, base, bias=1.0)

    # ---- 표면 디테일 (이음·리벳·녹·성문)
    def hx_(z):
        return 25 - 8 * (z - hb) / (ht - hb)

    def hy_(z):
        return 16 - 5.5 * (z - hb) / (ht - hb)
    seam, riv = drk(body_c, 0.5), lit(body_c, 0.55)
    for sgn in (-1, 1):
        if not _vis(sc, (0, sgn, 0.4)):
            continue
        for xs in (-12, 0, 12):
            f0, f1 = hb + 5, ht - 2
            sc.line((xs * hx_(f0) / 25, sgn * hy_(f0), f0), (xs * hx_(f1) / 25, sgn * hy_(f1), f1), seam, 1, bias=0.6)
        for xx in range(-21, 22, 4):
            zz = hb + 6.5
            q = (xx * hx_(zz) / 25, sgn * hy_(zz), zz)
            sc.line(q, q, riv, 1, bias=0.7)
        if ph == 1:
            for xs, zz, w_, h_ in ((-14, 11, 5, 3), (4, 8, 4, 5), (14, 14, 3, 2)):
                z0_, z1_ = hb + zz, hb + zz + h_
                for_ = [(xs * hx_(zz + hb) / 25, sgn * hy_(z0_), z0_), ((xs + w_) * hx_(zz + hb) / 25, sgn * hy_(z0_), z0_),
                        ((xs + w_) * hx_(zz + hb) / 25, sgn * hy_(z1_), z1_), (xs * hx_(zz + hb) / 25, sgn * hy_(z1_), z1_)]
                sc.face(for_, (140, 76, 50), hc, 0.5)
    if _vis(sc, (1, 0, 0.45)) and ph != 3:                                 # 앞면 성문 아치
        zb, zt = hb + 4, ht - 4
        sc.face(((hx_(zb) + 0.1, -9, zb), (hx_(zb) + 0.1, 9, zb), (hx_(zt) + 0.1, 7.5, zt), (hx_(zt) + 0.1, -7.5, zt)), (30, 24, 42), hc, 0.35)
        for yy in (-9.6, 9.6):
            sc.line((hx_(zb) + 0.2, yy, zb), (hx_(zt) + 0.2, yy * 0.84, zt), lit(trim, 0.45), 2, bias=0.5)
    for xx in (-9, -3, 3, 9):                                              # 윗면 환기구
        if ph != 3:
            sc.box(xx - 1.6, xx + 1.6, -3.5, 3.5, ht, ht + 0.8, drk(base, 0.6), bias=0.45)

    # ---- 앞면: 성문 아치 + 외눈 렌즈
    gz = (hb + ht) / 2 - 1
    ex_ = 21.0
    sc.fn((ex_, 0, gz), lambda cv_, x, y: _eye(cv_, x, y, e, trim, glowc, pulse, wind, stun, t, st, hd), bias=1.2)
    if ph == 1 and not (e["exp"] > 0 or stun):                              # 닫힌 쇠창살 (눈 아래 문)
        for yy in (-5, -2.5, 0, 2.5, 5):
            sc.line((ex_ + 0.3, yy, hb + 3), (ex_ - 1.8, yy, gz - 5), trim, 2, bias=1.1)

    # ---- 드릴 파일벙커 (진행 방향)
    L = 14.0 + (16.0 + math.sin(t * 22) * 1.2 if wind else 0.0)
    a0 = (24.0, 0, hb + 7)
    a1 = (24.0 + L, 0, hb + 7 - (0.5 if wind else 0))
    sc.caps((22.5, 0, hb + 7), (25.5, 0, hb + 7), 10.5, 9.5, trim, bias=1.4)
    sc.caps((25, 0, hb + 7), a1, 8.0, 3.2, steel, bias=1.45)
    tip = (a1[0] + 6.0, 0, a1[2])
    sc.poly(((a1[0], -2.5, a1[2] + 0.3), (a1[0], 2.5, a1[2] + 0.3), tip), (236, 242, 255), bias=1.5)
    for i in range(4):                                                      # 회전 나선
        f = ((i + t * (8 if wind else 3)) % 4) / 4
        px = 26 + (L - 2) * f
        w_ = 7.0 * (1 - f * 0.55) / 2
        sc.line((px, -w_ * 0.85, hb + 7 + w_ * 0.5), (px + 1.6, w_ * 0.85, hb + 7 - w_ * 0.5), drk(steel, 0.5), 1, bias=1.55)
    if wind:
        sc.fn((tip[0], 0, tip[2]), lambda cv_, x, y: (K.glow(cv_, x, y, 14, (255, 90, 70), 190), D.circle(cv_, (255, 150, 120), (int(x), int(y)), 2 + int(t * 20) % 2)), bias=1.8)

    # ---- 1페이즈: 낡은 깃발
    if ph == 1:
        bx = -15.0
        sc.caps((bx, 0, ht), (bx, 0, ht + 17), 2.2, 1.6, (170, 170, 186), bias=1.0)
        w1_, w2_ = math.sin(t * 5) * 2.6, math.sin(t * 5 + 1) * 2.6
        sc.poly(((bx, 0, ht + 17), (bx - 3.5 - w1_ * 0.3, 8.5 + w1_, ht + 16 + w2_ * 0.4), (bx - 3.0, 6.5 + w2_, ht + 11.5),
                 (bx - 3.5, 9.5 + w1_, ht + 8.5 + w1_ * 0.3), (bx, 0, ht + 7)), (160, 42, 48), bias=1.0)
    # ---- 2페이즈: 등 포탑 + 배기 증기
    if ph == 2:
        ta = e["fa"] - hd                                                   # 몸 기준 조준 각도
        rc = math.sin(t * 40) * 1.6 if stt == "turret" else 0.0
        tz = ht + 5
        sc.ball((-4, 0, tz), 6.5, base, bias=1.0)
        bl = 15 + rc
        tipb = (-4 + math.cos(ta) * (6 + bl), math.sin(ta) * (6 + bl), tz + 1.5 + 0.5)
        sc.caps((-4, 0, tz + 1), tipb, 6.0, 5.0, trim, bias=1.05)
        sc.caps((-4 + math.cos(ta) * 10, math.sin(ta) * 10, tz + 1.5), tipb, 7.0, 7.0, steel, bias=1.1)
        if stt == "turret" and int(t * 30) % 2:
            sc.fn(tipb, lambda cv_, x, y: K.glow(cv_, x, y, 12, (255, 230, 150), 230), bias=1.9)
        for yy in (-9, 9):
            sc.box(-13, -9, yy - 2, yy + 2, ht - 1, ht + 6, trim, bias=0.9)
            sc.fn((-11, yy, ht + 7), lambda cv_, x, y, yy=yy: K.puff(cv_, x, y, t, (206, 212, 230), 4, 14, 0.9, yy, 3), bias=2.0)
    # ---- 3페이즈: 후방 분사
    if ph == 3:
        for k, yy in enumerate((-6.0, 6.0)):
            sc.fn((-27, yy, hb + 6), lambda cv_, x, y, k=k, hd_=hd: K.jet(cv_, x, y, -math.cos(hd_), -math.sin(hd_) * SE_, t,
                                                                          20 if moving else 11, 7, k, (255, 150, 60)), bias=-3)
    # ---- 상태 연출
    if stun:
        sc.fn((0, 0, ht + 8), lambda cv_, x, y: [cv_.fill((255, 235, 110), (int(x + math.cos(t * 4 + k * 2.09) * 13), int(y - 4 + math.sin(t * 4 + k * 2.09) * 4), 3, 3)) for k in range(3)], bias=3)
        for xx in (-8, 8):
            sc.fn((xx, 0, ht), lambda cv_, x, y, xx=xx: K.puff(cv_, x, y, t, (214, 218, 232), 4, 18, 1.2, xx, 3), bias=3)
        sc.fn((0, 0, hb + 8), lambda cv_, x, y: K.sparks(cv_, x, y, t, (255, 220, 120), 5, 20, 7, 0, 2), bias=3)
    if dash:
        sc.fn((-26, 0, 1), lambda cv_, x, y: K.puff(cv_, x, y, t, (200, 180, 158), 5, 9, 2.5, 5, 3), bias=-4)
    if wind and int(t * 14) % 2:
        sc.fn((0, 0, hb), lambda cv_, x, y: D.rect(cv_, (255, 90, 80), (int(x) - 40, int(y) - 46, 80, 62), 1), bias=4)
    sc.flush()
    if e["fl"] > 0:
        K.flash(cv)
    return cv


SE_ = R3.SE


def _vis(sc, n):
    w = sc.rot(n)
    return w[0] * R3.VIEW[0] + w[1] * R3.VIEW[1] + w[2] * R3.VIEW[2] > 0.0


def _eye(cv, x, y, e, trim, glowc, pulse, wind, stun, t, st, hd):
    """앞면 외눈: 몸이 돌아선 방향에 맞춰 시선이 따라간다"""
    if math.sin(hd) * R3.CE < -0.2:
        return                                                       # 등을 보이고 있으면 눈이 가려진다
    ic = (255, 255, 255) if (wind and int(t * 16) % 2) else mix(glowc, (255, 244, 210), pulse * 0.5)
    ox = math.cos(e["fa"] - hd) * 1.6
    K.ball(cv, x, y, 7.0, drk(trim, 0.25))
    K.glow(cv, x + ox, y, 12, glowc, 110 if not stun else 40)
    D.circle(cv, (24, 18, 34), (int(x), int(y)), 4)
    D.circle(cv, ic, (int(x + ox), int(y)), 2 + (1 if pulse > 0.5 else 0))
    cv.fill((255, 255, 255), (int(x + ox) - 1, int(y) - 2, 1, 1))
