"""v9 보스 로스터 모듈 (v9_roster.py)
 - 중간보스 3기 : 수문장 벌크스틸 / 공장장 알케미스트 / 수석 정비관 오버히트   (서쪽·동쪽·북쪽 보스방 순서)
 - 최종 보스    : 도시의 심장, 빅 브라더 - Ω
v9_boss.py 의 위험 구역·패턴 스케줄러를 그대로 쓰고, 그 위에 새 보스 AI·그리기·상태이상(화상/빙결/조작 반전)을 얹는다.
수치는 config.py 에서 바꾼다."""
import math
import random

import pygame

D = pygame.draw
SC = pygame.SRCALPHA
G = C = B = None
TAU = 6.283185
DANGER = (255, 86, 70)
NAMES = ("수문장 벌크스틸 (Bulksteel-01)", "공장장 알케미스트 (Tech-Alchemist Mk.II)", "수석 정비관 오버히트 (Overheat-9)")
SUBS = ("도시 외곽 성벽을 지키던 방어 특화 거대 기신", "자동화 생산 공정의 메인 유닛", "도시의 고온 냉각·에너지 제어 기계")
PNAMES = (("녹슨 철벽", "요새화 거포 모드", "제한 해제"),
          ("컨베이어 조종", "용융 제련", "자원 재활용", "공장 자폭 시퀀스"),
          ("과열 모드", "극저온 열교환", "열폭주 과부하", "초고온 플라즈마 폼"))
FINAL_NAME, FINAL_SUB = "도시의 심장, 빅 브라더 (Big Brother - Ω)", "공간을 왜곡하는 메인 코어"
FINAL_PN = ("외곽 시스템", "본체 노출 · 공간 왜곡", "시스템 해킹 · 정신 오염", "멸망 프로토콜")
MID_COL = ((235, 70, 70), (255, 150, 60), (255, 220, 110), (255, 250, 230))
YES = lambda g, e: True  # noqa: E731
_FNT = {}


# ---------------------------------------------------------------- 작은 도구들
def ang_diff(a, b):
    return (a - b + math.pi) % TAU - math.pi


def turn_to(e, ang, rate, dt):
    d = ang_diff(ang, e["fa"])
    e["fa"] += max(-rate * dt, min(rate * dt, d))


def lunge(g, e, ang, speed, dur):
    t = 0.0
    while t < dur:
        G.move(e, math.cos(ang) * speed * 0.03, math.sin(ang) * speed * 0.03, g["solid"])
        t += 0.03
        yield 0.03


def center(g):
    x0, y0, x1, y1 = B.bounds(g)
    return (x0 + x1) / 2, (y0 + y1) / 2


def hz(g, kind, warn, act, **kw):
    return B.add_hz(g, kind, warn, act, **kw)


def trail(g, ax, ay, bx, by, col, n=6):
    for i in range(n + 1):
        G.spark(g, ax + (bx - ax) * i / n, ay + (by - ay) * i / n, col, 2)


def drift_home(g, e, dt, hx, hy, sp):
    d = G.dist(e["x"], e["y"], hx, hy)
    if d > 4:
        G.move(e, (hx - e["x"]) / d * sp * dt, (hy - e["y"]) / d * sp * dt, g["solid"])


def alive_ex(g, sub, own=None):
    return [o for o in g["en"] if o["kind"] == "ex" and o["sub"] == sub and o["hp"] > 0 and (own is None or o["own"] is own)]


def mk_ex(sub, x, y, own, hp, r, **kw):
    e = dict(kind="ex", sub=sub, own=own, x=x, y=y, hx=None, hy=y, hp=hp, mhp=hp, fl=0, kb=0, kx=0, ky=0, ag=True, hb=4,
             r=r, an=random.random() * 9, al=0, mv=False, st="idle", stt=0.0, acd=random.uniform(1.2, 2.0), nodrop=True,
             vx=0.0, vy=0.0, lx=0.0, ly=0.0, life=99.0, notarget=False, var="")
    e.update(kw)
    return e


def seg_cross(ax, ay, bx, by, cx, cy, dx, dy):
    def o(px, py, qx, qy, rx, ry):
        return (qx - px) * (ry - py) - (qy - py) * (rx - px)
    return o(ax, ay, bx, by, cx, cy) * o(ax, ay, bx, by, dx, dy) < 0 and o(cx, cy, dx, dy, ax, ay) * o(cx, cy, dx, dy, bx, by) < 0


def covered(g, x, y, px, py):
    """(x,y)에서 플레이어까지 벽이나 방패가 가로막고 있으면 True"""
    if not G.los(g, x, y, px, py):
        return True
    s = g.get("b_shield")
    return bool(s and seg_cross(x, y, px, py, s["x1"], s["y1"], s["x2"], s["y2"]))


def font14():
    if 14 not in _FNT:
        _FNT[14] = G.load_font(14)
    return _FNT[14]


_GL = {}


def glow(r, col, a):
    k = (r, col, a)
    if k not in _GL:
        sf = pygame.Surface((r * 2, r * 2), SC)
        for i in range(r, 0, -2):
            D.circle(sf, col + (int(a * (1 - i / r) ** 1.6),), (r, r), i)
        _GL[k] = sf
    return _GL[k]


def vis_alpha(g, e):
    ap = e.get("appear", 0.0)
    return 1.0 if ap <= 0 else max(0.0, 1.0 - ap / 0.3)


def blink_to(g, e, x, y, col=(255, 170, 80)):
    # 순간이동: 떠난 자리에 잔상이 남아 서서히 사라지고, 도착 지점에서는 서서히 나타난다
    if e.get("kind") == "mid":                      # 최종보스(id=3)는 중간보스용 그리기 함수가 없어 잔상을 남기지 않는다
        g.setdefault("ai", []).append([dict(e), 0.4, 0.4])
    trail(g, e["x"], e["y"], x, y, col)
    g["rings"].append([x, y, 0.0, 26, col])
    e["x"], e["y"], e["appear"] = x, y, 0.3


def fade_text(screen, font, s, cx, y, col, alpha, u):
    img, sh = font.render(s, True, col), font.render(s, True, G.INK)
    w, h = img.get_size()
    t = pygame.Surface((w + 3 * u, h + 3 * u), SC)
    t.blit(sh, (2 * u, 2 * u))
    t.blit(sh, (0, u))
    t.blit(img, (u, u))
    t.set_alpha(int(255 * max(0.0, min(1.0, alpha))))
    screen.blit(t, (cx - t.get_width() // 2, y))


def heat_col(e):
    ph = e["phase"]
    if ph == 3 and e["stun"] > 0:
        return (130, 190, 240)
    return (255, 120, 70) if ph in (1, 3) else (130, 200, 255) if ph == 2 else (255, 255, 235)


# ---------------------------------------------------------------- 피격 처리
def hit_ex(g, e, b, dmg):
    if e["sub"] == "gear":                                   # 톱니바퀴는 파괴할 수 없다
        e["fl"] = 0.05
        G.spark(g, e["x"], e["y"], (210, 225, 255), 4)
        G.play("clang")
        return False
    e["hp"] -= dmg
    e["fl"] = 0.1
    G.spark(g, e["x"], e["y"], (255, 240, 150), 5)
    G.play("hit")
    G.ftext(g, f"-{round(dmg, 1):g}", e["x"], e["y"] - 14, (255, 240, 150))
    return True


def hit_boss(g, e, b, dmg):
    if e["inv"] > 0 or not (g["lock"] and g["intro"] <= 0):
        G.spark(g, e["x"], e["y"] - 8, (255, 255, 255), 6)
        G.play("clang")
        return False
    mult, note = 1.0, ""
    if e["kind"] == "mid":
        i, ph = e["id"], e["phase"]
        if i == 0 and ph == 1 and e["exp"] <= 0 and b["dx"] * math.cos(e["fa"]) + b["dy"] * math.sin(e["fa"]) < -0.25:
            mult, note = 0.2, "정면 장갑!"                    # 정면 타격은 80% 경감
        elif i == 2 and ph == 3:
            mult, note = (1.5, "약점 노출!") if e["stun"] > 0 else (0.5, "")
    real = dmg * mult
    e["hp"] -= real
    e["fl"] = 0.12
    G.ftext(g, f"-{round(real, 1):g} {note}".strip(), e["x"] + random.randint(-8, 8), e["y"] - 30,
            (255, 240, 150) if mult >= 1 else (190, 200, 225))
    G.spark(g, e["x"], e["y"], (255, 240, 150), 8)
    G.play("hit" if mult >= 1 else "clang")
    return True


def final_hit(g, e, b, dmg):
    if e["kind"] == "pylon":
        e["hp"] -= dmg
        e["fl"] = 0.12
        G.spark(g, e["x"], e["y"], (120, 232, 232))
        G.play("hit")
        G.ftext(g, f"-{dmg}", e["x"], e["y"] - 14, (255, 240, 150))
        return True
    if e["phase"] == 1 and e["inv"] <= 0:
        G.spark(g, e["x"], e["y"] - 10, (120, 232, 232), 8)
        G.ftext(g, "무적 결계!", e["x"], e["y"] - 26, (150, 240, 240))
        G.play("clang")
        return False
    return hit_boss(g, e, b, dmg)


# ================================================================= 1. 수문장 벌크스틸
COMBO = ((0.55, 0.18), (0.6, 0.18), (0.75, 0.22))


def b1_combo(g, e):
    """파일벙커 찌르기 -> 회전 방패 치기 -> 바닥 찍기"""
    for i, (wa, ac) in enumerate(COMBO):
        a = B.angto(g, e)
        e["fa"], e["st"] = a, "wind"
        yield from lunge(g, e, a, 80, 0.22)
        x, y = e["x"], e["y"]
        if i == 0:
            hz(g, "beam", wa, ac, x=x, y=y, a=a, len=58, w=12)
        elif i == 1:
            hz(g, "circle", wa, ac, x=x, y=y, r=38)
        else:
            fx, fy = x + math.cos(a) * 34, y + math.sin(a) * 34
            hz(g, "circle", wa, ac, x=fx, y=fy, r=44)
        yield B.tm(wa) + ac + 0.1
        if i == 2:
            G.ring(g, fx, fy, 10, B.bs(80), random.random() * TAU)
    e["st"] = "idle"


def b1_charge(g, e):
    """철벽 돌진: 맵 끝까지 달려 벽에 부딪히면 지진파 (벽 뒤에 숨어야 한다)"""
    a = B.angto(g, e)
    e["fa"], e["st"] = a, "wind"
    hz(g, "beam", 0.9, 0.0, x=e["x"], y=e["y"], a=a, len=600, w=14, dmg=False)
    G.play("boss")
    yield B.tm(0.9)
    e["st"] = "dash"
    still, t = 0, 0.0
    while t < 2.4:
        x0, y0 = e["x"], e["y"]
        G.move(e, math.cos(a) * 240 * 0.03, math.sin(a) * 240 * 0.03, g["solid"])
        still = still + 1 if G.dist(x0, y0, e["x"], e["y"]) < 1.0 else 0
        if still >= 2:
            break
        t += 0.03
        yield 0.03
    G.play("boom")
    g["shake"] = 0.5
    hz(g, "knock", 0.35, 2.8, x=e["x"], y=e["y"], r=8, spd=210, maxr=520, hit=False)
    e["st"], e["exp"] = "stun", 1.8                              # 충돌 직후에는 정면도 통한다
    yield 1.8
    e["st"] = "idle"


def plant_shield(g, e):
    a = B.angto(g, e)
    e["fa"] = a
    cx, cy = e["x"] + math.cos(a) * 30, e["y"] + math.sin(a) * 30
    px, py = -math.sin(a) * 30, math.cos(a) * 30
    g["b_shield"] = dict(x1=cx - px, y1=cy - py, x2=cx + px, y2=cy + py, a=a)


def b2_spray(g, e):
    """360도 플라즈마 난사: 방패 뒤가 안전지대"""
    e["st"] = "turret"
    a0, dr = random.random() * TAU, random.choice((-1, 1))
    for i in range(44):
        a = a0 + dr * i * 0.33
        e["fa"] = a
        for k in range(3):
            B.fire(g, e, a + k * TAU / 3, 90, 3, 3.4)
        if i % 5 == 0:
            G.play("shoot")
        yield 0.07
    e["st"] = "idle"


def b2_volley(g, e):
    e["st"] = "turret"
    for _ in range(5):
        a = B.angto(g, e)
        e["fa"] = a
        for k in range(-2, 3):
            B.fire(g, e, a + k * 0.16, 125, 3, 3.2)
        G.play("shoot")
        yield 0.6
    e["st"] = "idle"


def b2_mortar(g, e):
    """방패 뒤에 웅크린 플레이어를 끌어내는 박격포"""
    for i in range(6):
        hz(g, "circle", 0.9, 0.3, x=g["x"] + random.uniform(-12, 12), y=g["y"] + random.uniform(-12, 12), r=24)
        G.play("switch")
        yield 0.5
    yield 0.8


def b3_spike(g, e):
    """부스터 파일 스파이크: 플레이어 뒤로 점멸해 내리꽂는다"""
    for _ in range(2):
        bx, by = g["x"] - g["dx"] * 30, g["y"] - g["dy"] * 30
        if G.blocked(bx, by, g["solid"], 6):
            bx, by = G.free_spot(g, g["x"], g["y"], 20, 40, 6)
        hz(g, "circle", 0.55, 0.1, x=bx, y=by, r=11, dmg=False)
        e["st"] = "wind"
        yield B.tm(0.5)
        blink_to(g, e, bx, by, (255, 160, 90))
        G.play("portal")
        a = B.angto(g, e)
        e["fa"] = a
        hz(g, "beam", 0.4, 0.15, x=bx, y=by, a=a, len=58, w=13)
        yield B.tm(0.4) + 0.35
    e["st"] = "idle"


def b3_ghosts(g, e):
    """열화 잔상 3기가 차례로 교차 돌진한 뒤, 마지막에 본체가 돌진한다"""
    for _ in range(3):
        a = random.random() * TAU
        hz(g, "dash", 0.7, 0.28, x=g["x"] - math.cos(a) * 220, y=g["y"] - math.sin(a) * 220, a=a, len=440, w=18, act0=0.28,
           px=0.0, py=0.0)
        G.play("portal")
        yield B.tm(0.45)
    yield B.tm(0.5)
    a = B.angto(g, e)
    e["fa"], e["st"] = a, "wind"
    hz(g, "beam", 0.9, 0.0, x=e["x"], y=e["y"], a=a, len=420, w=16, dmg=False)
    G.play("boss")
    yield B.tm(0.9)
    e["st"] = "dash"
    yield from lunge(g, e, a, 300, 0.55)
    e["st"] = "idle"
    yield 0.6


BULK = {1: [("combo", b1_combo, 3, YES), ("charge", b1_charge, 2, YES)],
        2: [("spray", b2_spray, 3, YES), ("volley", b2_volley, 2, YES), ("mortar", b2_mortar, 3, YES)],
        3: [("spike", b3_spike, 3, YES), ("ghosts", b3_ghosts, 3, YES), ("combo", b1_combo, 1, YES)]}


def bulk_ai(g, e, dt, d, ux, uy):
    ph = e["phase"]
    if not e["cos"] and e["st"] == "idle":
        turn_to(e, math.atan2(uy, ux), (1.5, 4.0, 5.0)[ph - 1], dt)       # 1페이즈: 천천히 돌아서 측면을 노릴 수 있다
        if ph == 1 and d > 44:
            G.move(e, ux * 32 * dt, uy * 32 * dt, g["solid"])
        elif ph == 3:
            vx, vy = (ux, uy) if d > 60 else (-uy * e["sg"], ux * e["sg"])
            G.move(e, vx * 70 * dt, vy * 70 * dt, g["solid"])
    if ph == 2:
        e["swt"] -= dt
        if e["swt"] <= 0:                                                  # 3초마다 바닥 전체 충격파
            e["swt"] = 3.2
            hz(g, "knock", 0.5, 2.8, x=e["x"], y=e["y"], r=8, spd=190, maxr=520, hit=False)
            G.play("boom")
    B.sched(g, e, dt, BULK[ph], lambda: B.cdm((1.2, 0.9, 0.8)[ph - 1] * random.uniform(0.8, 1.2)))
    return e["st"] in ("idle", "dash")


def hook_bulk(g, e, p):
    if p == 2:
        plant_shield(g, e)
        e["swt"] = 2.2
    elif p == 3:
        g["b_shield"] = None
        e["r"] = 14
        G.spark(g, e["x"], e["y"] - 10, (190, 200, 225), 30)
        G.toast(g, "장갑이 분리되었다! 속도가 폭발적으로 오른다", 3.0)


# ================================================================= 2. 공장장 알케미스트
def drones(g, e):
    return [o for o in g["en"] if o["kind"] == "bomber" and o.get("own") is e and o["hp"] > 0]


def press(g, x, y, warn=0.85, s=32):
    hz(g, "rect", warn, 0.3, x0=x - s, x1=x + s, y0=y - s, y1=y + s)


def a_drones(g, e):
    e["st"] = "cast"
    G.play("portal")
    yield B.tm(0.7)
    for _ in range(max(0, 3 - len(drones(g, e)))):
        x, y = G.free_spot(g, e["x"], e["y"], 30, 60, 6)
        d = G.mk_foe("bomber", x, y, True)
        d.update(nodrop=True, own=e, hp=3)
        g["en"].append(d)
        G.spark(g, x, y, (150, 230, 120), 8)
    e["st"] = "idle"
    yield 0.8


def a_belts(g, e):
    x0, y0, x1, y1 = B.bounds(g)
    cy = (y0 + y1) / 2
    belts = [hz(g, "conv", 0.9, 8.0, x0=x0, x1=x1, y0=yy - 26, y1=yy + 26, dx=random.choice((-1, 1)), dy=0, spd=50)
             for yy in (cy - 108, cy, cy + 108)]
    G.play("gate")
    yield B.tm(0.9)
    for _ in range(3):
        yield 2.2
        for b in belts:
            if random.random() < 0.7:
                b["dx"] = -b["dx"]
        G.play("switch")
    yield 1.6


def a_gears(g, e):
    """톱니바퀴 바조카: 벽면 레일에서 튕기는 대형 톱니 4개"""
    x0, y0, x1, y1 = B.bounds(g)
    yield B.tm(0.9)
    for _ in range(4):
        side = random.choice("lrt")
        if side == "l":
            x, y, a = x0 + 10, random.uniform(y0 + 40, y1 - 40), random.uniform(-0.6, 0.6)
        elif side == "r":
            x, y, a = x1 - 10, random.uniform(y0 + 40, y1 - 40), math.pi + random.uniform(-0.6, 0.6)
        else:
            x, y, a = random.uniform(x0 + 40, x1 - 40), y0 + 10, math.pi / 2 + random.uniform(-0.6, 0.6)
        hz(g, "circle", 0.6, 0.0, x=x, y=y, r=12, dmg=False)
        yield B.tm(0.6)
        g["en"].append(mk_ex("gear", x, y, e, 999, 10, notarget=True, vx=math.cos(a) * 105, vy=math.sin(a) * 105, life=6.5))
        G.play("gate")
        yield 0.35


def a_press(g, e):
    for i in range(3 if e["phase"] < 3 else 4):
        press(g, g["x"] + g["dx"] * 26, g["y"] + g["dy"] * 26)
        G.play("gate")
        yield 0.62
    yield 1.0


def a_net(g, e):
    """용융 열화선 그물: 가로 띠 -> 세로 띠가 격자로 바닥을 쓸고 지나간다"""
    x0, y0, x1, y1 = B.bounds(g)
    sp = 75.0 if e["phase"] < 3 else 95.0
    G.play("gate")
    for k in range(4):
        y = y0 + 24 + k * 88
        hz(g, "rect", 1.0, 1.6, x0=x0, x1=x1, y0=y - 7, y1=y + 7, vx=0.0, vy=sp)
    yield B.tm(1.0) + 1.8
    G.play("gate")
    for k in range(5):
        x = x0 + 24 + k * 100
        hz(g, "rect", 1.0, 1.6, x0=x - 7, x1=x + 7, y0=y0, y1=y1, vx=sp, vy=0.0)
    yield B.tm(1.0) + 1.8


def a_slag(g, e):
    """폐기물 투하: 쇳물 덩어리가 지속 화염 지대를 만든다"""
    x0, y0, x1, y1 = B.bounds(g)
    for i in range(7):
        if i % 2 == 0:
            x, y = g["x"] + random.uniform(-26, 26), g["y"] + random.uniform(-26, 26)
        else:
            x, y = random.uniform(x0 + 20, x1 - 20), random.uniform(y0 + 20, y1 - 20)
        hz(g, "circle", 1.0, 5.0, x=x, y=y, r=22)
        G.play("switch")
        yield 0.42
    yield 0.6


def a_golem(g, e):
    cx, cy = center(g)
    hz(g, "circle", 1.3, 0.0, x=cx, y=cy + 30, r=26, dmg=False)
    e["st"] = "cast"
    G.play("boss")
    yield B.tm(1.3)
    hp = 10 + 2 * min(4, e["scrap"])                           # 부서진 드론이 많을수록 튼튼하다
    e["scrap"] = 0
    g["en"].append(mk_ex("golem", cx, cy + 30, e, hp, 13, acd=2.0))
    G.spark(g, cx, cy + 30, (200, 190, 170), 20)
    e["st"] = "idle"
    yield 1.0


def a_magnet(g, e):
    """과전압 자석: 중앙으로 끌어당긴 뒤 프레스 연계"""
    cx, cy = center(g)
    hz(g, "well", 0.9, 5.4, x=cx, y=cy, r=210, pull=85)
    G.play("boss")
    yield B.tm(0.9) + 0.4
    for _ in range(4):
        press(g, g["x"], g["y"], 0.8)
        G.play("gate")
        yield 1.15
    yield 1.0


def a_spiral(g, e):
    a, dr = random.random() * TAU, random.choice((-1, 1))
    for i in range(36):
        for k in range(3):
            B.fire(g, e, a + k * TAU / 3, 95, 0, 4.5)
        a += dr * 0.33
        if i % 4 == 0:
            G.play("shoot")
        yield 0.08


def a_ringgap(g, e):
    for r in range(3):
        B.ring_gap(g, e, 26, 88 + r * 10, B.angto(g, e) + random.uniform(-1.0, 1.0), 0.34, 0)
        G.play("shoot")
        yield 0.8


def a_fan(g, e):
    for _ in range(3):
        a = B.angto(g, e)
        for i in range(-4, 5):
            B.fire(g, e, a + i * 0.12, 125, 0, 4.0)
        G.play("shoot")
        yield 0.7


_P2 = [("press", a_press, 3, YES), ("net", a_net, 3, YES), ("slag", a_slag, 3, YES), ("gears", a_gears, 1, YES)]
ALCH = {1: [("drones", a_drones, 2, lambda g, e: len(drones(g, e)) < 2), ("belts", a_belts, 3,
                                                                         lambda g, e: not any(h["kind"] == "conv" for h in g["hz"])),
            ("gears", a_gears, 2, YES)],
        2: _P2,
        3: _P2 + [("drones", a_drones, 1, lambda g, e: len(drones(g, e)) < 2),
                  ("golem", a_golem, 4, lambda g, e: not alive_ex(g, "golem", e)), ("magnet", a_magnet, 3, YES)],
        4: [("spiral", a_spiral, 3, YES), ("ringgap", a_ringgap, 3, YES), ("fan", a_fan, 2, YES)]}


def alch_extra(g, e, name):
    return [a_gears] if name == "belts" else []


def alch_ai(g, e, dt, d, ux, uy):
    ph = e["phase"]
    cx, cy = center(g)
    x0, y0, x1, y1 = B.bounds(g)
    if ph == 4:
        drift_home(g, e, dt, cx, y0 + 40, 60)                  # 천장에 매달린다
    elif e["st"] == "idle" and not e["cos"]:
        drift_home(g, e, dt, cx, cy - 20 if ph == 1 else y0 + 80, 22)
    n = len(drones(g, e))
    if n < e["_dn"]:
        e["scrap"] += e["_dn"] - n
    e["_dn"] = n
    B.sched(g, e, dt, ALCH[ph], lambda: B.cdm((1.2, 0.9, 0.8, 0.6)[ph - 1] * random.uniform(0.8, 1.2)), alch_extra)
    return False


def hook_alch(g, e, p):
    if p == 4:
        x0, y0, x1, y1 = B.bounds(g)
        g["sq"] = dict(t=0.0, total=30.0, tick=0.0, s=0.0)
        blink_to(g, e, (x0 + x1) / 2, y0 + 40, (150, 255, 170))
        G.toast(g, "양쪽 벽이 조여 온다! 닫히기 전에 쓰러뜨려라", 3.5)


# ================================================================= 3. 수석 정비관 오버히트
def h_sweep(g, e):
    """플라즈마 스윕: 양팔 토치가 회전하며 부채꼴을 쓸어낸다 (화상)"""
    spd = (1.5, 1.5, 1.7, 2.4)[e["phase"] - 1]
    base, dr = B.angto(g, e), random.choice((-1, 1))
    e["st"] = "torch"
    G.play("gate")
    hs = [hz(g, "beam", 0.8, 2.8, x=e["x"], y=e["y"], a=base + k * math.pi, len=128, w=14, spin=spd * dr, own=e, fx="burn")
          for k in range(2)]
    yield B.tm(0.8)
    t = 0.0
    while t < 2.6:
        for h in hs:
            if h["warn"] <= 0:
                B.fire(g, e, h["a"], 115, 0, 1.5)
        t += 0.22
        yield 0.22
    e["st"] = "idle"


def h_thrust(g, e):
    """과열 3연속 찌르기: 점멸 -> 찌르기 -> 화염 궤적"""
    for i in range(3 if e["phase"] < 4 else 4):
        x, y = G.free_spot(g, g["x"], g["y"], 55, 85, 7)
        blink_to(g, e, x, y, (255, 170, 80))
        G.play("portal")
        a = B.angto(g, e)
        e["fa"], e["st"] = a, "wind"
        hz(g, "beam", 0.5, 0.14, x=x, y=y, a=a, len=104, w=13, fx="burn")
        yield B.tm(0.5) + 0.08
        for k in range(8):
            G.move(e, math.cos(a) * 11, math.sin(a) * 11, g["solid"])
            if k % 2 == 1:
                hz(g, "circle", 0.1, 3.0, x=e["x"], y=e["y"], r=10, fx="burn")
            yield 0.015
        yield 0.35
    e["st"] = "idle"


def h_vent(g, e):
    """냉각재 방출: 닿으면 빙결"""
    e["st"] = "vent"
    G.play("boss")
    hz(g, "circle", 0.9, 2.2, x=e["x"], y=e["y"], r=62, fx="freeze")
    for k in range(6):
        a = k * TAU / 6 + random.random()
        hz(g, "circle", 0.9, 2.2, x=e["x"] + math.cos(a) * 100, y=e["y"] + math.sin(a) * 100, r=26, fx="freeze")
    yield B.tm(0.9) + 2.4
    e["st"] = "idle"


def h_shatter(g, e):
    """동결 쇄빙참: 도약해 내리친다 (피해 2)"""
    tx, ty = g["x"], g["y"]
    sx, sy = e["x"], e["y"]
    e["st"] = "leap"
    G.play("portal")
    hz(g, "circle", 1.0, 0.25, x=tx, y=ty, r=42, dmgv=2, fx="freeze")
    yield B.tm(0.5)
    for i in range(1, 11):
        k = i / 10
        e["x"], e["y"] = sx + (tx - sx) * k, sy + (ty - sy) * k
        e["lift"] = math.sin(math.pi * k) * 32
        yield 0.05
    e["lift"] = 0
    G.ring(g, tx, ty, 12, B.bs(90), random.random() * TAU)
    g["shake"] = 0.3
    e["st"] = "idle"
    yield 0.8


def h_tornado(g, e):
    """플라즈마 토네이도: 중심에서 바깥으로 밀어낸다"""
    cx, cy = center(g)
    e["st"] = "tornado"
    for _ in range(10):
        e["x"] += (cx - e["x"]) * 0.3
        e["y"] += (cy - e["y"]) * 0.3
        yield 0.04
    hz(g, "well", 0.9, 5.6, x=e["x"], y=e["y"], r=150, pull=-112)
    for k in range(2):
        hz(g, "beam", 0.9, 5.6, x=e["x"], y=e["y"], a=k * math.pi, len=150, w=11, spin=1.15, fx="burn")
    G.play("boss")
    yield B.tm(0.9)
    for _ in range(4):
        G.ring(g, e["x"], e["y"], 10, B.bs(70), random.random() * TAU)
        yield 1.2
    yield 0.2
    e["st"] = "idle"


def h_frenzy(g, e):
    """무한 점멸 난무: 떠난 자리마다 잔상 폭발"""
    for i in range(9):
        hz(g, "circle", 0.8, 0.25, x=e["x"], y=e["y"], r=34)
        x, y = G.free_spot(g, g["x"], g["y"], 40, 130, 7)
        blink_to(g, e, x, y, (255, 255, 220))
        G.play("portal")
        if i % 3 == 2:
            G.ring(g, x, y, 8, B.bs(90), random.random() * TAU)
        yield 0.42
    yield 0.3


HEAT = {1: [("sweep", h_sweep, 3, YES), ("thrust", h_thrust, 3, YES)],
        2: [("vent", h_vent, 3, YES), ("shatter", h_shatter, 3, lambda g, e: g.get("freeze", 0) > 0 or random.random() < 0.35),
            ("sweep", h_sweep, 2, YES), ("thrust", h_thrust, 2, YES)],
        3: [("tornado", h_tornado, 3, YES), ("sweep", h_sweep, 3, YES), ("thrust", h_thrust, 2, YES),
            ("shatter", h_shatter, 1, lambda g, e: g.get("freeze", 0) > 0)],
        4: [("frenzy", h_frenzy, 4, YES), ("thrust", h_thrust, 2, YES), ("sweep", h_sweep, 1, YES)]}


def heat_ai(g, e, dt, d, ux, uy):
    ph = e["phase"]
    if ph == 3:                                                # 과열 게이지: 100%가 되면 5초 정지 (유일한 폭딜 찬스)
        if e["stun"] > 0:
            e["stun"] -= dt
            e["st"] = "vent"
            if random.random() < 0.5:
                G.spark(g, e["x"] + random.uniform(-10, 10), e["y"] - 20, (210, 230, 250), 1)
            if e["stun"] <= 0:
                e["st"], e["heat"], e["rest"] = "idle", 0.0, 1.2
            return False
        e["heat"] += 100 / 14 * dt
        if e["heat"] >= 100:
            e["stun"], e["cos"], e["st"], e["lift"] = 5.0, [], "vent", 0
            g["hz"] = []
            g["rings"].append([e["x"], e["y"], 0.0, 90, (150, 210, 255)])
            G.toast(g, "과열 배출! 5초간 정지한다 - 지금이 기회!", 3.0)
            G.play("boss")
            return False
    if e["st"] == "idle" and not e["cos"]:
        if d < 60:
            vx, vy = -ux, -uy
        elif d > 110:
            vx, vy = ux, uy
        else:
            vx, vy = -uy * e["sg"], ux * e["sg"]
        sp = 76 if ph == 4 else 38
        G.move(e, vx * sp * dt, vy * sp * dt, g["solid"])
    B.sched(g, e, dt, HEAT[ph], lambda: B.cdm((1.1, 0.9, 0.7, 0.35)[ph - 1] * random.uniform(0.85, 1.15)))
    return e["st"] == "idle"


def hook_heat(g, e, p):
    if p == 2:
        g["floor"] = dict(axis=random.choice("vh"), side=random.randint(0, 1), t=0.0, period=8.0, tick=0.0)
        G.toast(g, "바닥이 화염 구역과 빙결 구역으로 갈라진다", 3.0)
    elif p == 3:
        e["heat"], e["stun"] = 0.0, 0.0
    elif p == 4:
        G.toast(g, "온몸이 빛으로 승화한다!", 3.0)


# ---------------------------------------------------------------- 중간보스 공통 진행
AIS = (bulk_ai, alch_ai, heat_ai)
HOOKS = (hook_bulk, hook_alch, hook_heat)


def enter_mid_phase(g, e, p):
    e["phase"], e["ph2"], e["inv"] = p, p >= 2, 1.4
    e["cos"], e["rest"], e["st"], e["lift"] = [], 1.2, "idle", 0
    g["hz"], g["shots"], g["met"] = [], [], []
    g["b_shield"] = g["floor"] = g["sq"] = None
    g["burn"] = g["freeze"] = 0
    for o in g["en"]:
        if o.get("own") is e and o["kind"] == "ex" and o["sub"] != "golem":
            o["hp"] = 0
        elif o["kind"] == "bomber" and o.get("own") is e:
            o["hp"] = 0
    g["rings"].append([e["x"], e["y"], 0.0, 110, (255, 120, 90)])
    G.spark(g, e["x"], e["y"] - 8, (255, 160, 110), 30)
    g["shake"] = 0.6
    g["pflash"] = [1.0, (255, 255, 255)]
    g["ptitle"] = [PNAMES[e["id"]][p - 1], 2.4, f"PHASE {p}"]
    G.play("boss")
    HOOKS[e["id"]](g, e, p)


def mid_ai(g, e, dt, d, ux, uy):
    try:
        if not e["ag"]:
            e["st"] = "idle"
            return False
        e["lk"] = math.atan2(uy, ux)
        e["exp"] = max(0.0, e["exp"] - dt)
        th = C.MID_BOSS["phases"][e["id"]]
        if e["phase"] <= len(th) and e["hp"] / e["mhp"] <= th[e["phase"] - 1] + 1e-6:
            enter_mid_phase(g, e, e["phase"] + 1)
        if e["inv"] > 0:
            e["inv"] -= dt
            return False
        return AIS[e["id"]](g, e, dt, d, ux, uy)
    except Exception:
        G.v9_log("roster-mid")
        return False


# ---------------------------------------------------------------- 소환체(ex) AI
def gear_ai(g, e, dt, d, ux, uy):
    e["life"] -= dt
    if e["life"] <= 0:
        e["hp"] = 0
        return False
    nx = e["x"] + e["vx"] * dt
    if G.blocked(nx, e["y"], g["solid"], 5):
        e["vx"], nx = -e["vx"], e["x"]
    e["x"] = nx
    ny = e["y"] + e["vy"] * dt
    if G.blocked(e["x"], ny, g["solid"], 5):
        e["vy"], ny = -e["vy"], e["y"]
    e["y"] = ny
    return True


def orb_ai(g, e, dt, d, ux, uy):
    e["life"] -= dt
    if e["life"] <= 0:
        e["hp"] = 0
        return False
    sp = 50.0
    vx, vy = e["vx"] + (ux * sp - e["vx"]) * 0.9 * dt, e["vy"] + (uy * sp - e["vy"]) * 0.9 * dt
    n = math.hypot(vx, vy) or 1
    vx, vy = vx / n * sp, vy / n * sp
    nx = e["x"] + vx * dt
    if G.blocked(nx, e["y"], g["solid"], 4):
        vx, nx = -vx, e["x"]
    ny = e["y"] + vy * dt
    if G.blocked(nx, ny, g["solid"], 4):
        vy, ny = -vy, e["y"]
    e["vx"], e["vy"], e["x"], e["y"] = vx, vy, nx, ny
    return True


def golem_ai(g, e, dt, d, ux, uy):
    if e["st"] == "idle":
        G.move(e, ux * 34 * dt, uy * 34 * dt, g["solid"])
        e["acd"] -= dt
        if d < 80 and e["acd"] <= 0:
            e["st"], e["stt"] = "wind", B.tm(0.7) + 0.45
            hz(g, "circle", 0.7, 0.2, x=e["x"], y=e["y"], r=38)
        return True
    e["stt"] -= dt
    if e["stt"] <= 0:
        e["st"], e["acd"] = "idle", 2.6
    return False


def phantom_ai(g, e, dt, d, ux, uy):
    sp, ds = dict(bulk=(30, 170), alch=(38, 150), heat=(46, 200))[e["var"]]
    if e["st"] == "idle":
        G.move(e, ux * sp * dt, uy * sp * dt, g["solid"])
        e["acd"] -= dt
        if d < 70 and e["acd"] <= 0:
            e["st"], e["stt"], e["lx"], e["ly"] = "wind", 0.55, ux, uy
        return True
    e["stt"] -= dt
    if e["st"] == "wind":
        if e["stt"] <= 0:
            e["st"], e["stt"] = "dash", 0.28
    elif e["st"] == "dash":
        G.move(e, e["lx"] * ds * dt, e["ly"] * ds * dt, g["solid"])
        if e["stt"] <= 0:
            e["st"], e["stt"] = "rest", 0.7
        return True
    elif e["stt"] <= 0:
        e["st"], e["acd"] = "idle", random.uniform(1.6, 2.4)
    return False


EX_AI = dict(gear=gear_ai, orb=orb_ai, golem=golem_ai, phantom=phantom_ai)


def ex_ai(g, e, dt, d, ux, uy):
    o = e.get("own")
    if o is not None and o["hp"] <= 0:
        e["hp"] = 0
        return False
    return EX_AI[e["sub"]](g, e, dt, d, ux, uy)


# ================================================================= 4. 최종 보스: 빅 브라더 - Ω
def fb_grid(g, e):
    """서브 코어끼리 레이저로 이어 아레나를 바둑판처럼 가른다 (코어가 죽으면 선이 줄어든다)"""
    cs = e["cores"]
    al = [o["hp"] > 0 for o in cs]
    P = [(o["x"], o["y"]) for o in cs]

    def line(p, q):
        hz(g, "beam", 1.1, 1.6, x=p[0], y=p[1], a=math.atan2(q[1] - p[1], q[0] - p[0]), len=G.dist(p[0], p[1], q[0], q[1]), w=7)

    def mid(p, q):
        return (p[0] + q[0]) / 2, (p[1] + q[1]) / 2
    for _ in range(2):
        for a, b in ((0, 1), (2, 3), (0, 2), (1, 3)):
            if al[a] and al[b]:
                line(P[a], P[b])
        if all(al):
            line(mid(P[0], P[1]), mid(P[2], P[3]))
            line(mid(P[0], P[2]), mid(P[1], P[3]))
        G.play("gate")
        yield B.tm(1.1) + 1.9


def fb_fan(g, e):
    for _ in range(3):
        a = B.angto(g, e)
        for i in range(-4, 5):
            B.fire(g, e, a + i * 0.12, 120, 0, 3.8)
        G.play("shoot")
        yield 0.7


def fb_bombard(g, e):
    """포메이션 그리드 폭격: 붉은 격자 -> 1초 뒤 광선 폭풍. 칸 가운데가 사각지대"""
    x0, y0, x1, y1 = B.bounds(g)
    cols = [x0 + 30 + 56 * i for i in range(int((x1 - x0 - 60) // 56) + 1)]
    rows = [y0 + 30 + 56 * i for i in range(int((y1 - y0 - 60) // 56) + 1)]
    for wave in range(2):
        off = 28 * wave
        for x in cols:
            hz(g, "rect", 1.0, 0.35, x0=x + off - 9, x1=x + off + 9, y0=y0, y1=y1)
        for y in rows:
            hz(g, "rect", 1.0, 0.35, x0=x0, x1=x1, y0=y + off - 9, y1=y + off + 9)
        G.play("gate")
        yield B.tm(1.0) + 0.85


def fb_gravity(g, e):
    """중력 역전: 벽으로 끌려가며 벽면 가시를 피해야 한다"""
    x0, y0, x1, y1 = B.bounds(g)
    hz(g, "well", 1.0, 6.0, x=e["x"], y=e["y"], r=420, pull=-72)
    G.play("boss")
    yield B.tm(1.0)
    for _ in range(5):
        px, py = g["x"], g["y"]
        wall = min(((px - x0, "l"), (x1 - px, "r"), (py - y0, "t"), (y1 - py, "b")))[1]
        if wall == "l":
            r = dict(x0=x0, x1=x0 + 18, y0=py - 55, y1=py + 55)
        elif wall == "r":
            r = dict(x0=x1 - 18, x1=x1, y0=py - 55, y1=py + 55)
        elif wall == "t":
            r = dict(x0=px - 55, x1=px + 55, y0=y0, y1=y0 + 18)
        else:
            r = dict(x0=px - 55, x1=px + 55, y0=y1 - 18, y1=y1)
        hz(g, "rect", 1.0, 1.2, **r)
        G.play("switch")
        yield 1.05
    yield 0.4


def fb_phantoms(g, e):
    """데이터 잔영: 과거 기계 가디언들의 환영"""
    G.play("portal")
    yield B.tm(0.8)
    have = {o["var"] for o in alive_ex(g, "phantom")}
    for v in ("bulk", "alch", "heat"):
        if v in have:
            continue
        x, y = G.free_spot(g, e["x"], e["y"], 60, 150, 8)
        g["en"].append(mk_ex("phantom", x, y, e, 5, 10, var=v))
        G.spark(g, x, y, (200, 180, 255), 10)
    yield 1.2


def fb_hack(g, e):
    """시스템 해킹: 10초간 이동 조작이 반전된다"""
    g["hack"] = float(C.FINAL_BOSS.get("hack_sec", 10))
    G.toast(g, "시스템 해킹! 이동 조작이 반전된다", 3.0)
    G.play("portal")
    for i in range(5):
        B.ring_gap(g, e, 18, 66 + 4 * i, B.angto(g, e) + random.uniform(-0.8, 0.8), 0.45, 0)
        yield 2.0


def fb_orbs(g, e):
    """차원 균열 구체: 튕기며 느리게 따라오는 구체 10개"""
    G.play("portal")
    yield B.tm(0.6)
    for i in range(10):
        a = i * TAU / 10 + random.random() * 0.3
        g["en"].append(mk_ex("orb", e["x"], e["y"], e, 1, 6, vx=math.cos(a) * 52, vy=math.sin(a) * 52, life=11.0, notarget=True))
        yield 0.1
    yield 1.5


def fb_corebeam(g, e):
    """전방위 코어 빔: 벽(기둥) 뒤에 숨으면 막힌다"""
    e["st"] = "beam"
    G.play("boss")
    base, dr = random.random() * TAU, random.choice((-1, 1))
    for k in range(2):
        hz(g, "beam", 1.4, 6.2, x=e["x"], y=e["y"], a=base + k * math.pi, len=620, w=22, spin=0.7 * dr, own=e, los=True, dmg=False)
    yield B.tm(1.4) + 6.4
    e["st"] = "idle"


FINAL_POOL = {
    1: [("grid", fb_grid, 3, lambda g, e: sum(1 for o in e["cores"] if o["hp"] > 0) >= 2),
        ("ring", lambda g, e: B.fp_ring(g, e), 2, YES), ("fan", fb_fan, 2, YES)],
    2: [("bombard", fb_bombard, 3, YES), ("gravity", fb_gravity, 3, YES),
        ("phantoms", fb_phantoms, 2, lambda g, e: len(alive_ex(g, "phantom")) < 2),
        ("ring", lambda g, e: B.fp_ring(g, e), 1, YES)],
    3: [("hack", fb_hack, 3, lambda g, e: g.get("hack", 0) <= 0), ("orbs", fb_orbs, 2, lambda g, e: len(alive_ex(g, "orb")) < 3),
        ("beam", fb_corebeam, 3, YES), ("spiral", lambda g, e: B.fp_spiral(g, e), 2, YES),
        ("meteors", lambda g, e: B.fp_meteors(g, e), 2, YES)],
    4: [("ring", lambda g, e: B.fp_ring(g, e), 2, YES), ("fan", fb_fan, 2, YES)]}


def enter_final_phase(g, e, p):
    e["phase"], e["inv"], e["st"] = p, C.FINAL_BOSS["transition_sec"], "idle"
    e["cos"], e["rest"] = [], 1.0
    g["hz"], g["shots"], g["met"] = [], [], []
    g["rings"].append([e["x"], e["y"], 0.0, 170, B.PHASE_COL[p - 1]])
    G.spark(g, e["x"], e["y"], B.PHASE_COL[p - 1], 30)
    g["shake"] = 0.8
    G.play("boss")
    g["pflash"] = [1.0, B.PHASE_COL[p - 1]]
    g["ptitle"] = [FINAL_PN[p - 1], 2.4, f"PHASE {p}"]
    for o in g["en"]:
        if o["kind"] == "pylon":
            o["hp"] = 0
    if p == 2:
        e["opened"] = True
        G.toast(g, "본체가 노출되었다! 핵을 공격하라", 3.0)
    elif p == 4:
        cx, cy = center(g)
        blink_to(g, e, 17 * G.T + 8, 11 * G.T + 8, (255, 120, 100))
        e["omega"], e["hp4"], e["lt"], e["boomed"] = float(C.FINAL_BOSS.get("omega_seconds", 30)), e["hp"], 1.0, False
        g["hack"] = 0


def pylon_ai(g, e, dt):
    o = e["own"]
    if o["hp"] <= 0:
        e["hp"] = 0
        return False
    e["acd"] -= dt
    if e["acd"] <= 0 and g["lock"] and o["inv"] <= 0:
        e["acd"] = B.cdm(random.uniform(2.0, 3.0))
        B.fire(g, e, math.atan2(g["y"] - e["y"], g["x"] - e["x"]), 120, 3, 3.5)
        G.play("shoot")
    return False


def final_ai(g, e, dt):
    try:
        return _final_ai(g, e, dt)
    except Exception:
        G.v9_log("roster-final")
        return False


def _final_ai(g, e, dt):
    if not (g["lock"] and g["intro"] <= 0):
        return False
    B.ensure(e)
    e["lk"] = B.angto(g, e)
    e["opened"] = True
    ph = e["phase"]
    if ph == 1:
        if "cores" not in e:                                   # 4대 서브 코어: 파괴할 때마다 본체 체력이 6.25% 깎인다
            e["cores"] = [B.mk_pylon(e, tx * G.T + 8, ty * G.T + 8) for tx, ty in B.PYLON_TILES]
            g["en"].extend(e["cores"])
        dead = sum(1 for o in e["cores"] if o["hp"] <= 0)
        e["hp"] = e["mhp"] * (1 - 0.0625 * dead)
    th = C.FINAL_BOSS["phases"]
    if ph < 4 and e["hp"] / e["mhp"] <= th[ph - 1] + 1e-6:
        enter_final_phase(g, e, ph + 1)
        ph = e["phase"]
    e["inv"] = max(0.0, e["inv"] - dt)
    if e["inv"] > 0:
        return False
    if ph == 4:                                                # 멸망 프로토콜
        e["omega"] -= dt
        e["hp"] = min(e["hp4"], e["hp"] + C.FINAL_BOSS.get("omega_regen", 0.8) * dt)
        e["lt"] -= dt
        if e["lt"] <= 0:
            e["lt"] = 0.36
            x0, y0, x1, y1 = B.bounds(g)
            if random.random() < 0.45:
                x, y = g["x"] + random.uniform(-34, 34), g["y"] + random.uniform(-34, 34)
            else:
                x, y = random.uniform(x0 + 16, x1 - 16), random.uniform(y0 + 16, y1 - 16)
            hz(g, "circle", 0.55, 0.15, x=x, y=y, r=17)
        if e["omega"] <= 0 and not e["boomed"]:
            e["boomed"] = True
            g["rings"].append([e["x"], e["y"], 0.0, 300, (255, 240, 200)])
            g["shake"] = 1.0
            G.toast(g, "코어가 자폭했다...", 3.0)
            G.hurt(g, 999)
            return False
    B.sched(g, e, dt, FINAL_POOL[ph], lambda: B.cdm((1.4, 1.2, 1.1, 1.5)[ph - 1] * random.uniform(0.85, 1.15)))
    return False


# ================================================================= 위험 구역 확장 (update / draw)
def hz_hit(h, px, py):
    k = h["kind"]
    if k == "circle":
        return G.dist(px, py, h["x"], h["y"]) < h["r"]
    if k == "rect":
        return h["x0"] <= px <= h["x1"] and h["y0"] <= py <= h["y1"]
    if k == "beam":
        return G.seg_dist(px, py, h["x"], h["y"], h["x"] + math.cos(h["a"]) * h["len"], h["y"] + math.sin(h["a"]) * h["len"]) < h["w"] / 2 + 2
    return False


def apply_fx(g, fx):
    if fx == "burn":
        g["burn"] = max(g.get("burn", 0), 1.6)
    elif fx == "freeze":
        if g.get("freeze", 0) <= 0:
            G.ftext(g, "빙결!", g["x"], g["y"] - 14, (160, 225, 255))
        g["freeze"] = max(g.get("freeze", 0), 2.6)


def pre_hz(g, dt):
    px, py = g["x"], g["y"]
    for h in g["hz"]:
        h["age"] = h.get("age", 0.0) + dt
        if h["warn"] > 0:
            continue
        k = h["kind"]
        if k == "knock":
            h["r"] += h["spd"] * dt
            d = G.dist(px, py, h["x"], h["y"])
            if not h["hit"] and abs(d - h["r"]) < 9:
                h["hit"] = True
                if g["iv"] <= 0 and not covered(g, h["x"], h["y"], px, py):
                    G.hurt(g, 1)
                    a = math.atan2(py - h["y"], px - h["x"])
                    for _ in range(8):
                        G.move(g, math.cos(a) * 5, math.sin(a) * 5, g["solid"])
        elif k == "conv":
            if h["x0"] <= px <= h["x1"] and h["y0"] <= py <= h["y1"]:
                G.move(g, h["dx"] * h["spd"] * dt, h["dy"] * h["spd"] * dt, g["solid"])
        elif k == "dash":
            p = 1 - max(0.0, h["act"]) / h["act0"]
            h["px"], h["py"] = h["x"] + math.cos(h["a"]) * h["len"] * p, h["y"] + math.sin(h["a"]) * h["len"] * p
            if g["iv"] <= 0 and G.dist(px, py, h["px"], h["py"]) < h["w"] / 2 + 2:
                G.hurt(g, 1)
        else:
            if "vx" in h:
                h["x0"] += h["vx"] * dt
                h["x1"] += h["vx"] * dt
                h["y0"] += h["vy"] * dt
                h["y1"] += h["vy"] * dt
            if h.get("los") and k == "beam":
                if g["iv"] <= 0 and hz_hit(h, px, py) and G.los(g, h["x"], h["y"], px, py):
                    G.hurt(g, C.DIFFICULTY["hazard_damage"])
            elif (h.get("fx") or h.get("dmgv")) and h["dmg"] and hz_hit(h, px, py):
                apply_fx(g, h.get("fx"))
                if h.get("dmgv") and g["iv"] <= 0:
                    G.hurt(g, h["dmgv"])


def floor_rects(g, fl):
    x0, y0, x1, y1 = B.bounds(g)
    if fl["axis"] == "v":
        m = (x0 + x1) / 2
        a, b = (x0, y0, m, y1), (m, y0, x1, y1)
    else:
        m = (y0 + y1) / 2
        a, b = (x0, y0, x1, m), (x0, m, x1, y1)
    return (a, b) if fl["side"] == 0 else (b, a)                # (화염, 빙결)


def post_hz(g, dt):
    play_ = g["mode"] == "play"
    pf = g.get("pflash")
    if pf:
        pf[0] -= dt * 1.7
        if pf[0] <= 0:
            g["pflash"] = None
    pt = g.get("ptitle")
    if pt:
        pt[1] -= dt
        if pt[1] <= 0:
            g["ptitle"] = None
    for k in ("freeze", "hack"):
        if g.get(k, 0) > 0:
            g[k] = max(0.0, g[k] - dt)
    b = g.get("burn", 0)
    if b > 0:                                                  # 화상: 시간이 지나면 한 번 더 아프다
        g["burn"] = max(0.0, b - dt)
        if g["burn"] <= 0 and play_:
            G.ftext(g, "화상!", g["x"], g["y"] - 14, (255, 140, 70))
            G.hurt(g, 1)
    pp = g.get("_pp")
    mx, my = (g["x"] - pp[0], g["y"] - pp[1]) if pp else (0.0, 0.0)
    if abs(mx) + abs(my) > 12:
        mx = my = 0.0
    if g.get("freeze", 0) > 0:                                 # 빙결: 이동 둔화 + 부메랑 재장전 지연
        g["x"] -= mx * 0.45
        g["y"] -= my * 0.45
        if g["cd"] > 0:
            g["cd"] += dt * 0.6
        if g["tcd"] > 0:
            g["tcd"] += dt * 0.6
    fl = g.get("floor")
    ice = False
    if fl:
        fl["t"] += dt
        if fl["t"] >= fl["period"]:
            fl["t"], fl["side"] = 0.0, fl["side"] ^ 1
            G.play("portal")
        fire, icer = floor_rects(g, fl)
        infire = fire[0] <= g["x"] <= fire[2] and fire[1] <= g["y"] <= fire[3]
        ice = not infire
        if infire and play_:
            fl["tick"] += dt
            if fl["tick"] >= 1.3 and g["iv"] <= 0:
                fl["tick"] = 0.0
                G.hurt(g, 1)
        else:
            fl["tick"] = 0.0
    if ice and not g["moving"] and play_:                      # 빙결 구역: 미끄러진다
        m = g.get("_m", (0.0, 0.0))
        G.move(g, m[0], m[1], g["solid"])
        g["_m"] = (m[0] * 0.92, m[1] * 0.92)
    else:
        g["_m"] = (mx, my)
    sq = g.get("sq")
    if sq:                                                     # 알케미스트 4페이즈: 좁혀 오는 벽
        if not any(o["kind"] == "mid" and o["hp"] > 0 for o in g["en"]):
            g["sq"] = None
        else:
            x0, y0, x1, y1 = B.bounds(g)
            sq["t"] += dt
            sq["s"] = min(1.0, sq["t"] / sq["total"]) * (x1 - x0 - 44) / 2
            L, R = x0 + sq["s"], x1 - sq["s"]
            g["x"] = min(max(g["x"], L + 6), R - 6)
            cxm = (L + R) / 2
            for _ in range(40):
                if not G.blocked(g["x"], g["y"], g["solid"], 4):
                    break
                g["x"] += 1 if g["x"] < cxm else -1
            if R - L < 80 and play_:
                sq["tick"] += dt
                if sq["tick"] >= 0.7:
                    sq["tick"] = 0.0
                    G.hurt(g, 1)
    sh = g.get("b_shield")
    if sh:                                                     # 방패가 탄막을 막는다
        for s in g["shots"][:]:
            if G.seg_dist(s[0], s[1], sh["x1"], sh["y1"], sh["x2"], sh["y2"]) < 4:
                g["shots"].remove(s)
                G.spark(g, s[0], s[1], (210, 225, 255), 3)
    g["_pp"] = (g["x"], g["y"])


def update_hz_wrap(old):
    def f(g, dt):
        try:
            pre_hz(g, dt)
        except Exception:
            G.v9_log("roster-pre")
        old(g, dt)
        try:
            post_hz(g, dt)
        except Exception:
            G.v9_log("roster-post")
    return f


# ---------------------------------------------------------------- 그리기: 위험 구역 확장
def draw_floor(surf, g, cx, cy):
    fl = g["floor"]
    fire, icer = floor_rects(g, fl)
    w_ = max(0.0, (fl["t"] - (fl["period"] - 1.6)) / 1.6)
    k_ = int(70 * w_ * abs(math.sin(g["t"] * 9)))
    for r, col in ((fire, (255, 90, 40, 70 + k_)), (icer, (120, 190, 255, 60 + k_))):
        rc = pygame.Rect(int(r[0]) - cx, int(r[1]) - cy, int(r[2] - r[0]), int(r[3] - r[1]))
        v = pygame.Surface(rc.size, SC)
        v.fill(col)
        surf.blit(v, rc.topleft)
    for i in range(16):
        w, h = int(fire[2] - fire[0]), int(fire[3] - fire[1])
        x = int(fire[0]) - cx + (i * 53 + int(g["t"] * 9)) % max(1, w)
        y = int(fire[1]) - cy + (i * 37 - int(g["t"] * 14)) % max(1, h)
        surf.fill((255, 190, 90), (x, y, 2, 2))
        w, h = int(icer[2] - icer[0]), int(icer[3] - icer[1])
        x = int(icer[0]) - cx + (i * 47) % max(1, w)
        y = int(icer[1]) - cy + (i * 61) % max(1, h)
        surf.fill((220, 240, 255), (x, y, 3, 1))


def draw_squeeze(surf, g, cx, cy):
    sq = g["sq"]
    x0, y0, x1, y1 = B.bounds(g)
    s = int(sq["s"])
    gap = (x1 - x0) - 2 * s
    col = (200, 70, 60) if gap < 80 else (110, 116, 140)
    for xa, xb in ((x0, x0 + s), (x1 - s, x1)):
        if xb > xa:
            rc = pygame.Rect(int(xa) - cx, int(y0) - cy, int(xb - xa), int(y1 - y0))
            D.rect(surf, col, rc)
            for yy in range(rc.y, rc.bottom, 16):
                D.line(surf, (250, 210, 80), (rc.x, yy), (rc.right, yy + 8), 2)
            D.rect(surf, (24, 20, 36), rc, 1)


def hz_color(h):
    if not h["dmg"] and not h.get("los"):
        return (255, 240, 170)
    fx = h.get("fx")
    return (150, 220, 255) if fx == "freeze" else (255, 160, 60) if fx == "burn" else DANGER


def dashed_ring(L, col, a, x, y, r, t):
    n = max(12, int(r) // 2)
    for i in range(0, n, 2):
        ang = i * TAU / n + t * 0.8
        L.fill(col + (a,), (x + int(math.cos(ang) * r), y + int(math.sin(ang) * r), 2, 2))


def draw_one_hz(L, g, h, cx, cy, t):
    k, warn = h["kind"], h["warn"] > 0
    col = hz_color(h)
    f_in = min(1.0, h.get("age", 0.0) / 0.25)
    if warn:
        out = min(1.0, h["warn"] / 0.12) if (not h["dmg"] and h["act"] <= 0.01) else 1.0
    else:
        out = min(1.0, max(0.0, h["act"]) / 0.2)
    p = 1 - max(0.0, h["warn"]) / h["tot"]
    fo = f_in * out
    LR = L.get_rect()
    if k == "circle":
        x, y, r = int(h["x"]) - cx, int(h["y"]) - cy, max(2, int(h["r"]))
        if warn:
            D.circle(L, col + (int((30 + 70 * p) * fo),), (x, y), max(1, int(r * (0.2 + 0.8 * p))))
            dashed_ring(L, col, int(230 * fo), x, y, r, t)
            D.circle(L, col + (int(120 * fo),), (x, y), r, 1)
        else:
            D.circle(L, col + (int(120 * out),), (x, y), r)
            D.circle(L, (255, 235, 200, int(190 * out)), (x, y), max(1, int(r * 0.62)))
            D.circle(L, (255, 255, 255, int(235 * out)), (x, y), max(1, int(r * 0.3)))
            D.circle(L, col + (int(255 * out),), (x, y), r, 2)
    elif k == "rect":
        rc = pygame.Rect(int(h["x0"]) - cx, int(h["y0"]) - cy, int(h["x1"] - h["x0"]), int(h["y1"] - h["y0"]))
        clip = rc.clip(LR)
        if clip.w <= 0 or clip.h <= 0:
            return
        if warn:
            L.fill(col + (int((20 + 70 * p) * fo),), clip)
            old = L.get_clip()
            L.set_clip(clip)
            sh = int(t * 16) % 12
            for xx in range(rc.x - rc.h, rc.right, 12):
                D.line(L, col + (int(150 * fo),), (xx + sh, rc.bottom), (xx + sh + rc.h, rc.y), 1)
            L.set_clip(old)
            D.rect(L, col + (int(220 * fo),), rc, 1)
        else:
            L.fill(col + (int(150 * out),), clip)
            L.fill((255, 235, 200, int(190 * out)), rc.inflate(-6, -6).clip(LR))
            D.rect(L, (255, 255, 255, int(240 * out)), rc, 1)
    elif k == "beam":
        x, y, a, ln, w = h["x"] - cx, h["y"] - cy, h["a"], h["len"], h["w"]
        ex, ey = x + math.cos(a) * ln, y + math.sin(a) * ln
        if warn:
            D.line(L, col + (int((90 + 130 * p) * fo),), (x, y), (ex, ey), max(1, int(w * 0.3 * (0.4 + 0.6 * p))))
            D.circle(L, col + (int(220 * fo),), (int(x), int(y)), 3 + int(5 * p), 1)
            for i in range(10, int(ln), 14):
                L.fill(col + (int(200 * fo),), (int(x + math.cos(a) * i), int(y + math.sin(a) * i), 2, 2))
        else:
            fl_ = 0.85 + 0.15 * math.sin(t * 40)
            D.line(L, col + (int(70 * out),), (x, y), (ex, ey), int(w) + 8)
            D.line(L, col + (int(170 * out),), (x, y), (ex, ey), int(w) + 3)
            D.line(L, (255, 250, 235, int(250 * out * fl_)), (x, y), (ex, ey), max(1, int(w) // 2))
            D.circle(L, (255, 245, 220, int(240 * out)), (int(x), int(y)), int(w * 0.8) + 1)
    elif k == "well":
        x, y, r = int(h["x"]) - cx, int(h["y"]) - cy, int(h["r"])
        dirn = 1 if h.get("pull", 1) > 0 else -1
        R = min(r, 210)
        for i in range(4):
            f = (i / 4 + t * (0.25 if warn else 0.6)) % 1.0
            rr = int(R * ((1 - f) if dirn > 0 else f))
            if rr > 6:
                D.circle(L, (170, 120, 255, int(80 * f_in * out * (0.4 + 0.6 * math.sin(f * 3.1416)))), (x, y), rr, 1)
        D.circle(L, (40, 20, 80, int(200 * fo)), (x, y), 3 if warn else 8)
        D.circle(L, (190, 150, 255, int(255 * fo)), (x, y), 3 if warn else 8, 1)
    elif k == "knock":
        x, y = int(h["x"]) - cx, int(h["y"]) - cy
        if warn:
            D.circle(L, DANGER + (int(200 * fo),), (x, y), int(10 + p * 14), 1)
            D.circle(L, DANGER + (int(60 * fo),), (x, y), int(6 + p * 8))
        else:
            r = int(h["r"])
            fade = max(0.15, 1 - r / h["maxr"])
            D.circle(L, (255, 240, 200, int(230 * fade * out)), (x, y), r, 4)
            D.circle(L, DANGER + (int(200 * fade * out),), (x, y), max(1, r - 4), 2)
    elif k == "conv":
        rc = pygame.Rect(int(h["x0"]) - cx, int(h["y0"]) - cy, int(h["x1"] - h["x0"]), int(h["y1"] - h["y0"]))
        clip = rc.clip(LR)
        if clip.w > 0 and clip.h > 0:
            L.fill((60, 70, 95, int((40 if warn else 95) * fo)), clip)
            D.rect(L, (230, 180, 60, int(230 * fo)), rc, 1)
            if not warn:
                sg = 1 if h["dx"] >= 0 else -1
                for i in range(rc.w // 26 + 1):
                    xx = rc.x + (i * 26 + int(t * 50 * sg)) % max(1, rc.w)
                    for fy in (0.25, 0.5, 0.75):
                        yy = rc.y + int(rc.h * fy)
                        D.lines(L, (255, 220, 110, int(230 * fo)), False, [(xx - 4 * sg, yy - 4), (xx, yy), (xx - 4 * sg, yy + 4)], 1)
    elif k == "dash":
        sx, sy = h["x"] - cx, h["y"] - cy
        if warn:
            D.line(L, col + (int((70 + 120 * p) * fo),), (sx, sy), (sx + math.cos(h["a"]) * h["len"], sy + math.sin(h["a"]) * h["len"]), 1)
        else:
            for j in range(4):
                q = max(0.0, (1 - max(0.0, h["act"]) / h["act0"]) - j * 0.06)
                gx, gy = h["x"] + math.cos(h["a"]) * h["len"] * q - cx, h["y"] + math.sin(h["a"]) * h["len"] * q - cy
                L.fill((255, 170 + 20 * j, 100, int((190 - 45 * j) * out)), (int(gx) - 8, int(gy) - 20, 16, 22))


def draw_trails(surf, g, cx, cy):
    for e, life, mx in g.get("ai", []):
        if not 0 <= e["id"] <= 2:
            continue
        draw_mid(surf, e, int(e["x"]) - cx, int(e["y"]) - cy, g, force=life / mx * 0.6, tint=True)
    for e, life, mx in g.get("fo", []):
        draw_ex(surf, e, int(e["x"]) - cx, int(e["y"]) - cy, g, force=life / mx)


def draw_hz_wrap(old):
    def f(surf, g, cx, cy):
        t = g["t"]
        try:
            if g.get("floor"):
                draw_floor(surf, g, cx, cy)
            if g.get("sq"):
                draw_squeeze(surf, g, cx, cy)
            draw_trails(surf, g, cx, cy)
            L = pygame.Surface((G.W, G.H), SC)
            for h in g["hz"]:
                draw_one_hz(L, g, h, cx, cy, t)
            sh = g.get("b_shield")
            if sh:
                a, b = (sh["x1"] - cx, sh["y1"] - cy), (sh["x2"] - cx, sh["y2"] - cy)
                D.line(L, (150, 200, 255, int(45 + 25 * math.sin(t * 4))), a, b, 16)
                D.line(L, (40, 46, 70, 255), a, b, 8)
                D.line(L, (120, 132, 170, 255), a, b, 5)
                D.line(L, (215, 225, 245, 255), a, b, 2)
            surf.blit(L, (0, 0))
            px, py = int(g["x"]) - cx, int(g["y"]) - cy
            if g.get("freeze", 0) > 0:
                D.circle(surf, (170, 225, 255), (px, py - 4), 10, 1)
                for i in range(4):
                    surf.fill((235, 248, 255), (px - 8 + i * 5, py - 14 + int(math.sin(t * 6 + i) * 2), 2, 2))
            if g.get("burn", 0) > 0:
                for i in range(4):
                    surf.fill((255, 150 + 30 * (i % 2), 60), (px - 6 + i * 4, py - 8 - int((t * 20 + i * 5) % 10), 2, 2))
            if g.get("hack", 0) > 0:
                D.rect(surf, (120, 232, 232), (px - 8, py - 16, 16, 20), 1)
        except Exception:
            G.v9_log("roster-draw-hz")
    return f


# ---------------------------------------------------------------- 그리기: 보스 / 소환체
def draw_bulk(surf, e, x, y, g):
    ph, fl, a = e["phase"], e["fl"] > 0, e["fa"]
    ca, sa = math.cos(a), math.sin(a)
    rust = (168, 108, 74) if ph == 1 else (112, 118, 142) if ph == 2 else (196, 200, 214)
    dk = G.lerp_c(rust, (30, 24, 40), 0.45)
    walk = int(math.sin(e["an"] * 7) * 2) if e["mv"] else 0
    D.rect(surf, dk, (x - 9, y - 8, 6, 9 + walk))
    D.rect(surf, dk, (x + 3, y - 8, 6, 9 - walk))
    D.rect(surf, (255, 255, 255) if fl else rust, (x - 12, y - 26, 24, 20))
    D.rect(surf, dk, (x - 12, y - 12, 24, 4))
    D.rect(surf, G.adj(rust, 30), (x - 12, y - 26, 24, 2))
    if ph < 3:
        D.rect(surf, dk, (x - 18, y - 28, 8, 9))
        D.rect(surf, dk, (x + 10, y - 28, 8, 9))
    else:
        for sx in (-14, 14):
            D.circle(surf, (255, 150, 60), (x + sx, y - 22), 3)
    D.rect(surf, dk, (x - 5, y - 34, 10, 8))
    D.rect(surf, (255, 80, 60), (x - 4 + int(ca * 2), y - 31, 8, 2))
    ax, ay = x + ca * 15, y - 20 + sa * 9
    D.line(surf, (210, 214, 230), (x + 7, y - 20), (ax, ay), 4)
    D.circle(surf, (250, 250, 255), (int(ax), int(ay)), 3)
    if ph == 1 and e["exp"] <= 0 and e["st"] != "stun":        # 전면 방패
        cxs, cys, p, q = x + ca * 18, y - 16 + sa * 10, -sa * 13, ca * 13
        D.line(surf, (40, 46, 70), (cxs + p, cys + q), (cxs - p, cys - q), 7)
        D.line(surf, (120, 132, 170), (cxs + p, cys + q), (cxs - p, cys - q), 4)
    if ph == 2:
        D.line(surf, (60, 64, 86), (x, y - 20), (x + ca * 22, y - 20 + sa * 13), 5)
        D.circle(surf, (255, 170, 80), (int(x + ca * 22), int(y - 20 + sa * 13)), 2)
    if e["st"] == "wind" and int(e["an"] * 14) % 2:
        D.rect(surf, (255, 90, 80), (x - 13, y - 27, 26, 22), 1)


def draw_alch(surf, e, x, y, g):
    ph, fl, t = e["phase"], e["fl"] > 0, e["an"]
    y += round(math.sin(t * 2) * 1.5)
    col = (110, 170, 130) if ph < 4 else (210, 120, 90)
    D.rect(surf, (60, 66, 86), (x - 14, y - 4, 28, 4))
    D.ellipse(surf, (40, 60, 56), (x - 16, y - 30, 32, 30))
    D.ellipse(surf, (255, 255, 255) if fl else col, (x - 14, y - 32, 28, 26))
    D.rect(surf, (50, 56, 76), (x - 14, y - 20, 28, 4))
    D.rect(surf, (30, 30, 46), (x - 7, y - 28, 14, 12), 1)
    h = int(8 * (0.5 + 0.5 * math.sin(t * 3)))
    D.rect(surf, (150, 255, 150) if ph < 3 else (255, 170, 90), (x - 6, y - 17 - h, 12, h + 1))
    for k in range(8):
        a = t * (1.5 if ph < 4 else 3) + k * 0.785
        D.circle(surf, (190, 196, 214), (x + int(math.cos(a) * 8), y - 38 + int(math.sin(a) * 8)), 2)
    D.circle(surf, (90, 96, 120), (x, y - 38), 5)
    surf.fill((255, 90, 60), (x - 1, y - 39, 3, 3))
    for k in range(2 if ph < 2 else 4):
        sg = -1 if k % 2 == 0 else 1
        hh = y - 24 - (k // 2) * 7
        ex_, ey_ = x + sg * 23, hh + int(math.sin(t * 3 + k) * 4) + (k // 2) * 10
        D.line(surf, (150, 156, 176), (x + sg * 13, hh), (ex_, ey_), 3)
        D.circle(surf, (255, 170, 70) if ph >= 2 else (200, 206, 226), (ex_, ey_), 3)


def draw_heat(surf, e, x, y, g):
    ph, fl, t = e["phase"], e["fl"] > 0, e["an"]
    y -= int(e.get("lift", 0))
    hot = (240, 100, 60) if ph in (1, 3) else (120, 200, 255) if ph == 2 else (255, 255, 235)
    if ph == 3 and e["stun"] > 0:
        hot = (130, 190, 240)
    dk = G.lerp_c(hot, (20, 16, 34), 0.65)
    D.circle(surf, G.lerp_c(hot, (0, 0, 0), 0.55), (x, y - 16), 17 + int(math.sin(t * 6) * 2) + (4 if ph == 4 else 0), 1)
    D.rect(surf, dk, (x - 7, y - 8, 5, 9))
    D.rect(surf, dk, (x + 2, y - 8, 5, 9))
    D.ellipse(surf, (255, 255, 255) if fl else G.lerp_c(hot, (60, 60, 80), 0.55), (x - 9, y - 26, 18, 20))
    D.rect(surf, hot, (x - 9, y - 17, 18, 2))
    D.circle(surf, dk, (x, y - 30), 6)
    D.rect(surf, hot, (x - 4, y - 31, 8, 2))
    for sg in (-1, 1):
        ax, ay = x + sg * 8, y - 22
        tx, ty = x + sg * 15, y - 12 + int(math.sin(t * 4 + sg) * 2)
        D.line(surf, dk, (ax, ay), (tx, ty), 3)
        D.circle(surf, hot, (tx, ty), 3 + int(t * 10) % 2)
        D.circle(surf, (255, 255, 255), (tx, ty), 1)
    if ph == 4:
        D.circle(surf, (255, 255, 255), (x, y - 16), 22 + int(math.sin(t * 9) * 2), 1)
    if e["stun"] > 0:
        for i in range(3):
            D.circle(surf, (210, 225, 240), (x - 6 + i * 6, y - 36 - int((t * 18 + i * 7) % 16)), 2)


def draw_mid_body(surf, e, x, y, g):
    surf.blit(pygame.transform.scale(G.SHADOW, (28, 8)), (x - 14, y))
    (draw_bulk, draw_alch, draw_heat)[e["id"]](surf, e, x, y, g)
    if e["inv"] > 0:
        D.circle(surf, (255, 255, 255), (x, y - 14), int(20 + 4 * math.sin(e["an"] * 8)), 1)
    if e["al"] > 0:
        surf.fill((255, 230, 80), (x - 1, y - 48, 2, 5))
        surf.fill((255, 230, 80), (x - 1, y - 42, 2, 2))


def draw_ex_body(surf, e, x, y, g):
    s, t, fl = e["sub"], e["an"], e["fl"] > 0
    if s == "gear":
        D.circle(surf, (60, 64, 90), (x, y), 12)
        for k in range(8):
            a = t * 3 + k * 0.785
            D.circle(surf, (190, 196, 214), (x + int(math.cos(a) * 11), y + int(math.sin(a) * 11)), 2)
        D.circle(surf, (255, 255, 255) if fl else (160, 166, 190), (x, y), 9)
        D.circle(surf, (70, 74, 100), (x, y), 4)
        D.circle(surf, (255, 170, 70), (x, y), 2)
        return
    if s == "orb":
        r = 5 + int(math.sin(t * 8))
        D.circle(surf, (120, 70, 200), (x, y), r + 2)
        D.circle(surf, (255, 255, 255) if fl else (200, 160, 255), (x, y), r)
        surf.fill((255, 255, 255), (x - 1, y - 1, 2, 2))
        return
    surf.blit(G.SHADOW, (x - 6, y - 1))
    if s == "golem":
        wind = e["st"] == "wind" and int(t * 14) % 2
        col = (255, 255, 255) if fl else (220, 110, 80) if wind else (150, 120, 100)
        D.rect(surf, col, (x - 10, y - 22, 20, 18))
        D.rect(surf, (80, 70, 70), (x - 10, y - 10, 20, 3))
        D.rect(surf, (100, 86, 80), (x - 14, y - 20, 5, 12))
        D.rect(surf, (100, 86, 80), (x + 9, y - 20, 5, 12))
        D.rect(surf, (80, 70, 70), (x - 7, y - 4, 5, 5))
        D.rect(surf, (80, 70, 70), (x + 2, y - 4, 5, 5))
        surf.fill((255, 90, 60), (x - 5, y - 18, 3, 3))
        surf.fill((255, 90, 60), (x + 2, y - 18, 3, 3))
    elif s == "phantom":
        v = e["var"]
        col = dict(bulk=(170, 120, 90), alch=(110, 200, 130), heat=(255, 130, 80))[v]
        al = 150 + int(40 * math.sin(t * 5))
        sf = pygame.Surface((26, 30), SC)
        c4 = col + (al,)
        D.rect(sf, c4, (6, 8, 14, 14))
        D.rect(sf, c4, (8, 0, 10, 8))
        D.rect(sf, c4, (7, 22, 5, 7))
        D.rect(sf, c4, (14, 22, 5, 7))
        if v == "bulk":
            D.rect(sf, (200, 210, 240, al), (1, 6, 4, 16))
        elif v == "alch":
            D.circle(sf, (220, 255, 200, al), (13, 4), 4, 1)
        else:
            D.circle(sf, (255, 230, 150, al), (3, 10), 3)
        sf.fill((255, 255, 255, 255), (10, 3, 2, 2))
        sf.fill((255, 255, 255, 255), (15, 3, 2, 2))
        if e["st"] == "wind" and int(t * 16) % 2:
            D.rect(sf, (255, 90, 80, 255), (4, 0, 18, 29), 1)
        surf.blit(sf, (x - 13, y - 27))
    D.rect(surf, (24, 20, 36), (x - 9, y - 32, 18, 3))
    D.rect(surf, (235, 70, 70), (x - 8, y - 31, int(16 * max(0, e["hp"]) // e["mhp"]), 1))


def draw_mid(surf, e, x, y, g, force=None, tint=False):
    a = force if force is not None else vis_alpha(g, e)
    if a <= 0.02:
        return
    gc = (255, 150, 80) if e["id"] == 0 else ((130, 255, 160) if e["phase"] < 4 else (255, 150, 100)) if e["id"] == 1 else heat_col(e)
    boost = 2.0 if e["inv"] > 0 else 1.0
    if g["intro"] > 0 and e["id"] >= 0:
        boost = 1.0 + 1.5 * math.sin(min(1.0, g["intro"] / 2.6) * 3.1416)
    ga = int((46 + 18 * math.sin(e["an"] * 3)) * a * boost) // 10 * 10
    if ga >= 10 and not tint:
        surf.blit(glow(44, gc, min(140, ga)), (x - 44, y - 14 - 44))
    if a >= 0.98 and not tint:
        draw_mid_body(surf, e, x, y, g)
        return
    tmp = pygame.Surface((96, 110), SC)
    draw_mid_body(tmp, e, 48, 84, g)
    if tint:
        tmp.fill((90, 30, 10, 0), special_flags=pygame.BLEND_RGB_ADD)
    tmp.set_alpha(int(255 * min(1.0, a)))
    surf.blit(tmp, (x - 48, y - 84))


def draw_ex(surf, e, x, y, g, force=None):
    a = force if force is not None else min(1.0, (g["t"] - e.setdefault("t0", g["t"])) / 0.35)
    if a <= 0.02:
        return
    if a >= 0.98:
        draw_ex_body(surf, e, x, y, g)
        return
    tmp = pygame.Surface((56, 64), SC)
    draw_ex_body(tmp, e, 28, 46, g)
    tmp.set_alpha(int(255 * a))
    surf.blit(tmp, (x - 28, y - 46))


def draw_final_wrap(old):
    def f(surf, e, cx, cy, t, g):
        e["opened"] = True
        a = vis_alpha(g, e)
        ph = e["phase"]
        x, y = int(e["x"]) - cx, int(e["y"]) - cy
        boost = 1.8 if e["inv"] > 0 else 1.0
        ga = int((50 + 20 * math.sin(t * 3)) * boost) // 10 * 10
        surf.blit(glow(64, B.PHASE_COL[ph - 1], min(150, ga)), (x - 64, y - 64))
        if a < 0.98:
            tmp = pygame.Surface((160, 170), SC)
            old(tmp, e, int(e["x"]) - 80, int(e["y"]) - 100, t, g)
            tmp.set_alpha(int(255 * a))
            surf.blit(tmp, (x - 80, y - 100))
        else:
            old(surf, e, cx, cy, t, g)
        if ph == 1:
            v = pygame.Surface((80, 80), SC)
            D.circle(v, (120, 232, 232, int(45 + 20 * math.sin(t * 3))), (40, 40), 38)
            D.circle(v, (190, 250, 250, 210), (40, 40), 38, 1)
            surf.blit(v, (x - 40, y - 40))
        elif ph == 4 and "omega" in e:
            s = f"{max(0.0, e['omega']):.1f}"
            fn = font14()
            col = (255, 80, 70) if int(t * 4) % 2 or e["omega"] > 8 else (255, 230, 200)
            img, sh = fn.render(s, True, col), fn.render(s, True, (24, 20, 36))
            surf.blit(sh, (x - img.get_width() // 2 + 1, y - 62 + 1))
            surf.blit(img, (x - img.get_width() // 2, y - 62))
    return f


# ---------------------------------------------------------------- HUD: 보스 체력바 (v9_ui.boss_bar 대체)
def status_list(g):
    out = []
    if g.get("burn", 0) > 0:
        out.append(("화상", (255, 150, 80)))
    if g.get("freeze", 0) > 0:
        out.append((f"빙결 {g['freeze']:.1f}", (160, 225, 255)))
    if g.get("hack", 0) > 0:
        out.append((f"조작 반전 {g['hack']:.1f}", (120, 232, 232)))
    return out


def banner(g, mb):
    if mb["kind"] == "final":
        ph = mb["phase"]
        if ph == 1:
            n = sum(1 for o in mb.get("cores", []) if o["hp"] > 0)
            return f"서브 코어 {n}/4  (중앙 코어는 무적)"
        if ph == 4:
            return f"자폭까지 {max(0.0, mb.get('omega', 0)):.1f}초 - 코어를 파괴하라!"
        return FINAL_PN[ph - 1]
    i, ph = mb["id"], mb["phase"]
    if i == 0:
        return ("[녹슨 철벽] 정면 장갑 - 측·후면을 노려라", "[요새화] 방패 뒤로 숨어라 - 3초마다 충격파", "[제한 해제] 잔상 속 진짜 돌진을 피하라")[ph - 1]
    if i == 1 and ph == 4 and g.get("sq"):
        x0, y0, x1, y1 = B.bounds(g)
        return f"[자폭 시퀀스] 벽 간격 {int(x1 - x0 - 2 * g['sq']['s'])}px"
    if i == 2 and ph == 3:
        return "[과열 배출] 지금이 기회!" if mb["stun"] > 0 else f"[열폭주] 과열 게이지 {int(mb['heat'])}%"
    return f"[{PNAMES[i][ph - 1]}]"


def boss_bar(screen, font, g, u):
    SW, SH = G.W * u, G.H * u
    y = 63
    for s, c in status_list(g):
        G.txt(screen, font, s, SW // 2, y * u, c, True, u)
        y += 8
    pf = g.get("pflash")
    if pf and pf[0] > 0:
        v = pygame.Surface((SW, SH), SC)
        v.fill(tuple(pf[1]) + (int(170 * max(0.0, pf[0]) ** 1.5),))
        screen.blit(v, (0, 0))
    pt = g.get("ptitle")
    if pt and pt[1] > 0:
        a_ = max(0.0, min(1.0, pt[1] / 0.6, (2.4 - pt[1]) / 0.5))
        fade_text(screen, G.bigfont(u), pt[0], SW // 2, int((68 + (1 - a_) * 4) * u), (255, 190, 150), a_, u)
        fade_text(screen, font, pt[2], SW // 2, int(86 * u), G.CREAM, a_, u)
    mb = next((e for e in g["en"] if e["kind"] in ("mid", "final") and e["hp"] > 0 and (g["lock"] or e["ag"])), None)
    if not mb:
        return
    fin = mb["kind"] == "final"
    bw = 190 * u if fin else 150 * u
    x0 = (SW - bw) // 2
    name = FINAL_NAME if fin else NAMES[mb["id"]]
    ph = mb["phase"]
    G.plate(screen, x0 - 8 * u, 31 * u, bw + 16 * u, 29 * u, u)
    G.txt(screen, font, name, SW // 2, 32 * u, (255, 120, 110) if ph >= 3 else G.CORAL, True, u)
    col = B.PHASE_COL[ph - 1] if fin else MID_COL[ph - 1]
    fr = max(0.0, mb["hp"] / mb["mhp"])
    wfill = int((bw - 2 * u) * fr)
    D.rect(screen, G.INK, (x0, 41 * u, bw, 8 * u))
    D.rect(screen, G.lerp_c(col, (0, 0, 0), 0.45), (x0 + u, 42 * u, bw - 2 * u, 6 * u))
    mb["hv"] = max(fr, mb.get("hv", fr) + (fr - mb.get("hv", fr)) * 0.05)
    D.rect(screen, (255, 235, 200), (x0 + u, 42 * u, int((bw - 2 * u) * mb["hv"]), 6 * u))
    D.rect(screen, col, (x0 + u, 42 * u, wfill, 6 * u))
    D.rect(screen, G.lerp_c(col, (255, 255, 255), 0.5), (x0 + u, 42 * u, wfill, 2 * u))
    marks = C.FINAL_BOSS["phases"] if fin else C.MID_BOSS["phases"][mb["id"]]
    for m in marks:
        D.rect(screen, G.INK, (x0 + int(bw * m), 41 * u, max(1, u), 8 * u))
    G.txt(screen, font, banner(g, mb), SW // 2, 50 * u, (150, 240, 240) if fin else G.CREAM, True, u)
    if g["intro"] > 0:                                         # 등장 연출
        a = max(0.0, min(1.0, g["intro"] / 0.5, (2.6 - g["intro"]) / 0.4))
        band = pygame.Surface((SW, 44 * u), SC)
        band.fill((14, 8, 24, int(215 * a)))
        screen.blit(band, (0, 92 * u))
        if a > 0.3:
            G.title_txt(screen, G.bigfont(u), name, SW // 2, 98 * u, u, (255, 150, 130))
            G.txt(screen, font, FINAL_SUB if fin else SUBS[mb["id"]], SW // 2, 116 * u, G.CREAM, True, u)


def make_objective(old):
    def objective(g):
        if g["zid"] == "boss_f":
            e = next((o for o in g["en"] if o["kind"] == "final"), None)
            h = {1: "네 개의 서브 코어를 파괴하라 (중앙 코어는 무적)", 2: "공간 왜곡과 환영을 피하며 본체를 공격하라",
                 3: "조작 반전과 코어 빔을 버텨라 - 벽 뒤로 숨어라", 4: "30초 안에 코어를 파괴하라!"}
            return h[e["phase"]] if e else "빅 브라더를 쓰러뜨려라"
        return old(g)
    return objective


# ---------------------------------------------------------------- 설치
def install(g_mod, cfg, boss_mod):
    global G, C, B
    G, C, B = g_mod, cfg, boss_mod
    G.MID_NAMES, G.BOSS_SUB = NAMES, SUBS
    G.FOE_NAME["ex"], G.FOE_NAME["final"], G.FOE_NAME["pylon"] = "소환체", "빅 브라더", "서브 코어"
    G.AGGRO["ex"] = 9999
    B.FINAL_NAME, B.FINAL_SUB = FINAL_NAME, FINAL_SUB
    B.final_ai, B.pylon_ai, B.final_hit = final_ai, pylon_ai, final_hit
    B.update_hz = update_hz_wrap(B.update_hz)
    B.draw_hz = draw_hz_wrap(B.draw_hz)
    B.draw_final = draw_final_wrap(B.draw_final)
    old_mk, old_foe, old_hit, old_de = G.mk_mid, G.foe_ai, G.hit_foe, G.draw_enemy
    old_clear, old_vt, old_upd, old_load = G.clear_arena, G.valid_targets, G.update, G.load_zone

    def mk_mid(x, y, i):
        e = old_mk(x, y, i)
        e.update(phase=1, ph2=False, cos=[], rest=1.6, last="", fa=math.pi / 2, stun=0.0, exp=0.0, heat=0.0, swt=2.5,
                 scrap=0, _dn=0, lift=0, r=(17, 16, 15)[i])
        return e

    def foe_ai(g, e, dt, d, ux, uy):
        if e["kind"] == "ex":
            e["ag"] = True
            try:
                return ex_ai(g, e, dt, d, ux, uy)
            except Exception:
                G.v9_log("roster-ex")
                e["hp"] = 0
                return False
        return old_foe(g, e, dt, d, ux, uy)

    def hit_foe(g, e, b, dmg):
        if e["kind"] == "mid":
            return hit_boss(g, e, b, dmg)
        if e["kind"] == "ex":
            return hit_ex(g, e, b, dmg)
        return old_hit(g, e, b, dmg)

    def draw_enemy(surf, e, cx, cy, t, g):
        k = e["kind"]
        if k in ("mid", "ex"):
            try:
                (draw_mid if k == "mid" else draw_ex)(surf, e, int(e["x"]) - cx, int(e["y"]) - cy, g)
            except Exception:
                G.v9_log("roster-draw")
            return
        return old_de(surf, e, cx, cy, t, g)

    def clear_arena(g):
        old_clear(g)
        for o in g["en"]:
            if o["hp"] > 0:
                o["hp"], o["nodrop"] = 0, True
        g["b_shield"] = g["floor"] = g["sq"] = None
        g["burn"] = g["freeze"] = g["hack"] = 0

    def valid_targets(g):
        return [t for t in old_vt(g) if not (t[3] == "e" and t[2].get("notarget"))]

    def update(g, inp, dt):
        if g.get("hack", 0) > 0 and not g["tr"]:               # 시스템 해킹: 이동 반전
            inp = (-inp[0], -inp[1], inp[2])
        z0 = g["zid"]
        prev = [o for o in g["en"] if o["kind"] in ("ex", "mid")]
        old_upd(g, inp, dt)
        if g["zid"] != z0:
            g["fo"], g["ai"] = [], []
            return
        cur = {id(o) for o in g["en"]}
        for o in prev:                                          # 사라진 소환체·보스는 뚝 끊기지 않고 서서히 흩어진다
            if id(o) not in cur:
                if o["kind"] == "mid":
                    g.setdefault("ai", []).append([dict(o), 1.3, 1.3])
                else:
                    g.setdefault("fo", []).append([dict(o), 0.4, 0.4])
        for o in g["en"]:
            if o.get("appear", 0) > 0:
                o["appear"] = max(0.0, o["appear"] - dt)
        for key in ("fo", "ai"):
            g[key] = [[e, l - dt, m] for e, l, m in g.get(key, []) if l - dt > 0]

    def load_zone(g, zid, tx, ty):
        old_load(g, zid, tx, ty)
        g["burn"] = g["freeze"] = g["hack"] = 0
        g["b_shield"] = g["floor"] = g["sq"] = g["_pp"] = None
        g["fo"], g["ai"], g["pflash"], g["ptitle"] = [], [], None, None

    G.mk_mid, G.mid_ai, G.foe_ai, G.hit_foe, G.draw_enemy = mk_mid, mid_ai, foe_ai, hit_foe, draw_enemy
    G.clear_arena, G.valid_targets, G.update, G.load_zone = clear_arena, valid_targets, update, load_zone