"""자동 시험 (test_smoke.py) - 코드를 고친 뒤 게임이 깨지지 않았는지 1~2분 안에 확인한다.

  python test_smoke.py

창을 띄우지 않고(소리도 끔) 게임을 조립한 뒤, 아래를 차례로 검사한다.
  1. topdown_rpg.py 원본 치환(game_v9.PATCHES)이 모두 적용됐는가
  2. 월드에 보스 성역이 만들어졌고, 마을에서 모든 사원 입구·워프·퍼즐 스위치까지 걸어갈 수 있는가
  3. 각 보스방(중간보스 3기·최종 보스·화룡)과 필드 보스 탈라소르를 무작위 조작으로 싸워도 오류가 없는가
  4. 저장 -> 불러오기 후에도 레벨·골드·클리어 기록이 그대로인가
진짜 세이브(savegame.json)와 로그(v9_errors.log)는 건드리지 않는다. 전부 임시 폴더에서 한다.
끝에 '통과' 또는 '실패'를 출력하고, 실패하면 종료 코드 1을 돌려준다."""
import os
import random
import sys
import tempfile
import traceback

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.argv = [os.path.join(HERE, "game_v9.py"), "--dev"]      # 개발자 모드 = 무적·원킬 치트를 시험에 쓴다

import pygame  # noqa: E402

import game_v9  # noqa: E402

TMP = tempfile.mkdtemp(prefix="v9_test_")
game_v9.LOG = os.path.join(TMP, "errors.log")
fails = []


def check(ok, msg):
    print(("  [OK]   " if ok else "  [실패] ") + msg)
    if not ok:
        fails.append(msg)


def errors_logged():
    if not os.path.exists(game_v9.LOG):
        return ""
    with open(game_v9.LOG, encoding="utf-8") as f:
        return f.read()


print("1. 게임 조립")
G, ui = game_v9.build()
import v9_dev  # noqa: E402

ui.SAVE = os.path.join(TMP, "savegame.json")
check(not game_v9.MISSED, f"원본 치환 {len(game_v9.PATCHES)}개 모두 적용" +
      (f" (빠진 것: {[m[:40] for m in game_v9.MISSED]})" if game_v9.MISSED else ""))
pygame.init()
G.init_sound()
U = 2
screen = pygame.display.set_mode((G.W * U, G.H * U))
surf, font = pygame.Surface((G.W, G.H)), G.load_font(6 * U)
random.seed(2026)


def play(g, secs, chase=None):
    """무작위로 움직이며 계속 부메랑을 던진다. chase 가 있으면 그 적 쪽으로 다가간다. 예외는 그대로 올린다."""
    g["dev_god"] = g["dev_dmg"] = True
    mv = (0, 0)
    for i in range(int(secs * 60)):
        if i % 20 == 0:
            mv = (random.choice((-1, 0, 1)), random.choice((-1, 0, 1)))
            t = chase and next((e for e in g["en"] if e["kind"] == chase and e["hp"] > 0), None)
            if t and abs(t["x"] - g["x"]) + abs(t["y"] - g["y"]) > 120:
                mv = ((t["x"] > g["x"]) - (t["x"] < g["x"]), (t["y"] > g["y"]) - (t["y"] < g["y"]))
        if g["ui"] is not None:
            g["ui"] = None
        if g["mode"] == "play":
            G.update(g, (mv[0], mv[1], random.random() < 0.5), 1 / 60)
        if i % 3 == 0:
            G.render(screen, surf, font, g, U)
    return g


def fight(name, g, enter, kind, secs=25):
    try:
        enter(g)
        g = play(g, secs, chase=kind)
        alive = [e for e in g["en"] if e["kind"] == kind and e["hp"] > 0]
        check(True, f"{name}: 오류 없음" + ("" if not alive else " (시간 안에 쓰러뜨리지는 못함)"))
    except Exception:
        check(False, f"{name}: 예외 발생\n{traceback.format_exc()}")
    return g


def to_arena(zid):
    def enter(g):
        g["cleared"].discard(zid)
        g["zones"].pop(zid, None)
        G.start_travel(g, zid, 17, 24)
    return enter


def to_kaiju(g):
    G.start_travel(g, "world", *G.ZONES["field"]["start"])
    play(g, 2)
    k = next(e for e in g["en"] if e["kind"] == "kaiju")
    g["x"], g["y"] = k["x"] + 70, k["y"]


print("2. 월드 구조")
g = G.new_state()
z = g["zones"].get("world") or g
meta = g.get("meta") or z.get("meta")
check(bool(meta and meta.get("sites")), f"보스 성역·중앙 사원 구역 생성 ({meta.get('sites') if meta else '없음'})")
start = tuple(meta["start"])
seen, q = {start}, [start]
for a, b in q:
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        n = (a + dx, b + dy)
        if n not in seen and 0 <= n[0] < g["wt"] and 0 <= n[1] < g["ht"] and n not in g["solid"]:
            seen.add(n)
            q.append(n)
T = G.T
targets = [(f"{k} 앞", tuple(v)) for k, v in meta["fronts"].items()]
targets += [(f"워프 {w['name']}", (w["tx"], w["ty"] + 1)) for w in g["warps"]]
targets += [(f"스위치 {p['pid']}", (int(s["x"]) // T, int(s["y"]) // T)) for p in g["pz"] for s in p["sw"]]
bad = [name for name, t in targets if t not in seen]
check(not bad, f"마을에서 목표 {len(targets)}곳 모두 걸어갈 수 있음" + (f" (막힘: {bad})" if bad else ""))
for key, (x0, y0, x1, y1, side, mid) in meta["lairs"].items():   # 보스 건물: 문이 열리면 걸어 들어가 보스방으로
    try:
        g2 = G.new_state()
        q = next(p for p in g2["pz"] if p["pid"] == key)
        q["done"] = True
        g2["solid"] -= q["gate"]
        mx = (x0 + x1) // 2
        rx, ry = G.ZONES[key]["lair"][0], G.ZONES[key]["lair"][1] + 2      # 보스를 쓰러뜨리고 돌아오는 자리
        g2["x"], g2["y"] = mx * T + 8, (y1 + 2) * T + 8
        g2["en"] = []
        for i in range(240):
            if g2["zid"] != "world":
                break
            G.update(g2, (0, -1, False), 1 / 60)
        check(g2["zid"] == G.ARENA_OF[mid] and (rx, ry) not in g["solid"],
              f"{G.ZONES[G.ARENA_OF[mid]]['name']}: 문으로 들어가면 보스방, 돌아오는 자리도 비어 있음 (도착: {g2['zid']})")
    except Exception:
        check(False, f"{key} 건물 입장 시험 예외\n{traceback.format_exc()}")

print("3. 보스 전투")
v9_dev.act_maxout(g, 0)
g = play(g, 3)
for zid, kind in (("boss_w", "mid"), ("boss_e", "mid"), ("boss_n", "mid"), ("boss_d", "dragon")):
    g = fight(f"{G.ZONES[zid]['name']} ({zid})", g, to_arena(zid), kind)
g = fight("필드 보스 탈라소르", g, to_kaiju, "kaiju")
g = fight(f"{G.ZONES['boss_f']['name']} (boss_f)", g, to_arena("boss_f"), "final", secs=40)   # 엔딩으로 끝나므로 마지막
log = errors_logged()
check(not log, "게임이 잡아서 기록한 오류 없음" + (f"\n{log[-3000:]}" if log else ""))

print("4. 저장 / 불러오기")
try:
    g = G.new_state()
    g["autosave_ok"] = True
    play(g, 1)
    g["lvl"], g["keys"], g["inv"]["gold"] = 12, 2, 345
    g["cleared"] |= {"boss_w", "boss_d"}
    G.save_game(g)
    g2 = G.load_game()
    same = (g2["lvl"], g2["keys"], g2["inv"]["gold"], g2["cleared"]) == (12, 2, 345, {"boss_w", "boss_d"})
    check(same, "레벨·열쇠·골드·클리어 기록 유지")
except Exception:
    check(False, f"저장/불러오기 예외\n{traceback.format_exc()}")

print("5. 새 기능 (안내 · 지역 카드 · 엔딩 · 슬롯 · 설정 · 화면)")
try:
    import v9_menu, v9_feel, v9_style
    import config as C
    v9_menu.SETTINGS = os.path.join(TMP, "settings.json")          # 진짜 설정 파일은 건드리지 않는다
    g = G.new_state()
    g["dev_god"] = True
    check(g.get("tut") == 0, "새 게임은 첫 모험 안내를 처음부터 시작")
    for i in range(90):
        G.update(g, (1, 0, False), 1 / 60)
    check(g.get("tut", 0) >= 1 and g.get("_card") is not None or g.get("_seenreg"), "걸으면 안내가 다음 단계로, 지역 이름 카드 표시")
    G.render(screen, surf, font, g, U)
    g["ui"] = "inv"
    G.on_key(g, pygame.K_d)
    check(g.get("ic") == 1, "인벤토리에서 A/D 로 재료 고르기")
    g["ui"] = None
    # 엔딩 -> 계속 탐험하기
    g["mode"], g["_end_t0"] = "ending", v9_feel.now() - 5
    G.render(screen, surf, font, g, U)
    G.on_key(g, pygame.K_RETURN)
    for i in range(120):
        G.update(g, (0, 0, False), 1 / 60)
    check(g["mode"] == "play" and g["zid"] == "world" and "boss_f" in g["cleared"], "엔딩 뒤 Enter = 사원 앞에서 계속 탐험")
    # 저장 슬롯: 플레이 시간·안내 진행도 저장
    v9_menu.use_slot(1)
    ui.SAVE = v9_menu.slot_path(1).replace(v9_menu.HERE, TMP)
    g["play_t"], g["tut"], g["autosave_ok"] = 754.0, 3, True
    G.save_game(g)
    g3 = G.load_game()
    check(abs(g3.get("play_t", 0) - 754.0) < 1 and g3.get("tut") == 3, "슬롯 저장: 플레이 시간·안내 진행도 유지")
    # 설정: 난이도 바꾸면 보스 탄속·예고 시간이 바뀐다
    v9_menu.SET["_sel"] = v9_menu.ROWS.index("difficulty")
    v9_menu.settings_key(pygame.K_d)
    check(abs(C.DIFFICULTY["bullet_speed"] - 1.15) < 1e-6, "설정: 난이도 '어려움' 적용")
    v9_menu.settings_key(pygame.K_d)
    v9_menu.settings_key(pygame.K_d)
    check(abs(C.DIFFICULTY["bullet_speed"] - 1.0) < 1e-6, "설정: 난이도 '보통'으로 되돌림")
    # 새 화면들을 한 번씩 그려 본다
    ui.draw_title(screen, font, U, 1.0, 0, v9_menu.title_items(), False)
    v9_menu.draw_slots(screen, font, U, dict(kind="slots", mode="load", sel=0, confirm=True), 1.0)
    v9_menu.draw_settings(screen, font, U)
    g["ui"], g["pm"] = "pause", 3
    G.render(screen, surf, font, g, U)
    v9_menu.pause_key(g, pygame.K_RETURN)
    check(g["ui"] == "settings", "일시정지 > 설정 열기")
    # 능력 부메랑 = 보스 처치 보상
    g = G.new_state()
    g["dev_god"] = False
    items = {it["key"]: it for it in G.shop_items(g, "smith", 0)}
    check(items["pierce"]["done"] and items["twin"]["done"] and "처치 보상" in items["pierce"]["label"]
          and not items["ghost"]["done"], "대장간: 관통·쌍둥이는 '처치 보상' 안내(구매 불가), 벽 넘기는 아직 제작")
    k = next(e for e in g["en"] if e["kind"] == "kaiju")
    G.kill(g, k)
    G.render(screen, surf, font, g, U)
    check("pierce" in g["own"] and "pierce" in g["act"] and g.get("_reward"), "탈라소르 처치 -> 관통 획득 + 보상 카드")
    G.start_travel(g, "boss_d", 17, 24)
    for i in range(200):
        G.update(g, (0, 0, False), 1 / 60)
        if g["zid"] == "boss_d" and not g["tr"]:
            break
    d = next(e for e in g["en"] if e["kind"] == "dragon")
    G.kill(g, d)
    check("twin" in g["own"], "화룡 이그니스 처치 -> 쌍둥이 획득")
    g["ui"] = "inv"
    G.render(screen, surf, font, g, U)
    g["ui"] = None
    check(not errors_logged(), "새 화면에서 기록된 오류 없음" + (f"\n{errors_logged()[-2000:]}" if errors_logged() else ""))
except Exception:
    check(False, f"새 기능 시험 예외\n{traceback.format_exc()}")

print()
print("통과" if not fails else f"실패 {len(fails)}건")
sys.exit(1 if fails else 0)
