"""v9_roster_pat.py - 보스 패턴 + 연출 패치 (v9_roster.py 는 수정하지 않는다)

사용법 (install 직전에 한 번):
    import v9_roster, v9_roster_art, v9_roster_pat
    v9_roster_art.apply(v9_roster)      # (선택) 비주얼 패치
    v9_roster_pat.apply(v9_roster)      # 이 파일
    v9_roster.install(G, C, B)

추가되는 패턴
 - 빅 브라더 : [박동] 심장 박동에 맞춰 예고(쿵) -> 발동(쿵). 4페이즈에는 박동 사이 이완기에 받는 피해 2배
               [감시의 시선] 부채꼴 시야에 머물면 조준 레이저. 기둥 뒤로 숨는다 (2~3페이즈)
               [과거의 그림자] 3초 전에 내가 있던 자리마다 장판이 터진다 (3~4페이즈)
 - 정비관    : 열 충격 - 화상 중 냉기 구역은 화상을 꺼 주고, 빙결 중 불꽃 구역은 추가 피해(열 충격)
 - 수문장    : 철벽 돌진이 벽에 박힌 자리에 균열 장판이 남는다 / [연쇄 발구르기] 체스판 충격파 (2~3페이즈)
연출
 - 히트 스톱(보스 피격 시 아주 짧은 정지), 페이즈 전환 슬로모션 + 화면 가장자리 비네팅
 - 최종 보스방: 박동에 맞춰 퍼지는 파동 링, 큰 패턴 시작 시 이름 컷인
튜닝 값은 아래 상수에서 바꾼다."""
import math
import random

import pygame

D = pygame.draw
SC = pygame.SRCALPHA
TAU = math.pi * 2
RATE = (1.0, 1.3, 1.8, 3.2)          # 빅 브라더 박동 속도 (v9_roster_art 의 심장과 같은 값)
HITSTOP = 0.045                       # 보스 피격 정지(초). 0 이면 끈다
HITSTOP_GAP = 0.28                    # 히트 스톱 최소 간격
RELAX_MULT = 2.0                      # 4페이즈 이완기 피해 배율
SLOWMO = 0.9                          # 페이즈 전환 슬로모션 길이(실시간 초)
_R = None
_VIG = {}

CUT = {"charge": "철벽 돌진", "mortar": "박격포 사격", "ghosts": "열화 잔상", "stomp": "연쇄 발구르기",
       "net": "용융 열화선 그물", "slag": "폐기물 투하", "golem": "골렘 주조", "magnet": "과전압 자석", "gears": "톱니 바조카",
       "sweep": "플라즈마 스윕", "vent": "냉각재 방출", "shatter": "동결 쇄빙참", "tornado": "플라즈마 토네이도",
       "frenzy": "무한 점멸 난무", "bombard": "그리드 폭격", "gravity": "중력 역전", "hack": "시스템 해킹",
       "beam": "코어 빔", "rhythm": "박동", "gaze": "감시의 시선", "echo": "과거의 그림자", "orbs": "차원 균열",
       "grid": "회로 절단"}


def safe(fn):
    """패턴 코루틴이 예외를 던져도 보스가 멈추지 않게 감싼다"""
    def w(g, e):
        try:
            yield from fn(g, e)
        except Exception:
            try:
                _R.G.v9_log("pat-" + fn.__name__)
            except Exception:
                pass
    w.__name__ = fn.__name__
    return w


def _tel(w):
    """실제로 w초 뒤에 터지도록 hz 의 warn 값을 보정한다 (난이도 배율 상쇄)"""
    return w / max(0.01, _R.B.tm(1.0))


def until_beat(e, rate):
    """다음 박동(쿵)까지 기다린다"""
    prev = (e["an"] * rate) % 1.0
    for _ in range(80):
        yield 0.02
        cur = (e["an"] * rate) % 1.0
        if cur < prev:
            return
        prev = cur


# ================================================================= 빅 브라더
@safe
def fb_rhythm(g, e):
    """박동 전투: 쿵(예고) -> 다음 쿵(발동). 홀수 박동은 탄막 고리, 짝수 박동은 내 자리에 장판"""
    R = _R
    G, B = R.G, R.B
    ph = e["phase"]
    rate = RATE[ph - 1]
    step = 2 if ph == 4 else 1                                  # 4페이즈는 너무 빨라서 두 박동에 한 번
    gap = step / rate
    G.play("boss")
    yield from until_beat(e, rate)
    for i in range(7):
        if i % 2 == 0 or ph >= 3:
            R.hz(g, "circle", _tel(gap), 0.3, x=g["x"], y=g["y"], r=22 + 2 * ph)
        if i % 2 == 1 or ph >= 3:
            B.ring_gap(g, e, 22 + 2 * ph, 94 + 8 * ph, B.angto(g, e) + random.uniform(-0.8, 0.8), 0.34, 0)
            G.play("shoot")
        g["shake"] = max(g.get("shake", 0), 0.06)
        for _ in range(step):
            yield from until_beat(e, rate)
    yield 0.6


@safe
def fb_gaze(g, e):
    """감시의 시선: 부채꼴 시야에 오래 머물면 조준 레이저. 기둥 뒤로 숨어 노출을 식혀라"""
    R = _R
    G, B = R.G, R.B
    ph = e["phase"]
    hw, turn, need = (0.4, 1.0, 0.9) if ph == 2 else (0.34, 1.5, 0.75)
    st = dict(own=e, x=e["x"], y=e["y"], a=B.angto(g, e) + random.choice((-1.1, 1.1)), hw=hw, exp=0.0, need=need,
              flash=0.0, len=560.0)
    g["gaze"] = st
    G.play("portal")
    try:
        yield B.tm(0.6)
        t = 0.0
        while t < 7.0 and e["hp"] > 0:
            st["x"], st["y"] = e["x"], e["y"]
            want = B.angto(g, e)
            d = R.ang_diff(want, st["a"])
            st["a"] += max(-turn * 0.03, min(turn * 0.03, d))
            e["lk"] = st["a"]                                   # 눈이 시야 방향을 본다
            px, py = g["x"], g["y"]
            inside = (abs(R.ang_diff(want, st["a"])) < hw and G.dist(e["x"], e["y"], px, py) < st["len"]
                      and not R.covered(g, e["x"], e["y"], px, py))
            if st["exp"] < 0:
                st["exp"] = min(0.0, st["exp"] + 0.03)          # 발사 후 재장전
            elif inside:
                st["exp"] = min(need, st["exp"] + 0.03)
            else:
                st["exp"] = max(0.0, st["exp"] - 0.045)
            st["flash"] = max(0.0, st["flash"] - 0.03)
            if st["exp"] >= need:
                a = B.angto(g, e)
                R.hz(g, "beam", 0.35, 0.14, x=e["x"], y=e["y"], a=a, len=620, w=11, dmg=False, los=True)
                G.play("gate")
                st["exp"], st["flash"] = -0.9, 0.5
            t += 0.03
            yield 0.03
        yield 0.5
    finally:
        g["gaze"] = None


@safe
def fb_echo(g, e):
    """과거의 그림자: 3초 전에 내가 있던 자리마다 장판이 터진다. 같은 곳에 오래 서 있지 마라"""
    R = _R
    G = R.G
    n = 8 if e["phase"] == 4 else 10
    hist = []
    G.play("portal")
    for _ in range(26):
        hist.append((g["x"], g["y"]))
        if len(hist) > n:
            px, py = hist.pop(0)
            R.hz(g, "circle", 0.55, 0.4, x=px, y=py, r=21)
            G.spark(g, px, py, (190, 160, 255), 5)
        yield 0.3
    yield 0.8


# ================================================================= 수문장
def crack_zone(g, x, y):
    """돌진 충돌 지점에 남는 균열 장판"""
    R = _R
    R.hz(g, "circle", 0.4, 6.0, x=x, y=y, r=24)
    base = random.random() * TAU
    for k in range(4):
        R.hz(g, "beam", 0.4, 6.0, x=x, y=y, a=base + k * TAU / 4, len=64, w=7)
    _R.G.spark(g, x, y, (255, 190, 110), 14)


def wrap_charge(orig):
    def b1_charge2(g, e):
        done = False
        try:
            for dt in orig(g, e):
                if not done and e["st"] == "stun":
                    done = True
                    crack_zone(g, e["x"], e["y"])
                yield dt
        except Exception:
            _R.G.v9_log("pat-charge")
    return b1_charge2


@safe
def b_stomp(g, e):
    """연쇄 발구르기: 체스판 모양으로 충격파가 번갈아 터진다. 반대 색 칸이 안전하다"""
    R = _R
    G, B = R.G, R.B
    x0, y0, x1, y1 = B.bounds(g)
    S = 52
    nx, ny = int((x1 - x0) // S) + 1, int((y1 - y0) // S) + 1
    par = random.randint(0, 1)
    for wave in range(4):
        warn = max(0.6, 0.95 - 0.1 * wave)
        for i in range(nx):
            for j in range(ny):
                if (i + j + par + wave) % 2 == 0:
                    R.hz(g, "rect", warn, 0.4, x0=x0 + i * S, x1=min(x1, x0 + (i + 1) * S),
                         y0=y0 + j * S, y1=min(y1, y0 + (j + 1) * S))
        G.play("gate")
        yield B.tm(warn) + 0.45
        g["shake"] = max(g.get("shake", 0), 0.25)
    yield 0.6


# ================================================================= 후킹
def _vig(W, H, col):
    k = (W, H, col)
    if k not in _VIG:
        sf = pygame.Surface((W, H), SC)
        for i in range(30):
            al = int(235 * (1 - i / 30) ** 2.3)
            D.rect(sf, tuple(col) + (al,), (i, i, W - 2 * i, H - 2 * i), 1)
        _VIG[k] = sf
    return _VIG[k]


def _draw_extra(surf, g, cx, cy):
    R = _R
    G, B = R.G, R.B
    W, H = G.W, G.H
    t = g["t"]
    fe = next((o for o in g["en"] if o["kind"] == "final" and o["hp"] > 0), None)
    gz = g.get("gaze")
    active_boss = bool(fe and g["lock"] and g["intro"] <= 0)
    if active_boss or gz:
        L = pygame.Surface((W, H), SC)
        if active_boss:                                         # 박동 파동 링
            ph = fe["phase"]
            f = (fe["an"] * RATE[ph - 1]) % 1.0
            col = tuple(B.PHASE_COL[ph - 1])
            ex, ey = int(fe["x"]) - cx, int(fe["y"]) - cy
            if f < 0.5:
                D.circle(L, col + (int((1 - f / 0.5) ** 1.5 * 150),), (ex, ey), max(2, int(f / 0.5 * 190)), 2)
            f2 = (f - 0.26) % 1.0
            if f2 < 0.4:
                D.circle(L, col + (int((1 - f2 / 0.4) * 90),), (ex, ey), int(f2 / 0.4 * 120) + 4, 1)
        if gz:                                                  # 감시 시야 부채꼴
            sx, sy = int(gz["x"]) - cx, int(gz["y"]) - cy
            ratio = max(0.0, gz["exp"]) / gz["need"]
            if gz["flash"] > 0:
                c = (255, 70, 60)
            else:
                c = (255, int(240 - 150 * ratio), int(170 - 110 * ratio))
            ln = gz["len"]
            pts = [(sx, sy)] + [(sx + math.cos(gz["a"] + u) * ln, sy + math.sin(gz["a"] + u) * ln)
                                for u in [(-1 + i / 4) * gz["hw"] for i in range(9)]]
            D.polygon(L, c + (int(30 + 55 * ratio + (90 if gz["flash"] > 0 else 0)),), pts)
            D.line(L, c + (170,), pts[0], pts[1], 1)
            D.line(L, c + (170,), pts[0], pts[-1], 1)
            for i in range(4):                                  # 바깥으로 훑는 스캔 호
                rr = (t * 110 + i * 140) % ln
                arc = [(sx + math.cos(gz["a"] + u) * rr, sy + math.sin(gz["a"] + u) * rr)
                       for u in [(-1 + j / 4) * gz["hw"] for j in range(9)]]
                D.lines(L, c + (int(90 * (1 - rr / ln)),), False, arc, 1)
        surf.blit(L, (0, 0))
        if gz and gz["exp"] > 0:                                # 노출 게이지 (플레이어 머리 위)
            px, py = int(g["x"]) - cx, int(g["y"]) - cy
            r = gz["exp"] / gz["need"]
            cc = (255, int(235 - 160 * r), int(120 - 80 * r))
            D.circle(surf, (24, 20, 36), (px, py - 4), 12, 1)
            D.arc(surf, cc, pygame.Rect(px - 12, py - 16, 24, 24), math.pi / 2, math.pi / 2 + TAU * r, 2)
    v = g.get("vig")
    if v and v[0] > 0:                                          # 페이즈 전환 비네팅
        sf = _vig(W, H, tuple(v[1]))
        sf.set_alpha(int(255 * min(1.0, v[0])))
        surf.blit(sf, (0, 0))


def apply(R):
    """v9_roster.install() 보다 먼저 호출한다."""
    global _R
    _R = R

    # --- 패턴 풀에 추가
    fin = R.FINAL_POOL
    yes = lambda g, e: True  # noqa: E731
    nogaze = lambda g, e: g.get("gaze") is None  # noqa: E731
    fin[1].append(("rhythm", fb_rhythm, 2, yes))
    fin[2] += [("rhythm", fb_rhythm, 2, yes), ("gaze", fb_gaze, 3, nogaze)]
    fin[3] += [("rhythm", fb_rhythm, 2, yes), ("echo", fb_echo, 3, yes), ("gaze", fb_gaze, 1, nogaze)]
    fin[4] += [("rhythm", fb_rhythm, 3, yes), ("echo", fb_echo, 2, yes)]
    for ph in (2, 3):
        R.BULK[ph].append(("stomp", b_stomp, 2, yes))
    for ph, pool in R.BULK.items():                             # 철벽 돌진 -> 균열 장판 버전
        for i, (n, fn, w, c) in enumerate(pool):
            if n == "charge":
                pool[i] = (n, wrap_charge(fn), w, c)

    # --- 정비관: 열 충격
    old_fx = R.apply_fx

    def apply_fx(g, fx):
        G = R.G
        try:
            if fx == "freeze" and g.get("burn", 0) > 0:
                g["burn"] = 0.0
                G.ftext(g, "소화!", g["x"], g["y"] - 26, (190, 235, 255))
                G.spark(g, g["x"], g["y"], (210, 240, 255), 8)
            elif fx == "burn" and g.get("freeze", 0) > 0:
                g["freeze"] = 0.0
                G.ftext(g, "열 충격!", g["x"], g["y"] - 26, (255, 200, 120))
                G.spark(g, g["x"], g["y"], (255, 220, 160), 10)
                if g["iv"] <= 0:
                    G.hurt(g, 1)
        except Exception:
            G.v9_log("pat-shock")
        old_fx(g, fx)
    R.apply_fx = apply_fx

    # --- 히트 스톱 + 4페이즈 이완기 보너스
    old_hb = R.hit_boss

    def hit_boss(g, e, b, dmg):
        res = old_hb(g, e, b, dmg)
        if res and HITSTOP > 0 and g.get("hs_cd", 0) <= 0:
            g["hs"], g["hs_cd"] = HITSTOP, HITSTOP_GAP
            g["shake"] = max(g.get("shake", 0), 0.1)
        return res
    R.hit_boss = hit_boss
    old_fh = R.final_hit

    def final_hit(g, e, b, dmg):
        relaxed = False
        if e["kind"] == "final" and e["phase"] == 4 and e["inv"] <= 0:
            f = (e["an"] * RATE[3]) % 1.0
            if 0.4 < f < 0.95:                                  # 박동 사이 이완기
                dmg, relaxed = dmg * RELAX_MULT, True
        res = old_fh(g, e, b, dmg)
        if res and relaxed:
            R.G.ftext(g, "이완!", e["x"], e["y"] - 40, (255, 120, 110))
            R.G.spark(g, e["x"], e["y"], (255, 200, 180), 10)
        return res
    R.final_hit = final_hit

    # --- 페이즈 전환: 슬로모션 + 비네팅 (+ 시선 정리)
    old_emp, old_efp = R.enter_mid_phase, R.enter_final_phase

    def enter_mid(g, e, p):
        old_emp(g, e, p)
        g["slow"], g["vig"], g["gaze"] = SLOWMO, [1.0, R.MID_COL[min(3, p - 1)]], None

    def enter_final(g, e, p):
        old_efp(g, e, p)
        g["slow"], g["vig"], g["gaze"] = SLOWMO, [1.0, tuple(R.B.PHASE_COL[p - 1])], None
    R.enter_mid_phase, R.enter_final_phase = enter_mid, enter_final

    # --- 그리기 후킹 (install 이 호출하는 wrap 함수를 확장)
    old_dw = R.draw_hz_wrap

    def draw_hz_wrap(old):
        inner = old_dw(old)

        def f(surf, g, cx, cy):
            inner(surf, g, cx, cy)
            try:
                _draw_extra(surf, g, cx, cy)
            except Exception:
                R.G.v9_log("pat-draw")
        return f
    R.draw_hz_wrap = draw_hz_wrap

    # --- install 뒤에 update / load_zone / sched 를 감싼다
    old_install = R.install

    def install(g_mod, cfg, boss_mod):
        old_install(g_mod, cfg, boss_mod)
        G, B = g_mod, boss_mod
        old_upd, old_load, old_sched = G.update, G.load_zone, B.sched

        def update(g, inp, dt):
            if g.get("hs_cd", 0) > 0:
                g["hs_cd"] -= dt
            if g.get("hs", 0) > 0:                              # 히트 스톱: 화면은 그대로, 시간만 멈춘다
                g["hs"] -= dt
                return None
            v = g.get("vig")
            if v:
                v[0] -= dt * 0.8
                if v[0] <= 0:
                    g["vig"] = None
            if g.get("slow", 0) > 0:                            # 슬로모션
                g["slow"] -= dt
                dt *= 0.4
            gz = g.get("gaze")
            if gz and gz["own"]["hp"] <= 0:
                g["gaze"] = None
            return old_upd(g, inp, dt)

        def load_zone(g, zid, tx, ty):
            old_load(g, zid, tx, ty)
            g["gaze"] = g["vig"] = None
            g["slow"] = g["hs"] = g["hs_cd"] = 0

        def sched(g, e, dt, pool, rest_fn, extra=None):
            had = bool(e["cos"])
            if extra is None:
                old_sched(g, e, dt, pool, rest_fn)
            else:
                old_sched(g, e, dt, pool, rest_fn, extra)
            if (not had and e["cos"] and e.get("kind") in ("mid", "final") and e["last"] in CUT
                    and not g.get("ptitle") and g["t"] - g.get("cut_t", -99.0) > 6.5):
                g["ptitle"] = [CUT[e["last"]], 1.6, "PATTERN"]  # 패턴 이름 컷인
                g["cut_t"] = g["t"]
        G.update, G.load_zone, B.sched = update, load_zone, sched
    R.install = install