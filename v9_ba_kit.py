"""v9 보스 아트 도구함 (v9_ba_kit.py) - 중간보스·최종보스 신규 디자인이 함께 쓰는 그리기 도구.
 - 모든 보스는 CW x CH 짜리 투명 도화지(canvas)에 그린 뒤 화면에 얹는다. 기준점(AX, AY) = 보스 발 밑 중심.
 - 피격 점멸(fl)은 도화지 전체에 흰색을 더하는 것으로 처리하므로 그리기 코드는 점멸을 신경 쓰지 않아도 된다.
 - 게임 코드에 의존하지 않는다 (pygame 과 math 만 쓴다)."""
import math

import pygame

D = pygame.draw
SC = pygame.SRCALPHA
TAU = math.pi * 2
OUT = (20, 12, 26)
WHITE = (255, 255, 255)
CW, CH, AX, AY = 320, 300, 160, 236           # 도화지 크기, 기준점
_CV = {}
_GL = {}
_BG = {}


# ---------------------------------------------------------------- 색
def mix(a, b, k):
    k = max(0.0, min(1.0, k))
    return (int(a[0] + (b[0] - a[0]) * k), int(a[1] + (b[1] - a[1]) * k), int(a[2] + (b[2] - a[2]) * k))


def lit(c, k=0.3):
    return mix(c, WHITE, k)


def drk(c, k=0.4):
    return mix(c, (10, 6, 20), k)


# ---------------------------------------------------------------- 도화지
def canvas(key="a"):
    cv = _CV.get(key)
    if cv is None:
        cv = _CV[key] = pygame.Surface((CW, CH), SC)
    cv.fill((0, 0, 0, 0))
    return cv


def flash(cv):
    cv.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGB_ADD)


def put(surf, cv, x, y, alpha=255, tint=False, scale=1.0, anchor=None):
    """도화지를 (x, y) = 보스 발 밑 중심에 맞춰 화면에 얹는다. scale < 1 이면 줄여서 얹는다"""
    if tint:
        cv = cv.copy()
        cv.fill((90, 30, 10, 0), special_flags=pygame.BLEND_RGB_ADD)
    if scale != 1.0:
        cv = pygame.transform.smoothscale(cv, (max(1, int(cv.get_width() * scale)), max(1, int(cv.get_height() * scale))))
    elif alpha < 255:
        cv = cv.copy()
    if alpha < 255:
        cv.set_alpha(alpha)
    ax, ay = anchor if anchor else (AX, AY)
    surf.blit(cv, (int(x) - int(ax * scale), int(y) - int(ay * scale)))


# ---------------------------------------------------------------- 빛무리
def _soft():
    s = _BG.get("s")
    if s is None:
        s = pygame.Surface((96, 96), SC)
        for yy in range(96):
            for xx in range(96):
                d = math.hypot(xx - 47.5, yy - 47.5) / 48
                s.set_at((xx, yy), (255, 255, 255, int(255 * max(0.0, 1 - d) ** 1.6) if d < 1 else 0))
        _BG["s"] = s
    return s


def glow(cv, x, y, r, col, a):
    r, a = max(2, int(r) // 2 * 2), max(0, min(255, int(a))) // 20 * 20
    if a <= 0:
        return
    key = (r, col, a)
    g = _GL.get(key)
    if g is None:
        g = pygame.transform.smoothscale(_soft(), (r * 2, r * 2))
        g.fill(col + (a,), special_flags=pygame.BLEND_RGBA_MULT)
        _GL[key] = g
    cv.blit(g, (int(x) - r, int(y) - r))


# ---------------------------------------------------------------- 입체감 있는 도형
def ball(cv, x, y, r, c):
    x, y, r = int(x), int(y), max(1, int(r))
    D.circle(cv, OUT, (x, y), r + 1)
    D.circle(cv, drk(c, 0.38), (x, y), r)
    D.circle(cv, c, (x - r // 8, y - r // 6), max(1, int(r * 0.88)))
    if r >= 4:
        D.circle(cv, lit(c, 0.42), (x - r // 3, y - r // 2), max(1, int(r * 0.36)))


def rod(cv, a, b, w1, c, w2=None):
    """굵기가 변하는 막대(캡슐). 외곽선 + 윗면 하이라이트"""
    w2 = w1 if w2 is None else w2
    n = max(1, int(math.hypot(b[0] - a[0], b[1] - a[1]) / max(1.0, min(w1, w2) * 0.35)))
    pts = [(a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n, (w1 + (w2 - w1) * i / n) / 2) for i in range(n + 1)]
    for x, y, r in pts:
        D.circle(cv, OUT, (int(x), int(y)), int(r) + 1)
    for x, y, r in pts:
        D.circle(cv, c, (int(x), int(y)), max(1, int(r)))
    hi = lit(c, 0.3)
    for x, y, r in pts:
        if r >= 2.5:
            D.circle(cv, hi, (int(x - r * 0.28), int(y - r * 0.34)), max(1, int(r * 0.42)))


def poly(cv, pts, c, hi=0.0, ol=True):
    """면 하나. hi > 0 이면 첫 변을 따라 밝은 띠"""
    pts = [(int(px), int(py)) for px, py in pts]
    D.polygon(cv, c, pts)
    if hi > 0 and len(pts) >= 3:
        D.line(cv, lit(c, hi), pts[0], pts[1], 2)
    if ol:
        D.polygon(cv, OUT, pts, 1)


def box(cv, x, y, w, h, c):
    """외곽선 + 밝은 윗/왼쪽 + 어두운 아래/오른쪽 블록"""
    x, y, w, h = int(x), int(y), int(w), int(h)
    if w <= 0 or h <= 0:
        return
    cv.fill(OUT, (x - 1, y - 1, w + 2, h + 2))
    cv.fill(c, (x, y, w, h))
    cv.fill(lit(c, 0.36), (x, y, w, 1))
    cv.fill(lit(c, 0.18), (x, y, 1, h))
    cv.fill(drk(c, 0.34), (x, y + h - 1, w, 1))
    cv.fill(drk(c, 0.24), (x + w - 1, y, 1, h))


def prism(cv, x, y, w, h, dep, c, top=0.26):
    """쿼터뷰 직육면체: (x, y) = 앞면 왼쪽 위, 위로 dep 만큼 윗면이 보인다"""
    f = [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    poly(cv, f, c)
    cv.fill(lit(c, 0.2), (int(x) + 1, int(y) + 1, int(w) - 2, 2))
    cv.fill(drk(c, 0.3), (int(x) + 1, int(y + h) - 3, int(w) - 2, 2))
    poly(cv, [(x, y), (x + dep, y - dep), (x + w + dep, y - dep), (x + w, y)], lit(c, top))
    poly(cv, [(x + w, y), (x + w + dep, y - dep), (x + w + dep, y + h - dep), (x + w, y + h)], drk(c, 0.28))


def gear_pts(x, y, r, a0, teeth=8, depth=0.2):
    pts, st = [], TAU / teeth
    for i in range(teeth):
        a = a0 + i * st
        for off, rr in ((-0.5, r * (1 - depth)), (-0.27, r), (0.27, r), (0.5, r * (1 - depth))):
            pts.append((x + math.cos(a + off * st) * rr, y + math.sin(a + off * st) * rr))
    return pts


def gear(cv, x, y, r, a0, c, teeth=8, hole=0.28):
    poly(cv, gear_pts(x, y, r, a0, teeth), c, ol=False)
    D.polygon(cv, OUT, gear_pts(x, y, r, a0, teeth), 1)
    D.circle(cv, drk(c, 0.3), (int(x), int(y)), int(r * 0.62))
    D.circle(cv, lit(c, 0.12), (int(x - r * 0.05), int(y - r * 0.08)), int(r * 0.54))
    D.circle(cv, OUT, (int(x), int(y)), max(1, int(r * hole)))


def ell(x, y, rx, ry, n=28):
    return [(x + math.cos(i * TAU / n) * rx, y + math.sin(i * TAU / n) * ry) for i in range(n)]


# ---------------------------------------------------------------- 연기·불꽃·분사
def puff(cv, x, y, t, col, n=4, rise=22, spd=1.0, seed=0, sz=4):
    for i in range(n):
        f = (t * spd + i / n + seed * 0.37) % 1.0
        r = max(1, int(sz * (0.7 + f * 0.9)))
        D.circle(cv, mix(col, (46, 40, 66), f * 0.6), (int(x + math.sin((f + i) * 5 + seed) * 4), int(y - f * rise)), r)


def flame(cv, x, y, t, h=18, w=10, seed=0, hot=(255, 120, 50)):
    x, y = int(x), int(y)
    for k, (sc, col) in enumerate(((1.0, hot), (0.68, mix(hot, (255, 225, 110), 0.65)), (0.38, (255, 252, 225)))):
        fh = max(2, int(h * sc * (0.8 + 0.2 * math.sin(t * 17 + seed * 1.3 + k))))
        fw = max(1, int(w * sc / 2))
        sway = int(math.sin(t * 11 + seed) * 2)
        D.polygon(cv, col, [(x - fw, y), (x - fw // 2 + sway, y - fh // 2), (x + sway * 2, y - fh),
                            (x + fw // 2 + sway, y - fh // 2), (x + fw, y)])


def jet(cv, x, y, dx, dy, t, L=16, w=7, seed=0, hot=(255, 140, 50)):
    for k, (sc, col) in enumerate(((1.0, hot), (0.65, mix(hot, (255, 225, 110), 0.65)), (0.35, (255, 252, 225)))):
        ln = L * sc * (0.8 + 0.2 * math.sin(t * 20 + seed + k))
        px, py = -dy, dx
        ww = max(1.0, w * sc / 2)
        D.polygon(cv, col, [(x + px * ww, y + py * ww), (x + dx * ln * 0.5 + px * ww * 0.6, y + dy * ln * 0.5 + py * ww * 0.6),
                            (x + dx * ln, y + dy * ln), (x + dx * ln * 0.5 - px * ww * 0.6, y + dy * ln * 0.5 - py * ww * 0.6),
                            (x - px * ww, y - py * ww)])


def sparks(cv, x, y, t, col, n=5, r=16, spd=3.0, seed=0, sq=3):
    for i in range(n):
        a = t * spd + i * TAU / n + seed
        cv.fill(col, (int(x + math.cos(a) * r), int(y + math.sin(a) * r * 0.45), sq, sq))


def shadow(cv, w=60, h=16, a=80):
    s = pygame.Surface((w * 2, h * 2), SC)
    D.ellipse(s, (0, 0, 0, a), (0, 0, w * 2, h * 2))
    cv.blit(s, (AX - w, AY - h + 2))


def shadow_at(cv, x, y, w=30, h=8, a=80):
    s = pygame.Surface((w * 2, h * 2), SC)
    D.ellipse(s, (0, 0, 0, a), (0, 0, w * 2, h * 2))
    cv.blit(s, (int(x) - w, int(y) - h))


def clip_circle(cv, x, y, r, fn):
    """원 안쪽에만 fn(layer) 의 그림을 얹는다"""
    layer = pygame.Surface((int(r) * 2 + 2, int(r) * 2 + 2), SC)
    fn(layer, int(r) + 1, int(r) + 1)
    mask = pygame.Surface(layer.get_size(), SC)
    D.circle(mask, (255, 255, 255, 255), (int(r) + 1, int(r) + 1), int(r))
    layer.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    cv.blit(layer, (int(x) - int(r) - 1, int(y) - int(r) - 1))
