"""v9 괴수 연출 모듈 (v9_kaiju_fx.py)  -  필드 보스 '탈라소르'를 3D 리그(v9_kaiju_rig.py)로 그리고 패턴마다 연기를 시킨다.
 이동
 - 어느 각도(8방향과 그 사이)로든 몸을 돌린다. 머리가 먼저 돌고 몸통·꼬리 세 갈래가 늦게 따라온다.
 - 기어다니기: 네 다리가 실제 이동 거리에 맞춰 걷는다. 돌진·사냥 때는 배를 땅에 붙이고 낮게 기어간다(low).
 - 비행: 고도가 오르면 그림자가 떨어지고 날개를 치며 다리를 접는다. 하늘 높이 오르면 그림자만 남는다.
 패턴별 연기 (준비 -> 실행 -> 후딜)
   발톱(rear_w/slam)   뒷발로 일어서 앞발을 치켜든다 -> 내려찍기          꼬리(coil_w/sweep) 꼬리 셋을 감아 쥐고 왕관을 편다 -> 몸을 돌리며 휘두름
   돌진(crawl_w/rush)  배를 깔고 땅을 긁는다 -> 낮게 질주 -> 벽에 박혀 기절   맥동(glow_w/pulse)  왕관이 활짝 펴지며 가슴이 빛난다 -> 고리 전기탄
   균열(gore_w/gore)   머리를 숙여 엄니를 땅에 꽂는다                   포효(roar_w/roar)  상체를 들고 왕관을 떤다 -> 포효 충격파
   가시(spine_w/spine) 꼬리 셋을 치켜들어 벌린다 -> 튕겨 쏨           돌풍(takeoff/gust/land) 이륙해 낮게 떠 날개를 크게 친다 -> 착지
   강하(ascend/high/dive) 높이 날아올라 사라졌다가 그림자 위로 내리꽂힘   브레스(breath_w/breath) 가슴에 냉기를 모았다가 고개를 휘두르며 뿜음
   사냥(prowl)          낮게 기어 플레이어 주위를 돌며 서리 자국을 남김
 잠(sleep)·기상 포효, 페이즈 전환(장갑 파괴·폭주), 처치(연쇄 폭발 -> 쓰러짐 -> 빛이 꺼짐)"""
import math
import random

import pygame

import v9_kaiju_rig as R

D = pygame.draw
SC = pygame.SRCALPHA
G = None
PALS = {
    1: dict(base=(176, 182, 196), dark=(118, 124, 146), deep=(62, 66, 92), hi=(226, 232, 240), belly=(214, 222, 232),
            belly_d=(150, 160, 182), horn=(232, 240, 246), eye=(150, 235, 255), spike=(170, 240, 255), wing=(70, 82, 120),
            wing_d=(46, 54, 86), vein=(110, 230, 255), vein_d=(40, 90, 150), glow=(90, 200, 255), plate=(92, 100, 128),
            plate_d=(56, 60, 84)),
    2: dict(base=(168, 178, 198), dark=(108, 118, 148), deep=(52, 60, 94), hi=(222, 232, 246), belly=(206, 220, 236),
            belly_d=(140, 156, 186), horn=(228, 244, 252), eye=(190, 250, 255), spike=(150, 240, 255), wing=(58, 76, 126),
            wing_d=(38, 48, 92), vein=(120, 245, 255), vein_d=(50, 120, 190), glow=(80, 210, 255), plate=(92, 100, 128),
            plate_d=(56, 60, 84)),
    3: dict(base=(150, 160, 190), dark=(94, 102, 140), deep=(40, 44, 82), hi=(214, 226, 248), belly=(196, 214, 240),
            belly_d=(128, 146, 186), horn=(236, 250, 255), eye=(240, 255, 255), spike=(200, 255, 255), wing=(48, 66, 128),
            wing_d=(30, 40, 92), vein=(170, 255, 255), vein_d=(60, 150, 220), glow=(110, 230, 255), plate=(92, 100, 128),
            plate_d=(56, 60, 84)),
}
_SH, _CV, _T = {}, {}, [0.0]
BREATH_DRAW = None                                               # v9_pfx 가 설치되면 냉기 브레스 그리기 함수가 들어온다
blit_gl = R.blit_gl


def lerpc(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def angdiff(a, b):
    return (a - b + math.pi) % (2 * math.pi) - math.pi


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def pulse(tc, atk, dec):
    if tc < 0:
        return 0.0
    if tc < atk:
        return tc / atk
    return math.exp(-(tc - atk) / dec)


# ================================================================= 포즈 표 (키 의미는 v9_kaiju_rig.DEF 참고)
def P_(**k):
    d = dict(R.DEF)
    d.update(k)
    return d


BASE = {
    "idle": P_(),
    "roam": P_(hx=46, hz=22, hp=-0.25, crown=0.15, tamp=1.2),
    "sleep": P_(bz=9, pitch=-0.06, hx=36, hz=8, hp=-0.6, mouth=0.0, nk=0.6, crown=0.0, tcurl=0.9, tamp=0.25, tfreq=0.6, brace=0.6,
                low=0.6),
    "recover": P_(bz=16, hx=44, hz=20, hp=-0.45, mouth=0.25, wfold=1.0, tamp=0.6, brace=0.5, crown=0.35),
    "rear_w": P_(bz=27, pitch=0.42, fz=30, fxo=6, hx=38, hz=50, hp=0.5, mouth=0.6, nk=1.3, wfold=0.1, wb0=0.6, wamp=0.18,
                 wfreq=2.0, glow=0.7, brace=0.6, tlift=9, crown=0.8),
    "slam": P_(bz=27, pitch=0.42, fz=30, fxo=6, hx=38, hz=50, hp=0.5, mouth=0.6, nk=1.3, wfold=0.1, wb0=0.6, wamp=0.18,
               wfreq=2.0, glow=0.7, brace=0.6, tlift=9, crown=0.8),
    "coil_w": P_(bz=16, pitch=-0.05, hx=40, hz=24, hp=-0.15, mouth=0.4, tcurl=1.0, tsplit=0.4, tamp=0.2, tfreq=3.0, crown=1.0,
                 glow=0.6, brace=0.9, wfold=0.6, wb0=0.3),
    "sweep": P_(bz=14, pitch=-0.06, hx=44, hz=18, hp=-0.3, mouth=0.6, tcurl=-0.9, tsplit=0.9, tamp=0.15, tfreq=2.0, crown=1.0,
                glow=0.8, brace=1.0, wfold=0.35, wb0=0.6, wsw=-0.3, low=0.4, roll=0.0),
    "crawl_w": P_(bz=8, pitch=-0.16, hx=52, hz=10, hp=-0.6, mouth=0.35, nk=0.75, wfold=1.0, brace=1.0, tlift=8, tamp=0.3, glow=0.4,
                  scr=4.5, low=1.0, crown=0.6),
    "rush": P_(bz=9, pitch=-0.1, hx=58, hz=12, hp=-0.45, mouth=0.5, nk=0.8, wfold=1.0, tamp=0.2, glow=0.7, tfreq=5.0, low=1.0,
               crown=0.9),
    "skid": P_(bz=12, pitch=0.1, hx=48, hz=18, hp=-0.2, mouth=0.4, wfold=0.8, tamp=1.2, brace=1.0, low=0.4),
    "stun": P_(bz=6, pitch=-0.2, hx=50, hz=5, hp=-0.95, mouth=0.1, nk=0.6, wfold=0.6, wb0=-0.5, tamp=0.15, brace=1.0, crown=0.0,
               low=0.8),
    "glow_w": P_(bz=24, pitch=0.28, fz=14, fxo=4, hx=40, hz=42, hp=0.6, nk=1.2, mouth=0.5, wfold=0.2, wb0=0.6, wamp=0.12,
                 wfreq=2.0, glow=1.0, chest=0.14, brace=0.8, tlift=6, crown=1.0, tsplit=0.6),
    "pulse": P_(bz=24, pitch=0.28, fz=14, fxo=4, hx=40, hz=42, hp=0.6, nk=1.2, mouth=0.8, wfold=0.0, wb0=0.6, wamp=0.12,
                wfreq=2.0, glow=1.0, chest=0.1, brace=0.8, tlift=6, crown=1.0, tsplit=0.6),
    "gore_w": P_(bz=17, pitch=0.18, hx=40, hz=36, hp=0.6, mouth=0.4, nk=1.2, wfold=0.7, brace=0.9, crown=0.7, tlift=6, glow=0.5),
    "gore": P_(bz=12, pitch=-0.22, hx=50, hz=6, hp=-1.05, mouth=0.6, nk=0.7, wfold=0.6, brace=1.0, crown=0.9, tlift=8, glow=0.7,
               low=0.5),
    "roar_w": P_(bz=20, pitch=0.16, hx=36, hz=30, hp=-0.2, mouth=0.2, nk=0.9, wfold=0.5, wb0=0.2, brace=0.9, crown=0.2, glow=0.4,
                 low=0.3),
    "roar": P_(bz=25, pitch=0.34, fz=18, fxo=4, hx=40, hz=50, hp=0.8, nk=1.3, mouth=1.0, wfold=0.0, wb0=0.5, wamp=0.18,
               wfreq=2.2, glow=0.9, chest=0.12, brace=0.9, tlift=7, crown=1.0, tsplit=0.5),
    "spine_w": P_(bz=17, pitch=0.05, hx=44, hz=26, hp=0.0, mouth=0.3, tlift=14, tsplit=1.0, tamp=0.3, tfreq=3.0, tcurl=0.3,
                  crown=0.6, glow=0.5, brace=0.6),
    "spine": P_(bz=17, pitch=0.0, hx=46, hz=24, hp=-0.1, mouth=0.5, tlift=10, tsplit=1.2, tamp=0.9, tfreq=7.0, tcurl=-0.3,
                crown=0.8, glow=0.6, brace=0.6),
    "takeoff": P_(alt=10, bz=20, pitch=0.2, hx=46, hz=34, hp=0.25, mouth=0.4, wfold=0, wb0=0.6, wamp=0.85, wfreq=2.6, tuck=0.4,
                  brace=0.4, tlift=5, crown=0.7),
    "gust": P_(alt=26, bz=20, pitch=0.08, hx=48, hz=32, hp=0.1, mouth=0.5, wfold=0, wb0=0.4, wamp=1.15, wfreq=1.5, tuck=1.0,
               tlift=6, tamp=1.3, crown=0.9, glow=0.6),
    "land": P_(alt=0, bz=20, pitch=0.2, hx=46, hz=34, hp=0.25, mouth=0.4, wfold=0, wb0=0.5, wamp=0.8, wfreq=3.0, tuck=0.0,
               brace=0.6, tlift=5),
    "ascend": P_(alt=60, bz=20, pitch=0.3, hx=50, hz=36, hp=0.4, mouth=0.4, wfold=0, wb0=0.3, wamp=1.1, wfreq=2.2, tuck=1.0,
                 tlift=6, tamp=1.4, crown=0.4),
    "high": P_(alt=150, bz=20, pitch=0.0, hx=52, hz=32, hp=0.0, mouth=0.4, wfold=0, wb0=0.3, wamp=0.9, wfreq=1.6, tuck=1.0,
               tamp=1.4, crown=0.4),
    "dive": P_(alt=0, bz=16, pitch=-0.55, hx=56, hz=20, hp=-0.5, mouth=0.9, wfold=0.5, wb0=-0.2, wamp=0.1, tuck=1.0, crown=1.0,
               glow=1.0),
    "breath_w": P_(bz=25, pitch=0.32, fz=12, fxo=4, hx=40, hz=46, hp=0.85, nk=1.25, mouth=0.3, wfold=0.1, wb0=0.55, wamp=0.12,
                   wfreq=2.0, glow=1.0, chest=0.16, brace=0.8, tlift=6, tamp=0.4, crown=1.0),
    "breath": P_(bz=22, pitch=0.12, hx=52, hz=30, hp=-0.15, mouth=1.0, nk=0.9, wfold=0.0, wb0=0.35, wamp=0.08, wfreq=3.0,
                 glow=1.0, brace=1.0, tlift=7, tamp=0.5, crown=1.0),
    "prowl": P_(bz=9, pitch=-0.08, hx=54, hz=12, hp=-0.4, mouth=0.4, nk=0.85, wfold=1.0, tamp=1.4, tfreq=3.5, glow=0.6, low=1.0,
                crown=0.5),
    "death": P_(bz=25, pitch=0.34, fz=18, fxo=4, hx=40, hz=50, hp=0.8, nk=1.3, mouth=1.0, wfold=0.0, wb0=0.5, wamp=0.18,
                wfreq=2.2, glow=0.9, brace=0.9, tlift=7, crown=1.0),
}
FAST = ("rush", "crawl_w", "stun", "rear_w", "slam", "pulse", "gore", "dive", "spine", "skid", "land")
LOCK = ("gore_w", "gore", "roar_w", "roar", "glow_w", "pulse", "sleep", "stun", "skid")
AIM = ("rear_w", "slam", "spine_w", "spine", "crawl_w", "breath_w", "takeoff", "gust")
VALID = set(BASE)


def build_pose(st, e, tc, t, ph, deadt):
    cn = e.get("cue")
    b = dict(BASE.get(st) or BASE["idle"])

    def kk(*names, atk=0.07, dec=0.25):
        return pulse(tc, atk, dec) if cn in names else 0.0
    if st == "slam":                                              # 앞발 내려찍기
        d = kk("slam", atk=0.08, dec=0.3)
        b["fz"] *= (1 - d)
        b["pitch"] -= 0.62 * d
        b["hz"] -= 26 * d
        b["hp"] -= 1.1 * d
        b["bz"] -= 8 * d
        b["wb0"] += 0.5 * d
        b["mouth"] = 0.6 + 0.4 * d
    elif st == "gore":
        d = kk("gore", atk=0.06, dec=0.28)
        b["hz"] -= 4 * d
        b["pitch"] -= 0.12 * d
        b["mouth"] = 0.6 + 0.4 * d
    elif st == "pulse":
        d = kk("pulse", atk=0.05, dec=0.3)
        b["chest"] += 0.15 * d
        b["crown"] = 1.0
        b["mouth"] += 0.2 * d
    elif st == "roar":
        b["hz"] += math.sin(t * 50) * 0.8
        b["crown"] = 0.85 + 0.15 * math.sin(t * 60)
    elif st == "spine":
        d = kk("flick", atk=0.05, dec=0.22)
        b["tlift"] += 8 * d
        b["tcurl"] -= 0.8 * d
        b["pitch"] -= 0.1 * d
    elif st == "gust":
        d = kk("flap", atk=0.08, dec=0.3)
        b["wb0"] -= 0.9 * d
        b["alt"] -= 4 * d
    elif st == "breath":
        b["hz"] += math.sin(t * 45) * 0.8
    elif st == "glow_w":
        b["crown"] = 0.9 + 0.1 * math.sin(t * 40)
    elif st == "sleep":
        b["bz"] += math.sin(t * 1.2) * 0.8                          # 숨 쉬듯 오르내림
    elif st == "death" and deadt is not None and deadt > 1.5:      # 처치: 쓰러진다
        u = min(1.0, (deadt - 1.5) / 0.9)
        b.update(bz=25 - 18 * u, pitch=0.34 - 0.55 * u, hz=50 - 44 * u, hp=0.8 - 1.7 * u, mouth=1.0 - 0.7 * u, wb0=0.5 - 1.0 * u,
                 wfold=0.5 * u, wamp=0.0, fz=18 * (1 - u), tamp=0.15, glow=0.9 * (1 - u), crown=1.0 - u)
    if ph >= 2:
        b["glow"] = max(b["glow"], 0.15 * (ph - 1))
    if e.get("fl", 0) > 0:                                        # 맞았을 때 움찔
        f = min(1.0, e["fl"] / 0.12)
        b["hx"] -= 5 * f
        b["hz"] += 2 * f
        b["mouth"] += 0.4 * f
    return b


# ================================================================= 입자 (서리·전기·먼지·파편)
def emit(fx, kind, x, y, vx, vy, life, size=1):
    if len(fx["p"]) < 280:
        fx["p"].append([x, y, vx, vy, life, life, kind, size])


def step_particles(fx, dt):
    for p in fx["p"]:
        p[0] += p[2] * dt
        p[1] += p[3] * dt
        p[4] -= dt
        if p[6] in ("dust", "frost"):
            p[2] *= 0.95
            p[3] *= 0.95
        elif p[6] == "snow":
            p[3] += 6 * dt
        elif p[6] == "wind":
            p[2] *= 0.97
            p[3] *= 0.97
    fx["p"] = [p for p in fx["p"] if p[4] > 0]
    fx["bm"] = [b for b in fx["bm"] if _T[0] - b[0] < 0.5]
    fx["rg"] = [r for r in fx["rg"] if _T[0] - r[0] < 1.0]
    fx["arc"] = [a for a in fx["arc"] if _T[0] - a[0] < 0.16]


def draw_particles(surf, fx, cx, cy):
    for p in fx["p"]:
        f = p[4] / p[5]
        x, y = int(p[0]) - cx, int(p[1]) - cy
        k = p[6]
        if k == "snow":
            s = p[7] if f > 0.3 else 1
            surf.fill(lerpc((255, 255, 255), (120, 170, 220), 1 - f), (x, y, s, s))
        elif k == "frost":
            blit_gl(surf, x, y, 3 + (1 - f) * 7, (190, 230, 255), 80 * f + 10)
        elif k == "dust":
            blit_gl(surf, x, y, 3 + (1 - f) * 7, (170, 176, 190), 80 * f + 10)
        elif k == "shard":
            L = 4 * p[7]
            sp = math.hypot(p[2], p[3]) or 1
            D.line(surf, (220, 250, 255), (x, y), (x - int(p[2] / sp * L), y - int(p[3] / sp * L)), 2 if p[7] > 1 else 1)
        elif k == "wind":
            sp = math.hypot(p[2], p[3]) or 1
            L = 6 + 8 * f
            D.line(surf, lerpc((240, 250, 255), (120, 160, 210), 1 - f), (x, y), (x - int(p[2] / sp * L), y - int(p[3] / sp * L)), 1)
        else:                                                      # 전기 불꽃
            D.line(surf, (200, 245, 255), (x, y), (x - int(p[2] * 0.04), y - int(p[3] * 0.04)), 1)


def draw_booms(surf, fx, cx, cy, t):
    for b in fx["bm"]:
        age = t - b[0]
        x, y, sz = int(b[1]) - cx, int(b[2]) - cy, b[3]
        blit_gl(surf, x, y, 14 * sz + age * 60 * sz, (170, 230, 255), 200 * (1 - age / 0.5))
        D.circle(surf, lerpc((255, 255, 255), (70, 140, 220), age / 0.5), (x, y), max(1, int(age * 90 * sz)), 2)
    for r in fx["rg"]:
        age = t - r[0]
        rr = max(1, int(age * 200))
        D.ellipse(surf, lerpc((200, 240, 255), (40, 60, 110), age), (int(r[1]) - cx - rr, int(r[2]) - cy - rr * 0.6, rr * 2, int(rr * 1.2)), 2)
    for a in fx["arc"]:                                           # 전기 호 (몸 위를 튀는 번개)
        pts = [(int(px) - cx, int(py) - cy) for px, py in a[1]]
        if len(pts) > 1:
            D.lines(surf, (120, 220, 255), False, pts, 3)
            D.lines(surf, (240, 255, 255), False, pts, 1)


def boom(fx, t, x, y, sz=1.0):
    fx["bm"].append([t, x, y, sz])
    for _ in range(int(8 * sz)):
        a, v = random.random() * 6.283, random.uniform(40, 120) * sz
        emit(fx, "spark", x, y, math.cos(a) * v, math.sin(a) * v, random.uniform(0.3, 0.6))
        emit(fx, "shard", x, y, math.cos(a) * v * 0.7, math.sin(a) * v * 0.7, random.uniform(0.3, 0.6), 1 + (random.random() < 0.3))
        emit(fx, "snow", x, y, math.cos(a) * v * 0.4, math.sin(a) * v * 0.4 - 15, random.uniform(0.6, 1.2), 2)


def dust_ring(fx, x, y, n=10, sp=70.0, big=1.0, kind="dust"):
    for i in range(n):
        a = i / n * 6.283 + random.uniform(-0.2, 0.2)
        v = sp * random.uniform(0.6, 1.2)
        emit(fx, kind, x, y, math.cos(a) * v, math.sin(a) * v * 0.55, random.uniform(0.5, 0.9) * big)


def arc(fx, t, x0, y0, x1, y1, n=6, jit=7):
    pts = []
    for i in range(n + 1):
        f = i / n
        j = 0 if i in (0, n) else random.uniform(-jit, jit)
        pts.append((x0 + (x1 - x0) * f + j, y0 + (y1 - y0) * f + j * 0.6))
    fx["arc"].append([t, pts])


def new_fx(t, e=None, g=None):
    ang = 0.0
    if e is not None and g is not None:
        ang = math.atan2(g["y"] - e["y"], g["x"] - e["x"])
    return dict(rig=R.new_state(), ang=ang, t=t, p=[], bm=[], rg=[], arc=[], gh=[], acc=0.0, sm=0.0, ph_seen=None, ph_t=-9.0,
                gt=0.0, lx=None, ly=None, vx=0.0, vy=0.0, cue_seen=None, wa=None, alt_prev=0.0, wcyc=0, dust_t=0.0, arc_t=0.0,
                armor_seen=None, frost_t=0.0, tt=[])


def eff_state(e, g):
    s = e["st"]
    if e.get("inv", 0) > 0 and s in ("idle", "roar"):
        return "roar"
    if s == "idle" and e.get("mode") != "fight":
        return "roam"
    return s if s in VALID else "idle"


def on_cue(fx, e, g, name, t):
    wa = fx.get("wa")
    if not wa:
        return
    feet, mouth, body = wa["feet"], wa["mouth"], wa["body"]
    gx, gy = body[0], body[1] + R.GY0 - 6
    if name == "slam":
        for k in (0, 2):
            boom(fx, t, feet[k][0], feet[k][1], 1.2)
            dust_ring(fx, feet[k][0], feet[k][1], 8, 90, 1.0, "frost")
        fx["rg"].append([t, (feet[0][0] + feet[2][0]) / 2, (feet[0][1] + feet[2][1]) / 2])
    elif name == "launch":
        for fp in feet:
            dust_ring(fx, fp[0], fp[1], 6, 100)
        fx["rg"].append([t, gx, gy])
    elif name == "crash":
        boom(fx, t, mouth[0], mouth[1] + 6, 1.6)
        for fp in feet:
            dust_ring(fx, fp[0], fp[1], 8, 110, 1.2, "frost")
        fx["rg"].append([t, gx, gy])
    elif name == "pulse":
        fx["rg"].append([t, gx, gy])
        c = wa["crown"]
        for _ in range(6):
            a = random.random() * 6.283
            arc(fx, t, c[0], c[1], c[0] + math.cos(a) * 46, c[1] + math.sin(a) * 30)
    elif name == "gore":
        boom(fx, t, mouth[0], mouth[1] + 4, 1.0)
        dust_ring(fx, mouth[0], mouth[1], 10, 90, 1.0, "frost")
    elif name == "roar":
        fx["rg"].append([t, gx, gy])
        fx["rg"].append([t + 0.15, gx, gy])
        for _ in range(16):
            a = random.random() * 6.283
            emit(fx, "wind", gx, gy, math.cos(a) * 160, math.sin(a) * 100, random.uniform(0.4, 0.7))
    elif name == "spin":
        dust_ring(fx, gx, gy, 16, 120, 1.1, "frost")
        fx["rg"].append([t, gx, gy])
    elif name == "spin_end":
        dust_ring(fx, gx, gy, 12, 90, 1.0, "dust")
        for _ in range(14):
            a = random.random() * 6.283
            emit(fx, "wind", gx, gy, math.cos(a) * 170, math.sin(a) * 110, random.uniform(0.3, 0.5))
    elif name == "flick":
        for tp in wa["tails"]:
            for _ in range(4):
                a = random.random() * 6.283
                emit(fx, "shard", tp[0], tp[1], math.cos(a) * 80, math.sin(a) * 80, 0.4, 2)
    elif name == "flap":
        for _ in range(22):
            a = random.random() * 6.283
            v = random.uniform(120, 220)
            emit(fx, "wind", gx, gy, math.cos(a) * v, math.sin(a) * v * 0.6, random.uniform(0.35, 0.6))
        dust_ring(fx, gx, gy, 14, 130, 1.1, "frost")
    elif name == "ignite":
        boom(fx, t, mouth[0], mouth[1], 0.9)
    elif name in ("break", "rage"):
        boom(fx, t, body[0], body[1] - 10, 2.2)
        for _ in range(30):
            a = random.random() * 6.283
            emit(fx, "shard", body[0], body[1] - 10, math.cos(a) * random.uniform(60, 160), math.sin(a) * random.uniform(60, 160), 0.6, 2)
        for _ in range(5):
            a = random.random() * 6.283
            arc(fx, t, body[0], body[1] - 10, body[0] + math.cos(a) * 60, body[1] - 10 + math.sin(a) * 40)
        fx["rg"].append([t, gx, gy])


# ================================================================= 움직임
def motion(fx, e, g, st, dt, t, deadt):
    if fx["lx"] is None or dt <= 1e-5:
        fx["lx"], fx["ly"] = e["x"], e["y"]
        return fx["vx"], fx["vy"], 0.0, 0.0
    k = 1 - math.exp(-dt * 12)
    fx["vx"] += ((e["x"] - fx["lx"]) / dt - fx["vx"]) * k
    fx["vy"] += ((e["y"] - fx["ly"]) / dt - fx["vy"]) * k
    fx["lx"], fx["ly"] = e["x"], e["y"]
    vx, vy = fx["vx"], fx["vy"]
    sp = math.hypot(vx, vy)
    if deadt is not None or sp > 700 or st in ("high", "dive"):
        sp, vx, vy = 0.0, 0.0, 0.0
    h = fx["ang"]
    pa = math.atan2(g["y"] - e["y"], g["x"] - e["x"])
    lz = e.get("lz", 0.0)
    rate, look = 2.2, 0.0
    if st in ("rush", "crawl_w", "sweep", "coil_w"):
        tgt, rate = lz, (9.0 if st != "sweep" else 60.0)
    elif st == "breath":
        tgt, rate, look = lz, 1.8, clamp(angdiff(lz, h) * 1.5, -1.25, 1.25)
    elif st == "prowl":
        tgt, rate = (math.atan2(vy, vx) if sp > 20 else h), 6.0
        look = clamp(angdiff(pa, tgt) * 0.8, -1.1, 1.1)
    elif st in ("stun", "death", "sleep"):
        tgt, rate, look = h, 0.0, (math.sin(t * 3) * 0.3 if st == "stun" else 0.0)
    elif st in AIM:
        tgt, rate = pa, 5.0
        look = clamp(angdiff(pa, h) * 0.8, -0.95, 0.95)
    elif st in LOCK:
        tgt, rate = h, 0.0
    else:
        tgt = pa if e.get("mode") == "fight" else (math.atan2(vy, vx) if sp > 6 else h)
        if sp > 12 and st in ("idle", "recover", "roam") and e.get("mode") == "fight":
            diff = angdiff(math.atan2(vy, vx), pa)
            tgt = pa if abs(diff) > 2.2 else pa + diff * 0.7
        look = clamp(angdiff(pa, h) * 0.8, -0.95, 0.95) if e.get("mode") == "fight" else math.sin(t * 0.7) * 0.4
    step = clamp(angdiff(tgt, h), -rate * dt, rate * dt)
    fx["ang"] = h + step
    turn = step / dt
    vf = vx * math.cos(fx["ang"]) + vy * math.sin(fx["ang"])
    return sp, vf, turn, look


# ================================================================= 한 프레임
def draw_core(surf, e, cx, cy, t, g, deadt=None):
    fx = e.setdefault("_fx", new_fx(t, e, g))
    _T[0] = t
    dt = max(0.0, min(0.08, t - fx["t"]))
    fx["t"] = t
    ph = e["phase"]
    P = PALS[ph]
    st = "death" if deadt is not None else eff_state(e, g)
    rig = fx["rig"]
    ps = rig["ps"]
    sp, vf, turn, look = motion(fx, e, g, st, dt, t, deadt)
    tc = t - e.get("cue_t", -99.0)
    tg = build_pose(st, e, tc, t, ph, deadt)
    tg["hyaw"] = look
    flying = ps["alt"] > 8
    tg["roll"] += clamp(-turn * (0.07 if flying else 0.03), -0.3, 0.3)
    if flying and sp > 20:
        tg["pitch"] -= 0.12 * min(1.0, sp / 120)
    R.update(rig, tg, dt, 15 if st in FAST else 9, vf, sp, turn)
    if fx["ph_seen"] != ph:
        if fx["ph_seen"] is not None:
            fx["ph_t"] = t
        fx["ph_seen"] = ph
    ex, ey = e["x"], e["y"]
    # ---- 상시 입자: 몸에서 흩날리는 눈송이, 페이즈가 오를수록 전기 호
    fx["acc"] += dt * (6 + 6 * ph)
    while fx["acc"] >= 1:
        fx["acc"] -= 1
        emit(fx, "snow", ex + random.uniform(-40, 40), ey + random.uniform(-34, 6), random.uniform(-10, 10), random.uniform(-26, -10),
             random.uniform(0.8, 1.6), 2 if ph >= 3 else 1)
    flash = 0
    if e.get("fl", 0) > 0:
        flash = 120
    elif e.get("inv", 0) > 0 and int(t * 18) % 2 and deadt is None:
        flash = 50
    ox = oy = 0
    alpha = 255
    if st == "high":                                              # 하늘 높이: 몸은 사라지고 그림자만 남는다
        alpha = int(255 * clamp(1 - (ps["alt"] - 70) / 60, 0.0, 1.0))
    if deadt is not None:
        flash = int(40 + 70 * (0.5 + 0.5 * math.sin(deadt * 30))) if deadt < 2.4 else 200
        a = max(0.0, 3.0 - deadt * 1.2)
        ox, oy = random.randint(-int(a) - 1, int(a) + 1), random.randint(-int(a) - 1, int(a) + 1)
        if deadt < 2.2 and random.random() < 0.35:
            boom(fx, t, ex + random.uniform(-44, 44), ey + random.uniform(-34, 14), random.uniform(0.7, 1.3))
            G.play("boom")
        if deadt > 1.9:
            alpha = int(255 * max(0.0, 1 - (deadt - 1.9) / 1.0))
        if 2.5 < deadt < 2.6 and not fx.get("fin"):
            fx["fin"] = True
            boom(fx, t, ex, ey, 3.5)
            G.play("boss")
    # ---- 렌더
    if "cv" not in _CV:
        _CV["cv"] = pygame.Surface((R.CW, R.CH), SC)
    img = _CV["cv"]
    img.fill((0, 0, 0, 0))
    anc = R.draw(img, rig, P, ph, t, fx["ang"], e.get("armor", 0))
    if flash > 0:
        img.fill((flash, flash, flash, 0), special_flags=pygame.BLEND_RGB_ADD)
    img.set_alpha(alpha)

    def Sx(p):
        return (ex - cx + (p[0] - R.CX), ey - cy + (p[1] - R.CY))

    def Wx(p):
        return (ex + (p[0] - R.CX), ey + (p[1] - R.CY))
    fx["wa"] = dict(mouth=Wx(anc["mouth"]), body=Wx(anc["body"]), feet=[Wx(p) for p in anc["feet"]], nose=Wx(anc["nose"]),
                    head=Wx(anc["head"]), tail=Wx(anc["tail"]), tails=[Wx(p) for p in anc["tails"]], tips=[Wx(p) for p in anc["tips"]],
                    top=Wx(anc["top"]), crown=Wx(anc["crown"]))
    wa = fx["wa"]
    if e.get("cue_t") is not None and fx["cue_seen"] != e["cue_t"]:
        fx["cue_seen"] = e["cue_t"]
        on_cue(fx, e, g, e.get("cue"), t)
    mx, my = Sx(anc["mouth"])
    # ---- 상태별 지속 효과
    if st == "breath":
        for _ in range(2):
            a = e.get("lz", 0.0) + random.uniform(-0.25, 0.25)
            v = random.uniform(80, 160)
            emit(fx, "snow", wa["mouth"][0], wa["mouth"][1], math.cos(a) * v, math.sin(a) * v, random.uniform(0.4, 0.8), 2)
    elif st in ("breath_w", "glow_w", "pulse"):
        c = wa["mouth"] if st == "breath_w" else wa["crown"]
        for _ in range(2):
            a = random.random() * 6.283
            emit(fx, "spark", c[0] + math.cos(a) * 30, c[1] + math.sin(a) * 30, -math.cos(a) * 90, -math.sin(a) * 90, 0.3)
    elif st in ("rush", "prowl"):
        if t - fx["gt"] > 0.035 and st == "rush":
            fx["gt"] = t
            gh = img.copy()
            gh.fill((140, 210, 255, 255), special_flags=pygame.BLEND_RGBA_MULT)
            fx["gh"].append([gh, ex, ey, t])
        if t - fx["dust_t"] > 0.05:
            fx["dust_t"] = t
            for fp in wa["feet"]:
                emit(fx, "frost", fp[0], fp[1], -math.cos(fx["ang"]) * 50, random.uniform(-15, 5), 0.6)
    elif st in ("crawl_w", "coil_w") and t - fx["dust_t"] > 0.08:
        fx["dust_t"] = t
        fp = wa["feet"][random.choice((0, 2))]
        emit(fx, "dust", fp[0], fp[1], random.uniform(-30, 30), random.uniform(-25, -5), 0.6)
    elif st == "sweep":                                             # 회전: 꼬리 끝의 궤적을 쌓아 둔다 (잔상 호)
        fx["tt"].append((t, list(wa["tails"])))
        if random.random() < 0.8:
            tp = random.choice(wa["tails"])
            a = math.atan2(tp[1] - ey, tp[0] - ex)
            emit(fx, "wind", tp[0], tp[1], -math.sin(a) * 160 * e.get("spin", 1), math.cos(a) * 110 * e.get("spin", 1), 0.35)
        if random.random() < 0.4:
            tp = random.choice(wa["tails"])
            emit(fx, "shard", tp[0], tp[1], random.uniform(-60, 60), random.uniform(-60, 60), 0.4, 2)
    elif st == "sleep" and random.random() < 0.05:                # 잠든 숨결: 콧김
        emit(fx, "frost", wa["nose"][0], wa["nose"][1], random.uniform(-10, 10), random.uniform(-20, -8), 1.2)
    fx["tt"] = [q for q in fx["tt"] if t - q[0] < 0.22]
    if (ph >= 2 or st in ("glow_w", "pulse", "roar")) and t - fx["arc_t"] > (0.5 if ph < 3 else 0.22):
        fx["arc_t"] = t                                           # 몸 위를 튀는 전기
        a0 = random.choice([wa["crown"], wa["body"], wa["tail"]] + wa["tails"])
        a = random.random() * 6.283
        arc(fx, t, a0[0], a0[1], a0[0] + math.cos(a) * 24, a0[1] + math.sin(a) * 18, 4, 5)
    cyc = int(rig["wph"] / 6.2832)                               # 날갯짓 바람: 낮게 떠 있을 때 서리 먼지
    if cyc != fx["wcyc"]:
        fx["wcyc"] = cyc
        if 0 < ps["alt"] < 40 and ps["wamp"] > 0.3:
            dust_ring(fx, wa["body"][0], wa["body"][1] + R.GY0 - 6, 10, 90, 1.0, "frost")
    if fx["alt_prev"] > 8 and ps["alt"] <= 8 and st in ("land", "idle", "roar", "recover", "dive", "stun") and deadt is None:
        boom(fx, t, wa["body"][0], wa["body"][1] + R.GY0 - 6, 1.6)
        dust_ring(fx, wa["body"][0], wa["body"][1] + R.GY0 - 6, 20, 130, 1.2, "frost")
        fx["rg"].append([t, wa["body"][0], wa["body"][1] + R.GY0 - 6])
        g["shake"] = max(g.get("shake", 0), 0.35)
    fx["alt_prev"] = ps["alt"]
    if e.get("armor_seen_fx") != e.get("armor"):                  # 장갑판이 깨질 때
        if e.get("armor_seen_fx") is not None and e.get("armor", 0) < e["armor_seen_fx"]:
            on_cue(fx, e, g, "break", t)
        e["armor_seen_fx"] = e.get("armor")
    step_particles(fx, dt)
    fx["gh"] = [h for h in fx["gh"] if t - h[3] < 0.3][-6:]
    # ---- 화면에 그리기
    gnd_y = int(e["y"] - cy) + R.GY0
    glow_a = 20 + ph * 14 + 10 * math.sin(t * 3)
    if alpha > 40:
        blit_gl(surf, ex - cx, ey - cy - 4, 110, P["glow"], glow_a * alpha / 255)
    alt = max(0.0, ps["alt"])
    sk = (1 - min(0.55, alt / 200)) * (1.25 if ps["wfold"] < 0.4 else 1.0)
    sw_, sh_ = int(round(124 * sk / 8)) * 8 + 8, int(round(30 * sk / 4)) * 4 + 4
    sa_ = int(95 * (1 - min(0.5, alt / 260))) // 15 * 15
    key = (sw_, sh_, sa_)
    shadow = _SH.get(key)
    if shadow is None:
        shadow = pygame.Surface((sw_, sh_), SC)
        D.ellipse(shadow, (0, 0, 0, sa_), shadow.get_rect())
        _SH[key] = shadow
    surf.blit(shadow, (int(ex - cx) - sw_ // 2, gnd_y - sh_ // 2))
    if st == "high":                                              # 강하 예고: 그림자 둘레에 조준 고리
        rr = 30 + int(6 * math.sin(t * 10))
        D.circle(surf, (150, 230, 255), (int(ex - cx), gnd_y), rr, 1)
    if len(fx["tt"]) > 1:                                         # 꼬리 궤적: 오래된 것일수록 가늘고 어둡게
        for k in range(3):
            pts = [(q[1][k][0] - cx, q[1][k][1] - cy) for q in fx["tt"] if len(q[1]) > k]
            n_ = len(pts)
            for i in range(n_ - 1):
                f = (i + 1) / n_
                col = lerpc((60, 110, 190), (235, 250, 255), f)
                D.line(surf, col, pts[i], pts[i + 1], 1 + int(f * 3))
        blit_gl(surf, ex - cx, ey - cy, 90, (140, 220, 255), 60)
    for gh in fx["gh"]:
        gh[0].set_alpha(int(120 * (1 - (t - gh[3]) / 0.3)))
        surf.blit(gh[0], gh[0].get_rect(center=(int(gh[1] - cx), int(gh[2] - cy))))
    if alpha > 0:
        surf.blit(img, img.get_rect(center=(int(ex - cx) + ox, int(ey - cy) + oy)))
    if st == "breath" and BREATH_DRAW is not None and BREATH_DRAW(surf, mx, my, e.get("lz", 0.0), t):
        blit_gl(surf, mx, my, 40, (150, 230, 255), 150)
    elif st == "breath":
        a = e.get("lz", 0.0)
        for i in range(20, -1, -1):
            d_ = i * 6
            D.circle(surf, lerpc((255, 255, 255), (60, 140, 220), i / 20), (int(mx + math.cos(a) * d_), int(my + math.sin(a) * d_ * 0.8)), int(3 + i * 0.6))
    elif st in ("breath_w",):
        ch = 0.5 + 0.5 * math.sin(t * 12)
        blit_gl(surf, mx, my, 14 + 14 * ch * ps["glow"], (150, 230, 255), 200)
        D.circle(surf, (235, 250, 255), (int(mx), int(my)), 3 + int(2 * ch))
    elif st in ("roar", "glow_w", "pulse"):
        c = Sx(anc["crown"])
        blit_gl(surf, c[0], c[1], 30 + 10 * math.sin(t * 20), (120, 220, 255), 130)
    if st == "stun":
        hx_, hy_ = Sx(anc["top"])
        for i in range(3):
            a = t * 5 + i * 2.094
            surf.fill((200, 245, 255), (int(hx_ + math.cos(a) * 18), int(hy_ - 8 + math.sin(a) * 5), 3, 3))
    if st == "sleep":                                              # 잠: Zzz
        hx_, hy_ = Sx(anc["top"])
        for i in range(3):
            f = (t * 0.6 + i / 3) % 1.0
            s_ = 2 + i
            px_, py_ = int(hx_ + 10 + f * 14), int(hy_ - 6 - f * 22)
            col = lerpc((230, 245, 255), (90, 120, 160), f)
            D.lines(surf, col, False, [(px_, py_), (px_ + s_, py_), (px_, py_ + s_), (px_ + s_, py_ + s_)], 1)
    draw_particles(surf, fx, cx, cy)
    draw_booms(surf, fx, cx, cy, t)
    if t - fx["ph_t"] < 1.4:                                     # 페이즈 전환: 빛기둥과 충격파
        age = t - fx["ph_t"]
        D.circle(surf, P["glow"], (int(ex - cx), int(ey - cy)), int(age * 260), 3)
        for i in range(12):
            h = i * 12
            wv = int(math.sin(t * 20 + i) * 4)
            blit_gl(surf, ex - cx + wv, ey - cy - h, 14 - i // 2, (140, 220, 255), 160 * (1 - age / 1.4))
    if e.get("al", 0) > 0 and deadt is None:
        hx_, hy_ = Sx(anc["top"])
        surf.fill((255, 230, 80), (int(hx_) - 1, int(hy_) - 18, 2, 5))
    return fx


def draw_kaiju(surf, e, cx, cy, t, g):
    try:
        draw_core(surf, e, cx, cy, t, g)
    except Exception:
        G.v9_log("kaiju-fx")


def draw_death(surf, g, cx, cy):
    dy = g.get("kaiju_dying")
    if not dy:
        return
    tt = g["t"] - dy["t0"]
    if tt > 3.4:
        g["kaiju_dying"] = None
        return
    ghost = dict(kind="kaiju", x=dy["x"], y=dy["y"], phase=dy["phase"], fl=0, inv=0, st="death", lz=0.0, an=dy["an"] + tt, al=0,
                 armor=0, mode="fight", _fx=dy["fx"])
    try:
        draw_core(surf, ghost, cx, cy, g["t"], g, deadt=tt)
    except Exception:
        G.v9_log("kaiju-death")
