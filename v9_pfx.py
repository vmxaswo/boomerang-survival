"""v9 pixelfx 이펙트 모듈 (v9_pfx.py)
탑다운 전용 pixelfx 이펙트(fx_sheets/*.png + .json, gen_fx.py 로 생성)를 보스 패턴 연출에 얹는다.
 - 모든 이펙트는 위에서 내려다본 바닥 평면의 그림이다 (솟는 기둥·피어오르는 연기 없음). 판정 범위 안에서 터지고 1초 안에 사라진다.
 - 보스마다 컨셉이 다르다: 벌크스틸 = 금속 파편·먼지·바닥 균열 / 알케미스트 = 산성 방울·웅덩이 / 오버히트 = 불꽃(빙결은 얼음 결정) /
   빅 브라더 = 데이터 조각·격자 / 화룡 = 용암
 - 다음 패턴을 가리지 않도록: 이펙트는 위험 구역 경고보다 '아래'에 그리고, 크기는 장판 반경에 맞추고, 짧게 끝낸다.
시트가 없으면 조용히 건너뛴다. game_v9.build() 맨 끝에서 설치한다:
    import v9_pfx
    v9_pfx.install(G, v9_roster, v9_boss, v9_dragon, v9_dragon_fx)"""
import json
import math
import os
import threading

import pygame

HERE = os.path.dirname(os.path.abspath(__file__))
DIR = os.path.join(HERE, "fx_sheets")
G = R = B = None
_SHEETS = {}
_LOCK = threading.RLock()
MAX_INST = 90
BREATH_DIRS = 24
FADE = 0.12                                       # 마지막 프레임들을 살짝 흐리게 (뚝 끊기지 않게)

ZONE_THEME = {"boss_w": "earth", "boss_e": "acid", "boss_n": "fire", "boss_f": "digital", "boss_d": "lava"}
PRELOAD = ("muzzle_{}", "beamend_{}", "dashkick_{}", "dashtrail_{}", "field_{}_16_h", "field_{}_16_v", "field_{}_28_h", "field_{}_28_v",
           "blast_{}_s", "blast_{}_m", "blast_{}_l", "blast_{}_xl", "strip_{}_h", "strip_{}_v", "hit_{}", "nova_{}", "death_{}",
           "charge_{}", "blinkout_{}", "blinkin_{}", "summon_{}", "implode_{}")


# ---------------------------------------------------------------- 시트
def sheet(name):
    if name in _SHEETS:
        return _SHEETS[name]
    with _LOCK:
        if name not in _SHEETS:
            _SHEETS[name] = _load(name)
        return _SHEETS[name]


def _load(name):
    """시트를 프레임 목록으로 자르고, 모든 프레임에서 투명한 바깥은 잘라 메모리를 아낀다"""
    try:
        with open(os.path.join(DIR, name + ".json"), encoding="utf-8") as f:
            meta = json.load(f)
        img = pygame.image.load(os.path.join(DIR, name + ".png")).convert_alpha()
    except Exception:
        return None
    px = meta["meta"]["pixelfx"]
    rects = [pygame.Rect(fr["frame"]["x"], fr["frame"]["y"], fr["frame"]["w"], fr["frame"]["h"]) for fr in meta["frames"]]
    bb = None
    for rc in rects:
        r = img.subsurface(rc).get_bounding_rect()
        if r.w and r.h:
            bb = r if bb is None else bb.union(r)
    bb = bb or pygame.Rect(0, 0, 1, 1)
    frames = [img.subsurface(pygame.Rect(rc.x + bb.x, rc.y + bb.y, bb.w, bb.h)).copy() for rc in rects]
    piv = px["pivot"]
    return dict(frames=frames, fps=px["fps"], loop=px["loop"], piv=(piv[0] - bb.x, piv[1] - bb.y), dur=len(frames) / px["fps"])


def preload(theme):
    names = [p.format(theme) for p in PRELOAD]
    if theme == "fire":
        names += ["blast_ice_s", "blast_ice_m", "blast_ice_l", "blast_ice_xl", "strip_ice_h", "strip_ice_v",
                  "field_ice_16_h", "field_ice_16_v", "field_ice_28_h", "field_ice_28_v"]
    if theme == "lava":
        names += [f"breath_{i:02d}" for i in range(BREATH_DIRS)]
    if theme == "storm":
        names += [f"kbreath_{i:02d}" for i in range(BREATH_DIRS)] + ["gust_storm", "field_storm_28_h", "field_storm_28_v"]
    threading.Thread(target=lambda: [sheet(n) for n in names], daemon=True).start()


# ---------------------------------------------------------------- 재생
def spawn(g, name, x, y, delay=0.0, life=None, trk=None):
    """월드 좌표 (x, y) = 이펙트 중심(바닥)에 띄운다. life: 반복 이펙트를 유지할 시간, trk: 매 프레임 위치를 돌려주는 함수(None 이면 끝)"""
    if sheet(name) is None:
        return None
    lst = g.setdefault("pfx", [])
    if len(lst) >= MAX_INST:
        del lst[0]
    ins = dict(n=name, x=x, y=y, t=-delay, life=life, trk=trk)
    lst.append(ins)
    return ins


def update(g, dt):
    lst = g.get("pfx")
    if not lst:
        return
    keep = []
    for ins in lst:
        ins["t"] += dt
        s = sheet(ins["n"])
        if s is None:
            continue
        end = ins["life"] if s["loop"] else s["dur"]
        if end is not None and ins["t"] >= end:
            continue
        if ins["trk"] is not None:
            pos = ins["trk"]()
            if pos is None:
                continue
            ins["x"], ins["y"] = pos
        keep.append(ins)
    g["pfx"] = keep


def draw(surf, g, cx, cy):
    for ins in g.get("pfx", ()):
        if ins["t"] < 0:
            continue
        s = sheet(ins["n"])
        if s is None:
            continue
        n = len(s["frames"])
        i = int(ins["t"] * s["fps"])
        i = i % n if s["loop"] else min(i, n - 1)
        fr = s["frames"][i]
        end = ins["life"] if s["loop"] else s["dur"]
        if end is not None:
            k = (end - ins["t"]) / FADE
            if s["loop"]:
                k = min(k, ins["t"] / 0.1)
            if k < 1:
                fr = fr.copy()
                fr.set_alpha(max(0, int(255 * k)))
        surf.blit(fr, (int(ins["x"]) - cx - s["piv"][0], int(ins["y"]) - cy - s["piv"][1]))


# ---------------------------------------------------------------- 위험 구역 -> 이펙트
def theme_of(g):
    return ZONE_THEME.get(g.get("zid"), "fire")


def _size(r):
    return "s" if r < 21 else "m" if r < 39 else "l" if r < 62 else "xl"


def hz_events(g):
    """장판이 경고에 들어가거나 발동하는 순간을 알아채 이펙트를 띄운다"""
    zth = theme_of(g)
    for h in g["hz"]:
        th = h.get("th") or zth                                       # 필드 보스처럼 장판마다 테마를 달고 오면 그걸 쓴다
        st = h.get("_pf", 0)
        k = h["kind"]
        if h["warn"] > 0:
            if st == 0:
                h["_pf"] = 1
                if k == "beam" and h.get("dmg", True):                   # 빔 발사 전: 발사구에 에너지가 모인다
                    spawn(g, f"charge_{th}", h["x"], h["y"], life=h["warn"])
            continue
        if st >= 2:
            continue
        h["_pf"] = 2
        if not h.get("dmg", True) and not h.get("los"):
            continue                                                  # 표식용(피해 없는) 장판은 그림을 얹지 않는다
        if k == "circle":
            if h.get("nofx"):
                continue
            r = h["r"]
            if r < 12:
                continue                                              # 아주 작은 장판(불꽃 자국 등)은 기존 그림으로 충분하다
            t2 = "ice" if h.get("fx") == "freeze" else th
            spawn(g, f"blast_{t2}_{_size(r)}", h["x"], h["y"])
        elif k == "rect":
            x0, x1, y0, y1 = h["x0"], h["x1"], h["y0"], h["y1"]
            horiz = (x1 - x0) >= (y1 - y0)
            ln = (x1 - x0) if horiz else (y1 - y0)
            n = max(1, min(10, int(round(ln / 48.0))))
            t2 = "ice" if h.get("fx") == "freeze" else th
            for i in range(n):                                        # 띠를 따라 48px 조각을 이어 붙인다 (물결처럼 순서대로)
                f = (i + 0.5) / n
                px = x0 + (x1 - x0) * f if horiz else (x0 + x1) / 2
                py = (y0 + y1) / 2 if horiz else y0 + (y1 - y0) * f
                spawn(g, f"strip_{t2}_{'h' if horiz else 'v'}", px, py, delay=i * 0.03)
            _fields(g, h, t2)
        elif k == "beam":
            ex, ey = h["x"] + math.cos(h["a"]) * h["len"], h["y"] + math.sin(h["a"]) * h["len"]
            spawn(g, f"hit_{th}", h["x"], h["y"])
            spawn(g, f"hit_{th}", ex, ey, delay=0.04)
            _beam_loops(g, h, th)
        elif k == "well":
            spawn(g, f"implode_{th}", h["x"], h["y"])
        elif k == "knock":
            spawn(g, f"blast_{th}_m", h["x"], h["y"])
        elif k == "dash":
            spawn(g, f"hit_{th}", h["x"], h["y"])


def _alive(g, h):
    return h in g["hz"] and h["warn"] <= 0


def _beam_loops(g, h, th):
    """레이저가 나가는 동안: 발사구의 섬광과 끝점의 불꽃 튀김이 빔을 따라 돈다"""
    life = max(0.15, h["act"])
    spawn(g, f"muzzle_{th}", h["x"], h["y"], life=life, trk=lambda: (h["x"], h["y"]) if _alive(g, h) else None)

    def end():
        if not _alive(g, h):
            return None
        return h["x"] + math.cos(h["a"]) * h["len"], h["y"] + math.sin(h["a"]) * h["len"]
    p0 = end()
    if p0:
        spawn(g, f"beamend_{th}", p0[0], p0[1], life=life, trk=end)


def _fields(g, h, th):
    """띠 장판이 살아 있는 동안 표면 타일을 깔아 둔다 (움직이는 띠도 따라간다)"""
    x0, x1, y0, y1 = h["x0"], h["x1"], h["y0"], h["y1"]
    horiz = (x1 - x0) >= (y1 - y0)
    ln, thick = ((x1 - x0), (y1 - y0)) if horiz else ((y1 - y0), (x1 - x0))
    w = 16 if thick < 22 else 28
    cols, rows = max(1, int(round(ln / 48.0))), max(1, int(round(thick / float(w))))
    if cols * rows > 24:
        return
    h["_fld"] = True
    name = f"field_{th}_{w}_{'h' if horiz else 'v'}"
    life = max(0.2, h["act"])
    for c in range(cols):
        for r in range(rows):
            fc, fr = (c + 0.5) / cols, (r + 0.5) / rows

            def pos(fc=fc, fr=fr):
                if not _alive(g, h):
                    return None
                if horiz:
                    return h["x0"] + (h["x1"] - h["x0"]) * fc, h["y0"] + (h["y1"] - h["y0"]) * fr
                return h["x0"] + (h["x1"] - h["x0"]) * fr, h["y0"] + (h["y1"] - h["y0"]) * fc
            p0 = pos()
            spawn(g, name, p0[0], p0[1], life=life, trk=pos)


# ---------------------------------------------------------------- 대쉬
DASH_SPEED, STOP_SPEED = 150.0, 60.0


def dash_fx(g, dt):
    """보스가 빠르게 움직이면(돌진·도약) 출발 폭발 + 지나간 자리의 흙먼지 + 멈출 때 미끄럼 폭발"""
    if dt <= 0:
        return
    for o in g["en"]:
        if o["kind"] not in ("mid", "final", "dragon", "kaiju") or o.get("st") in ("ascend", "high", "dive", "sleep"):
            o.pop("_pfx_p", None)
            continue
        last = o.get("_pfx_p")
        o["_pfx_p"] = (o["x"], o["y"])
        if last is None:
            continue
        d = math.hypot(o["x"] - last[0], o["y"] - last[1])
        if d > 40:                                                   # 순간이동은 대쉬가 아니다
            continue
        sp = d / dt
        th = boss_theme(o)
        if not o.get("_dash"):
            if sp > DASH_SPEED:
                o["_dash"], o["_dash_t"] = True, 0.0
                spawn(g, f"dashkick_{th}", last[0], last[1])
        else:
            o["_dash_t"] = o.get("_dash_t", 0.0) + dt
            if o["_dash_t"] >= 0.045:
                o["_dash_t"] = 0.0
                spawn(g, f"dashtrail_{th}", o["x"] - (o["x"] - last[0]) * 2, o["y"] - (o["y"] - last[1]) * 2 + 4)
            if sp < STOP_SPEED:
                o["_dash"] = False
                spawn(g, f"dashkick_{th}", o["x"], o["y"] + 4)


# ---------------------------------------------------------------- 화룡 브레스
def breath_draw(surf, x, y, a, t, prefix="breath_"):
    """화룡의 화염 방사(또는 탈라소르의 냉기 브레스 prefix='kbreath_')를 24방향 시트 중 가장 가까운 방향으로 그린다. 시트가 없으면 False"""
    i = int(round((a % (2 * math.pi)) / (2 * math.pi) * BREATH_DIRS)) % BREATH_DIRS
    s = sheet(f"{prefix}{i:02d}")
    if s is None:
        return False
    fr = s["frames"][int(t * s["fps"]) % len(s["frames"])]
    surf.blit(fr, (int(x) - s["piv"][0], int(y) - s["piv"][1]))
    return True


# ---------------------------------------------------------------- 보스 이벤트
def boss_theme(e):
    if e.get("kind") == "final":
        return "digital"
    if e.get("kind") == "dragon":
        return "lava"
    if e.get("kind") == "kaiju":
        return "storm"
    return ("earth", "acid", "fire")[min(2, e.get("id", 0))]


def install(g_mod, roster, boss, dragon=None, dragon_fx=None):
    global G, R, B
    G, R, B = g_mod, roster, boss

    old_upd = B.update_hz

    def update_hz(g, dt):
        old_upd(g, dt)
        try:
            hz_events(g)
            update(g, dt)
        except Exception:
            G.v9_log("pfx-update")
    B.update_hz = update_hz

    old_draw = B.draw_hz

    def draw_hz(surf, g, cx, cy):
        try:
            draw(surf, g, cx, cy)                                     # 이펙트를 먼저(아래에) 그리고, 위험 구역 경고는 그 위에 그린다
        except Exception:
            G.v9_log("pfx-draw")
        old_draw(surf, g, cx, cy)
    B.draw_hz = draw_hz

    old_load = G.load_zone

    def load_zone(g, zid, tx, ty):
        old_load(g, zid, tx, ty)
        g["pfx"] = []
        if zid in ZONE_THEME:
            preload(ZONE_THEME[zid])
        elif any(o["kind"] == "kaiju" for o in g["en"]):               # 필드 보스가 있는 월드
            preload("storm")                                  # 보스방에 들어갈 때 뒤에서 미리 불러 둔다
    G.load_zone = load_zone

    old_emp, old_efp = R.enter_mid_phase, R.enter_final_phase

    def enter_mid(g, e, p):
        old_emp(g, e, p)
        try:
            spawn(g, f"nova_{boss_theme(e)}", e["x"], e["y"])
        except Exception:
            G.v9_log("pfx-phase")
    R.enter_mid_phase = enter_mid

    def enter_final(g, e, p):
        old_efp(g, e, p)
        try:
            spawn(g, "nova_digital", e["x"], e["y"])
        except Exception:
            G.v9_log("pfx-phase")
    R.enter_final_phase = enter_final

    def hit_pfx(old):
        def f(g, e, b, dmg, *a):
            r = old(g, e, b, dmg, *a)
            try:
                if dmg and g.get("t", 0) - g.get("_pfx_hit", -9) > 0.12:
                    g["_pfx_hit"] = g.get("t", 0)
                    bx, by = (b["x"], b["y"]) if isinstance(b, dict) and "x" in b else (e["x"], e["y"])
                    spawn(g, f"hit_{boss_theme(e)}", (bx + e["x"]) / 2, (by + e["y"]) / 2)
            except Exception:
                G.v9_log("pfx-hit")
            return r
        return f
    R.hit_boss = hit_pfx(R.hit_boss)
    R.final_hit = hit_pfx(R.final_hit)

    old_blink = R.blink_to

    def blink_to(g, e, x, y, col=(255, 170, 80)):
        try:
            th = boss_theme(e)
            spawn(g, f"blinkout_{th}", e["x"], e["y"])
            spawn(g, f"blinkin_{th}", x, y, delay=0.1)
        except Exception:
            G.v9_log("pfx-blink")
        return old_blink(g, e, x, y, col)
    R.blink_to = blink_to

    old_mk_ex = R.mk_ex

    def mk_ex(sub, x, y, own, hp, r, **kw):
        e = old_mk_ex(sub, x, y, own, hp, r, **kw)
        e["_pfx_new"] = True
        return e
    R.mk_ex = mk_ex

    old_upd_g = G.update
    seen = {}

    def update_g(g, inp, dt):
        old_upd_g(g, inp, dt)
        try:
            th = theme_of(g)
            dash_fx(g, dt)
            for o in g["en"]:
                if o.get("_pfx_new"):
                    o["_pfx_new"] = False
                    spawn(g, f"summon_{th}", o["x"], o["y"])
            cur = {id(o): o for o in g["en"] if o["kind"] in ("mid", "final", "dragon", "kaiju")}
            for k, o in list(seen.items()):
                if k not in cur and g.get("zid") == o["z"]:               # 보스가 사라졌다 = 처치
                    spawn(g, f"death_{o['th']}", o["x"], o["y"])
            seen.clear()
            for k, o in cur.items():
                seen[k] = dict(x=o["x"], y=o["y"], th=boss_theme(o), z=g.get("zid"))
        except Exception:
            G.v9_log("pfx-upd")
    G.update = update_g

    if dragon_fx is not None:
        dragon_fx.BREATH_DRAW = breath_draw
        old_cue = dragon_fx.on_cue

        def on_cue(fx, e, g, name, t):
            old_cue(fx, e, g, name, t)
            try:
                wa = fx.get("wa")
                if not wa:
                    return
                feet, mouth, body = wa["feet"], wa["mouth"], wa["body"]
                if name == "slam":
                    spawn(g, "blast_lava_m", (feet[0][0] + feet[2][0]) / 2, (feet[0][1] + feet[2][1]) / 2)
                elif name == "crash":
                    spawn(g, "blast_lava_l", mouth[0], mouth[1] + 6)
                elif name in ("ring", "ring2", "burst"):
                    spawn(g, "nova_lava", body[0], body[1] + 10)
                elif name in ("spit", "spawn", "ignite"):
                    spawn(g, "hit_lava", mouth[0], mouth[1])
            except Exception:
                G.v9_log("pfx-dragon")
        dragon_fx.on_cue = on_cue
