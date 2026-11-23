"""픽셀 폐허 탐험 v9 실행 파일

  python game_v9.py           (개발자 모드: python game_v9.py --dev  ->  게임 중 F1)

같은 폴더에 아래 파일이 있어야 한다.
  topdown_rpg.py  (v8 원본 - 수정하지 않는다)   config.py   v9_boss.py   v9_roster.py   v9_world.py   v9_ui.py   v9_dev.py(선택)
오류가 나도 게임은 계속 돌아가며, 내용은 v9_errors.log 에 기록된다."""
import os
import sys
import traceback
import types

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import config as C  # noqa: E402

LOG = os.path.join(HERE, "v9_errors.log")
_seen = set()
# v8 원본의 '함수 안에 박혀 있던 숫자'를 config.py 의 값으로 바꿔 끼운다. (원본 파일은 그대로 두고 읽을 때만 바꾼다)
PATCHES = [
    ('sp = 70 * (1 + 0.08 * g["lv"]["spd"])', 'sp = CFG.PLAYER["speed"] * (1 + 0.08 * g["lv"]["spd"])'),
    ('spd=70 * (1 + 0.08 * lv["spd"])', 'spd=CFG.PLAYER["speed"] * (1 + 0.08 * lv["spd"])'),
    ('hp=5 + lv["hp"] + lvl // 3', 'hp=CFG.PLAYER["start_hp"] + lv["hp"] + lvl // 3'),
    ('face="down", hp=5, mhp=5,', 'face="down", hp=CFG.PLAYER["start_hp"], mhp=CFG.PLAYER["start_hp"],'),
    ('b["x"] += b["dx"] * 200 * dt', 'b["x"] += b["dx"] * CFG.PLAYER["boom_speed"] * dt'),
    ('b["y"] += b["dy"] * 200 * dt', 'b["y"] += b["dy"] * CFG.PLAYER["boom_speed"] * dt'),
    ('b["d"] += 200 * dt', 'b["d"] += CFG.PLAYER["boom_speed"] * dt'),
    ('b["x"] += ex_ / d * 240 * dt', 'b["x"] += ex_ / d * CFG.PLAYER["boom_return"] * dt'),
    ('b["y"] += ey_ / d * 240 * dt', 'b["y"] += ey_ / d * CFG.PLAYER["boom_return"] * dt'),
    ('if g["regen"] >= 2:', 'if g["regen"] >= CFG.PLAYER["regen_sec"]:'),
    # v8 에는 소리 끔 변수(MUTED)와 UI 색(MUTED)의 이름이 겹쳐, 소리가 전혀 나지 않고 M 키가 UI를 깨뜨린다 -> 이름을 분리
    ("MUTED = False\n_music", "SND_MUTED = False\n_music"),
    ("if s and not MUTED:", "if s and not SND_MUTED:"),
    ("set_volume(0.0 if MUTED else 0.35)", "set_volume(0.0 if SND_MUTED else 0.35)"),
    ("global MUTED\n    MUTED = not MUTED", "global SND_MUTED\n    SND_MUTED = not SND_MUTED"),
    ('"소리 꺼짐" if MUTED else "소리 켜짐"', '"소리 꺼짐" if SND_MUTED else "소리 켜짐"'),
    # 보스방(넓은 아레나)에서 플레이어와 360px 넘게 떨어지면 보스 AI가 멈추던 문제 -> 보스·소환체는 항상 동작
    ('if d > 360:\n            e["mv"] = False',
     'if d > 360 and e["kind"] not in ("mid", "final", "pylon", "ex"):\n            e["mv"] = False'),
]


def v9_log(tag=""):
    msg = traceback.format_exc()
    key = (tag, msg.splitlines()[-1] if msg.strip() else "")
    if key in _seen:
        return
    _seen.add(key)
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"[{tag}]\n{msg}\n")
    except OSError:
        pass
    print(f"[v9] {tag} 오류 - v9_errors.log 를 확인하세요", file=sys.stderr)


def load_base(path):
    src = open(path, encoding="utf-8").read()
    for old, new in PATCHES:
        if old in src:
            src = src.replace(old, new)
        else:
            print(f"[v9] 참고: 원본에서 찾지 못한 치환 -> {old[:40]!r} (해당 설정은 config.py 에서 적용되지 않을 수 있음)", file=sys.stderr)
    mod = types.ModuleType("topdown_rpg")
    mod.__file__ = path
    mod.CFG = C
    mod.v9_log = v9_log
    sys.modules["topdown_rpg"] = mod
    exec(compile(src, path, "exec"), mod.__dict__)
    return mod


def build():
    G = load_base(os.path.join(HERE, "topdown_rpg.py"))
    import v9_boss
    import v9_roster, v9_roster_art, v9_roster_pat
    import v9_ui
    import v9_world
    import v9_open
    import v9_art
    import v9_boss_art
    import v9_pfx
    import v9_kaiju
    import v9_lair
    import v9_dragon
    import v9_dragon_fx

    v9_boss.install(G, C)
    v9_roster_art.apply(v9_roster)
    v9_roster_pat.apply(v9_roster)
    v9_boss_art.apply(v9_roster)             # 중간보스·최종보스 신규 디자인 (그리기 함수만 교체)
    v9_roster.install(G, C, v9_boss)          # 새 보스 4기 (반드시 v9_boss 다음, v9_world 앞)
    v9_world.install(G, C, v9_boss)
    v9_ui.install(G, C, v9_boss, v9_world)
    v9_ui.boss_bar = v9_roster.boss_bar       # 새 보스용 체력바·상태 표시
    v9_ui.objective = v9_roster.make_objective(v9_ui.objective)

    v9_open.install(G, C, v9_boss, v9_world, v9_ui)   # 오픈월드: 가장 마지막에 설치
    v9_dragon.install(G, C, v9_boss, v9_world, v9_open, v9_ui)
    v9_dragon_fx.install(G, v9_world, v9_dragon)
    v9_art.install(G, C, v9_world, v9_open, v9_ui)
    v9_lair.install(G, C, v9_world, v9_open)
    v9_pfx.install(G, v9_roster, v9_boss, v9_dragon, v9_dragon_fx)   # pixelfx 이펙트 (패턴 발동·페이즈·피격·처치)
    v9_kaiju.install(G, C, v9_boss, v9_world, v9_open, v9_ui, v9_roster)   # 필드 보스 탈라소르 (월드 남서쪽 얼음 공터)
    if "--dev" in sys.argv:
        import v9_dev
        v9_dev.install(G, C, v9_ui, v9_world)
    return G, v9_ui


if __name__ == "__main__":
    G, ui = build()
    ui.main()