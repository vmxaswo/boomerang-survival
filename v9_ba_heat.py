"""수석 정비관 오버히트 - 열·냉기 이중 구동 6족 보일러 거미 (v9_ba_heat.py)  3D 리그 버전 (v9_ba_r3, 최종 크기 1:1 도트)
 몸통 = 가로 보일러 탱크(앞쪽 절반은 열, 뒤쪽 절반은 냉기로 갈라진 이중 구동), 다리 여섯은 2본 IK 삼각 보행,
 양팔은 불 토치(오른쪽)·냉동 노즐(왼쪽), 머리 센서가 플레이어를 노려본다.
 1 과열(붉게) / 2 극저온(성에·얼음 결정) / 3 열폭주(점검창 온도에 따라 균열·연기) / 4 초고온 플라즈마(백열 + 불꽃 오라)
 정지(stun) = 푸른 냉각 상태로 주저앉아 증기를 뿜음, torch = 두 팔을 쭉 뻗어 불꽃·냉기를 동시에 분사, leap = 도약"""
import math

import pygame

import v9_ba_kit as K
import v9_ba_r3 as R3
from v9_ba_kit import D, OUT, TAU, drk, lit, mix

METAL = (120, 126, 152)
COLD = (150, 214, 255)
HIPS = ((13, 1), (0, 1), (-13, 1), (13, -1), (0, -1), (-13, -1))   # (x, 좌우 부호)
LEG_OFF = (0.0, 0.5, 0.0, 0.5, 0.0, 0.5)                              # 삼각 보행: 앞·뒤 같은 쪽, 가운데 반대쪽


def _palette(ph, stun, heat):
    if stun:
        return 0.15, 0.6, (130, 190, 240), (92, 112, 156)
    if ph == 1:
        return 1.0, 0.2, (255, 120, 70), (122, 100, 110)
    if ph == 2:
        return 0.2, 1.0, (255, 150, 90), (100, 130, 166)
    if ph == 3:
        return 1.0, 0.8, mix((255, 150, 70), (255, 50, 40), heat), mix((112, 94, 102), (192, 74, 66), heat)
    return 1.0, 1.0, (255, 255, 235), (238, 236, 248)


def _arm(sc, side, kind, inten, hotc, body, ext, torch, t, seed):
    """side: +1 = 오른쪽(냉동), -1 = 왼쪽(불). 팔 끝에서 분사한다"""
    sh = (14.0, side * 11.0, 31.0)
    sw = math.sin(t * 3 + seed) * 1.2
    hand = (24.0 + ext, side * (17.0 - ext * 0.18), 26.0 + sw)
    elb = (19.0 + ext * 0.4, side * 21.0, 33.0 + sw * 0.5)
    metal = drk(body, 0.2)
    sc.caps(sh, elb, 6.0, 5.0, metal, bias=0.8)
    sc.caps(elb, hand, 5.0, 4.4, lit(metal, 0.1), bias=0.8)
    sc.ball(elb, 3.6, drk(body, 0.35), bias=0.85)
    cc = hotc if kind == "fire" else COLD
    tip = (hand[0] + 6.0, hand[1], hand[2])
    sc.caps(hand, tip, 7.0, 6.0, drk(body, 0.42), bias=0.9)
    sc.ball(tip, 2.4, cc if inten > 0.3 else drk(cc, 0.6), bias=0.95)
    ux, uy, _ = R3.screen_dir(sc, tip, (1, 0, 0))
    if inten < 0.3:
        if kind == "fire":
            sc.fn(tip, lambda c_, x, y: K.flame(c_, x, y, t, 5, 4, seed, hotc), bias=1.2)
        return
    ln = (10 + 15 * inten) * (1.6 if torch else 1.0)
    if kind == "fire":
        sc.fn(tip, lambda c_, x, y: (K.jet(c_, x + ux * 3, y + uy * 3, ux, uy, t, ln, 7 if torch else 6, seed, hotc),
                                     K.glow(c_, x + ux * ln * 0.4, y + uy * ln * 0.4, 14, hotc, 110)), bias=1.2)
    else:
        def ice(c_, x, y):
            K.jet(c_, x + ux * 3, y + uy * 3, ux, uy, t, ln * 0.9, 6, seed, (130, 206, 255))
            for i in range(5):
                f = (t * 1.4 + i / 5 + seed * 0.2) % 1.0
                c_.fill((226, 244, 255), (int(x + ux * (4 + f * ln) - uy * math.sin(f * 6 + i) * 5),
                                          int(y + uy * (4 + f * ln) + ux * math.sin(f * 6 + i) * 5), 2, 2))
        sc.fn(tip, ice, bias=1.2)


def draw(e):
    ph, t = e["phase"], e["an"]
    stun = e["stun"] > 0
    torch = e["st"] == "torch"
    heat = min(1.0, e["heat"] / 100.0)
    fire_i, ice_i, hotc, body = _palette(ph, stun, heat)
    pulse = 0.5 + 0.5 * math.sin(t * 6)
    moving = e["mv"] or e["st"] == "leap"
    st, dt = R3.anim(e, "_r3")
    R3.turn_toward(st, e.get("lk", 0.0), dt, 6.0)
    hd = st["hd"]
    vf = st["vx"] * math.cos(hd) + st["vy"] * math.sin(hd)
    st["g"] += 0.6 * vf * dt / 12.0
    amp = min(1.0, st["sp"] / 24.0)
    g = st["g"]
    lift = float(e.get("lift", 0))
    cv = R3.canvas("heat")
    K.shadow_at(cv, R3.R3X, R3.R3Y, 34, 9, max(30, 80 - int(lift * 2)))
    sag = 6.0 if stun else 0.0
    bob = (math.sin(g * 12.566) * 1.3 * amp) if moving else math.sin(t * 2.4) * 0.8
    jit = math.sin(t * 55) * 0.8 if (ph == 3 and heat > 0.7 and not stun) else 0.0
    sc = R3.Scene(cv, hd, z0=lift)
    zc = 27.0 - sag + bob                                          # 보일러 중심 높이

    # ---- 4페이즈: 백열 오라 (뒤쪽에 깐다)
    if ph == 4:
        sc.fn((0, 0, zc), lambda c_, x, y: (K.glow(c_, x, y, 44, (255, 220, 170), 110),
                                            [K.flame(c_, x + (i - 3) * 8, y - 10 - abs(i - 3), t, 20 - abs(i - 3) * 2, 8, i, (255, 240, 200)) for i in range(7)],
                                            [c_.fill((255, 255, 255), (int(x + math.cos(t * 2.5 + i * TAU / 18) * 40),
                                                                       int(y + math.sin(t * 2.5 + i * TAU / 18) * 22), 2, 2)) for i in range(18)]), bias=-8)

    # ---- 다리 여섯
    for i, (hx, sgn) in enumerate(HIPS):
        ph_ = (g + LEG_OFF[i]) % 1.0
        if ph_ < 0.65:
            fxs, lf = 0.5 - ph_ / 0.65, 0.0
        else:
            u = (ph_ - 0.65) / 0.35
            fxs, lf = -0.5 + u, math.sin(math.pi * u)
        stride = 8.0 * amp
        foot = (hx * 1.15 + fxs * stride, sgn * (27.0 + (3 if stun else 0)), lf * (3.0 + stride * 0.3))
        hip = (hx, sgn * 9.0, zc - 7 + jit)
        knee, foot = R3.leg_ik(hip, foot, 15.0, 15.0, (0.0, sgn * 0.5, 1.0))
        c = drk(body, 0.3 + 0.1 * (i % 2))
        sc.caps(hip, knee, 6.4, 5.4, c, bias=-1.5)
        sc.caps(knee, foot, 5.2, 2.4, drk(c, 0.15), bias=-1.5)
        sc.ball(knee, 3.3, mix(hotc if i % 2 else COLD, c, 0.4), bias=-1.4)
        sc.ball(foot, 1.9, OUT, bias=-1.4)

    # ---- 보일러 본체: 뒤쪽 냉기 / 앞쪽 열
    wc = mix(body, hotc, 0.30 * fire_i)
    cc = mix(body, COLD, 0.36 * ice_i)
    bz = zc + jit
    sc.caps((-22, 0, bz), (0, 0, bz), 29.0, 30.0, cc, bias=0.0)
    sc.caps((0, 0, bz), (22, 0, bz), 30.0, 28.0, wc, bias=0.02)
    for xx in (-13, 13):                                           # 보강 띠 + 리벳
        sc.caps((xx, 0, bz), (xx + 1.6, 0, bz), 31.4, 31.4, drk(body, 0.4), bias=0.1)
        for k in range(7):
            ang = -0.4 + k * 0.5
            q = (xx + 0.8, math.cos(ang) * 14.5, bz + math.sin(ang) * 14.5)
            sc.line(q, q, lit(body, 0.6), 1, bias=0.2)
    # 점검창 (온도) - 보이는 쪽 옆면
    lvl = int(7 * (heat if ph == 3 else 0.55 if ph != 2 else 0.35))
    liq = COLD if (ph == 2 or stun) else hotc
    for sg in (-1, 1):
        if not R3.visible(sc, (0, sg, 0.3)):
            continue
        sc.fn((0, sg * 13.5, bz - 1), lambda c_, x, y: (K.box(c_, x - 6, y - 4, 12, 10, (24, 20, 40)),
                                                       c_.fill(liq, (int(x - 5), int(y + 5 - lvl), 10, lvl)),
                                                       c_.fill(lit(liq, 0.6), (int(x - 5), int(y + 5 - lvl), 10, 1))), bias=0.5)

    # ---- 후면 방열 핀 + 배기
    spread = 7.0 if (stun or ph == 4 or heat > 0.85) else 4.5
    for i in range(5):
        fin = mix(METAL, hotc, 0.15 + 0.35 * fire_i * (0.5 + 0.5 * math.sin(t * 5 + i)))
        sc.box(-24 - spread, -22, -6, 6, bz - 12 + i * 5, bz - 9.4 + i * 5, fin, bias=-0.1)
    if ph >= 3 and not stun:
        bx_, by_, _ = R3.screen_dir(sc, (-26, 0, bz), (-1, 0, 0))
        for k, yy in enumerate((-4.0, 4.0)):
            sc.fn((-24 - spread, yy, bz - 2), lambda c_, x, y, k=k: K.jet(c_, x, y, bx_, by_, t, 13 + (9 if moving else 0), 6, k + 3, hotc), bias=-6)

    # ---- 굴뚝 + 압력계
    sc.caps((-9, 0, bz + 12), (-9, 0, bz + 24), 8.0, 8.0, METAL, bias=0.3)
    sc.caps((-9, 0, bz + 23), (-9, 0, bz + 25), 9.4, 9.4, drk(METAL, 0.5), bias=0.35)
    smoke = (222, 238, 252) if (stun or ph == 2) else (104, 98, 116)
    sc.fn((-9, 0, bz + 27), lambda c_, x, y: K.puff(c_, x, y, t, smoke, 4, 20, 1.0, 3, 3), bias=2)
    gz = bz + 13
    sc.ball((10, 0, gz), 5.4, (230, 232, 240), bias=0.5)
    gang = -2.4 + (heat * 2.4 if ph == 3 else 0.9 + 0.2 * math.sin(t * 3))
    sc.fn((10, 0, gz), lambda c_, x, y: (D.arc(c_, (230, 60, 50), pygame.Rect(int(x - 4), int(y - 4), 8, 8), 0.4, 1.4, 2),
                                         D.line(c_, (30, 24, 40), (int(x), int(y)), (int(x + math.cos(gang) * 4), int(y + math.sin(gang) * 4)), 1)), bias=0.9)

    # ---- 페이즈 장식
    if ph == 2:                                                    # 등에 돋은 얼음 결정
        for xs, ys, h_ in ((-14, -4, 14), (-3, 5, 18), (7, -6, 12), (14, 3, 15)):
            base_z = bz + 12
            sc.poly(((xs - 2.4, ys, base_z), (xs + 2.4, ys, base_z), (xs, ys, base_z + h_)), (204, 240, 255), bias=0.8)
            sc.poly(((xs, ys - 2.4, base_z), (xs, ys + 2.4, base_z), (xs, ys, base_z + h_ - 1)), (160, 214, 246), bias=0.75)
    if ph == 3 and heat > 0.4:                                     # 과열 균열 + 연기
        for k in range(1 + int(heat * 3)):
            xx = -12 + k * 10
            sc.line((xx, 9, bz + 12), (xx + 3, 14, bz + 4), hotc, 2, bias=0.7)
            sc.line((xx, -9, bz + 12), (xx + 3, -14, bz + 4), hotc, 2, bias=0.7)
        if heat > 0.6 and not stun:
            sc.fn((4, 0, bz + 14), lambda c_, x, y: K.puff(c_, x, y, t, (234, 124, 92), 3, 14, 1.6, 1, 3), bias=2)

    # ---- 머리 센서
    look = math.atan2(math.sin(e.get("lk", 0.0) - hd), math.cos(e.get("lk", 0.0) - hd))
    hx_, hz_ = 29.0, bz + 3
    sc.ball((hx_, 0, hz_), 7.4, METAL, bias=0.7)
    ic = mix(hotc, COLD, 0.5) if ph == 3 else (hotc if ph != 2 else COLD)
    sc.fn((hx_ + 4, 0, hz_), lambda c_, x, y: (K.glow(c_, x, y, 11, ic, 120), D.circle(c_, (20, 16, 32), (int(x), int(y)), 4),
                                               D.circle(c_, mix(ic, (255, 255, 255), 0.4 * pulse), (int(x + math.sin(look) * 1.5), int(y)), 2)), bias=1.0)

    # ---- 양팔
    ext = 12 if torch else 4 + math.sin(t * 3) * 1.6
    _arm(sc, 1, "ice", ice_i, hotc, body, ext, torch, t, 1)
    _arm(sc, -1, "fire", fire_i, hotc, body, ext + 1, torch, t, 2)

    if stun:
        for sx_ in (-12, 4):
            sc.fn((sx_, 0, bz + 14), lambda c_, x, y, sx_=sx_: K.puff(c_, x, y, t, (216, 232, 248), 4, 22, 1.4, sx_, 3), bias=3)
        sc.fn((0, 0, bz + 22), lambda c_, x, y: [c_.fill((220, 236, 250), (int(x + math.cos(t * 3 + k * 2.09) * 12), int(y + math.sin(t * 3 + k * 2.09) * 3), 3, 3))
                                                  for k in range(3)], bias=3)
    sc.flush()
    if e["fl"] > 0:
        K.flash(cv)
    return cv
