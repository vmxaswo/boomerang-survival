"""v9 필드 보스 모듈 (v9_kaiju.py)  -  오픈월드를 배회하는 5등급 괴수 '탈라소르 (Thalassor)'
 - 서식지: 월드 남서쪽 '남서 폐허 초소' 워프포인트 근처의 얼어붙은 공터 (반경 약 17칸). 얼음 기둥 4개가 포효를 막아 준다.
 - 평소: 서식지 안을 천천히 기어다니다가 잠든다. 가까이 가거나 부메랑을 맞히면 포효하며 깨어난다.
 - 서식지 밖으로 멀리 벗어나면 전투를 풀고 서식지로 돌아가 체력·장갑을 모두 회복한다.
 - 처치하면 큰 보상, 일정 시간(RESPAWN) 뒤 서식지에 다시 나타난다.
 전투 (3페이즈)
   1페이즈: 등의 장갑판 3장 (각 14). 장갑이 남아 있으면 본체는 피해를 1/4만 받는다. 다 깨면 2페이즈.
   2페이즈: 약점이 드러나고 패턴이 늘고 빨라진다.   3페이즈(체력 33%): 발광 폭주, 연계기.
   기절(돌진이 벽에 박힘 / 강하 착지) 중에는 피해 2배.
 패턴 11종: 발톱 내려찍기 / 가시 꼬리 휘두르기 / 광란 돌진 / 발광 맥동 / 지면 균열 / 포효 충격파 / 가시 투척 /
           날개짓 돌풍 / 활공 강하 / 빙전 브레스 / 기어가기 사냥  (+ 3페이즈 연계기)
 수치는 config.py 에 KAIJU 사전을 두면 바꿀 수 있다 (없으면 기본값).
 v9_pfx 설치 뒤에 설치한다:
    import v9_kaiju
    v9_kaiju.install(G, C, v9_boss, v9_world, v9_open, v9_ui, v9_roster)"""
import math
import random

import pygame

import v9_kaiju_fx as FX

D = pygame.draw
SC = pygame.SRCALPHA
G = C = V = W = O = UI = R = None
NAME, SUB = "탈라소르 (Thalassor)", "얼음 왕관을 쓴 5등급 괴수"
DEFAULT = dict(hp=260, armor=3, plate_hp=14, phase3=0.33, gold=320, exp=420, parts=10, respawn=300.0, nest_r=17,
               aggro=150, leave=130, armor_chip=0.25)
PHASE_COL = ((150, 220, 255), (110, 230, 255), (200, 250, 255))
PILLARS = ((-7, -5), (7, -5), (-7, 5), (7, 5))
_S = {}


def conf():
    d = dict(DEFAULT)
    d.update(getattr(C, "KAIJU", {}) or {})
    return d


def nest(g):
    m = (g.get("meta") or {}).get("kaiju")
    return (m[0] * G.T + 8, m[1] * G.T + 8) if m else None


def _pfx(name, x, y, **kw):
    """v9_pfx 가 있으면 탑다운 이펙트를 띄운다"""
    try:
        import v9_pfx
        if _G_[0] is not None:
            v9_pfx.spawn(_G_[0], name, x, y, **kw)
    except Exception:
        pass


_G_ = [None]


# ================================================================= 보스 데이터
def mk_kaiju(x, y):
    cf = conf()
    return dict(kind="kaiju", x=x, y=y, hx=None, hy=y, hp=cf["hp"], mhp=cf["hp"], fl=0, kb=0, kx=0, ky=0, ag=True, hb=12, r=30,
                an=0.0, al=0, mv=False, st="sleep", stt=0.0, phase=1, ph2=False, inv=0.0, lz=0.0, sg=1, armor=cf["armor"],
                plates=[cf["plate_hp"]] * cf["armor"], mode="sleep", home=(x, y), cos=[], rest=1.4, last="", wake=False,
                roam_t=0.0, sleep_t=0.0, wp=None, cue=None, cue_t=-99.0, nodrop=True)


# ================================================================= 도구
def cue(g, e, name):
    e["cue"], e["cue_t"] = name, g["t"]


def shake(g, v):
    g["shake"] = max(g.get("shake", 0), v)


def hz(g, kind, warn, act, **kw):
    """괴수의 위험 구역: 이펙트 테마(storm)와 '괴수 것' 표시를 붙인다 (전투가 풀리면 한꺼번에 지운다)"""
    h = V.add_hz(g, kind, warn, act, **kw)
    h["th"], h["kj"] = "storm", True
    return h


def clear_hz(g):
    g["hz"] = [h for h in g["hz"] if not h.get("kj")]


def kmove(g, e, dx, dy):
    """서식지 반경 안에서만 움직인다. 막히면 False"""
    x0, y0 = e["x"], e["y"]
    G.move(e, dx, dy, g["solid"])
    n = nest(g)
    if n:
        R_ = conf()["nest_r"] * G.T - 20
        d = G.dist(e["x"], e["y"], n[0], n[1])
        if d > R_:
            e["x"] = n[0] + (e["x"] - n[0]) / d * R_
            e["y"] = n[1] + (e["y"] - n[1]) / d * R_
    return abs(e["x"] - x0) + abs(e["y"] - y0) > (abs(dx) + abs(dy)) * 0.35


def rest_pose(e):
    if e["st"] not in ("stun", "sleep"):
        e["st"] = "recover"


# ================================================================= 패턴
def p_claw(g, e):
    """발톱 내려찍기: 일어서 앞발을 치켜들었다가 플레이어 자리를 내려찍는다 (2연타, 3페이즈 3연타)"""
    ph = e["phase"]
    for i in range(2 + (ph >= 3)):
        x, y = g["x"], g["y"]
        w = 0.85 if i == 0 else 0.7
        hz(g, "circle", w, 0.25, x=x, y=y, r=34)
        e["st"] = "rear_w"
        yield V.tm(w)
        e["st"] = "slam"
        cue(g, e, "slam")
        shake(g, 0.3)
        G.play("boom")
        if ph >= 2:
            k = R.hz(g, "knock", 0.0, 1.1, x=x, y=y, r=8, spd=170, maxr=150, hit=False)
            k["th"], k["kj"] = "storm", True
        yield 0.42
    rest_pose(e)
    yield 0.4


TAIL_R = 108                                                     # 꼬리가 닿는 반경 (몸 중심에서)


def p_tails(g, e):
    """회전 꼬리치기: 꼬리 셋을 감아 쥐고 몸을 낮췄다가, 제자리에서 빠르게 몇 바퀴 돌며 꼬리로 주위를 쓸어 낸다.
    예고 동안 꼬리가 닿는 원 밖으로 벗어나면 안전하다. 3페이즈는 반대로 한 번 더 돈다."""
    ph = e["phase"]
    e["lz"] = V.angto(g, e)
    e["st"] = "coil_w"
    turns = 2 + (ph >= 2)
    spin_t = 0.45 * turns
    rounds = 2 if ph >= 3 else 1
    hz(g, "circle", 0.85, spin_t, x=e["x"], y=e["y"], r=TAIL_R, nofx=True)
    G.play("gate")
    yield V.tm(0.85)
    dr = random.choice((-1, 1))
    for rd in range(rounds):
        if rd > 0:                                               # 3페이즈: 잠깐 멈췄다가 반대로 한 번 더
            e["st"] = "coil_w"
            hz(g, "circle", 0.55, spin_t, x=e["x"], y=e["y"], r=TAIL_R, nofx=True)
            yield V.tm(0.55)
            dr = -dr
        e["st"], e["spin"] = "sweep", dr
        cue(g, e, "spin")
        _pfx("gust_storm", e["x"], e["y"] + 6)
        shake(g, 0.25)
        w = turns * math.tau / spin_t * dr
        t = 0.0
        while t < spin_t:
            e["lz"] += w * 0.03
            if int(t / 0.15) != int((t + 0.03) / 0.15):
                G.play("throw")
            t += 0.03
            yield 0.03
        e["st"] = "skid"
        cue(g, e, "spin_end")
        shake(g, 0.2)
        yield 0.45
    rest_pose(e)
    yield 0.4


def p_charge(g, e):
    """광란 돌진: 배를 깔고 땅을 긁다가 낮게 질주. 벽(기둥·서식지 경계)에 박히면 3초 기절 = 약점"""
    ph = e["phase"]
    a = V.angto(g, e)
    e["lz"], e["st"] = a, "crawl_w"
    L, sp = 250.0, 360.0 + 30 * ph
    act = L / sp
    R.hz(g, "dash", 1.1, act, x=e["x"], y=e["y"], a=a, len=L, w=36, act0=act, px=e["x"], py=e["y"])["th"] = "storm"
    g["hz"][-1]["kj"] = True
    G.play("gate")
    yield V.tm(1.1)
    e["st"] = "rush"
    cue(g, e, "launch")
    shake(g, 0.15)
    t, crashed = 0.0, False
    while t < act:
        if not kmove(g, e, math.cos(a) * sp * 0.03, math.sin(a) * sp * 0.03):
            crashed = True
            break
        t += 0.03
        yield 0.03
    if crashed or t >= act * 0.98:
        n = nest(g)
        if crashed or (n and G.dist(e["x"], e["y"], n[0], n[1]) > conf()["nest_r"] * G.T - 30):
            e["st"] = "stun"
            cue(g, e, "crash")
            shake(g, 0.5)
            G.play("boom")
            G.toast(g, "탈라소르가 벽에 박혀 쓰러졌다! 지금이 기회다", 2.0)
            yield 3.0
            e["st"] = "recover"
            yield 0.4
            return
    e["st"] = "skid"
    yield 0.6
    rest_pose(e)
    yield 0.3


def p_pulse(g, e):
    """발광 맥동: 왕관이 활짝 펴지며 가슴이 푸르게 달아오른 뒤, 한 군데가 빈 전기탄 고리 (3페이즈 2연발)"""
    ph = e["phase"]
    e["st"] = "glow_w"
    G.play("portal")
    yield V.tm(1.0)
    for r in range(1 + (ph >= 3)):
        e["st"] = "pulse"
        cue(g, e, "pulse")
        V.ring_gap(g, e, 22 + 2 * ph, 100 + 10 * r, V.angto(g, e) + random.uniform(-0.8, 0.8), 0.34, 1)
        G.play("shoot")
        yield 0.75
    rest_pose(e)
    yield 0.4


def p_fissure(g, e):
    """지면 균열: 엄니를 땅에 꽂으면 플레이어 주위를 가로지르는 띠가 순서대로 터진다 (한 줄은 비어 있다)"""
    ph = e["phase"]
    n = 5 + (ph >= 3) * 2
    horiz = random.random() < 0.5
    n_ = nest(g) or (e["x"], e["y"])
    R_ = conf()["nest_r"] * G.T
    gap = random.randrange(1, n - 1)
    c = g["y"] if horiz else g["x"]
    e["st"] = "gore_w"
    yield 0.45
    e["st"] = "gore"
    cue(g, e, "gore")
    shake(g, 0.25)
    for i in range(n):
        if i == gap:
            continue
        off = c + (i - (n - 1) / 2) * 40
        w = 0.9 + i * 0.18
        if horiz:
            hz(g, "rect", w, 0.45, x0=n_[0] - R_, x1=n_[0] + R_, y0=off - 13, y1=off + 13)
        else:
            hz(g, "rect", w, 0.45, x0=off - 13, x1=off + 13, y0=n_[1] - R_, y1=n_[1] + R_)
    G.play("gate")
    yield V.tm(0.9 + n * 0.18) + 0.2
    rest_pose(e)
    yield 0.4


def p_roar(g, e):
    """포효 충격파: 상체를 들고 왕관을 떨며 포효 -> 퍼지는 충격파 (얼음 기둥 뒤에 숨으면 막힌다)"""
    e["st"] = "roar_w"
    yield V.tm(0.9)
    e["st"] = "roar"
    cue(g, e, "roar")
    shake(g, 0.6)
    G.play("boss")
    k = R.hz(g, "knock", 0.0, 2.6, x=e["x"], y=e["y"], r=10, spd=200, maxr=440, hit=False)
    k["th"], k["kj"] = "storm", True
    yield 1.1
    rest_pose(e)
    yield 0.4


def p_spines(g, e):
    """가시 투척: 꼬리 셋을 치켜들어 벌렸다가 부채꼴로 가시를 튕긴다 (첫 발은 조준탄, 3페이즈 2단)"""
    ph = e["phase"]
    e["st"] = "spine_w"
    yield V.tm(0.6)
    for r in range(1 + (ph >= 3)):
        e["st"] = "spine"
        cue(g, e, "flick")
        a = V.angto(g, e)
        V.fire(g, e, a, 185, 1, 3.0)
        n = 7 + 2 * ph
        for i in range(n):
            V.fire(g, e, a + (i - (n - 1) / 2) * 0.17, 120 + 10 * r, 1, 3.2)
        G.play("shoot")
        yield 0.55
    rest_pose(e)
    yield 0.35


def p_gust(g, e):
    """날개짓 돌풍: 이륙해 낮게 떠서 날개를 크게 친다. 칠 때마다 밀어내는 바람 + 얼음 파편"""
    ph = e["phase"]
    e["st"] = "takeoff"
    G.play("gate")
    yield 0.6
    e["st"] = "gust"
    for k in range(3 + ph):
        cue(g, e, "flap")
        _pfx("gust_storm", e["x"], e["y"] + 10)
        w = hz(g, "well", 0.0, 0.45, x=e["x"], y=e["y"], r=170, pull=-170, dmg=False)
        w["gust"] = True
        a = V.angto(g, e)
        for i in range(5):
            V.fire(g, e, a + (i - 2) * 0.22, 140, 1, 2.6)
        G.play("shoot")
        yield 0.62
    e["st"] = "land"
    yield 0.55
    rest_pose(e)
    yield 0.3


def p_dive(g, e):
    """활공 강하: 높이 날아올라 사라졌다가, 플레이어 자리의 그림자로 내리꽂힌다. 착지 후 잠시 기절 = 약점"""
    ph = e["phase"]
    e["st"] = "ascend"
    G.play("gate")
    yield 0.7
    e["st"], e["r"] = "high", 0                                  # 하늘 높이: 맞지도 부딪히지도 않는다
    tx, ty = g["x"], g["y"]
    hz(g, "circle", 1.3, 0.35, x=tx, y=ty, r=52)
    t = 0.0
    while t < V.tm(1.3) - 0.25:                                 # 그림자가 목표 지점으로 미끄러져 간다
        d = G.dist(e["x"], e["y"], tx, ty)
        if d > 2:
            k = min(1.0, 260 * 0.05 / d)
            e["x"] += (tx - e["x"]) * k
            e["y"] += (ty - e["y"]) * k
        t += 0.05
        yield 0.05
    e["x"], e["y"] = tx, ty
    e["st"] = "dive"
    yield 0.25
    e["r"] = 30
    cue(g, e, "crash")
    _pfx("nova_storm", tx, ty)
    shake(g, 0.7)
    G.play("boom")
    if ph >= 2:
        for i in range(6):
            a = i * math.tau / 6
            hz(g, "circle", 0.5, 1.4, x=tx + math.cos(a) * 70, y=ty + math.sin(a) * 70, r=16, fx="freeze")
    e["st"] = "stun"
    yield 1.6
    e["st"] = "recover"
    yield 0.4


def p_breath(g, e):
    """빙전 브레스: 가슴에 냉기를 모았다가 고개를 휘두르며 얼음 숨결을 뿜는다. 지나간 자리에 얼음 가시가 솟는다"""
    ph = e["phase"]
    a0, sweep = V.angto(g, e), 0.8 + 0.12 * ph
    dr = random.choice((-1, 1))
    e["lz"], e["st"] = a0 - dr * sweep, "breath_w"
    for s in (-1, 1):
        hz(g, "beam", 0.9, 0.0, x=e["x"], y=e["y"], a=a0 + s * sweep, len=260, w=2, dmg=False)
    G.play("gate")
    yield V.tm(0.9)
    e["st"] = "breath"
    cue(g, e, "ignite")
    shake(g, 0.3)
    n = int((1.4 + 0.25 * ph) / 0.06)
    for i in range(n):
        a = a0 + dr * (-sweep + 2 * sweep * i / n)
        e["lz"] = a
        if i % 6 != 5:
            V.fire(g, e, a, 155 + 12 * ph, 1, 2.2)
        if i % 5 == 0:
            d_ = random.uniform(70, 110)
            hz(g, "circle", 0.45, 1.3, x=e["x"] + math.cos(a) * d_, y=e["y"] + math.sin(a) * d_, r=15, fx="freeze")
        if i % 4 == 0:
            G.play("shoot")
        yield 0.06
    rest_pose(e)
    yield 0.5


def p_hunt(g, e):
    """기어가기 사냥: 배를 깔고 플레이어 주위를 빠르게 돌며 서리 자국을 남기고, 마지막에 엄니로 들이받는다"""
    ph = e["phase"]
    e["st"] = "prowl"
    G.play("gate")
    dr = random.choice((-1, 1))
    t, last = 0.0, 0.0
    while t < 2.0 + 0.3 * ph:
        dx, dy = g["x"] - e["x"], g["y"] - e["y"]
        d = math.hypot(dx, dy) or 1
        tx, ty = -dy / d * dr, dx / d * dr
        rx_, ry_ = dx / d * (d - 95) / 60, dy / d * (d - 95) / 60
        vx, vy = tx + rx_, ty + ry_
        vl = math.hypot(vx, vy) or 1
        kmove(g, e, vx / vl * 150 * 0.05, vy / vl * 150 * 0.05)
        e["lz"] = math.atan2(vy, vx)
        if t - last > 0.3:
            last = t
            hz(g, "circle", 0.35, 1.4, x=e["x"], y=e["y"], r=16, fx="freeze")
        t += 0.05
        yield 0.05
    a = V.angto(g, e)                                            # 엄니로 들이받기
    e["lz"], e["st"] = a, "crawl_w"
    R.hz(g, "dash", 0.5, 0.28, x=e["x"], y=e["y"], a=a, len=100, w=32, act0=0.28, px=e["x"], py=e["y"])["th"] = "storm"
    g["hz"][-1]["kj"] = True
    yield V.tm(0.5)
    e["st"] = "rush"
    cue(g, e, "launch")
    for _ in range(9):
        kmove(g, e, math.cos(a) * 360 * 0.03, math.sin(a) * 360 * 0.03)
        yield 0.03
    e["st"] = "gore"
    cue(g, e, "gore")
    shake(g, 0.3)
    yield 0.5
    rest_pose(e)
    yield 0.3


def p_combo(g, e):
    """3페이즈 연계기: 발톱 2연타 -> (틈) -> 꼬리 휘두르기"""
    yield from p_claw(g, e)
    yield 0.4
    yield from p_tails(g, e)


ALWAYS = lambda g, e: True                                       # noqa: E731
POOLS = {1: [("claw", p_claw, 3, ALWAYS), ("tails", p_tails, 2, ALWAYS), ("spines", p_spines, 3, ALWAYS), ("hunt", p_hunt, 2, ALWAYS),
             ("gust", p_gust, 1, ALWAYS)],
         2: [("claw", p_claw, 2, ALWAYS), ("tails", p_tails, 2, ALWAYS), ("spines", p_spines, 2, ALWAYS), ("hunt", p_hunt, 2, ALWAYS),
             ("gust", p_gust, 2, ALWAYS), ("charge", p_charge, 3, ALWAYS), ("pulse", p_pulse, 2, ALWAYS),
             ("fissure", p_fissure, 2, ALWAYS), ("roar", p_roar, 2, ALWAYS), ("breath", p_breath, 3, ALWAYS),
             ("dive", p_dive, 2, ALWAYS)],
         3: [("claw", p_claw, 2, ALWAYS), ("tails", p_tails, 2, ALWAYS), ("spines", p_spines, 2, ALWAYS), ("hunt", p_hunt, 2, ALWAYS),
             ("gust", p_gust, 2, ALWAYS), ("charge", p_charge, 3, ALWAYS), ("pulse", p_pulse, 2, ALWAYS),
             ("fissure", p_fissure, 2, ALWAYS), ("roar", p_roar, 2, ALWAYS), ("breath", p_breath, 3, ALWAYS),
             ("dive", p_dive, 3, ALWAYS), ("combo", p_combo, 2, ALWAYS)]}
REST = (1.2, 0.9, 0.7)


def p_wake(g, e):
    """잠에서 깨어나 포효"""
    e["st"] = "roar_w"
    yield 0.6
    e["st"] = "roar"
    cue(g, e, "roar")
    shake(g, 0.5)
    G.play("boss")
    G.toast(g, f"{NAME}가 깨어났다!", 2.5)
    yield 1.0
    rest_pose(e)
    yield 0.6


def enter_phase(g, e, p):
    e["phase"], e["ph2"], e["inv"] = p, p >= 2, 1.6
    V.reset_cos(g, e, 1.0)
    clear_hz(g)
    e["st"], e["r"] = "roar", 30
    cue(g, e, "rage")
    g["rings"].append([e["x"], e["y"], 0.0, 170, PHASE_COL[p - 1]])
    G.spark(g, e["x"], e["y"], PHASE_COL[p - 1], 30)
    shake(g, 0.8)
    G.play("boss")
    G.toast(g, ("장갑이 모두 깨졌다! 탈라소르의 몸이 푸르게 타오른다", "탈라소르가 폭주한다! 온몸에서 전기가 튄다")[p - 2], 3.0)


# ================================================================= AI
def kaiju_ai(g, e, dt):
    _G_[0] = g
    cf = conf()
    e["ag"] = True
    V.ensure(e)
    n = nest(g) or e["home"]
    T = G.T
    d = G.dist(g["x"], g["y"], e["x"], e["y"])
    dn = G.dist(g["x"], g["y"], n[0], n[1])
    mode = e["mode"]
    if mode in ("sleep", "roam"):
        if d < cf["aggro"] or e.get("_hit"):
            e["mode"] = "fight"
            e["_hit"] = False
            e["cos"], e["rest"] = [[p_wake(g, e), 0.0]], 1.0
            return False
        if mode == "sleep":
            e["st"] = "sleep"
            e["sleep_t"] -= dt
            if e["sleep_t"] <= 0:
                e["mode"], e["roam_t"], e["st"] = "roam", random.uniform(14, 22), "idle"
            return False
        e["st"] = "idle"
        e["roam_t"] -= dt
        if e["wp"] is None or G.dist(e["x"], e["y"], *e["wp"]) < 10:
            a, r = random.random() * math.tau, random.uniform(0, 6) * T
            e["wp"] = (n[0] + math.cos(a) * r, n[1] + math.sin(a) * r)
        dx, dy = e["wp"][0] - e["x"], e["wp"][1] - e["y"]
        dl = math.hypot(dx, dy) or 1
        if not kmove(g, e, dx / dl * 26 * dt, dy / dl * 26 * dt):
            e["wp"] = None
        if e["roam_t"] <= 0:
            e["mode"], e["sleep_t"] = "sleep", random.uniform(10, 16)
        return True
    if mode == "return":
        dx, dy = n[0] - e["x"], n[1] - e["y"]
        dl = math.hypot(dx, dy)
        e["st"] = "idle"
        e["hp"] = min(e["mhp"], e["hp"] + 30 * dt)
        if dl > 12:
            G.move(e, dx / dl * 80 * dt, dy / dl * 80 * dt, g["solid"])
        else:
            reset_fight(e)
        if d < cf["aggro"] * 0.7 and dn < cf["nest_r"] * T:
            e["mode"] = "fight"
        return True
    # ---- 전투
    if dn > cf["nest_r"] * T + cf["leave"] and d > 220:            # 서식지를 멀리 벗어나면 전투를 풀고 돌아간다
        e["mode"] = "return"
        V.reset_cos(g, e, 1.2)
        clear_hz(g)
        e["r"] = 30
        G.toast(g, f"{NAME}가 서식지로 돌아간다...", 2.0)
        return False
    if e["phase"] == 2 and e["hp"] / e["mhp"] <= cf["phase3"]:
        enter_phase(g, e, 3)
    e["inv"] = max(0.0, e["inv"] - dt)
    if e["inv"] > 0:
        return False
    if e["st"] == "roar" and not e["cos"]:
        e["st"] = "idle"
    if not e["cos"]:                                               # 패턴 사이: 플레이어 주위를 기어다니며 거리를 잰다
        if e["st"] in ("recover", "skid", "land"):
            e["st"] = "idle"
        ux, uy = (g["x"] - e["x"]) / (d or 1), (g["y"] - e["y"]) / (d or 1)
        if d < 80:
            vx, vy, sp = -ux, -uy, 42
        elif d > 150:
            vx, vy, sp = ux, uy, 36
        else:
            vx, vy, sp = -uy * e["sg"], ux * e["sg"], 28
        kmove(g, e, vx * sp * dt, vy * sp * dt)

    def rest():
        e["sg"] = random.choice((-1, 1))
        return V.cdm(REST[e["phase"] - 1] * random.uniform(0.85, 1.15))
    V.sched(g, e, dt, POOLS[e["phase"]], rest)
    return not e["cos"]


def reset_fight(e):
    """서식지로 돌아와 원래 상태로: 체력·장갑·페이즈 전부 회복하고 다시 배회"""
    cf = conf()
    e.update(hp=cf["hp"], mhp=cf["hp"], armor=cf["armor"], plates=[cf["plate_hp"]] * cf["armor"], phase=1, ph2=False, inv=0.0,
             mode="roam", roam_t=random.uniform(10, 16), st="idle", r=30, wp=None)
    e["cos"], e["rest"] = [], 1.4


# ================================================================= 피격 / 처치
def hit_wrap(old):
    def f(g, e, b, dmg):
        if e["kind"] != "kaiju":
            return old(g, e, b, dmg)
        e["_hit"] = True
        if e["mode"] in ("sleep", "roam", "return"):
            e["fl"] = 0.12
            G.spark(g, e["x"], e["y"] - 8, (200, 240, 255), 6)
            G.play("clang")
            return True
        if e["inv"] > 0 or e["st"] == "high":
            G.spark(g, e["x"], e["y"] - 8, (255, 255, 255), 6)
            G.play("clang")
            return False
        cf = conf()
        weak = e["st"] == "stun"
        if weak:
            dmg *= 2
        if e["armor"] > 0:                                         # 장갑판부터 깎인다
            i = e["armor"] - 1
            e["plates"][i] -= dmg
            e["hp"] -= max(1, int(dmg * cf["armor_chip"])) if dmg >= 2 else 0
            e["fl"] = 0.1
            G.spark(g, e["x"], e["y"] - 14, (190, 210, 240), 8)
            G.play("clang")
            G.ftext(g, f"장갑 -{dmg}", e["x"] + random.randint(-8, 8), e["y"] - 34, (190, 220, 255))
            if e["plates"][i] <= 0:
                e["armor"] -= 1
                shake(g, 0.4)
                G.play("boom")
                G.ftext(g, "장갑 파괴!", e["x"], e["y"] - 46, (150, 240, 255))
                if e["armor"] == 0:
                    enter_phase(g, e, 2)
            return True
        e["hp"] -= dmg
        e["fl"] = 0.12
        G.ftext(g, f"-{dmg}" + ("!!" if weak else ""), e["x"] + random.randint(-8, 8), e["y"] - 30,
                (255, 120, 120) if weak else (220, 245, 255))
        G.spark(g, e["x"], e["y"], (170, 230, 255), 8)
        G.play("hit")
        return True
    return f


def kill_wrap(old):
    def f(g, e):
        if e["kind"] != "kaiju":
            return old(g, e)
        cf = conf()
        g["kaiju_dying"] = dict(x=e["x"], y=e["y"], phase=e["phase"], t0=g["t"], an=e["an"], fx=e.get("_fx") or FX.new_fx(g["t"], e, g))
        g["kaiju_dead_t"] = g["t"]
        G.spark(g, e["x"], e["y"], (170, 230, 255), 40)
        g["rings"].append([e["x"], e["y"], 0.0, 160, (200, 245, 255)])
        G.play("boss")
        W.spawn_loot(g, e["x"], e["y"], cf["gold"], cf["parts"], True)
        G.gain_exp(g, cf["exp"], e["x"], e["y"] - 24)
        clear_hz(g)
        g["shake"] = 1.0
        G.toast(g, f"{NAME}를 쓰러뜨렸다! 얼어붙은 왕관이 부서진다", 5.0)
        if C.FX.get("autosave") and W.V.get("save"):
            W.V["save"](g, quiet=True)
    return f


# ================================================================= 서식지 (월드에 얼음 공터를 만든다)
def decorate(z):
    T = G.T
    w = next((q for q in z["warps"] if q["id"] == "w2"), z["warps"][0])
    cx = max(20, min(z["wt"] - 21, w["tx"] + 12))
    cy = max(20, min(z["ht"] - 21, w["ty"] - 10))
    R_ = conf()["nest_r"]
    ter, solid, ntile, water = z["ter"], z["solid"], z["ntile"], z["water"]
    area = {(cx + i, cy + j) for i in range(-R_, R_ + 1) for j in range(-R_, R_ + 1) if i * i + j * j <= (R_ - 2) ** 2}
    for nd in z["nodes"]:
        if nd["alive"] and (nd["tx"], nd["ty"]) in area:
            nd["alive"], nd["t"] = False, 1e9
    z["deco"][:] = [d for d in z["deco"] if d[0] == "warp" or (int(d[1]) // T, int(d[2]) // T) not in area]
    z["en"][:] = [e for e in z["en"] if (int(e["x"]) // T - cx) ** 2 + (int(e["y"]) // T - cy) ** 2 > (R_ + 2) ** 2]
    for t in area:
        solid.discard(t)
        ntile.discard(t)
        water.discard(t)
        if ter[t[1]][t[0]] in (1, 8):
            ter[t[1]][t[0]] = 0
    for px, py in PILLARS:                                          # 얼음 기둥 (포효를 막아 주는 엄폐물)
        for i in (0, 1):
            for j in (0, 1):
                solid.add((cx + px + i, cy + py + j))
                ntile.add((cx + px + i, cy + py + j))
    z["meta"]["kaiju"] = (cx, cy)
    z["en"].append(mk_kaiju(cx * T + 8, cy * T + 8))
    z["_kaiju"] = True


def nest_surface(R_):
    """서식지 바닥: 서리 덮인 땅, 얼음 균열, 얼어붙은 뼈 (한 번만 그려 둔다)"""
    T = G.T
    S = (R_ * 2 + 2) * T
    s = pygame.Surface((S, S), SC)
    c = S // 2
    rnd = random.Random(77)
    for i in range(60):
        a, r = rnd.random() * math.tau, rnd.random() ** 0.6 * (R_ - 1) * T
        x, y = c + math.cos(a) * r, c + math.sin(a) * r
        w, h = rnd.randint(14, 40), rnd.randint(8, 22)
        D.ellipse(s, (220, 236, 250, rnd.randint(40, 90)), (x - w // 2, y - h // 2, w, h))
    for i in range(14):                                             # 얼음 균열
        a = rnd.random() * math.tau
        x, y = c + math.cos(a) * rnd.uniform(10, 60), c + math.sin(a) * rnd.uniform(10, 60)
        pts = [(x, y)]
        for k in range(6):
            a += rnd.uniform(-0.6, 0.6)
            x += math.cos(a) * rnd.uniform(8, 18)
            y += math.sin(a) * rnd.uniform(8, 18)
            pts.append((x, y))
        D.lines(s, (150, 210, 245, 170), False, pts, 1)
    for i in range(9):                                              # 얼어붙은 뼈
        a, r = rnd.random() * math.tau, rnd.uniform(3, R_ - 3) * T
        x, y = int(c + math.cos(a) * r), int(c + math.sin(a) * r)
        D.line(s, (60, 64, 80, 255), (x - 6, y + 1), (x + 6, y - 1), 4)
        D.line(s, (232, 228, 214, 255), (x - 6, y), (x + 6, y - 2), 2)
        for ex in (-6, 6):
            D.circle(s, (232, 228, 214, 255), (x + ex, y - (1 if ex > 0 else 0)), 2)
    D.circle(s, (200, 230, 255, 60), (c, c), (R_ - 1) * T, 2)
    return s


def draw_pillar(surf, x, y, t):
    """얼음 기둥 (2x2칸): 길쭉한 결정 다발, 꼭대기가 푸르게 빛난다"""
    base = [(x - 14, y + 10), (x + 14, y + 10), (x + 10, y + 16), (x - 10, y + 16)]
    D.polygon(surf, (40, 60, 90), base)
    for i, (ox, h, w) in enumerate(((-7, 30, 7), (6, 38, 8), (0, 46, 9), (-11, 20, 5), (11, 24, 5))):
        bx, by = x + ox, y + 12
        pts = [(bx - w, by), (bx - w * 0.6, by - h * 0.85), (bx, by - h), (bx + w * 0.6, by - h * 0.85), (bx + w, by)]
        D.polygon(surf, (14, 12, 26), [(px, py + 1) for px, py in pts])
        D.polygon(surf, (120, 180, 230) if i % 2 else (150, 210, 245), pts)
        D.polygon(surf, (210, 240, 255), [pts[0], pts[1], pts[2], (bx - w * 0.2, by)])
        D.line(surf, (255, 255, 255), pts[1], pts[2], 1)
    FX.blit_gl(surf, x, y - 40, 14 + 2 * math.sin(t * 2), (120, 220, 255), 110)


def draw_nest(surf, g, cx, cy):
    n = (g.get("meta") or {}).get("kaiju")
    if not n:
        return
    T = G.T
    R_ = conf()["nest_r"]
    S = (R_ * 2 + 2) * T
    x0, y0 = n[0] * T + 8 - S // 2 - cx, n[1] * T + 8 - S // 2 - cy
    if x0 > G.W or y0 > G.H or x0 + S < 0 or y0 + S < 0:
        return
    if "nest" not in _S:
        _S["nest"] = nest_surface(R_)
    surf.blit(_S["nest"], (x0, y0))
    for px, py in PILLARS:
        draw_pillar(surf, (n[0] + px) * T + T - cx, (n[1] + py) * T + T - cy, g["t"])


# ================================================================= UI
def boss_bar_wrap(old):
    def f(screen, font, g, u):
        e = next((o for o in g["en"] if o["kind"] == "kaiju" and o["hp"] > 0 and o["mode"] == "fight"
                  and G.dist(g["x"], g["y"], o["x"], o["y"]) < 460), None)
        if e is None:
            return old(screen, font, g, u)
        SW = G.W * u
        bw = 190 * u
        x0 = (SW - bw) // 2
        col = PHASE_COL[e["phase"] - 1]
        G.plate(screen, x0 - 8 * u, 31 * u, bw + 16 * u, 24 * u, u)
        G.txt(screen, font, NAME + f"   PHASE {e['phase']}", SW // 2, 32 * u, col, True, u)
        D.rect(screen, G.INK, (x0, 44 * u, bw, 8 * u))
        wfill = max(0, (bw - 2 * u) * int(e["hp"]) // e["mhp"])
        D.rect(screen, G.lerp_c(col, (0, 0, 0), 0.45), (x0 + u, 45 * u, bw - 2 * u, 6 * u))
        D.rect(screen, col, (x0 + u, 45 * u, wfill, 6 * u))
        D.rect(screen, G.lerp_c(col, (255, 255, 255), 0.5), (x0 + u, 45 * u, wfill, 2 * u))
        D.rect(screen, G.INK, (x0 + int(bw * conf()["phase3"]), 44 * u, max(1, u), 8 * u))
        for i in range(conf()["armor"]):                          # 장갑판 표시
            px = x0 + bw + 12 * u + i * 9 * u
            alive = i < e["armor"]
            D.rect(screen, G.INK, (px - u, 43 * u, 8 * u, 10 * u))
            D.rect(screen, (150, 165, 200) if alive else (40, 50, 70), (px, 44 * u, 6 * u, 8 * u))
            if alive:
                k = max(0.0, e["plates"][i] / conf()["plate_hp"])
                D.rect(screen, (220, 235, 255), (px, 44 * u + int(8 * u * (1 - k)), 6 * u, max(u, int(8 * u * k))))
        if e["st"] == "stun":
            G.txt(screen, font, "약점 노출! 피해 2배", SW // 2, 53 * u, (255, 240, 150), True, u)
        elif e["armor"] > 0:
            G.txt(screen, font, "등의 장갑판을 깨라", SW // 2, 53 * u, (190, 220, 255), True, u)
    return f


def map_wrap(old):
    def f(screen, font, g, u):
        old(screen, font, g, u)
        meta = g.get("meta") or {}
        if g["zid"] != O.WID or "kaiju" not in meta:
            return
        try:
            SW, SH = G.W * u, G.H * u
            pw, ph = int(SW * 0.94), 246 * u
            px, py = (SW - pw) // 2, (SH - ph) // 2
            kx = min((pw / u - 24 - 150) / g["wt"], (ph / u - 38) / g["ht"])
            dx, dy = meta["kaiju"]
            if (dx, dy) not in W.mm_base(g)[2]:
                return
            x, y = px + 12 * u + int((dx + 0.5) * kx * u), py + 22 * u + int((dy + 0.5) * kx * u)
            D.polygon(screen, G.INK, [(x - 3 * u, y - 5 * u), (x + 3 * u, y - 5 * u), (x, y)])
            D.circle(screen, G.INK, (x, y - 6 * u), int(4.4 * u))
            D.circle(screen, (110, 210, 255), (x, y - 6 * u), int(3.4 * u))
            D.circle(screen, (235, 250, 255), (x, y - 6 * u), max(1, int(1.4 * u)))
            G.txt(screen, font, "탈라소르의 서식지", x + 6 * u, y - 8 * u, (170, 225, 255), u=u)
        except Exception:
            G.v9_log("kaiju-map")
    return f


# ================================================================= 설치
def install(g_mod, cfg, boss_mod, world_mod, open_mod, ui_mod, roster_mod):
    global G, C, V, W, O, UI, R
    G, C, V, W, O, UI, R = g_mod, cfg, boss_mod, world_mod, open_mod, ui_mod, roster_mod
    FX.G = G
    try:
        import v9_pfx
        FX.BREATH_DRAW = lambda surf, x, y, a, t: v9_pfx.breath_draw(surf, x, y, a, t, "kbreath_")
    except Exception:
        pass
    G.AGGRO["kaiju"] = 9999
    G.FOE_NAME["kaiju"] = "탈라소르"
    old_foe, old_hit, old_de, old_kill = G.foe_ai, G.hit_foe, G.draw_enemy, G.kill
    old_update, old_zone, old_load = G.update, G.build_zone, G.load_zone

    def foe_ai(g, e, dt, d, ux, uy):
        if e["kind"] == "kaiju":
            try:
                return kaiju_ai(g, e, dt)
            except Exception:
                G.v9_log("kaiju-ai")
                return False
        return old_foe(g, e, dt, d, ux, uy)

    def draw_enemy(surf, e, cx, cy, t, g):
        if e["kind"] == "kaiju":
            return FX.draw_kaiju(surf, e, cx, cy, t, g)
        return old_de(surf, e, cx, cy, t, g)

    def update(g, inp, dt):
        old_update(g, inp, dt)
        if g["mode"] != "play" or g["tr"] or g.get("zid") != O.WID:
            return
        try:
            for e in g["en"]:                                       # 기본 AI는 360px 넘게 떨어지면 멈추므로 싸우는 중이면 따로 돌린다
                if e["kind"] == "kaiju" and e["hp"] > 0 and e["mode"] in ("fight", "return") and G.dist(g["x"], g["y"], e["x"], e["y"]) > 360:
                    e["an"] += dt
                    kaiju_ai(g, e, dt)
            n = nest(g)
            dead = g.get("kaiju_dead_t")
            if n and dead is not None and not any(o["kind"] == "kaiju" for o in g["en"]):
                if g["t"] - dead > conf()["respawn"] and G.dist(g["x"], g["y"], n[0], n[1]) > 420:
                    g["en"].append(mk_kaiju(n[0], n[1]))
                    g["kaiju_dead_t"] = None
        except Exception:
            G.v9_log("kaiju-update")

    def build_zone(zid):
        z = old_zone(zid)
        if zid == O.WID and z.get("meta") and not z.get("_kaiju"):
            try:
                decorate(z)
            except Exception:
                G.v9_log("kaiju-decorate")
        return z

    def load_zone(g, zid, tx, ty):
        old_load(g, zid, tx, ty)
        g["kaiju_dying"] = None
        if g.get("zid") == O.WID:
            dead = g.get("kaiju_dead_t")
            if dead is not None and g["t"] - dead <= conf()["respawn"]:   # 쓰러뜨린 뒤 재생성 전이면 나오지 않는다
                g["en"] = [e for e in g["en"] if e["kind"] != "kaiju"]

    old_draw_hz = V.draw_hz

    def draw_hz(surf, g, cx, cy):
        if g.get("zid") == O.WID:
            try:
                draw_nest(surf, g, cx, cy)
                FX.draw_death(surf, g, cx, cy)
            except Exception:
                G.v9_log("kaiju-nest")
        old_draw_hz(surf, g, cx, cy)
    V.draw_hz = draw_hz

    G.foe_ai, G.draw_enemy = foe_ai, draw_enemy
    G.hit_foe, G.kill = hit_wrap(old_hit), kill_wrap(old_kill)
    G.update, G.build_zone, G.load_zone = update, build_zone, load_zone
    UI.boss_bar = boss_bar_wrap(UI.boss_bar)
    if hasattr(UI, "draw_map"):
        UI.draw_map = map_wrap(UI.draw_map)
