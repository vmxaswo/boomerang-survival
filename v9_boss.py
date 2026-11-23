"""v9 보스 모듈
 - 위험 구역(원형 장판·직사각 띠·회전 레이저·중력장) 공통 시스템
 - 패턴 스케줄러(코루틴 스크립트)와 최종 보스 전용 보스방(boss_f)을 만든다
 - 참고: 이 파일의 중간보스 3기(오큘러스·가이아·노바)와 최종 보스 AI는 v8 시절 버전이다.
   지금 게임에 나오는 보스(벌크스틸·알케미스트·오버히트·빅 브라더 Ω)는 v9_roster.py 가 그 위에 덮어쓴다.
수치는 전부 config.py 에서 바꾼다."""
import math
import random

import pygame

D = pygame.draw
G = C = None
DANGER, HOT = (255, 86, 70), (255, 214, 150)
FINAL_NAME, FINAL_SUB = "관리 기계의 핵 (CORE-0)", "문명의 마지막 수호자"
PYLON_TILES = ((8, 6), (26, 6), (8, 17), (26, 17))
PHASE_COL = ((90, 200, 230), (255, 200, 90), (255, 100, 80), (255, 250, 230))
PHASE_NAME = {2: "방어 시스템 가동", 3: "폭주 개시", 4: "최종 폭주"}


# ---------------------------------------------------------------- 작은 도구들
def tm(x):
    return x * C.DIFFICULTY["telegraph"]


def bs(x):
    return x * C.DIFFICULTY["bullet_speed"]


def cdm(x):
    return x * C.DIFFICULTY["cooldown"]


def angto(g, e):
    return math.atan2(g["y"] - e["y"], g["x"] - e["x"])


def bounds(g):
    return G.T, G.T, g["wt"] * G.T - G.T, 23 * G.T


def fire(g, src, ang, sp, kind=0, life=4.0):
    x, y = (src["x"], src["y"]) if isinstance(src, dict) else src
    G.shoot(g, x, y, ang, bs(sp), kind, life)


def ring_gap(g, src, n, sp, gap, gw, kind=0, life=4.5):
    """한 군데가 비어 있는 탄막 고리"""
    for i in range(n):
        a = i * 6.283 / n
        if abs((a - gap + math.pi) % 6.283 - math.pi) < gw:
            continue
        fire(g, src, a, sp, kind, life)


def foes_alive(g, kind, own=None):
    return [o for o in g["en"] if o["kind"] == kind and o["hp"] > 0 and (own is None or o.get("own") is own)]


# ---------------------------------------------------------------- 위험 구역
def add_hz(g, kind, warn, act, **kw):
    w = tm(warn)
    h = dict(kind=kind, warn=w, tot=max(w, 0.01), act=act, dmg=True, own=None, spin=0.0, tick=0.0)
    h.update(kw)
    g["hz"].append(h)
    return h


def update_hz(g, dt):
    px, py = g["x"], g["y"]
    for h in g["hz"][:]:
        o = h["own"]
        if o is not None and h["kind"] == "beam" and o["hp"] > 0:
            h["x"], h["y"] = o["x"], o["y"]
        if h["warn"] > 0:
            h["warn"] -= dt
            continue
        h["act"] -= dt
        k, hit = h["kind"], False
        if k == "circle":
            hit = G.dist(px, py, h["x"], h["y"]) < h["r"]
        elif k == "rect":
            hit = h["x0"] <= px <= h["x1"] and h["y0"] <= py <= h["y1"]
        elif k == "beam":
            h["a"] += h["spin"] * dt
            hit = G.seg_dist(px, py, h["x"], h["y"], h["x"] + math.cos(h["a"]) * h["len"],
                             h["y"] + math.sin(h["a"]) * h["len"]) < h["w"] / 2 + 2
        elif k == "well":
            d = G.dist(px, py, h["x"], h["y"])
            if 7 < d < h["r"]:
                G.move(g, (h["x"] - px) / d * h["pull"] * dt, (h["y"] - py) / d * h["pull"] * dt, g["solid"])
            hit = d < 8
        if h["dmg"] and hit and g["iv"] <= 0 and g["mode"] == "play":
            G.hurt(g, C.DIFFICULTY["hazard_damage"])
        if h["act"] <= 0:
            g["hz"].remove(h)


def draw_hz(surf, g, cx, cy):
    t = g["t"]
    for h in g["hz"]:
        warn, k = h["warn"] > 0, h["kind"]
        f = 1 - max(0.0, h["warn"]) / h["tot"]
        blink = int(t * 16) % 2
        if k == "circle":
            x, y, r = int(h["x"]) - cx, int(h["y"]) - cy, int(h["r"])
            if warn:
                D.circle(surf, DANGER, (x, y), r, 1)
                D.circle(surf, (255, 160, 120), (x, y), max(1, int(r * f)), 1)
            else:
                D.circle(surf, DANGER, (x, y), r)
                D.circle(surf, HOT, (x, y), max(1, r - 4))
        elif k == "rect":
            rc = pygame.Rect(int(h["x0"]) - cx, int(h["y0"]) - cy, int(h["x1"] - h["x0"]), int(h["y1"] - h["y0"]))
            if warn:
                v = pygame.Surface(rc.size, pygame.SRCALPHA)
                v.fill((255, 80, 70, int(30 + 90 * f)))
                surf.blit(v, rc.topleft)
                D.rect(surf, DANGER, rc, 1)
            else:
                D.rect(surf, DANGER, rc)
                D.rect(surf, HOT, rc.inflate(-6, -6))
        elif k in ("beam",):
            x, y, a = int(h["x"]) - cx, int(h["y"]) - cy, h["a"]
            ex, ey = x + math.cos(a) * h["len"], y + math.sin(a) * h["len"]
            if warn:
                if blink or f > 0.7:
                    D.line(surf, DANGER, (x, y), (ex, ey), 1)
                D.circle(surf, DANGER, (x, y), 3 + int(4 * f), 1)
            else:
                D.line(surf, DANGER, (x, y), (ex, ey), int(h["w"]))
                D.line(surf, HOT, (x, y), (ex, ey), max(1, int(h["w"]) // 2))
                D.circle(surf, HOT, (x, y), int(h["w"]))
        elif k == "well":
            x, y, r = int(h["x"]) - cx, int(h["y"]) - cy, int(h["r"])
            D.circle(surf, (150, 100, 230), (x, y), r, 1)
            for i in range(8):
                a = t * (2.5 if not warn else 0.8) + i * 0.785
                rr = r - ((t * 30 + i * 9) % r)
                surf.fill((210, 190, 255), (int(x + math.cos(a) * rr), int(y + math.sin(a) * rr), 2, 2))
            D.circle(surf, (40, 20, 80), (x, y), 8 if not warn else 3)
            D.circle(surf, (190, 150, 255), (x, y), 8 if not warn else 3, 1)


# ---------------------------------------------------------------- 패턴 스케줄러 (코루틴)
def ensure(e):
    if "cos" not in e:
        e.update(cos=[], rest=1.4, last="")


def pick(g, e, pool):
    ok = [p for p in pool if p[3](g, e) and p[0] != e["last"]] or [p for p in pool if p[3](g, e)] or pool
    n, fn, w, _ = random.choices(ok, [p[2] for p in ok])[0]
    e["last"] = n
    return n, fn


def sched(g, e, dt, pool, rest_fn, extra=None):
    busy = bool(e["cos"])
    for c in e["cos"][:]:
        c[1] -= dt
        while c[1] <= 0:
            try:
                c[1] += next(c[0])
            except StopIteration:
                e["cos"].remove(c)
                break
    if busy and not e["cos"]:
        e["rest"] = rest_fn()
    if not e["cos"]:
        e["rest"] -= dt
        if e["rest"] <= 0:
            n, fn = pick(g, e, pool)
            e["cos"].append([fn(g, e), 0.0])
            if extra:
                for fn2 in extra(g, e, n):
                    e["cos"].append([fn2(g, e), 0.0])


def reset_cos(g, e, rest=1.2):
    e["cos"], e["rest"] = [], rest
    g["hz"] = [h for h in g["hz"] if h["own"] is not e and h["kind"] != "well"]
    e["st"] = "idle"


def mid_phase_check(g, e):
    ensure(e)
    if e.get("_ph") != e["ph2"]:
        e["_ph"] = e["ph2"]
        g["hz"] = []
        reset_cos(g, e, 1.4)


# ---------------------------------------------------------------- 오큘러스 (관측자): 저격·분신·교차 레이저
def op_snipe(g, e):
    ph2 = e["ph2"]
    aim, n = tm(0.65 if ph2 else 0.9), 5 if ph2 else 3
    e["st"], e["stt"] = "aim", aim
    t = 0.0
    while t < aim - 0.3:
        e["lz"] = angto(g, e)
        t += 0.05
        yield 0.05
    e["lz"] = angto(g, e)
    yield 0.3
    e["st"] = "fire"
    for _ in range(n):
        fire(g, e, e["lz"], 320, 1, 1.5)
        G.play("shoot")
        yield 0.085
    e["st"] = "idle"


def op_prism(g, e):
    a = angto(g, e)
    px, py = -math.sin(a), math.cos(a)
    off = (-34, 0, 34) if not e["ph2"] else (-52, -26, 0, 26, 52)
    e["st"], e["stt"], e["lz"] = "aim", tm(1.1), a
    for o in off:
        add_hz(g, "beam", 1.1, 0.0, x=e["x"] + px * o, y=e["y"] + py * o, a=a, len=560, w=2, dmg=False)
    yield tm(1.1)
    e["st"] = "fire"
    for _ in range(3):
        for o in off:
            fire(g, (e["x"] + px * o, e["y"] + py * o), a, 300, 1, 1.9)
        G.play("shoot")
        yield 0.13
    e["st"] = "idle"


def op_cross(g, e):
    x0, y0, x1, y1 = bounds(g)
    for i in range(4 if e["ph2"] else 3):
        x, y = g["x"], g["y"]
        w = 1.0 - 0.1 * i
        add_hz(g, "rect", w, 0.5, x0=x0, x1=x1, y0=y - 14, y1=y + 14)
        add_hz(g, "rect", w, 0.5, x0=x - 14, x1=x + 14, y0=y0, y1=y1)
        if e["ph2"]:
            for a in (0.785, 2.356):
                add_hz(g, "beam", w, 0.5, x=x, y=y, a=a, len=700, w=14)
        G.play("gate")
        yield tm(w) + 0.45


def op_clone(g, e):
    e["st"], e["stt"] = "clone", tm(0.8)
    G.play("portal")
    yield tm(0.8)
    for _ in range(3 if e["ph2"] else 2):
        x, y = G.free_spot(g, e["hx"], e["hy"], 25, 85)
        G.spark(g, x, y, (180, 140, 255), 8)
        g["en"].append(G.mk_illu(e, x, y))
    e["st"] = "idle"
    yield 1.0


def op_barrage(g, e):
    for _ in range(3):
        G.blink(g, e)
        e["st"], e["lz"], e["stt"] = "aim", angto(g, e), tm(0.5)
        yield tm(0.5)
        a = angto(g, e)
        for o in (-0.28, 0, 0.28):
            fire(g, e, a + o, 270, 1, 1.7)
        G.play("shoot")
        e["st"] = "idle"
        yield 0.3


def op_fan(g, e):
    a = angto(g, e)
    for i in range(13):
        fire(g, e, a + (i - 6) * 0.13, 130 + 9 * abs(i - 6), 0, 3.8)
    G.play("shoot")
    yield 0.7
    yield from op_snipe(g, e)


OCULUS_POOL = [("snipe", op_snipe, 4, lambda g, e: True), ("prism", op_prism, 3, lambda g, e: True),
               ("cross", op_cross, 3, lambda g, e: True),
               ("clone", op_clone, 2, lambda g, e: not foes_alive(g, "illu", e)),
               ("fan", op_fan, 2, lambda g, e: True), ("barrage", op_barrage, 3, lambda g, e: e["ph2"])]


def new_oculus_ai(g, e, dt, d, ux, uy):
    mid_phase_check(g, e)
    e["stt"] = max(0.0, e["stt"] - dt)
    if e["st"] == "idle":
        if d < 60:
            vx, vy, sp = -ux, -uy, 48
        elif d > 115:
            vx, vy, sp = ux, uy, 34
        else:
            vx, vy, sp = -uy * e["sg"], ux * e["sg"], 30
        G.move(e, vx * sp * dt, vy * sp * dt, g["solid"])
    sched(g, e, dt, OCULUS_POOL, lambda: cdm((0.8 if e["ph2"] else 1.3) * random.uniform(0.8, 1.2)))
    return e["st"] == "idle"


# ---------------------------------------------------------------- 가이아 (덩굴 수호자): 씨앗·채찍·뿌리·꽃
def gp_seeds(g, e):
    n = 3 - len(foes_alive(g, "seed", e))
    e["st"], e["stt"] = "seed", 1.0
    for _ in range(max(0, n)):
        x, y = G.free_spot(g, e["x"], e["y"], 40, 90, 5)
        G.spark(g, x, y, (150, 230, 120), 8)
        g["en"].append(G.mk_seed(e, x, y))
    if e["sc"] <= 0:
        e["sc"] = 4
    G.play("gate")
    yield 1.0
    e["st"] = "idle"


def gp_whip(g, e):
    ph2 = e["ph2"]
    dur, arms, sp = (4.6, 3, 3.5) if ph2 else (4.0, 2, 2.5)
    e["st"], e["wd"], e["wa"], t, flipped = "whip", random.choice((-1, 1)), angto(g, e), 0.0, False
    G.play("gate")
    while t < dur:
        e["wa"] += e["wd"] * sp * 0.03
        e["wl"] = min(66.0, t * 115)
        if t > dur * 0.5 and not flipped:
            e["wd"], flipped = -e["wd"], True
        for i in range(arms):
            a = e["wa"] + i * 6.283 / arms
            tip = (e["x"] + math.cos(a) * e["wl"], e["y"] + math.sin(a) * e["wl"])
            if g["iv"] <= 0 and G.seg_dist(g["x"], g["y"], e["x"], e["y"], tip[0], tip[1]) < 6:
                G.hurt(g, C.DIFFICULTY["hazard_damage"])
            if ph2 and int(t / 0.55) != int((t - 0.03) / 0.55) and t > 0.6:
                fire(g, tip, a, 95, 2, 3.0)
        t += 0.03
        yield 0.03
    e["st"], e["wl"] = "idle", 0.0


def gp_roots(g, e):
    n = 9 if e["ph2"] else 6
    for i in range(n):
        x, y = g["x"], g["y"]
        add_hz(g, "circle", 0.85, 0.4, x=x, y=y, r=21)
        if e["ph2"] and i % 3 == 2:
            for k in range(5):
                a = k * 1.2566
                add_hz(g, "circle", 0.85, 0.4, x=x + math.cos(a) * 46, y=y + math.sin(a) * 46, r=16)
        G.play("switch")
        yield 0.3
    yield 1.0


def gp_rain(g, e):
    a = angto(g, e)
    for i in range(17):
        fire(g, e, a + (i - 8) * 0.1, 95 + random.uniform(0, 55), 2, 4.0)
        if i % 4 == 0:
            G.play("shoot")
        yield 0.05
    yield 0.6


def gp_bloom(g, e):
    for r in range(4 if e["ph2"] else 3):
        ring_gap(g, e, 20, 80 + r * 12, angto(g, e) + random.uniform(-1.2, 1.2), 0.36, 2)
        G.play("shoot")
        yield 0.8


def gp_lanes(g, e):
    x0, y0, x1, y1 = bounds(g)
    ys = random.sample(range(int(y0) + 30, int(y1) - 30, 44), 4)
    for y in ys:
        add_hz(g, "rect", 1.2, 0.6, x0=x0, x1=x1, y0=y - 14, y1=y + 14)
    G.play("gate")
    yield tm(1.2) + 0.9
    for y in random.sample(range(int(x0) + 30, int(x1) - 30, 52), 5):
        add_hz(g, "rect", 1.0, 0.6, x0=y - 14, x1=y + 14, y0=y0, y1=y1)
    yield tm(1.0) + 0.9


GAIA_POOL = [("seeds", gp_seeds, 2, lambda g, e: len(foes_alive(g, "seed", e)) < 2),
             ("whip", gp_whip, 3, lambda g, e: True), ("roots", gp_roots, 3, lambda g, e: True),
             ("rain", gp_rain, 2, lambda g, e: True), ("bloom", gp_bloom, 2, lambda g, e: True),
             ("lanes", gp_lanes, 2, lambda g, e: e["ph2"])]


def new_gaia_ai(g, e, dt, d, ux, uy):
    mid_phase_check(g, e)
    seeds = foes_alive(g, "seed", e)
    if seeds and e["sc"] < 4:                                  # 씨앗이 살아 있으면 보호막이 차오른다
        e["rg"] += dt
        if e["rg"] >= 2.2:
            e["rg"], e["sc"] = 0.0, e["sc"] + 1
            G.play("switch")
    if e["st"] == "idle" and d > 50:
        G.move(e, ux * 12 * dt, uy * 12 * dt, g["solid"])
    sched(g, e, dt, GAIA_POOL, lambda: cdm((0.9 if e["ph2"] else 1.4) * random.uniform(0.8, 1.2)))
    return False


# ---------------------------------------------------------------- 노바 (중력기계): 유성·중력장·별 폭발·특이점
def meteors(g, e, n, gap):
    for i in range(n):
        ox, oy = (0, 0) if i % 3 == 0 else (random.uniform(-52, 52), random.uniform(-52, 52))
        w = tm(0.9)
        g["met"].append([g["x"] + ox, g["y"] + oy, w, w, 20])
        yield gap


def np_meteors(g, e):
    e["st"] = "meteor"
    yield from meteors(g, e, 20 if e["ph2"] else 13, 0.21 if e["ph2"] else 0.3)
    e["st"] = "idle"
    yield 0.8


def np_pull(g, e, push=False):
    tot = 2.0 if push else 2.7
    e["st"], e["tot"], e["stt"] = ("push" if push else "pull"), tot, tot
    G.play("boss")
    yield tm(0.5)
    t = 0.0
    while t < tot - 0.5:
        d = G.dist(g["x"], g["y"], e["x"], e["y"])
        if 8 < d < 190:
            s = (-1 if push else 1) * (95 if push else 66) * 0.03
            G.move(g, (e["x"] - g["x"]) / d * s, (e["y"] - g["y"]) / d * s, g["solid"])
        t += 0.03
        yield 0.03
    if not push:
        G.ring(g, e["x"], e["y"], 14, bs(78), random.random() * 6.283)
    e["st"] = "idle"


def np_push(g, e):
    yield from np_pull(g, e, True)


def np_star(g, e):
    for r in range(5 if e["ph2"] else 3):
        a0, n = random.random() * 6.283, 18
        for i in range(n):
            fire(g, e, a0 + i * 6.283 / n, 70 + r * 20, 0, 5.0)
        G.play("shoot")
        yield 0.5


def np_wells(g, e):
    for _ in range(3 if e["ph2"] else 2):
        x, y = G.free_spot(g, g["x"], g["y"], 40, 120, 5)
        add_hz(g, "well", 0.9, 5.0, x=x, y=y, r=50, pull=52)
    yield tm(0.9) + 5.2


def np_singularity(g, e):
    for i in range(3 if e["ph2"] else 2):
        add_hz(g, "circle", 1.7, 0.5, x=g["x"], y=g["y"], r=60 + 6 * i)
        G.play("boss")
        yield tm(1.7) + 0.8
        G.ring(g, g["x"], g["y"], 10, bs(75), random.random())


def np_sweep(g, e):
    n, spin = (3, 1.1) if e["ph2"] else (2, 0.8)
    base, dr = random.random() * 6.283, random.choice((-1, 1))
    for k in range(n):
        add_hz(g, "beam", 1.1, 3.2, x=e["x"], y=e["y"], a=base + k * 6.283 / n, len=640, w=9, spin=spin * dr, own=e)
    G.play("gate")
    yield tm(1.1) + 3.4


NOVA_POOL = [("meteors", np_meteors, 3, lambda g, e: True), ("pull", np_pull, 2, lambda g, e: True),
             ("push", np_push, 2, lambda g, e: True), ("star", np_star, 3, lambda g, e: True),
             ("wells", np_wells, 2, lambda g, e: not any(h["kind"] == "well" for h in g["hz"])),
             ("sing", np_singularity, 2, lambda g, e: e["ph2"]), ("sweep", np_sweep, 2, lambda g, e: e["ph2"])]


def nova_extra(g, e, name):
    """2페이즈의 노바는 중력 계열 패턴 도중 유성을 함께 떨어뜨린다"""
    if e["ph2"] and name in ("pull", "wells", "sweep") and random.random() < 0.6:
        return [np_meteors]
    return []


def new_nova_ai(g, e, dt, d, ux, uy):
    mid_phase_check(g, e)
    e["stt"] = max(0.0, e["stt"] - dt)
    if e["st"] == "idle" and d > 70:
        G.move(e, ux * 14 * dt, uy * 14 * dt, g["solid"])
    sched(g, e, dt, NOVA_POOL, lambda: cdm((0.9 if e["ph2"] else 1.3) * random.uniform(0.8, 1.2)), nova_extra)
    return False


# ---------------------------------------------------------------- 최종 보스: 관리 기계의 핵
def mk_final(x, y):
    hp = C.FINAL_BOSS["hp"]
    return dict(kind="final", x=x, y=y, hx=None, hy=y, hp=hp, mhp=hp, fl=0, kb=0, kx=0, ky=0, ag=True, hb=10, r=22,
                an=0.0, al=0, mv=False, st="idle", stt=0.0, phase=1, inv=0.0, stun=0.0, opened=False, cos=[],
                rest=2.0, last="", lk=0.0, ph2=False, id=3, tp=0.0)


def mk_pylon(own, x, y):
    hp = C.FINAL_BOSS["pylon_hp"]
    return dict(kind="pylon", own=own, x=x, y=y, hx=None, hy=y, hp=hp, mhp=hp, fl=0, kb=0, kx=0, ky=0, ag=True, hb=5,
                r=9, an=random.random() * 9, al=0, mv=False, st="idle", stt=0.0, acd=random.uniform(1.2, 2.0), nodrop=True)


def shielded(g, e):
    return e["phase"] == 2 and bool(foes_alive(g, "pylon", e))


def fp_spiral(g, e):
    ph = e["phase"]
    arms, a, dr = (2, 3, 3, 4)[ph - 1], random.random() * 6.283, random.choice((-1, 1))
    for i in range(int(3.4 / 0.08)):
        for k in range(arms):
            fire(g, e, a + k * 6.283 / arms, 90 + 7 * ph, 0, 5.0)
            if ph >= 3:
                fire(g, e, -a * 0.8 + k * 6.283 / arms, 80 + 6 * ph, 0, 5.0)
        a += dr * (0.31 + 0.02 * ph)
        if i % 4 == 0:
            G.play("shoot")
        yield 0.08


def fp_beams(g, e):
    ph = e["phase"]
    n, spin = (2, 3, 4, 5)[ph - 1], (0.75, 0.9, 1.15, 1.35)[ph - 1] * random.choice((-1, 1))
    base = random.random() * 6.283
    for k in range(n):
        add_hz(g, "beam", 1.1, 3.0, x=e["x"], y=e["y"], a=base + k * 6.283 / n, len=640, w=9, spin=spin, own=e)
    G.play("gate")
    yield tm(1.1) + 3.2


def fp_ring(g, e):
    ph = e["phase"]
    for r in range(3 + ph // 2):
        ring_gap(g, e, 22 + 2 * ph, 96 + 8 * r + 6 * ph, angto(g, e) + random.uniform(-0.9, 0.9), 0.3 + 0.04 * (4 - ph))
        G.play("shoot")
        yield 0.85 - 0.08 * ph


def fp_grid(g, e):
    ph = e["phase"]
    x0, y0, x1, y1 = bounds(g)
    for _ in range(2 if ph < 3 else 3):
        if random.random() < 0.5:
            for y in random.sample(range(int(y0) + 30, int(y1) - 30, 44), 3 + ph // 2):
                add_hz(g, "rect", 1.15 - 0.05 * ph, 0.55, x0=x0, x1=x1, y0=y - 13, y1=y + 13)
        else:
            for x in random.sample(range(int(x0) + 30, int(x1) - 30, 52), 3 + ph // 2):
                add_hz(g, "rect", 1.15 - 0.05 * ph, 0.55, x0=x - 13, x1=x + 13, y0=y0, y1=y1)
        G.play("gate")
        yield tm(1.15 - 0.05 * ph) + 0.7


def fp_meteors(g, e):
    yield from meteors(g, e, 12 + 3 * e["phase"], 0.26 - 0.02 * e["phase"])
    yield 0.8


def fp_cross(g, e):
    x0, y0, x1, y1 = bounds(g)
    for i in range(2 + e["phase"] // 3):
        x, y = g["x"], g["y"]
        add_hz(g, "rect", 1.0 - 0.1 * i, 0.5, x0=x0, x1=x1, y0=y - 14, y1=y + 14)
        add_hz(g, "rect", 1.0 - 0.1 * i, 0.5, x0=x - 14, x1=x + 14, y0=y0, y1=y1)
        G.play("gate")
        yield tm(1.0 - 0.1 * i) + 0.45


def fp_summon(g, e):
    G.play("portal")
    yield tm(0.6)
    for _ in range(2 if e["phase"] < 4 else 3):
        x, y = G.free_spot(g, e["x"], e["y"], 50, 130, 6)
        b = G.mk_foe("bomber", x, y, True)
        b["nodrop"] = True
        g["en"].append(b)
        G.spark(g, x, y, (255, 170, 80), 8)
    yield 1.2


def fp_teleport(g, e):
    G.spark(g, e["x"], e["y"], (200, 180, 255), 14)
    G.play("portal")
    yield 0.3
    e["x"], e["y"] = random.choice(((17, 11), (11, 8), (23, 8), (11, 14), (23, 14)))
    e["x"], e["y"] = e["x"] * G.T + 8, e["y"] * G.T + 8
    G.spark(g, e["x"], e["y"], (200, 180, 255), 14)
    G.ring(g, e["x"], e["y"], 16, bs(85), random.random())
    yield 0.6


def _p(ph):
    return lambda g, e: e["phase"] >= ph


FINAL_POOL = {1: [("spiral", fp_spiral, 3, lambda g, e: True), ("beams", fp_beams, 2, lambda g, e: True),
                  ("ring", fp_ring, 2, lambda g, e: True), ("cross", fp_cross, 2, lambda g, e: True)],
              2: [("ring", fp_ring, 3, lambda g, e: True), ("grid", fp_grid, 3, lambda g, e: True),
                  ("cross", fp_cross, 2, lambda g, e: True), ("spiral", fp_spiral, 1, lambda g, e: True)],
              3: [("spiral", fp_spiral, 2, lambda g, e: True), ("beams", fp_beams, 3, lambda g, e: True),
                  ("meteors", fp_meteors, 3, lambda g, e: True), ("grid", fp_grid, 2, lambda g, e: True),
                  ("summon", fp_summon, 2, lambda g, e: len(foes_alive(g, "bomber")) < 2),
                  ("ring", fp_ring, 2, lambda g, e: True), ("tele", fp_teleport, 1, lambda g, e: True)]}
FINAL_POOL[4] = FINAL_POOL[3] + [("cross", fp_cross, 2, lambda g, e: True)]


def final_extra(g, e, name):
    """4페이즈: 패턴 두 개를 동시에 굴린다"""
    if e["phase"] < 4:
        return []
    pair = dict(spiral=fp_meteors, beams=fp_ring, grid=fp_summon, meteors=fp_spiral, ring=fp_beams, cross=fp_meteors)
    return [pair[name]] if name in pair and random.random() < 0.8 else []


def enter_phase(g, e, p):
    e["phase"], e["inv"], e["st"] = p, C.FINAL_BOSS["transition_sec"], "idle"
    reset_cos(g, e, 1.0)
    g["hz"], g["shots"], g["met"] = [], [], []
    g["rings"].append([e["x"], e["y"], 0.0, 170, PHASE_COL[p - 1]])
    G.spark(g, e["x"], e["y"], PHASE_COL[p - 1], 30)
    g["shake"] = 0.8
    G.play("boss")
    G.toast(g, f"{PHASE_NAME[p]}!", 3.0)
    if p == 2:
        for tx, ty in PYLON_TILES[:max(1, min(4, C.FINAL_BOSS["pylon_count"]))]:
            g["en"].append(mk_pylon(e, tx * G.T + 8, ty * G.T + 8))
    if p >= 3:
        g["en"] = [o for o in g["en"] if o["kind"] != "pylon"]


def final_ai(g, e, dt):
    if not (g["lock"] and g["intro"] <= 0):
        return False
    ensure(e)
    e["lk"] = angto(g, e)
    th, fr = C.FINAL_BOSS["phases"], e["hp"] / e["mhp"]
    if e["phase"] < 4 and fr <= th[e["phase"] - 1]:
        enter_phase(g, e, e["phase"] + 1)
    e["inv"] = max(0.0, e["inv"] - dt)
    if e["inv"] > 0:
        return False
    if e["phase"] == 2 and not e["opened"] and not foes_alive(g, "pylon", e):
        e["opened"], e["stun"] = True, C.FINAL_BOSS["stun_sec"]
        reset_cos(g, e, 0.5)
        g["rings"].append([e["x"], e["y"], 0.0, 120, (120, 232, 232)])
        G.toast(g, "방어 시스템이 정지했다! 핵을 공격하라!", 3.0)
        G.play("up")
        g["shake"] = 0.5
    if e["stun"] > 0:
        e["stun"] -= dt
        e["st"] = "stun"
        return False
    e["st"] = "idle"
    ph = e["phase"]
    sched(g, e, dt, FINAL_POOL[ph], lambda: cdm((1.6, 1.3, 1.0, 0.55)[ph - 1] * random.uniform(0.85, 1.15)), final_extra)
    return False


def pylon_ai(g, e, dt):
    o = e["own"]
    if o["hp"] <= 0:
        e["hp"] = 0
        return False
    e["acd"] -= dt
    if e["acd"] <= 0 and g["lock"] and o["inv"] <= 0:
        e["acd"] = cdm(random.uniform(1.7, 2.5))
        a = math.atan2(g["y"] - e["y"], g["x"] - e["x"])
        for off in ((-0.2, 0, 0.2) if o["phase"] >= 3 else (0,)):
            fire(g, e, a + off, 125, 3, 3.5)
        G.play("shoot")
    return False


def final_hit(g, e, b, dmg):
    if e["kind"] == "pylon":
        e["hp"] -= dmg
        e["fl"] = 0.12
        G.spark(g, e["x"], e["y"], (120, 232, 232))
        G.play("hit")
        G.ftext(g, f"-{dmg}", e["x"], e["y"] - 14, (255, 240, 150))
        return True
    if e["inv"] > 0 or not (g["lock"] and g["intro"] <= 0):
        G.spark(g, e["x"], e["y"] - 8, (255, 255, 255), 6)
        G.play("clang")
        return False
    if shielded(g, e):
        G.spark(g, e["x"], e["y"] - 10, (120, 232, 232), 8)
        G.ftext(g, "방어막!", e["x"], e["y"] - 26, (150, 240, 240))
        G.play("clang")
        return False
    e["hp"] -= dmg
    e["fl"] = 0.12
    G.ftext(g, f"-{dmg}" if dmg < 4 else f"-{dmg}!", e["x"] + random.randint(-8, 8), e["y"] - 26,
            (255, 240, 150) if dmg < 3 else (255, 170, 80) if dmg < 5 else (255, 100, 90))
    G.spark(g, e["x"], e["y"], (255, 240, 150), 8)
    G.play("hit")
    return True


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def draw_final(surf, e, cx, cy, t, g):
    ph = e["phase"]
    x, y = int(e["x"]) - cx, int(e["y"]) - cy + round(math.sin(e["an"] * 2) * 2)
    col = PHASE_COL[ph - 1]
    surf.blit(pygame.transform.scale(G.SHADOW, (46, 11)), (x - 23, y + 20))
    spin = e["an"] * (0.7 if ph < 3 else 1.6)
    for i in range(16):                                        # 바깥 톱니 고리
        a = spin + i * 0.3927
        D.circle(surf, (170, 180, 195), (x + int(math.cos(a) * 29), y + int(math.sin(a) * 29)), 3)
    for i in range(8):                                         # 반대로 도는 안쪽 고리
        a = -spin * 1.4 + i * 0.785
        D.circle(surf, lerp(col, (255, 255, 255), 0.3), (x + int(math.cos(a) * 21), y + int(math.sin(a) * 21)), 2)
    D.circle(surf, (50, 56, 86), (x, y), 19)
    D.circle(surf, (110, 116, 140), (x, y), 17)
    D.circle(surf, col, (x, y), 13, 2)
    fl = e["fl"] > 0 or (e["inv"] > 0 and int(e["an"] * 20) % 2)
    D.circle(surf, (255, 255, 255) if fl else lerp(col, (255, 255, 255), 0.45), (x, y), 9)
    D.circle(surf, (24, 20, 36), (x + int(math.cos(e["lk"]) * 3), y + int(math.sin(e["lk"]) * 3)), 4)
    surf.fill((255, 255, 255), (x - 2, y - 4, 2, 2))
    if e["stun"] > 0:                                          # 정지: 불꽃이 튄다
        for _ in range(3):
            a = random.random() * 6.283
            D.line(surf, (255, 240, 150), (x, y), (x + math.cos(a) * 26, y + math.sin(a) * 26), 1)
    if ph == 2 and not e["opened"] and foes_alive(g, "pylon", e):       # 방어막 돔
        v = pygame.Surface((76, 76), pygame.SRCALPHA)
        D.circle(v, (120, 232, 232, 60), (38, 38), 36)
        D.circle(v, (190, 250, 250, 200), (38, 38), 36, 1)
        surf.blit(v, (x - 38, y - 38))
    if ph == 4:                                                # 폭주: 전기 호
        for _ in range(2):
            a = random.random() * 6.283
            D.line(surf, (255, 255, 255), (x + math.cos(a) * 14, y + math.sin(a) * 14),
                   (x + math.cos(a + random.uniform(-0.6, 0.6)) * 34, y + math.sin(a) * 34), 1)
    if e["al"] > 0:
        surf.fill((255, 230, 80), (x - 1, y - 40, 2, 5))


def draw_pylon(surf, e, cx, cy, t, g):
    x, y = int(e["x"]) - cx, int(e["y"]) - cy
    o = e["own"]
    if o["hp"] > 0 and o["phase"] == 2:                        # 핵과 이어지는 에너지 선
        a = (int(t * 12) % 2) * 60
        D.line(surf, (60, 140 + a, 170), (x, y - 8), (int(o["x"]) - cx, int(o["y"]) - cy), 2)
        D.line(surf, (190, 250, 250), (x, y - 8), (int(o["x"]) - cx, int(o["y"]) - cy), 1)
    surf.blit(G.SHADOW, (x - 6, y + 4))
    D.rect(surf, (96, 100, 124), (x - 6, y + 2, 12, 6))
    D.rect(surf, (140, 146, 170), (x - 6, y + 2, 12, 2))
    c = (255, 255, 255) if e["fl"] > 0 else (120, 232, 232)
    bob = round(math.sin(e["an"] * 3) * 1.5)
    D.polygon(surf, c, [(x, y - 16 + bob), (x + 6, y - 7 + bob), (x, y + 2 + bob), (x - 6, y - 7 + bob)])
    D.polygon(surf, (24, 20, 36), [(x, y - 16 + bob), (x + 6, y - 7 + bob), (x, y + 2 + bob), (x - 6, y - 7 + bob)], 1)
    surf.fill((255, 255, 255), (x - 1, y - 12 + bob, 1, 3))
    D.rect(surf, (24, 20, 36), (x - 8, y - 22, 16, 3))
    D.rect(surf, (235, 70, 70), (x - 7, y - 21, 14 * e["hp"] // e["mhp"], 1))


def build_final_arena(zid):
    sp = G.ZONES[zid]
    wt, ht = sp["size"]
    rng = random.Random(901)
    solid = set()
    G.ring_(solid, 0, 0, wt - 1, ht - 1)
    ter = [[4] * wt for _ in range(ht)]
    for x in range(wt):
        solid.add((x, 23))
    for y in range(24, ht - 1):
        for x in range(1, wt - 1):
            if not (15 <= x <= 19 and y <= 27):
                solid.add((x, y))
    for x in range(15, 20):
        for y in range(24, 28):
            ter[y][x] = 3
    for x in (16, 17, 18):
        solid.discard((x, 23))
        ter[23][x] = 3
    deco = []
    for bx, by in ((4, 3), (29, 3), (4, 20), (29, 20)):
        solid.add((bx, by))
        deco.append(("brazier", bx, by))
    for px_, py_ in ((9, 8), (23, 8), (9, 15), (23, 15)):      # 엄폐용 2x2 기둥
        for i in (0, 1):
            for j in (0, 1):
                solid.add((px_ + i, py_ + j))
    for tx, ty in PYLON_TILES:
        deco.append(("socket", tx, ty))
    fn = G.fractal(rng, 6, 3, wt, ht)
    shade = [[fn(x, y) for x in range(wt)] for y in range(ht)]
    return dict(solid=solid, nodes=[], ntile=set(), houses={}, pz=[], en=[mk_final(17 * G.T + 8, 11 * G.T + 8)], ter=ter,
                water=set(), shade=shade, rs=[], npcs=[], spec=sp, tgate=set(), core=None, vil=None, portals=[], exits=[],
                wt=wt, ht=ht, zreg=sp["reg"], deco=deco, arena="final")


def draw_final_floor(surf, g, cx, cy):
    """최종 보스방 바닥: 핵을 중심으로 한 회로 문양. 페이즈가 오를수록 붉게 달아오른다"""
    e = next((o for o in g["en"] if o["kind"] == "final"), None)
    ph = e["phase"] if e else 1
    col = PHASE_COL[ph - 1]
    bx, by = 17 * G.T + 8 - cx, 11 * G.T + 8 - cy
    p = 0.5 + 0.5 * math.sin(g["t"] * (2 + ph))
    c2 = lerp((50, 56, 90), col, 0.35 + 0.35 * p)
    for r in (34, 70, 110, 150):
        D.circle(surf, c2, (bx, by), r, 1)
    for i in range(24):
        a = i * 0.2618 + g["t"] * 0.05
        D.line(surf, c2, (bx + math.cos(a) * 34, by + math.sin(a) * 34), (bx + math.cos(a) * 150, by + math.sin(a) * 150), 1)
    for tx, ty in PYLON_TILES:                                 # 기둥 자리에서 중심으로 이어지는 도선
        px, py = tx * G.T + 8 - cx, ty * G.T + 8 - cy
        D.line(surf, c2, (px, py), (bx, by), 1)
        D.circle(surf, c2, (px, py), 12, 1)
        D.circle(surf, c2, (px, py), 7, 1)


# ---------------------------------------------------------------- 설치
def install(g_mod, cfg):
    global G, C
    G, C = g_mod, cfg
    FN, ENM = G.FOE_NAME, C.MID_BOSS
    FN["final"], FN["pylon"] = "관리 기계의 핵", "방어 기둥"
    for k in ("final", "pylon"):
        G.AGGRO[k] = 9999
    G.REGIONS.append(dict(name="관리 기계의 심장부", floor=(52, 58, 92), floor2=(44, 50, 82), wall=(30, 32, 60), leaf=(80, 100, 150)))
    G.ZONES["boss_f"] = dict(name="관리 기계의 심장부", reg=len(G.REGIONS) - 1, size=(34, 30), arena="final", boss=3,
                              origin="temple", npcs=[], roads=[], exits=[], river=None, portals=[], n={})

    old_mid, old_arena, old_foe, old_hit, old_de = G.mk_mid, G.build_arena, G.foe_ai, G.hit_foe, G.draw_enemy
    old_oc, old_ga, old_no = G.oculus_ai, G.gaia_ai, G.nova_ai

    def mk_mid(x, y, i):
        e = old_mid(x, y, i)
        e["hp"] = e["mhp"] = ENM["hp"][i]
        return e

    def build_arena(zid):
        return build_final_arena(zid) if G.ZONES[zid].get("arena") == "final" else old_arena(zid)

    def foe_ai(g, e, dt, d, ux, uy):
        if e["kind"] == "final":
            e["ag"] = True
            return final_ai(g, e, dt)
        if e["kind"] == "pylon":
            e["ag"] = True
            return pylon_ai(g, e, dt)
        return old_foe(g, e, dt, d, ux, uy)

    def hit_foe(g, e, b, dmg):
        return final_hit(g, e, b, dmg) if e["kind"] in ("final", "pylon") else old_hit(g, e, b, dmg)

    def draw_enemy(surf, e, cx, cy, t, g):
        if e["kind"] == "final":
            return draw_final(surf, e, cx, cy, t, g)
        if e["kind"] == "pylon":
            return draw_pylon(surf, e, cx, cy, t, g)
        return old_de(surf, e, cx, cy, t, g)

    def guarded(new, old):
        def f(*a):
            try:
                return new(*a)
            except Exception:
                G.v9_log("boss-ai")
                return old(*a)
        return f
    G.mk_mid, G.build_arena, G.foe_ai, G.hit_foe, G.draw_enemy = mk_mid, build_arena, foe_ai, hit_foe, draw_enemy
    G.oculus_ai, G.gaia_ai, G.nova_ai = (guarded(new_oculus_ai, old_oc), guarded(new_gaia_ai, old_ga),
                                         guarded(new_nova_ai, old_no))