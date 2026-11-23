"""v9 화룡 모듈 (v9_dragon.py)
 - 선택형 슈퍼보스 '화룡 이그니스(Ignis)'와 전용 보스방 '화룡의 용암 둥지'를 추가한다.
 - 입구: 월드 남동쪽 '남동 이정표' 워프포인트 5칸 동쪽의 흑요석 문 (불타는 화룡 해골 문)
 - 보스방 테마: 현무암 바닥 + 끓는 용암 웅덩이 + 달아오르는 균열 + 금화 더미/뼈 + 불씨 입자 + 전용 BGM + 붉은 열기
 - 3페이즈: 화염 탄막 / 화염 숨결(약점) / 돌진(약점) / 용암 분출 / 유성 / 용암 줄무늬 / 화염 폭발
   입을 벌릴 때(숨결)와 돌진 직후 기절했을 때는 부메랑 피해 2배
 - 수치는 config.py 에 DRAGON 사전을 추가해 바꾼다 (없으면 기본값):
     DRAGON = dict(hp=170, phases=(0.66, 0.33), gold=250, exp=300, parts=8, transition_sec=1.8, require_keys=0)
v9_open.install 뒤, 가장 마지막에 설치한다:
    import v9_dragon
    v9_dragon.install(G, C, v9_boss, v9_world, v9_open, v9_ui)
"""
import array
import math
import random

import pygame

D = pygame.draw
SC = pygame.SRCALPHA
G = C = V = W = O = UI = None
ZID = "boss_d"
NAME, SUB = "화룡 이그니스 (Ignis)", "잿더미 위에 군림하는 불꽃의 용"
DEFAULT = dict(hp=170, phases=(0.66, 0.33), gold=250, exp=300, parts=8, transition_sec=1.8, require_keys=0)
PHASE_COL = ((255, 160, 80), (255, 110, 50), (255, 60, 60))
HOARDS = ((2, 21), (31, 21), (3, 3))
BONES = ((12, 5), (22, 4), (6, 17), (27, 17))
_R = {}
_S = {}


def conf():
    d = dict(DEFAULT)
    d.update(getattr(C, "DRAGON", {}) or {})
    return d


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


# ================================================================= 보스 데이터
def mk_dragon(x, y):
    hp = conf()["hp"]
    return dict(kind="dragon", x=x, y=y, hx=x, hy=y, hp=hp, mhp=hp, fl=0, kb=0, kx=0, ky=0, ag=True, hb=10, r=22,
                an=0.0, al=0, mv=False, st="idle", stt=0.0, phase=1, ph2=False, inv=0.0, fc=1, sg=1, lz=0.0)


# ================================================================= 패턴
def dp_fan(g, e):
    ph = e["phase"]
    e["st"] = "spit"
    for r in range(2 + ph):
        a, n = V.angto(g, e), 3 + 2 * ph
        for i in range(n):
            V.fire(g, e, a + (i - (n - 1) / 2) * 0.16, 115 + 12 * r, 3, 3.2)
        G.play("shoot")
        yield 0.5 - 0.04 * ph
    e["st"] = "idle"
    yield 0.3


def dp_breath(g, e):
    ph = e["phase"]
    a0, sweep = V.angto(g, e), 0.85 + 0.15 * ph
    dr = random.choice((-1, 1))
    e["st"] = "breath_w"
    for s in (-1, 1):
        V.add_hz(g, "beam", 0.9, 0.0, x=e["x"], y=e["y"], a=a0 + s * sweep, len=300, w=2, dmg=False)
    G.play("gate")
    yield V.tm(0.9)
    e["st"] = "breath"
    n = int((1.5 + 0.3 * ph) / 0.06)
    for i in range(n):
        a = a0 + dr * (-sweep + 2 * sweep * i / n)
        e["lz"] = a
        if i % 6 != 5:
            V.fire(g, e, a, 150 + 15 * ph, 3, 2.2)
        if ph >= 3 and i % 3 == 0:
            V.fire(g, e, a + dr * 0.5, 120, 0, 3.0)
        if i % 4 == 0:
            G.play("shoot")
        yield 0.06
    e["st"] = "idle"
    yield 0.5


def dp_charge(g, e):
    ph = e["phase"]
    x0, y0, x1, y1 = V.bounds(g)
    for k in range(1 + (ph >= 2) + (ph >= 3)):
        a = V.angto(g, e)
        e["fc"], e["st"], e["lz"] = (1 if math.cos(a) >= 0 else -1), "wind", a
        V.add_hz(g, "beam", 0.8, 0.0, x=e["x"], y=e["y"], a=a, len=360, w=3, dmg=False)
        G.play("gate")
        yield V.tm(0.8)
        e["st"] = "dash"
        t, sp = 0.0, 300 + 30 * ph
        while t < 0.55:
            e["x"] = min(max(e["x"] + math.cos(a) * sp * 0.03, x0 + 22), x1 - 22)
            e["y"] = min(max(e["y"] + math.sin(a) * sp * 0.03, y0 + 22), y1 - 24)
            G.spark(g, e["x"], e["y"], (255, 150, 60), 2)
            t += 0.03
            yield 0.03
        if ph >= 2:
            G.ring(g, e["x"], e["y"], 12, V.bs(80), random.random() * 6.283)
        e["st"] = "stun"                                        # 돌진 직후 기절: 약점
        yield 0.9 if k == 0 else 0.6
    e["st"] = "idle"
    yield 0.2


def dp_erupt(g, e):
    ph = e["phase"]
    e["st"] = "roar"
    for i in range(4 + 2 * ph):
        x, y = g["x"], g["y"]
        V.add_hz(g, "circle", 0.9, 0.45, x=x, y=y, r=22)
        if ph >= 2 and i % 2 == 1:
            for k in range(4):
                a = k * 1.5708 + 0.785
                V.add_hz(g, "circle", 0.9, 0.45, x=x + math.cos(a) * 50, y=y + math.sin(a) * 50, r=17)
        G.play("switch")
        yield 0.35
    e["st"] = "idle"
    yield 1.0


def dp_meteor(g, e):
    ph = e["phase"]
    e["st"] = "roar"
    yield from V.meteors(g, e, 11 + 4 * ph, max(0.18, 0.3 - 0.04 * ph))
    e["st"] = "idle"
    yield 0.7


def dp_ring(g, e):
    ph = e["phase"]
    for r in range(2 + ph // 2):
        V.ring_gap(g, e, 22 + 2 * ph, 95 + 8 * r, V.angto(g, e) + random.uniform(-0.9, 0.9), 0.34, 3)
        G.play("shoot")
        yield 0.85
    yield 0.3


def dp_lanes(g, e):
    x0, y0, x1, y1 = V.bounds(g)
    for y in random.sample(range(int(y0) + 30, int(y1) - 30, 44), 4):
        V.add_hz(g, "rect", 1.2, 0.6, x0=x0, x1=x1, y0=y - 14, y1=y + 14)
    G.play("gate")
    yield V.tm(1.2) + 0.9
    for x in random.sample(range(int(x0) + 30, int(x1) - 30, 52), 5):
        V.add_hz(g, "rect", 1.0, 0.6, x0=x - 14, x1=x + 14, y0=y0, y1=y1)
    yield V.tm(1.0) + 0.9


def dp_summon(g, e):
    e["st"] = "roar"
    G.play("portal")
    yield V.tm(0.6)
    for _ in range(2):
        x, y = G.free_spot(g, e["x"], e["y"], 50, 130, 6)
        b = G.mk_foe("bomber", x, y, True)
        b["nodrop"] = True
        g["en"].append(b)
        G.spark(g, x, y, (255, 170, 80), 8)
    e["st"] = "idle"
    yield 1.2


def dp_nova(g, e):
    e["st"] = "roar"
    V.add_hz(g, "circle", 1.4, 0.5, x=e["x"], y=e["y"], r=100)
    G.play("boss")
    yield V.tm(1.4) + 0.6
    for r in range(3):
        V.ring_gap(g, e, 28, 90 + 10 * r, V.angto(g, e) + random.uniform(-1, 1), 0.3, 3)
        G.play("shoot")
        yield 0.6
    e["st"] = "idle"
    yield 0.4


def dp_spiral(g, e):
    a, dr = random.random() * 6.283, random.choice((-1, 1))
    for i in range(int(3.2 / 0.08)):
        for k in range(3):
            V.fire(g, e, a + k * 2.0944, 95, 0, 5.0)
        a += dr * 0.34
        if i % 4 == 0:
            G.play("shoot")
        yield 0.08


ALWAYS = lambda g, e: True
POOLS = {1: [("fan", dp_fan, 3, ALWAYS), ("breath", dp_breath, 2, ALWAYS), ("erupt", dp_erupt, 2, ALWAYS),
             ("charge", dp_charge, 2, ALWAYS), ("ring", dp_ring, 1, ALWAYS)],
         2: [("fan", dp_fan, 2, ALWAYS), ("breath", dp_breath, 3, ALWAYS), ("erupt", dp_erupt, 3, ALWAYS),
             ("charge", dp_charge, 3, ALWAYS), ("ring", dp_ring, 2, ALWAYS), ("meteor", dp_meteor, 2, ALWAYS),
             ("lanes", dp_lanes, 2, ALWAYS),
             ("summon", dp_summon, 1, lambda g, e: len(V.foes_alive(g, "bomber")) < 2)],
         3: [("spiral", dp_spiral, 2, ALWAYS), ("breath", dp_breath, 3, ALWAYS), ("charge", dp_charge, 3, ALWAYS),
             ("meteor", dp_meteor, 3, ALWAYS), ("lanes", dp_lanes, 2, ALWAYS), ("erupt", dp_erupt, 3, ALWAYS),
             ("nova", dp_nova, 2, ALWAYS), ("fan", dp_fan, 2, ALWAYS), ("ring", dp_ring, 2, ALWAYS)]}
REST = (1.5, 1.1, 0.7)


def enter_phase(g, e, p):
    e["phase"], e["ph2"], e["inv"] = p, p >= 2, conf()["transition_sec"]
    V.reset_cos(g, e, 1.2)
    e["st"] = "roar"
    g["hz"], g["shots"], g["met"] = [], [], []
    g["rings"].append([e["x"], e["y"], 0.0, 170, PHASE_COL[p - 1]])
    G.spark(g, e["x"], e["y"], PHASE_COL[p - 1], 30)
    g["shake"] = 0.8
    G.play("boss")
    G.toast(g, ("화룡이 날개를 활짝 펼친다!", "화룡이 분노했다! 용암이 끓어오른다!")[p - 2], 3.0)


def dragon_ai(g, e, dt):
    if not (g["lock"] and g["intro"] <= 0):
        return False
    V.ensure(e)
    d = G.dist(g["x"], g["y"], e["x"], e["y"])
    ux, uy = (g["x"] - e["x"]) / (d or 1), (g["y"] - e["y"]) / (d or 1)
    if e["st"] not in ("dash", "wind") and abs(ux) > 0.25:
        e["fc"] = 1 if ux > 0 else -1
    th, fr = conf()["phases"], e["hp"] / e["mhp"]
    if e["phase"] < 3 and fr <= th[e["phase"] - 1]:
        enter_phase(g, e, e["phase"] + 1)
    e["inv"] = max(0.0, e["inv"] - dt)
    if e["inv"] > 0:
        return False
    if e["st"] == "roar" and not e["cos"]:
        e["st"] = "idle"
    if not e["cos"]:                                            # 패턴 사이: 플레이어 주위를 선회
        if d < 70:
            vx, vy, sp = -ux, -uy, 40
        elif d > 135:
            vx, vy, sp = ux, uy, 30
        else:
            vx, vy, sp = -uy * e["sg"], ux * e["sg"], 26
        x0, y0, x1, y1 = V.bounds(g)
        e["x"] = min(max(e["x"] + vx * sp * dt, x0 + 22), x1 - 22)
        e["y"] = min(max(e["y"] + vy * sp * dt, y0 + 22), y1 - 24)

    def rest():
        e["sg"] = random.choice((-1, 1))
        return V.cdm(REST[e["phase"] - 1] * random.uniform(0.85, 1.15))
    V.sched(g, e, dt, POOLS[e["phase"]], rest)
    return not e["cos"]


def hit_wrap(old):
    def f(g, e, b, dmg):
        if e["kind"] != "dragon":
            return old(g, e, b, dmg)
        e["ag"] = True
        if e["inv"] > 0 or not (g["lock"] and g["intro"] <= 0):
            G.spark(g, e["x"], e["y"] - 8, (255, 255, 255), 6)
            G.play("clang")
            return False
        weak = e["st"] in ("breath", "stun")
        if weak:
            dmg *= 2
        e["hp"] -= dmg
        e["fl"] = 0.12
        G.ftext(g, f"-{dmg}" + ("!!" if weak else ""), e["x"] + random.randint(-8, 8), e["y"] - 30,
                (255, 100, 90) if weak else (255, 240, 150))
        G.spark(g, e["x"], e["y"], (255, 190, 90), 8)
        G.play("hit")
        return True
    return f


def kill_wrap(old):
    def f(g, e):
        if e["kind"] != "dragon":
            return old(g, e)
        cf = conf()
        G.spark(g, e["x"], e["y"], (255, 170, 70), 40)
        g["rings"].append([e["x"], e["y"], 0.0, 160, (255, 200, 100)])
        G.play("boss")
        G.spawn_loot(g, e["x"], e["y"], cf["gold"], cf["parts"], True)
        G.gain_exp(g, cf["exp"], e["x"], e["y"] - 24)
        for o in g["en"]:
            if o is not e and o["kind"] == "bomber":
                o["hp"] = 0
        G.clear_arena(g)
        g["hz"], g["shots"], g["met"] = [], [], []
        g["shake"] = 1.0
        G.toast(g, "화룡 이그니스를 쓰러뜨렸다! 중앙의 전송문으로 돌아갈 수 있다", 5.0)
        if C.FX.get("autosave") and W.V.get("save"):
            W.V["save"](g, quiet=True)
    return f


# ================================================================= 보스방 생성
def build_arena_dragon():
    T = G.T
    sp = G.ZONES[ZID]
    wt, ht = sp["size"]
    rng = random.Random(777)
    solid = set()
    G.ring_(solid, 0, 0, wt - 1, ht - 1)
    ter = [[0] * wt for _ in range(ht)]
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
    for px_, py_ in ((8, 7), (25, 7), (8, 15), (25, 15)):       # 현무암 기둥
        for i in (0, 1):
            for j in (0, 1):
                solid.add((px_ + i, py_ + j))
    lava = set()
    for cx_, cy_, rx, ry in ((4.5, 11, 2.2, 3.6), (29.5, 11, 2.2, 3.6), (12, 20, 2.4, 1.5), (22, 20, 2.4, 1.5)):
        for y in range(1, 23):
            for x in range(1, wt - 1):
                if ((x - cx_) / rx) ** 2 + ((y - cy_) / ry) ** 2 < 1 and (x, y) not in solid:
                    lava.add((x, y))
    solid |= lava
    fn = G.fractal(rng, 6, 3, wt, ht)
    shade = [[fn(x, y) for x in range(wt)] for y in range(ht)]
    return dict(solid=solid, nodes=[], ntile=set(), houses={}, pz=[], en=[mk_dragon(17 * T + 8, 7 * T + 8)], ter=ter,
                water=set(lava), shade=shade, rs=[], npcs=[], spec=sp, tgate=set(), core=None, vil=None, portals=[],
                exits=[], wt=wt, ht=ht, zreg=sp["reg"], deco=deco, arena="dragon")


# ================================================================= 월드: 화룡의 문
def decorate_world(z):
    T = G.T
    w = next((q for q in z["warps"] if q["id"] == "w3"), z["warps"][-1])
    cx, cy = w["tx"] + 5, w["ty"]
    ter, solid, ntile, water = z["ter"], z["solid"], z["ntile"], z["water"]
    area = {(cx + i, cy + j) for i in range(-4, 5) for j in range(-4, 5) if i * i + j * j <= 18}
    for nd in z["nodes"]:
        if nd["alive"] and (nd["tx"], nd["ty"]) in area:
            nd["alive"], nd["t"] = False, 1e9
    z["deco"][:] = [d for d in z["deco"] if d[0] == "warp" or (int(d[1]) // T, int(d[2]) // T) not in area]
    z["en"][:] = [e for e in z["en"] if abs(int(e["x"]) // T - cx) > 6 or abs(int(e["y"]) // T - cy) > 6]
    for t in area:
        solid.discard(t)
        ntile.discard(t)
        water.discard(t)
        if ter[t[1]][t[0]] in (1, 8):
            ter[t[1]][t[0]] = 0
    for sx in (cx - 2, cx + 2):                                 # 흑요석 첨탑 (통과 불가)
        solid.add((sx, cy))
        ntile.add((sx, cy))
    z["portals"].append(dict(x=cx * T + 8, y=cy * T + 8, to=ZID, at=(17, 26), boss=True))
    z["meta"]["dragon"] = (cx, cy)
    G.ZONES[O.WID]["lair"] = (cx - 1, cy - 2, cx + 1, cy, "e", 3)      # 보스방 클리어 후 돌아올 위치 = 문 바로 아래
    z["_dragon"] = True


def glow(r, col, a):
    return W.glow(r, col, a)


def draw_world_gate(surf, g, camx, camy):
    meta = g.get("meta") or {}
    if "dragon" not in meta:
        return
    T, t = G.T, g["t"]
    X, Y = meta["dragon"][0] * T + 8 - camx, meta["dragon"][1] * T + 8 - camy
    if X < -90 or X > G.W + 90 or Y < -90 or Y > G.H + 90:
        return
    surf.blit(glow(64, (30, 10, 8), 170), (X - 64, Y - 64))                    # 그을린 땅
    for i in range(10):                                                         # 갈라진 틈의 용암 빛
        a = i * 0.628 + 0.3
        c = lerp((120, 40, 24), (255, 140, 44), 0.3 + 0.3 * math.sin(t * 2 + i))
        p1 = (X + math.cos(a) * 14, Y + math.sin(a) * 14)
        p2 = (X + math.cos(a + 0.2) * (30 + i % 3 * 8), Y + math.sin(a + 0.2) * (30 + i % 3 * 8))
        D.line(surf, c, p1, p2, 1)
    for sx in (X - 32, X + 32):                                                 # 흑요석 첨탑
        D.polygon(surf, (30, 22, 38), [(sx - 7, Y + 9), (sx - 4, Y - 30), (sx, Y - 46), (sx + 4, Y - 30), (sx + 7, Y + 9)])
        D.polygon(surf, (62, 48, 78), [(sx, Y - 46), (sx + 4, Y - 30), (sx + 7, Y + 9), (sx, Y + 9)])
        for k in range(3):
            c = lerp((120, 40, 24), (255, 150, 50), 0.5 + 0.4 * math.sin(t * 3 + k + sx))
            surf.fill(c, (sx - 1, Y - 24 + k * 10, 2, 5))
        fl = int(math.sin(t * 12 + sx) * 2)
        surf.blit(glow(24, (255, 160, 70), 70), (sx - 24, Y - 56))
        D.circle(surf, (255, 120, 50), (sx, Y - 50), 4 + fl)
        D.circle(surf, (255, 210, 100), (sx, Y - 50), 2)
    bone = (234, 218, 180)
    for s in (-1, 1):                                                           # 문 위로 휘어진 뿔
        pts = [(X + s * 32, Y - 46), (X + s * 26, Y - 58), (X + s * 15, Y - 64), (X + s * 6, Y - 60)]
        D.lines(surf, bone, False, pts, 3)
    D.circle(surf, bone, (X, Y - 56), 6)                                        # 용의 해골
    surf.fill(bone, (X - 4, Y - 51, 8, 4))
    for ex in (X - 3, X + 2):
        surf.fill((255, 130, 50), (ex, Y - 58, 2, 3))
    for i in range(8):                                                          # 피어오르는 불씨
        px = X - 30 + (i * 37 + int(t * 20)) % 60
        py = Y + 6 - (t * 18 + i * 11) % 52
        surf.fill((255, 170, 70), (int(px), int(py), 1, 1))
    req = conf()["require_keys"]
    if g["keys"] < req:                                                         # 봉인 표시
        D.line(surf, (255, 70, 60), (X - 8, Y - 8), (X + 8, Y + 8), 2)
        D.line(surf, (255, 70, 60), (X - 8, Y + 8), (X + 8, Y - 8), 2)


# ================================================================= 보스방 그리기
def draw_arena_floor(surf, g, cx, cy):
    T, t = G.T, g["t"]
    solid, water, reg = g["solid"], g["water"], G.REGIONS[g["zreg"]]
    dr = next((o for o in g["en"] if o["kind"] == "dragon"), None)
    heat = dr["phase"] if dr else 1
    tx0, ty0 = cx // T, cy // T
    for ty in range(ty0, min(ty0 + G.H // T + 2, g["ht"])):
        for tx in range(tx0, min(tx0 + G.W // T + 2, g["wt"])):
            px, py, h, p = tx * T - cx, ty * T - cy, G.hsh(tx, ty), (tx, ty)
            if p in water:                                                      # 끓는 용암
                surf.fill((196, 58, 18), (px, py, T, T))
                for i in range(3):
                    w_ = 4 + (h >> i) % 6
                    surf.fill((255, 150, 48), (px + (h >> (i + 1)) % (T - w_), py + int((t * 9 + h * 3 + i * 6) % T), w_, 1))
                if h % 4 == 0:
                    surf.fill((255, 226, 120), (px + h % 12 + 2, py + int((t * 6 + h) % T), 2, 1))
                for dx, dy, rc in ((0, -1, (px, py, T, 2)), (0, 1, (px, py + T - 2, T, 2)),
                                   (-1, 0, (px, py, 2, T)), (1, 0, (px + T - 2, py, 2, T))):
                    if (tx + dx, ty + dy) not in water:
                        surf.fill((52, 26, 28), rc)
            elif p in solid:
                if p in G.ARENA_DOOR and g["lock"]:                             # 마그마 봉인
                    c = lerp((170, 60, 24), (255, 180, 70), 0.5 + 0.5 * math.sin(t * 8 + tx))
                    surf.fill((60, 22, 18), (px, py, T, T))
                    for i in range(3):
                        surf.fill(c, (px + 2 + i * 5, py + 1, 2, T - 2))
                    surf.fill(c, (px, py + 7, T, 2))
                    continue
                w = reg["wall"]
                surf.fill(w, (px, py, T, T))
                surf.fill(G.adj(w, 22), (px, py, T, 2))
                surf.fill(G.adj(w, -24), (px, py + 12, T, 4))
                if h % 4 == 0:
                    surf.fill(G.adj(w, -14), (px + 2 + h % 8, py + 4 + h % 6, 4, 1))
                if h % 6 == 1:
                    rc = lerp(w, (255, 120, 40), 0.35 + 0.35 * math.sin(t * 2 + tx))
                    surf.fill(rc, (px + 7, py + 4, 2, 5))
                    surf.fill(rc, (px + 5, py + 6, 6, 1))
            else:
                col = G.adj(reg["floor"] if g["shade"][ty][tx] > 0.5 else reg["floor2"], (h % 5 - 2) * 2)
                if any((tx + i, ty + j) in water for i, j in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                    col = lerp(col, (150, 56, 28), 0.4)                         # 용암 옆 바닥은 달아올라 있다
                surf.fill(col, (px, py, T, T))
                if h % 9 == 0:                                                  # 달아오르는 균열 (페이즈가 오를수록 밝다)
                    c = lerp((120, 44, 26), (255, 140, 44), (0.25 + 0.2 * heat) * (0.6 + 0.4 * (0.5 + 0.5 * math.sin(t * 2 + h))))
                    surf.fill(c, (px + 2, py + 6, 5, 1))
                    surf.fill(c, (px + 6, py + 7, 4, 1))
                    surf.fill(c, (px + 9, py + 8, 1, 4))
                    surf.fill(c, (px + 4, py + 5, 1, 2))
                elif h % 5 == 0:
                    surf.fill(G.adj(col, -22), (px + 3 + h % 8, py + 9, 3, 2))
                elif h % 13 == 0:
                    surf.fill(G.adj(col, 18), (px + 5, py + 4, 2, 1))
    for hx, hy in HOARDS:                                                       # 용의 보물 더미
        x, y = hx * T + 8 - cx, hy * T + 8 - cy
        if -20 < x < G.W + 20 and -20 < y < G.H + 20:
            D.polygon(surf, (150, 104, 30), [(x - 14, y + 8), (x - 8, y - 4), (x, y - 10), (x + 8, y - 4), (x + 14, y + 8)])
            D.polygon(surf, (214, 166, 50), [(x - 12, y + 7), (x - 7, y - 3), (x, y - 9), (x + 3, y + 2)])
            D.polygon(surf, (250, 214, 90), [(x - 7, y - 3), (x, y - 9), (x + 5, y - 4), (x - 1, y)])
            for i in range(5):
                surf.fill((255, 240, 150), (x - 10 + i * 5, y + 1 + (i * 3) % 5, 2, 1))
            if int(t * 2 + hx) % 3 == 0:
                surf.fill((255, 255, 255), (x - 3 + int(hx) % 7, y - 8, 1, 1))
    for bx, by in BONES:                                                        # 뼈 무더기
        x, y = bx * T + 8 - cx, by * T + 8 - cy
        if -20 < x < G.W + 20 and -20 < y < G.H + 20:
            bone = (226, 210, 174)
            for i in range(3):
                D.arc(surf, bone, (x - 8 + i * 4, y - 4, 10, 10), 0.2, 2.9, 1)
            D.line(surf, bone, (x - 10, y + 5), (x + 10, y + 5), 2)
            D.circle(surf, bone, (x + 9, y), 3)
            surf.fill((40, 20, 20), (x + 8, y - 1, 1, 2))


def draw_arena_wrap(old):
    def f(surf, g, cx, cy):
        if g.get("arena") == "dragon":
            try:
                draw_arena_floor(surf, g, cx, cy)
            except Exception:
                G.v9_log("dragon-floor")
            old(surf, g, cx, cy)
            return
        old(surf, g, cx, cy)
        if g.get("zid") == O.WID:
            try:
                draw_world_gate(surf, g, cx, cy)
            except Exception:
                G.v9_log("dragon-gate")
    return f


def draw_wrap(old):
    def f(surf, g):
        old(surf, g)
        if g.get("zid") == ZID and g.get("mode") == "play":     # 붉은 열기
            try:
                dr = next((o for o in g["en"] if o["kind"] == "dragon"), None)
                ph = dr["phase"] if dr else 1
                if "tint" not in _R:
                    _R["tint"] = pygame.Surface((G.W, G.H))
                    _R["tint"].fill((255, 70, 20))
                _R["tint"].set_alpha(int(10 + 5 * ph + 6 * math.sin(g["t"] * 3)))
                surf.blit(_R["tint"], (0, 0))
            except Exception:
                G.v9_log("dragon-tint")
    return f


# ================================================================= 화룡 그리기
def draw_dragon(surf, e, cx, cy, t, g):
    x, y = int(e["x"]) - cx, int(e["y"]) - cy
    ph, fc, st = e["phase"], e["fc"], e["st"]
    hurt = e["fl"] > 0 or (e["inv"] > 0 and int(t * 20) % 2)
    y0 = y + int(math.sin(e["an"] * 2.4) * 2)
    if "sh" not in _S:
        _S["sh"] = pygame.transform.scale(G.SHADOW, (64, 14))
    surf.blit(_S["sh"], (x - 32, y + 24))
    pal = ((176, 46, 38), (190, 52, 34), (210, 56, 30))[ph - 1]
    base, dark, belly, hi = pal, G.adj(pal, -56), (238, 186, 110), G.adj(pal, 48)
    wing, wing_hi = G.adj(pal, -70), (236, 120, 70)
    if hurt:
        base = dark = belly = hi = wing = wing_hi = (255, 244, 236)

    def P(dx, dy):
        return (x + dx * fc, y0 + dy)
    flap = math.sin(e["an"] * (11 if st == "dash" else 5))

    def draw_wing(ox, oy, col):
        root, el = (-4 + ox, -8 + oy), (-20 + ox, -30 + flap * 8 + oy)
        tip, m1, m2 = (-48 + ox, -12 + flap * 14 + oy), (-40 + ox, 6 + flap * 8 + oy), (-24 + ox, 2 + oy)
        D.polygon(surf, col, [P(*root), P(*el), P(*tip), P(*m1), P(*m2)])
        D.line(surf, wing_hi, P(*el), P(*m1), 1)
        D.line(surf, wing_hi, P(*el), P(*m2), 1)
        D.lines(surf, dark, False, [P(*root), P(*el), P(*tip)], 2)
    draw_wing(8, -4, G.adj(wing, -16))                           # 먼 쪽 날개
    for i in range(10):                                          # 꼬리
        px, py = -18 - i * 6.5, 6 + math.sin(t * 3 - i * 0.55) * (1.5 + i * 0.7)
        r = max(2, int(7 - i * 0.55))
        D.circle(surf, dark if i % 2 else base, P(px, py), r)
        if i % 2 == 0 and i < 8:
            D.polygon(surf, hi, [P(px - 2, py - r), P(px + 1, py - r - 4), P(px + 3, py - r)])
        if i == 9 and ph >= 3:
            D.circle(surf, (255, 140, 50), P(px - 4, py), 4 + int(math.sin(t * 12) * 1.5))
    D.ellipse(surf, dark, (x - 23, y0 - 12, 46, 28))             # 몸통
    D.ellipse(surf, base, (x - 22, y0 - 13, 44, 26))
    D.ellipse(surf, belly, (x - 14, y0 + 1, 28, 10))
    for i in range(4):
        D.line(surf, G.adj(belly, -34), (x - 10 + i * 7, y0 + 2), (x - 10 + i * 7, y0 + 9))
    for i in range(5):
        D.arc(surf, hi, (x - 18 + i * 7, y0 - 12, 8, 7), 0.3, 2.8, 1)
    for lx in (x - 12, x + 6):                                   # 다리와 발톱
        surf.fill(dark, (lx, y0 + 11, 5, 7))
        surf.fill((236, 222, 190), (lx, y0 + 17, 2, 2))
        surf.fill((236, 222, 190), (lx + 3, y0 + 17, 2, 2))
    if ph >= 2:                                                  # 몸에 번지는 용암 균열
        for k in range(6):
            c = lerp((150, 50, 24), (255, 170, 60), 0.4 + 0.4 * math.sin(t * 4 + k))
            D.line(surf, c, (x - 14 + k * 6, y0 - 7), (x - 12 + k * 6, y0 + 3), 1)
    for i in range(5):                                           # 목
        f = i / 4
        D.circle(surf, base if i % 2 else dark, P(14 + f * 16, -4 - f * 13 + math.sin(t * 2 + i) * 0.8), int(7 - f * 2))
    op = 6 if st in ("breath", "breath_w", "roar") else 3 if st in ("spit", "wind") else 0
    D.polygon(surf, base, [P(28, -27), P(50, -21), P(49, -17), P(30, -14)])        # 머리
    if op:
        D.polygon(surf, (255, 120, 40), [P(30, -14), P(49, -17), P(49, -17 + op), P(30, -9)])
    D.polygon(surf, dark, [P(30, -14), P(49, -17 + op), P(46, -12 + op), P(30, -9)])
    D.circle(surf, base, P(32, -21), 8)
    for k in range(3):
        tx_, ty_ = P(38 + k * 4, -16)
        surf.fill((250, 244, 220), (tx_, ty_, 1, 2))
    ex_, ey_ = P(35, -23)
    D.circle(surf, (255, 226, 80), (ex_, ey_), 2)
    surf.fill(dark, (ex_, ey_ - 1, 1, 3))
    D.polygon(surf, (234, 216, 176), [P(27, -27), P(14, -39), P(22, -26)])          # 뿔
    D.polygon(surf, (234, 216, 176), [P(31, -28), P(22, -42), P(29, -26)])
    if st in ("breath", "breath_w"):                             # 입 안의 불꽃
        mx, my = P(48, -14)
        surf.blit(glow(22, (255, 150, 60), 140), (mx - 22, my - 22))
    draw_wing(0, 0, wing)                                        # 가까운 쪽 날개
    if ph >= 3:                                                  # 분노의 불꽃 기운
        D.circle(surf, (255, 90, 40), (x, y0), 36 + int(2 * math.sin(t * 8)), 1)
    if st == "dash":                                             # 돌진의 속도선
        a = e["lz"]
        for i in range(4):
            o = (i - 1.5) * 6
            D.line(surf, (255, 180, 90), (x - math.cos(a) * 26 - math.sin(a) * o, y0 - math.sin(a) * 26 + math.cos(a) * o),
                   (x - math.cos(a) * 46 - math.sin(a) * o, y0 - math.sin(a) * 46 + math.cos(a) * o), 1)
    if st == "stun":                                             # 기절: 별이 돈다
        for i in range(3):
            a = t * 5 + i * 2.094
            surf.fill((255, 240, 150), (x + int(math.cos(a) * 14), y0 - 34 + int(math.sin(a) * 4), 2, 2))
    if e["al"] > 0:
        surf.fill((255, 230, 80), (x - 1, y0 - 50, 2, 5))
        surf.fill((255, 230, 80), (x - 1, y0 - 44, 2, 2))


# ================================================================= UI · 음악
def boss_bar_wrap(old):
    def f(screen, font, g, u):
        e = next((o for o in g["en"] if o["kind"] == "dragon" and o["hp"] > 0), None)
        if e is None or not (g["lock"] or g["intro"] > 0):
            return old(screen, font, g, u)
        SW, SH = G.W * u, G.H * u
        bw = 190 * u
        x0 = (SW - bw) // 2
        col = PHASE_COL[e["phase"] - 1]
        G.plate(screen, x0 - 8 * u, 31 * u, bw + 16 * u, 24 * u, u)
        G.txt(screen, font, NAME + f"   PHASE {e['phase']}", SW // 2, 32 * u, col, True, u)
        D.rect(screen, G.INK, (x0, 44 * u, bw, 8 * u))
        wfill = (bw - 2 * u) * e["hp"] // e["mhp"]
        D.rect(screen, G.lerp_c(col, (0, 0, 0), 0.45), (x0 + u, 45 * u, bw - 2 * u, 6 * u))
        D.rect(screen, col, (x0 + u, 45 * u, wfill, 6 * u))
        D.rect(screen, G.lerp_c(col, (255, 255, 255), 0.5), (x0 + u, 45 * u, wfill, 2 * u))
        for m in conf()["phases"]:
            D.rect(screen, G.INK, (x0 + int(bw * m), 44 * u, max(1, u), 8 * u))
        if e["st"] in ("breath", "stun"):
            G.txt(screen, font, "약점 노출! 피해 2배", SW // 2, 53 * u, (255, 240, 150), True, u)
        if g["intro"] > 0:
            a = max(0.0, min(1.0, g["intro"] / 0.5, (2.6 - g["intro"]) / 0.4))
            band = pygame.Surface((SW, 44 * u), SC)
            band.fill((24, 6, 6, int(215 * a)))
            screen.blit(band, (0, 92 * u))
            if a > 0.3:
                G.title_txt(screen, G.bigfont(u), NAME, SW // 2, 98 * u, u, (255, 150, 90))
                G.txt(screen, font, SUB, SW // 2, 116 * u, G.CREAM, True, u)
    return f


def objective_wrap(old):
    def f(g):
        if g["zid"] == ZID:
            e = next((o for o in g["en"] if o["kind"] == "dragon"), None)
            if not e:
                return "화룡을 쓰러뜨렸다! 중앙의 전송문으로 돌아가라"
            return {1: "화염 탄막을 피하며 부메랑을 맞혀라 (입을 벌릴 때가 기회!)",
                    2: "용암 분출과 돌진을 피하라. 돌진 직후 기절한 틈을 노려라",
                    3: "분노한 화룡! 불꽃 폭발 범위 밖으로 벗어나라"}[e["phase"]]
        return old(g)
    return f


def map_wrap(old):
    def f(screen, font, g, u):
        old(screen, font, g, u)
        meta = g.get("meta") or {}
        if g["zid"] != O.WID or "dragon" not in meta:
            return
        try:
            SW, SH = G.W * u, G.H * u
            pw, ph = int(SW * 0.94), 246 * u
            px, py = (SW - pw) // 2, (SH - ph) // 2
            kx = min((pw / u - 24 - 150) / g["wt"], (ph / u - 38) / g["ht"])
            dx, dy = meta["dragon"]
            if (dx, dy) not in W.mm_base(g)[2]:
                return
            x, y = px + 12 * u + int((dx + 0.5) * kx * u), py + 22 * u + int((dy + 0.5) * kx * u)
            D.polygon(screen, G.INK, [(x - 3 * u, y - 5 * u), (x + 3 * u, y - 5 * u), (x, y)])
            D.circle(screen, G.INK, (x, y - 6 * u), int(4.4 * u))
            D.circle(screen, (255, 120, 40), (x, y - 6 * u), int(3.4 * u))
            D.circle(screen, (255, 230, 120), (x, y - 6 * u), max(1, int(1.4 * u)))
            G.txt(screen, font, "화룡의 둥지", x + 6 * u, y - 8 * u, (255, 190, 120), u=u)
        except Exception:
            G.v9_log("dragon-map")
    return f


def dragon_track():
    SR = G.SR
    step, steps = 0.2, 40
    N = int(SR * step * steps)
    buf = [0.0] * N
    r = random.Random(666)

    def note(t0, f, dur, kind, vol, dec):
        i0, n, ph = int(t0 * SR), int(dur * SR), 0.0
        for i in range(n):
            ph += f / SR
            buf[(i0 + i) % N] += vol * math.exp(-dec * i / n) * min(1, i / 150) * G._wave(kind, ph)
    root, sc, deg = 98.0, [0, 3, 5, 7, 8, 10], 0
    for s in range(steps):
        t0 = s * step
        if s % 4 == 0:
            note(t0, root * 2 ** (r.choice((0, 0, 0, -2, 3)) / 12), 0.38, "saw", 0.16, 2.5)
            note(t0, 55.0, 0.16, "sine", 0.28, 6)
            note(t0, 0, 0.05, "noise", 0.12, 10)
        if s % 8 == 0:
            note(t0, root / 2, 1.5, "sine", 0.18, 1.0)
        if s % 2 == 1:
            note(t0, 0, 0.03, "noise", 0.04, 8)
        if r.random() < 0.5:
            deg = max(0, min(11, deg + r.choice((-2, -1, 0, 1, 2))))
            note(t0, root * 4 * 2 ** ((sc[deg % 6] + 12 * (deg // 6)) / 12), 0.16, "sq", 0.045, 4)
    return array.array("h", [int(max(-1, min(1, v)) * 32767 * 0.55) for v in buf])


# ================================================================= 설치
def install(g_mod, cfg, boss_mod, world_mod, open_mod, ui_mod):
    global G, C, V, W, O, UI
    G, C, V, W, O, UI = g_mod, cfg, boss_mod, world_mod, open_mod, ui_mod
    G.REGIONS.append(dict(name="화룡의 용암 둥지", floor=(74, 46, 52), floor2=(64, 40, 46), wall=(40, 30, 40), leaf=(120, 60, 40)))
    reg = len(G.REGIONS) - 1
    G.ZONES[ZID] = dict(name="화룡의 용암 둥지", reg=reg, size=(34, 30), arena="dragon", boss=3, origin=O.WID, npcs=[],
                        roads=[], exits=[], river=None, portals=[], n={})
    G.ZONES[O.WID].setdefault("lair", (0, 0, 0, 0, "e", 3))
    G.AGGRO["dragon"] = 9999
    G.FOE_NAME["dragon"] = "화룡 이그니스"
    W.AMBIENT[reg] = (120, 30, 10, 60)
    W.AMB_KIND[reg] = ((255, 150, 60), -1.3, 10, 0)

    old_arena, old_foe, old_hit, old_de, old_kill = G.build_arena, G.foe_ai, G.hit_foe, G.draw_enemy, G.kill
    old_track, old_travel, old_load, old_update, old_zone = G.make_track, G.start_travel, G.load_zone, G.update, G.build_zone

    def build_arena(zid):
        return build_arena_dragon() if G.ZONES[zid].get("arena") == "dragon" else old_arena(zid)

    def foe_ai(g, e, dt, d, ux, uy):
        if e["kind"] == "dragon":
            e["ag"] = True
            return dragon_ai(g, e, dt)
        return old_foe(g, e, dt, d, ux, uy)

    def draw_enemy(surf, e, cx, cy, t, g):
        if e["kind"] == "dragon":
            return draw_dragon(surf, e, cx, cy, t, g)
        return old_de(surf, e, cx, cy, t, g)

    def make_track(r):
        return dragon_track() if r == reg else old_track(r)

    def start_travel(g, zid, tx, ty):
        if zid == ZID:
            need = conf()["require_keys"]
            if g["keys"] < need:
                G.toast(g, f"봉인된 문이다... 수호 기계의 열쇠 조각이 필요하다 ({g['keys']}/{need})", 3.0)
                G.play("deny")
                g["pcd"] = 1.5
                return
            if ZID not in g["cleared"]:
                G.toast(g, "강대한 열기가 느껴진다... 화룡의 둥지", 3.0)
        return old_travel(g, zid, tx, ty)

    def load_zone(g, zid, tx, ty):
        old_load(g, zid, tx, ty)
        if g["zid"] == ZID and ZID in g["cleared"]:             # 이미 쓰러뜨린 화룡은 다시 나오지 않는다
            g["en"] = [e for e in g["en"] if e["kind"] != "dragon"]
            g["lock"] = False

    def update(g, inp, dt):
        old_update(g, inp, dt)
        if g["mode"] != "play" or g["tr"]:
            return
        for e in g["en"]:                                       # 기본 AI는 360px 넘게 떨어지면 멈추므로 화룡만 따로 돌린다
            if e["kind"] == "dragon" and e["hp"] > 0 and G.dist(g["x"], g["y"], e["x"], e["y"]) > 360:
                e["ag"] = True
                try:
                    dragon_ai(g, e, dt)
                except Exception:
                    G.v9_log("dragon-ai")

    def build_zone(zid):
        z = old_zone(zid)
        if (zid == O.WID or zid in O.LEGACY) and z.get("meta") and not z.get("_dragon"):
            try:
                decorate_world(z)
            except Exception:
                G.v9_log("dragon-decorate")
        return z

    def guarded(new, old):
        def f(*a):
            try:
                return new(*a)
            except Exception:
                G.v9_log("dragon-ai")
                return old(*a)
        return f
    G.build_arena, G.draw_enemy, G.make_track, G.start_travel = build_arena, draw_enemy, make_track, start_travel
    G.foe_ai = guarded(foe_ai, old_foe)
    G.hit_foe, G.kill = hit_wrap(old_hit), kill_wrap(old_kill)
    G.load_zone, G.update, G.build_zone = load_zone, update, build_zone
    G.draw_arena = draw_arena_wrap(G.draw_arena)
    G.draw = draw_wrap(G.draw)
    UI.boss_bar = boss_bar_wrap(UI.boss_bar)
    UI.objective = objective_wrap(UI.objective)
    UI.draw_map = map_wrap(UI.draw_map)