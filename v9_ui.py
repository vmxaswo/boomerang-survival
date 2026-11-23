"""v9 UI 모듈
 - HUD 전면 개편: 초상 엠블럼·레벨 배지·경험치 바, 미니맵, 현재 목표, 재료 띠, 보스 체력바(페이즈 표시)
 - 지도 화면(M): 안개가 걷히는 구역 지도 + 월드 연결도
 - 타이틀 화면 / 일시정지 메뉴 / 저장·불러오기
 - 상점: 재료별 일괄 판매"""
import json
import math
import os
import random

import pygame

D = pygame.draw
G = C = B = None
HERE = os.path.dirname(os.path.abspath(__file__))
SAVE = os.path.join(HERE, "savegame.json")
PAUSE_ITEMS = ("계속하기", "저장하기", "지도 보기", "소리 켜기/끄기", "타이틀로", "게임 종료")
NODES = dict(north=(80, 40), boss_n=(136, 40), temple=(80, 84), boss_f=(136, 84), field=(80, 128), west=(24, 128),
             boss_w=(24, 100), east=(136, 128), boss_e=(136, 100))
LINKS = (("field", "temple"), ("temple", "north"), ("field", "west"), ("field", "east"), ("west", "boss_w"),
         ("east", "boss_e"), ("north", "boss_n"), ("temple", "boss_f"))
SHORT = dict(field="초원 마을", west="서쪽 회랑", east="동쪽 정원", temple="사원 터", north="북쪽 유적",
             boss_w="관측의 전당", boss_e="가시 성소", boss_n="중력 심장", boss_f="핵의 심장부")
_CACHE = {}


# ---------------------------------------------------------------- 저장 / 불러오기
def has_save():
    return os.path.exists(SAVE)


def save_game(g, quiet=False):
    if quiet and not g.get("autosave_ok"):
        return
    data = dict(v=1, lvl=g["lvl"], xp=g["xp"], inv=g["inv"], lv=g["lv"], keys=g["keys"], own=sorted(g["own"]),
                act=sorted(g["act"]), cleared=sorted(g["cleared"]), seen=sorted(g["seen"]), topen=g["topen"],
                solved=sorted(g["solved"]))
    try:
        with open(SAVE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        G.toast(g, "자동 저장" if quiet else "게임을 저장했다", 1.6)
    except OSError:
        G.toast(g, "저장에 실패했다", 2.0)


def load_game():
    g = G.new_state()
    try:
        with open(SAVE, encoding="utf-8") as f:
            d = json.load(f)
        g["lvl"], g["xp"], g["keys"], g["topen"] = d["lvl"], d["xp"], d["keys"], d["topen"]
        g["inv"].update(d["inv"])
        g["lv"].update(d["lv"])
        g["own"], g["act"] = set(d["own"]), set(d["act"])
        g["cleared"], g["seen"], g["solved"] = set(d["cleared"]), set(d["seen"]) | {"field"}, set(d["solved"])
        G.set_mhp(g)
        g["hp"] = g["mhp"]
        G.toast(g, "저장된 게임을 불러왔다", 2.5)
    except (OSError, ValueError, KeyError):
        G.toast(g, "저장 파일을 읽지 못해 새 게임을 시작한다", 3.0)
    g["autosave_ok"] = True
    return g


# ---------------------------------------------------------------- 공통 그리기 도구
def wrap(font, s, maxw):
    lines, cur = [], ""
    for ch in s:
        if font.size(cur + ch)[0] > maxw:
            lines.append(cur)
            cur = ch.lstrip()
        else:
            cur += ch
    return lines + [cur]


def red_vig(u):
    if ("rv", u) not in _CACHE:
        sw, sh = G.W // 4, G.H // 4
        v = pygame.Surface((sw, sh), pygame.SRCALPHA)
        for y in range(sh):
            for x in range(sw):
                d = math.hypot((x / sw - 0.5) * 1.2, (y / sh - 0.5) * 1.4)
                v.set_at((x, y), (200, 20, 40, int(max(0, min(1, (d - 0.25) / 0.4)) * 200)))
        _CACHE[("rv", u)] = pygame.transform.smoothscale(v, (G.W * u, G.H * u))
    return _CACHE[("rv", u)]


def objective(g):
    if g["zid"] == "boss_f":
        e = next((o for o in g["en"] if o["kind"] == "final"), None)
        hint = {1: "핵의 공격 패턴을 읽고 부메랑을 맞혀라", 2: "방어 기둥을 모두 부숴 방어막을 벗겨라",
                3: "폭주하는 핵의 레이저와 유성을 피하며 공격하라", 4: "최후의 폭주! 모든 힘을 쏟아라"}
        return hint[e["phase"]] if e else "관리 기계의 핵을 쓰러뜨려라"
    if g["spec"].get("arena"):
        return "수호 기계를 쓰러뜨려라"
    if g["keys"] >= 3:
        return "사원의 문이 열렸다! 황혼의 사원 터로 가서 핵에 맞서라" if g["zid"] != "temple" else "열린 문으로 들어가 전송문을 타라"
    origin = dict(boss_w="west", boss_e="east", boss_n="north")
    z = next((b for b in ("boss_w", "boss_e", "boss_n") if b not in g["cleared"]), "boss_w")
    if g["zid"] == origin[z]:
        return f"스위치 퍼즐을 풀어 수호 기계의 방을 열어라 (열쇠 {g['keys']}/3)"
    return f"{G.ZONES[origin[z]]['name']}의 수호 기계를 쓰러뜨려라 (열쇠 {g['keys']}/3)"


# ---------------------------------------------------------------- 미니맵
def minimap_surface(g, vw=60, vh=44):
    base, fog, seen = G.mm_base(g)
    wt, ht = g["wt"], g["ht"]
    aw, ah = min(vw, wt), min(vh, ht)
    tx, ty = int(g["x"]) // G.T, int(g["y"]) // G.T
    wx, wy = max(0, min(wt - aw, tx - aw // 2)), max(0, min(ht - ah, ty - ah // 2))
    s = pygame.Surface((vw, vh))
    s.fill((10, 10, 24))
    ox, oy = (vw - aw) // 2, (vh - ah) // 2
    area = pygame.Rect(wx, wy, aw, ah)
    s.blit(base, (ox, oy), area)
    s.blit(fog, (ox, oy), area)

    def mark(x, y, c, r=1):
        px, py = ox + x - wx, oy + y - wy
        if 0 <= px < vw and 0 <= py < vh and (x, y) in seen:
            s.fill(c, (px - r + 1, py - r + 1, r * 2 - 1, r * 2 - 1))
    for ex in g["exits"]:
        cx_, cy_ = G.exit_center(g, ex)
        mark(min(wt - 1, int(cx_) // G.T), min(ht - 1, int(cy_) // G.T), (255, 226, 120), 2)
    for k, nx, ny in g["npcs"]:
        mark(nx, ny, (255, 226, 120))
    for p in g["portals"]:
        mark(int(p["x"]) // G.T, int(p["y"]) // G.T, (255, 110, 100) if p.get("boss") else (120, 210, 255), 2)
    for z in g["pz"]:
        for sw in z["sw"]:
            if not sw["on"]:
                mark(int(sw["x"]) // G.T, int(sw["y"]) // G.T, (255, 255, 160))
    px, py = ox + tx - wx, oy + ty - wy
    s.fill((20, 20, 40), (px - 2, py - 2, 5, 5))
    s.fill((255, 255, 255) if int(g["t"] * 4) % 2 else (255, 90, 90), (px - 1, py - 1, 3, 3))
    return s


def draw_minimap(screen, g, u, x, y):
    s = minimap_surface(g)
    screen.blit(pygame.transform.scale(s, (s.get_width() * u, s.get_height() * u)), (x, y))


# ---------------------------------------------------------------- HUD
def hud(screen, font, g, u):
    inv, SW, SH = g["inv"], G.W * u, G.H * u
    if g["hurt_t"] > 0:                                         # 피격 섬광
        v = pygame.Surface((SW, SH), pygame.SRCALPHA)
        v.fill((255, 30, 40, int(95 * g["hurt_t"] / 0.45)))
        screen.blit(v, (0, 0))
    if g["hp"] <= max(1, g["mhp"] // 4) and g["mode"] == "play":
        rv = red_vig(u)
        rv.set_alpha(int(110 + 90 * math.sin(g["t"] * 5)))
        screen.blit(rv, (0, 0))
    # ---- 좌상단: 초상 + 체력 + 경험치
    w = G.hp_bar(screen, g, 27 * u, 5 * u, u)
    for r, c in ((12, G.INK), (11, G.BRASS), (9, G.INK), (8, (70, 34, 58))):
        D.circle(screen, c, (14 * u, 14 * u), r * u)
    screen.blit(G.icon("heart", 2 * u), (5 * u, 5 * u))
    G.plate(screen, 3 * u, 25 * u, 22 * u, 9 * u, u, 235)
    G.txt(screen, font, f"Lv.{g['lvl']}", 14 * u, 25 * u, (140, 200, 255), True, u)
    G.txt(screen, font, f"{max(0, g['hp'])}/{g['mhp']}", 27 * u + w + 4 * u, 6 * u, G.CREAM, u=u)
    need, xw = G.need_xp(g["lvl"]), 74 * u
    D.rect(screen, G.INK, (27 * u, 17 * u, xw + 2 * u, 5 * u))
    D.rect(screen, (30, 40, 90), (28 * u, 18 * u, xw, 3 * u))
    fillw = xw * (g["xp"] if g["lvl"] < G.LV_MAX else need) // need
    D.rect(screen, (70, 130, 230), (28 * u, 18 * u, fillw, 3 * u))
    D.rect(screen, (150, 200, 255), (28 * u, 18 * u, fillw, u))
    G.plate(screen, 3 * u, 36 * u, 62 * u, 25 * u, u)
    screen.blit(G.icon("coin", u), (8 * u, 39 * u))
    G.txt(screen, font, str(inv["gold"]), 20 * u, 38 * u, G.GOLD, u=u)
    for i in range(3):
        screen.blit(G.icon("shard" if i < g["keys"] else "shard0", u), (8 * u + i * 11 * u, 49 * u))
    G.txt(screen, font, f"{g['keys']}/3", 44 * u, 48 * u, G.CREAM if g["keys"] else G.MUTED, u=u)
    # ---- 우상단: 미니맵 + 목표
    mx = SW - 72 * u
    G.plate(screen, mx, 4 * u, 68 * u, 58 * u, u)
    draw_minimap(screen, g, u, mx + 4 * u, 8 * u)
    G.txt(screen, font, "M 지도", mx + 34 * u, 53 * u, G.MUTED, True, u)
    lines = wrap(font, objective(g), 104 * u)
    G.plate(screen, SW - 110 * u, 64 * u, 106 * u, (9 + 8 * len(lines)) * u, u, 225)
    G.txt(screen, font, "목표", SW - 107 * u, 65 * u, G.GOLD, u=u)
    for i, ln in enumerate(lines):
        G.txt(screen, font, ln, SW - 107 * u, (73 + i * 8) * u, G.CREAM, u=u)
    # ---- 상단 중앙: 지역 이름 / 알림
    name = G.REGIONS[g["reg"]]["name"]
    pw = font.size(name)[0] + 20 * u
    G.plate(screen, (SW - pw) // 2, 3 * u, pw, 12 * u, u)
    G.txt(screen, font, name, SW // 2, 4 * u, G.GOLD, True, u)
    G.diamond(screen, (SW - pw) // 2 + 6 * u, 9 * u, 2 * u, G.BRASS)
    G.diamond(screen, (SW + pw) // 2 - 6 * u, 9 * u, 2 * u, G.BRASS)
    if g["toast"][1] > 0 and g["toast"][0] != name:
        tw = font.size(g["toast"][0])[0] + 20 * u
        G.plate(screen, (SW - tw) // 2, 17 * u, tw, 12 * u, u, 235)
        G.txt(screen, font, g["toast"][0], SW // 2, 18 * u, (255, 240, 170), True, u)
    boss_bar(screen, font, g, u)
    if g["lvup"] > 0:
        G.title_txt(screen, G.bigfont(u), f"LEVEL UP!  Lv.{g['lvl']}", SW // 2,
                    (64 - int(10 * (1 - min(1.0, g["lvup"] / 2.4)))) * u, u, (150, 210, 255))
    # ---- 하단: 재료 띠 / 핫바 / 힌트
    G.plate(screen, 3 * u, SH - 17 * u, 112 * u, 14 * u, u)
    x = 8 * u
    for k in ("wood", "stone", "ore", "herb", "part"):
        screen.blit(G.icon(k, u), (x, SH - 14 * u))
        s = str(inv[k])
        x += 11 * u + G.txt(screen, font, s, x + 11 * u, SH - 15 * u, G.CREAM if inv[k] else G.MUTED, u=u) + 5 * u
    sx0, sy = (G.W - 84) // 2 * u, (G.H - 44) * u
    for i, (nm, key) in enumerate((("potion", "Q"),) + tuple((m[0], G.MOD_KEYS[j]) for j, m in enumerate(G.MODS))):
        sx = sx0 + i * 22 * u
        mod = i > 0
        owned, on = (nm in g["own"], nm in g["act"]) if mod else (inv["potion"] > 0, False)
        G.slot(screen, sx, sy, 18, u, on=on, name=nm, dim=not owned)
        if not mod:
            s = str(inv["potion"])
            G.txt(screen, font, s, sx + 17 * u - font.size(s)[0], sy + 10 * u, G.CREAM if owned else G.MUTED, u=u)
        G.txt(screen, font, key, sx + 9 * u, sy + 19 * u, G.GOLD if on else G.MUTED, True, u)
    npc, a, ex = G.near_npc(g), g["aim"], G.near_exit(g)
    if npc and npc[0] == "bench":
        hint = "[E] 모루에서 강화하기"
    elif npc:
        hint = f"[E] {npc[1]} 이용하기"
    elif a:
        hint = f"[Space] 부메랑 발사  ·  조준: {G.target_name(a)}"
    elif ex:
        hint = f"길을 따라 이동 → {G.ZONES[ex['to']]['name']}"
    else:
        hint = "[Space] 부메랑 발사 (바라보는 방향)"
    hw = font.size(hint)[0] + 18 * u
    G.plate(screen, (SW - hw) // 2, SH - 13 * u, hw, 11 * u, u)
    G.txt(screen, font, hint, SW // 2, SH - 12 * u, G.CREAM, True, u)


def boss_bar(screen, font, g, u):
    SW, SH = G.W * u, G.H * u
    mb = next((e for e in g["en"] if e["kind"] in ("mid", "final") and e["hp"] > 0 and (g["lock"] or e["ag"])), None)
    if not mb:
        return
    fin = mb["kind"] == "final"
    bw = 190 * u if fin else 150 * u
    x0 = (SW - bw) // 2
    name = B.FINAL_NAME if fin else G.MID_NAMES[mb["id"]]
    G.plate(screen, x0 - 8 * u, 31 * u, bw + 16 * u, 24 * u, u)
    G.txt(screen, font, name + (f"   PHASE {mb['phase']}" if fin else ("  - 폭주" if mb["ph2"] else "")), SW // 2, 32 * u,
          (255, 120, 110) if (fin and mb["phase"] >= 3) or (not fin and mb["ph2"]) else G.CORAL, True, u)
    D.rect(screen, G.INK, (x0, 44 * u, bw, 8 * u))
    col = B.PHASE_COL[mb["phase"] - 1] if fin else ((255, 120, 60) if mb["ph2"] else (235, 70, 70))
    wfill = (bw - 2 * u) * mb["hp"] // mb["mhp"]
    D.rect(screen, G.lerp_c(col, (0, 0, 0), 0.45), (x0 + u, 45 * u, bw - 2 * u, 6 * u))
    D.rect(screen, col, (x0 + u, 45 * u, wfill, 6 * u))
    D.rect(screen, G.lerp_c(col, (255, 255, 255), 0.5), (x0 + u, 45 * u, wfill, 2 * u))
    marks = C.FINAL_BOSS["phases"] if fin else (0.5,)
    for m in marks:
        D.rect(screen, G.INK, (x0 + int(bw * m), 44 * u, max(1, u), 8 * u))
    if fin and B.shielded(g, mb):
        G.txt(screen, font, "방어막 가동 중 - 방어 기둥을 부숴라", SW // 2, 53 * u, (150, 240, 240), True, u)
    elif fin and mb["stun"] > 0:
        G.txt(screen, font, "핵이 멈췄다! 지금이 기회!", SW // 2, 53 * u, (255, 240, 150), True, u)
    if g["intro"] > 0:                                          # 등장 연출
        a = max(0.0, min(1.0, g["intro"] / 0.5, (2.6 - g["intro"]) / 0.4))
        band = pygame.Surface((SW, 44 * u), pygame.SRCALPHA)
        band.fill((14, 8, 24, int(215 * a)))
        screen.blit(band, (0, 92 * u))
        if a > 0.3:
            G.title_txt(screen, G.bigfont(u), B.FINAL_NAME if fin else G.MID_NAMES[mb["id"]], SW // 2, 98 * u, u, (255, 150, 130))
            G.txt(screen, font, B.FINAL_SUB if fin else G.BOSS_SUB[mb["id"]], SW // 2, 116 * u, G.CREAM, True, u)


# ---------------------------------------------------------------- 지도 화면
def draw_map(screen, font, g, u):
    SW, SH = G.W * u, G.H * u
    f2 = G.bigfont(u)
    v = pygame.Surface((SW, SH), pygame.SRCALPHA)
    v.fill((8, 6, 20, 215))
    screen.blit(v, (0, 0))
    pw, ph = int(SW * 0.94), 246 * u
    px, py = (SW - pw) // 2, (SH - ph) // 2
    G.frame(screen, px, py, pw, ph, u)
    G.ribbon(screen, f2, "지도 — " + G.ZONES[g["zid"]]["name"], px + pw // 2, py - 6 * u, u)
    base, fog, seen = G.mm_base(g)
    wt, ht = g["wt"], g["ht"]
    k = max(2, min((G.W - 200) // wt, 190 // ht))
    s2 = base.copy()
    s2.blit(fog, (0, 0))
    big = pygame.transform.scale(s2, (wt * k * u, ht * k * u))
    mx, my = px + 12 * u, py + 22 * u
    screen.blit(big, (mx, my))
    D.rect(screen, G.INK, (mx - u, my - u, wt * k * u + 2 * u, ht * k * u + 2 * u), u)

    def pt(tx, ty):
        return mx + int((tx + 0.5) * k * u), my + int((ty + 0.5) * k * u)

    def vis(tx, ty):
        return (int(tx), int(ty)) in seen
    for ex in g["exits"]:
        cx_, cy_ = G.exit_center(g, ex)
        tx, ty = min(wt - 1, int(cx_) // G.T), min(ht - 1, int(cy_) // G.T)
        if vis(tx, ty):
            G.diamond(screen, *pt(tx, ty), 3 * u, G.GOLD)
    for kd, nx, ny in g["npcs"]:
        if vis(nx, ny):
            D.rect(screen, G.GOLD, (*pt(nx, ny), 3 * u, 3 * u))
            G.txt(screen, font, {"smith": "대장간", "shop": "상점", "bench": "모루", "cart": "마차"}[kd], pt(nx, ny)[0] + 4 * u,
                  pt(nx, ny)[1] - 4 * u, G.CREAM, u=u)
    for p in g["portals"]:
        tx, ty = int(p["x"]) // G.T, int(p["y"]) // G.T
        if vis(tx, ty):
            D.circle(screen, (255, 110, 100) if p.get("boss") else G.CYAN, pt(tx, ty), 3 * u)
            G.txt(screen, font, "보스" if p.get("boss") else "전송문", pt(tx, ty)[0] + 5 * u, pt(tx, ty)[1] - 4 * u, G.CREAM, u=u)
    for z in g["pz"]:
        for sw_ in z["sw"]:
            tx, ty = int(sw_["x"]) // G.T, int(sw_["y"]) // G.T
            if vis(tx, ty):
                G.diamond(screen, *pt(tx, ty), 2 * u, (255, 255, 160) if not sw_["on"] else (120, 120, 90))
    pxp, pyp = pt(int(g["x"]) // G.T, int(g["y"]) // G.T)
    D.circle(screen, G.INK, (pxp, pyp), 4 * u)
    D.circle(screen, (255, 255, 255) if int(g["t"] * 3) % 2 else (255, 90, 90), (pxp, pyp), 3 * u)
    G.txt(screen, font, "나", pxp + 5 * u, pyp - 4 * u, (255, 255, 255), u=u)
    ly = my + ht * k * u + 4 * u
    for i, (c, t) in enumerate(((G.GOLD, "◆ 출구  ■ 시설"), (G.CYAN, "● 전송문"), ((255, 255, 160), "◆ 스위치"))):
        G.txt(screen, font, t, mx + i * 70 * u, ly, c, u=u)
    G.txt(screen, font, "M · ESC 닫기", px + pw - 12 * u - font.size("M · ESC 닫기")[0], py + 9 * u, G.MUTED, u=u)
    # ---- 월드 연결도
    gx, gy = px + pw - 168 * u, py + 22 * u
    G.txt(screen, font, "월드", gx + 4 * u, gy - 2 * u, G.GOLD, u=u)
    cz = g["zid"]
    for a, b in LINKS:
        D.line(screen, (90, 96, 130), (gx + NODES[a][0] * u, gy + NODES[a][1] * u + 8 * u), (gx + NODES[b][0] * u, gy + NODES[b][1] * u + 8 * u), u)
    for i in range(0, 112, 8):                                  # 서쪽-동쪽 전송문 연결
        D.rect(screen, G.CYAN, (gx + (24 + i) * u, gy + 142 * u + 8 * u, 4 * u, u))
    G.txt(screen, font, "전송문", gx + 66 * u, gy + 144 * u, G.CYAN, u=u)
    for z, (nx, ny) in NODES.items():
        known = z in g["seen"] or (z == "field")
        boss = z.startswith("boss")
        cleared = z in g["cleared"]
        x, y, w, h = gx + (nx - 24) * u, gy + ny * u, 48 * u, 16 * u
        D.rect(screen, G.INK, (x, y, w, h))
        D.rect(screen, G.CYAN if z == cz else (G.BRASS if known else (70, 72, 96)), (x + u, y + u, w - 2 * u, h - 2 * u), u)
        D.rect(screen, (60, 40, 50) if boss else G.NAVY2, (x + 2 * u, y + 2 * u, w - 4 * u, h - 4 * u))
        label = SHORT[z] if known else "???"
        G.txt(screen, font, label, x + w // 2, y + 4 * u, G.CREAM if known else G.MUTED, True, u)
        if boss and cleared:
            G.diamond(screen, x + w - 5 * u, y + 5 * u, 2 * u, G.GOLD)
    G.txt(screen, font, "◆ 노란 점 = 처치한 수호 기계", gx + 4 * u, gy + 160 * u, G.MUTED, u=u)


# ---------------------------------------------------------------- 일시정지 메뉴
def draw_pause(screen, font, g, u):
    SW, SH = G.W * u, G.H * u
    v = pygame.Surface((SW, SH), pygame.SRCALPHA)
    v.fill((8, 6, 20, 170))
    screen.blit(v, (0, 0))
    pw, ph = 150 * u, (24 + len(PAUSE_ITEMS) * 14 + 14) * u
    px, py = (SW - pw) // 2, (SH - ph) // 2
    G.frame(screen, px, py, pw, ph, u)
    G.ribbon(screen, G.bigfont(u), "일시정지", px + pw // 2, py - 6 * u, u)
    for i, s in enumerate(PAUSE_ITEMS):
        ry = py + (14 + i * 14) * u
        if i == g["pm"]:
            D.rect(screen, (58, 78, 128), (px + 8 * u, ry, pw - 16 * u, 13 * u))
            D.rect(screen, G.CYAN, (px + 8 * u, ry, pw - 16 * u, 13 * u), u)
        label = s + (f"  ({'꺼짐' if getattr(G, 'SND_MUTED', False) else '켜짐'})" if i == 3 else "")
        G.txt(screen, font, label, px + pw // 2, ry + 3 * u, G.CREAM if i == g["pm"] else G.MUTED, True, u)
    G.txt(screen, font, "W/S 선택 · Enter 확인 · ESC 닫기", px + pw // 2, py + ph - 12 * u, G.MUTED, True, u)


def pause_key(g, k):
    if k in (pygame.K_ESCAPE,):
        g["ui"] = None
    elif k in (pygame.K_UP, pygame.K_w):
        g["pm"] = (g["pm"] - 1) % len(PAUSE_ITEMS)
        G.play("ui")
    elif k in (pygame.K_DOWN, pygame.K_s):
        g["pm"] = (g["pm"] + 1) % len(PAUSE_ITEMS)
        G.play("ui")
    elif k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
        i = g["pm"]
        if i == 0:
            g["ui"] = None
        elif i == 1:
            g["autosave_ok"] = True
            save_game(g)
            g["ui"] = None
        elif i == 2:
            g["ui"] = "map"
        elif i == 3:
            G.toggle_mute(g)
        elif i == 4:
            g["_title"] = True
        else:
            g["_exit"] = True
    return g


# ---------------------------------------------------------------- 타이틀
def title_font(u):
    if ("tf", u) not in _CACHE:
        _CACHE[("tf", u)] = G.load_font(int(19 * u))
    return _CACHE[("tf", u)]


def draw_title(screen, font, u, t, sel, items, help_on):
    SW, SH = G.W * u, G.H * u
    for y in range(0, SH, u * 2):                               # 황혼 하늘
        c = G.lerp_c((14, 10, 40), (120, 60, 110), (y / SH) ** 1.6)
        D.rect(screen, c, (0, y, SW, u * 2))
    rng = random.Random(7)
    for i in range(90):
        x, y = rng.randint(0, SW), rng.randint(0, int(SH * 0.6))
        b = 0.5 + 0.5 * math.sin(t * 2 + i)
        D.rect(screen, G.lerp_c((60, 60, 100), (255, 255, 255), b), (x, y, u, u))
    cx, base = SW // 2, int(SH * 0.78)
    for i, (hh, w, c) in enumerate(((60, 120, (40, 30, 70)), (40, 90, (52, 40, 86)))):   # 멀리 보이는 폐허 능선
        D.polygon(screen, c, [(cx - w * u * 2, base), (cx - w * u, base - hh * u), (cx, base - (hh + 20) * u),
                              (cx + w * u, base - hh * u), (cx + w * u * 2, base)])
    D.polygon(screen, (28, 20, 50), [(cx - 70 * u, base), (cx - 70 * u, base - 46 * u), (cx, base - 84 * u),
                                     (cx + 70 * u, base - 46 * u), (cx + 70 * u, base)])
    for dx in (-52, -26, 26, 52):
        D.rect(screen, (40, 30, 66), (cx + dx * u - 4 * u, base - 46 * u, 8 * u, 46 * u))
    D.rect(screen, (255, 190, 90), (cx - 9 * u, base - 36 * u, 18 * u, 36 * u))               # 빛나는 문
    D.circle(screen, (255, 190, 90), (cx, base - 36 * u), 9 * u)
    pulse = 0.5 + 0.5 * math.sin(t * 2)
    D.circle(screen, G.lerp_c((255, 190, 90), (255, 250, 200), pulse), (cx, base - 84 * u + 24 * u), (7 + int(pulse * 2)) * u)
    for i in range(7):                                          # 떠다니는 톱니
        gx = (i * 97 + t * 8 * (1 + i % 3)) % SW
        gy = SH * 0.15 + 40 * u * math.sin(t * 0.6 + i) + i * 6 * u
        for j in range(8):
            a = t * (0.6 + i * 0.1) + j * 0.785
            D.circle(screen, (150, 154, 176), (int(gx + math.cos(a) * 9 * u), int(gy + math.sin(a) * 9 * u)), u * 2)
        D.circle(screen, (110, 114, 140), (int(gx), int(gy)), 7 * u)
        D.circle(screen, (60, 64, 96), (int(gx), int(gy)), 3 * u)
    D.rect(screen, (22, 16, 40), (0, base, SW, SH - base))
    tf = title_font(u)
    G.title_txt(screen, tf, "PIXEL RUINS", SW // 2, 28 * u, u, G.BRASS_L)
    G.txt(screen, font, "잊혀진 기계 문명의 수수께끼", SW // 2, 56 * u, G.CREAM, True, u)
    D.rect(screen, G.BRASS_D, (SW // 2 - 60 * u, 66 * u, 120 * u, u))
    G.diamond(screen, SW // 2, 66 * u, 3 * u, G.BRASS)
    for i, (label, on) in enumerate(items):
        y = 150 * u + i * 15 * u
        w = 100 * u
        if i == sel:
            D.rect(screen, (58, 78, 128), (SW // 2 - w // 2, y, w, 13 * u))
            D.rect(screen, G.CYAN, (SW // 2 - w // 2, y, w, 13 * u), u)
        G.txt(screen, font, label, SW // 2, y + 3 * u, G.CREAM if on and i == sel else G.MUTED if not on else G.CREAM, True, u)
    G.txt(screen, font, "W/S 선택 · Enter 확인", SW // 2, SH - 14 * u, G.MUTED, True, u)
    if help_on:
        pw, ph = 230 * u, 150 * u
        px, py = (SW - pw) // 2, (SH - ph) // 2
        G.frame(screen, px, py, pw, ph, u)
        G.ribbon(screen, G.bigfont(u), "조작법", SW // 2, py - 6 * u, u)
        rows = ("이동  WASD / 방향키 (8방향)", "부메랑  Space (자동조준: 가까운 적 우선)", "상호작용  E (상점·대장간·모루·마차)",
                "인벤토리  I    포션  Q", "능력 부메랑  Z / X / C", "지도  M    소리  N    일시정지  ESC",
                "모루 강화: 장비 선택 → Space로 타이밍 3번", "수호 기계 3기를 쓰러뜨려 열쇠 조각을 모아라", "그리고 중앙 사원의 핵을 멈춰라")
        for i, s in enumerate(rows):
            G.txt(screen, font, s, px + 14 * u, py + (16 + i * 13) * u, G.CREAM if i < 6 else G.GOLD, u=u)


# ---------------------------------------------------------------- 상점: 재료별 일괄 판매
def install(g_mod, cfg, boss_mod, world_mod):
    global G, C, B
    G, C, B = g_mod, cfg, boss_mod
    world_mod.V["save"] = save_game
    old_items, old_buy, old_key, old_over = G.shop_items, G.buy, G.on_key, G.overlay

    def shop_items(g, kind, tab):
        if not (kind == "shop" and tab == 1):
            return old_items(g, kind, tab)
        inv, out, tot = g["inv"], [], 0
        for res, price in G.SELL:
            n = inv[res]
            tot += n * price
            out.append(dict(label=f"{G.NAMES[res]} 1개 판매 (보유 {n})", desc=f"개당 {price}G", cost={}, gain=price,
                            kind="sell1", key=res, done=n <= 0))
            out.append(dict(label=f"{G.NAMES[res]} 전부 판매 ({n}개)", desc=f"{n}개 x {price}G = {n * price}G", cost={},
                            gain=n * price, kind="sellres", key=res, done=n <= 0))
        out.append(dict(label="재료 전부 판매", desc="나무·돌·약초·철광석을 모두 판다", cost={}, gain=tot, kind="sellall",
                        key=None, done=tot <= 0))
        return out

    def buy(g, it):
        if it["kind"] == "sellres" and not it["done"]:
            res, n = it["key"], g["inv"][it["key"]]
            g["inv"][res] = 0
            g["inv"]["gold"] += it["gain"]
            g["smsg"] = (f"{G.NAMES[res]} {n}개를 팔아 {it['gain']}G를 받았다", True)
            G.play("buy")
            return
        return old_buy(g, it)

    def on_key(g, k):
        play = g["mode"] == "play" and not g["tr"]
        if k == pygame.K_n:
            G.toggle_mute(g)
            return g
        if k == pygame.K_m:                                     # M = 지도 (소리는 N)
            if play and g["ui"] in (None, "map"):
                g["ui"] = "map" if g["ui"] is None else None
                G.play("ui")
            return g
        if play and g["ui"] == "pause":
            return pause_key(g, k)
        if play and k == pygame.K_ESCAPE and g["ui"] is None:
            g.update(ui="pause", pm=0)
            return g
        return old_key(g, k)

    def overlay(screen, font, g, u):
        if g["ui"] == "map":
            draw_map(screen, font, g, u)
        elif g["ui"] == "pause":
            draw_pause(screen, font, g, u)
        else:
            old_over(screen, font, g, u)
    G.shop_items, G.buy, G.on_key, G.overlay, G.hud = shop_items, buy, on_key, overlay, hud
    G.save_game, G.load_game, G.has_save, G.draw_title = save_game, load_game, has_save, draw_title


# ---------------------------------------------------------------- 메인 루프 (타이틀 -> 게임)
def main():
    pygame.init()
    G.init_sound()
    try:
        dw, dh = pygame.display.get_desktop_sizes()[0]
    except Exception:
        dw, dh = 1280, 720
    u = max(2, min(dw * 9 // 10 // G.W, dh * 9 // 10 // G.H))
    screen = pygame.display.set_mode((G.W * u, G.H * u))
    pygame.display.set_caption("Pixel Ruins v9")
    surf, font, clock = pygame.Surface((G.W, G.H)), G.load_font(6 * u), pygame.time.Clock()
    state, sel, g, help_on, t = "title", 0, None, False, 0.0
    G.set_music(5)
    while True:
        dt = min(clock.tick(60) / 1000, 0.05)
        t += dt
        items = [("새 게임", True), ("이어하기", has_save()), ("조작법", True), ("종료", True)]
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                return
            if ev.type != pygame.KEYDOWN:
                continue
            k = ev.key
            if state == "title":
                if help_on:
                    help_on = False
                elif k in (pygame.K_UP, pygame.K_w):
                    sel = (sel - 1) % 4
                    G.play("ui")
                elif k in (pygame.K_DOWN, pygame.K_s):
                    sel = (sel + 1) % 4
                    G.play("ui")
                elif k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    if sel == 0 or (sel == 1 and items[1][1]):
                        g = G.new_state() if sel == 0 else load_game()
                        g["autosave_ok"] = True
                        state = "game"
                        G.set_music(g["reg"])
                        G.play("up")
                    elif sel == 2:
                        help_on = True
                    elif sel == 3:
                        pygame.quit()
                        return
                elif k == pygame.K_ESCAPE:
                    pygame.quit()
                    return
            else:
                g = G.on_key(g, k)
                if g is None:
                    pygame.quit()
                    return
        if state == "game":
            if g.get("_exit"):
                pygame.quit()
                return
            if g.get("_title"):
                state, g = "title", None
                G.set_music(5)
                continue
            if g["mode"] == "play" and g["ui"] is None:
                G.update(g, G.read_input(pygame.key.get_pressed()), dt)
            elif g["mode"] == "play" and g["ui"] == "bench":
                G.update_forge(g, dt)
            G.render(screen, surf, font, g, u)
        else:
            draw_title(screen, font, u, t, sel, items, help_on)
        pygame.display.flip()