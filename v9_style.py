"""v9 스타일 모듈 (v9_style.py) - '고대 기계 황동' UI 전면 개편
 - 도트 한글 글꼴(assets/fonts/Galmuri11, SIL OFL 1.1): 원래 크기(12px)로 그린 뒤 정수 배로 키워 또렷하게 보인다
 - 공통 부품: 철판 + 황동 테두리 패널, 황동 명판(리본), 청록 룬 선택 막대, 키캡 안내
 - 새 디자인: 시작화면 / 조작법 / 일시정지 / 인벤토리(방향키로 재료 선택) / 상점 / 쓰러짐·엔딩 화면
 - 지도·모루·HUD·개발자 메뉴는 그리는 방식은 그대로 두고 새 패널·글꼴만 입는다
 - 윈도우 화면 배율(125%·150%)에서 창이 흐릿하게 늘어나던 문제: 고해상도(DPI) 인식을 켠다
게임 로직은 건드리지 않는다. game_v9.build() 맨 끝에서 설치한다:
    import v9_style
    v9_style.install(G, C, v9_ui, v9_open)
"""
import math
import os
import random
import sys

import pygame

D = pygame.draw
SC = pygame.SRCALPHA
HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = os.path.join(HERE, "assets", "fonts")
G = C = UI = O = None

# ---------------------------------------------------------------- 색 (황동 계열은 topdown_rpg.py 의 것을 그대로 쓴다)
IRON0, IRON1, IRON2, IRON3 = (13, 12, 19), (27, 25, 35), (40, 37, 50), (66, 61, 80)
RUNE, RUNE_D = (120, 232, 232), (34, 96, 108)
DISABLED = (86, 86, 104)
_C = {}           # 그림 캐시


def now():
    return pygame.time.get_ticks() / 1000.0


def lerp(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


# ================================================================= 도트 글꼴
class PixelFont:
    """Galmuri11(비트맵 12px)을 원래 크기로 그린 뒤 scale 배로 키운다. pygame.font.Font 처럼 쓴다."""
    _base = {}

    def __init__(self, size=12, bold=False, scale=None):
        self.scale = scale or max(1, int(size / 12 + 0.25))
        self.f = self._load(bold)
        self._cache = {}

    @classmethod
    def _load(cls, bold):
        if bold not in cls._base:
            cls._base[bold] = pygame.font.Font(os.path.join(FONT_DIR, "Galmuri11-Bold.ttf" if bold else "Galmuri11.ttf"), 12)
        return cls._base[bold]

    def render(self, text, antialias=False, color=(255, 255, 255), background=None):
        key = (text, tuple(color), tuple(background) if background else None)
        s = self._cache.get(key)
        if s is None:
            if len(self._cache) > 800:
                self._cache.clear()
            img = self.f.render(text, False, color, background) if background else self.f.render(text, False, color)
            w, h = img.get_size()
            base = pygame.Surface((w, h), SC)
            base.blit(img, (0, 0))
            s = pygame.transform.scale(base, (w * self.scale, h * self.scale)) if self.scale > 1 and w else base
            self._cache[key] = s
        return s

    def size(self, text):
        w, h = self.f.size(text)
        return w * self.scale, h * self.scale

    def get_height(self):
        return self.f.get_height() * self.scale

    def get_linesize(self):
        return self.f.get_linesize() * self.scale

    def get_ascent(self):
        return self.f.get_ascent() * self.scale

    def get_descent(self):
        return self.f.get_descent() * self.scale


def fonts_ok():
    return all(os.path.exists(os.path.join(FONT_DIR, n)) for n in ("Galmuri11.ttf", "Galmuri11-Bold.ttf"))


def load_font(size):
    return PixelFont(size)


def bigfont(u):
    k = ("big", u)
    if k not in _C:
        _C[k] = PixelFont(8.5 * u, bold=True)
    return _C[k]


def logo_font(u, scale=None):
    s = scale or max(2, round(u * 1.5))
    k = ("logo", s)
    if k not in _C:
        _C[k] = PixelFont(bold=True, scale=s)
    return _C[k]


def fpx(font, u):
    """글꼴 한 픽셀의 화면 크기 (그림자·외곽선 두께)"""
    return getattr(font, "scale", max(1, u // 2))


# ================================================================= 글자
def txt(screen, font, s, x, y, col=(255, 255, 255), center=False, u=2):
    img = font.render(s, True, col)
    sh = font.render(s, True, G.INK)
    x = x - img.get_width() // 2 if center else x
    o = fpx(font, u)
    screen.blit(sh, (x + o, y + o))
    screen.blit(img, (x, y))
    return img.get_width()


def title_txt(screen, font, s, cx, y, u, col=None):
    col = col or G.BRASS_L
    img, sh = font.render(s, True, col), font.render(s, True, G.INK)
    x = cx - img.get_width() // 2
    o = fpx(font, u)
    for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1), (1, 1), (2, 2), (1, 2)):
        screen.blit(sh, (x + ox * o, y + oy * o))
    screen.blit(img, (x, y))


def grad_text(font, s, top, bot, outline=None, shadow=None):
    """세로 그라데이션 글자 + 외곽선 + 그림자를 한 장으로 (로고·큰 제목용)"""
    k = ("gt", id(font), s, top, bot, outline, shadow)
    if k in _C:
        return _C[k]
    o = font.scale
    img = font.render(s, True, (255, 255, 255)).copy()
    w, h = img.get_size()
    gr = pygame.Surface((w, h), SC)
    for y in range(0, h, o):
        t = y / max(1, h - o)
        c = lerp(top, bot, t * 1.15 - 0.05)
        gr.fill(c + (255,), (0, y, w, o))
    img.blit(gr, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
    pad = 3 * o
    out = pygame.Surface((w + pad * 2, h + pad * 2), SC)
    if shadow:
        sh = font.render(s, True, shadow)
        for dx in range(-1, 2):
            out.blit(sh, (pad + dx * o + o, pad + 3 * o))
    if outline:
        ol = font.render(s, True, outline)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx or dy:
                    out.blit(ol, (pad + dx * o, pad + dy * o))
    out.blit(img, (pad, pad))
    _C[k] = (out, pad)
    return _C[k]


# ================================================================= 패널 · 명판 · 칸
def _panel_surf(w, h, u):
    k = ("panel", w, h, u)
    if k in _C:
        return _C[k]
    s = pygame.Surface((w, h), SC)
    s.fill(G.INK)
    D.rect(s, G.BRASS_D, (u, u, w - 2 * u, h - 2 * u))                     # 황동 테두리 (빛은 왼쪽 위)
    D.rect(s, G.BRASS, (u, u, w - 3 * u, h - 3 * u))
    D.rect(s, G.BRASS_L, (u, u, w - 2 * u, u))
    D.rect(s, G.BRASS_L, (u, u, u, h - 2 * u))
    D.rect(s, G.INK, (3 * u, 3 * u, w - 6 * u, h - 6 * u))
    ix, iy, iw, ih = 4 * u, 4 * u, w - 8 * u, h - 8 * u                       # 철판: 위가 조금 밝은 그라데이션
    step = 2 * u
    n = max(1, ih // step)
    for i in range(n + 1):
        y0 = iy + i * step
        if y0 >= iy + ih:
            break
        D.rect(s, lerp(IRON2, IRON1, i / max(1, n)), (ix, y0, iw, min(step, iy + ih - y0)))
    rng = random.Random(w * 31 + h)                                         # 결 무늬 (가는 줄)
    for _ in range(max(2, ih // (9 * u))):
        yy = iy + rng.randrange(2, max(3, ih // u - 2)) * u
        x0 = ix + rng.randrange(0, max(1, iw // u - 20)) * u
        ln = rng.randrange(10, 40) * u
        D.rect(s, lerp(IRON2, IRON3, 0.35), (x0, yy, min(ln, ix + iw - x0), u))
    D.rect(s, IRON3, (ix, iy, iw, u))                                       # 안쪽 윗면 반사 / 아래 그림자
    D.rect(s, IRON0, (ix, iy + ih - u, iw, u))
    for xx in range(14 * u, w - 14 * u, 26 * u):                            # 리벳
        for yy in (u, h - 3 * u):
            D.rect(s, G.BRASS_D, (xx, yy, 2 * u, 2 * u))
            D.rect(s, G.BRASS_L, (xx, yy, u, u))
    for cx, cy in ((0, 0), (w - 10 * u, 0), (0, h - 10 * u), (w - 10 * u, h - 10 * u)):   # 모서리 황동판 + 톱니 리벳
        D.rect(s, G.INK, (cx, cy, 10 * u, 10 * u))
        D.rect(s, G.BRASS_D, (cx + u, cy + u, 8 * u, 8 * u))
        D.rect(s, G.BRASS, (cx + u, cy + u, 7 * u, 7 * u))
        D.rect(s, G.BRASS_L, (cx + u, cy + u, 7 * u, u))
        mx, my = cx + 5 * u, cy + 5 * u
        for a in range(6):
            r = 3 * u
            D.rect(s, G.BRASS_D, (mx + int(math.cos(a * 1.047) * r) - u // 2, my + int(math.sin(a * 1.047) * r) - u // 2, u, u))
        D.circle(s, G.INK, (mx, my), 2 * u)
        D.circle(s, G.BRASS_L, (mx, my), u)
    _C[k] = s
    return s


def _shadow(w, h, a=120):
    k = ("shadow", w, h, a)
    if k not in _C:
        s = pygame.Surface((w, h), SC)
        s.fill((4, 2, 10, a))
        _C[k] = s
    return _C[k]


def frame(s, x, y, w, h, u):
    """철판 + 황동 테두리 + 리벳 + 모서리 톱니의 큰 패널"""
    w, h = int(w), int(h)
    s.blit(_shadow(w, h), (x + 2 * u, y + 3 * u))
    s.blit(_panel_surf(w, h, u), (x, y))


def plate(s, x, y, w, h, u, a=210):
    """HUD용 얇은 반투명 철판"""
    k = ("plate", w, h, u, a)
    if k not in _C:
        p = pygame.Surface((w, h), SC)
        p.fill(G.INK)
        D.rect(p, G.BRASS_D, (u, u, w - 2 * u, h - 2 * u), u)
        D.rect(p, G.BRASS, (u, u, w - 2 * u, u))
        D.rect(p, G.INK, (2 * u, 2 * u, w - 4 * u, h - 4 * u))
        D.rect(p, IRON1 + (a,), (3 * u, 3 * u, w - 6 * u, h - 6 * u))
        D.rect(p, IRON3 + (a,), (3 * u, 3 * u, w - 6 * u, u))
        for cx, cy in ((u, u), (w - 2 * u, u), (u, h - 2 * u), (w - 2 * u, h - 2 * u)):
            D.rect(p, G.BRASS_L, (cx, cy, u, u))
        _C[k] = p
    s.blit(_C[k], (x, y))


def _hex(x, y, w, h, c):
    return [(x + c, y), (x + w - c, y), (x + w, y + h // 2), (x + w - c, y + h), (x + c, y + h), (x, y + h // 2)]


def ribbon(screen, f2, text, cx, y, u):
    """패널 윗변에 걸치는 황동 명판 제목 (양 끝은 육각, 톱니 리벳)"""
    k = ("rib", text, u, id(f2))
    if k not in _C:
        tw, th = f2.size(text)
        w, h = tw + 36 * u, max(15 * u, th + 4 * u)
        s = pygame.Surface((w + 2 * u, h + 3 * u), SC)
        D.polygon(s, (4, 2, 10, 120), _hex(2 * u, 3 * u, w, h, 6 * u))
        D.polygon(s, G.INK, _hex(0, 0, w, h, 6 * u))
        D.polygon(s, G.BRASS_D, _hex(u, u, w - 2 * u, h - 2 * u, 5 * u))
        D.polygon(s, G.BRASS, _hex(u, u, w - 3 * u, h - 3 * u, 5 * u))
        D.rect(s, G.BRASS_L, (6 * u, u, w - 12 * u, u))
        D.rect(s, G.BRASS_D, (6 * u, h - 3 * u, w - 12 * u, u))
        for gx in (10 * u, w - 10 * u):
            D.circle(s, G.INK, (gx, h // 2), 3 * u)
            D.circle(s, G.BRASS_D, (gx, h // 2), 2 * u)
            D.rect(s, G.BRASS_L, (gx - u, h // 2 - u, u, u))
        o = fpx(f2, u)
        ty = (h - th) // 2
        s.blit(f2.render(text, True, G.BRASS_L), ((w - tw) // 2, ty + o))      # 새긴 글자: 아래쪽 반사
        s.blit(f2.render(text, True, G.INK), ((w - tw) // 2, ty))
        _C[k] = s
    s = _C[k]
    screen.blit(s, (cx - (s.get_width() - 2 * u) // 2, y))


def slot(s, x, y, size, u, on=False, name=None, dim=False, k=None):
    """아이콘 칸: 철판에 파인 홈 + 황동 테두리. on 이면 청록 룬 빛."""
    w = size * u
    key = ("slot", size, u, on, dim)
    if key not in _C:
        p = pygame.Surface((w + 2 * u, w + 2 * u), SC)
        if on:
            D.rect(p, RUNE_D, (0, 0, w + 2 * u, w + 2 * u), u)
        D.rect(p, G.INK, (u, u, w, w))
        rim = RUNE if on else (64, 62, 78) if dim else G.BRASS_D
        D.rect(p, rim, (2 * u, 2 * u, w - 2 * u, w - 2 * u), u)
        if not dim and not on:
            D.rect(p, G.BRASS, (2 * u, 2 * u, w - 2 * u, u))
        n = max(1, size - 4)
        for i in range(n):
            D.rect(p, lerp(IRON0, IRON2, i / max(1, n - 1)), (3 * u, (3 + i) * u, w - 4 * u, u))
        D.rect(p, (0, 0, 0), (3 * u, 3 * u, w - 4 * u, u))
        _C[key] = p
    s.blit(_C[key], (x - u, y - u))
    if name:
        ic = G.icon(name, k or u, dim)
        s.blit(ic, (x + (w - ic.get_width()) // 2, y + (w - ic.get_height()) // 2))


def sel_bar(s, x, y, w, h, u, cursor=True):
    """선택 막대: 청록 룬 빛 + 왼쪽 강조선 + 깜빡이는 화살표"""
    k = ("sel", w, h, u)
    if k not in _C:
        p = pygame.Surface((w, h), SC)
        for i in range(0, w, u):
            a = int(190 * (1 - i / w) ** 1.3) + 25
            D.rect(p, (36, 104, 116, a), (i, 0, u, h))
        D.rect(p, RUNE + (200,), (0, 0, w, u))
        D.rect(p, RUNE_D + (220,), (0, h - u, w, u))
        D.rect(p, RUNE, (0, 0, 2 * u, h))
        _C[k] = p
    s.blit(_C[k], (x, y))
    if cursor:
        bob = int((math.sin(now() * 8) + 1) * 0.5 * 2) * u
        cx, cy = x - 5 * u - bob, y + h // 2
        D.polygon(s, G.INK, [(cx - u, cy - 4 * u), (cx + 4 * u, cy), (cx - u, cy + 4 * u)])
        D.polygon(s, RUNE, [(cx, cy - 3 * u), (cx + 3 * u, cy), (cx, cy + 3 * u)])


def section(s, font, label, x, y, w, u, col=None):
    """'가방'·'능력 부메랑' 같은 소제목 + 황동 선"""
    tw = txt(s, font, label, x, y, col or G.GOLD, u=u)
    ly = y + font.get_height() // 2
    D.rect(s, G.BRASS_D, (x + tw + 4 * u, ly, w - tw - 4 * u, u))
    G.diamond(s, x + w, ly, 2 * u, G.BRASS)


def keycap_w(font, label, u):
    return font.size(label)[0] + 6 * fpx(font, u)


def keycap(s, font, label, x, y, u):
    """키보드 자판 모양 안내 (밝은 윗면 + 아래 턱). y 는 옆 글자의 y 와 같게 주면 된다. 너비를 돌려준다."""
    o = fpx(font, u)
    tw, th = font.size(label)
    w, h = tw + 6 * o, th - o
    y -= o
    D.rect(s, G.INK, (x, y, w, h + 2 * o))
    D.rect(s, (118, 112, 140), (x + o, y + o, w - 2 * o, h))
    D.rect(s, (214, 208, 228), (x + o, y + o, w - 2 * o, h - 2 * o))
    D.rect(s, (246, 242, 252), (x + o, y + o, w - 2 * o, o))
    s.blit(font.render(label, True, G.INK), (x + 3 * o, y + o))
    return w


def hints_w(font, pairs, u):
    o = fpx(font, u)
    return sum(keycap_w(font, k, u) + (3 * o + font.size(d)[0] if d else 0) for k, d in pairs) + 10 * o * (len(pairs) - 1)


def hints(s, font, pairs, x, y, u, align="left", col=None):
    """[(키, 설명)] 을 키캡과 함께 한 줄로. align = left / center / right"""
    o = fpx(font, u)
    total = hints_w(font, pairs, u)
    x = x - total // 2 if align == "center" else x - total if align == "right" else x
    for k, d in pairs:
        x += keycap(s, font, k, x, y, u)
        if d:
            x += 3 * o + txt(s, font, d, x + 3 * o, y, col or G.MUTED, u=u)
        x += 10 * o
    return total


def veil(screen, col, a):
    k = ("veil", screen.get_size(), col, a)
    if k not in _C:
        v = pygame.Surface(screen.get_size(), SC)
        v.fill(col + (a,))
        _C[k] = v
    screen.blit(_C[k], (0, 0))


def blur_bg(screen, tint=(10, 8, 22), a=150):
    """게임 화면을 흐리게 깔고 어둡게 덮는다 (일시정지·인벤토리 뒤)"""
    sw, sh = screen.get_size()
    small = pygame.transform.smoothscale(screen, (max(1, sw // 10), max(1, sh // 10)))
    screen.blit(pygame.transform.smoothscale(small, (sw, sh)), (0, 0))
    veil(screen, tint, a)


def vignette_edges(screen, col=(0, 0, 0), strength=170):
    sw, sh = screen.get_size()
    k = ("vig", sw, sh, col, strength)
    if k not in _C:
        lw, lh = 96, 54
        v = pygame.Surface((lw, lh), SC)
        for yy in range(lh):
            for xx in range(lw):
                d = math.hypot((xx / lw - 0.5) * 1.2, (yy / lh - 0.5) * 1.5)
                v.set_at((xx, yy), col + (int(max(0.0, min(1.0, (d - 0.32) / 0.5)) * strength),))
        _C[k] = pygame.transform.smoothscale(v, (sw, sh))
    screen.blit(_C[k], (0, 0))


# ================================================================= 작은 그림 (부메랑 · 메뉴 아이콘)
def boomerang(scale, angle, col=None):
    """도트 부메랑을 돌려서 scale 배로 (돌린 뒤 키워서 도트 느낌 유지)"""
    a = int(angle) // 15 * 15 % 360
    k = ("boom", scale, a, col)
    if k not in _C:
        b = pygame.Surface((17, 17), SC)
        pts = [(3, 12), (8, 4), (13, 12)]
        D.lines(b, G.INK, False, pts, 5)
        D.lines(b, col or G.BRASS, False, pts, 3)
        D.lines(b, G.BRASS_L, False, [(4, 11), (8, 5), (12, 11)], 1)
        D.rect(b, (220, 70, 70), (7, 4, 3, 2))
        r = pygame.transform.rotate(b, a)
        _C[k] = pygame.transform.scale(r, (r.get_width() * scale, r.get_height() * scale))
    return _C[k]


MENU_ICON = {}


def menu_icon(name, k):
    key = (name, k)
    if key in MENU_ICON:
        return MENU_ICON[key]
    s = pygame.Surface((9, 9), SC)
    c, d = G.CREAM, G.INK
    if name == "play":
        D.polygon(s, c, [(2, 1), (7, 4), (2, 7)])
    elif name == "save":
        s.fill(c, (1, 1, 7, 7)); s.fill(d, (3, 1, 3, 3)); s.fill(d, (2, 5, 5, 2))
    elif name == "map":
        D.polygon(s, c, [(1, 2), (3, 1), (6, 2), (8, 1), (8, 7), (6, 8), (3, 7), (1, 8)])
        s.fill(d, (3, 2, 1, 5)); s.fill(d, (5, 3, 1, 5))
    elif name == "sound":
        s.fill(c, (1, 3, 2, 3)); D.polygon(s, c, [(3, 3), (6, 0), (6, 8), (3, 5)])
        s.fill(c, (7, 2, 1, 1)); s.fill(c, (8, 4, 1, 1)); s.fill(c, (7, 6, 1, 1))
    elif name == "mute":
        s.fill(c, (1, 3, 2, 3)); D.polygon(s, c, [(3, 3), (6, 0), (6, 8), (3, 5)])
        s.fill((240, 108, 116), (7, 3, 1, 1)); s.fill((240, 108, 116), (8, 5, 1, 1))
    elif name == "home":
        D.polygon(s, c, [(0, 4), (4, 0), (8, 4)]); s.fill(c, (1, 4, 7, 4)); s.fill(d, (4, 5, 1, 3))
    elif name == "exit":
        s.fill(c, (1, 0, 5, 9)); s.fill(d, (2, 1, 3, 7)); D.polygon(s, c, [(5, 2), (8, 4), (5, 6)])
    elif name == "new":
        D.polygon(s, c, [(4, 0), (5, 3), (8, 4), (5, 5), (4, 8), (3, 5), (0, 4), (3, 3)])
    elif name == "load":
        D.circle(s, c, (4, 4), 4); D.circle(s, d, (4, 4), 2); s.fill(c, (4, 2, 1, 3))
    elif name == "help":
        s.fill(c, (2, 0, 5, 2)); s.fill(c, (6, 1, 2, 3)); s.fill(c, (4, 4, 2, 2)); s.fill(c, (4, 7, 2, 2))
    elif name == "gear":
        D.circle(s, c, (4, 4), 3); D.circle(s, d, (4, 4), 1)
        for px, py in ((4, 0), (4, 8), (0, 4), (8, 4), (1, 1), (7, 7), (1, 7), (7, 1)):
            s.fill(c, (px, py, 1, 1))
    MENU_ICON[key] = pygame.transform.scale(s, (9 * k, 9 * k))
    return MENU_ICON[key]


# ================================================================= 시작 화면
TITLE_DESC = {"새 게임": "빈 슬롯을 골라 처음부터 새로운 모험을 시작합니다", "이어하기": "저장 슬롯을 골라 모험을 이어갑니다",
              "설정": "화면 · 소리 · 화면 흔들림 · 난이도를 바꿉니다",
              "조작법": "키보드 · 게임패드 조작과 게임의 목표를 확인합니다", "종료": "게임을 끕니다"}
TITLE_ICON = {"새 게임": "new", "이어하기": "load", "설정": "gear", "조작법": "help", "종료": "exit"}


def _title_bg(u):
    """움직이지 않는 배경(하늘·노을 해·산·폐허·땅)을 한 장으로 만들어 둔다"""
    k = ("tbg", u)
    if k in _C:
        return _C[k]
    W, H = G.W, G.H
    s = pygame.Surface((W * u, H * u))
    stops = ((0.0, (9, 8, 24)), (0.42, (32, 20, 58)), (0.66, (96, 46, 86)), (0.76, (178, 86, 82)), (0.80, (232, 140, 90)))
    for y in range(0, H, 3):                                                 # 노을 하늘 (3도트 띠)
        f = y / H
        for (a0, c0), (a1, c1) in zip(stops, stops[1:]):
            if a0 <= f <= a1:
                c = lerp(c0, c1, (f - a0) / (a1 - a0))
                break
        else:
            c = stops[-1][1]
        s.fill(c, (0, y * u, W * u, 3 * u))
    sx, sy, sr = int(W * 0.72), int(H * 0.70), 46                           # 지는 해 + 빛무리
    for i in range(6, 0, -1):
        g_ = pygame.Surface(((sr + i * 9) * 2 * u, (sr + i * 9) * 2 * u), SC)
        D.circle(g_, (255, 160, 100, 14), ((sr + i * 9) * u, (sr + i * 9) * u), (sr + i * 9) * u)
        s.blit(g_, ((sx - sr - i * 9) * u, (sy - sr - i * 9) * u))
    D.circle(s, (255, 196, 128), (sx * u, sy * u), sr * u)
    D.circle(s, (255, 222, 160), (sx * u, (sy - 4) * u), (sr - 8) * u)
    for i, yy in enumerate((10, 18, 25, 31, 36)):                            # 해의 가로 줄무늬
        s.fill((150, 74, 84), ((sx - sr) * u, (sy + yy) * u, sr * 2 * u, (1 + i // 2) * u))
    base = int(H * 0.80)

    def ridge(seed, amp, y0, col, step=4):
        rng = random.Random(seed)
        ph = [rng.random() * 6 for _ in range(3)]
        pts = [(0, H * u)]
        for x in range(0, W + step, step):
            h = (math.sin(x * 0.013 + ph[0]) * 0.5 + math.sin(x * 0.031 + ph[1]) * 0.3 + math.sin(x * 0.07 + ph[2]) * 0.2)
            pts.append((x * u, int(y0 - amp * (0.6 + 0.4 * h)) // 2 * 2 * u))
        pts.append((W * u, H * u))
        D.polygon(s, col, pts)
    ridge(3, 52, base - 6, (70, 38, 80))
    ridge(9, 30, base + 2, (48, 28, 64), 3)
    rng = random.Random(21)                                                  # 폐허 실루엣: 부러진 기둥 · 아치 · 묻힌 톱니
    ruin = (30, 20, 46)
    for x in (150, 176, 214, 248, 400, 430, 462):
        hh = rng.randint(26, 58)
        s.fill(ruin, (x * u, (base - hh) * u, 8 * u, (hh + 20) * u))
        s.fill(ruin, ((x - 2) * u, (base - hh) * u, 12 * u, 3 * u))
        for j in range(3):
            s.fill(ruin, ((x + rng.randint(0, 6)) * u, (base - hh - j * 2 - 2) * u, 2 * u, 2 * u))
    D.circle(s, ruin, (196 * u, (base - 4) * u), 26 * u, 6 * u)
    gx, gy, gr = 108, base + 6, 34
    for i in range(14):
        a = i / 14 * math.tau
        D.circle(s, ruin, (int((gx + math.cos(a) * (gr + 3)) * u), int((gy + math.sin(a) * (gr + 3)) * u)), 4 * u)
    D.circle(s, ruin, (gx * u, gy * u), gr * u)
    D.circle(s, (40, 28, 58), (gx * u, gy * u), 10 * u)
    s.fill((16, 12, 26), (0, base * u, W * u, (H - base) * u))               # 땅 + 풀
    rng = random.Random(5)
    for x in range(0, W, 3):
        hh = rng.choice((1, 1, 2, 3))
        s.fill((16, 12, 26), (x * u, (base - hh) * u, 2 * u, hh * u))
    _C[k] = s
    return s


def _gate(screen, u, t):
    """오른쪽의 고대 기계 문: 돌 고리 + 순서대로 켜지는 청록 룬 + 소용돌이"""
    W, H = G.W, G.H
    cx, cy, R = int(W * 0.76), int(H * 0.80) - 50, 40
    k = ("gate", u)
    if k not in _C:
        s = pygame.Surface(((R + 22) * 2 * u, (R + 60) * 2 * u), SC)
        ox, oy = (R + 22) * u, (R + 22) * u
        for side in (-1, 1):                                                  # 기둥 (받침 위에 선다)
            px = ox + side * (R + 12) * u - 7 * u
            s.fill((44, 36, 58), (px, oy - 10 * u, 14 * u, (R + 12) * u))
            s.fill((60, 50, 76), (px, oy - 10 * u, 3 * u, (R + 12) * u))
            s.fill((30, 24, 42), (px - 3 * u, oy - 14 * u, 20 * u, 5 * u))
        D.circle(s, (22, 18, 32), (ox, oy), (R + 6) * u)                     # 고리
        D.circle(s, (74, 64, 92), (ox, oy), (R + 4) * u)
        D.circle(s, (56, 48, 72), (ox, oy), (R + 1) * u)
        D.circle(s, (10, 8, 20), (ox, oy), (R - 6) * u)
        for i in range(16):                                                    # 돌 블록 이음매
            a = i / 16 * math.tau
            p0 = (ox + int(math.cos(a) * (R - 6) * u), oy + int(math.sin(a) * (R - 6) * u))
            p1 = (ox + int(math.cos(a) * (R + 4) * u), oy + int(math.sin(a) * (R + 4) * u))
            D.line(s, (30, 24, 42), p0, p1, u)
        for i, (dw, hh) in enumerate(((20, 6), (26, 6), (32, 8))):            # 3단 돌 받침 (땅까지)
            yy = oy + (R + 2 + i * 6) * u
            s.fill((44, 36, 58) if i % 2 == 0 else (38, 30, 52), (ox - (R + dw) * u, yy, (R + dw) * 2 * u, hh * u))
            s.fill((66, 56, 82), (ox - (R + dw) * u, yy, (R + dw) * 2 * u, u))
        _C[k] = (s, ox, oy)
    s, ox, oy = _C[k]
    screen.blit(s, (cx * u - ox, cy * u - oy))
    core = pygame.Surface(((R - 6) * 2 * u, (R - 6) * 2 * u), SC)            # 문 안쪽 소용돌이
    cc = (R - 6) * u
    for i in range(46):
        a = i * 0.9 + t * (0.8 + (i % 3) * 0.3)
        r = ((i * 7.3 + t * 9) % (R - 8)) * u
        al = int(200 * (1 - r / ((R - 6) * u)))
        D.rect(core, (120, 232, 232, al), (cc + int(math.cos(a) * r), cc + int(math.sin(a) * r), u, u))
    pulse = 0.5 + 0.5 * math.sin(t * 1.7)
    D.circle(core, (120, 232, 232, int(30 + 30 * pulse)), (cc, cc), int((10 + 4 * pulse) * u))
    D.circle(core, (220, 255, 255, int(80 + 60 * pulse)), (cc, cc), 3 * u)
    screen.blit(core, (cx * u - cc, cy * u - cc))
    lit = t * 5
    for i in range(16):                                                       # 룬: 한 바퀴씩 차례로 빛난다
        a = i / 16 * math.tau - math.pi / 2
        d = (lit - i) % 16
        b = max(0.0, 1 - d / 5)
        col = lerp((40, 70, 80), RUNE, b)
        x, y = cx * u + int(math.cos(a) * (R - 1) * u), cy * u + int(math.sin(a) * (R - 1) * u)
        D.rect(screen, G.INK, (x - 2 * u, y - 2 * u, 4 * u, 4 * u))
        D.rect(screen, col, (x - u, y - u, 2 * u, 2 * u))
        if b > 0.6:
            gl = pygame.Surface((10 * u, 10 * u), SC)
            D.circle(gl, RUNE + (int(70 * b),), (5 * u, 5 * u), 5 * u)
            screen.blit(gl, (x - 5 * u, y - 5 * u))


def _embers(screen, u, t, n=46):
    W, H = G.W, G.H
    for i in range(n):
        r1, r2 = (i * 0.6180339) % 1, (i * 0.7548776) % 1
        sp = 6 + r2 * 10
        y = H - ((t * sp + r1 * H * 1.3) % (H * 1.1))
        x = (r2 * W + math.sin(t * 0.7 + i) * 8 + t * 2) % W
        f = max(0.0, min(1.0, y / H))
        col = lerp((255, 236, 170), (255, 120, 60), 1 - f)
        if f < 0.25 and int(t * 8 + i) % 3 == 0:
            continue
        D.rect(screen, col, (int(x) * u, int(y) * u, u, u))


def _stars(screen, u, t):
    rng = random.Random(7)
    for i in range(80):
        x, y = rng.randrange(0, G.W), rng.randrange(0, int(G.H * 0.45))
        b = 0.5 + 0.5 * math.sin(t * (1 + rng.random() * 2) + i)
        if b > 0.25:
            D.rect(screen, lerp((70, 66, 110), (255, 255, 255), b), (x * u, y * u, u, u))


def draw_title(screen, font, u, t, sel, items, help_on):
    SW, SH = G.W * u, G.H * u
    screen.blit(_title_bg(u), (0, 0))
    _stars(screen, u, t)
    _gate(screen, u, t)
    _embers(screen, u, t)
    vignette_edges(screen, (6, 4, 14), 150)
    lx = 30 * u                                                             # ---- 로고
    sub = bigfont(u)
    txt(screen, sub, "P I X E L   R U I N S", lx + 2 * u, 26 * u, (210, 160, 120), u=u)
    lf = logo_font(u)
    for i, (line, dx) in enumerate((("부메랑으로", 0), ("살아남기", 22))):
        img, pad = grad_text(lf, line, (255, 240, 180), (196, 120, 52), outline=G.INK, shadow=(26, 10, 30))
        screen.blit(img, (lx + dx * u - pad, (40 + i * 26) * u - pad))
    bw = lf.size("살아남기")[0] + 22 * u
    bx = lx + bw + 6 * u
    screen.blit(*_centered(boomerang(max(2, lf.scale - 1), t * 240), (bx + 14 * u, 76 * u)))
    ly = 98 * u
    D.rect(screen, G.BRASS_D, (lx, ly, 150 * u, u))
    G.diamond(screen, lx + 150 * u, ly, 3 * u, G.BRASS)
    txt(screen, font, "잊혀진 기계 문명의 수수께끼", lx, ly + 5 * u, G.CREAM, u=u)
    my, rh = 132 * u, 17 * u                                                # ---- 메뉴
    for i, (label, on) in enumerate(items):
        y = my + i * rh
        cur = i == sel
        if cur:
            sel_bar(screen, lx - 2 * u, y, 128 * u, rh - 3 * u, u)
        col = DISABLED if not on else G.GOLD if cur else G.CREAM
        x = lx + (8 if cur else 4) * u
        ic = menu_icon(TITLE_ICON.get(label, "play"), u)
        if not on:
            ic = ic.copy()
            ic.set_alpha(90)
        screen.blit(ic, (x, y + (rh - 3 * u - ic.get_height()) // 2))
        txt(screen, font, label + ("  (저장 없음)" if not on else ""), x + 14 * u, y + (rh - 3 * u - font.get_height()) // 2, col, u=u)
    label, on = items[sel]
    desc = TITLE_DESC.get(label, "")
    txt(screen, font, desc, lx, my + len(items) * rh + 3 * u, G.MUTED, u=u)
    D.rect(screen, (0, 0, 0), (0, SH - 18 * u, SW, 18 * u))                # ---- 아래 띠
    D.rect(screen, G.BRASS_D, (0, SH - 18 * u, SW, u))
    fy = SH - 13 * u
    th = _PRE_thread()
    if th:
        gx = 14 * u
        ic = boomerang(max(1, u // 2), t * 300, G.GOLD)
        screen.blit(*_centered(ic, (gx, fy + font.get_height() // 2)))
        txt(screen, font, "세계를 만드는 중" + "." * (int(t * 2) % 4), gx + 10 * u, fy, G.GOLD, u=u)
    else:
        txt(screen, font, "v9  ·  Pixel Ruins", 10 * u, fy, (110, 104, 130), u=u)
    hints(screen, font, [("W/S", "선택"), ("Enter", "확인")], SW - 10 * u, fy, u, "right")
    if help_on:
        draw_help(screen, font, u)


def _centered(img, c):
    return img, (c[0] - img.get_width() // 2, c[1] - img.get_height() // 2)


def _PRE_thread():
    if O is None:
        return False
    try:
        O.start_build()
        th = O._PRE["th"]
        return th is not None and th.is_alive()
    except Exception:
        return False


HELP_ROWS = ((("W", "A", "S", "D"), "이동 (방향키도 된다)"), (("Space",), "부메랑 던지기 · 가까운 적 자동 조준"),
             (("E",), "상호작용 · 상점 · 대장간 · 모루 · 마차 · 워프"), (("I",), "인벤토리"), (("Q",), "포션 마시기"),
             (("Z", "X", "C"), "능력 부메랑 켜기 / 끄기"), (("M",), "지도 · 워프포인트 이동"), (("N",), "소리 켜기 / 끄기"),
             (("ESC",), "일시정지"), (("F11",), "전체화면 켜기 / 끄기"))
PAD_LINE = "게임패드  스틱 이동 · A 부메랑/확인 · B 취소 · X 상호작용 · Y 가방 · LB 포션 · START 정지"


def draw_help(screen, font, u):
    SW, SH = G.W * u, G.H * u
    veil(screen, (6, 4, 14), 170)
    pw, ph = 330 * u, 232 * u
    px, py = (SW - pw) // 2, (SH - ph) // 2 + 6 * u
    frame(screen, px, py, pw, ph, u)
    ribbon(screen, bigfont(u), "조작법", SW // 2, py - 7 * u, u)
    y = py + 16 * u
    section(screen, font, "조작", px + 14 * u, y, pw - 30 * u, u)
    y += 12 * u
    for keys, desc in HELP_ROWS:
        x = px + 18 * u
        for kk in keys:
            x += keycap(screen, font, kk, x, y, u) + fpx(font, u) * 2
        txt(screen, font, desc, px + 96 * u, y, G.CREAM, u=u)
        y += 12 * u
    y += 3 * u
    section(screen, font, "목표", px + 14 * u, y, pw - 30 * u, u)
    txt(screen, font, "세 수호 기계를 쓰러뜨려 열쇠 조각을 모으고,", px + 18 * u, y + 12 * u, G.GOLD, u=u)
    txt(screen, font, "중앙 사원 깊은 곳에서 도시의 심장을 멈춰라.", px + 18 * u, y + 23 * u, G.GOLD, u=u)
    txt(screen, font, PAD_LINE, px + 18 * u, y + 37 * u, G.MUTED, u=u)
    hints(screen, font, [("아무 키", "닫기")], px + pw - 14 * u, py + ph - 14 * u, u, "right")


# ================================================================= 일시정지
PAUSE_ICONS = ("play", "save", "map", "gear", "home", "exit")


def draw_pause(screen, font, g, u):
    SW, SH = G.W * u, G.H * u
    blur_bg(screen, (10, 8, 22), 150)
    t = now()
    bx, by, bw, bh = 12 * u, 12 * u, 150 * u, SH - 24 * u                  # ---- 왼쪽: 메뉴
    frame(screen, bx, by, bw, bh, u)
    title_txt(screen, bigfont(u), "일시정지", bx + bw // 2, by + 12 * u, u, G.GOLD)
    txt(screen, font, "P A U S E D", bx + bw // 2, by + 30 * u, G.MUTED, True, u)
    D.rect(screen, G.BRASS_D, (bx + 14 * u, by + 42 * u, bw - 28 * u, u))
    G.diamond(screen, bx + bw // 2, by + 42 * u, 3 * u, G.BRASS)
    muted = getattr(G, "SND_MUTED", False)
    rh = 20 * u
    for i, label in enumerate(UI.PAUSE_ITEMS):
        y = by + 52 * u + i * rh
        cur = i == g["pm"]
        if cur:
            sel_bar(screen, bx + 10 * u, y, bw - 20 * u, rh - 4 * u, u)
        name = PAUSE_ICONS[i] if i < len(PAUSE_ICONS) else "play"
        if name == "sound" and muted:
            name = "mute"
        x = bx + (18 if cur else 14) * u
        ic = menu_icon(name, u)
        screen.blit(ic, (x, y + (rh - 4 * u - ic.get_height()) // 2))
        txt(screen, font, label, x + 14 * u, y + (rh - 4 * u - font.get_height()) // 2, G.GOLD if cur else G.CREAM, u=u)
    hints(screen, font, [("W/S", "선택"), ("Enter", "확인")], bx + bw // 2, by + bh - 26 * u, u, "center")
    hints(screen, font, [("ESC", "게임으로")], bx + bw // 2, by + bh - 14 * u, u, "center")
    rx, ry, rw = bx + bw + 10 * u, by, SW - (bx + bw + 10 * u) - 12 * u   # ---- 오른쪽: 현재 상황
    rh2 = 150 * u
    frame(screen, rx, ry, rw, rh2, u)
    ix = rx + 14 * u
    txt(screen, font, "현재 위치", ix, ry + 12 * u, G.MUTED, u=u)
    title_txt(screen, bigfont(u), G.REGIONS[g["reg"]]["name"], ix + bigfont(u).size(G.REGIONS[g["reg"]]["name"])[0] // 2,
              ry + 22 * u, u, G.CREAM)
    y = ry + 44 * u
    section(screen, font, "목표", ix, y, rw - 30 * u, u)
    for j, ln in enumerate(UI.wrap(font, UI.objective(g), rw - 32 * u)[:3]):
        txt(screen, font, ln, ix + 4 * u, y + (12 + j * 11) * u, G.CREAM, u=u)
    y = ry + 94 * u
    section(screen, font, "모험 기록", ix, y, rw - 30 * u, u)
    bosses = ("boss_w", "boss_e", "boss_n", "boss_d", "boss_f")
    stats = (("heart", "체력", f"{max(0, g['hp'])} / {g['mhp']}"), ("coin", "골드", f"{g['inv']['gold']}"),
             ("shard", "열쇠 조각", f"{g['keys']} / 3"), ("boom", "레벨", f"Lv.{g['lvl']}"),
             ("pierce", "능력 부메랑", f"{len(g['own'])} / {len(G.MODS)}"),
             ("part", "쓰러뜨린 보스", f"{sum(b in g['cleared'] for b in bosses)} / {len(bosses)}"))
    cw = (rw - 28 * u) // 3
    for j, (ic, lab, val) in enumerate(stats):
        x, yy = ix + (j % 3) * cw, y + 13 * u + (j // 3) * 19 * u
        slot(screen, x, yy, 14, u, name=ic)
        txt(screen, font, lab, x + 18 * u, yy, G.MUTED, u=u)
        txt(screen, font, val, x + 18 * u, yy + 8 * u, G.CREAM, u=u)
    tip = TIPS[int(t / 6) % len(TIPS)]                                       # ---- 아래: 팁
    ty = ry + rh2 + 8 * u
    plate(screen, rx, ty, rw, 24 * u, u, 200)
    txt(screen, font, "TIP", rx + 8 * u, ty + 8 * u, G.GOLD, u=u)
    txt(screen, font, tip, rx + 30 * u, ty + 8 * u, G.CREAM, u=u)


TIPS = ("부메랑은 돌아올 때도 적을 맞힌다. 되돌아오는 길을 노려라.",
        "모루 단련은 노란 중앙에서 내리치면 성공률이 크게 오른다.",
        "워프포인트는 가까이 가서 E로 켜야 지도에서 이동할 수 있다.",
        "보스가 기절했을 때가 공격할 기회다.",
        "능력 부메랑은 Z · X · C로 언제든 켜고 끌 수 있다.",
        "남은 재료는 상점에서 한꺼번에 팔 수 있다.")


# ================================================================= 인벤토리
INV_ITEMS = ("wood", "stone", "ore", "herb", "part", "potion")
INV_SRC = dict(wood="나무를 베어 얻는다", stone="바위를 깨서 얻는다", ore="철광석 광맥을 캐서 얻는다",
               herb="들판의 약초를 뜯어 얻는다", part="기계 적을 쓰러뜨리면 떨어진다", potion="상점에서 산다 · Q로 마시면 체력 3 회복")


def item_uses(k):
    reward = getattr(G, "MOD_REWARD", {})                                     # 보스 보상 능력은 재료로 만들지 않는다
    uses = [lab for key, lab, cost in G.MODS if k in cost and key not in reward] + \
           [lab for key, lab, desc, cost in G.ENH if k in cost]
    return uses


def draw_inventory(screen, font, g, u):
    SW, SH = G.W * u, G.H * u
    blur_bg(screen, (10, 8, 22), 120)
    inv, L, f2 = g["inv"], g["lv"], bigfont(u)
    pw, ph = 452 * u, 222 * u
    px, py = (SW - pw) // 2, (SH - ph) // 2 + 5 * u
    frame(screen, px, py, pw, ph, u)
    ribbon(screen, f2, "인벤토리", SW // 2, py - 8 * u, u)
    t = now()
    # ---- 왼쪽: 캐릭터 카드
    cx, cy, cw = px + 12 * u, py + 16 * u, 128 * u
    D.rect(screen, G.INK, (cx, cy, cw, 74 * u))
    for i in range(37):
        D.rect(screen, lerp((34, 30, 52), (16, 14, 26), i / 36), (cx + u, cy + u + i * 2 * u, cw - 2 * u, 2 * u))
    for i in range(7):                                                       # 뒤쪽 빛줄기
        a = t * 0.3 + i * 0.9
        p1 = (cx + cw // 2 + int(math.cos(a) * 70 * u), cy + 38 * u + int(math.sin(a) * 70 * u))
        p2 = (cx + cw // 2 + int(math.cos(a + 0.12) * 70 * u), cy + 38 * u + int(math.sin(a + 0.12) * 70 * u))
        ray = pygame.Surface((cw - 2 * u, 72 * u), SC)
        D.polygon(ray, (255, 226, 150, 14), [(cw // 2, 37 * u), (p1[0] - cx, p1[1] - cy), (p2[0] - cx, p2[1] - cy)])
        screen.blit(ray, (cx + u, cy + u))
    D.ellipse(screen, (10, 8, 18), (cx + cw // 2 - 22 * u, cy + 60 * u, 44 * u, 8 * u))
    spr = G.player_set(min(5, L["hp"]), min(5, L["spd"]))["down"][int(t * 2) % 2]
    img = pygame.transform.scale(spr, (spr.get_width() * 4 * u, spr.get_height() * 4 * u))
    screen.blit(img, (cx + (cw - img.get_width()) // 2, cy + 64 * u - img.get_height() + int(math.sin(t * 3) * u)))
    D.rect(screen, G.BRASS_D, (cx, cy, cw, 74 * u), u)
    y = cy + 80 * u
    title_txt(screen, f2, f"Lv.{g['lvl']}", cx + f2.size(f"Lv.{g['lvl']}")[0] // 2, y, u, (150, 210, 255))
    need = G.need_xp(g["lvl"])
    xt = f"{g['xp']} / {need}" if g["lvl"] < G.LV_MAX else "MAX"
    txt(screen, font, xt, cx + cw - font.size(xt)[0], y + 4 * u, G.MUTED, u=u)
    by_ = y + 15 * u
    D.rect(screen, G.INK, (cx, by_, cw, 6 * u))
    D.rect(screen, (24, 34, 70), (cx + u, by_ + u, cw - 2 * u, 4 * u))
    fw = (cw - 2 * u) * (g["xp"] if g["lvl"] < G.LV_MAX else need) // need
    D.rect(screen, (70, 130, 230), (cx + u, by_ + u, fw, 4 * u))
    D.rect(screen, (160, 210, 255), (cx + u, by_ + u, fw, u))
    y = by_ + 11 * u
    for j, (key, label, desc, base) in enumerate(G.ENH):                     # 능력치 (강화 반영)
        yy = y + j * 11 * u
        screen.blit(G.icon(G.ENH_ICON[key], u), (cx, yy))
        txt(screen, font, G.stat_line(g, key, L[key]), cx + 13 * u, yy, G.CREAM, u=u)
    yy = y + 5 * 11 * u + 3 * u
    screen.blit(G.icon("coin", u), (cx, yy))
    txt(screen, font, str(inv["gold"]), cx + 13 * u, yy, G.GOLD, u=u)
    for i in range(3):
        screen.blit(G.icon("shard" if i < g["keys"] else "shard0", u), (cx + 64 * u + i * 11 * u, yy))
    D.rect(screen, G.BRASS_D, (px + 148 * u, py + 16 * u, u, ph - 38 * u))   # 세로 구분선
    # ---- 오른쪽 위: 가방
    rx, rw = px + 156 * u, pw - 168 * u
    y = py + 14 * u
    section(screen, font, "가방", rx, y, rw, u)
    cur = g.get("ic", 0) % len(INV_ITEMS)
    sw_ = 38 * u
    for i, kk in enumerate(INV_ITEMS):
        x = rx + i * (sw_ + 8 * u)
        on = i == cur
        bob = int(abs(math.sin(t * 5)) * 2) * u if on else 0
        slot(screen, x, y + 12 * u - bob, 38, u, on=on, name=kk, k=3 * u, dim=inv[kk] == 0)
        s = str(inv[kk])
        txt(screen, font, s, x + sw_ - 4 * u - font.size(s)[0], y + 38 * u - bob, G.CREAM if inv[kk] else G.MUTED, u=u)
    kk = INV_ITEMS[cur]                                                      # 선택한 재료 설명
    dy = y + 56 * u
    D.rect(screen, G.INK, (rx, dy, rw, 34 * u))
    D.rect(screen, IRON0, (rx + u, dy + u, rw - 2 * u, 32 * u))
    D.rect(screen, RUNE_D, (rx + u, dy + u, 2 * u, 32 * u))
    txt(screen, font, f"{G.NAMES[kk]}  ×{inv[kk]}", rx + 8 * u, dy + 3 * u, G.GOLD, u=u)
    txt(screen, font, INV_SRC[kk], rx + 8 * u, dy + 13 * u, G.CREAM, u=u)
    uses = item_uses(kk)
    price = dict(G.SELL).get(kk)
    extra = ("쓰임: " + " · ".join(uses)) if uses else ""
    if price:
        extra += ("   " if extra else "") + f"판매가 {price}G"
    txt(screen, font, extra, rx + 8 * u, dy + 23 * u, G.MUTED, u=u)
    # ---- 오른쪽 가운데: 능력 부메랑
    y = dy + 40 * u
    section(screen, font, "능력 부메랑", rx, y, rw, u)
    cw3 = (rw - 8 * u) // 3
    for i, (key, label, cost) in enumerate(G.MODS):
        x = rx + i * (cw3 + 4 * u)
        own, on = key in g["own"], key in g["act"]
        plate(screen, x, y + 12 * u, cw3, 30 * u, u, 230)
        slot(screen, x + 5 * u, y + 16 * u, 22, u, on=on, name=key, k=2 * u, dim=not own)
        txt(screen, font, label, x + 31 * u, y + 17 * u, G.CREAM if own else G.MUTED, u=u)
        reward = getattr(G, "MOD_REWARD", {}).get(key)
        st, sc = ("켜짐", RUNE) if on else ("꺼짐", G.MUTED) if own else \
            ((f"{reward[2]} 처치 보상", G.GOLD) if reward else ("대장간 제작", G.CORAL))
        txt(screen, font, st, x + 31 * u, y + 28 * u, sc, u=u)
        keycap(screen, font, G.MOD_KEYS[i], x + cw3 - 14 * u, y + 17 * u, u)
    # ---- 오른쪽 아래: 강화
    y += 48 * u
    section(screen, font, "강화", rx, y, rw - 92 * u, u)
    txt(screen, font, "모루 작업대에서 강화", rx + rw - 88 * u, y, G.MUTED, u=u)
    cw5 = rw // 5
    for i, (key, label, desc, base) in enumerate(G.ENH):
        x = rx + i * cw5
        n = L[key]
        slot(screen, x + 2 * u, y + 12 * u, 16, u, on=n >= G.ENH_MAX, name=G.ENH_ICON[key], dim=n == 0)
        txt(screen, font, label, x + 21 * u, y + 12 * u, G.CREAM if n else G.MUTED, u=u)
        for j in range(G.ENH_MAX):
            D.rect(screen, G.INK, (x + (21 + j * 6) * u, y + 23 * u, 5 * u, 4 * u))
            D.rect(screen, G.GOLD if j < n else (54, 52, 70), (x + (21 + j * 6) * u + u, y + 23 * u + u, 3 * u, 2 * u))
    hints(screen, font, [("A/D", "재료 보기"), ("Q", "포션"), ("I", "닫기")], px + pw - 14 * u, py + ph - 15 * u, u, "right")


# ================================================================= 상점
def draw_shop(screen, font, g, u):
    SW, SH = G.W * u, G.H * u
    blur_bg(screen, (10, 8, 22), 110)
    kind, tab, cur = g["ui"], g["tab"], g["cur"]
    items, tabs, inv = G.shop_items(g, kind, tab), G.shop_tabs(kind), g["inv"]
    f2, rh = bigfont(u), 16 * u
    pw = 400 * u
    ph = (36 + len(items) * 16 + 56) * u
    px, py = (SW - pw) // 2, max(14 * u, (SH - ph) // 2 + 4 * u)
    frame(screen, px, py, pw, ph, u)
    ribbon(screen, f2, G.NPC_LABEL[kind], SW // 2, py - 8 * u, u)
    gs = str(inv["gold"])                                                    # 보유 골드
    plate(screen, px + pw - 62 * u, py + 13 * u, 50 * u, 14 * u, u, 240)
    screen.blit(G.icon("coin", u), (px + pw - 57 * u, py + 16 * u))
    txt(screen, font, gs, px + pw - 16 * u - font.size(gs)[0], py + 16 * u, G.GOLD, u=u)
    x = px + 12 * u                                                          # 탭
    for i, name in enumerate(tabs):
        tw = font.size(name)[0] + 16 * u
        on = i == tab
        D.rect(screen, G.INK, (x, py + 13 * u, tw, 14 * u))
        D.rect(screen, G.BRASS if on else IRON2, (x + u, py + 14 * u, tw - 2 * u, 12 * u))
        D.rect(screen, G.BRASS_L if on else IRON3, (x + u, py + 14 * u, tw - 2 * u, u))
        ty = py + 14 * u + (12 * u - font.get_height()) // 2
        if on:                                                               # 고른 탭: 황동판에 새긴 글자
            screen.blit(font.render(name, True, G.INK), (x + (tw - font.size(name)[0]) // 2, ty))
        else:
            txt(screen, font, name, x + tw // 2, ty, G.MUTED, True, u)
        x += tw + 4 * u
    y0 = py + 33 * u
    D.rect(screen, G.BRASS_D, (px + 10 * u, y0 - 3 * u, pw - 20 * u, u))
    for i, it in enumerate(items):
        ry = y0 + i * rh
        on = i == cur
        if on:
            sel_bar(screen, px + 10 * u, ry, pw - 20 * u, rh - 2 * u, u)
        slot(screen, px + 16 * u, ry + u, 12, u, on=on, name=G.item_icon(it), dim=it["done"] and it["kind"] != "mod")
        ty = ry + (rh - 2 * u - font.get_height()) // 2
        txt(screen, font, it["label"], px + 34 * u, ty, G.MUTED if it["done"] else G.GOLD if on else G.CREAM, u=u)
        lst = [(G.ICON_RES[k], str(v), G.GREEN if inv[k] >= v else G.CORAL) for k, v in it["cost"].items()]
        if it["gain"]:
            lst.append(("coin", f"+{it['gain']}", G.GOLD))
        G.chips(screen, font, lst, px + pw - 16 * u, ty, u)
    fy = y0 + len(items) * rh + 4 * u
    sel = items[min(cur, len(items) - 1)]
    D.rect(screen, G.INK, (px + 10 * u, fy, pw - 20 * u, 24 * u))
    D.rect(screen, IRON0, (px + 11 * u, fy + u, pw - 22 * u, 22 * u))
    D.rect(screen, RUNE_D, (px + 11 * u, fy + u, 2 * u, 22 * u))
    txt(screen, font, sel["desc"], px + 18 * u, fy + 3 * u, (206, 212, 230), u=u)
    m, ok = g["smsg"]
    if m:
        txt(screen, font, m, px + 18 * u, fy + 13 * u, G.GREEN if ok else G.CORAL, u=u)
    x, by_ = px + 14 * u, py + ph - 17 * u                                   # 보유 재료 + 안내
    for kk in ("wood", "stone", "ore", "herb", "part"):
        screen.blit(G.icon(kk, u), (x, by_))
        x += 11 * u
        x += txt(screen, font, str(inv[kk]), x, by_, G.CREAM if inv[kk] else G.MUTED, u=u) + 8 * u
    hints(screen, font, [("W/S", "선택"), ("A/D", "탭"), ("Enter", "확인"), ("E", "닫기")], px + pw - 14 * u, by_, u, "right")


# ================================================================= 쓰러짐 / 엔딩
def draw_end(screen, font, g, u):
    SW, SH = G.W * u, G.H * u
    dead = g["mode"] == "dead"
    if dead:
        veil(screen, (40, 4, 10), 150)
        vignette_edges(screen, (60, 0, 8), 230)
    else:
        veil(screen, (10, 8, 26), 175)
        vignette_edges(screen, (0, 0, 0), 160)
    t = now()
    lf = logo_font(u, max(2, u))
    title = "쓰러졌다..." if dead else "핵이 멈췄다"
    top, bot = ((255, 150, 150), (180, 40, 60)) if dead else ((255, 246, 190), (210, 140, 50))
    img, pad = grad_text(lf, title, top, bot, outline=G.INK, shadow=(10, 4, 10))
    y = int(SH * 0.30) + int(math.sin(t * 2) * u)
    screen.blit(img, (SW // 2 - img.get_width() // 2, y - pad))
    ly = y + lf.get_height() + 8 * u
    D.rect(screen, G.BRASS_D, (SW // 2 - 90 * u, ly, 180 * u, u))
    G.diamond(screen, SW // 2, ly, 3 * u, G.BRASS)
    lines = ["부메랑이 손에서 미끄러졌다. 하지만 모험은 끝나지 않았다.", "마을에서 다시 일어나면 골드의 20%를 잃는다."] if dead else \
        ["벽화의 마지막 기록이 떠올랐다.", "문명을 무너뜨린 것은 외부의 적이 아니라", "스스로 만든 기계의 폭주였다."]
    for i, s in enumerate(lines):
        txt(screen, font, s, SW // 2, ly + (8 + i * 12) * u, G.CREAM, True, u)
    hy = ly + (14 + len(lines) * 12) * u
    pairs = [("R", "마을에서 부활"), ("ESC", "게임 종료")] if dead else [("R", "새 게임"), ("ESC", "게임 종료")]
    hints(screen, font, pairs, SW // 2, hy, u, "center")


# ================================================================= HUD
def _vtxt(screen, font, s, x, y, h, col, u, center=False):
    """높이 h 칸의 세로 가운데에 글자"""
    return txt(screen, font, s, x, y + (h - font.get_height()) // 2 + fpx(font, u) // 2, col, center, u)


def hud(screen, font, g, u):
    inv, SW, SH = g["inv"], G.W * u, G.H * u
    fh, o = font.get_height(), fpx(font, u)
    if g["hurt_t"] > 0:                                                     # 피격 섬광 / 빈사 붉은 테두리
        v = pygame.Surface((SW, SH), SC)
        v.fill((255, 30, 40, int(95 * g["hurt_t"] / 0.45)))
        screen.blit(v, (0, 0))
    if g["hp"] <= max(1, g["mhp"] // 4) and g["mode"] == "play":
        rv = UI.red_vig(u)
        rv.set_alpha(int(110 + 90 * math.sin(g["t"] * 5)))
        screen.blit(rv, (0, 0))
    # ---- 왼쪽 위: 초상 + 체력 + 경험치 + 레벨
    for r, c in ((13, G.INK), (12, G.BRASS_D), (11, G.BRASS), (9, G.INK), (8, (70, 34, 58))):
        D.circle(screen, c, (15 * u, 15 * u), r * u)
    screen.blit(G.icon("heart", 2 * u), (6 * u, 6 * u))
    w = G.hp_bar(screen, g, 30 * u, 5 * u, u)
    _vtxt(screen, font, f"{max(0, g['hp'])}/{g['mhp']}", 30 * u + w + 4 * u, 5 * u, 10 * u, G.CREAM, u)
    need, xw = G.need_xp(g["lvl"]), 74 * u
    D.rect(screen, G.INK, (30 * u, 17 * u, xw + 2 * u, 5 * u))
    D.rect(screen, (24, 34, 70), (31 * u, 18 * u, xw, 3 * u))
    fw = xw * (g["xp"] if g["lvl"] < G.LV_MAX else need) // need
    D.rect(screen, (70, 130, 230), (31 * u, 18 * u, fw, 3 * u))
    D.rect(screen, (160, 210, 255), (31 * u, 18 * u, fw, u))
    lv = f"Lv.{g['lvl']}"
    lw = font.size(lv)[0] + 8 * u
    ph = fh + 4 * u
    plate(screen, 15 * u - lw // 2, 26 * u, lw, ph, u, 240)
    _vtxt(screen, font, lv, 15 * u, 26 * u, ph, (150, 210, 255), u, True)
    y = 26 * u + ph + 3 * u                                                 # 골드 / 열쇠 조각
    plate(screen, 3 * u, y, 64 * u, ph * 2 + 2 * u, u)
    screen.blit(G.icon("coin", u), (9 * u, y + (ph - 9 * u) // 2 + u))
    _vtxt(screen, font, str(inv["gold"]), 21 * u, y + u, ph, G.GOLD, u)
    for i in range(3):
        screen.blit(G.icon("shard" if i < g["keys"] else "shard0", u), (9 * u + i * 11 * u, y + ph + (ph - 9 * u) // 2))
    _vtxt(screen, font, f"{g['keys']}/3", 45 * u, y + ph, ph, G.CREAM if g["keys"] else G.MUTED, u)
    # ---- 오른쪽 위: 미니맵 + 목표
    mx = SW - 72 * u
    plate(screen, mx, 4 * u, 68 * u, 52 * u, u)
    UI.draw_minimap(screen, g, u, mx + 4 * u, 8 * u)
    hints(screen, font, [("M", "지도")], mx + 34 * u, 59 * u, u, "center")
    ow = 128 * u
    lines = UI.wrap(font, UI.objective(g), ow - 12 * u)
    lh = fh + o
    oy = 59 * u + fh + 4 * u
    plate(screen, SW - ow - 4 * u, oy, ow, 8 * u + fh + lh * len(lines), u, 225)
    G.diamond(screen, SW - ow + 3 * u, oy + 4 * u + fh // 2, 2 * u, G.GOLD)
    txt(screen, font, "목표", SW - ow + 8 * u, oy + 4 * u, G.GOLD, u=u)
    for i, ln in enumerate(lines):
        txt(screen, font, ln, SW - ow + 3 * u, oy + 4 * u + fh + i * lh, G.CREAM, u=u)
    # ---- 위 가운데: 지역 이름 / 알림
    name = G.REGIONS[g["reg"]]["name"]
    nw = font.size(name)[0] + 24 * u
    plate(screen, (SW - nw) // 2, 3 * u, nw, ph, u)
    _vtxt(screen, font, name, SW // 2, 3 * u, ph, G.GOLD, u, True)
    G.diamond(screen, (SW - nw) // 2 + 7 * u, 3 * u + ph // 2, 2 * u, G.BRASS)
    G.diamond(screen, (SW + nw) // 2 - 7 * u, 3 * u + ph // 2, 2 * u, G.BRASS)
    if g["toast"][1] > 0 and g["toast"][0] != name:
        tw = font.size(g["toast"][0])[0] + 20 * u
        plate(screen, (SW - tw) // 2, 5 * u + ph, tw, ph, u, 235)
        _vtxt(screen, font, g["toast"][0], SW // 2, 5 * u + ph, ph, (255, 240, 170), u, True)
    UI.boss_bar(screen, font, g, u)
    if g["lvup"] > 0:
        title_txt(screen, bigfont(u), f"LEVEL UP!  Lv.{g['lvl']}", SW // 2,
                  (64 - int(10 * (1 - min(1.0, g["lvup"] / 2.4)))) * u, u, (150, 210, 255))
    # ---- 아래: 상호작용 안내 / 핫바 / 재료 띠
    npc, a, ex = G.near_npc(g), g["aim"], G.near_exit(g)
    warp = O.near_warp(g) if (O and g["zid"] == O.WID and g["ui"] is None and g["mode"] == "play") else None
    if warp:
        pairs, extra = [("E", "워프포인트 활성화" if warp["id"] not in g["wact"] else "지도 열기 · 워프 이동")], ""
    elif npc and npc[0] == "bench":
        pairs, extra = [("E", "모루에서 강화하기")], ""
    elif npc:
        pairs, extra = [("E", f"{npc[1]} 이용하기")], ""
    elif a:
        pairs, extra = [("Space", "부메랑 발사")], f"  ·  조준: {G.target_name(a)}"
    elif ex:
        pairs, extra = [], f"길을 따라 이동 → {G.ZONES[ex['to']]['name']}"
    else:
        pairs, extra = [("Space", "부메랑 발사")], "  (바라보는 방향)"
    hw = (hints_w(font, pairs, u) if pairs else 0) + font.size(extra)[0] + 18 * u
    hy = SH - ph - 3 * u
    plate(screen, (SW - hw) // 2, hy, hw, ph, u)
    x = (SW - hw) // 2 + 9 * u
    ty = hy + (ph - fh) // 2 + o // 2
    if pairs:
        x += hints(screen, font, pairs, x, ty, u, col=G.CREAM)
    if extra:
        txt(screen, font, extra, x, ty, (150, 245, 245) if warp else G.CREAM, u=u)
    sz = 18
    sy = hy - 4 * u - fh // 2 - sz * u
    sx0 = (SW - (4 * sz + 3 * 4) * u) // 2
    for i, (nm, key) in enumerate((("potion", "Q"),) + tuple((m[0], G.MOD_KEYS[j]) for j, m in enumerate(G.MODS))):
        sx = sx0 + i * (sz + 4) * u
        mod = i > 0
        owned, on = (nm in g["own"], nm in g["act"]) if mod else (inv["potion"] > 0, False)
        slot(screen, sx, sy, sz, u, on=on, name=nm, dim=not owned)
        if not mod:
            s = str(inv["potion"])
            txt(screen, font, s, sx + (sz - 2) * u - font.size(s)[0], sy + sz * u - fh - u, G.CREAM if owned else G.MUTED, u=u)
        kw = keycap_w(font, key, u)
        keycap(screen, font, key, sx + (sz * u - kw) // 2, sy + sz * u - fh // 3, u)
    mw = 8 * u
    for k in ("wood", "stone", "ore", "herb", "part"):
        mw += 11 * u + font.size(str(inv[k]))[0] + 6 * u
    plate(screen, 3 * u, SH - ph - 3 * u, mw, ph, u)
    x = 8 * u
    for k in ("wood", "stone", "ore", "herb", "part"):
        screen.blit(G.icon(k, u), (x, SH - ph - 3 * u + (ph - 9 * u) // 2))
        x += 11 * u
        x += _vtxt(screen, font, str(inv[k]), x, SH - ph - 3 * u, ph, G.CREAM if inv[k] else G.MUTED, u) + 6 * u


# ================================================================= 설치
def _dpi_aware():
    """윈도우 화면 배율(125%·150%)에서 창이 흐릿하게 늘어나지 않도록 고해상도를 직접 쓴다"""
    if sys.platform != "win32" or os.environ.get("SDL_VIDEODRIVER") == "dummy":
        return
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def install(g_mod, cfg, ui_mod, open_mod=None):
    global G, C, UI, O
    G, C, UI, O = g_mod, cfg, ui_mod, open_mod
    if not fonts_ok():
        print("[v9] 참고: assets/fonts 에 Galmuri 글꼴이 없어 새 UI 스타일을 끈다", file=sys.stderr)
        return
    _dpi_aware()
    G.load_font, G.bigfont = load_font, bigfont
    G.txt, G.title_txt = txt, title_txt
    G.frame, G.plate, G.ribbon, G.slot = frame, plate, ribbon, slot
    G.draw_inventory, G.draw_shop, G.draw_end = draw_inventory, draw_shop, draw_end
    UI.draw_pause = draw_pause
    G.hud = hud                                                             # 워프 안내도 여기서 그린다 (v9_open.hud_wrap 대체)
    UI.draw_title = G.draw_title = draw_title
    old_key = G.on_key

    def on_key(g, k):                                                        # 인벤토리: A/D(←/→)로 재료 고르기
        if g is not None and g.get("ui") == "inv" and k in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d):
            d = -1 if k in (pygame.K_LEFT, pygame.K_a) else 1
            g["ic"] = (g.get("ic", 0) + d) % len(INV_ITEMS)
            G.play("ui")
            return g
        return old_key(g, k)
    G.on_key = on_key
