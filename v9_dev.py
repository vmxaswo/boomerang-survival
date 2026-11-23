"""v9 개발자 모드 (v9_dev.py)
  python game_v9.py --dev      로 실행했을 때만 켜진다.  게임 중 F1 = 개발자 메뉴
  무적 / 골드·재료 무한 / 데미지 x100 / 재장전 없음 / 이동속도 x2 / 만렙·강화 MAX / 보스방 순간이동 등
  개발자 모드에서는 저장을 하지 않는다 (치트 데이터가 세이브를 오염시키지 않도록)."""
import pygame

D = pygame.draw
G = C = None
ZONE_LIST = ("field", "west", "east", "temple", "north", "boss_w", "boss_e", "boss_n", "boss_f")
BOSS_LABEL = dict(boss_w="서쪽: 수문장 벌크스틸", boss_e="동쪽: 공장장 알케미스트", boss_n="북쪽: 수석 정비관 오버히트",
                  boss_f="최종: 빅 브라더 Ω")
SPEED0 = [70]


def toggle(flag, label):
    def act(g, d):
        g[flag] = not g.get(flag, False)
        G.play("ui")
    return dict(label=label, act=act, val=lambda g: ("ON", G.GREEN) if g.get(flag) else ("OFF", G.MUTED))


def act_maxout(g, d):
    if d:
        return
    g["lvl"], g["xp"] = G.LV_MAX, 0
    for k in g["lv"]:
        g["lv"][k] = G.ENH_MAX
    mods = {m[0] for m in G.MODS}
    g["own"] |= mods
    g["act"] |= mods
    G.set_mhp(g)
    g["hp"] = g["mhp"]
    G.toast(g, "Lv.30 · 강화 MAX · 능력 부메랑 전부 해금", 2.5)
    G.play("levelup")


def act_heal(g, d):
    if d:
        return
    g["hp"] = g["mhp"]
    g["inv"]["potion"] = 9
    G.toast(g, "체력 회복, 포션 9개", 2.0)
    G.play("potion")


def act_keys(g, d):
    if d:
        return
    g["keys"] = 3
    G.toast(g, "열쇠 조각 3개 (중앙 사원 개방)", 2.5)
    G.play("up")


def act_killall(g, d):
    if d:
        return
    for e in g["en"]:
        e["hp"] = 0
    G.toast(g, "현재 방의 모든 적 제거", 2.0)


def act_boss1(g, d):
    if d:
        return
    for e in g["en"]:
        if e["kind"] in ("mid", "final"):
            e["hp"] = 1
        elif e["kind"] == "pylon":
            e["hp"] = 0                                         # 빅 브라더 1페이즈: 서브 코어를 모두 제거
    G.toast(g, "보스 체력 1 (빅 브라더는 서브 코어 제거)", 2.5)


def dest(g):
    return ZONE_LIST[g.get("dtp", 0) % len(ZONE_LIST)]


def act_tp(g, d):
    n = len(ZONE_LIST)
    if d:
        g["dtp"] = (g.get("dtp", 0) + d) % n
        G.play("ui")
        return
    zid = dest(g)
    z = G.ZONES[zid]
    if z.get("arena"):                                          # 보스방은 클리어 기록을 지우고 처음부터
        g["cleared"].discard(zid)
        g["zones"].pop(zid, None)
        at = (17, 26)
    else:
        cx, cy = next((tx, ty) for k, tx, ty in z["npcs"] if k == "cart")
        at = (cx, cy + 2)
    g["seen"].add(zid)
    G.play("portal")
    G.start_travel(g, zid, *at)


ITEMS = [
    toggle("dev_god", "무적"),
    toggle("dev_inf", "골드·재료 무한"),
    toggle("dev_dmg", "데미지 x100 (원킬)"),
    toggle("dev_nocd", "재장전 없음"),
    toggle("dev_fast", "이동속도 x2"),
    toggle("dev_hud", "디버그 정보 표시"),
    dict(label="만렙 · 강화 MAX · 능력 전부 해금", act=act_maxout),
    dict(label="체력 회복 + 포션 9개", act=act_heal),
    dict(label="열쇠 조각 3개 (사원 개방)", act=act_keys),
    dict(label="현재 방의 적 전멸", act=act_killall),
    dict(label="보스 체력 1로", act=act_boss1),
    dict(label="순간이동  (A/D로 장소 선택, Enter)", act=act_tp,
         val=lambda g: (("< " + (BOSS_LABEL.get(dest(g)) or G.ZONES[dest(g)]["name"]) + " >"), G.CYAN)),
]


def dev_key(g, k):
    n = len(ITEMS)
    cur = g.get("dm", 0)
    if k in (pygame.K_ESCAPE, pygame.K_F1):
        g["ui"] = None
    elif k in (pygame.K_UP, pygame.K_w):
        g["dm"] = (cur - 1) % n
        G.play("ui")
    elif k in (pygame.K_DOWN, pygame.K_s):
        g["dm"] = (cur + 1) % n
        G.play("ui")
    elif k in (pygame.K_LEFT, pygame.K_a):
        ITEMS[cur]["act"](g, -1)
    elif k in (pygame.K_RIGHT, pygame.K_d):
        ITEMS[cur]["act"](g, 1)
    elif k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
        ITEMS[cur]["act"](g, 0)
    return g


def draw_menu(screen, font, g, u):
    SW, SH = G.W * u, G.H * u
    veil = pygame.Surface((SW, SH), pygame.SRCALPHA)
    veil.fill((8, 6, 20, 170))
    screen.blit(veil, (0, 0))
    pw, ph = int(SW * 0.68), (26 + len(ITEMS) * 12 + 16) * u
    px, py = (SW - pw) // 2, (SH - ph) // 2
    G.frame(screen, px, py, pw, ph, u)
    G.ribbon(screen, G.bigfont(u), "개발자 모드", px + pw // 2, py - 6 * u, u)
    cur = g.get("dm", 0)
    for i, it in enumerate(ITEMS):
        ry = py + (16 + i * 12) * u
        if i == cur:
            D.rect(screen, (58, 78, 128), (px + 8 * u, ry, pw - 16 * u, 11 * u))
            D.rect(screen, G.CYAN, (px + 8 * u, ry, pw - 16 * u, 11 * u), u)
        G.txt(screen, font, it["label"], px + 14 * u, ry + 2 * u, G.CREAM if i == cur else G.MUTED, u=u)
        v = it["val"](g) if it.get("val") else None
        if v:
            G.txt(screen, font, v[0], px + pw - 14 * u - font.size(v[0])[0], ry + 2 * u, v[1], u=u)
    G.txt(screen, font, "W/S 선택 · A/D 값 변경 · Enter 실행 · F1/ESC 닫기", px + pw // 2, py + ph - 12 * u, G.MUTED, True, u)


def install(g_mod, cfg, ui_mod, world_mod):
    global G, C
    G, C = g_mod, cfg
    SPEED0[0] = cfg.PLAYER["speed"]
    old_hurt, old_derived, old_upd, old_key, old_over = G.hurt, G.derived, G.update, G.on_key, G.overlay

    def hurt(g, n=1):
        if g.get("dev_god"):
            return
        return old_hurt(g, n)

    def derived(g, lv=None, lvl=None):
        d = old_derived(g, lv, lvl)
        if g.get("dev_dmg"):
            d["atk"] *= 100
        return d

    def update(g, inp, dt):
        old_upd(g, inp, dt)
        cfg.PLAYER["speed"] = SPEED0[0] * (2 if g.get("dev_fast") else 1)
        if g.get("dev_inf"):
            inv = g["inv"]
            inv["gold"] = max(inv["gold"], 999999)
            for k in ("wood", "stone", "ore", "herb", "part"):
                inv[k] = max(inv[k], 999)
            inv["potion"] = 9
        if g.get("dev_nocd"):
            g["cd"] = g["tcd"] = 0

    def on_key(g, k):
        if k == pygame.K_F1:
            if g["mode"] == "play" and not g["tr"]:
                if g["ui"] == "dev":
                    g["ui"] = None
                elif g["ui"] is None:
                    g["ui"] = "dev"
                    G.play("ui")
            return g
        if g["ui"] == "dev":
            return dev_key(g, k)
        return old_key(g, k)

    def overlay(screen, font, g, u):
        old_over(screen, font, g, u)
        SW, SH = G.W * u, G.H * u
        if g["ui"] == "dev":
            draw_menu(screen, font, g, u)
        if g.get("dev_hud"):
            tx, ty = int(g["x"]) // G.T, int(g["y"]) // G.T
            G.txt(screen, font, f"{g['zid']} ({tx},{ty})  적 {len(g['en'])}  탄 {len(g['shots'])}  hz {len(g.get('hz', []))}",
                  3 * u, 64 * u, G.CYAN, u=u)
        tag = "DEV  F1"
        G.txt(screen, font, tag, SW - 4 * u - font.size(tag)[0], SH - 10 * u, G.CORAL, u=u)

    def save(g, quiet=False):                                   # 개발자 모드에서는 저장하지 않는다
        if not quiet:
            G.toast(g, "개발자 모드: 저장하지 않음", 2.0)

    G.hurt, G.derived, G.update, G.on_key, G.overlay = hurt, derived, update, on_key, overlay
    ui_mod.save_game = save
    world_mod.V["save"] = save
    print("[v9] 개발자 모드 켜짐 - 게임 중 F1 으로 메뉴를 연다", flush=True)