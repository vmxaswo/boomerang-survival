"""v9 화룡 연출 모듈 (v9_dragon_fx.py)  -  화룡을 3D 뼈대 리그(v9_dragon_rig.py)로 다시 그리고 패턴마다 연기를 시킨다.
 이동
 - 8방향(그 사이 각도 포함)으로 몸을 돌리며 이동한다. 머리가 먼저 돌고 몸통과 꼬리가 늦게 따라온다.
 - 기어다니기: 네 다리가 실제 이동 거리에 맞춰 걷는다 (옆걸음·뒷걸음도 자연스럽게). 페이즈 3의 평상시 이동은 저공비행.
 - 비행: 고도가 올라가면 그림자가 몸에서 떨어지고 날개를 치며 다리를 접는다. 이륙·착지 때 먼지와 충격파.
 패턴별 연기 (준비 -> 실행 -> 후딜)
   fan 탄막: 머리를 뒤로 젖혔다가 뱉을 때마다 튕겨 나옴   breath 숨결: 상체를 들고 가슴이 빛남 -> 목을 휘두르며 불을 뿜음
   charge 돌진: 웅크려 땅을 긁음 -> 질주(잔상) -> 미끄러져 머리를 박고 기절   erupt 분출: 뒷발로 서서 앞발로 땅을 내려찍음
   meteor 유성: 이륙해 높이 떠서 포효, 끝나면 착지   ring 링: 날개를 치켜들었다가 크게 내리쳐 충격파   lanes 줄무늬: 꼬리를 휘두르고 땅을 긁음
   summon 소환: 가슴이 달아오르고 불씨를 토해 냄   nova 폭발: 날개로 몸을 감싸고 떨다가 활짝 펼치며 폭발   spiral 나선: 공중에서 몸을 돌리며 발사
 등장(하늘에서 강하·착지·포효), 페이즈 전환, 처치(연쇄 폭발 -> 쓰러짐 -> 재)
v9_dragon.install 뒤, 가장 마지막에 설치한다:
    import v9_dragon_fx
    v9_dragon_fx.install(G, v9_world, v9_dragon)
(v9_dragon_rig.py 가 같은 폴더에 있어야 한다)
"""
import math
import random

import pygame

import v9_dragon_rig as R

D = pygame.draw
SC = pygame.SRCALPHA
G = W = DR = V = None
INTRO_T = 2.6
PALS = {
    1: dict(base=(168, 40, 36), dark=(112, 26, 32), deep=(64, 16, 26), hi=(222, 92, 60), belly=(236, 184, 108),
            belly_d=(190, 128, 70), horn=(236, 222, 186), eye=(255, 214, 70), wing=(122, 28, 40), wing_d=(86, 20, 32),
            vein=(255, 130, 60), vein_d=(130, 44, 28), glow=(255, 150, 60)),
    2: dict(base=(188, 46, 32), dark=(124, 28, 30), deep=(70, 16, 24), hi=(244, 112, 58), belly=(246, 196, 110),
            belly_d=(200, 134, 70), horn=(240, 226, 190), eye=(255, 160, 40), wing=(140, 30, 38), wing_d=(96, 20, 30),
            vein=(255, 150, 50), vein_d=(150, 50, 26), glow=(255, 120, 50)),
    3: dict(base=(210, 56, 30), dark=(136, 30, 28), deep=(52, 12, 20), hi=(255, 130, 56), belly=(255, 206, 120),
            belly_d=(214, 140, 70), horn=(246, 232, 196), eye=(255, 250, 220), wing=(150, 30, 34), wing_d=(100, 18, 28),
            vein=(255, 210, 90), vein_d=(170, 56, 24), glow=(255, 80, 40)),
}
_SH, _CV, _T = {}, {}, [0.0]
BREATH_DRAW = None                                               # v9_pfx 가 설치되면 탑다운 브레스 그리기 함수가 들어온다
blit_gl = R.blit_gl


def lerpc(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def angdiff(a, b):
    return (a - b + math.pi) % (2 * math.pi) - math.pi


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def pulse(tc, atk, dec):
    """신호(cue)가 온 뒤 tc 초: atk 동안 0->1, 그 뒤 dec 로 사그라든다"""
    if tc < 0:
        return 0.0
    if tc < atk:
        return tc / atk
    return math.exp(-(tc - atk) / dec)


# ================================================================= 포즈 표 (키 의미는 v9_dragon_rig.DEF 참고)
def P_(**k):
    d = dict(R.DEF)
    d.update(k)
    return d


BASE = {
    "idle": P_(),
    "recover": P_(bz=15, hx=44, hz=20, hp=-0.45, mouth=0.25, wfold=1.0, tamp=0.6, brace=0.5),
    "hover": P_(alt=22, bz=18, wfold=0.0, wamp=0.55, wfreq=1.7, wb0=0.3, tuck=0.85, hx=48, hz=30, mouth=0.1, tfreq=2.4),
    "spit_w": P_(bz=18, pitch=0.1, hx=34, hz=33, hp=0.35, nk=1.3, mouth=0.22, wfold=0.55, wb0=0.35, wamp=0.12, wfreq=2.5,
                 brace=0.4, glow=0.5, tlift=4),
    "breath_w": P_(bz=22, pitch=0.32, fz=12, fxo=4, hx=42, hz=44, hp=0.8, nk=1.25, mouth=0.3, wfold=0.1, wb0=0.55, wamp=0.12,
                   wfreq=2.0, glow=1.0, chest=0.12, brace=0.8, tlift=6, tamp=0.4),
    "breath": P_(bz=20, pitch=0.12, hx=54, hz=30, hp=-0.12, mouth=1.0, nk=0.9, wfold=0.0, wb0=0.35, wamp=0.08, wfreq=3.0,
                 glow=1.0, brace=1.0, tlift=7, tamp=0.5),
    "wind": P_(bz=8, pitch=-0.14, hx=50, hz=14, hp=-0.55, mouth=0.3, nk=0.8, wfold=1.0, brace=1.0, tlift=8, tamp=0.25, glow=0.4,
               scr=4.0),
    "dash": P_(bz=11, pitch=-0.08, hx=60, hz=17, hp=-0.22, mouth=0.45, nk=0.8, wfold=1.0, tamp=0.18, glow=0.7, tfreq=5.0),
    "stun": P_(bz=6, pitch=-0.2, hx=52, hz=6, hp=-0.9, mouth=0.0, nk=0.6, wfold=0.5, wb0=-0.5, tamp=0.15, brace=1.0),
    "slam_w": P_(bz=23, pitch=0.34, fz=26, fxo=6, hx=40, hz=46, hp=0.5, mouth=0.6, nk=1.3, wfold=0.05, wb0=0.65, wamp=0.18,
                 wfreq=2.2, glow=0.8, brace=0.7, tlift=9),
    "meteor_w": P_(alt=58, bz=20, pitch=0.12, hx=52, hz=38, hp=0.55, mouth=0.7, wfold=0, wb0=0.3, wamp=0.95, wfreq=1.9, tuck=1.0,
                   tlift=6, tamp=1.4, glow=0.6),
    "meteor": P_(alt=58, bz=20, pitch=0.12, hx=52, hz=38, hp=0.55, mouth=0.9, wfold=0, wb0=0.3, wamp=0.95, wfreq=1.9, tuck=1.0,
                 tlift=6, tamp=1.4, glow=0.8, nk=1.1),
    "land": P_(alt=0, bz=19, pitch=0.2, hx=46, hz=34, hp=0.25, mouth=0.4, wfold=0, wb0=0.5, wamp=0.8, wfreq=3.0, tuck=0.0,
               brace=0.6, tlift=5),
    "ring_w": P_(alt=8, bz=20, pitch=0.1, hx=44, hz=36, hp=0.3, mouth=0.35, wfold=0, wb0=0.9, wsw=-0.3, wamp=0.1, wfreq=2.0,
                 glow=0.7, tuck=0.6, tlift=6),
    "ring": P_(alt=8, bz=20, pitch=0.1, hx=44, hz=36, hp=0.3, mouth=0.35, wfold=0, wb0=0.9, wsw=-0.3, wamp=0.1, wfreq=2.0,
               glow=0.7, tuck=0.6, tlift=6),
    "lanes": P_(bz=12, pitch=-0.05, hx=52, hz=20, hp=-0.35, mouth=0.5, wfold=0.4, wb0=0.2, tamp=2.0, tfreq=5.5, tlift=3, glow=0.6,
                brace=0.9, scr=3.0),
    "summon": P_(bz=22, pitch=0.26, fz=14, fxo=4, hx=40, hz=42, hp=0.55, mouth=0.7, nk=1.2, wfold=0, wb0=0.6, wamp=0.15, wfreq=1.8,
                 glow=1.0, chest=0.1, brace=0.6, tlift=6),
    "nova_w": P_(bz=8, pitch=-0.05, hx=30, hz=12, hp=-0.8, nk=0.6, mouth=0.1, wfold=0, wb0=1.15, wsw=-0.6, wamp=0.06, wfreq=5.0,
                 glow=1.0, chest=0.18, brace=1.0, tcurl=1.0, tamp=0.3),
    "nova": P_(bz=24, pitch=0.38, fz=24, hx=42, hz=52, hp=0.9, nk=1.3, mouth=1.0, wfold=0, wb0=0.4, wsw=0.1, wamp=0.3, wfreq=2.2,
               glow=1.0, brace=0.8, tlift=10),
    "spiral_w": P_(alt=14, bz=19, pitch=0.1, hx=48, hz=34, hp=0.3, mouth=0.4, wfold=0, wb0=0.3, wamp=0.7, wfreq=2.2, tuck=0.8,
                   glow=0.6),
    "spiral": P_(alt=32, bz=20, roll=0.0, hx=50, hz=30, hp=0.0, mouth=0.75, wfold=0, wb0=0.25, wamp=0.7, wfreq=2.4, tuck=1.0,
                 tamp=1.0, tfreq=3.0, glow=0.8),
    "roar": P_(bz=22, pitch=0.3, fz=18, fxo=4, hx=40, hz=48, hp=0.75, nk=1.3, mouth=1.0, wfold=0, wb0=0.45, wamp=0.18, wfreq=2.2,
               glow=0.9, chest=0.12, brace=0.9, tlift=7),
    "fly_in": P_(alt=14, bz=20, pitch=-0.25, hx=56, hz=22, hp=-0.2, mouth=0.5, wfold=0, wb0=0.1, wamp=0.9, wfreq=1.8, tuck=1.0),
    "death": P_(bz=22, pitch=0.3, fz=18, fxo=4, hx=40, hz=48, hp=0.75, nk=1.3, mouth=1.0, wfold=0, wb0=0.45, wamp=0.18,
                wfreq=2.2, glow=0.9, brace=0.9, tlift=7),
}
FAST = ("dash", "wind", "stun", "slam_w", "slam", "ring", "nova", "land")
# 조준하지 않는 패턴 연기 중에는 플레이어를 따라 돌지 않고, 시작할 때의 방향을 유지한다
LOCK = ("lanes", "nova_w", "nova", "spiral_w", "land")
# 플레이어를 겨냥하는 패턴은 빠르게 돌아 정확히 그쪽을 보고 공격한다 (겨냥 방향 = 몸이 보는 방향)
AIM = ("spit_w", "spit", "breath_w", "slam_w", "slam", "ring_w", "ring", "summon", "meteor_w", "meteor")
VALID = set(BASE) | {"breath", "dash", "slam", "spit"}


def build_pose(st, e, tc, t, ph, deadt):
    cn = e.get("cue")
    b = dict(BASE.get(st) or BASE["idle"])

    def kk(*names, atk=0.07, dec=0.25):
        return pulse(tc, atk, dec) if cn in names else 0.0
    if st == "spit":
        b.update(BASE["spit_w"])
        k = kk("spit", atk=0.05, dec=0.22)
        b["hx"] += 16 * k
        b["hz"] -= 6 * k
        b["hp"] -= 0.55 * k
        b["mouth"] += 0.85 * k
        b["pitch"] -= 0.1 * k
        b["bz"] -= 2 * k
    elif st == "slam":
        b.update(BASE["slam_w"])
        d = kk("slam", atk=0.08, dec=0.3)
        b["fz"] *= (1 - d)
        b["pitch"] -= 0.55 * d
        b["hz"] -= 22 * d
        b["hp"] -= 1.0 * d
        b["bz"] -= 6 * d
        b["wb0"] += 0.5 * d
        b["mouth"] = 0.6 + 0.4 * d
    elif st == "ring":
        d = kk("ring", "ring2", atk=0.08, dec=0.35)
        b["wb0"] -= 1.5 * d
        b["wsw"] += 0.8 * d
        b["alt"] += 10 * d
        b["pitch"] -= 0.12 * d
        b["mouth"] += 0.5 * d
    elif st == "lanes":
        d = kk("lane", atk=0.08, dec=0.3)
        b["hz"] -= 8 * d
        b["mouth"] = 0.5 + 0.5 * d
        b["pitch"] -= 0.2 * d
        b["wb0"] += 0.6 * d
        b["wfold"] -= 0.4 * d
    elif st == "summon":
        k = kk("spawn", atk=0.06, dec=0.25)
        b["hx"] += 14 * k
        b["hp"] -= 0.5 * k
        b["mouth"] += 0.3 * k
        b["pitch"] -= 0.12 * k
    elif st == "nova":
        k = kk("ring2", atk=0.06, dec=0.3)
        b["pitch"] -= 0.1 * k
        b["wb0"] += 0.25 * k
    elif st == "breath":
        b["hz"] += math.sin(t * 45) * 0.8
    elif st == "nova_w":
        b["wb0"] += math.sin(t * 38) * 0.04
    elif st == "death" and deadt is not None and deadt > 1.5:      # 처치: 쓰러진다
        u = min(1.0, (deadt - 1.5) / 0.9)
        b.update(bz=22 - 16 * u, pitch=0.3 - 0.5 * u, hz=48 - 40 * u, hp=0.75 - 1.6 * u, mouth=1.0 - 0.7 * u, wb0=0.45 - 1.0 * u,
                 wfold=0.5 * u, wamp=0.0, fz=18 * (1 - u), tamp=0.15, glow=0.9)
    if ph >= 2:
        b["glow"] = max(b["glow"], 0.12 * (ph - 1))
    if e.get("fl", 0) > 0:                                        # 맞았을 때 움찔
        f = min(1.0, e["fl"] / 0.12)
        b["hx"] -= 5 * f
        b["hz"] += 2 * f
        b["mouth"] += 0.4 * f
        b["pitch"] += 0.08 * f
    return b


# ================================================================= 입자와 효과
def emit(fx, kind, x, y, vx, vy, life, size=1):
    if len(fx["p"]) < 260:
        fx["p"].append([x, y, vx, vy, life, life, kind, size])


def step_particles(fx, dt):
    for p in fx["p"]:
        p[0] += p[2] * dt
        p[1] += p[3] * dt
        p[4] -= dt
        if p[6] == "ember":
            p[3] -= 8 * dt
        elif p[6] == "smoke":
            p[3] -= 6 * dt
        elif p[6] == "dust":
            p[2] *= 0.96
            p[3] *= 0.96
    fx["p"] = [p for p in fx["p"] if p[4] > 0]
    fx["bm"] = [b for b in fx["bm"] if _T[0] - b[0] < 0.5]
    fx["rg"] = [r for r in fx["rg"] if _T[0] - r[0] < 1.0]


def draw_particles(surf, fx, cx, cy):
    for p in fx["p"]:
        f = p[4] / p[5]
        x, y = int(p[0]) - cx, int(p[1]) - cy
        if p[6] == "ember":
            s = p[7] if f > 0.3 else 1
            surf.fill(lerpc((255, 236, 150), (190, 40, 20), 1 - f), (x, y, s, s))
        elif p[6] == "smoke":
            blit_gl(surf, x, y, 3 + (1 - f) * 6, (66, 54, 60), 100 * f + 20)
        elif p[6] == "dust":
            blit_gl(surf, x, y, 3 + (1 - f) * 7, (150, 126, 106), 90 * f + 10)
        elif p[6] == "flame":
            D.circle(surf, lerpc((255, 220, 120), (200, 50, 20), 1 - f), (x, y), max(1, int(p[7] * f)))
        else:
            D.line(surf, (255, 240, 170), (x, y), (x - int(p[2] * 0.04), y - int(p[3] * 0.04)), 1)


def draw_booms(surf, fx, cx, cy, t):
    for b in fx["bm"]:
        age = t - b[0]
        x, y, sz = int(b[1]) - cx, int(b[2]) - cy, b[3]
        blit_gl(surf, x, y, 14 * sz + age * 60 * sz, (255, 220, 140), 200 * (1 - age / 0.5))
        D.circle(surf, lerpc((255, 250, 220), (220, 70, 30), age / 0.5), (x, y), max(1, int(age * 90 * sz)), 2)
    for r in fx["rg"]:
        age = t - r[0]
        rr = max(1, int(age * 190))
        D.ellipse(surf, lerpc((255, 210, 130), (70, 24, 24), age), (int(r[1]) - cx - rr, int(r[2]) - cy - rr * 0.6, rr * 2, int(rr * 1.2)), 2)


def boom(fx, t, x, y, sz=1.0):
    fx["bm"].append([t, x, y, sz])
    for _ in range(int(8 * sz)):
        a, v = random.random() * 6.283, random.uniform(40, 120) * sz
        emit(fx, "spark", x, y, math.cos(a) * v, math.sin(a) * v, random.uniform(0.3, 0.7))
        emit(fx, "ember", x, y, math.cos(a) * v * 0.5, math.sin(a) * v * 0.5 - 20, random.uniform(0.6, 1.4), 2)


def dust_ring(fx, x, y, n=10, sp=70.0, big=1.0):
    for i in range(n):
        a = i / n * 6.283 + random.uniform(-0.2, 0.2)
        v = sp * random.uniform(0.6, 1.2)
        emit(fx, "dust", x, y, math.cos(a) * v, math.sin(a) * v * 0.55, random.uniform(0.5, 0.9) * big)


def new_fx(t, e=None, g=None):
    ang = 0.0
    if e is not None and g is not None:
        ang = math.atan2(g["y"] - e["y"], g["x"] - e["x"])
    return dict(rig=R.new_state(), ang=ang, t=t, p=[], bm=[], rg=[], gh=[], acc=0.0, sm=0.0, rr=0.0, ph_seen=None, ph_t=-9.0,
                gt=0.0, landed=False, lx=None, ly=None, vx=0.0, vy=0.0, cue_seen=None, wa=None, alt_prev=0.0, wcyc=0, dt_=0.0,
                dust_t=0.0)


def eff_state(e, g, intro_on, ti):
    if intro_on:
        return "fly_in" if ti < 0.9 else "roar"
    if e["inv"] > 0 and e["st"] in ("roar", "idle"):
        return "roar"
    s = e["st"]
    if s == "idle" and e["phase"] >= 3:
        return "hover"
    return s if s in VALID else "idle"


def on_cue(fx, e, g, name, t):
    wa = fx.get("wa")
    if not wa:
        return
    feet, mouth, body = wa["feet"], wa["mouth"], wa["body"]
    gx, gy = body[0], body[1] + R.GY0 - 6
    if name == "slam":
        for k in (0, 2):
            fxp = feet[k]
            boom(fx, t, fxp[0], fxp[1], 1.1)
            dust_ring(fx, fxp[0], fxp[1], 8, 80)
        fx["rg"].append([t, (feet[0][0] + feet[2][0]) / 2, (feet[0][1] + feet[2][1]) / 2])
    elif name == "launch":
        for fp in feet:
            dust_ring(fx, fp[0], fp[1], 5, 90)
        fx["rg"].append([t, gx, gy])
    elif name == "crash":
        boom(fx, t, mouth[0], mouth[1] + 6, 1.4)
        for fp in feet:
            dust_ring(fx, fp[0], fp[1], 7, 100)
        fx["rg"].append([t, gx, gy])
    elif name in ("ring", "ring2"):
        fx["rg"].append([t, gx, gy])
        dust_ring(fx, gx, gy, 14, 110)
        for _ in range(10):
            a = random.random() * 6.283
            emit(fx, "ember", gx, gy - 14, math.cos(a) * 90, math.sin(a) * 60 - 20, random.uniform(0.5, 1.0), 2)
    elif name == "lane":
        for k in (0, 2):
            dust_ring(fx, feet[k][0], feet[k][1], 8, 90)
        boom(fx, t, mouth[0], mouth[1], 0.8)
    elif name in ("spit", "spawn", "ignite"):
        boom(fx, t, mouth[0], mouth[1], 0.7 if name != "ignite" else 1.0)
        for _ in range(8):
            a = e.get("lz", 0.0) + random.uniform(-0.6, 0.6) if name == "ignite" else math.atan2(g["y"] - mouth[1], g["x"] - mouth[0]) + random.uniform(-0.4, 0.4)
            v = random.uniform(70, 150)
            emit(fx, "ember", mouth[0], mouth[1], math.cos(a) * v, math.sin(a) * v, random.uniform(0.4, 0.8), 2)
    elif name == "burst":
        boom(fx, t, body[0], body[1], 2.6)
        fx["rg"].append([t, gx, gy])
        fx["rg"].append([t + 0.12, gx, gy])
        for _ in range(40):
            a = random.random() * 6.283
            emit(fx, "ember", body[0], body[1], math.cos(a) * random.uniform(30, 150), math.sin(a) * random.uniform(30, 150) - 20,
                 random.uniform(0.7, 1.5), 2)
        dust_ring(fx, gx, gy, 18, 130)


# ================================================================= 한 프레임
def motion(fx, e, g, st, dt, t, deadt):
    """속도·진행 방향·머리 시선을 갱신하고 (속력, 앞방향 속도, 회전속도, 시선) 을 돌려준다"""
    if fx["lx"] is None or dt <= 1e-5:
        fx["lx"], fx["ly"] = e["x"], e["y"]
        return fx["vx"], fx["vy"], 0.0, 0.0
    k = 1 - math.exp(-dt * 12)
    fx["vx"] += ((e["x"] - fx["lx"]) / dt - fx["vx"]) * k
    fx["vy"] += ((e["y"] - fx["ly"]) / dt - fx["vy"]) * k
    fx["lx"], fx["ly"] = e["x"], e["y"]
    vx, vy = fx["vx"], fx["vy"]
    sp = math.hypot(vx, vy)
    if deadt is not None or sp > 700:
        sp, vx, vy = 0.0, 0.0, 0.0
    h = fx["ang"]
    pa = math.atan2(g["y"] - e["y"], g["x"] - e["x"])
    lz = e.get("lz", 0.0)
    rate, look = 2.4, 0.0
    if st in ("dash", "wind"):
        tgt, rate = lz, 9.0
    elif st == "breath":
        tgt, rate, look = lz, 1.7, clamp(angdiff(lz, h) * 1.5, -1.25, 1.25)
    elif st in ("spiral",):
        tgt, rate = lz, 8.0
    elif st in ("stun", "death"):
        tgt, rate, look = h, 0.0, (math.sin(t * 3) * 0.3 if st == "stun" else 0.0)
    elif st in AIM:                                               # 겨냥 패턴: 빠르게 플레이어 쪽으로 정렬
        tgt, rate = pa, 5.0
        look = clamp(angdiff(pa, h) * 0.8, -0.95, 0.95)
    elif st in LOCK:                                              # 패턴 연기 중에는 시작할 때의 방향을 유지
        tgt, rate, look = h, 0.0, (math.sin(t * 2.4) * 0.75 if st == "lanes" else 0.0)
    else:
        tgt = pa
        if sp > 12 and st in ("idle", "hover", "recover", "spit_w", "spit"):
            diff = angdiff(math.atan2(vy, vx), pa)
            tgt = pa if abs(diff) > 2.2 else pa + diff * 0.7
        look = clamp(angdiff(pa, h) * 0.8, -0.95, 0.95)
    step = clamp(angdiff(tgt, h), -rate * dt, rate * dt)
    fx["ang"] = h + step
    turn = step / dt
    vf = vx * math.cos(fx["ang"]) + vy * math.sin(fx["ang"])
    return sp, vf, turn, look


def draw_core(surf, e, cx, cy, t, g, deadt=None):
    fx = e.setdefault("_fx", new_fx(t, e, g))
    _T[0] = t
    dt = max(0.0, min(0.08, t - fx["t"]))
    fx["t"] = t
    ph = e["phase"]
    P = PALS[ph]
    intro = g.get("intro", 0.0) if (g.get("lock") and deadt is None) else 0.0
    ti = INTRO_T - intro if intro > 0 else 9.0
    st = "death" if deadt is not None else eff_state(e, g, intro > 0, ti)
    rig = fx["rig"]
    ps = rig["ps"]
    sp, vf, turn, look = motion(fx, e, g, st, dt, t, deadt)
    tc = t - e.get("cue_t", -99.0)
    tg = build_pose(st, e, tc, t, ph, deadt)
    tg["hyaw"] = look
    flying = ps["alt"] > 8
    tg["roll"] += clamp(-turn * (0.07 if flying else 0.03), -0.3, 0.3)
    if st == "spiral":
        tg["roll"] += 0.42 * (1 if e.get("spin", 1) > 0 else -1)
    if flying and sp > 20:
        tg["pitch"] -= 0.12 * min(1.0, sp / 120)
    R.update(rig, tg, dt, 14 if st in FAST else 9, vf, sp, turn)
    if fx["ph_seen"] != ph:                                      # 페이즈 전환 폭발
        if fx["ph_seen"] is not None:
            fx["ph_t"] = t
            boom(fx, t, e["x"], e["y"], 2.0)
            for _ in range(60):
                a = random.random() * 6.283
                emit(fx, "ember", e["x"], e["y"], math.cos(a) * random.uniform(20, 110), math.sin(a) * random.uniform(20, 110) - 30,
                     random.uniform(0.8, 1.8), 2)
        fx["ph_seen"] = ph
    yoff, shadow_k = 0.0, 1.0
    if intro > 0 and ti < 0.9:                                   # 하늘에서 강하
        u = ti / 0.9
        yoff, shadow_k = -190 * (1 - u) ** 2, 0.3 + 0.7 * u
        if random.random() < 0.6:
            emit(fx, "smoke", e["x"] + random.uniform(-40, 40), e["y"] + 20, random.uniform(-30, 30), random.uniform(10, 40), 0.7)
    if intro > 0 and ti >= 0.9 and not fx["landed"]:
        fx["landed"] = True
        boom(fx, t, e["x"], e["y"] + 18, 2.2)
        dust_ring(fx, e["x"], e["y"] + 20, 26, 110, 1.3)
    ex, ey = e["x"], e["y"] + yoff
    # ---- 입자 방출
    fx["acc"] += dt * (10 + 9 * ph)
    while fx["acc"] >= 1:
        fx["acc"] -= 1
        emit(fx, "ember", ex + random.uniform(-34, 34), ey + random.uniform(-26, 8), random.uniform(-10, 10), random.uniform(-30, -12),
             random.uniform(0.8, 1.7), 2 if ph >= 3 else 1)
    flash = 0
    if e["fl"] > 0:
        flash = 120
    elif e["inv"] > 0 and int(t * 18) % 2 and deadt is None:
        flash = 50
    ox = oy = 0
    alpha = 255
    if deadt is not None:                                        # 처치 연출
        flash = int(40 + 70 * (0.5 + 0.5 * math.sin(deadt * 30))) if deadt < 2.4 else 200
        a = max(0.0, 3.0 - deadt * 1.2)
        ox, oy = random.randint(-int(a) - 1, int(a) + 1), random.randint(-int(a) - 1, int(a) + 1)
        if deadt < 2.2 and random.random() < 0.35:
            boom(fx, t, ex + random.uniform(-40, 40), ey + random.uniform(-30, 14), random.uniform(0.7, 1.3))
            G.play("boom")
        if deadt > 1.9:
            alpha = int(255 * max(0.0, 1 - (deadt - 1.9) / 1.0))
        if 2.5 < deadt < 2.6 and not fx.get("fin"):
            fx["fin"] = True
            boom(fx, t, ex, ey, 3.5)
            G.play("boss")
        if deadt > 2.0:
            for _ in range(3):
                emit(fx, "ember", ex + random.uniform(-40, 40), ey + random.uniform(-30, 20), random.uniform(-20, 20),
                     random.uniform(-60, -20), random.uniform(0.8, 1.6), 2)
    # ---- 렌더
    if "cv" not in _CV:
        _CV["cv"] = pygame.Surface((R.CW, R.CH), SC)
    img = _CV["cv"]
    img.fill((0, 0, 0, 0))
    anc = R.draw(img, rig, P, ph, t, fx["ang"])
    if flash > 0:
        img.fill((flash, flash, flash, 0), special_flags=pygame.BLEND_RGB_ADD)
    img.set_alpha(alpha)                                         # None 은 픽셀별 알파까지 꺼서 검은 네모가 생긴다

    def Sx(p):                                                   # 도화지 -> 화면
        return (ex - cx + (p[0] - R.CX), ey - cy + (p[1] - R.CY))

    def Wx(p):                                                   # 도화지 -> 월드
        return (ex + (p[0] - R.CX), ey + (p[1] - R.CY))
    fx["wa"] = dict(mouth=Wx(anc["mouth"]), body=Wx(anc["body"]), feet=[Wx(p) for p in anc["feet"]], nose=Wx(anc["nose"]),
                    head=Wx(anc["head"]), tail=Wx(anc["tail"]), tips=[Wx(p) for p in anc["tips"]], top=Wx(anc["top"]))
    wa = fx["wa"]
    if e.get("cue_t") is not None and fx["cue_seen"] != e["cue_t"]:
        fx["cue_seen"] = e["cue_t"]
        on_cue(fx, e, g, e.get("cue"), t)
    mx, my = Sx(anc["mouth"])
    # ---- 상태별 지속 효과
    fx["sm"] -= dt
    if fx["sm"] <= 0:
        fx["sm"] = 0.4 if st != "stun" else 0.12
        emit(fx, "smoke", wa["nose"][0], wa["nose"][1], 10, -22, 1.0)
    if st == "roar" and t - fx["rr"] > 0.4:
        fx["rr"] = t
        fx["rg"].append([t, wa["mouth"][0], wa["mouth"][1]])
    flame_a = e.get("lz", 0.0)
    if st == "breath":
        for _ in range(2):
            a = flame_a + random.uniform(-0.25, 0.25)
            v = random.uniform(80, 150)
            emit(fx, "ember", wa["mouth"][0], wa["mouth"][1], math.cos(a) * v, math.sin(a) * v, random.uniform(0.4, 0.9), 2)
    elif st in ("breath_w", "spit_w", "summon", "nova_w", "slam_w"):
        c = wa["body"] if st == "nova_w" else wa["mouth"]
        for _ in range(2):
            a = random.random() * 6.283
            emit(fx, "spark", c[0] + math.cos(a) * 30, c[1] + math.sin(a) * 30, -math.cos(a) * 90, -math.sin(a) * 90, 0.3)
    elif st == "dash":
        if t - fx["gt"] > 0.035:
            fx["gt"] = t
            gh = img.copy()
            gh.fill((255, 130, 60, 255), special_flags=pygame.BLEND_RGBA_MULT)
            fx["gh"].append([gh, ex, ey, t])
        if t - fx["dust_t"] > 0.05:
            fx["dust_t"] = t
            for fp in wa["feet"]:
                emit(fx, "dust", fp[0], fp[1], -math.cos(fx["ang"]) * 50, random.uniform(-15, 5), 0.6)
    elif st in ("wind", "lanes") and t - fx["dust_t"] > 0.08:
        fx["dust_t"] = t
        fp = wa["feet"][random.choice((0, 2))]
        emit(fx, "dust", fp[0], fp[1], random.uniform(-30, 30), random.uniform(-25, -5), 0.6)
    elif st in ("meteor", "spiral", "meteor_w", "spiral_w"):
        for tp in wa["tips"]:
            if random.random() < 0.3:
                emit(fx, "ember", tp[0], tp[1], random.uniform(-15, 15), random.uniform(10, 40), 0.7, 2)
        if st in ("meteor", "spiral") and random.random() < 0.5:
            emit(fx, "ember", wa["mouth"][0], wa["mouth"][1], random.uniform(-40, 40), random.uniform(-40, 40), 0.5, 2)
        if st == "spiral":
            emit(fx, "ember", wa["tail"][0], wa["tail"][1], random.uniform(-20, 20), random.uniform(-20, 20), 0.5, 2)
    if ph >= 3 and ps["alt"] > 8 and random.random() < 0.25:
        tp = random.choice(wa["tips"])
        emit(fx, "ember", tp[0], tp[1], random.uniform(-10, 10), random.uniform(5, 25), 0.8, 2)
    cyc = int(rig["wph"] / 6.2832)                               # 날갯짓 바람: 낮게 떠 있을 때 먼지
    if cyc != fx["wcyc"]:
        fx["wcyc"] = cyc
        if 0 < ps["alt"] < 34 and ps["wamp"] > 0.3:
            dust_ring(fx, wa["body"][0], wa["body"][1] + R.GY0 - 6, 8, 80)
    if fx["alt_prev"] > 8 and ps["alt"] <= 8 and st in ("land", "idle", "roar", "recover", "hover") and deadt is None:
        boom(fx, t, wa["body"][0], wa["body"][1] + R.GY0 - 6, 1.6)           # 착지
        dust_ring(fx, wa["body"][0], wa["body"][1] + R.GY0 - 6, 18, 120, 1.2)
        fx["rg"].append([t, wa["body"][0], wa["body"][1] + R.GY0 - 6])
        g["shake"] = max(g.get("shake", 0), 0.35)
    fx["alt_prev"] = ps["alt"]
    step_particles(fx, dt)
    fx["gh"] = [h for h in fx["gh"] if t - h[3] < 0.3][-6:]
    # ---- 화면에 그리기
    gnd_y = int(e["y"] - cy) + R.GY0
    glow_a = 26 + ph * 14 + 10 * math.sin(t * 3)
    blit_gl(surf, ex - cx, ey - cy - 4, 100, P["glow"], glow_a)
    alt = max(0.0, ps["alt"]) + (-yoff * 0.0)
    sk = shadow_k * (1 - min(0.5, alt / 120)) * (1.25 if ps["wfold"] < 0.4 else 1.0)
    sw_, sh_, sa_ = int(round(110 * sk / 8)) * 8 + 8, int(round(26 * sk / 4)) * 4 + 4, int(90 * (1 - min(0.6, alt / 100))) // 15 * 15
    key = (sw_, sh_, sa_)
    shadow = _SH.get(key)
    if shadow is None:
        shadow = pygame.Surface((sw_, sh_), SC)
        D.ellipse(shadow, (0, 0, 0, sa_), shadow.get_rect())
        _SH[key] = shadow
    surf.blit(shadow, (int(ex - cx) - sw_ // 2, gnd_y - sh_ // 2))
    for gh in fx["gh"]:
        gh[0].set_alpha(int(120 * (1 - (t - gh[3]) / 0.3)))
        surf.blit(gh[0], gh[0].get_rect(center=(int(gh[1] - cx), int(gh[2] - cy))))
    surf.blit(img, img.get_rect(center=(int(ex - cx) + ox, int(ey - cy) + oy)))
    if st == "breath" and BREATH_DRAW is not None and BREATH_DRAW(surf, mx, my, flame_a, t):   # 화염 방사 (pixelfx 탑다운 브레스)
        blit_gl(surf, mx, my, 40, (255, 190, 90), 150)
    elif st == "breath":                                         # 화염 방사 (시트가 없을 때)
        a = flame_a
        for i in range(24, -1, -1):
            d_ = i * 7 + random.uniform(-2, 2)
            r_ = 3 + i * 0.75
            col = lerpc((255, 255, 230), (200, 40, 20), i / 24)
            D.circle(surf, col, (int(mx + math.cos(a) * d_ + math.sin(t * 40 + i) * 2), int(my + math.sin(a) * d_ * 0.8 + math.cos(t * 37 + i) * 2)),
                     int(r_))
        blit_gl(surf, mx, my, 44, (255, 190, 90), 170)
    elif st in ("breath_w", "spit_w", "spit", "summon"):         # 불덩이 충전
        ch = 0.5 + 0.5 * math.sin(t * 12)
        blit_gl(surf, mx, my, 14 + 12 * ch * ps["glow"], (255, 170, 70), 200)
        D.circle(surf, (255, 240, 190), (int(mx), int(my)), 3 + int(2 * ch))
    elif st == "roar" or deadt is not None:
        blit_gl(surf, mx, my, 30, (255, 150, 60), 120)
    elif st == "nova_w":                                         # 폭발 전: 몸이 달아오른다
        bx, by = Sx(anc["body"])
        blit_gl(surf, bx, by, 34 + 14 * ps["glow"], (255, 150, 60), 120 + 80 * (0.5 + 0.5 * math.sin(t * 20)))
    if st == "stun":
        hx_, hy_ = Sx(anc["top"])
        for i in range(3):
            a = t * 5 + i * 2.094
            surf.fill((255, 240, 150), (int(hx_ + math.cos(a) * 16), int(hy_ - 8 + math.sin(a) * 5), 2, 2))
    draw_particles(surf, fx, cx, cy)
    draw_booms(surf, fx, cx, cy, t)
    if t - fx["ph_t"] < 1.4:                                     # 페이즈 전환 불기둥과 충격파
        age = t - fx["ph_t"]
        D.circle(surf, P["glow"], (int(ex - cx), int(ey - cy)), int(age * 260), 3)
        for i in range(12):
            h = i * 12
            wv = int(math.sin(t * 20 + i) * 4)
            blit_gl(surf, ex - cx + wv, ey - cy - h, 14 - i // 2, (255, 150, 60), 160 * (1 - age / 1.4))
    if e["al"] > 0 and deadt is None:
        hx_, hy_ = Sx(anc["top"])
        surf.fill((255, 230, 80), (int(hx_) - 1, int(hy_) - 18, 2, 5))
    return fx


def draw_dragon_fx(surf, e, cx, cy, t, g):
    try:
        draw_core(surf, e, cx, cy, t, g)
    except Exception:
        G.v9_log("dragon-fx")


def draw_death(surf, g, cx, cy):
    dy = g.get("dragon_dying")
    if not dy:
        return
    tt = g["t"] - dy["t0"]
    if tt > 3.4:
        g["dragon_dying"] = None
        return
    ghost = dict(kind="dragon", x=dy["x"], y=dy["y"], fc=dy["fc"], phase=dy["phase"], fl=0, inv=0, st="death", lz=0.0,
                 an=dy["an"] + tt, al=0, _fx=dy["fx"])
    try:
        draw_core(surf, ghost, cx, cy, g["t"], g, deadt=tt)
    except Exception:
        G.v9_log("dragon-death")


# ================================================================= 패턴 연기: 기존 패턴을 감싸 준비 동작·상태·신호(cue)를 넣는다
def cue(g, e, name):
    e["cue"], e["cue_t"] = name, g["t"]


def shake(g, v):
    g["shake"] = max(g.get("shake", 0), v)


def w_fan(g, e, orig):
    e["st"] = "spit_w"
    yield 0.32                                                   # 머리를 뒤로 젖히며 불덩이를 모은다
    for y in orig(g, e):
        if e["st"] == "spit":
            cue(g, e, "spit")
        else:
            e["st"] = "recover"
        yield y


def w_breath(g, e, orig):
    last = None
    for y in orig(g, e):
        s = e["st"]
        if s != last:
            if s == "breath":
                cue(g, e, "ignite")
                shake(g, 0.3)
            last = s
        if s == "idle":
            e["st"] = "recover"
        yield y


def w_erupt(g, e, orig):
    e["st"] = "slam_w"
    yield 0.45                                                   # 뒷발로 일어선다
    for y in orig(g, e):
        if e["st"] == "roar":
            e["st"] = "slam"
            cue(g, e, "slam")                                    # 앞발로 땅을 내려찍는다
            shake(g, 0.22)
        elif e["st"] == "idle":
            e["st"] = "recover"
        yield y


def w_charge(g, e, orig):
    last = None
    for y in orig(g, e):
        s = e["st"]
        if s != last:
            if s == "dash":
                cue(g, e, "launch")
                shake(g, 0.15)
            elif s == "stun":
                cue(g, e, "crash")
                shake(g, 0.45)
            last = s
        if s == "idle":
            e["st"] = "recover"
        yield y


def w_ring(g, e, orig):
    e["st"] = "ring_w"
    yield 0.4                                                    # 날개를 치켜든다
    for y in orig(g, e):
        if y > 0.5:
            e["st"] = "ring"
            cue(g, e, "ring")                                    # 크게 내리쳐 충격파
            shake(g, 0.2)
        else:
            e["st"] = "recover"
        yield y


def w_meteor(g, e, orig):
    e["st"] = "meteor_w"
    yield 0.7                                                    # 이륙
    for y in orig(g, e):
        if e["st"] == "roar":
            e["st"] = "meteor"
        elif e["st"] == "idle":
            e["st"] = "land"                                     # 착지
        yield y


def w_lanes(g, e, orig):
    e["st"] = "lanes"
    for i, y in enumerate(orig(g, e)):
        try:
            t1 = float(V.tm(1.2 if i == 0 else 1.0))
        except Exception:
            t1 = y * 0.5
        if 0.05 < t1 < y:
            yield t1                                             # 경고선이 그어지는 동안 꼬리를 휘두른다
            cue(g, e, "lane")                                    # 땅을 내려찍으며 줄무늬 발동
            shake(g, 0.2)
            yield y - t1
        else:
            yield y
    e["st"] = "recover"
    yield 0.4


def w_summon(g, e, orig):
    for i, y in enumerate(orig(g, e)):
        if i == 0:
            e["st"] = "summon"                                   # 가슴이 달아오른다
        else:
            cue(g, e, "spawn")                                   # 불씨를 토해 폭탄병 소환
            e["st"] = "recover"
        yield y


def w_nova(g, e, orig):
    for i, y in enumerate(orig(g, e)):
        if i == 0:
            try:
                t1 = float(V.tm(1.4))
            except Exception:
                t1 = y * 0.7
            e["st"] = "nova_w"                                   # 날개로 몸을 감싸고 떤다
            if 0.05 < t1 < y:
                yield t1
                y = y - t1
            e["st"] = "nova"
            cue(g, e, "burst")                                   # 활짝 펼치며 폭발
            shake(g, 0.7)
        elif y == 0.4:
            e["st"] = "recover"
        else:
            cue(g, e, "ring2")
        yield y


def w_spiral(g, e, orig):
    a, dr = random.random() * 6.283, random.choice((-1, 1))
    e["st"] = "spiral_w"
    e["lz"] = a
    yield 0.5                                                    # 떠오르며 날개를 편다
    e["st"], e["spin"] = "spiral", dr
    for i in range(int(3.2 / 0.08)):
        e["lz"] = a
        for k in range(3):
            V.fire(g, e, a + k * 2.0944, 95, 0, 5.0)
        a += dr * 0.34
        if i % 4 == 0:
            G.play("shoot")
        yield 0.08
    e["st"] = "recover"
    yield 0.5
    e["st"] = "idle"


WRAP = dict(fan=w_fan, breath=w_breath, erupt=w_erupt, charge=w_charge, ring=w_ring, meteor=w_meteor, lanes=w_lanes,
            summon=w_summon, nova=w_nova, spiral=w_spiral)


def mk_wrap(name, fn):
    w = WRAP[name]

    def f(g, e):
        yield from w(g, e, fn)
        if e["st"] in ("recover", "land", "spit", "ring", "slam", "nova", "summon", "lanes", "spit_w", "ring_w", "slam_w"):
            e["st"] = "idle"
    return f


# ================================================================= 설치
def install(g_mod, world_mod, dragon_mod):
    global G, W, DR, V
    G, W, DR = g_mod, world_mod, dragon_mod
    V = DR.V
    DR.draw_dragon = draw_dragon_fx
    old_mk = DR.mk_dragon

    def mk_dragon(x, y):
        e = old_mk(x, y)
        e["r"] = 30
        return e
    DR.mk_dragon = mk_dragon
    if not getattr(DR, "_fx_wrapped", False):                    # 패턴 감싸기 (한 번만)
        DR._fx_wrapped = True
        for ph in list(DR.POOLS):
            DR.POOLS[ph] = [(n, mk_wrap(n, fn) if n in WRAP else fn, w, c) for (n, fn, w, c) in DR.POOLS[ph]]
    old_cam, old_update, old_kill, old_load, old_arena = G.camera, G.update, G.kill, G.load_zone, G.draw_arena

    def dragon_of(g):
        return next((o for o in g["en"] if o["kind"] == "dragon" and o["hp"] > 0), None)

    def camera(g):
        cx, cy = old_cam(g)
        if g.get("zid") == DR.ZID and g.get("lock") and g.get("intro", 0) > 0:
            e = dragon_of(g)
            if e:
                ti = INTRO_T - g["intro"]
                a, b = min(1.0, ti / 0.5), min(1.0, g["intro"] / 0.5)
                k = (a * a * (3 - 2 * a)) * (b * b * (3 - 2 * b))
                tx = min(max(int(e["x"]) - G.W // 2, 0), g["wt"] * G.T - G.W)
                ty = min(max(int(e["y"]) - G.H // 2 - 10, 0), g["ht"] * G.T - G.H)
                return int(cx + (tx - cx) * k), int(cy + (ty - cy) * k)
        return cx, cy

    def update(g, inp, dt):
        intro_on = g.get("zid") == DR.ZID and g.get("lock") and g.get("intro", 0) > 0 and g["mode"] == "play" and not g["tr"]
        if intro_on:
            inp = (0, 0, False)
        old_update(g, inp, dt)
        if intro_on:
            e = dragon_of(g)
            if e:
                fx = e.get("_fx")
                if fx and fx["landed"] and not e.get("_shook"):
                    e["_shook"] = True
                    g["shake"] = max(g["shake"], 0.6)
                    G.play("boom")
                    g["rings"].append([e["x"], e["y"] + 10, 0.0, 90, (255, 190, 110)])
                if INTRO_T - g["intro"] >= 1.0 and not e.get("_roar"):
                    e["_roar"] = True
                    G.play("boss")

    def kill(g, e):
        if e["kind"] == "dragon":
            g["dragon_dying"] = dict(x=e["x"], y=e["y"], fc=e["fc"], phase=e["phase"], t0=g["t"], an=e["an"],
                                     fx=e.get("_fx") or new_fx(g["t"], e, g))
        return old_kill(g, e)

    def load_zone(g, zid, tx, ty):
        g["dragon_dying"] = None
        return old_load(g, zid, tx, ty)

    def draw_arena(surf, g, cx, cy):
        old_arena(surf, g, cx, cy)
        if g.get("zid") == DR.ZID and g.get("dragon_dying"):
            draw_death(surf, g, cx, cy)
    G.camera, G.update, G.kill, G.load_zone, G.draw_arena = camera, update, kill, load_zone, draw_arena