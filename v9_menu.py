"""v9 메뉴 모듈 (v9_menu.py) - 메인 루프 · 저장 슬롯 · 설정 · 플레이 시간 · 게임패드
 - 시작화면: 이어하기 / 새 게임 / 설정 / 조작법 / 종료. 이어하기·새 게임은 저장 슬롯 3개 중에서 고른다
   (슬롯마다 레벨 · 위치 · 열쇠 · 플레이 시간 · 저장 날짜 표시, 쓰던 슬롯에 새 게임을 시작하면 한 번 더 확인)
 - 예전 savegame.json 은 처음 실행할 때 슬롯 1(savegame_1.json)로 옮긴다
 - 설정 (settings.json 에 저장): 전체화면 · 배경음 음량 · 효과음 음량 · 화면 흔들림 · 난이도(쉬움/보통/어려움)
   시작화면과 일시정지 메뉴(설정) 양쪽에서 연다. F11 = 전체화면 켜기/끄기
 - 플레이 시간을 세어 저장하고, 첫 모험 안내 진행도(tut)도 저장한다
 - 게임패드(XInput 배치): 스틱/십자키 이동 · A 부메랑(메뉴에서는 확인) · B 취소 · X 상호작용(E) · Y 가방(I) ·
   LB 포션(Q) · RB 능력 부메랑 바꾸기 · START 일시정지 · BACK 지도
game_v9.build() 맨 끝에서 설치한다 (v9_ui.main 을 이 모듈의 main 으로 바꾼다)."""
import json
import os
import time

import pygame

G = C = UI = ST = AU = FL = None
HERE = os.path.dirname(os.path.abspath(__file__))
SETTINGS = os.path.join(HERE, "settings.json")
SLOTS = 3
SET = dict(fullscreen=False, music=8, sfx=8, shake=True, difficulty=1)
DIFF = {0: dict(bullet_speed=0.85, telegraph=1.3, cooldown=1.25),
        1: dict(bullet_speed=1.0, telegraph=1.0, cooldown=1.0),
        2: dict(bullet_speed=1.15, telegraph=0.85, cooldown=0.85)}
DIFF_NAME = ("쉬움", "보통", "어려움")
ROWS = ("fullscreen", "music", "sfx", "shake", "difficulty", "back")
ROW_NAME = dict(fullscreen="화면", music="배경음 음량", sfx="효과음 음량", shake="화면 흔들림", difficulty="난이도", back="돌아가기")
ROW_DESC = dict(fullscreen="Enter 또는 F11 로 전체화면과 창 모드를 바꾼다", music="A/D 로 조절 (N 키는 소리 전체 끄기)",
                sfx="A/D 로 조절", shake="큰 공격·폭발 때 화면이 흔들리는 연출", back="",
                difficulty="쉬움: 예고가 길고 탄이 느리다 / 어려움: 예고가 짧고 탄이 빠르다")
PAUSE_ITEMS = ("계속하기", "저장하기", "지도 보기", "설정", "타이틀로", "게임 종료")
_FS = dict(on=False)


# ================================================================= 설정
def load_settings():
    try:
        with open(SETTINGS, encoding="utf-8") as f:
            d = json.load(f)
        for k in SET:
            if k in d and isinstance(d[k], type(SET[k])):
                SET[k] = d[k]
    except (OSError, ValueError):
        pass


def save_settings():
    try:
        with open(SETTINGS, "w", encoding="utf-8") as f:
            json.dump(SET, f, ensure_ascii=False, indent=1)
    except OSError:
        pass


def apply_settings():
    SET["music"] = max(0, min(10, SET["music"]))
    SET["sfx"] = max(0, min(10, SET["sfx"]))
    SET["difficulty"] = max(0, min(2, SET["difficulty"]))
    C.DIFFICULTY.update(DIFF[SET["difficulty"]])
    if AU:
        AU.set_volumes(SET["music"] / 10, SET["sfx"] / 10)
    C.FX["screen_shake"] = SET["shake"]


def set_fullscreen(on):
    if on == _FS["on"]:
        return
    try:
        pygame.display.toggle_fullscreen()
        _FS["on"] = on
    except pygame.error:
        pass


def settings_key(k):
    """설정 화면 키. 닫아야 하면 True"""
    i = SET.get("_sel", 0)
    row = ROWS[i]
    if k in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
        G.play("back")
        save_settings()
        return True
    if k in (pygame.K_UP, pygame.K_w):
        SET["_sel"] = (i - 1) % len(ROWS)
        G.play("ui")
    elif k in (pygame.K_DOWN, pygame.K_s):
        SET["_sel"] = (i + 1) % len(ROWS)
        G.play("ui")
    elif k in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d, pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
        d = -1 if k in (pygame.K_LEFT, pygame.K_a) else 1
        if row == "back":
            if k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                G.play("back")
                save_settings()
                return True
            return False
        if row == "fullscreen":
            SET["fullscreen"] = not SET["fullscreen"]
            set_fullscreen(SET["fullscreen"])
        elif row in ("music", "sfx"):
            SET[row] = max(0, min(10, SET[row] + (d if k not in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE) else 0)))
        elif row == "shake":
            SET["shake"] = not SET["shake"]
        elif row == "difficulty":
            SET["difficulty"] = (SET["difficulty"] + d) % 3
        apply_settings()
        G.play("ok")
    return False


def draw_settings(screen, font, u):
    SW, SH = G.W * u, G.H * u
    ST.veil(screen, (6, 4, 14), 160)
    pw, ph = 280 * u, 150 * u
    px, py = (SW - pw) // 2, (SH - ph) // 2 + 4 * u
    ST.frame(screen, px, py, pw, ph, u)
    ST.ribbon(screen, ST.bigfont(u), "설정", SW // 2, py - 8 * u, u)
    sel = SET.get("_sel", 0)
    rh = 17 * u
    fh = font.get_height()
    for i, row in enumerate(ROWS):
        y = py + 16 * u + i * rh
        cur = i == sel
        if cur:
            ST.sel_bar(screen, px + 12 * u, y, pw - 24 * u, rh - 3 * u, u)
        ty = y + (rh - 3 * u - fh) // 2 + u
        ST.txt(screen, font, ROW_NAME[row], px + 22 * u, ty, G.GOLD if cur else G.CREAM, u=u)
        vx = px + 130 * u
        if row in ("music", "sfx"):
            for j in range(10):
                on = j < SET[row]
                pygame.draw.rect(screen, G.INK, (vx + j * 9 * u, ty + u, 7 * u, fh - 3 * u))
                pygame.draw.rect(screen, G.GOLD if on else (60, 58, 76), (vx + j * 9 * u + u, ty + 2 * u, 5 * u, fh - 5 * u))
            ST.txt(screen, font, str(SET[row]), vx + 94 * u, ty, G.CREAM, u=u)
        elif row != "back":
            val = {"fullscreen": "전체화면" if SET["fullscreen"] else "창 모드", "shake": "켜짐" if SET["shake"] else "꺼짐",
                   "difficulty": DIFF_NAME[SET["difficulty"]]}[row]
            ST.txt(screen, font, "<  " + val + "  >" if cur else val, vx, ty, G.CREAM if cur else G.MUTED, u=u)
    desc = ROW_DESC[ROWS[sel]]
    ST.txt(screen, font, desc, px + 16 * u, py + ph - 30 * u, G.MUTED, u=u)
    ST.hints(screen, font, [("W/S", "선택"), ("A/D", "바꾸기"), ("ESC", "닫기")], px + pw - 14 * u, py + ph - 16 * u, u, "right")


# ================================================================= 저장 슬롯
def slot_path(i):
    return os.path.join(HERE, f"savegame_{i + 1}.json")


def migrate_old_save():
    old = os.path.join(HERE, "savegame.json")
    if os.path.exists(old) and not os.path.exists(slot_path(0)):
        try:
            os.replace(old, slot_path(0))
        except OSError:
            pass


def slot_info(i):
    try:
        with open(slot_path(i), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def any_save():
    return any(os.path.exists(slot_path(i)) for i in range(SLOTS))


def use_slot(i):
    UI.SAVE = slot_path(i)


def save_wrap(old):
    def f(g, quiet=False):
        old(g, quiet)
        path = UI.SAVE
        try:
            with open(path, encoding="utf-8") as fh:
                d = json.load(fh)
        except (OSError, ValueError):
            return
        try:
            d.update(play_t=round(g.get("play_t", 0.0), 1), tut=g.get("tut", 99),
                     zname=G.REGIONS[g["reg"]]["name"] if g.get("reg") is not None and g["reg"] < len(G.REGIONS) else "",
                     date=time.strftime("%Y-%m-%d %H:%M"), ending=bool(g.get("ending_seen")))
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(d, fh, ensure_ascii=False)
        except (OSError, ValueError, TypeError):
            pass
    return f


def load_wrap(old):
    def f():
        g = old()
        d = {}
        try:
            with open(UI.SAVE, encoding="utf-8") as fh:
                d = json.load(fh)
        except (OSError, ValueError):
            pass
        g["play_t"] = float(d.get("play_t", 0.0))
        g["tut"] = int(d.get("tut", 99))                          # 예전 저장(안내 기록 없음)은 안내를 끝낸 것으로
        g["ending_seen"] = bool(d.get("ending"))
        return g
    return f


def draw_slots(screen, font, u, sub, t):
    SW, SH = G.W * u, G.H * u
    ST.veil(screen, (6, 4, 14), 160)
    pw, ph = 300 * u, 148 * u
    px, py = (SW - pw) // 2, (SH - ph) // 2 + 4 * u
    ST.frame(screen, px, py, pw, ph, u)
    ST.ribbon(screen, ST.bigfont(u), "새 게임 - 슬롯 선택" if sub["mode"] == "new" else "이어하기", SW // 2, py - 8 * u, u)
    fh = font.get_height()
    for i in range(SLOTS):
        y = py + 16 * u + i * 34 * u
        cur = i == sub["sel"]
        info = slot_info(i)
        ST.plate(screen, px + 12 * u, y, pw - 24 * u, 30 * u, u, 235)
        if cur:
            ST.sel_bar(screen, px + 15 * u, y + 3 * u, pw - 30 * u, 24 * u, u)
        ST.txt(screen, font, f"슬롯 {i + 1}", px + 24 * u, y + 5 * u, G.GOLD if cur else G.CREAM, u=u)
        if info:
            top = f"Lv.{info.get('lvl', 1)}   {info.get('zname') or ''}"
            bot = (f"열쇠 {info.get('keys', 0)}/3   ·   플레이 {FL.fmt_time(info.get('play_t'))}   ·   {info.get('date', '')}"
                   + ("   ·   엔딩 봄" if info.get("ending") else ""))
            ST.txt(screen, font, top, px + 70 * u, y + 5 * u, G.CREAM, u=u)
            ST.txt(screen, font, bot, px + 70 * u, y + 5 * u + fh, G.MUTED, u=u)
        else:
            ST.txt(screen, font, "비어 있음", px + 70 * u, y + 5 * u, (100, 98, 120), u=u)
    if sub.get("confirm"):
        msg = f"슬롯 {sub['sel'] + 1} 의 기록을 지우고 새로 시작할까요?  Enter 한 번 더 = 확인"
        ST.txt(screen, font, msg, SW // 2, py + ph - 14 * u, G.CORAL, True, u)
    elif sub.get("msg"):
        ST.txt(screen, font, sub["msg"], SW // 2, py + ph - 14 * u, G.CORAL, True, u)
    else:
        ST.hints(screen, font, [("W/S", "슬롯"), ("Enter", "확인"), ("ESC", "닫기")], SW // 2, py + ph - 14 * u, u, "center")


# ================================================================= 일시정지 (설정 항목 포함)
def pause_key(g, k):
    n = len(PAUSE_ITEMS)
    if k == pygame.K_ESCAPE:
        g["ui"] = None
    elif k in (pygame.K_UP, pygame.K_w):
        g["pm"] = (g["pm"] - 1) % n
        G.play("ui")
    elif k in (pygame.K_DOWN, pygame.K_s):
        g["pm"] = (g["pm"] + 1) % n
        G.play("ui")
    elif k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
        i = g["pm"]
        G.play("ok")
        if i == 0:
            g["ui"] = None
        elif i == 1:
            g["autosave_ok"] = True
            UI.save_game(g)
            g["ui"] = None
        elif i == 2:
            g["ui"] = "map"
        elif i == 3:
            g["ui"] = "settings"
            SET["_sel"] = 0
        elif i == 4:
            g["_title"] = True
        else:
            g["_exit"] = True
    return g


# ================================================================= 게임패드
PAD = dict(sticks={}, nav_t=0.0, last=(0, 0))
BTN_A, BTN_B, BTN_X, BTN_Y, BTN_LB, BTN_RB, BTN_BACK, BTN_START = range(8)


def pad_move():
    dx = dy = 0
    for j in PAD["sticks"].values():
        try:
            ax, ay = j.get_axis(0), j.get_axis(1)
            if abs(ax) > 0.35:
                dx = 1 if ax > 0 else -1
            if abs(ay) > 0.35:
                dy = 1 if ay > 0 else -1
            if j.get_numhats():
                hx, hy = j.get_hat(0)
                dx, dy = dx or hx, dy or -hy
        except pygame.error:
            pass
    return dx, dy


def pad_throw():
    for j in PAD["sticks"].values():
        try:
            if j.get_numbuttons() > BTN_A and j.get_button(BTN_A):
                return True
        except pygame.error:
            pass
    return False


def pad_button_key(b, menu):
    if b == BTN_A:
        return pygame.K_RETURN if menu else None
    return {BTN_B: pygame.K_ESCAPE, BTN_X: pygame.K_e, BTN_Y: pygame.K_i, BTN_LB: pygame.K_q,
            BTN_RB: pygame.K_d if menu else pygame.K_z, BTN_BACK: pygame.K_m, BTN_START: pygame.K_ESCAPE}.get(b)


def pad_nav(dt, menu):
    """메뉴에서 스틱/십자키를 방향키처럼 (누르고 있으면 반복)"""
    if not menu:
        PAD["last"] = (0, 0)
        return []
    dx, dy = pad_move()
    out = []
    if (dx, dy) != PAD["last"]:
        PAD["nav_t"] = 0.35
        if (dx, dy) != (0, 0):
            out.append((dx, dy))
    elif (dx, dy) != (0, 0):
        PAD["nav_t"] -= dt
        if PAD["nav_t"] <= 0:
            PAD["nav_t"] = 0.12
            out.append((dx, dy))
    PAD["last"] = (dx, dy)
    keys = []
    for dx, dy in out:
        keys.append(pygame.K_UP if dy < 0 else pygame.K_DOWN if dy > 0 else pygame.K_LEFT if dx < 0 else pygame.K_RIGHT)
    return keys


# ================================================================= 메인 루프
def title_items():
    has = any_save()
    return [("이어하기", has), ("새 게임", True), ("설정", True), ("조작법", True), ("종료", True)]


def start_game(slot, new):
    use_slot(slot)
    if new:
        try:
            if os.path.exists(slot_path(slot)):
                os.remove(slot_path(slot))
        except OSError:
            pass
        g = G.new_state()
        g["play_t"] = 0.0
    else:
        g = UI.load_game()
    g["autosave_ok"] = True
    g["slot"] = slot
    if new:
        UI.save_game(g, quiet=True)                               # 슬롯을 바로 차지해 둔다
    G.set_music(g["reg"])
    G.play("up")
    return g


def main():
    pygame.init()
    try:
        pygame.joystick.init()
    except pygame.error:
        pass
    G.init_sound()
    load_settings()
    apply_settings()
    migrate_old_save()
    try:
        dw, dh = pygame.display.get_desktop_sizes()[0]
    except Exception:
        dw, dh = 1280, 720
    u = max(2, min(dw * 9 // 10 // G.W, dh * 9 // 10 // G.H))
    try:
        pygame.display.set_icon(ST.boomerang(2, 30))
    except Exception:
        pass
    screen = pygame.display.set_mode((G.W * u, G.H * u))
    pygame.display.set_caption("부메랑으로 살아남기")
    if SET["fullscreen"]:
        set_fullscreen(True)
    surf, font, clock = pygame.Surface((G.W, G.H)), G.load_font(6 * u), pygame.time.Clock()
    state, sel, g, help_on, t, sub = "title", 0, None, False, 0.0, None
    G.set_music(5)
    while True:
        dt = min(clock.tick(60) / 1000, 0.05)
        t += dt
        items = title_items()
        if not items[sel][1]:
            sel = 1
        in_game = state == "game" and g is not None
        menu = not in_game or g["ui"] is not None or g["mode"] != "play"
        keys = []
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                return
            if ev.type == getattr(pygame, "JOYDEVICEADDED", -1):
                try:
                    j = pygame.joystick.Joystick(ev.device_index)
                    PAD["sticks"][j.get_instance_id()] = j
                    if in_game:
                        G.toast(g, "게임패드 연결됨", 2.0)
                except pygame.error:
                    pass
            elif ev.type == getattr(pygame, "JOYDEVICEREMOVED", -1):
                PAD["sticks"].pop(ev.instance_id, None)
            elif ev.type == pygame.JOYBUTTONDOWN:
                k = pad_button_key(ev.button, menu)
                if k:
                    keys.append(k)
            elif ev.type == pygame.KEYDOWN:
                keys.append(ev.key)
        keys += pad_nav(dt, menu)
        for k in keys:
            if k == pygame.K_F11:
                SET["fullscreen"] = not SET["fullscreen"]
                set_fullscreen(SET["fullscreen"])
                save_settings()
                continue
            if state == "title":
                if help_on:
                    help_on = False
                    continue
                if sub and sub["kind"] == "settings":
                    if settings_key(k):
                        sub = None
                    continue
                if sub and sub["kind"] == "slots":
                    if k in (pygame.K_ESCAPE, pygame.K_BACKSPACE):
                        sub = None
                        G.play("back")
                    elif k in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s):
                        sub["sel"] = (sub["sel"] + (-1 if k in (pygame.K_UP, pygame.K_w) else 1)) % SLOTS
                        sub["confirm"], sub["msg"] = False, ""
                        G.play("ui")
                    elif k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                        i, has = sub["sel"], slot_info(sub["sel"]) is not None
                        if sub["mode"] == "load":
                            if has:
                                g, state, sub = start_game(i, False), "game", None
                            else:
                                sub["msg"] = "빈 슬롯이다"
                                G.play("deny")
                        elif has and not sub.get("confirm"):
                            sub["confirm"] = True
                            G.play("deny")
                        else:
                            g, state, sub = start_game(i, True), "game", None
                    continue
                if k in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s):
                    d = -1 if k in (pygame.K_UP, pygame.K_w) else 1
                    for _ in range(len(items)):
                        sel = (sel + d) % len(items)
                        if items[sel][1]:
                            break
                    G.play("ui")
                elif k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                    label = items[sel][0]
                    G.play("ok")
                    if label == "이어하기":
                        last = max(range(SLOTS), key=lambda i: (slot_info(i) or {}).get("date", ""))
                        sub = dict(kind="slots", mode="load", sel=last, confirm=False, msg="")
                    elif label == "새 게임":
                        empty = next((i for i in range(SLOTS) if slot_info(i) is None), 0)
                        sub = dict(kind="slots", mode="new", sel=empty, confirm=False, msg="")
                    elif label == "설정":
                        SET["_sel"] = 0
                        sub = dict(kind="settings")
                    elif label == "조작법":
                        help_on = True
                    else:
                        pygame.quit()
                        return
                elif k == pygame.K_ESCAPE:
                    pygame.quit()
                    return
            else:
                if g["ui"] == "settings":
                    if settings_key(k):
                        g["ui"] = "pause"
                    continue
                g = G.on_key(g, k)
                if g is None:
                    pygame.quit()
                    return
        if state == "game":
            if g.get("_exit"):
                pygame.quit()
                return
            if g.get("_title"):
                state, g, sel = "title", None, 0
                G.set_music(5)
                continue
            if g["mode"] == "play" and g["ui"] is None:
                kp = pygame.key.get_pressed()
                dx, dy, th = G.read_input(kp)
                px, py = pad_move()
                inp = (max(-1, min(1, dx + px)), max(-1, min(1, dy + py)), th or pad_throw())
                G.update(g, inp, dt)
            elif g["mode"] == "play" and g["ui"] == "bench":
                G.update_forge(g, dt)
            if g["mode"] == "play" and g["ui"] not in ("pause", "settings"):
                g["play_t"] = g.get("play_t", 0.0) + dt
            if not SET["shake"]:
                g["shake"] = 0
            G.render(screen, surf, font, g, u)
            if g["ui"] == "settings":
                draw_settings(screen, font, u)
        else:
            UI.draw_title(screen, font, u, t, sel, items, help_on)
            if sub and sub["kind"] == "slots":
                draw_slots(screen, font, u, sub, t)
            elif sub and sub["kind"] == "settings":
                draw_settings(screen, font, u)
        if pygame.mixer.get_init() and AU:                       # 새 곡이 재생되면 채널 음량이 초기화되므로 매 프레임 맞춘다
            try:
                pygame.mixer.Channel(0).set_volume(AU.VOL["music"])
            except pygame.error:
                pass
        pygame.display.flip()


# ================================================================= 설치
def install(g_mod, cfg, ui_mod, style_mod, audio_mod, feel_mod):
    global G, C, UI, ST, AU, FL
    G, C, UI, ST, AU, FL = g_mod, cfg, ui_mod, style_mod, audio_mod, feel_mod
    UI.PAUSE_ITEMS = PAUSE_ITEMS
    UI.pause_key = pause_key
    same = G.save_game is UI.save_game                            # 개발자 모드에서는 UI 쪽만 '저장 안 함'으로 바뀌어 있다
    UI.save_game = save_wrap(UI.save_game)
    G.save_game = UI.save_game if same else save_wrap(G.save_game)
    same = G.load_game is UI.load_game
    UI.load_game = load_wrap(UI.load_game)
    G.load_game = UI.load_game if same else load_wrap(G.load_game)
    UI.has_save = G.has_save = any_save
    UI.main = main
    load_settings()
    apply_settings()
