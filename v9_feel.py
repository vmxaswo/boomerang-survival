"""v9 손맛·연출 모듈 (v9_feel.py)
 1. 그리기 순서(깊이): 캐릭터·적이 나무·석상·탑·건물 '뒤'에 있으면 그 물체가 캐릭터를 가린다 (조명보다 먼저 처리)
 2. 히트스톱: 보스를 맞히면 아주 잠깐(0.05초) 멈춰 타격감을 준다. 일반 적 처치는 더 짧게
 3. 봉인 해제 연출: 퍼즐을 풀어 보스 건물 문이 열리면 카메라가 문으로 이동했다가 돌아온다 (그동안 무적)
 4. 지역 이름 카드: 새 지역에 처음 들어가면 화면 위쪽에 큰 지역 이름이 떠올랐다 사라진다
 5. 첫 모험 안내(튜토리얼): 이동 -> 부메랑 -> 워프 -> 지도 -> 전투 -> 스위치 퍼즐 -> 모루 강화를 차례로 알려 준다
 6. 엔딩: 이야기 + 크레딧이 올라가고, Enter 로 '계속 탐험하기'(사원 앞으로 돌아간다)
 7. 발소리: 걸을 때 일정 간격으로 발소리 (v9_audio 의 'step')
게임 판정은 바꾸지 않는다. game_v9.build() 에서 v9_style 다음에 설치한다."""
import math

import pygame

D = pygame.draw
SC = pygame.SRCALPHA
G = C = UI = W = O = S = ST = None
BOSSK = ("mid", "final", "dragon", "kaiju", "pylon", "ex")
PAN_DUR = 2.6


def now():
    return pygame.time.get_ticks() / 1000.0


# ================================================================= 1. 깊이
def _occluders(g, cx, cy):
    T, out = G.T, []
    view = pygame.Rect(-48, -64, G.W + 96, G.H + 128)
    for d in g["deco"]:
        if len(d) < 4 or d[0] in ("flower", "husk", "vent", "warp") or d[0] not in W.SPRITES:
            continue
        x, y = int(d[1]) - cx, int(d[2]) - cy
        if not view.collidepoint(x, y):
            continue
        spr = W.sprite(d[0])
        w, h = spr.get_size()
        out.append((pygame.Rect(x - w // 2, y + 8 - h, w, h), int(d[2]) + 8, ("img", spr)))
    for n in g["nodes"]:
        if not n["alive"] or n["kind"] == "herb":
            continue
        px, py = n["tx"] * T - cx, n["ty"] * T - cy
        if view.collidepoint(px, py):
            out.append((pygame.Rect(px - 2, py - 10, 20, 26), n["ty"] * T + 15, ("node", n, px, py)))
    if S is not None and g.get("meta") and g.get("zid") == O.WID:
        for key, (x0, y0, x1, y1, side, mid) in g["meta"]["lairs"].items():
            r = pygame.Rect(x0 * T - cx, (y0 - S.REAR) * T - cy, S.BW, S.BH)
            if r.colliderect(view):
                out.append((r, (y1 + 1) * T, ("img", S.building(mid))))
    return out


def depth_pass(surf, g, cx, cy):
    ents = []
    if g["mode"] == "play" and not (g["iv"] > 0 and int(g["t"] * 20) % 2):
        ents.append((pygame.Rect(int(g["x"]) - 7 - cx, int(g["y"]) - 13 - cy, 14, 16), g["y"] + 2))
    for e in g["en"]:
        if e["kind"] not in BOSSK and e.get("hp", 1) > 0:
            ents.append((pygame.Rect(int(e["x"]) - 9 - cx, int(e["y"]) - 16 - cy, 18, 20), e["y"] + 3))
    if not ents:
        return
    occ = _occluders(g, cx, cy)
    for er, eb in ents:
        for r, ob, what in occ:
            if ob <= eb or not r.colliderect(er):
                continue
            surf.set_clip(er)
            if what[0] == "img":
                surf.blit(what[1], r.topleft)
            else:
                G.draw_node(surf, what[1], what[2], what[3], G.tile_reg(g, what[1]["tx"], what[1]["ty"]))
            surf.set_clip(None)


def lighting_wrap(old):
    def f(surf, g, cx, cy):
        try:
            depth_pass(surf, g, cx, cy)
        except Exception:
            G.v9_log("feel-depth")
        return old(surf, g, cx, cy)
    return f


# ================================================================= 2·3·4·5·7. 매 프레임 갱신
def door_target(g, pid):
    meta = g.get("meta")
    if not meta or pid not in meta["lairs"]:
        return None
    x0, y0, x1, y1, _, _ = meta["lairs"][pid]
    return ((x0 + x1) // 2 * G.T + 8, (y1 - 2) * G.T)


TUT = (("move", [("WASD", "이동하기")], ""),
       ("throw", [("Space", "부메랑 던지기")], "가까운 적을 자동으로 조준한다"),
       ("warp", [("E", "워프포인트 켜기")], "켜 둔 워프포인트는 지도에서 언제든 순간이동"),
       ("map", [("M", "지도 열기")], "목표와 수호 기계의 방 위치를 확인하자"),
       ("fight", [], "적을 쓰러뜨리면 골드와 재료를 얻는다"),
       ("switch", [], "수호 기계의 방 앞 스위치를 부메랑으로 맞혀 문을 열자"),
       ("forge", [("E", "모루 작업대")], "마을 모루에서 재료로 부메랑을 강화할 수 있다"))
TUT_SKIP = dict(warp=45, map=35, fight=90, switch=150, forge=80)


def tut_done(g, key):
    if key == "move":
        sx, sy = g.get("_tut_start") or (g["x"], g["y"])
        return math.hypot(g["x"] - sx, g["y"] - sy) > 48
    if key == "throw":
        return bool(g["booms"])
    if key == "warp":
        return len(g.get("wact") or ()) > 1
    if key == "map":
        return g.get("ui") == "map"
    if key == "fight":
        return g.get("_kills", 0) > 0
    if key == "switch":
        return any(s["on"] for q in g["pz"] for s in q["sw"]) or bool(g["cleared"])
    if key == "forge":
        return sum(g["lv"].values()) > 0
    return True


def tut_tick(g, dt):
    i = g.get("tut", 99)
    if i >= len(TUT) or g.get("zid") != O.WID:
        return
    g.setdefault("_tut_start", (g["x"], g["y"]))
    g["_tt"] = g.get("_tt", 0.0) + dt
    if g.get("_tok", 0) > 0:                                      # '완료!' 표시 뒤 다음 단계로
        g["_tok"] -= dt
        if g["_tok"] <= 0:
            g["tut"], g["_tt"] = i + 1, 0.0
        return
    key = TUT[i][0]
    if tut_done(g, key) or g["_tt"] > TUT_SKIP.get(key, 1e9):
        g["_tok"] = 1.1
        G.play("tut")


def update_wrap(old):
    def f(g, inp, dt):
        if g.get("_hs", 0) > 0:                                   # 히트스톱
            g["_hs"] -= dt
            return
        world = g.get("zid") == O.WID
        before = {q["pid"]: q["done"] for q in g["pz"]} if world else {}
        pan = g.get("_pan")
        if pan:
            pan[0] += dt
            g["iv"] = max(g.get("iv", 0), 0.25)
            inp = (0, 0, False)
            if pan[0] > PAN_DUR:
                g["_pan"] = None
        old(g, inp, dt)
        if g["mode"] != "play":
            return
        if world:
            for q in g["pz"]:                                     # 봉인이 풀린 순간: 카메라를 문으로
                if q["done"] and not before.get(q["pid"], True):
                    tgt = door_target(g, q["pid"])
                    if tgt:
                        g["_pan"] = [0.0, tgt]
                        G.play("unlock")
                        G.toast(g, "수호 기계의 방 봉인이 풀렸다!", 3.0)
            reg = g["reg"]
            if reg != g.get("_lreg"):
                g["_lreg"] = reg
                seen = g.setdefault("_seenreg", set())
                if reg not in seen:
                    seen.add(reg)
                    g["_card"] = [G.REGIONS[reg]["name"], 0.0]
        if g.get("_card"):
            g["_card"][1] += dt
            if g["_card"][1] > 3.4:
                g["_card"] = None
        try:
            tut_tick(g, dt)
        except Exception:
            G.v9_log("feel-tut")
        if g["moving"] and g["ui"] is None:                       # 발소리
            g["_step"] = g.get("_step", 0.0) - dt
            if g["_step"] <= 0:
                g["_step"] = 0.31
                G.play("step")
    return f


def camera_wrap(old):
    def f(g):
        base = old(g)
        p = g.get("_pan")
        if not p:
            return base
        T, t = G.T, p[0]
        tx, ty = p[1]
        tc = (min(max(int(tx) - G.W // 2, 0), g["wt"] * T - G.W), min(max(int(ty) - G.H // 2, 0), g["ht"] * T - G.H))
        k = min(1.0, t / 0.6) if t < 1.9 else max(0.0, 1 - (t - 1.9) / (PAN_DUR - 1.9))
        k = k * k * (3 - 2 * k)
        return (int(base[0] + (tc[0] - base[0]) * k), int(base[1] + (tc[1] - base[1]) * k))
    return f


def hit_wrap(old):
    def f(g, e, b, dmg):
        hp0 = e.get("hp", 0)
        r = old(g, e, b, dmg)
        if e["kind"] in BOSSK and e.get("hp", hp0) < hp0:
            g["_hs"] = max(g.get("_hs", 0), 0.05)
        return r
    return f


def kill_wrap(old):
    def f(g, e):
        if e["kind"] not in ("illu", "seed"):
            g["_kills"] = g.get("_kills", 0) + 1
            if e["kind"] not in BOSSK:
                g["_hs"] = max(g.get("_hs", 0), 0.03)
        return old(g, e)
    return f


def new_state_wrap(old):
    def f(*a, **k):
        g = old(*a, **k)
        g["tut"] = 0                                              # 새 게임은 안내를 처음부터
        return g
    return f


# ================================================================= 화면 위 카드 (지역 이름 · 안내)
def draw_card(screen, g, u):
    c = g.get("_card")
    if not c or g["ui"] is not None:
        return
    name, t = c
    a = min(1.0, t / 0.45) if t < 2.6 else max(0.0, 1 - (t - 2.6) / 0.8)
    if a <= 0:
        return
    lf = ST.logo_font(u, max(2, u - 1))
    img, pad = ST.grad_text(lf, name, (255, 246, 214), (214, 170, 86), outline=G.INK, shadow=(10, 6, 20))
    SW = G.W * u
    w, h = img.get_size()
    layer = pygame.Surface((max(w, 220 * u), h + 22 * u), SC)
    lw = layer.get_width()
    layer.blit(img, ((lw - w) // 2, 0))
    ly = h - pad + 6 * u
    span = int(min(lw // 2 - 10 * u, (w // 2 + 20 * u) * min(1.0, t / 0.9)))
    D.rect(layer, G.BRASS_D, (lw // 2 - span, ly, span * 2, u))
    G.diamond(layer, lw // 2, ly, 3 * u, G.BRASS)
    layer.set_alpha(int(255 * a))
    screen.blit(layer, ((SW - lw) // 2, int(54 * u - (1 - a) * 6 * u)))


def draw_tut(screen, font, g, u):
    i = g.get("tut", 99)
    if i >= len(TUT) or g.get("zid") != O.WID or g["ui"] is not None or g["mode"] != "play" or g.get("_card"):
        return
    key, pairs, text = TUT[i]
    ok = g.get("_tok", 0) > 0
    SW = G.W * u
    fh = font.get_height()
    body = "완료!" if ok else text
    w = (ST.hints_w(font, pairs, u) if pairs else 0) + font.size(body)[0] + 50 * u
    h = fh + 8 * u
    x, y = (SW - w) // 2, 33 * u
    ST.plate(screen, x, y, w, h, u, 235)
    ST.txt(screen, font, "TIP", x + 8 * u, y + 4 * u + u, G.GOLD, u=u)
    xx = x + 26 * u
    if pairs and not ok:
        xx += ST.hints(screen, font, pairs, xx, y + 4 * u + u, u, col=G.CREAM) + 8 * u
    ST.txt(screen, font, body, xx, y + 4 * u + u, G.GREEN if ok else G.CREAM, u=u)
    dots = len(TUT)
    for j in range(dots):                                         # 진행 점
        D.rect(screen, G.GOLD if j < i or (j == i and ok) else (70, 66, 86),
               (SW // 2 - dots * 3 * u + j * 6 * u, y + h + 2 * u, 4 * u, 2 * u))


def hud_wrap(old):
    def f(screen, font, g, u):
        old(screen, font, g, u)
        try:
            draw_card(screen, g, u)
            draw_tut(screen, font, g, u)
        except Exception:
            G.v9_log("feel-hud")
    return f


# ================================================================= 6. 엔딩 크레딧 + 계속 탐험하기
CREDITS = ("부메랑으로 살아남기", "PIXEL RUINS", "",
           "벽화의 마지막 기록이 떠올랐다.", "문명을 무너뜨린 것은 외부의 적이 아니라", "스스로 만든 기계의 폭주였다.", "",
           "[ 쓰러뜨린 수호 기계 ]", "수문장 벌크스틸", "공장장 알케미스트", "수석 정비관 오버히트", "도시의 심장, 빅 브라더 Ω", "",
           "[ 사용한 자료 ]", "글꼴  Galmuri - Lee Minseo (SIL OFL 1.1)", "엔진  pygame-ce", "",
           "플레이해 주셔서 감사합니다")


def fmt_time(sec):
    sec = int(sec or 0)
    return f"{sec // 3600}:{sec // 60 % 60:02d}:{sec % 60:02d}"


def draw_ending(screen, font, g, u):
    SW, SH = G.W * u, G.H * u
    t0 = g.setdefault("_end_t0", now())
    t = now() - t0
    ST.veil(screen, (6, 4, 16), int(min(235, 60 + t * 60)))
    ST.vignette_edges(screen, (0, 0, 0), 180)
    lh = font.get_height() + 4 * u
    big = ST.bigfont(u)
    y0 = SH - int(t * 22 * u)                                     # 아래에서 위로 올라가는 크레딧
    for i, s in enumerate(CREDITS):
        y = y0 + i * lh + (24 * u if i > 1 else 0)
        if y < -lh or y > SH:
            continue
        if i == 0:
            img, pad = ST.grad_text(ST.logo_font(u, max(2, u)), s, (255, 246, 190), (210, 140, 50), outline=G.INK)
            screen.blit(img, (SW // 2 - img.get_width() // 2, y - pad - 10 * u))
        elif s.startswith("["):
            ST.txt(screen, big, s.strip("[] "), SW // 2, y, G.GOLD, True, u)
        else:
            ST.txt(screen, font, s, SW // 2, y, G.MUTED if i == 1 else G.CREAM, True, u)
    end_y = y0 + len(CREDITS) * lh + 24 * u
    if end_y < SH * 0.5 or t > 3.0:
        bh = 30 * u
        ST.plate(screen, 0, SH - bh, SW, bh, u, 230)
        stats = f"Lv.{g['lvl']}   ·   플레이 시간 {fmt_time(g.get('play_t'))}   ·   골드 {g['inv']['gold']}"
        ST.txt(screen, font, stats, SW // 2, SH - bh + 4 * u, G.MUTED, True, u)
        ST.hints(screen, font, [("Enter", "계속 탐험하기"), ("R", "새 게임"), ("ESC", "게임 종료")], SW // 2,
                 SH - bh + 4 * u + font.get_height() + 2 * u, u, "center")


def end_wrap(old):
    def f(screen, font, g, u):
        if g["mode"] == "ending":
            return draw_ending(screen, font, g, u)
        return old(screen, font, g, u)
    return f


def continue_explore(g):
    """엔딩 뒤 계속 탐험하기: 중앙 사원 앞으로 돌아간다 (남은 콘텐츠: 화룡 이그니스, 필드 보스 탈라소르)"""
    tx0, ty0, tx1, ty1 = G.ZONES["temple"]["temple"]
    g["mode"] = "play"
    g["cleared"].add("boss_f")
    g["ending_seen"] = True
    g.pop("_end_t0", None)
    G.start_travel(g, O.WID, (tx0 + tx1) // 2, ty1 + 3)
    G.toast(g, "모험은 계속된다 - 화룡과 괴수가 아직 남아 있다", 4.0)


def key_wrap(old):
    def f(g, k):
        if g is not None and g.get("mode") == "ending" and k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            if now() - g.get("_end_t0", now()) > 1.0:
                continue_explore(g)
                G.play("up")
            return g
        return old(g, k)
    return f


# ================================================================= 설치
def install(g_mod, cfg, ui_mod, world_mod, open_mod, sites_mod, style_mod):
    global G, C, UI, W, O, S, ST
    G, C, UI, W, O, S, ST = g_mod, cfg, ui_mod, world_mod, open_mod, sites_mod, style_mod
    W.lighting = lighting_wrap(W.lighting)
    G.update = update_wrap(G.update)
    G.camera = camera_wrap(G.camera)
    G.hit_foe = hit_wrap(G.hit_foe)
    G.kill = kill_wrap(G.kill)
    G.new_state = new_state_wrap(G.new_state)
    G.hud = hud_wrap(G.hud)
    G.draw_end = end_wrap(G.draw_end)
    G.on_key = key_wrap(G.on_key)
