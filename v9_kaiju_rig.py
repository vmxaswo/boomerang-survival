"""v9 괴수 리그 (v9_kaiju_rig.py)  -  필드 보스 '탈라소르'를 '3D 뼈대 -> 쿼터뷰 도트'로 그리는 렌더러.
화룡 리그(v9_dragon_rig.py)와 같은 방식(마디 체인 + 2본 IK 다리 + 관절 날개, 바라보는 각도로 돌려 42도 내려다보는 시점에 투영,
먼 부위부터 그리기)으로 만들었고, 생김새는 '5등급 괴수 + 얼음 숨결의 거대 알파 드래곤' 컨셉이다.
 - 납작하고 넓은 머리, 아래턱에서 앞으로 휘어 솟는 거대한 엄니 두 개, 머리 뒤로 부채처럼 펼쳐지는 가시 왕관(펼침 정도 = crown)
 - 굵고 긴 몸통, 등을 따라 솟은 얼음 끝 가시, 등을 덮는 장갑판 3장(깨지면 푸른 균열의 약점이 드러난다)
 - 서로 꼬여 흔들리는 가시 꼬리 세 갈래, 갈고리 발톱이 달린 굵은 다리 넷, 푸른 핏줄이 흐르는 거대한 막 날개
 - 눈·몸의 무늬·가시 끝이 전기 같은 푸른빛으로 맥동한다
이 모듈은 게임 코드에 의존하지 않는다 (pygame 과 math 만 쓴다)."""
import math

import pygame

D = pygame.draw
SC = pygame.SRCALPHA
OL = (14, 12, 26)
CW, CH, CX, CY = 560, 470, 280, 250                    # 도화지 크기와 중심(= 괴수 좌표)
GY0 = 20                                               # 중심에서 지면까지 (화면 픽셀)
HS = 1.5                                               # 머리 배율
SCALE = 1.0                                            # 모델 단위 -> 픽셀
_EL = math.radians(42)
SE, CE = math.sin(_EL), math.cos(_EL)
_GL, _B = {}, {}

DEF = dict(alt=0.0, bz=19.0, pitch=0.0, roll=0.0, hx=52.0, hz=32.0, hp=-0.1, hyaw=0.0, mouth=0.05, nk=1.0,
           wfold=0.95, wamp=0.0, wfreq=1.0, wb0=0.0, wsw=0.0, tamp=1.0, tlift=0.0, tcurl=0.0, tfreq=1.4, tsplit=0.0,
           tuck=0.0, brace=0.0, fz=0.0, fxo=0.0, scr=0.0, glow=0.0, chest=0.0, crown=0.25, low=0.0)
RATE = dict(alt=3.0, wfold=7.0, glow=4.0, tfreq=4.0, wfreq=5.0, hyaw=10.0, crown=6.0)


def new_state():
    return dict(ps=dict(DEF), wph=0.0, tph=0.0, g=0.0, sp=0.0, amp_f=0.0, stride=16.0, turn=0.0)


def update(st, tg, dt, rate, vf, sp, turn):
    """tg: 목표 포즈, rate: 섞는 속도, vf: 앞방향 이동속도, sp: 속력, turn: 회전속도(rad/s)"""
    ps = st["ps"]
    for key, v in tg.items():
        if key in ps:
            ps[key] += (v - ps[key]) * (1 - math.exp(-dt * RATE.get(key, rate)))
    st["wph"] += dt * ps["wfreq"] * 6.2832
    st["tph"] += dt * ps["tfreq"]
    stride = min(46.0, max(16.0, 16 + 0.08 * sp))
    st["stride"], st["sp"] = stride, sp
    st["amp_f"] = min(1.0, sp / 20.0)
    st["g"] += 0.6 * vf * dt / stride
    st["turn"] += (turn - st["turn"]) * (1 - math.exp(-dt * 5))


# ================================================================= 작은 도구
def dk(c, f=0.6):
    return tuple(int(v * f) for v in c)


def mix(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def lerp3(a, b, f):
    return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f)


def rx(v, s, b):
    """v 를 앞축 기준으로 b 만큼 들어 올린다 (s: 좌우 부호)"""
    w = v[1] * s
    cb, sb = math.cos(b), math.sin(b)
    return (v[0], (w * cb - v[2] * sb) * s, v[2] * cb + w * sb)


def unit(v):
    l = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]) or 1.0
    return (v[0] / l, v[1] / l, v[2] / l)


def gl(r, col, a):
    r, a = max(2, int(r) // 2 * 2), max(0, min(255, int(a))) // 20 * 20
    if a <= 0:
        return None
    if "b" not in _B:
        s = pygame.Surface((96, 96), SC)
        for y in range(96):
            for x in range(96):
                d = math.hypot(x - 47.5, y - 47.5) / 48
                s.set_at((x, y), (255, 255, 255, int(255 * max(0.0, 1 - d) ** 1.6) if d < 1 else 0))
        _B["b"] = s
    key = (r, col, a)
    if key not in _GL:
        s = pygame.transform.smoothscale(_B["b"], (r * 2, r * 2))
        s.fill(col + (a,), special_flags=pygame.BLEND_RGBA_MULT)
        _GL[key] = s
    return _GL[key]


def blit_gl(surf, x, y, r, col, a):
    s = gl(r, col, a)
    if s:
        surf.blit(s, (int(x) - s.get_width() // 2, int(y) - s.get_height() // 2))


# ================================================================= 프리미티브 그리기
def fill_sph(cv, xi, yi, ri, sty):
    D.circle(cv, sty[0], (xi, yi), ri)
    D.circle(cv, sty[1], (xi - ri // 8, yi - ri // 6), max(1, int(ri * 0.9)))
    if ri >= 4:
        D.circle(cv, sty[2], (xi - ri // 3, yi - ri // 2), max(1, int(ri * 0.4)))


def d_sph(cv, x, y, r, sty):
    xi, yi, ri = int(x), int(y), max(1, int(r))
    D.circle(cv, OL, (xi, yi), ri + 1)
    fill_sph(cv, xi, yi, ri, sty)


def d_caps(cv, segs, fill, hi):
    pts = []
    for x1, y1, r1, x2, y2, r2 in segs:
        n = max(1, int(math.hypot(x2 - x1, y2 - y1) / max(1.0, min(r1, r2) * 0.8)))
        for i in range(n + 1):
            f = i / n
            pts.append((x1 + (x2 - x1) * f, y1 + (y2 - y1) * f, r1 + (r2 - r1) * f))
    for x, y, r in pts:
        D.circle(cv, OL, (int(x), int(y)), int(r) + 1)
    for x, y, r in pts:
        D.circle(cv, fill, (int(x), int(y)), max(1, int(r)))
    if hi:
        for x, y, r in pts:
            if r >= 2.5:
                D.circle(cv, hi, (int(x - r * 0.3), int(y - r * 0.35)), max(1, int(r * 0.45)))


def d_chain(cv, items, spikes, dots):
    for x, y, r, sty, dep in items:
        D.circle(cv, OL, (int(x), int(y)), int(r) + 1)
    for x, y, r, sty, dep in sorted(items, key=lambda a: a[4]):
        fill_sph(cv, int(x), int(y), max(1, int(r)), sty)
    for pts, col in spikes:
        D.polygon(cv, col, pts)
        D.polygon(cv, OL, pts, 1)
    for x, y, r, col in dots:
        D.circle(cv, col, (int(x), int(y)), r)


def d_poly(cv, d):
    pts, fill, ol, w = d
    D.polygon(cv, fill, pts)
    if ol:
        D.polygon(cv, ol, pts, w)


def d_wing(cv, w):
    S_, E_, W_, tips, scal, Bk = w["S"], w["E"], w["W"], w["tips"], w["scal"], w["Bk"]
    if w["folded"]:                                          # 접힌 날개: 하나의 어두운 덩어리 + 뼈
        mass = [S_, E_, W_, tips[0], tips[1], tips[2], tips[3], Bk]
        D.polygon(cv, w["wd"], mass)
        D.polygon(cv, OL, mass, 1)
        for sc_ in scal:
            D.line(cv, w["vein"], W_, sc_, 1)
        D.line(cv, OL, S_, E_, 5)
        D.line(cv, w["bone"], S_, E_, 3)
        D.circle(cv, OL, (int(W_[0]), int(W_[1])), 4)
        D.circle(cv, w["bone"], (int(W_[0]), int(W_[1])), 3)
        return
    wc, wd, wl, bone = w["wc"], w["wd"], w["wl"], w["bone"]
    D.polygon(cv, wd, [S_, W_, tips[3], Bk])
    for i in range(3):
        D.polygon(cv, wl if i % 2 else wc, [W_, tips[i], scal[i], tips[i + 1]])
    outline = [S_, E_, W_, tips[0], scal[0], tips[1], scal[1], tips[2], scal[2], tips[3], Bk]
    D.polygon(cv, OL, outline, 1)
    for i in range(3):                                       # 막을 흐르는 푸른 핏줄
        mid = ((tips[i][0] + tips[i + 1][0]) / 2, (tips[i][1] + tips[i + 1][1]) / 2)
        D.line(cv, w["vein"], W_, mid, 1)
        D.line(cv, w["vein_d"], scal[i], mid, 1)
    D.line(cv, w["vein"], S_, tips[3], 1)
    D.line(cv, OL, S_, E_, 6)
    D.line(cv, bone, S_, E_, 4)
    D.line(cv, OL, E_, W_, 5)
    D.line(cv, bone, E_, W_, 3)
    for t_ in tips:
        D.line(cv, OL, W_, t_, 2)
        D.line(cv, bone, W_, t_, 1)
        D.circle(cv, w["spike"], (int(t_[0]), int(t_[1])), 1)
    D.circle(cv, OL, (int(W_[0]), int(W_[1])), 5)
    D.circle(cv, bone, (int(W_[0]), int(W_[1])), 4)
    D.polygon(cv, w["claw"], [(W_[0] - 3, W_[1] - 1), (W_[0] + 1, W_[1] - 12), (W_[0] + 5, W_[1])])     # 손목 가시
    D.polygon(cv, OL, [(W_[0] - 3, W_[1] - 1), (W_[0] + 1, W_[1] - 12), (W_[0] + 5, W_[1])], 1)


# ================================================================= 한 프레임
def draw(cv, st, P, ph, t, heading, armor=0):
    """cv(도화지)에 괴수를 그리고 기준점(anchors)을 돌려준다.  기준점은 모두 도화지 좌표. armor: 남은 장갑판 수(0~3)"""
    ps = st["ps"]
    cyw, syw = math.cos(heading), math.sin(heading)
    cp, sp_ = math.cos(ps["pitch"]), math.sin(ps["pitch"])
    cr, sr = math.cos(ps["roll"]), math.sin(ps["roll"])
    amp_f, g = st["amp_f"], st["g"]
    bob = math.sin(12.566 * g) * (0.6 + min(2.5, st["sp"] * 0.01)) * amp_f
    sway = math.sin(6.283 * g) * 2.0 * amp_f
    zc = ps["bz"] + ps["alt"] + bob + math.sin(t * 1.6) * 0.5 - ps["low"] * 6
    CYG = CY + GY0

    def Bf(x, y, z):
        x2 = x * cp - z * sp_
        z2 = z * cp + x * sp_
        return (x2, y * cr - z2 * sr + sway, z2 * cr + y * sr + zc)

    def Pj(p):
        wx = p[0] * cyw - p[1] * syw
        wy = p[0] * syw + p[1] * cyw
        return (CX + wx * SCALE, CYG + (wy * SE - p[2] * CE) * SCALE, wy * CE + p[2] * SE)

    def T(x, y, z):
        return Pj(Bf(x, y, z))

    base, dark, hi, belly, belly_d = P["base"], P["dark"], P["hi"], P["belly"], P["belly_d"]
    deep, horn, eye, spike = P["deep"], P["horn"], P["eye"], P["spike"]
    vein, vein_d = P["vein"], P["vein_d"]
    sty_b = (belly_d, base, hi)
    sty_d = (deep, dark, base)
    Q, GLW = [], []
    bdep = T(0, 0, 0)[2]
    pulse = 0.5 + 0.5 * math.sin(t * 3.2)
    veinc = mix(vein_d, vein, pulse * (0.6 + 0.4 * min(1.0, ps["glow"] + 0.3)))
    chest_k = 1.0 + ps["chest"]

    # ------------------------------------------------ 몸통 (굵고 긴 등)
    tor = [(26, 0, 1, 13.5 * chest_k), (14, 0, 0, 15.5 * chest_k), (1, 0, 0, 15.0), (-12, 0, -1, 13.5), (-23, 0, -2, 11.0)]
    items, spikes, dots = [], [], []
    for x, y, z, r in tor:
        c = T(x, y, z)
        items.append((c[0], c[1], r * SCALE, sty_b, c[2]))
    for i in range(11):                                       # 등 가시 (얼음 끝)
        x = 26 - i * 5.2
        z0 = 15.5 if 2 <= i <= 7 else 13.5 - abs(i - 5) * 0.2
        h = 6 + 7 * math.sin((i + 0.5) / 11 * math.pi)
        a, b_, c = T(x - 2.6, 0, z0), T(x + 2.6, 0, z0), T(x - 2.4, 0, z0 + h)
        spikes.append(([a[:2], c[:2], b_[:2]], dark if i % 2 else deep))
        tip = T(x - 2.4, 0, z0 + h)
        dots.append((tip[0], tip[1], 1, spike))
        if ph >= 2 or ps["glow"] > 0.5:
            GLW.append((tip[0], tip[1], 6, P["glow"], 70 + 60 * ps["glow"]))
    for i in range(7):                                        # 옆구리의 푸른 발광 무늬 (생체 발광)
        x = 20 - i * 6.5
        for sd in (-1, 1):
            c = T(x, sd * (13.5 - abs(i - 3) * 0.6), 4.0 + (i % 2) * 2)
            dots.append((c[0], c[1], 2 if ph >= 2 else 1, veinc))
    Q.append((bdep, 3, (items, spikes, dots)))
    # 장갑판 (등의 넓은 골판): 남은 수만큼, 깨진 자리는 푸른 균열이 빛난다
    for k, (px, w0, l0) in enumerate(((14, 12.5, 9.0), (1, 14.0, 9.5), (-12, 12.0, 8.5))):
        zt = 16.5 if k != 1 else 17.5
        quad = [T(px + l0, -w0 * 0.75, zt - 2), T(px + l0 * 0.6, w0 * 0.85, zt - 1), T(px - l0, w0 * 0.75, zt - 2.5),
                T(px - l0 * 0.7, -w0 * 0.9, zt - 1.5)]
        dep = sum(q[2] for q in quad) / 4 + 0.6
        if k < armor:
            Q.append((dep, 1, ([q[:2] for q in quad], P["plate"], OL, 1)))
            ridge = T(px + l0 * 0.8, 0, zt + 1), T(px - l0 * 0.8, 0, zt + 1)
            Q.append((dep + 0.05, 4, (ridge[0][:2], ridge[1][:2], mix(P["plate"], (255, 255, 255), 0.35), 2)))
            for sd in (-1, 1):
                r_ = T(px, sd * w0 * 0.55, zt)
                Q.append((dep + 0.06, 0, (r_[0], r_[1], 1.6, (P["plate_d"], P["plate"], mix(P["plate"], (255, 255, 255), 0.5)))))
        else:
            c1, c2, c3 = T(px + l0 * 0.6, -3, zt - 2), T(px, 2, zt - 1), T(px - l0 * 0.6, -1, zt - 2)
            Q.append((dep, 4, (c1[:2], c2[:2], veinc, 2)))
            Q.append((dep, 4, (c2[:2], c3[:2], veinc, 2)))
            GLW.append((c2[0], c2[1], 12, P["glow"], 110 + 70 * pulse))
    sc = T(0, 0, 0)

    # ------------------------------------------------ 다리 (2본 IK, 갈고리 발톱)
    stride = st["stride"] * amp_f
    feet, legs = [], []
    for i, (front, s, off) in enumerate(((1, 1, 0.0), (0, -1, 0.25), (1, -1, 0.5), (0, 1, 0.75))):
        hxl, hyl, hzl = (15, s * 11.0, -5) if front else (-16, s * 12.0, -4)
        Hp = Bf(hxl, hyl, hzl)
        rest_x = (19 + ps["brace"] * 5) if front else (-19 - ps["brace"] * 3)
        rest_y = s * ((21 if front else 22) + ps["brace"] * 6 + ps["low"] * 6)
        ph_ = (g + off) % 1.0
        if ph_ < 0.65:
            fxs, lift = 0.5 - ph_ / 0.65, 0.0
        else:
            u = (ph_ - 0.65) / 0.35
            fxs, lift = -0.5 + u, math.sin(math.pi * u)
        fx_, fy_, fz_ = rest_x + fxs * stride, rest_y, lift * (5 + stride * 0.2)
        if front:
            fx_ += ps["fxo"] + math.sin(t * 24) * ps["scr"]
            fz_ += ps["fz"] + max(0.0, math.cos(t * 24)) * ps["scr"] * 0.7
        if ps["tuck"] > 0.01:
            tk = Bf(8, s * 10, -14) if front else Bf(-12, s * 11, -13)
            fx_, fy_, fz_ = fx_ + (tk[0] - fx_) * ps["tuck"], fy_ + (tk[1] - fy_) * ps["tuck"], fz_ + (tk[2] - fz_) * ps["tuck"]
        dx, dy, dz = fx_ - Hp[0], fy_ - Hp[1], fz_ - Hp[2]
        L1, L2 = 17.0, 16.0
        L = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
        if L > L1 + L2 - 0.6:
            k = (L1 + L2 - 0.6) / L
            dx, dy, dz, L = dx * k, dy * k, dz * k, L * k
            fx_, fy_, fz_ = Hp[0] + dx, Hp[1] + dy, Hp[2] + dz
        a_ = (L1 * L1 - L2 * L2 + L * L) / (2 * L)
        h_ = math.sqrt(max(0.0, L1 * L1 - a_ * a_))
        bd = (-0.3, s * 1.0, 0.5) if front else (0.6, s * 0.9, 0.6)
        dd = (dx * bd[0] + dy * bd[1] + dz * bd[2]) / (L * L)
        bd = unit((bd[0] - dx * dd, bd[1] - dy * dd, bd[2] - dz * dd))
        K = (Hp[0] + dx * a_ / L + bd[0] * h_, Hp[1] + dy * a_ / L + bd[1] * h_, Hp[2] + dz * a_ / L + bd[2] * h_)
        pH, pK, pF = Pj(Hp), Pj(K), Pj((fx_, fy_, fz_))
        dep = (pH[2] + pK[2] + pF[2]) / 3
        far = dep < bdep
        col, hic, cold = (dk(base, 0.74), dk(hi, 0.74), dk(dark, 0.74)) if far else (base, hi, dark)
        rt = 7.8 if not front else 6.8
        segs = [(pH[0], pH[1], rt * SCALE, pK[0], pK[1], (rt - 1.6) * SCALE), (pK[0], pK[1], (rt - 1.6) * SCALE, pF[0], pF[1], 4.0 * SCALE)]
        claws = []
        for kk in (-1, 0, 1):                                 # 갈고리 발톱 셋
            c0 = Pj((fx_ + 1, fy_ + kk * 2.8, fz_ + 1.2))
            c1 = Pj((fx_ + 7.5, fy_ + kk * 3.8, fz_ + 1.6))
            c2 = Pj((fx_ + 9.5, fy_ + kk * 4.2, fz_ - 1.0))
            c3 = Pj((fx_ + 1, fy_ + kk * 2.8 + 1.4, fz_ + 1.2))
            claws.append(([c0[:2], c1[:2], c2[:2], c3[:2]], horn))
        knee_glow = Pj(K)
        legs.append((dep, segs, col, hic, cold, claws, pF, knee_glow))
        feet.append((pF[0], pF[1]))
    for dep, segs, col, hic, cold, claws, pF, kg in legs:
        Q.append((dep, 7, (segs, col, hic, cold, claws, pF, kg)))

    # ------------------------------------------------ 가시 꼬리 세 갈래 (서로 꼬이며 흔들린다)
    N = 12
    ld = 1.0 - min(1.0, ps["alt"] / 22.0) * 0.6
    tails_tip = []
    for ti, (by, phs) in enumerate(((-4.0, 0.0), (0.0, 2.094), (4.0, 4.189))):
        titems, tspikes, tdots = [], [], []
        tp = []
        for i in range(N + 1):
            s_ = i / N
            braid = math.sin(st["tph"] * 1.3 + phs - s_ * 3.0) * (2.0 + 4.0 * s_)       # 서로 꼬이는 흔들림
            fan = (ti - 1) * ps["tsplit"] * s_ * s_ * 30                                # 부채처럼 갈라짐
            x = -22 - i * 7.0 + ps["tcurl"] * s_ * s_ * 24
            y = (by * (1 - s_ * 0.4) + braid + fan
                 + ps["tamp"] * math.sin(st["tph"] - i * 0.5) * (1.0 + i * 0.85) * 0.9 - st["turn"] * 7 * s_ * s_
                 + ps["tcurl"] * s_ ** 1.5 * 28)
            z = -1 - (s_ ** 1.1) * (ps["bz"] - 4) * ld * 0.85 + ps["tlift"] * s_ * s_ * 3.4
            r = 9.0 * (1 - s_) ** 0.9 + 1.8 * s_
            p = Bf(x, y, z)
            p = (p[0], p[1], max(p[2], r * 0.8))
            tp.append((p, r))
        for i, (p, r) in enumerate(tp):
            c = Pj(p)
            titems.append((c[0], c[1], r * SCALE, sty_b if (i + ti) % 2 == 0 else sty_d, c[2]))
            if 1 <= i < N and i % 2 == 1:                     # 갈고리 가시
                sh = 3.5 + 2.5 * (1 - i / N)
                a, b_, c2 = Pj((p[0] - 2, p[1], p[2] + r * 0.8)), Pj((p[0] + 2, p[1], p[2] + r * 0.8)), Pj((p[0] - 3.5, p[1], p[2] + r + sh))
                tspikes.append(([a[:2], c2[:2], b_[:2]], spike if i % 4 == 1 else deep))
            if i % 3 == 0 and i > 0:
                tdots.append((c[0], c[1], 1, veinc))
        pe = tp[N][0]
        back = (tp[N][0][0] - tp[N - 1][0][0], tp[N][0][1] - tp[N - 1][0][1])
        bl = math.hypot(back[0], back[1]) or 1.0
        bx, by_ = back[0] / bl, back[1] / bl
        nx, ny = -by_, bx
        blade = [Pj((pe[0] + bx * 10, pe[1] + by_ * 10, pe[2])), Pj((pe[0] + nx * 4.5, pe[1] + ny * 4.5, pe[2])),
                 Pj((pe[0] - bx * 3, pe[1] - by_ * 3, pe[2] + 2)), Pj((pe[0] - nx * 4.5, pe[1] - ny * 4.5, pe[2]))]
        tspikes.append(([q[:2] for q in blade], horn))
        GLW.append((blade[0][0], blade[0][1], 9, P["glow"], 90 + 80 * ps["glow"]))
        tdep = sum(c[4] for c in titems) / len(titems)
        Q.append((tdep, 3, (titems, tspikes, tdots)))
        tails_tip.append((blade[0][0], blade[0][1]))

    # ------------------------------------------------ 날개 (거대한 막 날개)
    wing_anc = []
    for s in (-1, 1):
        f, amp, b0, sw = ps["wfold"], ps["wamp"], ps["wb0"], ps["wsw"]
        sh = (8.0, s * 10.0, 13.0)
        h = lerp3((-8.5 - 13 * sw, s * 27.0, 8.5), (-10.0, s * 4.5, 9.0), f)
        fa = lerp3((11.0 - 15 * sw, s * 30.0, 9.5), (24.0, s * 2.0, 2.0), f)
        ph1 = st["wph"] + s * 0.12
        h = rx(h, s, b0 + amp * 0.8 * math.sin(ph1))
        fa = rx(fa, s, b0 + amp * math.sin(ph1 - 0.7))
        E = (sh[0] + h[0], sh[1] + h[1], sh[2] + h[2])
        Wr = (E[0] + fa[0], E[1] + fa[1], E[2] + fa[2])
        tips3 = []
        for i, (g_, L) in enumerate(zip((-0.05, 0.45, 0.9, 1.35), (54, 58, 50, 38))):
            go = g_ + 0.5 * sw
            d = lerp3((-math.sin(go), s * math.cos(go), 0.05), (-1.0, s * (0.03 + 0.07 * i), -0.28 - 0.08 * i), f)
            d = unit(d)
            ln = L * (1 - 0.18 * f)
            d = rx((d[0] * ln, d[1] * ln, d[2] * ln), s, b0 + amp * (1.2 + 0.2 * i) * math.sin(ph1 - 1.4 - 0.2 * i))
            tips3.append((Wr[0] + d[0], Wr[1] + d[1], Wr[2] + d[2]))
        sc3 = []
        for i in range(3):
            mx = ((tips3[i][0] + tips3[i + 1][0]) / 2, (tips3[i][1] + tips3[i + 1][1]) / 2, (tips3[i][2] + tips3[i + 1][2]) / 2 - 2)
            sc3.append((mx[0] + (Wr[0] - mx[0]) * 0.3, mx[1] + (Wr[1] - mx[1]) * 0.3, mx[2] + (Wr[2] - mx[2]) * 0.3))
        pS, pE, pW = T(*sh), T(*E), T(*Wr)
        pT = [T(*q) for q in tips3]
        pC = [T(*q) for q in sc3]
        pB = T(-17, s * 10.0, 3.0)
        dep = (pS[2] + pW[2] + sum(q[2] for q in pT)) / 6
        far = dep < bdep - 1
        wc, wd = P["wing"], P["wing_d"]
        wl = mix(wc, vein_d, 0.3)
        bone = mix(horn, wd, 0.45)
        if far:
            wc, wd, wl, bone = dk(wc, 0.76), dk(wd, 0.76), dk(wl, 0.76), dk(bone, 0.7)
        Q.append((dep, 5, dict(S=pS[:2], E=pE[:2], W=pW[:2], tips=[q[:2] for q in pT], scal=[q[:2] for q in pC], Bk=pB[:2], wc=wc, wd=wd,
                               wl=wl, bone=bone, vein=veinc, vein_d=vein_d, claw=horn, spike=spike, folded=f > 0.6)))
        wing_anc.append(pT[1][:2])
        if ph >= 2 and f < 0.6:
            for q in pT:
                GLW.append((q[0], q[1], 7, P["glow"], 90))

    # ------------------------------------------------ 목과 머리 (짧고 굵은 목, 넓고 납작한 머리)
    a = ps["hyaw"] * 0.85
    ca, sa = math.cos(a), math.sin(a)
    nbx, nbz = 26.0, 7.0
    dxh = ps["hx"] - nbx
    head = (nbx + dxh * ca, dxh * sa, ps["hz"])
    hp_, hyw = ps["hp"], ps["hyaw"]
    chp, shp, cyh, syh = math.cos(hp_), math.sin(hp_), math.cos(hyw), math.sin(hyw)
    hf = (chp * cyh, chp * syh, shp)
    hu = (-shp * cyh, -shp * syh, chp)
    hs = (hu[1] * hf[2] - hu[2] * hf[1], hu[2] * hf[0] - hu[0] * hf[2], hu[0] * hf[1] - hu[1] * hf[0])
    p0 = (nbx, 0.0, nbz)
    p1 = (nbx + 3 + dxh * 0.12 * ca, dxh * 0.12 * sa, nbz + 22 * ps["nk"])
    p2 = (head[0] - hf[0] * 14, head[1] - hf[1] * 14, head[2] - hf[2] * 14)
    NN = 13
    nitems, nspikes, ndots, npos = [], [], [], []
    for i in range(NN + 1):
        u = 1 - i / NN
        f_ = i / NN
        x = u ** 3 * p0[0] + 3 * u * u * f_ * p1[0] + 3 * u * f_ * f_ * p2[0] + f_ ** 3 * head[0]
        y = u ** 3 * p0[1] + 3 * u * u * f_ * p1[1] + 3 * u * f_ * f_ * p2[1] + f_ ** 3 * head[1]
        z = u ** 3 * p0[2] + 3 * u * u * f_ * p1[2] + 3 * u * f_ * f_ * p2[2] + f_ ** 3 * head[2]
        r = (11.5 - 4.0 * f_) * (1 + ps["chest"] * 0.5 * (1 - f_))
        c = T(x, y, z)
        nitems.append((c[0], c[1], r * SCALE, sty_b if i % 2 else sty_d, c[2]))
        npos.append((c[0], c[1]))
        if 1 <= i < NN and i % 2 == 1:
            sh_ = 7.0 - 2.0 * f_
            q1, q2, q3 = T(x - 2.6, y, z + r * 0.8), T(x + 1.8, y, z + r * 0.8), T(x - 2.0, y, z + r + sh_)
            nspikes.append(([q1[:2], q3[:2], q2[:2]], deep if i % 4 == 1 else dark))
            ndots.append((q3[0], q3[1], 1, spike))
    Q.append((sum(c[4] for c in nitems) / len(nitems) + 0.3, 3, (nitems, nspikes, ndots)))
    if ps["glow"] > 0.1:                                     # 목을 타고 오르는 푸른 빛
        for k in range(3):
            fr = (t * 1.8 + k / 3) % 1.0
            j = min(NN, int(fr * NN))
            GLW.append((npos[j][0], npos[j][1], 13, P["glow"], 120 * ps["glow"]))

    def Hh(px, py, pz):
        px, py, pz = px * HS, py * HS, pz * HS
        return T(head[0] + hf[0] * px + hs[0] * py + hu[0] * pz, head[1] + hf[1] * px + hs[1] * py + hu[1] * pz,
                 head[2] + hf[2] * px + hs[2] * py + hu[2] * pz)

    hd0 = Hh(0, 0, 0)[2]
    m = min(1.0, ps["mouth"]) * 0.75
    cm, sm = math.cos(m), math.sin(m)
    J0, J1 = (1.0, 0.0, -4.0), (1 + 22 * cm, 0.0, -4.0 - 22 * sm)
    # 가시 왕관 (머리 뒤로 부채처럼 펼쳐진다)
    cr_ = ps["crown"]
    crown_pts = []
    for k in range(9):
        u_ = (k - 4) / 4.0                                    # -1 .. 1 (좌 -> 우)
        ang = u_ * (0.55 + 0.75 * cr_)
        L = (11 + 6 * (1 - abs(u_))) * (0.7 + 0.45 * cr_)
        base_p = (-6, math.sin(ang) * 6, 4 + math.cos(ang) * 3)
        tip_p = (-6 - L * (0.85 - 0.45 * cr_), math.sin(ang) * (6 + L * 0.95), 4 + math.cos(ang) * (3 + L * (0.35 + 0.55 * cr_)))
        crown_pts.append((Hh(*base_p), Hh(*tip_p)))
    for k in range(8):                                        # 가시 사이의 막
        (b1, t1), (b2, t2) = crown_pts[k], crown_pts[k + 1]
        fdep = (b1[2] + t1[2] + b2[2] + t2[2]) / 4
        memb = mix(P["wing"], vein_d, 0.25) if fdep >= hd0 - 1 else dk(P["wing"], 0.75)
        Q.append((fdep - 0.4, 1, ([b1[:2], t1[:2], t2[:2], b2[:2]], memb, None, 0)))
    for k, (b1, t1) in enumerate(crown_pts):
        dep = (b1[2] + t1[2]) / 2
        hc = horn if dep >= hd0 - 2 else dk(horn, 0.75)
        Q.append((dep - 0.2, 2, ([(b1[0], b1[1], 2.2 * HS * SCALE, t1[0], t1[1], 0.6)], hc, mix(hc, (255, 255, 255), 0.3))))
        Q.append((dep - 0.15, 0, (t1[0], t1[1], 1.4, (spike, spike, (255, 255, 255)))))
        if ps["glow"] > 0.3 or cr_ > 0.7:
            GLW.append((t1[0], t1[1], 6, P["glow"], 80 + 100 * ps["glow"]))
    for sd in (-1, 1):
        # 엄니: 아래턱 옆에서 앞으로 휘어 솟는다
        tusk = [(5, sd * 5.5, -3.5), (12, sd * 8.0, -5.5), (19, sd * 9.0, -4.0), (24, sd * 8.5, 0.5), (27, sd * 7.0, 5.0)]
        hp3 = [Hh(*q) for q in tusk]
        segs = []
        for i in range(len(hp3) - 1):
            r1 = (2.5 - i * 0.48) * HS
            r2 = (2.5 - (i + 1) * 0.48) * HS
            segs.append((hp3[i][0], hp3[i][1], r1 * SCALE, hp3[i + 1][0], hp3[i + 1][1], max(0.6, r2) * SCALE))
        dep = sum(q[2] for q in hp3) / 5
        tc_ = horn if dep >= hd0 - 2 else dk(horn, 0.8)
        Q.append((dep + 0.4, 2, (segs, tc_, mix(tc_, (255, 255, 255), 0.45))))
        # 눈 위의 짧은 더듬이 가시
        e1, e2 = Hh(6, sd * 5.5, 5.5), Hh(1, sd * 7.5, 11)
        Q.append(((e1[2] + e2[2]) / 2, 2, ([(e1[0], e1[1], 1.4 * HS, e2[0], e2[1], 0.5)], spike, None)))
        ec = Hh(8.5, sd * 6.2, 2.6)                          # 눈 (전기 같은 푸른빛)
        Q.append((ec[2] + 0.4, 0, (ec[0], ec[1], 2.2 * HS * SCALE, (eye, eye, (255, 255, 255)))))
        GLW.append((ec[0], ec[1], 13, P["glow"], 190))
        b1_, b2_ = Hh(4, sd * 5.8, 5.2), Hh(13, sd * 6.4, 4.4)          # 눈썹뼈
        Q.append((ec[2] + 0.8, 2, ([(b1_[0], b1_[1], 2.4 * HS, b2_[0], b2_[1], 1.8 * HS)], deep, None)))
        hp3 = [Hh(px, sd * py, pz) for px, py, pz in ((0, 4.5, 5.5), (-7, 7.0, 8.5), (-15, 9.0, 11.0), (-23, 8.5, 11.5), (-29, 6.0, 9.5))]
        segs = []
        for i in range(len(hp3) - 1):                         # 뒤로 휘어 뻗은 큰 뿔
            segs.append((hp3[i][0], hp3[i][1], (2.6 - i * 0.5) * HS * SCALE, hp3[i + 1][0], hp3[i + 1][1], max(0.6, 2.6 - (i + 1) * 0.5) * HS * SCALE))
        hdep = sum(q[2] for q in hp3) / 5
        hcol = mix(horn, deep, 0.3) if hdep >= hd0 - 2 else dk(mix(horn, deep, 0.3), 0.75)
        Q.append((hdep, 2, (segs, hcol, mix(hcol, (255, 255, 255), 0.35))))
        GLW.append((hp3[-1][0], hp3[-1][1], 6, P["glow"], 90))
    skull = Hh(0, 0, 0)
    Q.append((skull[2], 0, (skull[0], skull[1], 7.8 * HS * SCALE, sty_b)))
    for sd in (-1, 1):                                        # 넓은 볼 (머리를 납작하고 넓게 만든다)
        ck = Hh(4, sd * 4.8, -0.8)
        Q.append((ck[2] - 0.05, 0, (ck[0], ck[1], 4.2 * HS * SCALE, sty_b)))
    sn0, sn1 = Hh(5, 0, -0.5), Hh(26, 0, -1.8)
    Q.append(((sn0[2] + sn1[2]) / 2 + 0.2, 2, ([(sn0[0], sn0[1], 6.4 * HS * SCALE, sn1[0], sn1[1], 4.2 * HS * SCALE)], base, hi)))
    for k in range(3):                                        # 콧등의 골판
        q1 = Hh(10 + k * 5.0, 0, 4.2 - k * 0.5)
        Q.append((q1[2] + 0.3, 0, (q1[0], q1[1], 1.8 * HS, (deep, dark, hi))))
    j0, j1 = Hh(*J0), Hh(*J1)
    jc = Hh((J0[0] + J1[0]) / 2, 0, (J0[2] + J1[2]) / 2)
    Q.append((jc[2] - 0.3, 2, ([(j0[0], j0[1], 4.4 * HS * SCALE, j1[0], j1[1], 2.8 * HS * SCALE)], dark, belly_d)))
    if ps["mouth"] > 0.14:                                    # 입 안: 푸른 냉기
        mi = [Hh(3, 0, -4.2), Hh(20, 0, -3.6), Hh(J1[0] - 1, 0, J1[2] + 1.2), Hh(*J0)]
        Q.append((jc[2] + 0.1, 1, ([q[:2] for q in mi], (30, 60, 110), None, 0)))
        if ps["glow"] > 0.35 or ps["mouth"] > 0.7:
            gm = [Hh(7, 0, -4.0), Hh(18, 0, -3.6), Hh(J1[0] - 3, 0, J1[2] + 2.2), Hh(J0[0] + 4, 0, J0[2] + 0.5)]
            Q.append((jc[2] + 0.12, 1, ([q[:2] for q in gm], mix((120, 220, 255), (235, 250, 255), ps["glow"]), None, 0)))
    for k in range(4):                                        # 이빨
        x = 8 + k * 4.6
        for sd in (-1, 1):
            a_, b_, c_ = Hh(x, sd * 4.0, -3.8), Hh(x + 2.0, sd * 4.0, -3.8), Hh(x + 1.0, sd * 3.8, -3.8 - (3.6 if k % 2 else 2.4))
            Q.append((Hh(x, sd * 4.0, -4.0)[2] + 0.25, 1, ([a_[:2], c_[:2], b_[:2]], (236, 246, 250), OL, 1)))
    if ps["glow"] > 0.2:
        GLW.append((j0[0], j0[1], 20, P["glow"], 150 * ps["glow"]))
    ctr = T(16, 0, 2)
    if ps["glow"] > 0.1:                                      # 가슴에서 차오르는 빛
        GLW.append((ctr[0], ctr[1] - 4, 15 + 12 * ps["glow"], P["glow"], 150 * ps["glow"]))

    # ------------------------------------------------ 그리기 (먼 것부터)
    for dep, kind, d in sorted(Q, key=lambda q: q[0]):
        if kind == 0:
            d_sph(cv, d[0], d[1], d[2], d[3])
        elif kind == 1:
            d_poly(cv, d)
        elif kind == 2:
            d_caps(cv, d[0], d[1], d[2])
        elif kind == 3:
            d_chain(cv, *d)
        elif kind == 4:
            D.line(cv, d[2], d[0], d[1], d[3])
        elif kind == 5:
            d_wing(cv, d)
        elif kind == 7:
            segs, col, hic, cold, claws, pF, kg = d
            d_caps(cv, segs, col, hic)
            D.circle(cv, OL, (int(pF[0]), int(pF[1])), 5)
            D.circle(cv, cold, (int(pF[0]), int(pF[1])), 4)
            D.circle(cv, veinc, (int(kg[0]), int(kg[1])), 2)
            for pts_, cc in claws:
                D.polygon(cv, cc, pts_)
                D.polygon(cv, OL, pts_, 1)
    for x, y, r, col, a in GLW:
        blit_gl(cv, x, y, r, col, a)
    mt = Hh(28, 0, -2.0 - 7 * sm)
    return dict(mouth=mt[:2], nose=Hh(26, 0, 1)[:2], eye=Hh(8.5, 6.2, 2.6)[:2], head=skull[:2], chest=ctr[:2], tail=tails_tip[1],
                tails=tails_tip, feet=feet, tips=wing_anc, body=sc[:2], top=Hh(0, 0, 18)[:2], crown=crown_pts[4][1][:2])
