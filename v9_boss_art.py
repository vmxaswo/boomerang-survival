"""v9 보스 아트 연결 모듈 (v9_boss_art.py)
중간보스 3기(벌크스틸·알케미스트·오버히트)와 최종보스(빅 브라더 Ω)의 새 디자인을 게임에 연결한다.
 - 각 보스는 v9_ba_bulk / v9_ba_alch / v9_ba_heat / v9_ba_core 가 큰 도화지에 그리고, 여기서 화면에 얹는다.
 - 전투 로직은 건드리지 않는다. 그리기 함수만 교체한다.
v9_roster_art.apply, v9_roster_pat.apply 뒤, v9_roster.install 앞에서 한 번 부른다:
    import v9_boss_art
    v9_boss_art.apply(v9_roster)
"""
import math

import pygame

import v9_ba_alch
import v9_ba_bulk
import v9_ba_core
import v9_ba_heat
import v9_ba_kit as K

D = pygame.draw
SC = pygame.SRCALPHA
BODIES = (v9_ba_bulk.draw, v9_ba_alch.draw, v9_ba_heat.draw)
SC_ = (1.0, 1.0, 1.0, 1.0)              # 보스별 표시 배율 (벌크스틸·알케미스트·오버히트·빅 브라더) - 원래 크기의 약 1.2배
TOP = (60, 88, 62, 100)                  # 체력·표식을 띄울 높이 (도화지 기준, 배율 적용 전)
GLOW_R = (80, 70, 80)
ANCH = {0: (110, 150), 1: (110, 150), 2: (110, 150), 3: (110, 150)}                       # 3D 리그 도화지를 쓰는 보스의 기준점 (나머지는 v9_ba_kit 기본값)


GHOST_COL = ((255, 170, 90), (130, 255, 150), (255, 130, 70))


def _ghosts(s, e, x, y, g, cv, bi):
    """대쉬 중(v9_pfx 가 e['_dash'] 를 켠다)에는 지나간 자리에 색이 입혀진 잔상이 남아 사라진다"""
    t = g.get("t", 0.0)
    gh = e.setdefault("_gh", [])
    if e.get("_dash") and t - e.get("_gh_t", -9) > 0.04:
        e["_gh_t"] = t
        c = cv.copy()
        c.fill(GHOST_COL[min(2, bi)] + (255,), special_flags=pygame.BLEND_RGBA_MULT)
        gh.append([c, e["x"], e["y"], t])
    cx, cy = e["x"] - x, e["y"] - y
    keep = []
    for c, gx, gy, t0 in gh:
        age = t - t0
        if 0 <= age < 0.26:
            keep.append([c, gx, gy, t0])
            K.put(s, c, gx - cx, gy - cy, alpha=int(130 * (1 - age / 0.26)), scale=SC_[bi], anchor=ANCH.get(bi))
    e["_gh"] = keep


def apply(R):
    def body_of(e, g=None):
        i = e.get("id", 0)
        if g is not None and i == 1:
            e["fa2"] = math.atan2(g["y"] - e["y"], g["x"] - e["x"])      # 알케미스트는 플레이어 쪽으로 돌아선다
        if e.get("kind") == "final" or i > 2:
            if g is not None:
                e["fa2"] = math.atan2(g["y"] - e["y"], g["x"] - e["x"])
            return v9_ba_core.draw(e), 3
        return BODIES[i](e), i

    def draw_mid_body(s, e, x, y, g):
        cv, i = body_of(e, g)
        sc = SC_[i]
        top = int(TOP[i] * sc)
        K.put(s, cv, x, y, scale=sc, anchor=ANCH.get(i))
        if e["inv"] > 0:
            D.circle(s, (255, 255, 255), (x, y - top // 2), int(top * 0.55 + 4 * math.sin(e["an"] * 8)), 1)
        if e.get("al", 0) > 0:
            s.fill((255, 230, 80), (x - 2, y - top - 12, 4, 8))
            s.fill((255, 230, 80), (x - 2, y - top - 2, 4, 3))

    def draw_mid(s, e, x, y, g, force=None, tint=False):
        a = force if force is not None else R.vis_alpha(g, e)
        if a <= 0.02:
            return
        i = min(2, e["id"])
        gc = (255, 150, 80) if i == 0 else ((130, 255, 160) if e["phase"] < 4 else (255, 150, 100)) if i == 1 else R.heat_col(e)
        boost = 2.0 if e["inv"] > 0 else 1.0
        if g["intro"] > 0:
            boost = 1.0 + 1.5 * math.sin(min(1.0, g["intro"] / 2.6) * 3.1416)
        ga = int((46 + 18 * math.sin(e["an"] * 3)) * a * boost) // 10 * 10
        if ga >= 10 and not tint:
            K.glow(s, x, y - 20, int(GLOW_R[i] * SC_[i] * (0.7 if i == 0 else 1.3)), gc, min(140, ga))
        cv, bi = body_of(e, g)
        top = int(TOP[bi] * SC_[bi])
        if not tint:
            _ghosts(s, e, x, y, g, cv, bi)
        K.put(s, cv, x, y, alpha=int(255 * min(1.0, a)) if (a < 0.98 or tint) else 255, tint=tint, scale=SC_[bi], anchor=ANCH.get(bi))
        if e["inv"] > 0:
            D.circle(s, (255, 255, 255), (x, y - top // 2), int(top * 0.55 + 4 * math.sin(e["an"] * 8)), 1)
        if e.get("al", 0) > 0:
            s.fill((255, 230, 80), (x - 2, y - top - 12, 4, 8))
            s.fill((255, 230, 80), (x - 2, y - top - 2, 4, 3))

    def draw_final_wrap(old):
        def f(surf, e, cx, cy, t, g):
            e["opened"] = True
            a = R.vis_alpha(g, e)
            ph = e["phase"]
            x, y = int(e["x"]) - cx, int(e["y"]) - cy
            v9_ba_core.cables(surf, e, cx, cy)
            e["fa2"] = math.atan2(g["y"] - e["y"], g["x"] - e["x"])
            cv = v9_ba_core.draw(e)
            K.put(surf, cv, x, y + 40, alpha=int(255 * a) if a < 0.98 else 255, anchor=ANCH[3])
            if ph == 1:
                v = pygame.Surface((200, 200), SC)
                D.circle(v, (120, 232, 232, int(45 + 20 * math.sin(t * 3))), (100, 100), 36)
                D.circle(v, (190, 250, 250, 210), (100, 100), 36, 2)
                surf.blit(v, (x - 100, y - 100))
            elif ph == 4 and "omega" in e:
                s = f"{max(0.0, e['omega']):.1f}"
                fn = R.font14()
                col = (255, 80, 70) if int(t * 4) % 2 or e["omega"] > 8 else (255, 230, 200)
                img, sh = fn.render(s, True, col), fn.render(s, True, (24, 20, 36))
                surf.blit(sh, (x - img.get_width() // 2 + 1, y - 70 + 1))
                surf.blit(img, (x - img.get_width() // 2, y - 70))
        return f

    R.draw_mid_body = draw_mid_body
    R.draw_mid = draw_mid
    R.draw_final_wrap = draw_final_wrap
