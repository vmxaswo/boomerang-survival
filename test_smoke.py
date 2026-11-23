"""자동 시험 (test_smoke.py) - 코드를 고친 뒤 게임이 깨지지 않았는지 1~2분 안에 확인한다.

  python test_smoke.py

창을 띄우지 않고(소리도 끔) 게임을 조립한 뒤, 아래를 차례로 검사한다.
  1. topdown_rpg.py 원본 치환(game_v9.PATCHES)이 모두 적용됐는가
  2. 각 보스방(중간보스 3기·최종 보스·화룡)과 필드 보스 탈라소르를 무작위 조작으로 싸워도 오류가 없는가
  3. 저장 -> 불러오기 후에도 레벨·골드·클리어 기록이 그대로인가
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


print("2. 보스 전투")
g = G.new_state()
v9_dev.act_maxout(g, 0)
g = play(g, 3)
for zid, kind in (("boss_w", "mid"), ("boss_e", "mid"), ("boss_n", "mid"), ("boss_d", "dragon")):
    g = fight(f"{G.ZONES[zid]['name']} ({zid})", g, to_arena(zid), kind)
g = fight("필드 보스 탈라소르", g, to_kaiju, "kaiju")
g = fight(f"{G.ZONES['boss_f']['name']} (boss_f)", g, to_arena("boss_f"), "final", secs=40)   # 엔딩으로 끝나므로 마지막
log = errors_logged()
check(not log, "게임이 잡아서 기록한 오류 없음" + (f"\n{log[-3000:]}" if log else ""))

print("3. 저장 / 불러오기")
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

print()
print("통과" if not fails else f"실패 {len(fails)}건")
sys.exit(1 if fails else 0)
