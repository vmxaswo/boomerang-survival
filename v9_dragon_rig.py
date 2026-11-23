"""v9 화룡 리그 (v9_dragon_rig.py)  -  화룡을 '3D 뼈대 -> 쿼터뷰 도트'로 그리는 렌더러.
 - 척추·목·꼬리(마디 체인), 다리 4개(2본 IK), 날개 2개(어깨-팔꿈치-손목-손가락 4개)를 3D 관절로 만든다.
 - 바라보는 각도(heading, 라디안, 0 = 오른쪽, 90도 = 아래)만큼 돌려 위에서 약 42도로 내려다보는 시점에 투영하고,
   먼 부위부터 그린다(화가 알고리즘). 그래서 8방향은 물론 그 사이 각도도 자연스럽게 이어진다.
 - 포즈는 숫자 몇 개(DEF 참고)로 정해지고, update()가 부드럽게 섞어 준다. 걷기(다리 보행 주기)는 실제 이동 거리에 맞춰 돈다.
 이 모듈은 게임 코드에 의존하지 않는다 (pygame 과 math 만 쓴다).
"""
import math

import pygame

D = pygame.draw
SC = pygame.SRCALPHA
OL = (22, 8, 16)
CW, CH, CX, CY = 440, 380, 220, 190                    # 도화지 크기와 중심(= 화룡 좌표)
GY0 = 16                                               # 중심에서 지면까지 (화면 픽셀)
HS = 1.4                                               # 머리 배율
SCALE = 1.0                                            # 모델 단위 -> 픽셀 (화룡 전체 크기)
_EL = math.radians(42)
SE, CE = math.sin(_EL), math.cos(_EL)
_GL, _B = {}, {}

DEF = dict(alt=0.0, bz=17.0, pitch=0.0, roll=0.0, hx=46.0, hz=27.0, hp=-0.1, hyaw=0.0, mouth=0.05, nk=1.0,
           wfold=0.92, wamp=0.0, wfreq=1.0, wb0=0.0, wsw=0.0, tamp=1.0, tlift=0.0, tcurl=0.0, tfreq=1.8,
           tuck=0.0, brace=0.0, fz=0.0, fxo=0.0, scr=0.0, glow=0.0, chest=0.0)
RATE = dict(alt=3.2, wfold=8.0, glow=4.0, tfreq=4.0, wfreq=5.0, hyaw=10.0)


def new_state():
    return dict(ps=dict(DEF), wph=0.0, tph=0.0, g=0.0, sp=0.0, amp_f=0.0, stride=14.0, turn=0.0)


def update(st, tg, dt, rate, vf, sp, turn):
    """tg: 목표 포즈, rate: 섞는 속도, vf: 앞방향 이동속도(px/s, 뒤로 가면 음수), sp: 속력, turn: 회전속도(rad/s)"""
    ps = st["ps"]
    for key, v in tg.items():
        ps[key] += (v - ps[key]) * (1 - math.exp(-dt * RATE.get(key, rate)))
    st["wph"] += dt * ps["wfreq"] * 6.2832
    st["tph"] += dt * ps["tfreq"]
    stride = min(42.0, max(14.0, 14 + 0.09 * sp))
    st["stride"], st["sp"] = stride, sp
    st["amp_f"] = min(1.0, sp / 22.0)
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
def d_sph(cv, x, y, r, sty):
    xi, yi, ri = int(x), int(y), max(1, int(r))
    D.circle(cv, OL, (xi, yi), ri + 1)
    fill_sph(cv, xi, yi, ri, sty)


def fill_sph(cv, xi, yi, ri, sty):
    D.circle(cv, sty[0], (xi, yi), ri)
    D.circle(cv, sty[1], (xi - ri // 8, yi - ri // 6), max(1, int(ri * 0.9)))
    if ri >= 4:
        D.circle(cv, sty[2], (xi - ri // 3, yi - ri // 2), max(1, int(ri * 0.4)))


def d_caps(cv, segs, fill, hi):
    """segs: [(x1, y1, r1, x2, y2, r2), ...] 굵기가 변하는 캡슐 묶음"""
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
    if w["folded"]:                                          # 접힌 날개: 잔선 없이 하나의 어두운 덩어리
        S_, E_, W_, tips, Bk = w["S"], w["E"], w["W"], w["tips"], w["Bk"]
        mass = [S_, E_, W_, tips[0], tips[1], tips[2], tips[3], Bk]
        D.polygon(cv, w["wd"], mass)
        D.polygon(cv, OL, mass, 1)
        D.line(cv, OL, S_, E_, 4)
        D.line(cv, w["bone"], S_, E_, 2)
        D.circle(cv, OL, (int(W_[0]), int(W_[1])), 3)
        D.circle(cv, w["bone"], (int(W_[0]), int(W_[1])), 2)
        return
    S_, E_, W_, tips, scal, Bk = w["S"], w["E"], w["W"], w["tips"], w["scal"], w["Bk"]
    wc, wd, wl, bone = w["wc"], w["wd"], w["wl"], w["bone"]
    D.polygon(cv, wd, [S_, W_, tips[3], Bk])
    for i in range(3):
        D.polygon(cv, wl if i % 2 else wc, [W_, tips[i], scal[i], tips[i + 1]])
    outline = [S_, E_, W_, tips[0], scal[0], tips[1], scal[1], tips[2], scal[2], tips[3], Bk]
    D.polygon(cv, OL, outline, 1)
    for i in range(3):                                       # 막의 주름
        mid = ((tips[i][0] + tips[i + 1][0]) / 2, (tips[i][1] + tips[i + 1][1]) / 2)
        D.line(cv, w["fold"], W_, mid, 1)
    if w["ph"] >= 2:                                         # 막을 따라 흐르는 용암 맥
        for sc_ in scal:
            D.line(cv, w["vein"], W_, sc_, 1)
        D.line(cv, w["vein"], S_, tips[3], 1)
    D.line(cv, OL, S_, E_, 5)
    D.line(cv, bone, S_, E_, 3)
    D.line(cv, OL, E_, W_, 4)
    D.line(cv, bone, E_, W_, 2)
    for t_ in tips:
        D.line(cv, OL, W_, t_, 2)
        D.line(cv, bone, W_, t_, 1)
    D.circle(cv, OL, (int(W_[0]), int(W_[1])), 4)
    D.circle(cv, bone, (int(W_[0]), int(W_[1])), 3)
    D.polygon(cv, w["claw"], [(W_[0] - 2, W_[1] - 1), (W_[0] + 1, W_[1] - 9), (W_[0] + 4, W_[1])])


# ================================================================= 한 프레임
def draw(cv, st, P, ph, t, heading):
    """cv(도화지)에 화룡을 그리고 기준점(anchors)을 돌려준다.  기준점은 모두 도화지 좌표."""
    ps = st["ps"]
    cyw, syw = math.cos(heading), math.sin(heading)
    cp, sp_ = math.cos(ps["pitch"]), math.sin(ps["pitch"])
    cr, sr = math.cos(ps["roll"]), math.sin(ps["roll"])
    amp_f, g = st["amp_f"], st["g"]
    bob = math.sin(12.566 * g) * (0.5 + min(2.5, st["sp"] * 0.01)) * amp_f
    sway = math.sin(6.283 * g) * 1.5 * amp_f
    zc = ps["bz"] + ps["alt"] + bob + math.sin(t * 2.0) * 0.4
    CYG = CY + GY0

    def Bf(x, y, z):                                         # 몸 좌표 -> 각도 없는 지면 좌표(피치·롤 적용)
        x2 = x * cp - z * sp_
        z2 = z * cp + x * sp_
        return (x2, y * cr - z2 * sr + sway, z2 * cr + y * sr + zc)

    def Pj(p):                                               # 지면 좌표 -> 화면 + 깊이
        wx = p[0] * cyw - p[1] * syw
        wy = p[0] * syw + p[1] * cyw
        return (CX + wx * SCALE, CYG + (wy * SE - p[2] * CE) * SCALE, wy * CE + p[2] * SE)

    def T(x, y, z):
        return Pj(Bf(x, y, z))

    base, dark, hi, belly, belly_d = P["base"], P["dark"], P["hi"], P["belly"], P["belly_d"]
    deep, horn, eye = P["deep"], P["horn"], P["eye"]
    vein, vein_d = P["vein"], P["vein_d"]
    sty_b = (belly_d, base, hi)
    sty_d = (deep, dark, base)
    sty_l = (deep, dark, base)
    Q, GLW = [], []
    bdep = T(0, 0, 0)[2]
    pulse = 0.5 + 0.5 * math.sin(t * 3)
    veinc = mix(vein_d, vein, pulse)
    chest_k = 1.0 + ps["chest"]

    # ------------------------------------------------ 몸통
    tor = [(16, 0, 1, 14.0 * chest_k), (6, 0, 0, 15.2 * chest_k), (-6, 0, 0, 14.4), (-16, 0, -1, 12.2)]
    items, spikes, dots = [], [], []
    for i, (x, y, z, r) in enumerate(tor):
        c = T(x, y, z)
        items.append((c[0], c[1], r * SCALE, sty_b, c[2]))
    for i in range(8):                                       # 등 가시
        x = 20 - i * 5.2
        z0 = 14.2 if 3 <= i <= 5 else 13.0 - abs(i - 4) * 0.3
        h = 6 + 5 * math.sin(i / 7 * math.pi)
        a, b_, c = T(x - 2.4, 0, z0), T(x + 2.4, 0, z0), T(x - 2.0, 0, z0 + h)
        spikes.append(([a[:2], c[:2], b_[:2]], hi if i % 2 else deep))
        if ph >= 2:
            dots.append((c[0], c[1], 1, vein))
    if ph >= 2:                                              # 등의 용암 균열
        for i in range(5):
            x = 14 - i * 7
            for sd in (-1, 1):
                c = T(x, sd * (7 + (i % 2) * 2), 10.0)
                dots.append((c[0], c[1], 2 if ph >= 3 else 1, veinc))
    sc = T(0, 0, 0)
    Q.append((bdep, 3, (items, spikes, dots)))
    if ph >= 2:                                              # 비늘 질감 (몸통 위)
        for k in range(10):
            c = T(14 - k * 3.6, ((k * 7) % 5 - 2) * 2.4, 12.2 - abs((k * 7) % 5 - 2) * 0.8)
            dots.append((c[0], c[1], 1, dk(base, 0.7)))

    # ------------------------------------------------ 다리 (2본 IK)
    stride = st["stride"] * amp_f
    feet = []
    legs = []
    for i, (front, s, off) in enumerate(((1, 1, 0.0), (0, -1, 0.25), (1, -1, 0.5), (0, 1, 0.75))):
        hxl, hyl, hzl = (13, s * 9.5, -5) if front else (-14, s * 10.5, -4)
        Hp = Bf(hxl, hyl, hzl)
        rest_x = (17 + ps["brace"] * 4) if front else (-17 - ps["brace"] * 3)
        rest_y = s * ((18 if front else 19) + ps["brace"] * 5)
        ph_ = (g + off) % 1.0
        if ph_ < 0.65:
            fxs, lift = 0.5 - ph_ / 0.65, 0.0
        else:
            u = (ph_ - 0.65) / 0.35
            fxs, lift = -0.5 + u, math.sin(math.pi * u)
        fx_, fy_, fz_ = rest_x + fxs * stride, rest_y, lift * (4 + stride * 0.2)
        if front:
            fx_ += ps["fxo"] + math.sin(t * 26) * ps["scr"]
            fz_ += ps["fz"] + max(0.0, math.cos(t * 26)) * ps["scr"] * 0.7
        if ps["tuck"] > 0.01:
            tk = Bf(7, s * 9, -13) if front else Bf(-11, s * 10, -12)
            fx_, fy_, fz_ = fx_ + (tk[0] - fx_) * ps["tuck"], fy_ + (tk[1] - fy_) * ps["tuck"], fz_ + (tk[2] - fz_) * ps["tuck"]
        dx, dy, dz = fx_ - Hp[0], fy_ - Hp[1], fz_ - Hp[2]
        L1, L2 = (15.0, 14.0)
        L = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
        if L > L1 + L2 - 0.6:
            k = (L1 + L2 - 0.6) / L
            dx, dy, dz, L = dx * k, dy * k, dz * k, L * k
            fx_, fy_, fz_ = Hp[0] + dx, Hp[1] + dy, Hp[2] + dz
        a_ = (L1 * L1 - L2 * L2 + L * L) / (2 * L)
        h_ = math.sqrt(max(0.0, L1 * L1 - a_ * a_))
        bd = (-0.3, s * 0.9, 0.5) if front else (0.6, s * 0.8, 0.6)
        dd = (dx * bd[0] + dy * bd[1] + dz * bd[2]) / (L * L)
        bd = unit((bd[0] - dx * dd, bd[1] - dy * dd, bd[2] - dz * dd))
        K = (Hp[0] + dx * a_ / L + bd[0] * h_, Hp[1] + dy * a_ / L + bd[1] * h_, Hp[2] + dz * a_ / L + bd[2] * h_)
        Fp = (fx_, fy_, fz_)
        pH, pK, pF = Pj(Hp), Pj(K), Pj(Fp)
        dep = (pH[2] + pK[2] + pF[2]) / 3
        far = dep < bdep
        col, hic, cold = (dk(base, 0.74), dk(hi, 0.74), dk(dark, 0.74)) if far else (base, hi, dark)
        rt = 7.4 if not front else 6.2
        segs1 = [(pH[0], pH[1], rt * SCALE, pK[0], pK[1], (rt - 1.2) * SCALE)]
        segs2 = [(pK[0], pK[1], (rt - 1.2) * SCALE, pF[0], pF[1], 3.0 * SCALE)]
        claws = []
        for k in (-1, 0, 1):
            c0 = Pj((fx_ + 1, fy_ + k * 2.2, fz_ + 1))
            c1 = Pj((fx_ + 6.5, fy_ + k * 3.0, fz_ - 0.5))
            c2 = Pj((fx_ + 1, fy_ + k * 2.2 + 1.2, fz_ + 1))
            claws.append(([c0[:2], c1[:2], c2[:2]], horn))
        legs.append((dep, segs1, segs2, col, hic, cold, claws, pF))
        feet.append((pF[0], pF[1]))
    for dep, s1, s2, col, hic, cold, claws, pF in legs:
        Q.append((dep, 7, (s1, s2, col, hic, cold, claws, pF)))

    # ------------------------------------------------ 꼬리
    N = 12
    titems, tspikes, tdots = [], [], []
    ld = 1.0 - min(1.0, ps["alt"] / 20.0) * 0.6
    tp = []
    for i in range(N + 1):
        s_ = i / N
        x = -16 - i * 6.2 + ps["tcurl"] * s_ * s_ * 24
        y = (ps["tamp"] * math.sin(st["tph"] - i * 0.5) * (1.2 + i * 0.95) * 0.9 - st["turn"] * 7 * s_ * s_ * 1.0
             + ps["tcurl"] * s_ ** 1.5 * 30)
        z = -1 - (s_ ** 1.1) * (ps["bz"] - 4) * ld * 0.85 + ps["tlift"] * s_ * s_ * 3.2
        r = 11.0 * (1 - s_) ** 0.85 + 2.2 * s_
        p = Bf(x, y, z)
        p = (p[0], p[1], max(p[2], r * 0.8))
        tp.append((p, r))
    for i, (p, r) in enumerate(tp):
        c = Pj(p)
        titems.append((c[0], c[1], r * SCALE, sty_b if i % 2 == 0 else sty_d, c[2]))
        if 1 <= i < N - 1 and i % 2 == 1:
            sh = 4.5 + (i % 3) * 0.8 + 3 * (1 - i / N)
            a, b_, c2 = Pj((p[0] - 2, p[1], p[2] + r * 0.85)), Pj((p[0] + 2, p[1], p[2] + r * 0.85)), Pj((p[0] - 1.5, p[1], p[2] + r + sh))
            tspikes.append(([a[:2], c2[:2], b_[:2]], hi if i % 4 == 1 else deep))
    pe, re_ = tp[N]
    tb = [Pj((pe[0] - 12 * cyw * 0, pe[1], pe[2]))]                                # 꼬리 끝 날
    # 꼬리 끝 날: 몸 좌표 기준 뒤쪽으로 향하는 마름모
    back = (tp[N][0][0] - tp[N - 1][0][0], tp[N][0][1] - tp[N - 1][0][1], 0.0)
    bl = math.hypot(back[0], back[1]) or 1.0
    bx, by_ = back[0] / bl, back[1] / bl
    nx, ny = -by_, bx
    blade = [Pj((pe[0] + bx * 11, pe[1] + by_ * 11, pe[2])), Pj((pe[0] + nx * 5 - bx * 1, pe[1] + ny * 5 - by_ * 1, pe[2])),
             Pj((pe[0] - bx * 3, pe[1] - by_ * 3, pe[2] + 2)), Pj((pe[0] - nx * 5 - bx * 1, pe[1] - ny * 5 - by_ * 1, pe[2]))]
    tspikes.append(([b[:2] for b in blade], horn))
    if ph >= 3:
        tdots.append((blade[0][0], blade[0][1], 3, vein))
        GLW.append((blade[0][0], blade[0][1], 13, (255, 140, 60), 160))
    tdep = sum(c[4] for c in titems) / len(titems)
    Q.append((tdep, 3, (titems, tspikes, tdots)))
    tail_tip = (blade[0][0], blade[0][1])

    # ------------------------------------------------ 날개
    wing_anc = []
    for s in (-1, 1):
        f, amp, b0, sw = ps["wfold"], ps["wamp"], ps["wb0"], ps["wsw"]
        sh = (6.0, s * 9.0, 11.0)
        h = lerp3((-7.7 - 12 * sw, s * 23.6, 7.7), (-9.0, s * 4.0, 8.0), f)
        fa = lerp3((10.0 - 14 * sw, s * 26.8, 8.7), (22.0, s * 2.0, 2.0), f)
        ph1 = st["wph"] + s * 0.12
        h = rx(h, s, b0 + amp * 0.8 * math.sin(ph1))
        fa = rx(fa, s, b0 + amp * math.sin(ph1 - 0.7))
        E = (sh[0] + h[0], sh[1] + h[1], sh[2] + h[2])
        Wr = (E[0] + fa[0], E[1] + fa[1], E[2] + fa[2])
        tips3 = []
        for i, (g_, L) in enumerate(zip((-0.05, 0.45, 0.9, 1.35), (46, 50, 44, 34))):
            go = g_ + 0.5 * sw
            d = lerp3((-math.sin(go), s * math.cos(go), 0.05), (-1.0, s * (0.03 + 0.07 * i), -0.28 - 0.08 * i), f)
            d = unit(d)
            ln = L * (1 - 0.15 * f)
            d = rx((d[0] * ln, d[1] * ln, d[2] * ln), s, b0 + amp * (1.2 + 0.2 * i) * math.sin(ph1 - 1.4 - 0.2 * i))
            tips3.append((Wr[0] + d[0], Wr[1] + d[1], Wr[2] + d[2]))
        sc3 = []
        for i in range(3):
            mx = ((tips3[i][0] + tips3[i + 1][0]) / 2, (tips3[i][1] + tips3[i + 1][1]) / 2, (tips3[i][2] + tips3[i + 1][2]) / 2 - 2)
            sc3.append((mx[0] + (Wr[0] - mx[0]) * 0.3, mx[1] + (Wr[1] - mx[1]) * 0.3, mx[2] + (Wr[2] - mx[2]) * 0.3))
        pS, pE, pW = T(*sh), T(*E), T(*Wr)
        pT = [T(*q) for q in tips3]
        pC = [T(*q) for q in sc3]
        pB = T(-15, s * 9.0, 3.0)
        dep = (pS[2] + pW[2] + sum(q[2] for q in pT)) / 6
        far = dep < bdep - 1
        wc, wd = P["wing"], P["wing_d"]
        wl = mix(wc, vein_d, 0.28)
        bone = mix(horn, wd, 0.42)
        if far:
            wc, wd, wl, bone = dk(wc, 0.76), dk(wd, 0.76), dk(wl, 0.76), dk(bone, 0.7)
        w = dict(S=pS[:2], E=pE[:2], W=pW[:2], tips=[q[:2] for q in pT], scal=[q[:2] for q in pC], Bk=pB[:2], wc=wc, wd=wd, wl=wl,
                 bone=bone, vein=veinc, fold=dk(wd, 0.8), ph=ph, claw=horn, folded=f > 0.6)
        Q.append((dep, 5, w))
        wing_anc.append(pT[1][:2])
        if ph >= 3:
            for q in pT[1:]:
                GLW.append((q[0], q[1], 8, (255, 120, 50), 110))

    # ------------------------------------------------ 목과 머리
    a = ps["hyaw"] * 0.85
    ca, sa = math.cos(a), math.sin(a)
    nbx, nbz = 22.0, 6.0
    dxh = ps["hx"] - nbx
    head = (nbx + dxh * ca, dxh * sa, ps["hz"])
    hp_, hyw = ps["hp"], ps["hyaw"]
    chp, shp, cyh, syh = math.cos(hp_), math.sin(hp_), math.cos(hyw), math.sin(hyw)
    hf = (chp * cyh, chp * syh, shp)
    hu = (-shp * cyh, -shp * syh, chp)
    hs = (hu[1] * hf[2] - hu[2] * hf[1], hu[2] * hf[0] - hu[0] * hf[2], hu[0] * hf[1] - hu[1] * hf[0])
    p0 = (nbx, 0.0, nbz)
    p1 = (nbx + 4 + dxh * 0.15 * ca, dxh * 0.15 * sa, nbz + 17 * ps["nk"])
    p2 = (head[0] - hf[0] * 16, head[1] - hf[1] * 16, head[2] - hf[2] * 16)
    NN = 12
    nitems, nspikes, ndots, npos = [], [], [], []
    for i in range(NN + 1):
        u = 1 - i / NN
        f_ = i / NN
        x = u ** 3 * p0[0] + 3 * u * u * f_ * p1[0] + 3 * u * f_ * f_ * p2[0] + f_ ** 3 * head[0]
        y = u ** 3 * p0[1] + 3 * u * u * f_ * p1[1] + 3 * u * f_ * f_ * p2[1] + f_ ** 3 * head[1]
        z = u ** 3 * p0[2] + 3 * u * u * f_ * p1[2] + 3 * u * f_ * f_ * p2[2] + f_ ** 3 * head[2]
        r = (13.0 - 4.6 * f_) * (1 + ps["chest"] * 0.5 * (1 - f_))
        c = T(x, y, z)
        nitems.append((c[0], c[1], r * SCALE, sty_b if i % 2 else sty_d, c[2]))
        npos.append((c[0], c[1]))
        if 1 <= i < NN and i % 2 == 1:
            sh_ = 6.5 - 2.5 * f_
            q1, q2, q3 = T(x - 2.4, y, z + r * 0.8), T(x + 1.6, y, z + r * 0.8), T(x - 1.8, y, z + r + sh_)
            nspikes.append(([q1[:2], q3[:2], q2[:2]], hi if i % 4 == 1 else deep))
    Q.append((sum(c[4] for c in nitems) / len(nitems) + 0.3, 3, (nitems, nspikes, ndots)))
    if ps["glow"] > 0.1:                                     # 목을 타고 오르는 열기
        for k in range(3):
            fr = (t * 1.8 + k / 3) % 1.0
            j = min(NN, int(fr * NN))
            GLW.append((npos[j][0], npos[j][1], 12, (255, 160, 60), 120 * ps["glow"]))

    def Hh(px, py, pz):
        px, py, pz = px * HS, py * HS, pz * HS
        return T(head[0] + hf[0] * px + hs[0] * py + hu[0] * pz, head[1] + hf[1] * px + hs[1] * py + hu[1] * pz,
                 head[2] + hf[2] * px + hs[2] * py + hu[2] * pz)

    hd0 = Hh(0, 0, 0)[2]
    m = min(1.0, ps["mouth"]) * 0.82
    cm, sm = math.cos(m), math.sin(m)
    J0, J1 = (2.0, 0.0, -4.5), (2 + 19 * cm, 0.0, -4.5 - 19 * sm)
    for sd in (-1, 1):
        fin = [Hh(-3, sd * 5, 3), Hh(-19, sd * 12, 8), Hh(-23, sd * 11, 1), Hh(-11, sd * 6, -2)]   # 머리 뒤 지느러미
        fdep = sum(q[2] for q in fin) / 4
        fl = dk(P["wing"], 0.8) if fdep < hd0 else P["wing"]
        Q.append((fdep - 0.2, 1, ([q[:2] for q in fin], fl, OL, 1)))
        Q.append((fdep - 0.1, 4, (fin[0][:2], fin[1][:2], vein if ph >= 2 else dk(P["wing_d"], 1.0), 1)))
        for pts_, w0 in (([(-1, 5), (-7, 7.5), (-13, 9), (-18, 8.5), (-21, 6.5)], 2.0),):                # 큰 뿔
            hp3 = [(Hh(px, sd * py, 5 + (-px) * 0.35 - (px * px) * 0.004)) for px, py in pts_]
            segs = []
            for i in range(len(hp3) - 1):
                r1 = (w0 * (1 - i / 4.2) + 0.5) * HS
                r2 = (w0 * (1 - (i + 1) / 4.2) + 0.5) * HS
                segs.append((hp3[i][0], hp3[i][1], r1 * SCALE, hp3[i + 1][0], hp3[i + 1][1], r2 * SCALE))
            hc = mix(horn, deep, 0.38)
            hc = hc if sum(q[2] for q in hp3) / 5 >= hd0 - 2 else dk(hc, 0.75)
            Q.append((sum(q[2] for q in hp3) / 5, 2, (segs, hc, mix(hc, (255, 255, 255), 0.22))))
        c1, c2 = Hh(6, sd * 4, 6), Hh(2, sd * 5.5, 13)                                              # 작은 뿔
        Q.append(((c1[2] + c2[2]) / 2, 2, ([(c1[0], c1[1], 1.8 * HS, c2[0], c2[1], 0.5)], horn, None)))
        c1, c2 = Hh(-2, sd * 7, -1), Hh(-13, sd * 12, -4)                                           # 뺨 가시
        Q.append(((c1[2] + c2[2]) / 2, 2, ([(c1[0], c1[1], 2.4 * HS, c2[0], c2[1], 0.5)], horn, None)))
        ec = Hh(7.5, sd * 5.2, 3.2)                                                                  # 눈
        Q.append((ec[2] + 0.4, 0, (ec[0], ec[1], 2.6 * HS * SCALE, (eye, eye, (255, 255, 240)))))
        pe1, pe2 = Hh(7.5, sd * 5.8, 4.7), Hh(7.5, sd * 5.8, 1.8)
        Q.append((ec[2] + 0.6, 4, (pe1[:2], pe2[:2], OL, 1)))
        GLW.append((ec[0], ec[1], 11, eye, 170))
        b1, b2 = Hh(3, sd * 5, 6), Hh(12, sd * 5.6, 5.2)                                             # 눈썹뼈
        Q.append((ec[2] + 0.8, 2, ([(b1[0], b1[1], 2.2 * HS, b2[0], b2[1], 1.7 * HS)], deep, None)))
        nc = Hh(22, sd * 2.4, 0.8)
        Q.append((nc[2] + 0.5, 0, (nc[0], nc[1], 1.6 * HS, (OL, deep, deep))))
    skull = Hh(0, 0, 0)
    Q.append((skull[2], 0, (skull[0], skull[1], 8.2 * HS * SCALE, sty_b)))
    sn0, sn1 = Hh(4, 0, -0.5), Hh(23, 0, -2.0)
    Q.append(((sn0[2] + sn1[2]) / 2 + 0.2, 2, ([(sn0[0], sn0[1], 6.4 * HS * SCALE, sn1[0], sn1[1], 4.2 * HS * SCALE)], base, hi)))
    j0, j1 = Hh(*J0), Hh(*J1)
    jc = Hh(*((J0[0] + J1[0]) / 2, 0, (J0[2] + J1[2]) / 2))
    Q.append((jc[2] - 0.3, 2, ([(j0[0], j0[1], 4.0 * HS * SCALE, j1[0], j1[1], 2.7 * HS * SCALE)], dark, belly_d)))
    ch0, ch1 = Hh((J0[0] + J1[0]) / 2, 0, (J0[2] + J1[2]) / 2 - 2), Hh((J0[0] + J1[0]) / 2 - 3, 0, (J0[2] + J1[2]) / 2 - 9)
    Q.append((jc[2] - 0.35, 2, ([(ch0[0], ch0[1], 1.8 * HS, ch1[0], ch1[1], 0.4)], horn, None)))
    if ps["mouth"] > 0.14:                                   # 입 안
        mi = [Hh(3, 0, -4.4), Hh(21, 0, -4.0), Hh(J1[0] - 1, 0, J1[2] + 1.2), Hh(*J0)]
        Q.append((jc[2] + 0.1, 1, ([q[:2] for q in mi], (176, 36, 26), None, 0)))
        if ps["glow"] > 0.35 or ps["mouth"] > 0.7:
            gm = [Hh(8, 0, -4.2), Hh(19, 0, -3.9), Hh(J1[0] - 3, 0, J1[2] + 2.2), Hh(J0[0] + 4, 0, J0[2] + 0.5)]
            Q.append((jc[2] + 0.12, 1, ([q[:2] for q in gm], mix((255, 150, 60), (255, 230, 160), ps["glow"]), None, 0)))
    for k in range(4):                                       # 송곳니
        x = 7 + k * 4.4
        for sd in (-1, 1):
            a_, b_, c_ = Hh(x, sd * 3.2, -4.2), Hh(x + 2.0, sd * 3.2, -4.2), Hh(x + 1.0, sd * 3.0, -4.2 - (4.0 if k % 3 == 1 else 2.8))
            Q.append((Hh(x, sd * 3.2, -4.4)[2] + 0.25, 1, ([a_[:2], c_[:2], b_[:2]], (250, 244, 222), OL, 1)))
    for k in range(3):
        fr = 0.35 + k * 0.28
        bx_, bz_ = J0[0] + (J1[0] - J0[0]) * fr, J0[2] + (J1[2] - J0[2]) * fr
        for sd in (-1, 1):
            a_, b_, c_ = Hh(bx_, sd * 2.6, bz_ + 1.5), Hh(bx_ + 1.8, sd * 2.6, bz_ + 1.5), Hh(bx_ + 0.9, sd * 2.5, bz_ + 4.5)
            Q.append((jc[2] + 0.2, 1, ([a_[:2], c_[:2], b_[:2]], (250, 244, 222), OL, 1)))
    if ps["glow"] > 0.2:
        GLW.append((j0[0], j0[1], 18, (255, 170, 70), 150 * ps["glow"]))
    ctr = T(14, 0, 2)
    if ps["glow"] > 0.1:                                     # 가슴의 불덩이
        GLW.append((ctr[0], ctr[1] - 4, 13 + 10 * ps["glow"], (255, 150, 60), 150 * ps["glow"]))

    # ------------------------------------------------ 그리기
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
            s1, s2, col, hic, cold, claws, pF = d
            d_caps(cv, s1 + s2, col, hic)
            D.circle(cv, OL, (int(pF[0]), int(pF[1])), 4)
            D.circle(cv, cold, (int(pF[0]), int(pF[1])), 3)
            for pts_, cc in claws:
                D.polygon(cv, cc, pts_)
                D.polygon(cv, OL, pts_, 1)
    for x, y, r, col, a in GLW:
        blit_gl(cv, x, y, r, col, a)
    mt = Hh(25, 0, -2.5 - 7 * sm)
    return dict(mouth=mt[:2], nose=Hh(23, 0, 1)[:2], eye=Hh(7.5, 5.2, 3.2)[:2], head=skull[:2], chest=ctr[:2], tail=tail_tip,
                feet=feet, tips=wing_anc, body=sc[:2], top=Hh(0, 0, 14)[:2])