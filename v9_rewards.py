"""v9 보스 보상 모듈 (v9_rewards.py) - 능력 부메랑을 대장간 제작 대신 보스 처치 보상으로 얻는다
 - 관통   = 필드 보스 탈라소르 처치 보상 (월드 남서쪽 얼어붙은 공터)
 - 쌍둥이 = 화룡 이그니스 처치 보상 (월드 남동쪽 흑요석 문 너머 용암 둥지)
 - 벽 넘기 = 새로 만들 보스의 보상이 될 예정. 그 보스가 생길 때까지는 대장간 제작으로 남겨 둔다
 대장간에는 보상 능력이 '○○ 처치 보상' 안내 줄로 보이고(살 수 없다), 인벤토리 능력 카드에도 어디서 얻는지 나온다.
 처치하는 순간 화면 가운데에 보상 카드가 뜨고 능력이 바로 켜진다. 이미 가진 능력이면 카드는 뜨지 않는다
 (탈라소르는 다시 나타나므로 두 번째부터는 일반 보상만 받는다).
game_v9.build() 에서 v9_feel 다음, v9_menu 앞에 설치한다."""
import math

import pygame

G = ST = UI = None
# 능력 -> (보스 종류, 보스 이름, 짧은 이름, 어디에 있는가)
REWARD = {"pierce": ("kaiju", "필드 보스 탈라소르", "탈라소르", "남서 폐허 초소 근처의 얼어붙은 공터"),
          "twin": ("dragon", "화룡 이그니스", "이그니스", "남동 이정표 옆 흑요석 문 너머 용암 둥지")}
CARD_T = 4.8


def now():
    return pygame.time.get_ticks() / 1000.0


def grant(g, key):
    if key in g["own"]:
        return False
    g["own"].add(key)
    g["act"].add(key)
    g["_reward"] = [key, now()]
    G.play("levelup")
    label = next(lab for k, lab, _ in G.MODS if k == key)
    G.toast(g, f"능력 부메랑 획득: {label}", 4.0)
    return True


def kill_wrap(old):
    def f(g, e):
        r = old(g, e)
        for key, (kind, *_rest) in REWARD.items():
            if e.get("kind") == kind:
                grant(g, key)
        return r
    return f


def shop_wrap(old):
    def f(g, kind, tab):
        items = old(g, kind, tab)
        if kind != "smith":
            return items
        out = []
        for it in items:
            if it["kind"] == "mod" and it["key"] in REWARD:
                key = it["key"]
                _, boss, short, where = REWARD[key]
                label = next(lab for k, lab, _ in G.MODS if k == key)
                own = key in g["own"]
                out.append(dict(label=f"{label}: {boss} 처치 보상" + ("  (획득)" if own else ""),
                                desc=G.MOD_DESC[key] + ("" if own else f"  -  {where}"),
                                cost={}, gain=0, kind="mod", key=key, done=True))
            else:
                out.append(it)
        return out
    return f


def draw_card(screen, font, g, u):
    r = g.get("_reward")
    if not r:
        return
    key, t0 = r
    t = now() - t0
    if t > CARD_T:
        g["_reward"] = None
        return
    a = min(1.0, t / 0.35) if t < CARD_T - 0.6 else max(0.0, (CARD_T - t) / 0.6)
    SW, SH = G.W * u, G.H * u
    layer = pygame.Surface((SW, SH), pygame.SRCALPHA)
    pw, ph = 230 * u, 92 * u
    px, py = (SW - pw) // 2, int(SH * 0.30)
    ST.frame(layer, px, py, pw, ph, u)
    ST.ribbon(layer, ST.bigfont(u), "능력 부메랑 획득", SW // 2, py - 8 * u, u)
    cx, cy = px + 34 * u, py + ph // 2 + 2 * u
    for i in range(10):                                              # 빛줄기
        ang = t * 0.8 + i * 0.628
        p2 = (cx + int(math.cos(ang) * 30 * u), cy + int(math.sin(ang) * 30 * u))
        pygame.draw.line(layer, (255, 226, 150, 60), (cx, cy), p2, u)
    ST.slot(layer, cx - 14 * u, cy - 14 * u, 28, u, on=True, name=key, k=3 * u)
    label = next(lab for k, lab, _ in G.MODS if k == key)
    lf = ST.logo_font(u, max(2, u - 1))
    img, pad = ST.grad_text(lf, label, (255, 246, 214), (214, 170, 86), outline=G.INK, shadow=(10, 6, 20))
    layer.blit(img, (px + 62 * u - pad, py + 12 * u - pad))
    desc = G.MOD_DESC[key]
    for j, ln in enumerate(UI.wrap(font, desc, pw - 74 * u)[:2]):
        ST.txt(layer, font, ln, px + 62 * u, py + 44 * u + j * (font.get_height() + u), G.CREAM, u=u)
    i = [m[0] for m in G.MODS].index(key)
    ST.hints(layer, font, [(G.MOD_KEYS[i], "켜기 / 끄기")], px + 62 * u, py + ph - 18 * u, u, col=G.MUTED)
    layer.set_alpha(int(255 * a))
    screen.blit(layer, (0, 0))


def hud_wrap(old):
    def f(screen, font, g, u):
        old(screen, font, g, u)
        try:
            draw_card(screen, font, g, u)
        except Exception:
            G.v9_log("rewards-card")
    return f


def install(g_mod, ui_mod, style_mod):
    global G, ST, UI
    G, ST, UI = g_mod, style_mod, ui_mod
    G.MOD_REWARD = REWARD
    G.kill = kill_wrap(G.kill)
    G.shop_items = shop_wrap(G.shop_items)
    G.hud = hud_wrap(G.hud)
