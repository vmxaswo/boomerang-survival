"""v9 보스 3D 리그 도구 (v9_ba_r3.py)  -  화룡 리그와 같은 방식(3D 모델 -> 쿼터뷰 도트)을 보스에 쓰기 위한 도구함.
 - 부품(상자·절두체·캡슐·구·다각형)을 3D 좌표로 정의하고, 바라보는 각도(heading, 0 = 오른쪽, 90도 = 아래)만큼 돌려
   위에서 약 42도로 내려다보는 시점에 투영한 뒤, 먼 부위부터 그린다(화가 알고리즘).
 - 면마다 월드 좌표의 빛(왼쪽 위)과의 각도로 3톤 명암을 입히므로, 몸을 돌려도 빛 방향이 일정하다.
 - 최종 크기(1:1 도트)에서 직접 그리므로 축소·확대로 흐려지지 않는다.
좌표계: x = 앞, y = 오른쪽, z = 위 (모델 단위 = 화면 픽셀)."""
import math

import pygame

import v9_ba_kit as K
from v9_ba_kit import OUT, drk, lit, mix

D = pygame.draw
R3W, R3H, R3X, R3Y = 220, 190, 110, 150          # 도화지 크기, 기준점(발 밑 중심)
_EL = math.radians(42)
SE, CE = math.sin(_EL), math.cos(_EL)
_LIGHT = (-0.42, -0.55, 0.72)
_L = math.sqrt(sum(v * v for v in _LIGHT))
LIGHT = tuple(v / _L for v in _LIGHT)
VIEW = (0.0, CE, SE)                              # 화면 쪽(보는 사람 쪽)을 향하는 방향
_CV = {}


def canvas(key):
    cv = _CV.get(key)
    if cv is None:
        cv = _CV[key] = pygame.Surface((R3W, R3H), pygame.SRCALPHA)
    cv.fill((0, 0, 0, 0))
    return cv


class Scene:
    """한 프레임 분량의 부품 목록. add_* 로 쌓고 flush() 로 먼 것부터 그린다."""

    def __init__(self, cv, heading, z0=0.0, ox=R3X, oy=R3Y, k=1.0):
        self.k = k
        self.cv = cv
        self.c, self.s = math.cos(heading), math.sin(heading)
        self.z0, self.ox, self.oy = z0, ox, oy
        self.q = []

    # ----- 좌표
    def world(self, p):
        k = self.k
        return (k * (p[0] * self.c - p[1] * self.s), k * (p[0] * self.s + p[1] * self.c), k * p[2] + self.z0)

    def pj(self, p):
        w = self.world(p)
        return (self.ox + w[0], self.oy + w[1] * SE - w[2] * CE, w[1] * CE + w[2] * SE)

    def rot(self, n):
        return (n[0] * self.c - n[1] * self.s, n[0] * self.s + n[1] * self.c, n[2])

    # ----- 부품
    def face(self, pts, color, center, bias=0.0, rim=0.0):
        """3D 다각형 면. center = 이 면이 속한 입체의 중심(바깥 방향 판정용)"""
        p3 = [self.world(p) for p in pts]
        a, b, c = p3[0], p3[1], p3[2]
        u, v = (b[0] - a[0], b[1] - a[1], b[2] - a[2]), (c[0] - a[0], c[1] - a[1], c[2] - a[2])
        n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
        ln = math.sqrt(n[0] ** 2 + n[1] ** 2 + n[2] ** 2) or 1.0
        n = (n[0] / ln, n[1] / ln, n[2] / ln)
        cw = self.world(center)
        fc = (sum(p[0] for p in p3) / len(p3), sum(p[1] for p in p3) / len(p3), sum(p[2] for p in p3) / len(p3))
        if n[0] * (fc[0] - cw[0]) + n[1] * (fc[1] - cw[1]) + n[2] * (fc[2] - cw[2]) < 0:
            n = (-n[0], -n[1], -n[2])
        if n[0] * VIEW[0] + n[1] * VIEW[1] + n[2] * VIEW[2] <= -0.02:
            return                                                    # 뒷면은 그리지 않는다
        k = n[0] * LIGHT[0] + n[1] * LIGHT[1] + n[2] * LIGHT[2]
        col = mix(drk(color, 0.5), lit(color, 0.32), (k + 0.35) / 1.35)
        s2 = [self.pj(p) for p in pts]
        dep = sum(p[2] for p in s2) / len(s2) + bias
        self.q.append((dep, 0, ([(p[0], p[1]) for p in s2], col, rim)))

    def box(self, x0, x1, y0, y1, z0, z1, color, bias=0.0):
        cx, cy, cz = (x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2
        ctr = (cx, cy, cz)
        for pts in (((x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)),          # 윗면
                    ((x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)),          # 앞
                    ((x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1)),          # 뒤
                    ((x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)),          # 오른쪽
                    ((x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1))):         # 왼쪽
            self.face(pts, color, ctr, bias)

    def frustum(self, bx, by, tx, ty, z0, z1, color, bias=0.0):
        """아래 (±bx, ±by) -> 위 (±tx, ±ty) 로 좁아지는 입체 (앞뒤·좌우 대칭)"""
        ctr = (0, 0, (z0 + z1) / 2)
        B = ((bx, -by, z0), (bx, by, z0), (-bx, by, z0), (-bx, -by, z0))
        T = ((tx, -ty, z1), (tx, ty, z1), (-tx, ty, z1), (-tx, -ty, z1))
        self.face(T, color, ctr, bias)
        for i in range(4):
            j = (i + 1) % 4
            self.face((B[i], B[j], T[j], T[i]), color, ctr, bias)

    def ball(self, p, r, color, bias=0.0):
        c = self.pj(p)
        self.q.append((c[2] + bias, 1, (c[0], c[1], r * self.k, color)))

    def caps(self, a, b, w1, w2, color, bias=0.0):
        pa, pb = self.pj(a), self.pj(b)
        self.q.append(((pa[2] + pb[2]) / 2 + bias, 2, (pa[:2], pb[:2], w1 * self.k, w2 * self.k, color)))

    def poly(self, pts, color, bias=0.0, ol=True):
        s2 = [self.pj(p) for p in pts]
        self.q.append((sum(p[2] for p in s2) / len(s2) + bias, 3, ([(p[0], p[1]) for p in s2], color, ol)))

    def line(self, a, b, color, w=1, bias=0.0):
        pa, pb = self.pj(a), self.pj(b)
        self.q.append(((pa[2] + pb[2]) / 2 + bias, 4, (pa[:2], pb[:2], color, w)))

    def fn(self, p, f, bias=0.0):
        """임의 그리기 함수 f(cv, sx, sy). 깊이는 p 기준"""
        c = self.pj(p)
        self.q.append((c[2] + bias, 5, (c[0], c[1], f)))

    # ----- 그리기
    def flush(self):
        cv = self.cv
        for dep, kind, d in sorted(self.q, key=lambda q: q[0]):
            if kind == 0:
                pts, col, rim = d
                ip = [(int(x), int(y)) for x, y in pts]
                D.polygon(cv, col, ip)
                D.polygon(cv, OUT, ip, 1)
            elif kind == 1:
                x, y, r, col = d
                K.ball(cv, x, y, r, col)
            elif kind == 2:
                a, b, w1, w2, col = d
                K.rod(cv, a, b, w1, col, w2)
            elif kind == 3:
                pts, col, ol = d
                ip = [(int(x), int(y)) for x, y in pts]
                D.polygon(cv, col, ip)
                if ol:
                    D.polygon(cv, OUT, ip, 1)
            elif kind == 4:
                a, b, col, w = d
                D.line(cv, col, a, b, w)
            else:
                x, y, f = d
                f(cv, x, y)
        self.q = []


def leg_ik(hip, foot, l1, l2, bend):
    """2본 IK: hip, foot (월드와 무관한 모델 좌표) -> 무릎 좌표. bend = 무릎이 꺾이는 방향(단위벡터에 가까운 값)"""
    dx, dy, dz = foot[0] - hip[0], foot[1] - hip[1], foot[2] - hip[2]
    L = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
    if L > l1 + l2 - 0.5:
        k = (l1 + l2 - 0.5) / L
        dx, dy, dz, L = dx * k, dy * k, dz * k, L * k
        foot = (hip[0] + dx, hip[1] + dy, hip[2] + dz)
    a = (l1 * l1 - l2 * l2 + L * L) / (2 * L)
    h = math.sqrt(max(0.0, l1 * l1 - a * a))
    dd = (dx * bend[0] + dy * bend[1] + dz * bend[2]) / (L * L)
    b = (bend[0] - dx * dd, bend[1] - dy * dd, bend[2] - dz * dd)
    bl = math.sqrt(b[0] ** 2 + b[1] ** 2 + b[2] ** 2) or 1.0
    b = (b[0] / bl, b[1] / bl, b[2] / bl)
    knee = (hip[0] + dx * a / L + b[0] * h, hip[1] + dy * a / L + b[1] * h, hip[2] + dz * a / L + b[2] * h)
    return knee, foot


def anim(e, key, tmax=0.1):
    """보스가 들고 있는 리그 상태(이동 속도·진행 방향 각도·걸음 위상)를 갱신해 돌려준다"""
    st = e.get(key)
    if st is None:
        st = e[key] = dict(an=e["an"], x=e["x"], y=e["y"], hd=e.get("fa", 0.0), g=0.0, sp=0.0, vf=0.0, turn=0.0, vx=0.0, vy=0.0)
    dt = e["an"] - st["an"]
    if dt < 0 or dt > 0.5:
        st.update(an=e["an"], x=e["x"], y=e["y"])
        return st, 0.0
    if dt > 1e-4:
        dt = min(dt, tmax)
        dx, dy = e["x"] - st["x"], e["y"] - st["y"]
        sp = math.hypot(dx, dy) / dt
        st["sp"] += (sp - st["sp"]) * min(1.0, dt * 12)
        st["vx"] += (dx / dt - st["vx"]) * min(1.0, dt * 12)
        st["vy"] += (dy / dt - st["vy"]) * min(1.0, dt * 12)
        st["an"], st["x"], st["y"] = e["an"], e["x"], e["y"]
        return st, dt
    return st, 0.0


def turn_toward(st, target, dt, rate=7.0):
    d = (target - st["hd"] + math.pi) % (2 * math.pi) - math.pi
    step = d * (1 - math.exp(-rate * dt))
    st["hd"] += step
    st["turn"] += ((step / dt if dt > 0 else 0.0) - st["turn"]) * min(1.0, dt * 6)


def screen_dir(sc, p, d):
    """모델 좌표 p 에서 방향 d 가 화면에서 향하는 단위벡터 (분사·불꽃 방향 계산용)"""
    a, b = sc.pj(p), sc.pj((p[0] + d[0], p[1] + d[1], p[2] + d[2]))
    dx, dy = b[0] - a[0], b[1] - a[1]
    l = math.hypot(dx, dy) or 1.0
    return dx / l, dy / l, l


def visible(sc, n):
    """모델 기준 법선 n 이 보는 쪽을 향하는가"""
    w = sc.rot(n)
    return w[0] * VIEW[0] + w[1] * VIEW[1] + w[2] * VIEW[2] > 0.0
