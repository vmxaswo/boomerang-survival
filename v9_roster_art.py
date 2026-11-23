"""v9_roster_art.py - 보스 비주얼 업그레이드 패치
v9_roster.py 는 한 줄도 고치지 않고, 그리기 함수만 갈아 끼운다.

사용법 (v9_roster.install(...) 을 부르기 "전"에 한 번):
    import v9_roster, v9_roster_art
    v9_roster_art.apply(v9_roster)
    v9_roster.install(G, C, B)

바뀌는 것
 - 수문장(네 발 이동식 성문 요새) / 공장장 / 정비관(불꽃+냉동 6족 보일러 거미) : 비인간형 디자인, 외곽선 + 셰이딩, 상태·페이즈 별 변화
 - 소환체 : 톱니바퀴(회전 톱니), 균열 구체(궤도 링), 골렘(균열 발광), 환영(글리치 + 잔상)
 - 위험 구역(원형/띠/레이저/중력장/충격파) : 경고 연출 + 폭발·플라즈마·불똥 이펙트
 - 빅 브라더 : 해부학적 기계 심장 + 감시의 눈 (심방/심실/대동맥/폐동맥/정맥, 박동, 눈꺼풀, 서브 코어 케이블)
모든 애니메이션은 e["an"] (또는 g/t 시간) 하나로 구동되므로 다른 코드는 건드릴 필요가 없다."""
import math

import pygame

D = pygame.draw
SC = pygame.SRCALPHA
TAU = math.pi * 2
OUT = (18, 14, 28)
WHITE = (255, 255, 255)
_R = None


# ---------------------------------------------------------------- 색 / 도형 도구
def mix(a, b, k):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


def lit(c, k=0.3):
    return mix(c, WHITE, k)


def drk(c, k=0.4):
    return mix(c, (10, 8, 20), k)


def block(s, x, y, w, h, c, fl=False):
    """외곽선 + 밝은 윗/왼쪽 + 어두운 아래/오른쪽이 있는 픽셀 블록"""
    x, y, w, h = int(x), int(y), int(w), int(h)
    if w <= 0 or h <= 0:
        return
    s.fill(OUT, (x - 1, y - 1, w + 2, h + 2))
    if fl:
        s.fill(WHITE, (x, y, w, h))
        return
    s.fill(c, (x, y, w, h))
    s.fill(lit(c, 0.38), (x, y, w, 1))
    s.fill(lit(c, 0.2), (x, y, 1, h))
    s.fill(drk(c, 0.35), (x, y + h - 1, w, 1))
    s.fill(drk(c, 0.25), (x + w - 1, y, 1, h))


def disc(s, x, y, r, c, fl=False):
    x, y = int(x), int(y)
    D.circle(s, OUT, (x, y), r + 1)
    D.circle(s, WHITE if fl else c, (x, y), r)
    if not fl and r >= 3:
        D.circle(s, lit(c, 0.45), (x - r // 3, y - r // 3), max(1, r // 3))


def limb(s, a, b, w, c, fl=False):
    D.line(s, OUT, a, b, w + 2)
    D.line(s, WHITE if fl else c, a, b, w)
    if not fl and w >= 3:
        D.line(s, lit(c, 0.3), (a[0], a[1] - 1), (b[0], b[1] - 1), 1)


def puff(s, x, y, t, col, n=3, rise=14, spd=1.0, seed=0, sz=2):
    """위로 올라가며 작아지고 어두워지는 연기/증기"""
    for i in range(n):
        f = (t * spd + i / n + seed * 0.37) % 1.0
        r = max(1, int(sz * (1.15 - f * 0.7)))
        D.circle(s, mix(col, (40, 36, 60), f * 0.7),
                 (int(x + math.sin((f + i) * 5 + seed) * 3), int(y - f * rise)), r)


def flame(s, x, y, t, h=10, w=6, seed=0, hot=(255, 120, 50)):
    """일렁이는 3겹 불꽃 (위쪽으로 솟는다)"""
    x, y = int(x), int(y)
    for k, (sc, col) in enumerate(((1.0, hot), (0.68, mix(hot, (255, 225, 110), 0.65)), (0.38, (255, 252, 225)))):
        fh = max(2, int(h * sc * (0.8 + 0.2 * math.sin(t * 17 + seed * 1.3 + k))))
        fw = max(1, int(w * sc / 2))
        sway = int(math.sin(t * 11 + seed) * 1.6)
        D.polygon(s, col, [(x - fw, y), (x - fw // 2 + sway, y - fh // 2), (x + sway * 2, y - fh),
                           (x + fw // 2 + sway, y - fh // 2), (x + fw, y)])


def jet(s, x, y, dx, dy, t, L=10, w=4, seed=0, hot=(255, 140, 50)):
    """(dx, dy) 방향으로 뿜는 분사 불꽃"""
    for k, (sc, col) in enumerate(((1.0, hot), (0.65, mix(hot, (255, 225, 110), 0.65)), (0.35, (255, 252, 225)))):
        ln = L * sc * (0.8 + 0.2 * math.sin(t * 20 + seed + k))
        px, py = -dy, dx
        ww = max(1.0, w * sc / 2)
        D.polygon(s, col, [(x + px * ww, y + py * ww), (x + dx * ln * 0.5 + px * ww * 0.6, y + dy * ln * 0.5 + py * ww * 0.6),
                           (x + dx * ln, y + dy * ln), (x + dx * ln * 0.5 - px * ww * 0.6, y + dy * ln * 0.5 - py * ww * 0.6),
                           (x - px * ww, y - py * ww)])


def poly(s, pts, c, fl=False):
    D.polygon(s, WHITE if fl else c, pts)
    D.polygon(s, OUT, pts, 1)


def gear_poly(x, y, r, a0, teeth=8):
    pts, st = [], TAU / teeth
    for i in range(teeth):
        a = a0 + i * st
        for off, rr in ((-0.5, r - 3), (-0.27, r), (0.27, r), (0.5, r - 3)):
            pts.append((x + math.cos(a + off * st) * rr, y + math.sin(a + off * st) * rr))
    return pts


def spark_ring(s, x, y, t, col, n=4, r=10, spd=3.0, seed=0):
    for i in range(n):
        a = t * spd + i * TAU / n + seed
        s.fill(col, (int(x + math.cos(a) * r), int(y + math.sin(a) * r * 0.45), 2, 2))


def shadow(s, w=28):
    try:
        sh = _R.G.SHADOW
        return sh
    except Exception:
        return None


# ================================================================= 1. 수문장 벌크스틸 (네 발 이동식 성문 요새)
def draw_bulk(s, e, x, y, g):
    ph, fl, a, t = e["phase"], e["fl"] > 0, e["fa"], e["an"]
    ca, sa = math.cos(a), math.sin(a)
    fx = 1 if ca >= 0 else -1
    st = e["st"]
    moving = e["mv"] or st == "dash"
    stun = st == "stun"
    base = (150, 102, 74) if ph == 1 else (108, 116, 146) if ph == 2 else (186, 192, 210)
    trim = (88, 68, 60) if ph == 1 else (68, 74, 100) if ph == 2 else (56, 60, 84)
    glowc = (255, 80, 56) if ph < 3 else (255, 160, 60)
    pulse = 0.5 + 0.5 * math.sin(t * 7)
    sag = 3 if (stun or ph == 2) else 0
    yb, yt = y - 14 + sag, y - 30 + sag
    if not moving and not stun:
        yb += int(math.sin(t * 2.5) * 1)
        yt += int(math.sin(t * 2.5) * 1)
    spread = 1.22 if ph == 2 else 1.0

    # --- 3페이즈: 후방 분사
    if ph == 3:
        for k, yy in enumerate((yb - 4, yb - 12)):
            jet(s, x - fx * 22, yy, -fx, 0, t, 14 if moving else 8, 5, k, (255, 150, 60))
    # --- 네 다리
    for k, off in enumerate((-18, -9, 9, 18)):
        osg = 1 if off > 0 else -1
        hx = x + off * spread * 0.85
        lift = max(0.0, math.sin(t * 9 + (k % 2) * math.pi)) * 3 if moving else 0.0
        hip = (hx, yb - 2)
        knee = (hx + osg * 5, y - 8 - lift * 0.5)
        foot = (hx + osg * 4, y - 2 - lift)
        c = drk(base, 0.3 + 0.12 * (k % 2))
        limb(s, hip, knee, 5, c, fl)
        limb(s, knee, foot, 4, drk(base, 0.45), fl)
        disc(s, knee[0], knee[1], 2, (255, 160, 60) if ph == 3 else trim, fl)
        block(s, foot[0] - 4, foot[1] - 1, 8, 3, trim, fl)
        if ph == 2:
            D.polygon(s, OUT, [(foot[0] - 2, foot[1] + 2), (foot[0], foot[1] + 5), (foot[0] + 2, foot[1] + 2)])
    # --- 선체
    hull = [(x - 22, yb), (x + 22, yb), (x + 17, yt), (x - 17, yt)]
    if ph == 3:                                                 # 장갑이 날아가 골조가 드러난다
        frame = drk(base, 0.55)
        poly(s, hull, frame, fl)
        if not fl:
            cyc = (yt + yb) // 2
            D.line(s, lit(frame, 0.3), (x - 20, yb - 1), (x + 16, yt + 1), 1)
            D.line(s, lit(frame, 0.3), (x + 20, yb - 1), (x - 16, yt + 1), 1)
            D.circle(s, drk(glowc, 0.5), (x, cyc), 7)
            D.circle(s, mix(glowc, WHITE, pulse * 0.5), (x, cyc), 4 + int(pulse * 1.5))
            D.circle(s, WHITE, (x, cyc), 2)
        for k in range(4):                                      # 떨어져 나온 장갑판이 주위를 돈다
            ang = t * 1.6 + k * TAU / 4
            px, py = x + math.cos(ang) * 27, yt + 8 + math.sin(ang) * 7
            block(s, px - 3, py - 2, 7, 4, base, fl)
    else:
        poly(s, hull, base, fl)
        if not fl:
            D.line(s, lit(base, 0.45), hull[3], hull[2], 1)
            D.line(s, lit(base, 0.25), hull[0], hull[3], 1)
            s.fill(trim, (x - 21, yb - 4, 42, 3))
            for sx_ in (-8, 8):
                D.line(s, drk(base, 0.4), (x + sx_, yt + 1), (x + sx_ * 1.15, yb - 5), 1)
            for rx in (-19, -13, -3, 4, 13, 18):
                s.fill(lit(base, 0.6), (x + rx, yb - 3, 1, 1))
            if ph == 1:                                         # 녹 자국
                for rx, ry, rw, rh in ((-12, 3, 5, 2), (5, 7, 4, 3), (-3, 10, 4, 1), (11, 2, 3, 2)):
                    s.fill((112, 64, 44), (x + rx, yt + ry, rw, rh))
        for i in range(5):                                      # 성벽 총안
            if ph == 1 and i == 3:
                continue
            block(s, x - 16 + i * 7, yt - 4, 4, 4, base, fl)
    # --- 앞쪽 성문 방패 (정면 장갑)
    if ph == 1:
        up = stun or e["exp"] > 0
        gx = x + fx * 22 - (3 if fx > 0 else 4)
        gy = yt - 2 - (11 if up else 0)
        if up and not fl:
            s.fill(mix(glowc, (30, 20, 30), 0.3), (gx, yt, 7, yb - yt))
        block(s, gx, gy, 7, yb - yt + 6, trim, fl)
        if not fl:
            for yy in range(gy + 2, gy + yb - yt + 5, 4):
                s.fill(lit(trim, 0.3), (gx, yy, 7, 1))
            for xx in (gx + 2, gx + 4):
                s.fill(drk(trim, 0.4), (xx, gy, 1, yb - yt + 6))
            for xx in (gx + 1, gx + 3, gx + 5):
                D.polygon(s, OUT, [(xx - 1, gy + yb - yt + 6), (xx, gy + yb - yt + 9), (xx + 1, gy + yb - yt + 6)])
    # --- 외눈 렌즈
    ex_, ey_ = x + fx * 8, yt + 8
    D.circle(s, OUT, (ex_, ey_), 5)
    D.circle(s, (30, 24, 40), (ex_, ey_), 4)
    ic = WHITE if (st == "wind" and int(t * 16) % 2) else mix(glowc, (255, 245, 210), pulse * 0.5)
    D.circle(s, ic, (ex_ + int(ca * 2), ey_ + int(sa * 1.5)), 2)
    s.fill(WHITE, (ex_ - 2 + fx, ey_ - 2, 1, 1))
    # --- 1페이즈: 낡은 깃발
    if ph == 1:
        bx, by = x - fx * 11, yt - 4
        D.line(s, OUT, (bx, by), (bx, by - 14), 3)
        D.line(s, (150, 150, 168), (bx, by), (bx, by - 14), 1)
        w1, w2 = math.sin(t * 5) * 2, math.sin(t * 5 + 1) * 2
        D.polygon(s, (150, 40, 44), [(bx, by - 14), (bx - fx * (8 + w1), by - 12 + w2), (bx - fx * (6 + w2), by - 9), (bx - fx * (9 + w1), by - 7 + w1), (bx, by - 7)])
    # --- 2페이즈: 요새 포탑 + 배기 증기
    if ph == 2:
        tx, ty = x - fx * 3, yt - 3
        rc = int(math.sin(t * 40) * 1.5) if st == "turret" else 0
        tip = (tx + ca * (14 + rc), ty - 3 + sa * 8)
        limb(s, (tx, ty - 2), tip, 5, trim, fl)
        disc(s, tx, ty - 1, 5, base, fl)
        D.circle(s, (255, 170, 80), (int(tip[0]), int(tip[1])), 2)
        if st == "turret" and int(t * 30) % 2:
            D.circle(s, (255, 240, 170), (int(tip[0] + ca * 3), int(tip[1] + sa * 2)), 3)
        puff(s, x - 14, yt - 6, t, (200, 206, 224), 3, 12, 0.9, 1)
        puff(s, x + 14, yt - 6, t, (200, 206, 224), 3, 12, 0.9, 2)
    # --- 드릴 파일벙커
    rx_, ry_ = x + fx * 21, yb - 6
    L = 8
    if st == "wind":
        L = 15 + int(math.sin(t * 22) * 2)
    tip = (rx_ + ca * L, ry_ + sa * L * 0.6)
    limb(s, (rx_, ry_), tip, 6, (150, 158, 182), fl)
    if not fl:
        for i in range(4):
            f = ((i + t * 6) % 4) / 4
            px, py = rx_ + (tip[0] - rx_) * f, ry_ + (tip[1] - ry_) * f
            D.line(s, drk((150, 158, 182), 0.5), (px - sa * 3, py + ca * 2), (px + sa * 3, py - ca * 2), 1)
    qx, qy = -sa * 3.5, ca * 2.2
    D.polygon(s, OUT, [(tip[0] + qx - ca, tip[1] + qy - sa), (tip[0] - qx - ca, tip[1] - qy - sa), (tip[0] + ca * 11, tip[1] + sa * 7)])
    D.polygon(s, WHITE if fl else (230, 236, 250), [(tip[0] + qx, tip[1] + qy), (tip[0] - qx, tip[1] - qy), (tip[0] + ca * 9, tip[1] + sa * 6)])
    if st == "wind":
        D.circle(s, (255, 90, 70), (int(tip[0]), int(tip[1])), 2 + int(t * 20) % 2)
    # --- 상태 연출
    if stun:
        for k in range(3):
            ang = t * 4 + k * 2.09
            s.fill((255, 235, 110), (int(x + math.cos(ang) * 12), int(yt - 12 + math.sin(ang) * 3), 3, 3))
        puff(s, x - 10, yt - 2, t, (210, 215, 230), 3, 12, 1.2, 3)
        puff(s, x + 10, yt - 2, t, (210, 215, 230), 3, 12, 1.2, 4)
    if st == "dash":
        puff(s, x - fx * 18, y - 2, t, (190, 170, 150), 4, 8, 2.5, 5, 3)
    if st == "wind" and int(t * 14) % 2:
        D.rect(s, (255, 90, 80), (x - 26, yt - 8, 52, yb - yt + 22), 1)


# ================================================================= 2. 공장장 알케미스트
def _tool(s, k, ex, ey, sg, t, liq, ph):
    ex, ey = int(ex), int(ey)
    if k == 0:                                                  # 플라스크
        block(s, ex - 3, ey - 2, 6, 6, (210, 230, 240))
        s.fill(liq, (ex - 2, ey + 1, 4, 2))
        s.fill(OUT, (ex - 1, ey - 4, 2, 2))
        if int(t * 5) % 2:
            s.fill(lit(liq, 0.5), (ex, ey - 6 - int(t * 6) % 3, 1, 1))
    elif k == 1:                                                # 집게
        op = 2 + int(math.sin(t * 6) * 1.5)
        D.line(s, OUT, (ex, ey), (ex + sg * 5, ey - op - 1), 3)
        D.line(s, OUT, (ex, ey), (ex + sg * 5, ey + op + 1), 3)
        D.line(s, (210, 214, 232), (ex, ey), (ex + sg * 5, ey - op), 1)
        D.line(s, (210, 214, 232), (ex, ey), (ex + sg * 5, ey + op), 1)
    elif k == 2:                                                # 용접기
        disc(s, ex, ey, 3, (255, 170, 70) if ph >= 3 else (170, 176, 196))
        if int(t * 18) % 3:
            s.fill((255, 255, 210), (ex + sg * 4 + int(math.sin(t * 40) * 2), ey + int(math.cos(t * 33) * 2), 2, 2))
    else:                                                       # 렌치
        D.line(s, OUT, (ex, ey), (ex + sg * 6, ey - 4), 4)
        D.line(s, (214, 170, 90), (ex, ey), (ex + sg * 6, ey - 4), 2)
        D.circle(s, (214, 170, 90), (ex + sg * 6, ey - 4), 3, 1)


def draw_alch(s, e, x, y, g):
    ph, fl, t = e["phase"], e["fl"] > 0, e["an"]
    cast = e["st"] == "cast"
    y = int(y + math.sin(t * 2) * 2)
    liq = (120, 255, 140) if ph < 3 else (255, 176, 80) if ph == 3 else (255, 92, 64)
    metal, brass = (104, 114, 142), (210, 166, 84)
    # --- 하부 분사
    for k, c in enumerate(((50, 190, 160) if ph < 4 else (255, 110, 60), (130, 250, 210) if ph < 4 else (255, 190, 100), WHITE)):
        w = 8 - k * 2
        h = max(2, int((9 - k * 2) * (0.8 + 0.2 * math.sin(t * 20 + k))))
        D.ellipse(s, c, (x - w, y - 3, w * 2, h))
    # --- 받침
    block(s, x - 16, y - 8, 32, 6, metal, fl)
    s.fill(brass, (x - 16, y - 6, 32, 1))
    for rx in (-13, -5, 3, 11):
        s.fill(lit(metal, 0.5), (x + rx, y - 5, 2, 2))
    # --- 배관 + 증기
    for sg in (-1, 1):
        D.line(s, OUT, (x + sg * 17, y - 10), (x + sg * 17, y - 40), 5)
        D.line(s, drk(metal, 0.1), (x + sg * 17, y - 10), (x + sg * 17, y - 40), 3)
        puff(s, x + sg * 17, y - 42, t, (214, 222, 232), 2, 9, 1.0, sg, 1)
    # --- 유리 탱크
    D.ellipse(s, OUT, (x - 19, y - 40, 38, 36))
    D.ellipse(s, (36, 54, 66), (x - 18, y - 39, 36, 34))
    lvl = y - 25 + int(math.sin(t * 4) * 1)
    old = s.get_clip()
    s.set_clip(old.clip(pygame.Rect(x - 19, lvl, 38, 40)))
    D.ellipse(s, drk(liq, 0.4), (x - 18, y - 39, 36, 34))
    D.ellipse(s, mix(liq, (20, 40, 30), 0.25), (x - 16, y - 37, 30, 30))
    s.set_clip(old)
    s.fill(lit(liq, 0.55), (x - 11, lvl, 22, 1))
    for i in range(6):                                          # 기포
        f = (t * 0.8 + i * 0.19) % 1.0
        by = int(y - 8 - f * 22)
        if by > lvl:
            D.circle(s, lit(liq, 0.65), (int(x - 11 + i * 4.4 + math.sin(f * 9 + i) * 2), by), 1 + (i % 2))
    D.line(s, (214, 238, 248), (x - 14, y - 32), (x - 14, y - 20), 1)
    s.fill((214, 238, 248), (x - 13, y - 35, 2, 1))
    if fl:
        D.ellipse(s, WHITE, (x - 18, y - 39, 36, 34))
    if ph == 4:                                                 # 금 간 유리 + 과열
        for ax_, ay_, bx_, by_ in ((6, -36, 2, -26), (2, -26, 8, -18), (-8, -34, -4, -24)):
            D.line(s, (255, 230, 170), (x + ax_, y + ay_), (x + bx_, y + by_), 1)
        for i in range(3):
            s.fill((255, 220, 120), (int(x - 10 + (t * 40 + i * 9) % 20), int(y - 30 + math.sin(t * 30 + i) * 8), 1, 1))
    # --- 뚜껑 / 머리
    block(s, x - 13, y - 44, 26, 5, metal, fl)
    s.fill(brass, (x - 13, y - 42, 26, 1))
    block(s, x - 6, y - 54, 12, 10, metal, fl)
    ec = (255, 90, 60) if not cast else (255, 255, 200)
    s.fill(drk(metal, 0.7), (x - 5, y - 50, 10, 3))
    s.fill(ec, (x - 4 + int(math.sin(t * 2) * 1.5), y - 49, 3, 2))
    s.fill(ec, (x + 1 + int(math.sin(t * 2) * 1.5), y - 49, 3, 2))
    D.line(s, OUT, (x, y - 54), (x + 3, y - 62), 3)
    D.line(s, (180, 186, 206), (x, y - 54), (x + 3, y - 62), 1)
    D.circle(s, (255, 90, 60) if int(t * 3) % 2 else (120, 40, 40), (x + 3, y - 63), 2)
    # --- 톱니 후광
    for k in range(6):
        ang = t * (1.5 if ph < 4 else 3.2) + k * TAU / 6
        gx, gy = x + int(math.cos(ang) * 15), y - 50 + int(math.sin(ang) * 5)
        D.polygon(s, OUT, gear_poly(gx, gy, 5, ang * 2, 5))
        D.polygon(s, (196, 202, 220), gear_poly(gx, gy, 4, ang * 2, 5))
        s.fill(OUT, (gx - 1, gy - 1, 2, 2))
    # --- 팔
    n = 2 if ph < 2 else 4
    for k in range(n):
        sg = -1 if k % 2 == 0 else 1
        row = k // 2
        sx, sy = x + sg * 19, y - 28 + row * 10
        sw = math.sin(t * 3 + k * 1.7)
        if cast:
            ex_, ey_ = x + sg * (23 + 5 * row), sy - 17 - sw * 2
        else:
            ex_, ey_ = x + sg * (28 + sw * 3), sy + 7 + row * 3 + sw * 3
        mx_, my_ = (sx + ex_) / 2 + sg * 3, (sy + ey_) / 2 - 5
        limb(s, (sx, sy), (mx_, my_), 3, (150, 158, 180), fl)
        limb(s, (mx_, my_), (ex_, ey_), 3, (150, 158, 180), fl)
        disc(s, mx_, my_, 2, brass)
        disc(s, sx, sy, 3, metal)
        _tool(s, k, ex_, ey_, sg, t, liq, ph)
    if cast:
        spark_ring(s, x, y - 50, t, (255, 255, 200), 5, 18, 5)


# ================================================================= 3. 수석 정비관 오버히트 (불꽃 + 냉동 6족 보일러 거미)
def _arm(s, sx, sy, fx, ext, sway, t, kind, inten, hotc, body, fl, torch, seed):
    ex_ = (sx + fx * (7 + ext * 0.35), sy + 5 + sway)
    tp = (sx + fx * (13 + ext), sy + (3 if kind == "fire" else -3) + sway * 0.6)
    metal = drk(body, 0.2)
    limb(s, (sx, sy), ex_, 4, metal, fl)
    limb(s, ex_, tp, 3, lit(metal, 0.1), fl)
    D.line(s, lit(metal, 0.5), (sx, sy + 3), (ex_[0], ex_[1] + 2), 1)
    disc(s, ex_[0], ex_[1], 3, drk(body, 0.4), fl)
    cc = hotc if kind == "fire" else (140, 214, 255)
    block(s, tp[0] - 3 + (fx > 0) * 1, tp[1] - 3, 6, 6, drk(body, 0.45), fl)
    s.fill(cc if inten > 0.3 else drk(cc, 0.6), (int(tp[0] + fx * 2), int(tp[1] - 1), 2, 2))
    nx, ny = tp[0] + fx * 4, tp[1]
    if inten < 0.3:                                             # 대기 중: 작은 점화 불꽃
        if kind == "fire":
            flame(s, nx, ny + 1, t, 4, 3, seed, hotc)
        return tp
    ln = (7 + 11 * inten) * (1.6 if torch else 1.0)
    if kind == "fire":
        jet(s, nx, ny, fx, 0, t, ln, 6 if torch else 5, seed, hotc)
        if int(t * 14 + seed) % 3 == 0:
            s.fill((255, 230, 140), (int(nx + fx * ln * (0.5 + 0.5 * math.sin(t * 9))), int(ny - 3), 2, 2))
    else:
        jet(s, nx, ny, fx, 0, t, ln * 0.9, 5, seed, (130, 206, 255))
        for i in range(4):                                      # 흩날리는 냉기 입자
            f = (t * 1.4 + i / 4 + seed * 0.2) % 1.0
            s.fill((226, 244, 255), (int(nx + fx * (3 + f * ln)), int(ny - 4 + math.sin(f * 6 + i) * 5), 2, 2))
    return tp


def draw_heat(s, e, x, y, g):
    ph, fl, t = e["phase"], e["fl"] > 0, e["an"]
    y -= int(e.get("lift", 0))
    stun = e["stun"] > 0
    torch = e["st"] == "torch"
    heat = min(1.0, e["heat"] / 100.0)
    look = e.get("lk", 0.0)
    fx = 1 if math.cos(look) >= 0 else -1
    moving = e["mv"] or e["st"] == "leap"
    if stun:
        fire_i, ice_i, hotc, body = 0.15, 0.6, (130, 190, 240), (86, 106, 148)
    elif ph == 1:
        fire_i, ice_i, hotc, body = 1.0, 0.2, (255, 120, 70), (112, 92, 100)
    elif ph == 2:
        fire_i, ice_i, hotc, body = 0.2, 1.0, (255, 150, 90), (92, 120, 154)
    elif ph == 3:
        fire_i, ice_i = 1.0, 0.8
        hotc, body = mix((255, 150, 70), (255, 50, 40), heat), mix((104, 86, 94), (178, 70, 62), heat)
    else:
        fire_i, ice_i, hotc, body = 1.0, 1.0, (255, 255, 235), (232, 230, 242)
    metal = (112, 118, 142)
    pulse = 0.5 + 0.5 * math.sin(t * 6)
    sag = 3 if stun else 0
    by = y - 21 + sag + (int(math.sin(t * 2.4) * 1) if not moving else -abs(int(math.sin(t * 8) * 2)))
    jx = int(math.sin(t * 55) * 1) if (ph == 3 and heat > 0.7 and not stun) else 0
    x += jx

    # --- 4페이즈 오라
    if ph == 4:
        for i in range(5):
            flame(s, x + (i - 2) * 8, by - 8 - abs(i - 2) * 2, t, 15 - abs(i - 2) * 2, 8, i, (255, 240, 200))
        for i in range(14):
            ang = t * 2.5 + i * TAU / 14
            s.fill(WHITE, (int(x + math.cos(ang) * 30), int(by + math.sin(ang) * 22), 2, 2))
    # --- 다리 여섯 개 (먼 쪽 -> 가까운 쪽)
    for idx, (far, off) in enumerate(((True, -10), (True, 2), (True, 14), (False, -14), (False, -2), (False, 10))):
        sgn = 1 if off > 0 else -1
        lf = max(0.0, math.sin(t * 8 + idx * 1.05)) * 3 if moving else 0.0
        dy = -3 if far else 0
        hip = (x + off, by + 7 + dy)
        knee = (hip[0] + sgn * 8, by + 5 + dy - lf * 0.4)
        foot = (hip[0] + sgn * 11, y - 1 + dy - lf)
        c = drk(body, 0.55 if far else 0.3)
        limb(s, hip, knee, 3, c, fl)
        limb(s, knee, foot, 3, drk(c, 0.15), fl)
        disc(s, knee[0], knee[1], 2, mix(hotc if idx % 2 else (130, 210, 255), c, 0.4), fl)
        s.fill(OUT, (int(foot[0]) - 2, int(foot[1]), 5, 2))
    # --- 먼 쪽 팔 (냉동 노즐)
    shx, shy = x + fx * 14, by - 8
    ext = 13 if torch else 6 + int(math.sin(t * 3) * 2)
    _arm(s, shx, shy, fx, ext, math.sin(t * 3 + 1) * 2, t, "ice", ice_i, hotc, body, fl, torch, 1)
    # --- 후면 방열 핀 + 배기
    spread = 10 if (stun or ph == 4 or heat > 0.85) else 7
    for i in range(4):
        fyy = by - 9 + i * 5
        fin = mix(metal, hotc, 0.15 + 0.35 * fire_i * (0.5 + 0.5 * math.sin(t * 5 + i)))
        block(s, x - fx * 20 - (spread if fx > 0 else 0) + (0 if fx > 0 else 0), fyy, spread, 3, fin, fl) if fx > 0 else block(s, x + 20, fyy, spread, 3, fin, fl)
    if ph >= 3 and not stun:
        for i, yy in enumerate((by - 3, by + 3)):
            jet(s, x - fx * (20 + spread), yy, -fx, 0, t, 10 + (6 if moving else 0), 5, i + 3, hotc)
    # --- 보일러 본체
    D.ellipse(s, OUT, (x - 21, by - 13, 42, 26))
    D.ellipse(s, WHITE if fl else body, (x - 20, by - 12, 40, 24))
    if not fl:
        D.ellipse(s, lit(body, 0.3), (x - 14, by - 11, 26, 5))
        D.arc(s, drk(body, 0.45), pygame.Rect(x - 20, by - 12, 40, 24), 3.6, 5.8, 2)
        for bx_ in (-9, 9):
            D.line(s, drk(body, 0.4), (x + bx_, by - 10), (x + bx_, by + 10), 2)
            for ry in (-8, -3, 2, 7):
                s.fill(lit(body, 0.6), (x + bx_ - 1, by + ry, 1, 1))
    # --- 점검창 (온도 표시)
    block(s, x - 6, by - 3, 12, 9, (24, 20, 40), fl)
    if not fl:
        lvl = int(7 * (heat if ph == 3 else 0.55 if ph != 2 else 0.35))
        liq = (140, 206, 255) if (ph == 2 or stun) else hotc
        s.fill(liq, (x - 5, by + 5 - lvl, 10, lvl))
        s.fill(lit(liq, 0.6), (x - 5, by + 5 - lvl, 10, 1))
        for i in range(2):
            f = (t * 1.2 + i * 0.5) % 1.0
            s.fill(WHITE, (int(x - 3 + i * 5), int(by + 5 - f * lvl), 1, 1))
    # --- 굴뚝 + 압력계
    block(s, x - fx * 7 - 3, by - 24, 6, 11, metal, fl)
    s.fill(drk(metal, 0.5), (x - fx * 7 - 3, by - 25, 6, 2))
    smoke = (220, 236, 250) if (stun or ph == 2) else (96, 90, 108)
    puff(s, x - fx * 7, by - 26, t, smoke, 3, 14, 1.0, 3, 2)
    gx, gy = x + fx * 6, by - 13
    disc(s, gx, gy, 5, (228, 230, 238), fl)
    if not fl:
        D.arc(s, (230, 60, 50), pygame.Rect(gx - 4, gy - 4, 8, 8), 0.4, 1.4, 2)
        ang = -2.4 + (heat * 2.4 if ph == 3 else 0.9 + 0.2 * math.sin(t * 3))
        D.line(s, (30, 24, 40), (gx, gy), (gx + math.cos(ang) * 4, gy + math.sin(ang) * 4), 1)
    if ph == 2:                                                 # 등에 돋은 얼음 결정
        for sx_, h_ in ((-12, 9), (-4, 12), (6, 8)):
            D.polygon(s, OUT, [(x + sx_ - 3, by - 10), (x + sx_, by - 10 - h_), (x + sx_ + 3, by - 10)])
            D.polygon(s, (200, 238, 255), [(x + sx_ - 2, by - 10), (x + sx_, by - 8 - h_), (x + sx_ + 2, by - 10)])
    if ph == 3 and not fl and heat > 0.4:                       # 과열 균열 + 연기
        for i in range(1 + int(heat * 3)):
            D.line(s, hotc, (x - 14 + i * 9, by - 9), (x - 11 + i * 9, by + 5), 1)
        if heat > 0.6 and not stun:
            puff(s, x + 4, by - 14, t, (232, 120, 90), 2, 10, 1.6, 1)
    # --- 머리 센서 (플레이어를 본다)
    hx_, hy_ = x + fx * 20, by - 5
    disc(s, hx_, hy_, 6, metal, fl)
    D.circle(s, (20, 16, 32), (hx_ + fx, hy_), 3)
    ic = mix(hotc, (130, 210, 255), 0.5) if ph == 3 else (hotc if ph != 2 else (130, 210, 255))
    D.circle(s, mix(ic, WHITE, 0.4 * pulse), (hx_ + fx + int(math.sin(look) * 1), hy_ + int(math.sin(look) * 1.5)), 2)
    # --- 가까운 쪽 팔 (화염 토치)
    nsx, nsy = x + fx * 15, by + 2
    _arm(s, nsx, nsy, fx, ext + 1, math.sin(t * 3) * 2, t, "fire", fire_i, hotc, body, fl, torch, 2)
    if stun:                                                    # 정지: 전체 배기
        for sx_ in (-14, 4):
            puff(s, x + sx_, by - 10, t, (214, 230, 246), 3, 18, 1.4, sx_, 3)
        for k in range(3):
            ang = t * 3 + k * 2.09
            s.fill((220, 236, 250), (int(x + math.cos(ang) * 10), int(by - 32 + math.sin(ang) * 3), 3, 3))


# ================================================================= 소환체
def _gear(s, e, x, y, fl):
    t = e["an"]
    D.polygon(s, OUT, gear_poly(x, y, 14, t * 3, 8))
    D.polygon(s, WHITE if fl else (150, 158, 184), gear_poly(x, y, 12, t * 3, 8))
    D.circle(s, (92, 98, 128), (x, y), 8)
    D.circle(s, WHITE if fl else (178, 186, 210), (x, y), 7)
    for k in range(3):
        a = t * 3 + k * TAU / 3
        D.line(s, (90, 96, 124), (x, y), (x + math.cos(a) * 6, y + math.sin(a) * 6), 2)
    D.circle(s, OUT, (x, y), 3)
    D.circle(s, (255, 170, 70) if int(t * 6) % 2 else (255, 120, 50), (x, y), 2)
    s.fill(WHITE, (x - 6, y - 7, 2, 1))
    for k in range(2):                                          # 튕길 때 튀는 불똥
        s.fill((255, 220, 130), (int(x + math.cos(t * 9 + k * 3) * 13), int(y + math.sin(t * 9 + k * 3) * 13), 1, 1))


def _orb(s, e, x, y, fl):
    t = e["an"]
    r = 5 + int(math.sin(t * 8))
    D.circle(s, (60, 30, 110), (x, y), r + 4, 1)
    D.circle(s, (90, 50, 160), (x, y), r + 2)
    D.circle(s, WHITE if fl else (200, 160, 255), (x, y), r)
    D.circle(s, (240, 225, 255), (x - 1, y - 1), max(1, r // 2))
    s.fill(WHITE, (x - 2, y - 2, 2, 2))
    for k in range(3):
        a = t * 5 + k * TAU / 3
        s.fill((230, 200, 255), (int(x + math.cos(a) * (r + 5)), int(y + math.sin(a) * (r + 5) * 0.6), 2, 2))


def _golem(s, e, x, y, fl):
    t = e["an"]
    wind = e["st"] == "wind"
    flick = wind and int(t * 14) % 2
    bob = int(abs(math.sin(t * 6)) * -2) if e["st"] == "idle" else 0
    y += bob
    rock = (255, 255, 255) if fl else (220, 112, 82) if flick else (146, 120, 102)
    for sg in (-1, 1):
        block(s, x + sg * 5 - 3, y - 7, 6, 8, (84, 72, 72), fl)
    block(s, x - 10, y - 24, 20, 18, rock, fl)
    block(s, x - 7, y - 30, 14, 8, mix(rock, (80, 70, 70), 0.15) if not fl else WHITE, fl)
    if not fl:
        for ax_, ay_, bx_, by_ in ((-6, -22, -2, -15), (-2, -15, -6, -9), (5, -23, 3, -16)):
            D.line(s, (255, 150, 70), (x + ax_, y + ay_), (x + bx_, y + by_), 1)
        eyec = (255, 220, 120) if flick else (255, 100, 60)
        s.fill(eyec, (x - 5, y - 27, 3, 3))
        s.fill(eyec, (x + 2, y - 27, 3, 3))
    up = -8 if wind else int(math.sin(t * 3) * 1)
    for sg in (-1, 1):
        block(s, x + sg * 13 - 3, y - 22 + up, 6, 12, (104, 88, 82), fl)
        block(s, x + sg * 13 - 4, y - 11 + up, 8, 7, (122, 104, 96), fl)
    if wind:
        spark_ring(s, x, y - 30, t, (255, 190, 100), 4, 12, 8)


def _phantom(s, e, x, y, fl):
    t, v = e["an"], e["var"]
    col = dict(bulk=(170, 120, 90), alch=(110, 200, 130), heat=(255, 130, 80))[v]
    al = 150 + int(40 * math.sin(t * 5))
    sf = pygame.Surface((30, 34), SC)
    c4 = col + (al,)
    dc = drk(col, 0.35) + (al,)
    D.rect(sf, dc, (9, 9, 12, 13))
    D.rect(sf, c4, (10, 9, 10, 11))
    D.rect(sf, c4, (11, 1, 9, 8))
    D.rect(sf, dc, (11, 22, 4, 8))
    D.rect(sf, dc, (17, 22, 4, 8))
    sway = int(math.sin(t * 6) * 1)
    if v == "bulk":
        D.rect(sf, (200, 210, 240, al), (2, 8 + sway, 5, 16))
        D.rect(sf, (240, 245, 255, al), (2, 8 + sway, 5, 1))
    elif v == "alch":
        D.circle(sf, (220, 255, 200, al), (24, 6 + sway), 4, 1)
        sf.fill((160, 255, 160, al), (23, 5 + sway, 2, 2))
    else:
        D.polygon(sf, (255, 200, 90, al), [(12, 1), (15, -3 + int(t * 9) % 3), (18, 1)])
        D.circle(sf, (255, 230, 150, al), (6, 11 + sway), 3)
    sf.fill((255, 255, 255, 255), (13, 4, 2, 2))
    sf.fill((255, 255, 255, 255), (17, 4, 2, 2))
    if e["st"] == "wind" and int(t * 16) % 2:
        D.rect(sf, (255, 90, 80, 255), (7, 0, 16, 31), 1)
    out = pygame.Surface((30, 34), SC)
    glitch = int(t * 6) % 7 == 0
    for ry in range(0, 34, 2):                                  # 글리치: 가로 줄이 어긋난다
        off = 0
        if glitch and (ry // 2 + int(t * 30)) % 4 == 0:
            off = 3 if (ry // 2) % 2 else -3
        out.blit(sf, (off, ry), (0, ry, 30, 2))
    for ry in range(0, 34, 4):                                  # 주사선
        out.fill((0, 0, 0, 0), (0, ry, 30, 1))
    if e["st"] in ("wind", "dash"):
        gh = out.copy()
        gh.set_alpha(80)
        s.blit(gh, (x - 15 - int(e.get("lx", 0) * 6), y - 31 - int(e.get("ly", 0) * 3)))
    if fl:
        out.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGB_ADD)
    s.blit(out, (x - 15, y - 31))


def draw_ex_body(s, e, x, y, g):
    sub, fl = e["sub"], e["fl"] > 0
    if sub == "gear":
        _gear(s, e, x, y, fl)
        return
    if sub == "orb":
        _orb(s, e, x, y, fl)
        return
    sh = shadow(s)
    if sh is not None:
        s.blit(sh, (x - 6, y - 1))
    if sub == "golem":
        _golem(s, e, x, y, fl)
    elif sub == "phantom":
        _phantom(s, e, x, y, fl)
    D.rect(s, (24, 20, 36), (x - 9, y - 34, 18, 3))
    s.fill((235, 70, 70), (x - 8, y - 33, int(16 * max(0, e["hp"]) // e["mhp"]), 1))


# ================================================================= 빅 브라더 : 기계 심장 + 감시의 눈
def _beat(t, rate):
    """두 번 쿵-쿵 뛰는 심장 박동 (0~1)"""
    f = (t * rate) % 1.0
    return max(max(0.0, 1 - abs(f - 0.06) / 0.09), 0.65 * max(0.0, 1 - abs(f - 0.26) / 0.09))


def _heart_pts(x, y, k, n=40):
    pts = []
    for i in range(n):
        a = i * TAU / n
        px = 16 * math.sin(a) ** 3
        py = -(13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a))
        pts.append((x + px * k, y + py * k))
    return pts


def _eye(s, e, x, cy, col, ph, beat, an, fl):
    W, H = 10, 7
    if ph == 1:                                                 # 눈꺼풀이 닫혀 있다가 가끔 실눈을 뜬다
        glance = (an * 0.7) % 4.0
        target = 0.28 if 3.0 < glance < 3.5 else 0.0
    else:
        target = 1.0 if ph < 4 else 0.85
    lid = e["_lid"] = e.get("_lid", 0.0) + (target - e.get("_lid", 0.0)) * 0.12
    D.ellipse(s, OUT, (x - W - 2, cy - H - 2, 2 * W + 4, 2 * H + 4))
    D.ellipse(s, (16, 14, 30), (x - W, cy - H, 2 * W, 2 * H))
    look = e.get("lk", 0.0)
    jit = int(math.sin(an * 37) * 2) if ph == 3 else 0
    ix, iy = x + int(math.cos(look) * 3) + jit, cy + int(math.sin(look) * 2)
    old = s.get_clip()
    s.set_clip(old.clip(pygame.Rect(x - W, cy - H, 2 * W, 2 * H)))
    if ph == 3:                                                 # 정신 오염: 붉은 잔상 홍채
        D.circle(s, (255, 70, 90), (ix - 3 - jit, iy + 1), 6)
    D.circle(s, drk(col, 0.45), (ix, iy), 6)
    D.circle(s, WHITE if fl else col, (ix, iy), 5)
    D.circle(s, lit(col, 0.5), (ix, iy), 3, 1)
    pr = 1 + int(beat * 2) + (2 if ph == 4 else 0)
    D.circle(s, (255, 40, 50) if ph == 4 else (10, 8, 20), (ix, iy), pr)
    s.fill(WHITE, (ix - 3, iy - 3, 2, 2))
    if ph == 4:                                                 # 깨진 눈
        for ax_, ay_, bx_, by_ in ((-9, -4, -1, 0), (-1, 0, 4, -7), (4, -7, 10, -5), (-2, 1, 3, 8), (3, 8, 9, 6)):
            D.line(s, WHITE, (x + ax_, cy + ay_), (x + bx_, cy + by_), 1)
    if lid < 0.99:                                              # 금속 눈꺼풀
        h = int((1 - lid) * H) + 1
        for top in (True, False):
            if top:
                s.set_clip(old.clip(pygame.Rect(x - W - 1, cy - H - 1, 2 * W + 2, h + 1)))
            else:
                s.set_clip(old.clip(pygame.Rect(x - W - 1, cy + H - h, 2 * W + 2, h + 2)))
            D.ellipse(s, WHITE if fl else (118, 126, 152), (x - W, cy - H, 2 * W, 2 * H))
            D.ellipse(s, drk((118, 126, 152), 0.3), (x - W + 2, cy - H + 2, 2 * W - 4, 2 * H - 4), 1)
        s.set_clip(old.clip(pygame.Rect(x - W, cy - 1, 2 * W, 2)))
        if lid < 0.1:
            s.fill(mix(col, WHITE, 0.4 * beat), (x - W + 2, cy, 2 * W - 4, 1))
    s.set_clip(old)
    D.ellipse(s, drk((118, 126, 152), 0.2), (x - W - 1, cy - H - 1, 2 * W + 2, 2 * H + 2), 1)
    for i in range(8):                                          # 눈 둘레 리벳 등
        a = an * (0.5 if ph < 3 else 1.6) + i * TAU / 8
        s.fill(col if int(a * 2) % 2 else drk(col, 0.5), (int(x + math.cos(a) * (W + 3)), int(cy + math.sin(a) * (H + 3)), 2, 2))


def _plate(s, px, py, a, col, fl):
    ca, sa = math.cos(a), math.sin(a)
    pts = [(px + ca * 5 - sa * 3, py + sa * 5 + ca * 3), (px + ca * 5 + sa * 3, py + sa * 5 - ca * 3),
           (px - ca * 5 + sa * 3, py - sa * 5 - ca * 3), (px - ca * 5 - sa * 3, py - sa * 5 + ca * 3)]
    D.polygon(s, WHITE if fl else (126, 134, 160), pts)
    D.polygon(s, OUT, pts, 1)
    D.line(s, col, pts[0], pts[1], 1)


def _ell(x, y, rx, ry, n=22):
    return [(x + math.cos(i * TAU / n) * rx, y + math.sin(i * TAU / n) * ry) for i in range(n)]


def _tube(s, pts, w, c, fl=False):
    """외곽선이 이어지는 굵은 관 (혈관)"""
    pts = [(int(px), int(py)) for px, py in pts]
    w = max(2, int(w))
    for p, q in zip(pts, pts[1:]):
        D.line(s, OUT, p, q, w + 2)
    for p in pts:
        D.circle(s, OUT, p, w // 2 + 1)
    cc = WHITE if fl else c
    for p, q in zip(pts, pts[1:]):
        D.line(s, cc, p, q, w)
    for p in pts:
        D.circle(s, cc, p, max(1, w // 2))
    if not fl and w >= 4:
        for p, q in zip(pts, pts[1:]):
            D.line(s, lit(c, 0.35), (p[0] - 1, p[1] - 1), (q[0] - 1, q[1] - 1), 1)


# 해부학적 심장 색 (심실, 심방, 대동맥, 정맥, 폐동맥)
_HCOL = {1: ((112, 120, 146), (98, 106, 132), (136, 144, 166), (92, 108, 140), (96, 118, 150)),
         2: ((158, 66, 82), (128, 56, 86), (206, 64, 70), (62, 90, 170), (74, 110, 184)),
         3: ((182, 50, 56), (150, 42, 64), (232, 72, 60), (68, 84, 170), (80, 100, 194)),
         4: ((214, 180, 168), (194, 156, 154), (244, 216, 196), (190, 202, 232), (202, 216, 238))}
_VENT = [(-12, -8), (-14, 0), (-11, 8), (-5, 14), (3, 19), (8, 17), (12, 10), (14, 2), (13, -6), (8, -12), (0, -13), (-7, -12)]
_RV = [(-12, -8), (-14, 0), (-11, 8), (-5, 14), (3, 19), (5, 10), (3, 0), (2, -12), (-7, -12)]
_CORO = (((-12, -3), (-4, -8), (3, -9), (10, -8)), ((3, -9), (4, 0), (6, 10), (8, 16)), ((10, -8), (13, 0), (12, 8)),
         ((-4, -8), (-7, 0), (-6, 8)))


def _heart_boss(s, e, cx, cy, t, g):
    R = _R
    ph, an = e["phase"], e["an"]
    col = R.B.PHASE_COL[ph - 1]
    rate = (1.0, 1.3, 1.8, 3.2)[ph - 1]
    beat = _beat(an, rate)
    K = (1 + 0.1 * beat) * 1.25
    x = int(e["x"]) - cx + (int(math.sin(an * 60) * 1) if ph == 4 else 0)
    y = int(e["y"]) - cy + round(math.sin(an * 2) * 2)
    hy = y - 3
    fl = e["fl"] > 0 or (e["inv"] > 0 and int(an * 20) % 2 == 1)
    ven, atr, aor, vei, pul = _HCOL[ph]

    def P(px, py):
        return (x + px * K, hy + py * K)

    def PL(pts):
        return [P(*p) for p in pts]
    try:
        s.blit(pygame.transform.scale(R.G.SHADOW, (46, 11)), (x - 23, y + 20))
    except Exception:
        pass
    # --- 서브 코어와 이어진 케이블 (박동에 맞춰 에너지가 흐른다)
    alive = 0
    if ph == 1:
        for c in e.get("cores", []):
            if c["hp"] <= 0:
                continue
            alive += 1
            px, py = int(c["x"]) - cx, int(c["y"]) - cy
            D.line(s, (40, 90, 120), (x, hy), (px, py - 8), 3)
            D.line(s, (150, 236, 240), (x, hy), (px, py - 8), 1)
            for i in range(3):
                f = (an * rate * 0.5 + i / 3 + alive * 0.17) % 1.0
                D.circle(s, WHITE, (int(x + (px - x) * f), int(hy + (py - 8 - hy) * f)), 2)
    # --- 뒤쪽 장갑 파편
    if 2 <= ph <= 3:
        sp = 0.8 if ph == 2 else 1.9
        for i in range(4):
            a = an * sp + i * TAU / 4
            if math.sin(a) <= 0:
                _plate(s, x + math.cos(a) * 36, hy + math.sin(a) * 11, a + 1.5, col, fl)
    # --- 상대정맥 / 대동맥궁 + 가지 (배경)
    _tube(s, PL([(-9, -14), (-9, -22), (-8, -30)]), 5 * K, vei, fl)
    _tube(s, PL([(1, -11), (2, -20), (6, -27), (12, -27), (16, -21), (16, -14)]), 6 * K, aor, fl)
    tips = []
    for a0, a1 in (((4, -26), (3, -33)), ((8, -28), (9, -34)), ((11, -27), (14, -32))):
        _tube(s, PL([a0, a1]), 3 * K, aor, fl)
        tips.append(P(*a1))
    # --- 심방
    poly(s, PL(_ell(-10, -6, 7, 9)), WHITE if fl else atr, fl)
    poly(s, PL(_ell(9, -11, 5, 4)), WHITE if fl else atr, fl)
    # --- 심실 덩어리 (우심실은 한 톤 어둡게, 사이에 심실간 고랑)
    poly(s, PL(_VENT), ven, fl)
    if not fl:
        D.polygon(s, mix(ven, (50, 36, 90), 0.28), PL(_RV))
        D.polygon(s, OUT, PL(_VENT), 1)
        D.polygon(s, lit(ven, 0.1), PL([(0 + (px - 1) * 0.74 + 3, 3 + (py - 3) * 0.74 - 1) for px, py in _VENT]))
        D.line(s, drk(ven, 0.55), P(2, -12), P(4, 2), 1)
        D.line(s, drk(ven, 0.55), P(4, 2), P(7, 18), 1)
        gl = P(5, -2)
        D.ellipse(s, lit(ven, 0.5), (gl[0] - 3, gl[1] - 6, 5, 9))
    # --- 폐동맥 (대동맥 앞을 가로지른다)
    _tube(s, PL([(3, -11), (6, -17), (12, -19), (16, -17)]), 5 * K, pul, fl)
    # --- 표면 문양: 1페이즈 장갑 이음매 / 이후 맥동하는 관상동맥
    if not fl:
        if ph == 1:
            seam = drk(ven, 0.5)
            for line in _CORO:
                for p, q in zip(line, line[1:]):
                    D.line(s, seam, P(*p), P(*q), 1)
            for rx, ry in ((-10, 0), (-6, 10), (9, 8), (11, -4), (0, -10), (-10, -8), (4, 16)):
                pp = P(rx, ry)
                s.fill(lit(ven, 0.6), (int(pp[0]), int(pp[1]), 2, 2))
        else:
            vc = mix(drk(col, 0.55), col, 0.35 + 0.65 * beat)
            for line in _CORO:
                for p, q in zip(line, line[1:]):
                    D.line(s, vc, P(*p), P(*q), 1)
        if ph == 3:                                             # 해킹: 글리치 가로줄
            for i in range(3):
                yy = hy - 20 + ((int(an * 20) + i * 9) % 44)
                s.fill(col, (int(x - 16 + (i * 5) % 8), int(yy), 10 + i * 4, 1))
        if ph == 4:                                             # 폭주: 균열에서 빛이 샌다
            for ax_, ay_, bx_, by_ in ((-3, -12, -7, -3), (-7, -3, -13, 2), (6, -11, 9, -2), (9, -2, 4, 7), (-2, 6, -5, 13), (7, 8, 6, 16)):
                D.line(s, (255, 250, 230), P(ax_, ay_), P(bx_, by_), 2)
                D.line(s, (255, 120, 90), P(ax_, ay_), P(bx_, by_), 1)
    # --- 서브 코어 연결구
    for i, (rx, ry) in enumerate(((-15, -8), (9, -12), (-9, 9), (11, 7))):
        on = (i < alive) if ph == 1 else ph >= 2
        pp = P(rx, ry)
        D.circle(s, OUT, (int(pp[0]), int(pp[1])), 3)
        D.circle(s, mix(col, WHITE, 0.5 * beat) if on else (46, 48, 68), (int(pp[0]), int(pp[1])), 2)
    # --- 혈관 끝: 증기 / 불꽃
    for i, tp in enumerate(tips + [P(-8, -30)]):
        if ph == 4:
            if int(an * 30 + i) % 2:
                s.fill((255, 240, 180), (int(tp[0] + math.sin(an * 50 + i) * 2), int(tp[1] - 4), 2, 2))
        else:
            puff(s, tp[0], tp[1] - 1, an, (214, 222, 236) if ph < 3 else (232, 150, 120), 2, 8, 1.0 + beat, i, 1)
    # --- 눈 (심실 앞면에 박혀 있다)
    ep = P(-1, 3)
    _eye(s, e, int(ep[0]), int(ep[1]), col, ph, beat, an, fl)
    if ph == 3:                                                 # 해킹: 곁눈들이 깜빡인다
        for i, (rx, ry) in enumerate(((-15, 2), (12, 0), (-9, 14), (8, 14))):
            pp = P(rx, ry)
            if int(an * 3 + i * 1.7) % 3:
                D.ellipse(s, OUT, (int(pp[0]) - 3, int(pp[1]) - 2, 6, 4))
                s.fill((255, 70, 90), (int(pp[0]) - 1, int(pp[1]) - 1, 2, 2))
    # --- 앞쪽 장갑 파편
    if 2 <= ph <= 3:
        sp = 0.8 if ph == 2 else 1.9
        for i in range(4):
            a = an * sp + i * TAU / 4
            if math.sin(a) > 0:
                _plate(s, x + math.cos(a) * 36, hy + math.sin(a) * 11, a + 1.5, col, fl)
    if ph == 4:                                                 # 전기 호
        for i in range(2):
            a = an * 9 + i * 3.1
            D.line(s, WHITE, (x + math.cos(a) * 20, hy + math.sin(a) * 18),
                   (x + math.cos(a + 0.4) * 40, hy + math.sin(a - 0.3) * 36), 1)
    if e["al"] > 0:
        s.fill((255, 230, 80), (x - 1, y - 52, 2, 5))


# ================================================================= 위험 구역 이펙트 (경고 + 폭발)
_OLD_HZ = None


def _hcol(h):
    if not h["dmg"] and not h.get("los"):
        return (255, 236, 160)
    fx = h.get("fx")
    return (130, 214, 255) if fx == "freeze" else (255, 150, 50) if fx == "burn" else (255, 84, 70)


def _ngon(cx, cy, r, a0, n):
    return [(cx + math.cos(a0 + i * TAU / n) * r, cy + math.sin(a0 + i * TAU / n) * r) for i in range(n)]


# 존별 레이저 색 (바깥 -> 안쪽): 벌크스틸 호박 / 알케미스트 독록 / 오버히트 불꽃 / 빅 브라더 진홍 / 화룡 용암
BEAM_COL = {"boss_w": ((120, 60, 20), (240, 150, 50), (255, 214, 120)), "boss_e": ((20, 90, 40), (90, 220, 90), (200, 255, 160)),
            "boss_n": ((140, 30, 20), (255, 110, 40), (255, 210, 120)), "boss_f": ((110, 10, 40), (240, 60, 100), (255, 170, 190)),
            "boss_d": ((120, 20, 10), (255, 90, 30), (255, 200, 110)), "storm": ((20, 50, 120), (80, 180, 255), (210, 245, 255))}


def _quad(L, c, x, y, ca, sa, s0, s1, hw):
    nx, ny = -sa * hw, ca * hw
    D.polygon(L, c, [(x + ca * s0 + nx, y + sa * s0 + ny), (x + ca * s1 + nx, y + sa * s1 + ny),
                     (x + ca * s1 - nx, y + sa * s1 - ny), (x + ca * s0 - nx, y + sa * s0 - ny)])


def _beam_body(L, g, h, x, y, ca, sa, ln, w, t, out, fx):
    """위에서 본 레이저: 곧은 빛줄기 여러 겹 + 가장자리의 흐르는 빛 + 앞으로 달려가는 맥동 띠 + 옆으로 튀는 불똥"""
    if fx == "freeze":
        dk, md, hi = (30, 70, 140), (110, 190, 255), (220, 245, 255)
    else:
        dk, md, hi = BEAM_COL.get("storm" if h.get("th") == "storm" else g.get("zid"), ((140, 30, 20), (255, 110, 60), (255, 220, 150)))
    pulse = 0.5 + 0.5 * math.sin(t * 30)
    hw = w / 2 * (0.92 + 0.12 * pulse)
    a8 = lambda v: max(0, min(255, int(v * out)))                       # noqa: E731
    _quad(L, dk + (a8(70),), x, y, ca, sa, 0, ln, hw + 6)                 # 바깥 아지랑이
    _quad(L, md + (a8(150),), x, y, ca, sa, 0, ln, hw + 2)
    _quad(L, md + (a8(235),), x, y, ca, sa, 0, ln, hw)
    _quad(L, hi + (a8(250),), x, y, ca, sa, 0, ln, max(1.0, hw * 0.55))
    _quad(L, (255, 255, 255, a8(255)), x, y, ca, sa, 0, ln, max(0.6, hw * 0.22))
    nx, ny = -sa, ca
    for sd in (-1, 1):                                                    # 가장자리: 흘러가는 점선
        ox, oy = nx * (hw + 1) * sd, ny * (hw + 1) * sd
        ph = (t * 220) % 10
        s_ = ph
        while s_ < ln:
            L.fill(hi + (a8(230),), (int(x + ca * s_ + ox), int(y + sa * s_ + oy), 2, 1 if abs(ca) > abs(sa) else 2))
            s_ += 10
    for i in range(int(ln // 34) + 1):                                    # 앞으로 달려가는 맥동 띠
        s_ = (t * 260 + i * 34) % max(1.0, ln)
        _quad(L, (255, 255, 255, a8(200)), x, y, ca, sa, s_, s_ + 3, hw + 3)
    for i in range(12):                                                   # 옆으로 튀어 나가는 불똥
        f = (t * 3.2 + i * 0.37) % 1.0
        s_ = (i * 53.7 + t * 40) % max(1.0, ln)
        sd = 1 if i % 2 else -1
        d = hw + 2 + f * (w * 1.2 + 6)
        L.fill(hi + (a8(255 * (1 - f)),), (int(x + ca * s_ + nx * d * sd), int(y + sa * s_ + ny * d * sd), 2, 2))
    if fx == "burn":
        for i in range(int(ln // 26)):
            flame(L, x + ca * (14 + i * 26), y + sa * (14 + i * 26), t, 7, 5, i, (255, 150, 50))


def draw_one_hz(L, g, h, cx, cy, t):
    k = h["kind"]
    if k not in ("circle", "rect", "beam", "well", "knock"):
        return _OLD_HZ(L, g, h, cx, cy, t)
    warn = h["warn"] > 0
    col = _hcol(h)
    hotc = lit(col, 0.55)
    age = h.get("age", 0.0)
    f_in = min(1.0, age / 0.25)
    if warn:
        out = min(1.0, h["warn"] / 0.12) if (not h["dmg"] and h["act"] <= 0.01) else 1.0
    else:
        out = min(1.0, max(0.0, h["act"]) / 0.2)
    p = 1 - max(0.0, h["warn"]) / h["tot"]
    fo = f_in * out
    ta = max(0.0, age - h["tot"])
    fx = h.get("fx")
    LR = L.get_rect()
    if k == "circle":
        x, y, r = int(h["x"]) - cx, int(h["y"]) - cy, max(2, int(h["r"]))
        if warn:
            D.circle(L, col + (int((26 + 80 * p) * fo),), (x, y), max(1, int(r * (0.15 + 0.85 * p))))
            D.circle(L, col + (int(170 * fo),), (x, y), r, 1)
            for i in range(0, max(12, r // 2), 2):              # 회전하는 점선 고리
                a = i * TAU / max(12, r // 2) + t * 0.9
                L.fill(col + (int(230 * fo),), (x + int(math.cos(a) * r), y + int(math.sin(a) * r), 2, 2))
            if r >= 14:                                         # 안쪽 룬: 서로 반대로 도는 삼각형
                for a0, sg in ((t * 1.3, 1), (-t * 1.3 + 1.05, -1)):
                    D.polygon(L, col + (int((70 + 110 * p) * fo),), _ngon(x, y, r * 0.68, a0, 3), 1)
            for i in range(4):                                  # 십자 눈금
                a = i * TAU / 4
                D.line(L, col + (int(220 * fo),), (x + math.cos(a) * (r - 5), y + math.sin(a) * (r - 5)), (x + math.cos(a) * r, y + math.sin(a) * r), 1)
            for i in range(6):                                  # 바깥에서 모여드는 입자
                f = (t * 1.1 + i / 6) % 1.0
                a = i * 1.047 + h["x"]
                L.fill(hotc + (int(200 * fo * (1 - f)),), (x + int(math.cos(a) * r * (1.5 - 0.5 * f)), y + int(math.sin(a) * r * (1.5 - 0.5 * f)), 2, 2))
            if p > 0.8:
                D.circle(L, (255, 255, 255, int(160 * fo * (p - 0.8) * 5)), (x, y), r, 2)
        else:
            D.circle(L, col + (int(52 * out),), (x, y), r)                 # 터지는 그림은 v9_pfx 의 이펙트가 맡는다. 여기서는 판정 범위만 은은하게 남긴다
            D.circle(L, (255, 232, 196, int(34 * out)), (x, y), max(1, int(r * 0.62)))
            D.circle(L, col + (int(255 * out),), (x, y), r, 2)
            if ta < 0.28:                                       # 폭발 충격파
                f = ta / 0.28
                D.circle(L, (255, 245, 220, int(220 * (1 - f) * out)), (x, y), int(r * (1.0 + 0.55 * f)), 3)
            for i in range(10):                                 # 튀는 파편
                f = (ta * 1.6 + i * 0.13) % 1.0
                a = i * TAU / 10 + h["x"] * 0.1
                dd = r * (0.25 + f * 0.95)
                L.fill((255, 240, 200, int(240 * (1 - f) * out)), (x + int(math.cos(a) * dd), y + int(math.sin(a) * dd), 2, 2))
            if fx == "burn" and out > 0.4:
                for i in range(5):
                    a = i * 1.257 + h["y"]
                    flame(L, x + math.cos(a) * r * 0.55, y + math.sin(a) * r * 0.35 + 3, t, 9, 6, i, (255, 140, 50))
            elif fx == "freeze":
                for i in range(8):
                    a = i * TAU / 8 + 0.2
                    bx, by = x + math.cos(a) * r, y + math.sin(a) * r
                    D.polygon(L, (200, 238, 255, int(240 * out)), [(bx - math.sin(a) * 3, by + math.cos(a) * 3), (bx + math.cos(a) * 9, by + math.sin(a) * 9), (bx + math.sin(a) * 3, by - math.cos(a) * 3)])
                for i in range(3):
                    a = i * 1.047 + 0.3
                    D.line(L, (230, 248, 255, int(220 * out)), (x - math.cos(a) * r * 0.7, y - math.sin(a) * r * 0.7), (x + math.cos(a) * r * 0.7, y + math.sin(a) * r * 0.7), 1)
    elif k == "rect":
        rc = pygame.Rect(int(h["x0"]) - cx, int(h["y0"]) - cy, int(h["x1"] - h["x0"]), int(h["y1"] - h["y0"]))
        clip = rc.clip(LR)
        if clip.w <= 0 or clip.h <= 0:
            return
        horiz = rc.w >= rc.h
        if warn:
            L.fill(col + (int((18 + 66 * p) * fo),), clip)
            old = L.get_clip()
            L.set_clip(clip)
            sh = int(t * 18) % 12
            for xx in range(rc.x - rc.h, rc.right, 12):
                D.line(L, col + (int(140 * fo),), (xx + sh, rc.bottom), (xx + sh + rc.h, rc.y), 1)
            pos = (t * 1.4) % 1.0                               # 훑고 지나가는 스캔선
            if horiz:
                L.fill(hotc + (int(200 * fo),), (rc.x + int(rc.w * pos), rc.y, 2, rc.h))
            else:
                L.fill(hotc + (int(200 * fo),), (rc.x, rc.y + int(rc.h * pos), rc.w, 2))
            L.set_clip(old)
            D.rect(L, col + (int(220 * fo),), rc, 1)
            for sx_, sy_ in ((rc.x, rc.y), (rc.right - 1, rc.y), (rc.x, rc.bottom - 1), (rc.right - 1, rc.bottom - 1)):
                dx_ = 6 if sx_ == rc.x else -6
                dy_ = 6 if sy_ == rc.y else -6
                D.line(L, hotc + (int(255 * fo),), (sx_, sy_), (sx_ + dx_, sy_), 2)
                D.line(L, hotc + (int(255 * fo),), (sx_, sy_), (sx_, sy_ + dy_), 2)
        else:
            if not h.get("_fld"):                               # 표면 이펙트(v9_pfx 의 field 타일)가 없을 때만 평평한 채움
                L.fill(col + (int(64 * out),), clip)
                inner = rc.inflate(-6, -6).clip(LR)
                if inner.w > 0 and inner.h > 0:
                    L.fill((255, 232, 196, int(46 * out)), inner)
            old = L.get_clip()
            L.set_clip(clip)
            n = 0 if h.get("_fld") else 3
            for i in range(n):                                  # 출렁이는 플라즈마 선
                pts = []
                if horiz:
                    yy = rc.y + rc.h * (i + 1) / (n + 1)
                    for xx in range(rc.x, rc.right + 8, 8):
                        pts.append((xx, yy + math.sin(xx * 0.09 + t * 14 + i * 2) * min(3, rc.h * 0.2)))
                else:
                    xx0 = rc.x + rc.w * (i + 1) / (n + 1)
                    for yy in range(rc.y, rc.bottom + 8, 8):
                        pts.append((xx0 + math.sin(yy * 0.09 + t * 14 + i * 2) * min(3, rc.w * 0.2), yy))
                if len(pts) > 1:
                    D.lines(L, (255, 255, 255, int(230 * out)), False, pts, 1)
            ln = rc.w if horiz else rc.h
            for i in range(8):                                  # 테두리를 따라 튀는 불꽃
                q = int((t * 70 + i * 37) % max(1, ln))
                if horiz:
                    L.fill((255, 250, 220, int(240 * out)), (rc.x + q, rc.y - 1 + (i % 2) * (rc.h + 1), 2, 2))
                else:
                    L.fill((255, 250, 220, int(240 * out)), (rc.x - 1 + (i % 2) * (rc.w + 1), rc.y + q, 2, 2))
            L.set_clip(old)
            D.rect(L, (255, 255, 255, int(245 * out)), rc, 2)
    elif k == "beam":
        x, y, a, ln, w = h["x"] - cx, h["y"] - cy, h["a"], h["len"], h["w"]
        ca, sa = math.cos(a), math.sin(a)
        ex, ey = x + ca * ln, y + sa * ln
        if warn:
            D.line(L, col + (int((70 + 130 * p) * fo),), (x, y), (ex, ey), max(1, int(w * 0.28 * (0.4 + 0.6 * p))))
            for i in range(10, int(ln), 14):
                L.fill(col + (int(190 * fo),), (int(x + ca * i), int(y + sa * i), 2, 2))
            ph_ = (t * 90) % 28                                  # 앞으로 흐르는 화살표
            for i in range(int(ph_), int(ln), 28):
                if i > 12:
                    bx, by = x + ca * i, y + sa * i
                    D.lines(L, hotc + (int(210 * fo),), False, [(bx - ca * 4 - sa * 3, by - sa * 4 + ca * 3), (bx, by), (bx - ca * 4 + sa * 3, by - sa * 4 - ca * 3)], 1)
            D.circle(L, col + (int(230 * fo),), (int(x), int(y)), 4 + int(6 * p), 1)
            for i in range(3):
                aa = t * 3 + i * 2.094
                L.fill(hotc + (int(240 * fo),), (int(x + math.cos(aa) * (5 + 6 * p)), int(y + math.sin(aa) * (5 + 6 * p)), 2, 2))
        else:
            _beam_body(L, g, h, x, y, ca, sa, ln, w, t, out, fx)
    elif k == "well":
        x, y, r = int(h["x"]) - cx, int(h["y"]) - cy, int(h["r"])
        dirn = 1 if h.get("pull", 1) > 0 else -1
        R_ = min(r, 210)
        sp = 0.25 if warn else 0.65
        for arm in range(3):                                    # 소용돌이 나선 팔
            for j in range(16):
                f = (j / 16 + t * sp * dirn) % 1.0
                rr = R_ * (1 - f if dirn > 0 else f)
                aa = arm * TAU / 3 + (rr / R_) * 3.6 * dirn + t * 0.8
                if rr > 5:
                    L.fill((196, 160, 255, int(220 * f_in * out * math.sin(f * 3.1416))), (x + int(math.cos(aa) * rr), y + int(math.sin(aa) * rr * 0.85), 2, 2))
        D.circle(L, (170, 120, 255, int(70 * f_in * out)), (x, y), R_, 1)
        D.circle(L, (90, 50, 170, int(120 * fo)), (x, y), 9 if not warn else 4)
        D.circle(L, (30, 14, 60, int(230 * fo)), (x, y), 6 if not warn else 3)
        D.circle(L, (200, 160, 255, int(255 * fo)), (x, y), 9 if not warn else 4, 1)
    elif k == "knock":
        x, y = int(h["x"]) - cx, int(h["y"]) - cy
        if warn:
            D.circle(L, col + (int(210 * fo),), (x, y), int(10 + p * 14), 1)
            D.circle(L, col + (int(60 * fo),), (x, y), int(6 + p * 8))
            for i in range(8):
                f = (t * 1.6 + i / 8) % 1.0
                aa = i * 0.785
                L.fill(hotc + (int(220 * fo),), (x + int(math.cos(aa) * (26 - 22 * f)), y + int(math.sin(aa) * (26 - 22 * f)), 2, 2))
        else:
            r = int(h["r"])
            fade = max(0.15, 1 - r / h["maxr"])
            for i, (dr, al, wd) in enumerate(((0, 235, 5), (7, 150, 3), (15, 80, 2))):
                if r - dr > 2:
                    D.circle(L, (255, 244, 214, int(al * fade * out)), (x, y), r - dr, wd)
            D.circle(L, col + (int(210 * fade * out),), (x, y), max(1, r - 4), 2)
            for i in range(28):                                 # 파면을 따라 번지는 균열 눈금
                aa = i * TAU / 28 + h["x"] * 0.01
                D.line(L, (255, 255, 255, int(190 * fade * out)), (x + math.cos(aa) * (r - 3), y + math.sin(aa) * (r - 3)),
                       (x + math.cos(aa) * (r + 4), y + math.sin(aa) * (r + 4)), 1)


# ================================================================= 설치
def apply(R):
    """v9_roster.install() 보다 먼저 호출한다."""
    global _R, _OLD_HZ
    _R = R
    R.draw_bulk, R.draw_alch, R.draw_heat, R.draw_ex_body = draw_bulk, draw_alch, draw_heat, draw_ex_body
    old_body = R.draw_mid_body

    def draw_mid_body(s, e, x, y, g):
        # 최종 보스의 순간이동 잔상(blink_to)도 이 함수로 들어온다 (id=3 -> 원래 코드는 IndexError)
        if e.get("kind") == "final" or e.get("id", 0) > 2:
            _heart_boss(s, e, int(e["x"]) - x, int(e["y"]) - y, 0, g)
            return
        old_body(s, e, x, y, g)
    R.draw_mid_body = draw_mid_body
    _OLD_HZ = R.draw_one_hz
    R.draw_one_hz = draw_one_hz                                 # 위험 구역 이펙트 교체
    orig = R.draw_final_wrap

    def wrap(old):
        def body(surf, e, cx, cy, t, g):
            _heart_boss(surf, e, cx, cy, t, g)                  # 기존 본체 그림 대신 기계 심장을 그린다
        return orig(body)
    R.draw_final_wrap = wrap