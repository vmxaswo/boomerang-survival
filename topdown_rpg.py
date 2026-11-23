"""픽셀 폐허 탐험 v8 (pygame-ce)
실행: pip install pygame-ce  ->  python topdown_rpg.py
이동 방향키/WASD(8방향) | Space 부메랑 (자동조준: 가까운 적 우선, 적이 없으면 가장 가까운 대상)
E 상호작용 | I 인벤토리(레벨·능력치) | Q 포션 | M 소리 켜기/끄기 | 능력 부메랑 Z/X/C 켜기/끄기 | R 부활/재시작 | ESC 닫기/종료
강화: 마을의 모루(강화작업대)에서 E -> 강화할 장비 선택 -> Space로 타이밍 맞춰 3번 내리친다
보스: 서쪽·동쪽·북쪽 수호 기계의 방(퍼즐을 풀면 열린다)의 전송문으로 들어가 전용 보스방에서 싸운다
상점/대장간/마차: W/S 선택, A/D 탭, Enter/Space 확인, E/ESC 닫기"""
import array
import math
import random
import sys
import threading

import pygame

W, H, T = 480, 270, 16
MAXD = 95
CART_PRICE = 15
ENH_MAX = 5
ENH_RATE = (1.0, 1.0, 0.9, 0.75, 0.6)                # 현재 레벨별 기본 강화 성공률 (모루 타이밍으로 최대 +15%)
NPC_LABEL = dict(smith="대장간", shop="상점", bench="모루 작업대", cart="마차 정류장")
NAMES = dict(gold="골드", wood="나무", stone="돌", ore="철광석", herb="약초", part="기계 부품", potion="포션")
MODS = [("pierce", "관통", dict(part=3, ore=3)), ("twin", "쌍둥이", dict(part=4, wood=6)),
        ("ghost", "벽 넘기", dict(part=6, herb=5, stone=4))]
MOD_KEYS = "ZXC"
MOD_DESC = dict(pierce="부메랑이 적을 관통해 여러 적을 한 번에 맞힌다",
                twin="부메랑을 최대 2개까지 동시에 날릴 수 있다 (각각 자동 조준)",
                ghost="부메랑이 벽을 통과하고, 벽 뒤 대상도 조준할 수 있다")
ENH = (("atk", "부메랑 날", "부메랑 피해량 +1", dict(gold=40, ore=2)),
       ("rng", "부메랑 줄", "사거리와 조준 범위 +15%", dict(gold=30, wood=3)),
       ("hp", "가죽 갑옷", "최대 체력 +1 (즉시 1 회복)", dict(gold=50, herb=2)),
       ("spd", "가벼운 장화", "이동 속도 +8%", dict(gold=35, herb=2, wood=2)),
       ("cdn", "정밀 손잡이", "부메랑 재장전 시간 단축", dict(gold=45, part=1, stone=3)))
ENH_ICON = dict(atk="boom", rng="range", hp="heart", spd="boot", cdn="part")
ENH_SHORT = dict(atk="날", rng="줄", hp="갑옷", spd="장화", cdn="손잡이")
SELL = (("wood", 2), ("stone", 2), ("herb", 3), ("ore", 6))
BUYMAT = (("wood", 3, 10), ("stone", 3, 10), ("herb", 2, 16))       # 자원, 수량, 골드
NODE = dict(tree=(3, "wood", (2, 3), 60), rock=(3, "stone", (2, 3), 70),
            ore=(5, "ore", (1, 2), 90), herb=(1, "herb", (1, 1), 45))   # hp, 자원, 수량, 리젠(초)
# ---- 적 데이터: 폭주 로봇(돌진 근접) / 포격 로봇(원거리) / 방패 로봇(방패 근접) / 자폭 로봇
FOE_HP = dict(bot=3, gunner=2, guard=5, bomber=2)
FOE_R = dict(bot=9, gunner=9, guard=10, bomber=8)
DROP = dict(bot=((3, 6), 0.35), gunner=((4, 8), 0.45), guard=((6, 10), 0.6), bomber=((2, 4), 0.25))
AGGRO = dict(bot=100, gunner=130, guard=90, bomber=110, mid=140)
FOE_NAME = dict(bot="폭주 로봇", gunner="포격 로봇", guard="방패 로봇", bomber="자폭 로봇", illu="환영", seed="가시 씨앗")
MID_NAMES = ("관측자 오큘러스 (Oculus)", "덩굴 수호자 가이아 (Gaia)", "고대 중력기계 노바 (Nova)")
MIX = dict(field=(("bot", 6), ("gunner", 2), ("bomber", 1)),
           west=(("bot", 3), ("gunner", 3), ("bomber", 2), ("guard", 1)),
           east=(("bot", 2), ("guard", 3), ("bomber", 2), ("gunner", 2)),
           north=(("gunner", 3), ("guard", 3), ("bomber", 3), ("bot", 2)),
           temple=(("bot", 3), ("gunner", 3), ("guard", 3), ("bomber", 3)))
SHOT_R = {0: 5, 1: 5, 2: 6, 3: 5}
ARENA_OF = {0: "boss_w", 1: "boss_e", 2: "boss_n"}                  # 중간보스 번호 -> 전용 보스방
ARENA_DOOR = {(16, 23), (17, 23), (18, 23)}                          # 보스방 입구(전투가 시작되면 봉인)
EXP = dict(bot=4, gunner=5, guard=8, bomber=4, mid=90)
NODE_EXP = dict(tree=1, rock=1, ore=3, herb=1)
LV_MAX = 30
BOSS_SUB = ("정찰과 저격의 수호 기계", "자연 침식의 수호 기계", "공간을 비트는 중력기계")
BOOM_COL = ((250, 220, 110), (215, 225, 240), (110, 190, 255), (190, 130, 255), (255, 160, 70), (255, 240, 160))
ARMOR_C = ((92, 142, 100), (100, 150, 170), (120, 132, 196), (172, 112, 204), (232, 150, 72), (255, 214, 96))
SCARF_C = ((235, 70, 70), (235, 70, 70), (255, 120, 90), (255, 150, 90), (255, 200, 90), (255, 250, 190))
BOOT_C = ((44, 38, 60), (150, 108, 70), (90, 150, 210), (172, 112, 210), (240, 150, 60), (255, 220, 100))
REGIONS = [
    dict(name="한낮의 마을 초원", floor=(172, 214, 148), floor2=(160, 204, 138), wall=(124, 132, 156), leaf=(58, 140, 72)),
    dict(name="노을빛 서쪽 회랑", floor=(244, 196, 150), floor2=(236, 184, 138), wall=(150, 104, 118), leaf=(200, 118, 64)),
    dict(name="한밤의 동쪽 정원", floor=(104, 108, 168), floor2=(94, 98, 158), wall=(70, 66, 112), leaf=(52, 96, 124)),
    dict(name="푸른 새벽의 북쪽 유적", floor=(150, 185, 205), floor2=(140, 174, 196), wall=(96, 104, 140), leaf=(70, 140, 150)),
    dict(name="황금빛 중앙 사원", floor=(226, 200, 140), floor2=(214, 188, 128), wall=(130, 100, 70), leaf=(150, 150, 70)),
    dict(name="황혼의 사원 터", floor=(200, 172, 176), floor2=(190, 162, 168), wall=(120, 92, 100), leaf=(150, 104, 124)),
]
# ---------------------------------------------------------------- 구역 데이터 (오픈월드)
# 구역끼리는 길(가장자리 출구), 고대 전송문, 마차로 이어진다. lair = 수호 기계의 방 (중간보스 전투를 위해 넓게)
ZONES = dict(
    field=dict(name="한낮의 마을 초원", reg=0, size=(80, 56), vil=(30, 40, 49, 52), start=(40, 47),
               houses=[(31, 41, 4, 3), (45, 41, 4, 3)],
               npcs=[("smith", 43, 45), ("shop", 37, 45), ("bench", 34, 49), ("cart", 46, 49)],
               roads=[[(40, 39), (40, 0)], [(40, 38), (30, 31), (16, 27), (0, 27)], [(40, 38), (50, 31), (64, 27), (79, 27)]],
               exits=[dict(side="n", a=38, b=41, to="temple", at=(30, 46)),
                      dict(side="w", a=26, b=29, to="west", at=(52, 21)),
                      dict(side="e", a=26, b=29, to="east", at=(3, 21))],
               river=("h", 14), portals=[], n=dict(tree=120, rock=22, ore=8, herb=26, bot=14, ruin=4)),
    west=dict(name="노을빛 서쪽 회랑", reg=1, size=(56, 44), lair=(6, 10, 14, 18, "e", 0),
              puzzle=("order", [(8, 28), (20, 34), (30, 26)]), npcs=[("cart", 50, 26)],
              roads=[[(55, 21), (44, 20), (32, 17), (16, 14)]],
              exits=[dict(side="e", a=20, b=23, to="field", at=(3, 27))],
              river=("v", 34), portals=[(44, 8, "east")], n=dict(tree=60, rock=14, ore=6, herb=14, bot=9, ruin=3)),
    east=dict(name="한밤의 동쪽 정원", reg=2, size=(56, 44), lair=(42, 10, 50, 18, "w", 1),
              puzzle=("all", [(46, 30), (36, 36), (26, 28)]), npcs=[("cart", 6, 26)],
              roads=[[(0, 21), (12, 20), (26, 17), (40, 14)]],
              exits=[dict(side="w", a=20, b=23, to="field", at=(76, 27))],
              river=("v", 22), portals=[(12, 8, "west")], n=dict(tree=70, rock=12, ore=6, herb=14, bot=10, ruin=3)),
    north=dict(name="푸른 새벽의 북쪽 유적", reg=3, size=(56, 44), lair=(23, 3, 33, 11, "s", 2),
               puzzle=("order", [(10, 10), (46, 10), (28, 21)]), npcs=[("cart", 23, 40)],
               roads=[[(28, 43), (27, 30), (28, 12)]],
               exits=[dict(side="s", a=26, b=29, to="temple", at=(30, 3))],
               river=("h", 30), portals=[], n=dict(tree=60, rock=14, ore=6, herb=14, bot=9, ruin=4)),
    temple=dict(name="황혼의 사원 터", reg=5, size=(60, 50), temple=(24, 14, 36, 25), npcs=[("cart", 25, 45)],
                roads=[[(30, 49), (30, 26)], [(30, 40), (14, 30), (14, 12), (22, 4), (30, 2), (30, 0)]],
                exits=[dict(side="s", a=28, b=31, to="field", at=(40, 3)),
                       dict(side="n", a=28, b=31, to="north", at=(28, 40))],
                river=None, portals=[], n=dict(tree=70, rock=14, ore=4, herb=14, bot=10, ruin=4)),
)
ZONE_ORDER = ("field", "west", "east", "temple", "north")
# 중간보스 전용 보스방 (수호 기계의 방 안쪽 전송문으로 들어간다)
ZONES.update(
    boss_w=dict(name="관측의 전당", reg=6, size=(34, 30), arena="eye", boss=0, origin="west", npcs=[], roads=[],
                exits=[], river=None, portals=[], n={}),
    boss_e=dict(name="가시덩굴 성소", reg=7, size=(34, 30), arena="vine", boss=1, origin="east", npcs=[], roads=[],
                exits=[], river=None, portals=[], n={}),
    boss_n=dict(name="중력의 심장부", reg=8, size=(34, 30), arena="grav", boss=2, origin="north", npcs=[], roads=[],
                exits=[], river=None, portals=[], n={}))
REGIONS += [dict(name="관측의 전당", floor=(226, 184, 136), floor2=(216, 172, 124), wall=(120, 76, 92), leaf=(200, 118, 64)),
            dict(name="가시덩굴 성소", floor=(84, 132, 100), floor2=(74, 120, 90), wall=(40, 76, 60), leaf=(60, 140, 72)),
            dict(name="중력의 심장부", floor=(66, 66, 118), floor2=(58, 58, 108), wall=(40, 32, 84), leaf=(70, 96, 150))]
PAL = {"k": (44, 38, 60), "s": (247, 208, 168), "h": (70, 120, 150), "H": (112, 176, 196), "b": (150, 108, 70),
       "c": (92, 142, 100), "g": (170, 180, 195), "G": (118, 126, 150), "r": (235, 70, 70), "d": (96, 64, 52),
       "n": (112, 78, 52), "p": (176, 134, 88), "L": (44, 38, 60), "w": (250, 250, 250), "y": (250, 220, 90), "o": (232, 140, 60),
       "u": (90, 170, 230), "D": (66, 64, 88)}


# ---------------------------------------------------------------- 소리 (코드로 합성, 외부 파일 없음)
SR = 22050
SND, TRACKS = {}, {}
MUTED = False
_music = dict(cur=None)


def _wave(kind, ph):
    p = ph % 1
    if kind == "sq":
        return 1.0 if p < 0.5 else -1.0
    if kind == "tri":
        return 4 * abs(p - 0.5) - 1
    if kind == "saw":
        return 2 * p - 1
    if kind == "noise":
        return random.uniform(-1, 1)
    return math.sin(ph * 6.283185)


def tone(f0, f1, dur, kind="sine", vol=0.3, decay=3.0):
    n, out, ph = int(SR * dur), array.array("h"), 0.0
    for i in range(n):
        t = i / n
        ph += (f0 + (f1 - f0) * t) / SR
        out.append(int(32767 * vol * min(1, i / 120) * math.exp(-decay * t) * _wave(kind, ph)))
    return out


def seq(*parts):
    out = array.array("h")
    for p in parts:
        out.extend(p)
    return out


def layer(*parts):
    n = max(len(p) for p in parts)
    out = array.array("h", [0] * n)
    for p in parts:
        for i, v in enumerate(p):
            out[i] = max(-32767, min(32767, out[i] + v))
    return out


def rest(dur):
    return array.array("h", [0] * int(SR * dur))


def init_sound():
    try:
        pygame.mixer.init(SR, -16, 1, 512)
        pygame.mixer.set_num_channels(14)
        pygame.mixer.set_reserved(1)                      # 0번 채널은 배경음악 전용
    except Exception:
        return
    fx = dict(
        throw=tone(420, 900, 0.14, "saw", 0.16, 4),
        catch=tone(760, 520, 0.07, "tri", 0.22, 4),
        hit=layer(tone(320, 90, 0.1, "sq", 0.2, 6), tone(0, 0, 0.1, "noise", 0.25, 8)),
        kill=layer(tone(520, 110, 0.28, "sq", 0.22, 3), tone(0, 0, 0.22, "noise", 0.2, 6)),
        hurt=tone(220, 80, 0.28, "saw", 0.3, 3),
        chop=layer(tone(170, 110, 0.08, "sine", 0.35, 8), tone(0, 0, 0.07, "noise", 0.2, 12)),
        pickup=seq(tone(880, 880, 0.05, "sq", 0.16, 2), tone(1320, 1320, 0.1, "sq", 0.16, 3)),
        buy=seq(tone(660, 660, 0.06, "sq", 0.16, 2), tone(880, 880, 0.06, "sq", 0.16, 2), tone(1100, 1100, 0.14, "sq", 0.16, 3)),
        deny=tone(160, 120, 0.2, "sq", 0.2, 3),
        up=seq(*[tone(f, f, 0.09, "tri", 0.28, 2) for f in (523, 659, 784, 1047)]),
        fail=tone(300, 70, 0.4, "saw", 0.25, 2.5),
        switch=tone(900, 1500, 0.12, "sine", 0.3, 2),
        gate=layer(tone(90, 55, 0.7, "saw", 0.28, 1.5), tone(0, 0, 0.7, "noise", 0.1, 3)),
        portal=layer(tone(250, 1300, 0.6, "sine", 0.3, 1.5), tone(255, 1330, 0.6, "tri", 0.15, 1.5)),
        potion=seq(tone(500, 700, 0.08, "sine", 0.3, 2), tone(700, 900, 0.1, "sine", 0.3, 3)),
        shoot=tone(420, 200, 0.1, "sq", 0.09, 4),
        ui=tone(900, 900, 0.035, "sq", 0.12, 2),
        cart=seq(*[seq(tone(0, 0, 0.05, "noise", 0.3, 12), rest(0.08)) for _ in range(5)]),
        boss=layer(tone(120, 40, 0.5, "saw", 0.3, 2), tone(0, 0, 0.4, "noise", 0.15, 4)),
        boom=layer(tone(140, 40, 0.35, "sine", 0.4, 4), tone(0, 0, 0.3, "noise", 0.3, 7)),
        clang=layer(tone(700, 650, 0.12, "sq", 0.12, 8), tone(1400, 1300, 0.1, "sine", 0.2, 8)),
        anvil=layer(tone(1500, 1450, 0.4, "sine", 0.28, 4), tone(2250, 2200, 0.3, "sine", 0.14, 5),
                    tone(0, 0, 0.05, "noise", 0.4, 30)),
        anvilg=layer(tone(1900, 1880, 0.45, "sine", 0.28, 3), tone(2850, 2800, 0.35, "sine", 0.16, 4),
                     tone(950, 940, 0.3, "tri", 0.12, 5), tone(0, 0, 0.05, "noise", 0.4, 30)),
        anvilp=layer(tone(2400, 2380, 0.5, "sine", 0.3, 3), tone(3600, 3560, 0.4, "sine", 0.18, 4),
                     tone(1200, 1190, 0.4, "tri", 0.16, 4), tone(0, 0, 0.06, "noise", 0.5, 35)),
        quench=layer(tone(0, 0, 0.7, "noise", 0.16, 2.5), tone(900, 300, 0.5, "sine", 0.14, 3)),
        levelup=seq(*[tone(f, f, 0.08, "tri", 0.28, 2) for f in (523, 659, 784, 1047, 1319)],
                    layer(tone(1568, 1568, 0.35, "tri", 0.26, 2), tone(784, 784, 0.35, "sine", 0.2, 2))),
    )
    for k, arr in fx.items():
        s = pygame.mixer.Sound(buffer=arr.tobytes())
        SND[k] = s


def play(name):
    s = SND.get(name)
    if s and not MUTED:
        try:
            s.play()
        except Exception:
            pass


def make_track(reg):
    """지역별 8초짜리 배경음악 루프 (펜타토닉 + 베이스)"""
    r = random.Random(reg * 77 + 3)
    root = (220.0, 196.0, 174.6, 233.1, 207.7, 246.9, 185.0, 164.8, 130.8)[reg]
    sc = [0, 2, 4, 7, 9] if reg in (0, 3, 4) else [0, 3, 5, 7, 10]
    step, steps = 0.3, 24
    N = int(SR * step * steps)
    buf = [0.0] * N

    def note(t0, f, dur, kind, vol, dec):
        i0, n, ph = int(t0 * SR), int(dur * SR), 0.0
        for i in range(n):
            ph += f / SR
            buf[(i0 + i) % N] += vol * math.exp(-dec * i / n) * min(1, i / 150) * _wave(kind, ph)
    deg = 2
    for s in range(steps):
        if r.random() < 0.55:
            deg = max(0, min(9, deg + r.choice((-2, -1, 0, 1, 2))))
            note(s * step, root * 2 * 2 ** ((sc[deg % 5] + 12 * (deg // 5)) / 12), 0.45, "tri", 0.1, 3)
        if s % 8 == 0:
            note(s * step, root / 2 * 2 ** (r.choice((0, sc[2], sc[3])) / 12), 2.0, "sine", 0.2, 1.0)
    return array.array("h", [int(max(-1, min(1, v)) * 32767 * 0.55) for v in buf])


def set_music(reg):
    if not SND or reg == _music["cur"]:
        return
    _music["cur"] = reg

    def gen():
        try:
            if reg not in TRACKS:
                TRACKS[reg] = pygame.mixer.Sound(buffer=make_track(reg).tobytes())
            if _music["cur"] == reg:
                ch = pygame.mixer.Channel(0)
                TRACKS[reg].set_volume(0.0 if MUTED else 0.35)
                ch.play(TRACKS[reg], loops=-1, fade_ms=800)
        except Exception:
            pass
    threading.Thread(target=gen, daemon=True).start()


def toggle_mute(g):
    global MUTED
    MUTED = not MUTED
    for t in TRACKS.values():
        t.set_volume(0.0 if MUTED else 0.35)
    toast(g, "소리 꺼짐" if MUTED else "소리 켜짐", 1.5)


# ---------------------------------------------------------------- 스프라이트
def make(rows, pal=None):
    p = {**PAL, **(pal or {})}
    surf = pygame.Surface((len(rows[0]), len(rows)), pygame.SRCALPHA)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch in p:
                surf.set_at((x, y), p[ch])
    return surf


def flash(s):
    f = s.copy()
    f.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGB_ADD)
    return f


def tint(s, col):
    f = s.copy()
    f.fill(col + (0,), special_flags=pygame.BLEND_RGB_ADD)
    return f


# 주인공: 푸른 모자 + 붉은 목도리 + 초록 망토 + 커다란 배낭 (말 없는 방랑 모험가)
LEG = ["..LL..LL..", "..LL..LL.."]
BASE = {
    "down": ["...hhhh...", "..hhhhhh..", ".HHHHHHHH.", "..ssssss..", "..skssks..", "..rrrrrr..",
             ".nccccccn.", ".nccbbccn.", "..cccccc..", "..cccccc.."] + LEG,
    "up": ["...hhhh...", "..hhhhhh..", ".HHHHHHHH.", "..dddddd..", "..dddddd..", "..rrrrrr..",
           ".nnnnnnnn.", ".nnppppnn.", ".nnppppnn.", "..nnnnnn.."] + LEG,
    "right": ["...hhhh...", "..hhhhhh..", ".HHHHHHHHH", "..dsssss..", "..dsssks..", "..drrrr...",
              ".nnccccc..", ".nnccccc..", "..cccc....", "..cccc...."] + ["...LLL....", "...LLL...."],
    "dr": ["...hhhh...", "..hhhhhh..", ".HHHHHHHHH", "..ssssss..", "..sssksk..", "..rrrrrr..",
           ".nnccccc..", ".nnccccc..", "..cccccc..", "..cccccc.."] + LEG,
    "ur": ["...hhhh...", "..hhhhhh..", ".HHHHHHHHH", "..dddddd..", "..ddddds..", "..rrrrrr..",
           ".nnnnnncc.", ".nnppppcc.", ".nnppppc..", "..nnnncc.."] + LEG,
}
_PS = {}


def player_set(ht, st):
    """갑옷(체력) 강화 단계는 망토·목도리 색, 장화 강화 단계는 장화 색으로 드러난다"""
    key = (ht, st)
    if key not in _PS:
        pal = dict(c=ARMOR_C[ht], r=SCARF_C[ht], L=BOOT_C[st])
        d = {n: [make(r[:10] + (["...LLLL...", "...LLLL..."] if f else r[10:]), pal) for f in (0, 1)]
             for n, r in BASE.items()}
        for a, b in (("left", "right"), ("dl", "dr"), ("ul", "ur")):
            d[a] = [pygame.transform.flip(s, True, False) for s in d[b]]
        _PS[key] = d
    return _PS[key]


PLAYER = player_set(0, 0)
NPC_IMG = {"smith": make(BASE["down"], dict(h=(110, 110, 125), H=(160, 160, 176), c=(200, 100, 60))),
           "shop": make(BASE["down"], dict(h=(70, 150, 90), H=(120, 200, 130), c=(235, 205, 90)))}
# 적: 폭주 로봇(붉은 눈의 뿔 달린 상자) / 포격 로봇(외눈 + 포신) / 방패 로봇(주황 투구) / 자폭 로봇(폭탄)
FOE_ROWS = dict(
    bot=["..r....r..", ".kkkkkkkk.", "kGggggggGk", "kgrrggrrgk", "kgrrggrrgk", "kgkykykygk", ".kGGGGGGk."],
    gunner=["...kkkk...", "..kggggk..", ".kguuuugk.", ".kguwuugkk", ".kgggggguu", ".kGGGGGGkk", "..kkkkkk.."],
    guard=["..kkkkkk..", ".kooooook.", "kooyyyyook", "kogkrrkgok", "kooggggook", "kGGGGGGGGk", ".kGkGGkGk."],
    bomber=["......y...", ".....k....", "..kkkkkk..", ".kDDDDDDk.", ".kDrDDrDk.", ".kDDrrDDk.", "..kkkkkk.."])
FOE_LEGS = dict(bot=(".k.k..k.k.", "k.k....k.k"), gunner=("..k....k..", "...k..k..."),
                guard=("..kk..kk..", "..k....k.."), bomber=("..kk..kk..", ".kk....kk."))
SPR = {k: [make(rows + [legs]) for legs in FOE_LEGS[k]] for k, rows in FOE_ROWS.items()}
SPR_F = {k: [flash(s) for s in v] for k, v in SPR.items()}
SPR_R = {k: [tint(s, (120, 0, 0)) for s in v] for k, v in SPR.items()}
SHADOW = pygame.Surface((12, 5), pygame.SRCALPHA)
pygame.draw.ellipse(SHADOW, (0, 0, 0, 70), (0, 0, 12, 5))


def _bench():
    """그루터기 위에 놓인 모루와 기대어 놓은 망치"""
    s = pygame.Surface((20, 18), pygame.SRCALPHA)
    pygame.draw.rect(s, (96, 64, 44), (4, 12, 12, 6))
    pygame.draw.rect(s, (136, 96, 62), (4, 12, 12, 2))
    pygame.draw.rect(s, (104, 108, 130), (7, 9, 6, 3))
    pygame.draw.rect(s, (150, 154, 176), (2, 6, 16, 3))
    pygame.draw.rect(s, (200, 204, 224), (2, 6, 16, 1))
    pygame.draw.polygon(s, (150, 154, 176), [(0, 7), (3, 6), (3, 9)])
    pygame.draw.rect(s, (150, 108, 70), (17, 7, 2, 8))
    pygame.draw.rect(s, (130, 136, 160), (15, 4, 5, 3))
    return s


def _cart():
    s = pygame.Surface((34, 22), pygame.SRCALPHA)
    pygame.draw.rect(s, (150, 108, 70), (8, 9, 22, 7))
    pygame.draw.rect(s, (110, 76, 50), (8, 14, 22, 2))
    pygame.draw.arc(s, (236, 224, 200), (9, 1, 20, 16), 0, math.pi, 4)
    pygame.draw.rect(s, (236, 224, 200), (9, 9, 20, 2))
    for cx in (13, 26):
        pygame.draw.circle(s, (70, 50, 40), (cx, 17), 4)
        pygame.draw.circle(s, (170, 140, 100), (cx, 17), 1)
    pygame.draw.rect(s, (140, 90, 60), (0, 9, 8, 5))                 # 말
    pygame.draw.rect(s, (140, 90, 60), (0, 6, 3, 4))
    pygame.draw.rect(s, (90, 60, 40), (1, 14, 2, 5))
    pygame.draw.rect(s, (90, 60, 40), (5, 14, 2, 5))
    return s


BENCH_IMG, CART_IMG = _bench(), _cart()


# ---------------------------------------------------------------- 유틸
def inrect(x, y, r):
    return r[0] <= x <= r[2] and r[1] <= y <= r[3]


def ring_(solid, x0, y0, x1, y1):
    solid |= {(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1) if x in (x0, x1) or y in (y0, y1)}


def hsh(x, y):
    return (x * 73856093 ^ y * 19349663) % 997


def lerp_c(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def adj(c, d):
    return tuple(max(0, min(255, v + d)) for v in c)


def mk_foe(kind, x, y, summoned=False):
    return dict(kind=kind, x=x, y=y, hx=None if summoned else x, hy=y, hp=FOE_HP[kind], fl=0, kb=0, kx=0, ky=0,
                ag=summoned, hb=4, r=FOE_R[kind], an=random.random() * 10, st="idle", stt=0, acd=random.uniform(0.6, 1.6),
                wx=0, wy=0, wt=random.uniform(0, 2), lx=0, ly=0, al=0, mv=False, sh=True, fx=0.0, fy=1.0)


def mk_mid(x, y, i):
    return dict(kind="mid", id=i, x=x, y=y, hx=x, hy=y, hp=28, mhp=28, fl=0, kb=0, kx=0, ky=0, ag=False,
                hb=7, r=13, inv=0.0, ph2=False, cd=2.0, an=random.random() * 10, al=0, mv=False, st="idle", stt=1.5, cyc=0, sg=1,
                lk=0.0, lz=0.0, bq=0, bt=0.0, sc=0, rg=0.0, wa=0.0, wd=1, wl=0.0, flip=False, tot=1.0, mt=0.0, mc=0)


def mk_illu(own, x, y):
    """오큘러스의 분신(환영): 한 방에 사라지지만 똑같이 저격한다"""
    return dict(kind="illu", own=own, x=x, y=y, hx=None, hy=y, hp=1, mhp=1, fl=0, kb=0, kx=0, ky=0, ag=True,
                hb=4, r=10, an=random.random() * 10, al=0, mv=False, st="idle", stt=random.uniform(0.8, 1.8),
                lk=0.0, lz=0.0, sg=random.choice((-1, 1)), life=9.0)


def mk_seed(own, x, y):
    """가이아가 심은 가시 씨앗 포탑"""
    return dict(kind="seed", own=own, x=x, y=y, hx=None, hy=y, hp=2, mhp=2, fl=0, kb=0, kx=0, ky=0, ag=True,
                hb=4, r=8, an=random.random() * 10, al=0, mv=False, st="idle", stt=0, gr=0.0, acd=random.uniform(1.4, 2.2))


def noise2(rng, cs, wt, ht):
    gw, gh = wt // cs + 3, ht // cs + 3
    grid = [[rng.random() for _ in range(gw)] for _ in range(gh)]

    def f(x, y):
        fx, fy = x / cs, y / cs
        ix, iy = int(fx), int(fy)
        tx, ty = fx - ix, fy - iy
        tx, ty = tx * tx * (3 - 2 * tx), ty * ty * (3 - 2 * ty)
        a, b, c, d = grid[iy][ix], grid[iy][ix + 1], grid[iy + 1][ix], grid[iy + 1][ix + 1]
        return (a + (b - a) * tx) * (1 - ty) + (c + (d - c) * tx) * ty
    return f


def fractal(rng, c1, c2, wt, ht):
    n1, n2 = noise2(rng, c1, wt, ht), noise2(rng, c2, wt, ht)
    return lambda x, y: 0.65 * n1(x, y) + 0.35 * n2(x, y)


# ---------------------------------------------------------------- 구역 생성
def build_zone(zid):
    if ZONES[zid].get("arena"):
        return build_arena(zid)
    sp = ZONES[zid]
    wt, ht = sp["size"]
    rng = random.Random(sum(ord(c) for c in zid) * 31 + 7)
    vil, temple, lair, puz = sp.get("vil"), sp.get("temple"), sp.get("lair"), sp.get("puzzle")
    cnt = sp["n"]
    solid, houses, structs, keep, pz, core, tgate, en, gate = set(), {}, [], [], [], None, set(), [], set()
    lair_portal = None
    if vil:
        structs.append(vil)
    for hx, hy, w, h in sp.get("houses", []):
        for x in range(hx, hx + w):
            for y in range(hy, hy + h):
                solid.add((x, y))
                houses[(x, y)] = (y == hy)
    if temple:
        x0, y0, x1, y1 = temple
        ring_(solid, *temple)
        solid |= {(x0 + 2, y0 + 2), (x1 - 2, y0 + 2), (x0 + 2, y1 - 3), (x1 - 2, y1 - 3)}
        mx = (x0 + x1) // 2
        tgate = {(mx - 1 + i, y1) for i in range(3)}
        core = (mx * T + 8, (y0 + 5) * T + 8)
        structs.append((x0 - 2, y0 - 2, x1 + 2, y1 + 2))
    if lair:
        x0, y0, x1, y1, side, mid = lair
        ring_(solid, x0, y0, x1, y1)
        mx, my = (x0 + x1) // 2, (y0 + y1) // 2
        gate = ({(x1, my - 1 + i) for i in range(3)} if side == "e" else
                {(x0, my - 1 + i) for i in range(3)} if side == "w" else {(mx - 1 + i, y1) for i in range(3)})
        structs.append((x0 - 2, y0 - 2, x1 + 2, y1 + 2))
        lair_portal = dict(x=mx * T + 8, y=my * T + 8, to=ARENA_OF[mid], at=(17, 26), boss=True)   # 보스방으로 가는 전송문
    if puz:
        pz.append(dict(mode=puz[0], next=0, done=False, gate=gate,
                       sw=[dict(x=x * T + 8, y=y * T + 8, on=False, idx=j) for j, (x, y) in enumerate(puz[1])]))
        keep += puz[1]
    npcs = [(k, tx, ty) for k, tx, ty in sp["npcs"]]
    keep += [(tx, ty) for _, tx, ty in npcs] + [e["at"] for e in sp["exits"]]
    if sp.get("start"):
        keep.append(sp["start"])
    portals = [lair_portal] if lair_portal else []
    for tx, ty, to in sp["portals"]:
        dp = ZONES[to]["portals"][0]
        portals.append(dict(x=tx * T + 8, y=ty * T + 8, to=to, at=(dp[0], dp[1] + 2)))
        keep += [(tx, ty), (tx, ty + 2)]
    ter = [[0] * wt for _ in range(ht)]                     # 0 풀 1 물 2 모래 3 길 4 폐허바닥 5 덤불 7 다리

    def carve(pts):
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            L = math.hypot(bx - ax, by - ay) or 1
            n, ph = int(L * 2) + 1, rng.random() * 6.283
            for i in range(n + 1):
                t = i / n
                w = math.sin(t * math.pi) * 2.2 * math.sin(t * 5 + ph)
                x = ax + (bx - ax) * t - (by - ay) / L * w
                y = ay + (by - ay) * t + (bx - ax) / L * w
                for ox in (0, 1):
                    for oy in (0, 1):
                        tx, ty = int(x) + ox, int(y) + oy
                        if 0 <= tx < wt and 0 <= ty < ht and (tx, ty) not in solid and not (vil and inrect(tx, ty, vil)):
                            ter[ty][tx] = 3
    for road in sp["roads"]:
        carve(road)
    riv = set()
    if sp["river"]:                                         # 구불구불한 강, 길과 만나는 곳은 다리
        axis, pos = sp["river"]
        ph1, ph2 = rng.random() * 6.28, rng.random() * 6.28
        for i in range(ht if axis == "v" else wt):
            c = pos + 3 * math.sin(i * 0.17 + ph1) + 1.5 * math.sin(i * 0.41 + ph2)
            w = 1.2 + 0.7 * math.sin(i * 0.29 + ph2)
            for o in range(int(c - w) - 1, int(c + w) + 2):
                if abs(o - c) > w:
                    continue
                x, y = (o, i) if axis == "v" else (i, o)
                if 0 <= x < wt and 0 <= y < ht and (x, y) not in solid and not any(inrect(x, y, r) for r in structs):
                    if ter[y][x] == 3:
                        ter[y][x] = 7
                    else:
                        ter[y][x] = 1
                        riv.add((x, y))
    for _ in range(2):                                      # 다리를 길 폭보다 넓게 (대각선으로 끊기지 않게)
        for x, y in list(riv):
            if any(0 <= x + i < wt and 0 <= y + j < ht and ter[y + j][x + i] in (3, 7) for i in (-1, 0, 1) for j in (-1, 0, 1)):
                ter[y][x] = 7
                riv.discard((x, y))
    clear = {(x + i, y + j) for y in range(ht) for x in range(wt) if ter[y][x] in (3, 7)
             for i in (-1, 0, 1) for j in (-1, 0, 1)}
    for y in range(ht):                                     # 가장자리 덤불 (벽이 아니라 보이지 않는 경계로 막힌다)
        for x in range(wt):
            if min(x, y, wt - 1 - x, ht - 1 - y) < 2 and ter[y][x] == 0:
                ter[y][x] = 5

    def okt(x, y):
        return (3 <= x <= wt - 4 and 3 <= y <= ht - 4 and ter[y][x] == 0 and (x, y) not in solid
                and (x, y) not in clear and not any(inrect(x, y, r) for r in structs)
                and all(abs(x - kx) > 2 or abs(y - ky) > 2 for kx, ky in keep))
    tiles = [(x, y) for y in range(ht) for x in range(wt) if okt(x, y)]
    e1, e2 = fractal(rng, 13, 6, wt, ht), noise2(rng, 3, wt, ht)
    el = lambda x, y: e1(x, y) + 0.22 * e2(x, y)
    wc = sorted((t for t in tiles if not (vil and inrect(t[0], t[1], (vil[0] - 4, vil[1] - 4, vil[2] + 4, vil[3] + 4)))),
                key=lambda t: -el(*t))
    water = set(wc[:int(len(tiles) * 0.05)])
    water = {t for t in water if sum((t[0] + i, t[1] + j) in water for i in (-1, 0, 1) for j in (-1, 0, 1)) >= 4}
    water |= riv
    for x, y in water:
        ter[y][x] = 1
    solid |= water
    for y in range(1, ht - 1):                              # 물가 모래
        for x in range(1, wt - 1):
            if ter[y][x] == 0 and (x, y) not in solid and any((x + i, y + j) in water for i in (-1, 0, 1) for j in (-1, 0, 1)):
                ter[y][x] = 2
    placed = 0
    for _ in range(90):                                     # 폐허
        if placed >= cnt["ruin"]:
            break
        w, h = rng.randint(5, 8), rng.randint(4, 6)
        x, y = rng.randint(4, wt - w - 5), rng.randint(4, ht - h - 5)
        if not all(okt(i, j) for i in range(x - 1, x + w + 1) for j in range(y - 1, y + h + 1)):
            continue
        placed += 1
        gap = rng.choice("tblr")
        for i in range(x, x + w):
            for j in range(y, y + h):
                ter[j][i] = 4
                edge, corner = i in (x, x + w - 1) or j in (y, y + h - 1), i in (x, x + w - 1) and j in (y, y + h - 1)
                if not edge:
                    continue
                gp = ((gap == "t" and j == y) or (gap == "b" and j == y + h - 1)) and abs(i - (x + w // 2)) <= 1 or \
                     ((gap == "l" and i == x) or (gap == "r" and i == x + w - 1)) and abs(j - (y + h // 2)) <= 1
                if corner or (not gp and rng.random() < 0.55):
                    solid.add((i, j))
        if rng.random() < 0.6:
            solid.add((x + w // 2, y + h // 2))
    tiles = [t for t in tiles if ter[t[1]][t[0]] == 0 and t not in solid]
    occ, nodes = set(), []

    def put(kind, t):
        occ.add(t)
        nodes.append(dict(kind=kind, tx=t[0], ty=t[1], hp=NODE[kind][0], t=0, alive=True))
    fo = fractal(rng, 9, 4, wt, ht)                         # 숲은 노이즈가 높은 곳에 뭉친다
    pool = sorted(tiles, key=lambda t: -fo(*t))[:int(len(tiles) * 0.3)]
    rng.shuffle(pool)
    for t in pool[:cnt["tree"]]:
        put("tree", t)
    rk = fractal(rng, 7, 3, wt, ht)
    rp = sorted((t for t in tiles if t not in occ), key=lambda t: -rk(*t))[:int(len(tiles) * 0.12)]
    rng.shuffle(rp)
    for t in rp[:cnt["ore"]]:
        put("ore", t)
    for t in [t for t in rp if t not in occ][:cnt["rock"]]:
        put("rock", t)
    rest_t = [t for t in tiles if t not in occ]
    shore = [t for t in rest_t if any(ter[t[1] + j][t[0] + i] == 2 for i in range(-2, 3) for j in range(-2, 3))]
    rng.shuffle(shore)
    for t in shore[:cnt["herb"] * 6 // 10]:
        put("herb", t)
    rest_t = [t for t in rest_t if t not in occ]
    for t in rng.sample(rest_t, min(len(rest_t), cnt["herb"] - cnt["herb"] * 6 // 10)):
        put("herb", t)
    ntile = {(n["tx"], n["ty"]) for n in nodes if n["kind"] != "herb"}
    solid |= ntile
    far = [(e["at"][0], e["at"][1]) for e in sp["exits"]] + [(tx, ty) for k, tx, ty in npcs]
    cand = [t for t in tiles if t not in occ and not (vil and inrect(t[0], t[1], (vil[0] - 5, vil[1] - 5, vil[2] + 5, vil[3] + 5)))
            and all(abs(t[0] - fx) + abs(t[1] - fy) > 9 for fx, fy in far)]
    kinds, wts = [k for k, _ in MIX[zid]], [w for _, w in MIX[zid]]
    for x, y in rng.sample(cand, min(len(cand), cnt["bot"])):
        occ.add((x, y))
        en.append(mk_foe(rng.choices(kinds, wts)[0], x * T + 8, y * T + 8))
    sn = fractal(rng, 6, 3, wt, ht)
    shade = [[sn(x, y) for x in range(wt)] for y in range(ht)]
    return dict(solid=solid, nodes=nodes, ntile=ntile, houses=houses, pz=pz, en=en, ter=ter, water=water,
                shade=shade, rs=[], npcs=npcs, spec=sp, tgate=tgate, core=core, vil=vil, portals=portals,
                exits=sp["exits"], wt=wt, ht=ht, zreg=sp["reg"], deco=[], arena=None)


def build_arena(zid):
    """중간보스 전용 보스방: 봉인되는 문, 전실, 기둥, 화로가 있는 넓은 전당"""
    sp = ZONES[zid]
    wt, ht = sp["size"]
    rng = random.Random(sum(ord(c) for c in zid) * 17 + 5)
    solid = set()
    ring_(solid, 0, 0, wt - 1, ht - 1)
    ter = [[4] * wt for _ in range(ht)]
    for x in range(wt):                                     # 전당과 전실 사이의 벽 (문만 열려 있다)
        solid.add((x, 23))
    for y in range(24, ht - 1):
        for x in range(1, wt - 1):
            if not (15 <= x <= 19 and y <= 27):
                solid.add((x, y))
    for x in range(15, 20):
        for y in range(24, 28):
            ter[y][x] = 3
    for x in (16, 17, 18):
        solid.discard((x, 23))
        ter[23][x] = 3
    deco = []
    for bx, by in ((4, 4), (29, 4), (4, 19), (29, 19)):     # 화로 기둥
        solid.add((bx, by))
        deco.append(("brazier", bx, by))
    for px_, py_ in ((8, 7), (25, 7), (8, 15), (25, 15)):   # 2x2 석조 기둥
        for i in (0, 1):
            for j in (0, 1):
                solid.add((px_ + i, py_ + j))
    if sp["arena"] == "vine":                               # 바닥을 뒤덮은 덩굴
        for _ in range(46):
            x, y = rng.randint(2, 31) * T + rng.randint(0, 15), rng.randint(2, 21) * T + rng.randint(0, 15)
            if (x // T, y // T) not in solid:
                deco.append(("vine", x, y, rng.randint(3, 8)))
    sn = fractal(rng, 6, 3, wt, ht)
    shade = [[sn(x, y) for x in range(wt)] for y in range(ht)]
    return dict(solid=solid, nodes=[], ntile=set(), houses={}, pz=[], en=[mk_mid(17 * T + 8, 11 * T + 8, sp["boss"])],
                ter=ter, water=set(), shade=shade, rs=[], npcs=[], spec=sp, tgate=set(), core=None, vil=None,
                portals=[], exits=[], wt=wt, ht=ht, zreg=sp["reg"], deco=deco, arena=sp["arena"])


ZK = ("solid", "nodes", "ntile", "houses", "pz", "en", "ter", "water", "shade", "rs", "npcs", "spec", "tgate",
      "core", "vil", "portals", "exits", "wt", "ht", "zreg", "deco", "arena")


def save_zone(g):
    if g.get("zid"):
        g["zones"][g["zid"]] = {k: g[k] for k in ZK}


def load_zone(g, zid, tx, ty):
    save_zone(g)
    if ZONES[zid].get("arena") and zid not in g["cleared"]:        # 아직 못 깬 보스방은 들어갈 때마다 처음 상태로
        g["zones"].pop(zid, None)
    z = g["zones"].get(zid) or build_zone(zid)
    g.update(z)
    g["zid"] = zid
    g["zones"][zid] = z
    tx, ty = safe_spot(g, tx, ty)
    g.update(x=tx * T + 8, y=ty * T + 8, booms=[], shots=[], parts=[], ft=[], met=[], rings=[], aim=None, tgt=None,
             iv=1.0, pcd=1.2, lock=False, intro=0.0)
    if g["topen"]:
        g["solid"] -= g["tgate"]
    g["seen"].add(zid)
    g["reg"] = tile_reg(g, tx, ty)
    toast(g, ZONES[zid]["name"])
    set_music(g["reg"])


def safe_spot(g, tx, ty):
    """도착 타일이 막혀 있으면 가장 가까운 빈 타일로"""
    for r in range(0, 6):
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                t = (tx + dx, ty + dy)
                if max(abs(dx), abs(dy)) == r and 1 < t[0] < g["wt"] - 2 and 1 < t[1] < g["ht"] - 2 and t not in g["solid"]:
                    return t
    return tx, ty


def tile_reg(g, tx, ty):
    tp = g["spec"].get("temple")
    return 4 if tp and tp[0] < tx < tp[2] and tp[1] < ty < tp[3] else g["zreg"]


def new_state():
    g = dict(x=0, y=0, dx=0, dy=1, face="down", hp=5, mhp=5, iv=0, t=0, mode="play", ui=None,
             inv=dict(gold=0, wood=0, stone=0, ore=0, herb=0, part=0, potion=1),
             lv=dict(atk=0, rng=0, hp=0, spd=0, cdn=0), keys=0, own=set(), act=set(), booms=[], cd=0, tcd=0, shots=[],
             parts=[], ft=[], regen=0, tab=0, cur=0, smsg=("", True), tgt=None, aim=None, reg=0,
             boss=dict(hp=40, mhp=40, cd=2.5, sp=5.0, fl=0, rot=0), topen=False, moving=False, toast=["", 0],
             zones={}, zid=None, seen=set(), tr=None, pcd=0, wcd=0, forge=None, met=[], rings=[], cleared=set(), lock=False, intro=0.0,
             lvl=1, xp=0, lvup=0.0, shake=0.0)
    sx, sy = ZONES["field"]["start"]
    load_zone(g, "field", sx, sy)
    g["iv"] = 0
    toast(g, ZONES["field"]["name"], 3.0)
    return g


def respawn(g):
    g.update(hp=g["mhp"], mode="play", ui=None, tr=None, forge=None)
    g["inv"]["gold"] = g["inv"]["gold"] * 4 // 5
    g["boss"]["hp"] = g["boss"]["mhp"]
    sx, sy = ZONES["field"]["start"]
    load_zone(g, "field", sx, sy)
    g["iv"] = 2.0
    toast(g, "마을에서 깨어났다 (골드 20% 손실)")
    return g


def toast(g, s, t=3.0):
    g["toast"] = [s, t]


def need_xp(lvl):
    return int(18 * lvl ** 1.5)


def derived(g, lv=None, lvl=None):
    """강화 + 레벨로 결정되는 실제 능력치"""
    lv, lvl = lv or g["lv"], lvl or g["lvl"]
    return dict(atk=1 + lv["atk"] + (lvl - 1) // 4, rng=int(MAXD * (1 + 0.15 * lv["rng"])),
                hp=5 + lv["hp"] + lvl // 3, spd=70 * (1 + 0.08 * lv["spd"]), cdn=max(0.05, 0.25 - 0.04 * lv["cdn"]))


def stat_line(g, key, n):
    """강화 단계 n일 때의 능력치 문장 (강화 전후 비교용)"""
    lv = dict(g["lv"])
    lv[key] = n
    d = derived(g, lv)
    return dict(atk=f"피해 {d['atk']}", rng=f"사거리 {d['rng']}", hp=f"최대 체력 {d['hp']}",
                spd=f"이동 속도 {int(d['spd'])}", cdn=f"재장전 {d['cdn']:.2f}초")[key]


def set_mhp(g):
    new = derived(g)["hp"]
    if new > g["mhp"]:
        g["hp"] += new - g["mhp"]
    g["mhp"] = new


def gain_exp(g, n, x, y):
    if n <= 0 or g["lvl"] >= LV_MAX:
        return
    g["xp"] += n
    ftext(g, f"+{n} EXP", x, y, (140, 200, 255))
    while g["lvl"] < LV_MAX and g["xp"] >= need_xp(g["lvl"]):
        g["xp"] -= need_xp(g["lvl"])
        g["lvl"] += 1
        g["lvup"] = 2.4
        set_mhp(g)
        g["hp"] = g["mhp"]
        perks = []
        if g["lvl"] % 3 == 0:
            perks.append("최대 체력 +1")
        if g["lvl"] > 1 and (g["lvl"] - 1) % 4 == 0:
            perks.append("피해 +1")
        toast(g, f"레벨 업! Lv.{g['lvl']}" + (f"  ({', '.join(perks)})" if perks else ""), 3.5)
        play("levelup")
        g["rings"].append([g["x"], g["y"], 0.0, 40, (140, 200, 255)])
        spark(g, g["x"], g["y"], (140, 200, 255), 20)
    if g["lvl"] >= LV_MAX:
        g["xp"] = 0


def ftext(g, s, x, y, col=(255, 255, 255)):
    g["ft"].append([s, x, y, 1.0, col])


def can_pay(g, cost):
    return all(g["inv"].get(k, 0) >= v for k, v in cost.items())


def blocked(cx, cy, solid, hb=4):
    for tx in range(int(cx - hb) // T, int(cx + hb - 1) // T + 1):
        for ty in range(int(cy - hb) // T, int(cy + hb - 1) // T + 1):
            if (tx, ty) in solid:
                return True
    return False


def move(o, dx, dy, solid):
    hb = o.get("hb", 4)
    if not blocked(o["x"] + dx, o["y"], solid, hb):
        o["x"] += dx
    if not blocked(o["x"], o["y"] + dy, solid, hb):
        o["y"] += dy


def dist(a, b, c, d):
    return math.hypot(a - c, b - d)


def seg_dist(px, py, ax, ay, bx, by):
    """점 (px,py)에서 선분 AB까지의 거리"""
    vx, vy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((px - ax) * vx + (py - ay) * vy) / ((vx * vx + vy * vy) or 1)))
    return dist(px, py, ax + vx * t, ay + vy * t)


def wall_at(g, x, y):
    """부메랑/탄막을 막는 벽 (물은 위로 날아 지나갈 수 있다)"""
    t = (int(x) // T, int(y) // T)
    return t in g["solid"] and t not in g["water"]


def ray_end(g, x, y, ang, maxd):
    for i in range(1, int(maxd // 6) + 1):
        px, py = x + math.cos(ang) * i * 6, y + math.sin(ang) * i * 6
        if wall_at(g, px, py):
            return px, py
    return x + math.cos(ang) * maxd, y + math.sin(ang) * maxd


def free_spot(g, cx, cy, rmin, rmax, hb=7):
    for _ in range(30):
        a, r = random.random() * 6.283, random.uniform(rmin, rmax)
        x, y = cx + math.cos(a) * r, cy + math.sin(a) * r
        if T < x < g["wt"] * T - T and T < y < g["ht"] * T - T and not blocked(x, y, g["solid"], hb):
            return x, y
    return cx, cy


def in_village(g, x, y):
    return bool(g["vil"]) and inrect(int(x) // T, int(y) // T, g["vil"])


def spark(g, x, y, color, n=6):
    for _ in range(n):
        a, v = random.random() * 6.283, random.uniform(30, 80)
        g["parts"].append([x, y, math.cos(a) * v, math.sin(a) * v, 0.35, color])


def dirname(dx, dy):
    v = "up" if dy < -0.3 else "down" if dy > 0.3 else ""
    h = "left" if dx < -0.3 else "right" if dx > 0.3 else ""
    return {"downright": "dr", "downleft": "dl", "upright": "ur", "upleft": "ul"}.get(v + h) or v or h


def hurt(g, n=1):
    g["hp"] -= n
    g["iv"] = 1.0
    play("hurt")
    if g["hp"] <= 0:
        g["mode"] = "dead"


def shoot(g, x, y, ang, sp, kind=0, life=4.0):
    """탄 종류: 0 붉은 구슬 / 1 청록 저격탄 / 2 초록 씨앗 / 3 주황 포탄"""
    g["shots"].append([x, y, math.cos(ang) * sp, math.sin(ang) * sp, life, kind])


def ring(g, x, y, n, sp, off=0.0):
    play("shoot")
    for i in range(n):
        shoot(g, x, y, off + i * 6.283 / n, sp)


def aim_range(g):
    return MAXD * (1 + 0.15 * g["lv"]["rng"]) + 15


# ---------------------------------------------------------------- 타겟팅 (항상 자동조준)
def los(g, ax, ay, bx, by, own=None):
    """두 점 사이에 벽이 있으면 False (물은 시야를 막지 않는다). own은 대상 자신의 타일."""
    d = dist(ax, ay, bx, by)
    steps = int(d // 5) + 1
    for i in range(1, steps):
        x, y = ax + (bx - ax) * i / steps, ay + (by - ay) * i / steps
        t = (int(x) // T, int(y) // T)
        if t != own and t in g["solid"] and t not in g["water"]:
            return False
    return True


def valid_targets(g):
    """사거리 안 + (벽 넘기가 없으면) 벽에 가려지지 않은 대상을 가까운 순으로"""
    px, py, rg = g["x"], g["y"], aim_range(g)
    ghost = "ghost" in g["act"]
    c = [(e["x"], e["y"], e, "e") for e in g["en"]]
    for z in g["pz"]:
        c += [(s["x"], s["y"], s, "s") for s in z["sw"] if not s["on"]]
    if g["core"] and g["boss"]["hp"] > 0:
        c.append((g["core"][0], g["core"][1], g["boss"], "c"))
    c += [(n["tx"] * T + 8, n["ty"] * T + 8, n, "n") for n in g["nodes"] if n["alive"]]
    out = []
    for x, y, o, cat in c:
        d = dist(x, y, px, py)
        if d > rg:
            continue
        if not ghost and not los(g, px, py, x, y, (int(x) // T, int(y) // T) if cat == "n" else None):
            continue
        out.append((x, y, o, cat, d))
    out.sort(key=lambda t: t[4])
    return out


def pick_target(g):
    """1순위: 사거리 안의 가장 가까운 적(보스 포함). 적이 없으면 2순위: 가장 가까운 아무 대상."""
    vt = valid_targets(g)
    if not vt:
        return None
    pool = [t for t in vt if t[3] in ("e", "c")] or vt
    best = pool[0]
    for t in pool:                                          # 현재 대상은 살짝 유리하게 (깜빡임 방지)
        if t[2] is g["tgt"] and t[4] <= best[4] + 20:
            return t
    return best


def throw(g, tx, ty):
    """부메랑 1개를 대상(tx, ty)을 향해 던진다. 쌍둥이는 '동시에' 2개가 아니라 '최대 2개까지' 날려 둘 수 있다."""
    ang = math.atan2(ty - g["y"], tx - g["x"])
    play("throw")
    g["tcd"] = max(0.06, 0.18 - 0.02 * g["lv"]["cdn"])
    g["booms"].append(dict(x=g["x"], y=g["y"], dx=math.cos(ang), dy=math.sin(ang), out=True, d=0, a=0, hit=set()))


def clear_arena(g):
    """보스방 클리어: 문이 열리고 중앙에 돌아가는 전송문이 나타난다"""
    zid = g["zid"]
    g["cleared"].add(zid)
    ox0, oy0, ox1, oy1, _, _ = ZONES[ZONES[zid]["origin"]]["lair"]
    g["portals"].append(dict(x=17 * T + 8, y=11 * T + 8, to=ZONES[zid]["origin"],
                             at=((ox0 + ox1) // 2, (oy0 + oy1) // 2 + 2), boss=False))
    g["rings"].append([17 * T + 8, 11 * T + 8, 0.0, 70, (255, 230, 150)])
    spark(g, 17 * T + 8, 11 * T + 8, (255, 230, 150), 30)
    g["shots"], g["met"], g["hp"], g["shake"] = [], [], g["mhp"], 0.7
    toast(g, "수호 기계가 정지했다! 중앙의 전송문으로 돌아갈 수 있다", 4.5)
    play("up")


def kill(g, e):
    k = e["kind"]
    spark(g, e["x"], e["y"], (160, 230, 160) if k in ("illu", "seed") else (235, 70, 70), 10)
    if k in ("illu", "seed"):
        play("hit")
        return
    if k in DROP and e["hx"] is not None:
        g["rs"].append([35.0, e["hx"], e["hy"], k])
    if e.get("nodrop"):                                     # 자폭한 로봇은 아무것도 떨구지 않는다
        return
    play("kill")
    if k in DROP:
        (lo, hi), pc = DROP[k]
        gold, part = random.randint(lo, hi), 1 if random.random() < pc else 0
    else:
        gold, part = 80, 4
        g["keys"] += 1
        toast(g, f"열쇠 조각 획득! ({g['keys']}/3)")
        play("up")
        if g["spec"].get("arena"):
            clear_arena(g)
    g["inv"]["gold"] += gold
    ftext(g, f"+{gold}G", e["x"], e["y"] - 8, (255, 230, 120))
    gain_exp(g, EXP.get(k, 0), e["x"], e["y"] - 24)
    if part:
        g["inv"]["part"] += part
        ftext(g, f"+{part} 부품", e["x"], e["y"] - 16, (200, 220, 255))


def hit_node(g, n):
    n["hp"] -= 1
    spark(g, n["tx"] * T + 8, n["ty"] * T + 8, (200, 255, 160), 4)
    play("chop")
    if n["hp"] <= 0:
        _, res, (lo, hi), rs = NODE[n["kind"]]
        q = random.randint(lo, hi)
        g["inv"][res] += q
        ftext(g, f"+{q} {NAMES[res]}", n["tx"] * T + 8, n["ty"] * T, (200, 255, 160))
        play("pickup")
        gain_exp(g, NODE_EXP[n["kind"]], n["tx"] * T + 8, n["ty"] * T - 8)
        n["alive"], n["t"] = False, rs
        g["solid"].discard((n["tx"], n["ty"]))
        g["ntile"].discard((n["tx"], n["ty"]))


def hit_switch(g, z, s):
    spark(g, s["x"], s["y"], (250, 220, 110), 10)
    play("switch")
    if z["mode"] == "order":
        if s["idx"] == z["next"]:
            s["on"] = True
            z["next"] += 1
        else:
            for q in z["sw"]:
                q["on"] = False
            z["next"] = 0
            play("deny")
            toast(g, "순서가 틀렸다! 점 개수가 적은 것부터 차례로")
            return
    else:
        s["on"] = True
    if all(q["on"] for q in z["sw"]) and not z["done"]:
        z["done"] = True
        g["solid"] -= z["gate"]
        play("gate")
        toast(g, "수호 기계의 방이 열렸다!")


def blink(g, e):
    """오큘러스: 피격 직후 짧게 순간이동해 회피한다"""
    x, y = free_spot(g, e["hx"], e["hy"], 25, 80)
    spark(g, e["x"], e["y"], (180, 140, 255), 10)
    e["x"], e["y"] = x, y
    spark(g, x, y, (180, 140, 255), 10)
    e["st"], e["stt"] = "idle", max(0.5, e["stt"] if e["st"] == "idle" else 0.6)
    play("portal")


def hit_foe(g, e, b, dmg):
    """부메랑이 적에게 닿았을 때. 방패/보호막에 막히면 False."""
    k = e["kind"]
    e["ag"] = True
    if k == "guard" and e["sh"] and b["dx"] * e["fx"] + b["dy"] * e["fy"] < -0.2:      # 정면 방패 방어
        e["fl"] = 0.06
        e["kb"], e["kx"], e["ky"] = 0.08, b["dx"], b["dy"]
        spark(g, e["x"] + e["fx"] * 9, e["y"] + e["fy"] * 7, (210, 225, 255), 6)
        play("clang")
        ftext(g, "막힘!", e["x"], e["y"] - 12, (200, 215, 245))
        return False
    if k == "mid" and e["id"] == 1 and e["sc"] > 0:                                     # 가이아의 보호막
        e["sc"] -= 1
        e["fl"] = 0.06
        spark(g, e["x"], e["y"] - 8, (140, 240, 230), 8)
        play("clang")
        if e["sc"] == 0:
            toast(g, "보호막이 깨졌다!", 1.8)
        return False
    if k == "mid" and e["inv"] > 0:                         # 페이즈 전환 중에는 무적
        spark(g, e["x"], e["y"] - 8, (255, 255, 255), 6)
        play("clang")
        return False
    e["hp"] -= dmg
    e["fl"] = 0.12
    ftext(g, f"-{dmg}" if dmg < 4 else f"-{dmg}!", e["x"] + random.randint(-6, 6), e["y"] - 14,
          (255, 240, 150) if dmg < 3 else (255, 170, 80) if dmg < 5 else (255, 100, 90))
    if k != "mid" and k not in ("illu", "seed"):
        e["kb"], e["kx"], e["ky"] = 0.15, b["dx"], b["dy"]
    spark(g, e["x"], e["y"], (255, 240, 150))
    play("hit")
    if k == "mid" and e["id"] == 0 and e["hp"] > 0 and random.random() < 0.45:
        blink(g, e)
    return True


# ---------------------------------------------------------------- 일반 적 AI
def bot_ai(g, e, dt, d, ux, uy):
    """폭주 로봇: 평소엔 어슬렁, 발견하면 추격 -> 가까이서 예고(떨림) -> 돌진 -> 숨 고르기. 움직이면 True."""
    sol, st = g["solid"], e["st"]
    if not e["ag"]:
        e["st"] = "idle"
        e["sh"] = True
        e["wt"] -= dt
        if e["wt"] <= 0:
            e["wt"] = random.uniform(1.0, 2.6)
            a = random.random() * 6.283
            e["wx"], e["wy"] = (math.cos(a), math.sin(a)) if random.random() < 0.6 else (0, 0)
        if e["hx"] is not None:
            hd = dist(e["x"], e["y"], e["hx"], e["hy"])
            if hd > 40:
                e["wx"], e["wy"] = (e["hx"] - e["x"]) / hd, (e["hy"] - e["y"]) / hd
        move(e, e["wx"] * 14 * dt, e["wy"] * 14 * dt, sol)
        return bool(e["wx"] or e["wy"])
    if st == "wind":
        e["stt"] -= dt
        if e["stt"] <= 0:
            e["lx"], e["ly"], e["st"], e["stt"] = ux, uy, "dash", 0.26
        return False
    if st == "dash":
        move(e, e["lx"] * 130 * dt, e["ly"] * 130 * dt, sol)
        e["stt"] -= dt
        if e["stt"] <= 0:
            e["st"], e["stt"], e["acd"] = "rest", 0.55, random.uniform(1.2, 2.0)
        return True
    if st == "rest":
        e["stt"] -= dt
        if e["stt"] <= 0:
            e["st"] = "idle"
        return False
    move(e, ux * 28 * dt, uy * 28 * dt, sol)
    e["acd"] -= dt
    if d < 56 and e["acd"] <= 0:
        e["st"], e["stt"] = "wind", 0.45
    return True


def gunner_ai(g, e, dt, d, ux, uy):
    """포격 로봇(원거리): 거리를 유지하며 맴돌다가 조준선을 보여준 뒤 포탄을 쏜다"""
    st = e["st"]
    if st == "aim":
        e["stt"] -= dt
        if e["stt"] > 0.25:
            e["lx"], e["ly"] = ux, uy
        if e["stt"] <= 0:
            shoot(g, e["x"], e["y"], math.atan2(e["ly"], e["lx"]), 140, 3, 2.6)
            play("shoot")
            e["st"], e["stt"], e["acd"] = "rest", 0.45, random.uniform(1.6, 2.4)
        return False
    if st == "rest":
        e["stt"] -= dt
        if e["stt"] <= 0:
            e["st"] = "idle"
        return False
    if d < 55:
        vx, vy, sp = -ux, -uy, 34
    elif d > 105:
        vx, vy, sp = ux, uy, 28
    else:
        sg = 1 if int(e["an"] / 2.5) % 2 else -1
        vx, vy, sp = -uy * sg, ux * sg, 22
    move(e, vx * sp * dt, vy * sp * dt, g["solid"])
    e["acd"] -= dt
    if e["acd"] <= 0 and d < 150 and los(g, e["x"], e["y"], g["x"], g["y"]):
        e["st"], e["stt"] = "aim", 0.7
    return True


def guard_ai(g, e, dt, d, ux, uy):
    """방패 로봇(방패 근접): 정면 방패가 부메랑을 막는다. 내려찍은 뒤 방패를 내린 틈이 약점."""
    st = e["st"]
    e["sh"] = st != "rest"
    if st == "wind":
        e["stt"] -= dt
        if e["stt"] <= 0:
            e["lx"], e["ly"], e["st"], e["stt"] = ux, uy, "slam", 0.16
        return False
    if st == "slam":
        move(e, e["lx"] * 170 * dt, e["ly"] * 170 * dt, g["solid"])
        if d < 22 and g["iv"] <= 0:
            hurt(g)
        e["stt"] -= dt
        if e["stt"] <= 0:
            e["st"], e["stt"], e["acd"] = "rest", 1.1, random.uniform(1.0, 1.8)
        return True
    if st == "rest":
        e["stt"] -= dt
        if e["stt"] <= 0:
            e["st"] = "idle"
        return False
    move(e, ux * 24 * dt, uy * 24 * dt, g["solid"])
    e["acd"] -= dt
    if d < 44 and e["acd"] <= 0:
        e["st"], e["stt"] = "wind", 0.5
    return True


def bomber_ai(g, e, dt, d, ux, uy):
    """자폭 로봇: 빠르게 달려와 가까이서 불꽃이 튀다가 폭발한다. 도화선이 타는 동안 맞히면 취소된다."""
    if e["st"] == "fuse":
        e["stt"] -= dt
        if e["stt"] <= 0:
            g["rings"].append([e["x"], e["y"], 0.0, 32, (255, 170, 70)])
            spark(g, e["x"], e["y"], (255, 190, 80), 16)
            play("boom")
            if dist(g["x"], g["y"], e["x"], e["y"]) < 32 and g["iv"] <= 0:
                hurt(g)
            e["hp"], e["nodrop"] = 0, True
        return False
    zz = math.sin(e["an"] * 6) * 0.5
    move(e, (ux - uy * zz) * 52 * dt, (uy + ux * zz) * 52 * dt, g["solid"])
    if d < 30:
        e["st"], e["stt"] = "fuse", 0.75
    return True


def foe_ai(g, e, dt, d, ux, uy):
    k = e["kind"]
    if not e["ag"] or k == "bot":
        return bot_ai(g, e, dt, d, ux, uy)
    e["fx"], e["fy"] = ux, uy
    return dict(gunner=gunner_ai, guard=guard_ai, bomber=bomber_ai)[k](g, e, dt, d, ux, uy)


# ---------------------------------------------------------------- 중간보스 AI
def oculus_ai(g, e, dt, d, ux, uy):
    """관측자 오큘러스: 거리를 벌리며 정찰 -> 레이저 조준선(마지막 0.3초 고정) -> 고속 저격탄. 분신 소환, 피격 시 순간이동."""
    e["stt"] -= dt
    st, half = e["st"], e["hp"] <= e["mhp"] / 2
    if st == "idle":
        if d < 60:
            vx, vy, sp = -ux, -uy, 44
        elif d > 115:
            vx, vy, sp = ux, uy, 32
        else:
            vx, vy, sp = -uy * e["sg"], ux * e["sg"], 28
        move(e, vx * sp * dt, vy * sp * dt, g["solid"])
        if e["stt"] <= 0:
            e["cyc"] += 1
            e["sg"] = random.choice((-1, 1))
            has = any(o["kind"] == "illu" and o["own"] is e and o["hp"] > 0 for o in g["en"])
            if not has and (e["cyc"] % 3 == 0 or (half and e["cyc"] % 2 == 0)):
                e["st"], e["stt"] = "clone", 0.8
                play("portal")
            else:
                e["st"], e["stt"] = "aim", 0.8 if half else 1.0
        return True
    if st == "clone":
        if e["stt"] <= 0:
            for _ in range(3 if half else 2):
                x, y = free_spot(g, e["hx"], e["hy"], 25, 80)
                spark(g, x, y, (180, 140, 255), 8)
                g["en"].append(mk_illu(e, x, y))
            e["st"], e["stt"] = "idle", 1.2
        return False
    if st == "aim":
        if e["stt"] > 0.3:
            e["lz"] = math.atan2(uy, ux)
        if e["stt"] <= 0:
            e["st"], e["stt"], e["bq"], e["bt"] = "fire", 0.6, 4 if half else 3, 0.0
        return False
    e["bt"] -= dt                                           # 저격탄 연사
    if e["bq"] > 0 and e["bt"] <= 0:
        e["bq"] -= 1
        e["bt"] = 0.09
        shoot(g, e["x"], e["y"], e["lz"], 280, 1, 1.4)
        play("shoot")
    if e["bq"] <= 0 and e["stt"] <= 0:
        e["st"], e["stt"] = "idle", random.uniform(1.2, 2.0)
    return False


def illu_ai(g, e, dt, d, ux, uy):
    """환영: 오큘러스처럼 조준선을 띄우고 한 발 쏜다 (한 방에 사라진다)"""
    o = e["own"]
    e["life"] -= dt
    if o["hp"] <= 0 or e["life"] <= 0:
        e["hp"] = 0
        return False
    e["lk"] = math.atan2(uy, ux)
    e["stt"] -= dt
    if e["st"] == "idle":
        if d < 55:
            vx, vy, sp = -ux, -uy, 36
        else:
            vx, vy, sp = -uy * e["sg"], ux * e["sg"], 24
        move(e, vx * sp * dt, vy * sp * dt, g["solid"])
        if e["stt"] <= 0:
            e["st"], e["stt"] = "aim", 1.0
        return True
    if e["stt"] > 0.3:
        e["lz"] = e["lk"]
    if e["stt"] <= 0:
        shoot(g, e["x"], e["y"], e["lz"], 200, 1, 1.8)
        play("shoot")
        e["st"], e["stt"], e["sg"] = "idle", random.uniform(1.8, 3.0), random.choice((-1, 1))
    return False


def gaia_ai(g, e, dt, d, ux, uy):
    """덩굴 수호자 가이아: 씨앗 포탑 + 보호막 -> 제자리에서 회전하는 가시 채찍을 번갈아 쓴다."""
    e["stt"] -= dt
    st, half = e["st"], e["hp"] <= e["mhp"] / 2
    seeds = [o for o in g["en"] if o["kind"] == "seed" and o["own"] is e and o["hp"] > 0]
    if seeds and e["sc"] < 4:                               # 씨앗이 살아 있으면 보호막이 차오른다
        e["rg"] += dt
        if e["rg"] >= 2.5:
            e["rg"], e["sc"] = 0.0, e["sc"] + 1
            play("switch")
    if st == "idle":
        if d > 50:
            move(e, ux * 10 * dt, uy * 10 * dt, g["solid"])
        if e["stt"] <= 0:
            e["cyc"] += 1
            if e["cyc"] % 2 == 1:
                for _ in range(3 - len(seeds)):
                    x, y = free_spot(g, e["x"], e["y"], 40, 85, 5)
                    spark(g, x, y, (150, 230, 120), 8)
                    g["en"].append(mk_seed(e, x, y))
                if e["sc"] <= 0:
                    e["sc"] = 4
                e["st"], e["stt"] = "seed", 1.0
            else:
                e["st"], e["stt"], e["wd"], e["flip"], e["wl"] = "whip", 4.2, random.choice((-1, 1)), False, 0.0
            play("gate")
        return False
    if st == "seed":
        if e["stt"] <= 0:
            e["st"], e["stt"] = "idle", 1.4
        return False
    e["wa"] += e["wd"] * (3.2 if half else 2.2) * dt        # 가시 채찍
    el = 4.2 - e["stt"]
    e["wl"] = min(62.0, el * 110)
    if el > 2.1 and not e["flip"]:
        e["wd"], e["flip"] = -e["wd"], True
    arms = 3 if half else 2
    if g["iv"] <= 0:
        for i in range(arms):
            a = e["wa"] + i * 6.283 / arms
            if seg_dist(g["x"], g["y"], e["x"], e["y"], e["x"] + math.cos(a) * e["wl"], e["y"] + math.sin(a) * e["wl"]) < 6:
                hurt(g)
                break
    if e["stt"] <= 0:
        e["st"], e["stt"], e["wl"] = "idle", 1.6, 0.0
    return False


def seed_ai(g, e, dt, d, ux, uy):
    o = e["own"]
    if o["hp"] <= 0:
        e["hp"] = 0
        return False
    if e["gr"] < 1:
        e["gr"] = min(1.0, e["gr"] + dt)
        return False
    e["acd"] -= dt
    if e["acd"] <= 0 and d < 220:
        e["acd"] = random.uniform(2.0, 2.8)
        shoot(g, e["x"], e["y"], math.atan2(uy, ux), 85, 2, 3.5)
        play("shoot")
    return False


def nova_ai(g, e, dt, d, ux, uy):
    """고대 중력기계 노바: 유성 탄막 -> 끌어당기기 -> 유성 탄막 -> 밀어내기를 반복한다."""
    e["stt"] -= dt
    st, half = e["st"], e["hp"] <= e["mhp"] / 2
    if st == "idle":
        if d > 70:
            move(e, ux * 12 * dt, uy * 12 * dt, g["solid"])
        if e["stt"] <= 0:
            e["cyc"] += 1
            nxt = ("meteor", "pull", "meteor", "push")[(e["cyc"] - 1) % 4]
            e["st"] = nxt
            e["tot"] = e["stt"] = dict(meteor=3.6 if half else 3.0, pull=2.6, push=2.0)[nxt]
            e["mt"] = 0.0
            play("boss")
        return False
    if st == "meteor":
        e["mt"] -= dt
        if e["mt"] <= 0 and e["stt"] > 0.5:
            e["mt"] = 0.22 if half else 0.34
            e["mc"] += 1
            ox, oy = (0, 0) if e["mc"] % 3 == 0 else (random.uniform(-48, 48), random.uniform(-48, 48))
            g["met"].append([g["x"] + ox, g["y"] + oy, 0.9, 0.9, 20])
        if e["stt"] <= 0:
            e["st"], e["stt"] = "idle", 1.3
        return False
    if e["tot"] - e["stt"] > 0.5 and 8 < d < 170:           # 중력장: 처음 0.5초는 예고
        s = (-1 if st == "pull" else 1) * (55 if st == "pull" else 80) * dt
        move(g, ux * s, uy * s, g["solid"])
    if e["stt"] <= 0:
        if st == "pull":
            ring(g, e["x"], e["y"], 10, 70, random.random() * 6.283)
        e["st"], e["stt"] = "idle", 1.3
    return False


def mid_ai(g, e, dt, d, ux, uy):
    if not e["ag"]:
        e["st"] = "idle"
        e["stt"] = max(e["stt"], 1.0)
        return False
    e["lk"] = math.atan2(uy, ux)
    if e["inv"] > 0:
        e["inv"] -= dt
        return False
    if not e["ph2"] and e["hp"] <= e["mhp"] / 2 and g["spec"].get("arena"):      # 페이즈 2: 폭주
        e["ph2"], e["inv"] = True, 1.4
        e["st"], e["stt"], e["sc"] = "idle", 1.4, 0
        g["shots"], g["met"] = [], []
        g["rings"].append([e["x"], e["y"], 0.0, 110, (255, 90, 90)])
        spark(g, e["x"], e["y"] - 8, (255, 120, 100), 30)
        g["shake"] = 0.6
        toast(g, "수호 기계가 폭주한다!", 2.5)
        play("boss")
        return False
    return (oculus_ai, gaia_ai, nova_ai)[e["id"]](g, e, dt, d, ux, uy)


def check_exit(g):
    tx, ty = int(g["x"]) // T, int(g["y"]) // T
    for ex in g["exits"]:
        s = ex["side"]
        if ((s == "w" and g["x"] < T + 3 and ex["a"] <= ty <= ex["b"]) or
                (s == "e" and g["x"] > g["wt"] * T - T - 3 and ex["a"] <= ty <= ex["b"]) or
                (s == "n" and g["y"] < T + 3 and ex["a"] <= tx <= ex["b"]) or
                (s == "s" and g["y"] > g["ht"] * T - T - 3 and ex["a"] <= tx <= ex["b"])):
            return ex
    return None


def exit_center(g, ex):
    c = (ex["a"] + ex["b"] + 1) / 2 * T
    return {"w": (0, c), "e": (g["wt"] * T, c), "n": (c, 0), "s": (c, g["ht"] * T)}[ex["side"]]


def near_exit(g):
    for ex in g["exits"]:
        if dist(g["x"], g["y"], *exit_center(g, ex)) < 90:
            return ex
    return None


def start_travel(g, zid, tx, ty):
    g["tr"] = dict(t=0.0, to=zid, at=(tx, ty), done=False)
    g["booms"] = []
    g["ui"] = None


def update(g, inp, dt):
    dx, dy, space = inp
    if g["tr"]:                                                # 구역 이동 중 (암전)
        tr = g["tr"]
        tr["t"] += dt
        if tr["t"] >= 0.25 and not tr["done"]:
            tr["done"] = True
            load_zone(g, tr["to"], *tr["at"])
        if tr["t"] >= 0.5:
            g["tr"] = None
        return
    g["t"] += dt
    g["iv"], g["cd"] = max(0, g["iv"] - dt), max(0, g["cd"] - dt)
    g["pcd"], g["wcd"] = max(0, g["pcd"] - dt), max(0, g["wcd"] - dt)
    g["tcd"] = max(0, g["tcd"] - dt)
    g["toast"][1] = max(0, g["toast"][1] - dt)
    g["intro"], g["shake"], g["lvup"] = max(0.0, g["intro"] - dt), max(0.0, g["shake"] - dt), max(0.0, g["lvup"] - dt)
    n = math.hypot(dx, dy)
    g["moving"] = n > 0
    if n:                                                      # 8방향 이동
        dx, dy = dx / n, dy / n
        g["dx"], g["dy"], g["face"] = dx, dy, dirname(dx, dy)
        sp = 70 * (1 + 0.08 * g["lv"]["spd"])
        move(g, dx * sp * dt, dy * sp * dt, g["solid"])
        if g["lv"]["spd"] >= 1 and random.random() < 0.12 * g["lv"]["spd"]:          # 장화 강화: 달릴 때 남는 잔상
            g["parts"].append([g["x"], g["y"] + 4, -dx * 20, -dy * 20, 0.3, BOOT_C[g["lv"]["spd"]]])
    ex = check_exit(g)                                         # 길 끝(구역 출구)
    if ex and n:
        play("portal")
        toast(g, f"{ZONES[ex['to']]['name']}(으)로 이동")
        start_travel(g, ex["to"], *ex["at"])
        return
    lx, hx, ly, hy = T, g["wt"] * T - T, T, g["ht"] * T - T    # 보이지 않는 구역 경계
    if g["x"] < lx or g["x"] > hx or g["y"] < ly or g["y"] > hy:
        g["x"], g["y"] = min(max(g["x"], lx), hx), min(max(g["y"], ly), hy)
        if n and g["wcd"] <= 0:
            g["wcd"] = 1.5
            toast(g, "이 너머로는 갈 수 없다", 1.5)
            play("deny")
    for p in g["portals"]:                                     # 고대 전송문
        if g["pcd"] <= 0 and dist(g["x"], g["y"], p["x"], p["y"]) < 11:
            play("portal")
            toast(g, f"고대 전송문 - {ZONES[p['to']]['name']}")
            start_travel(g, p["to"], *p["at"])
            return
    reg = tile_reg(g, int(g["x"]) // T, int(g["y"]) // T)
    if reg != g["reg"]:
        g["reg"] = reg
        toast(g, REGIONS[reg]["name"])
        set_music(reg)
    vil = in_village(g, g["x"], g["y"])
    if vil and g["hp"] < g["mhp"]:
        g["regen"] += dt
        if g["regen"] >= 2:
            g["regen"], g["hp"] = 0, g["hp"] + 1

    if g["spec"].get("arena") and not g["lock"] and g["zid"] not in g["cleared"] and g["y"] < 22 * T:
        g["lock"], g["intro"] = True, 2.6                                         # 보스방 봉인 + 보스 등장 연출
        g["solid"] |= ARENA_DOOR
        g["shake"] = 0.5
        play("gate")
    t = pick_target(g)                                         # 자동조준(표시용) + Space로 발사
    g["aim"], g["tgt"] = t, (t[2] if t else None)
    cap = 2 if "twin" in g["act"] else 1                       # 쌍둥이: 공중에 최대 2개까지
    if len(g["booms"]) < cap and g["cd"] <= 0 and g["tcd"] <= 0 and space:
        if t:
            throw(g, t[0], t[1])
        else:
            throw(g, g["x"] + g["dx"], g["y"] + g["dy"])

    dmg, mx = derived(g)["atk"], MAXD * (1 + 0.15 * g["lv"]["rng"])
    pierce, ghost = "pierce" in g["act"], "ghost" in g["act"]
    boss = g["boss"]
    for b in g["booms"][:]:
        b["a"] += dt * 18
        if g["lv"]["atk"] >= 1 and random.random() < 0.3 + 0.1 * g["lv"]["atk"]:     # 날 강화: 부메랑이 빛나는 꼬리를 남긴다
            g["parts"].append([b["x"], b["y"], random.uniform(-10, 10), random.uniform(-10, 10), 0.25, BOOM_COL[g["lv"]["atk"]]])
        if b["out"]:
            b["x"] += b["dx"] * 200 * dt
            b["y"] += b["dy"] * 200 * dt
            b["d"] += 200 * dt
            if b["d"] >= mx:
                b["out"] = False
            hit_any = False
            for e in g["en"]:
                if id(e) not in b["hit"] and dist(b["x"], b["y"], e["x"], e["y"]) < e["r"]:
                    b["hit"].add(id(e))
                    hit_any = True
                    if not hit_foe(g, e, b, dmg):               # 방패·보호막에 막히면 부메랑도 되돌아간다
                        b["out"] = False
            if g["core"] and boss["hp"] > 0 and "core" not in b["hit"] and dist(b["x"], b["y"], *g["core"]) < 16:
                b["hit"].add("core")
                boss["hp"] -= dmg
                boss["fl"] = 0.12
                spark(g, b["x"], b["y"], (255, 240, 150))
                play("hit")
                hit_any = True
            for z in g["pz"]:
                for s in z["sw"]:
                    if not s["on"] and dist(b["x"], b["y"], s["x"], s["y"]) < 9:
                        hit_switch(g, z, s)
                        b["out"] = False
            for nd in g["nodes"]:
                if nd["alive"] and id(nd) not in b["hit"] and dist(b["x"], b["y"], nd["tx"] * T + 8, nd["ty"] * T + 8) < 10:
                    b["hit"].add(id(nd))
                    hit_node(g, nd)
                    b["out"] = False
            if hit_any and not pierce:
                b["out"] = False
            if b["out"] and not ghost and wall_at(g, b["x"], b["y"]):
                b["out"] = False
        else:
            ex_, ey_ = g["x"] - b["x"], g["y"] - b["y"]
            d = math.hypot(ex_, ey_)
            if d < 7:
                g["booms"].remove(b)
                play("catch")
                if not g["booms"]:
                    g["cd"] = max(0.05, 0.25 - 0.04 * g["lv"]["cdn"])
            else:
                b["x"] += ex_ / d * 240 * dt
                b["y"] += ey_ / d * 240 * dt

    lo_x, hi_x, lo_y, hi_y = T, g["wt"] * T - T, T, g["ht"] * T - T
    for e in g["en"]:                                          # 적 AI
        e["fl"] = max(0, e["fl"] - dt)
        e["al"] = max(0, e["al"] - dt)
        e["an"] += dt
        d = dist(g["x"], g["y"], e["x"], e["y"])
        if d > 360:
            e["mv"] = False
            continue
        k, was = e["kind"], e["ag"]
        if k == "mid" and g["spec"].get("arena"):
            e["ag"] = g["lock"] and g["intro"] <= 0
        elif k in ("illu", "seed"):
            e["ag"] = True
        elif vil:
            e["ag"] = False
        elif not e["ag"] and d < AGGRO[k]:
            e["ag"] = True
        elif e["ag"] and d > 220:
            e["ag"] = False
        if e["ag"] and not was:
            e["al"] = 0.6
        ux, uy = (g["x"] - e["x"]) / (d or 1), (g["y"] - e["y"]) / (d or 1)
        if e["kb"] > 0:
            e["kb"] -= dt
            move(e, e["kx"] * 110 * dt, e["ky"] * 110 * dt, g["solid"])
            e["mv"] = False
            if k in DROP:
                e["st"], e["acd"] = "idle", max(e["acd"], 0.7)
        elif k == "mid":
            e["mv"] = mid_ai(g, e, dt, d, ux, uy)
        elif k == "illu":
            e["mv"] = illu_ai(g, e, dt, d, ux, uy)
        elif k == "seed":
            e["mv"] = seed_ai(g, e, dt, d, ux, uy)
        else:
            e["mv"] = foe_ai(g, e, dt, d, ux, uy)
        e["x"], e["y"] = min(max(e["x"], lo_x), hi_x), min(max(e["y"], lo_y), hi_y)
        if d < e["r"] and g["iv"] <= 0 and not vil and k not in ("illu", "seed"):
            hurt(g)
    alive = []
    for e in g["en"]:
        if e["hp"] > 0:
            alive.append(e)
        else:
            kill(g, e)
    g["en"] = alive
    for r in g["rs"][:]:                                       # 몹 리젠 (플레이어가 멀리 있을 때)
        r[0] = max(0, r[0] - dt)
        if r[0] <= 0 and dist(g["x"], g["y"], r[1], r[2]) > 200:
            g["en"].append(mk_foe(r[3], r[1], r[2]))
            g["rs"].remove(r)

    for nd in g["nodes"]:                                      # 채집물 리젠
        if not nd["alive"]:
            nd["t"] -= dt
            if nd["t"] <= 0 and dist(g["x"], g["y"], nd["tx"] * T + 8, nd["ty"] * T + 8) > 24:
                nd["alive"], nd["hp"] = True, NODE[nd["kind"]][0]
                if nd["kind"] != "herb":
                    g["solid"].add((nd["tx"], nd["ty"]))
                    g["ntile"].add((nd["tx"], nd["ty"]))

    if g["keys"] >= 3 and not g["topen"]:
        g["topen"] = True
        g["solid"] -= g["tgate"]
        play("gate")
        toast(g, "열쇠 조각이 모였다! 중앙 사원의 문이 열렸다!")
    core = g["core"]
    if core and boss["hp"] > 0 and dist(g["x"], g["y"], *core) < 200:   # 최종 보스: 탄막 + 로봇 소환
        boss["fl"] = max(0, boss["fl"] - dt)
        boss["cd"] -= dt
        if boss["cd"] <= 0:
            boss["cd"] = 2.4 if boss["hp"] > boss["mhp"] / 2 else 1.5
            boss["rot"] += 0.3
            ring(g, core[0], core[1], 12, 60, boss["rot"])
        boss["sp"] -= dt
        if boss["sp"] <= 0:
            boss["sp"] = 5.0
            if len([e for e in g["en"] if dist(e["x"], e["y"], *core) < 170]) < 3:
                g["en"].append(mk_foe("bot", core[0] + random.choice((-30, 30)), core[1] + 26, True))
    if core and boss["hp"] <= 0 and g["mode"] == "play":
        g["mode"] = "ending"
        g["en"], g["shots"], g["met"] = [], [], []
        play("boss")
        spark(g, *core, (255, 220, 120), 30)

    for m in g["met"][:]:                                      # 노바의 유성: 예고 원 -> 낙하 -> 폭발
        m[2] -= dt
        if m[2] <= 0:
            g["met"].remove(m)
            g["rings"].append([m[0], m[1], 0.0, m[4] + 6, (255, 170, 80)])
            spark(g, m[0], m[1], (255, 170, 80), 10)
            play("boom")
            if dist(g["x"], g["y"], m[0], m[1]) < m[4] and g["iv"] <= 0 and not vil:
                hurt(g)
    for r in g["rings"]:
        r[2] += dt
    g["rings"] = [r for r in g["rings"] if r[2] < 0.35]

    for s in g["shots"][:]:                                    # 탄막
        s[0] += s[2] * dt
        s[1] += s[3] * dt
        s[4] -= dt
        if s[4] <= 0 or wall_at(g, s[0], s[1]):
            g["shots"].remove(s)
        elif dist(s[0], s[1], g["x"], g["y"]) < SHOT_R[s[5]] and g["iv"] <= 0 and not vil:
            hurt(g)
            g["shots"].remove(s)
    for p in g["parts"]:
        p[0] += p[2] * dt
        p[1] += p[3] * dt
        p[4] -= dt
    g["parts"] = [p for p in g["parts"] if p[4] > 0]
    for f in g["ft"]:
        f[2] -= 12 * dt
        f[3] -= dt
    g["ft"] = [f for f in g["ft"] if f[3] > 0]


# ---------------------------------------------------------------- 상점 / 대장간 / 마차
def shop_tabs(kind):
    return dict(smith=["제작"], shop=["구매", "판매"], cart=["이동"])[kind]


def shop_items(g, kind, tab):
    """항목 목록. label/desc/cost/gain/kind/key/done"""
    inv, out = g["inv"], []
    if kind == "smith":
        for key, label, cost in MODS:
            done = key in g["own"]
            out.append(dict(label=f"능력 제작: {label}" + (" (완료)" if done else ""),
                            desc=MOD_DESC[key] + (f"  [{MOD_KEYS[[m[0] for m in MODS].index(key)]} 키로 켜기/끄기]" if done else ""),
                            cost={} if done else cost, gain=0, kind="mod", key=key, done=done))
    elif kind == "cart":
        for zid in ZONE_ORDER:
            if zid not in g["seen"]:
                out.append(dict(label="???", desc="아직 가 본 적 없는 곳", cost={}, gain=0, kind="cart", key=zid, done=True))
            else:
                here = zid == g["zid"]
                out.append(dict(label=ZONES[zid]["name"] + ("  (현재 위치)" if here else ""),
                                desc=f"마차로 {CART_PRICE}G에 이동 (가 본 곳만 갈 수 있다)",
                                cost={} if here else dict(gold=CART_PRICE), gain=0, kind="cart", key=zid, done=here))
    elif tab == 0:
        out.append(dict(label=f"포션 (보유 {inv['potion']}/9)", desc="체력 3 회복, Q 키로 사용", cost=dict(gold=20),
                        gain=0, kind="potion", key="potion", done=False))
        for res, q, price in BUYMAT:
            out.append(dict(label=f"{NAMES[res]} {q}개", desc="강화·제작 재료가 부족할 때", cost=dict(gold=price),
                            gain=0, kind="give", key=(res, q), done=False))
    else:
        for res, price in SELL:
            out.append(dict(label=f"{NAMES[res]} 1개 판매 (보유 {inv[res]})", desc=f"개당 {price}G", cost={}, gain=price,
                            kind="sell1", key=res, done=False))
        tot = sum(inv[k] * v for k, v in SELL)
        out.append(dict(label="재료 전부 판매", desc="나무·돌·약초·철광석을 모두 판다", cost={}, gain=tot,
                        kind="sellall", key=None, done=False))
    return out


def buy(g, it):
    inv, k = g["inv"], it["kind"]

    def msg(s, ok=True):
        g["smsg"] = (s, ok)
        play("buy" if ok else "deny")
    if it["done"]:
        return msg("선택할 수 없는 항목이다", False)
    if k == "sell1":
        if inv[it["key"]] <= 0:
            return msg("팔 재료가 없다", False)
        inv[it["key"]] -= 1
        inv["gold"] += it["gain"]
        return msg(f"+{it['gain']}G")
    if k == "sellall":
        tot = sum(inv[r] * v for r, v in SELL)
        if not tot:
            return msg("팔 재료가 없다", False)
        for r, _ in SELL:
            inv[r] = 0
        inv["gold"] += tot
        return msg(f"재료를 팔아 {tot}G를 받았다")
    if not can_pay(g, it["cost"]):
        return msg("골드나 재료가 부족하다", False)
    if k == "potion" and inv["potion"] >= 9:
        return msg("포션은 최대 9개까지 들 수 있다", False)
    for r, v in it["cost"].items():
        inv[r] -= v
    if k == "cart":
        z = ZONES[it["key"]]
        cx, cy = next((tx, ty) for kk, tx, ty in z["npcs"] if kk == "cart")
        play("cart")
        toast(g, f"마차를 타고 {z['name']}(으)로 이동")
        start_travel(g, it["key"], cx, cy + 2)
        return
    if k == "potion":
        inv["potion"] += 1
    elif k == "give":
        inv[it["key"][0]] += it["key"][1]
    else:
        g["own"].add(it["key"])
        g["act"].add(it["key"])
    msg("구매 완료!" if k != "mod" else f"능력 부메랑 완성! {MOD_KEYS}키로 켜고 끌 수 있다")


# ---------------------------------------------------------------- 강화: 모루에서 장비를 고르고 직접 단련
def enh_cost(g, key):
    base = next(c for k, _, _, c in ENH if k == key)
    n = g["lv"][key] + 1
    return {k: v * n for k, v in base.items()}


def forge_bonus(f):
    """타이밍 보너스: 좋음 +4%, 완벽 +3% 추가, 세 번 모두 성공하면 +5%"""
    return 0.04 * f["good"] + 0.03 * f["perfect"] + (0.05 if f["good"] == 3 else 0.0)


def new_forge(cur=0):
    return dict(stage="select", cur=cur, key=None, lv0=0, cost={}, paid=False, n=0, good=0, perfect=0, combo=0, hits=[],
                pos=0.5, dir=1, spd=1.05, zc=0.5, zw=0.24, lock=0.0, t=0.0, sw=0.0, shake=0.0, amp=2, heat=0.1,
                heat_t=0.1, sp=[], pop=[], rg=[], flash=0.0, stop=0.0, rt=0.0, res=None, rate=1.0, msg="",
                before="", after="", xp=0)


def open_forge(g):
    g["ui"], g["forge"] = "bench", new_forge()
    play("ui")


def choose_forge(g):
    f = g["forge"]
    key = ENH[f["cur"]][0]
    if g["lv"][key] >= ENH_MAX:
        f["msg"] = "이미 최대 강화다"
        play("deny")
        return
    cur = f["cur"]
    f.update(new_forge(cur), stage="ready", key=key, lv0=g["lv"][key], cost=enh_cost(g, key))
    play("ui")


def forge_zone(f):
    """다음 내리치기의 성공 구간(초록)과 표식 속도 - 갈수록 좁고 빨라진다"""
    f["zw"] = (0.26, 0.2, 0.15)[min(2, f["n"])]
    f["zc"] = random.uniform(0.28, 0.72)
    f["spd"] = 1.05 + 0.45 * f["n"]


def start_forge(g):
    f = g["forge"]
    if not can_pay(g, f["cost"]):
        f["msg"] = "재료가 부족하다"
        play("deny")
        return
    for r, v in f["cost"].items():
        g["inv"][r] -= v
    f.update(stage="strike", paid=True, msg="", heat_t=0.35)
    forge_zone(f)
    play("ui")


def strike_forge(g):
    f = g["forge"]
    d = abs(f["pos"] - f["zc"])
    perfect, good = d <= f["zw"] * 0.17, d <= f["zw"] / 2
    grade = 2 if perfect else 1 if good else 0
    f["hits"].append(grade)
    f["good"] += int(good)
    f["perfect"] += int(perfect)
    f["combo"] = f["combo"] + 1 if good else 0
    f["n"] += 1
    f["sw"], f["lock"], f["amp"] = 0.33, 0.6, 3 if perfect else 2
    f["shake"] = 0.3 if perfect else 0.18
    f["stop"] = 0.13 if perfect else 0.07 if good else 0.0       # 히트스톱: 맞는 순간 화면이 멈칫한다
    f["flash"] = 0.3 if perfect else 0.12 if good else 0.0
    f["heat_t"] = 0.35 + 0.2 * f["n"]
    f["rg"].append([0.0, grade])
    play("anvilp" if perfect else "anvilg" if good else "clang")
    for _ in range((44, 24, 8)[2 - grade]):
        a, v = random.uniform(-math.pi, 0), random.uniform(40, (170, 130, 70)[2 - grade])
        f["sp"].append([random.uniform(-8, 8), -31.0, math.cos(a) * v, math.sin(a) * v, random.uniform(0.35, 0.8)])
    f["pop"].append([("빗나감...", "좋음!", "완벽!!")[grade], random.randint(-6, 6), -46.0, 0.9,
                     (MUTED, GREEN, GOLD)[grade]])
    if f["combo"] >= 2:
        f["pop"].append([f"콤보 x{f['combo']}", 0, -58.0, 1.0, CYAN])


def finish_forge(g):
    f = g["forge"]
    key, lv = f["key"], f["lv0"]
    f["rate"] = rate = min(1.0, ENH_RATE[lv] + forge_bonus(f))
    f["stage"], f["rt"] = "result", 0.0
    if random.random() <= rate:
        g["lv"][key] += 1
        set_mhp(g)
        f["res"], f["heat_t"] = "ok", 1.3
        f["before"], f["after"] = stat_line(g, key, lv), stat_line(g, key, lv + 1)
        f["xp"] = 12 * (lv + 1)
        g["shake"] = 0.3
        play("up")
        play("quench")
        f["rg"] += [[0.0, 2], [-0.12, 2], [-0.24, 1]]
        f["sp"] += [[random.uniform(-10, 10), -31.0, random.uniform(-110, 110), random.uniform(-190, -30),
                     random.uniform(0.6, 1.2)] for _ in range(50)]
    else:
        f["res"], f["heat_t"], f["xp"] = "fail", 0.05, 5
        play("fail")
    gain_exp(g, f["xp"], g["x"], g["y"] - 18)


def update_forge(g, dt):
    f = g["forge"]
    if not f:
        return
    f["t"] += dt
    f["flash"] = max(0.0, f["flash"] - dt)
    if f["stop"] > 0:                                          # 히트스톱 중에는 모든 것이 멈춘다
        f["stop"] -= dt
        return
    f["sw"] = max(0.0, f["sw"] - dt)
    f["shake"] = max(0.0, f["shake"] - dt)
    f["heat"] += (f["heat_t"] - f["heat"]) * min(1.0, dt * 4)
    if f["stage"] == "result":
        f["rt"] += dt
    if f["stage"] == "strike":
        if f["lock"] > 0:
            f["lock"] -= dt
            if f["lock"] <= 0:
                f["lock"] = 0.0
                if f["n"] >= 3:
                    finish_forge(g)
                else:
                    forge_zone(f)
        else:
            f["pos"] += f["dir"] * f["spd"] * dt
            if f["pos"] >= 1.0:
                f["pos"], f["dir"] = 1.0, -1
            elif f["pos"] <= 0.0:
                f["pos"], f["dir"] = 0.0, 1
    for s in f["sp"]:
        s[0] += s[2] * dt
        s[1] += s[3] * dt
        s[3] += 260 * dt
        s[4] -= dt
    f["sp"] = [s for s in f["sp"] if s[4] > 0]
    for p in f["pop"]:
        p[2] -= 14 * dt
        p[3] -= dt
    f["pop"] = [p for p in f["pop"] if p[3] > 0]
    for r in f["rg"]:
        r[0] += dt
    f["rg"] = [r for r in f["rg"] if r[0] < 0.45]


def forge_key(g, k):
    f = g["forge"]
    ok = k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE)
    up, down = k in (pygame.K_UP, pygame.K_w), k in (pygame.K_DOWN, pygame.K_s)
    if f["stage"] == "select":
        if up or down:
            f["cur"], f["msg"] = (f["cur"] + (1 if down else -1)) % len(ENH), ""
            play("ui")
        elif pygame.K_1 <= k <= pygame.K_5:
            f["cur"], f["msg"] = k - pygame.K_1, ""
        elif ok:
            choose_forge(g)
        elif k == pygame.K_e:
            g["ui"], g["forge"] = None, None
    elif f["stage"] == "ready":
        if ok:
            start_forge(g)
        elif k in (pygame.K_e, pygame.K_a, pygame.K_LEFT, pygame.K_BACKSPACE):
            g["forge"] = new_forge(f["cur"])                   # 다른 장비 고르기
            play("ui")
    elif f["stage"] == "strike":
        if ok and f["lock"] <= 0:
            strike_forge(g)
    elif f["rt"] > 0.5:                                        # 결과 확인 후 계속 단련하거나 닫는다
        if ok:
            g["forge"] = new_forge(f["cur"])
            play("ui")
        elif k == pygame.K_e:
            g["ui"], g["forge"] = None, None
    return g


def near_npc(g):
    for k, tx, ty in g["npcs"]:
        if dist(g["x"], g["y"], tx * T + 8, ty * T + 8) < 28:
            return k, NPC_LABEL[k]
    return None


def use_potion(g):
    if g["inv"]["potion"] > 0 and g["hp"] < g["mhp"]:
        g["inv"]["potion"] -= 1
        g["hp"] = min(g["mhp"], g["hp"] + 3)
        play("potion")
        ftext(g, "+3 HP", g["x"], g["y"] - 14, (255, 130, 130))


def toggle_mod(g, i):
    key = MODS[i][0]
    if key not in g["own"]:
        toast(g, "아직 제작하지 않은 능력이다 (대장간)")
        play("deny")
    elif key in g["act"]:
        g["act"].discard(key)
        play("ui")
    else:
        g["act"].add(key)
        play("ui")


# ---------------------------------------------------------------- 그리기 (월드)
def camera(g):
    return (min(max(int(g["x"]) - W // 2, 0), g["wt"] * T - W), min(max(int(g["y"]) - H // 2, 0), g["ht"] * T - H))


def draw_reticle(surf, g, cx, cy):
    """조준 표시: 색은 대상 종류(적=붉은색, 스위치=노랑, 핵=주황, 채집물=연두), 모서리는 숨 쉬듯 움직인다"""
    a = g["aim"]
    if not a:
        return
    x, y, cat = a[0] - cx, a[1] - cy, a[3]
    col = {"e": (255, 90, 90), "s": (255, 230, 120), "c": (255, 150, 60), "n": (200, 255, 160)}[cat]
    r = 10 + int(2 * math.sin(g["t"] * 8)) + (6 if cat == "c" else 0)
    for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        px, py = x + sx * r, y + sy * r
        pygame.draw.line(surf, col, (px, py), (px - sx * 4, py), 1)
        pygame.draw.line(surf, col, (px, py), (px, py - sy * 4), 1)
    surf.fill((255, 255, 255), (int(x) - 1, int(y) - r - 5, 2, 2))        # 머리 위 작은 표식
    ox, oy = g["x"] - cx, g["y"] - cy
    d = dist(ox, oy, x, y)
    for i in range(1, int(d // 8)):
        surf.fill(col, (int(ox + (x - ox) * i * 8 / d), int(oy + (y - oy) * i * 8 / d), 1, 1))


def draw_node(surf, n, px, py, reg):
    k = n["kind"]
    if k in ("tree", "rock", "ore"):
        surf.blit(SHADOW, (px + 2, py + 11))
    if k == "tree":
        leaf = REGIONS[reg]["leaf"]
        v = hsh(n["tx"], n["ty"]) % 3
        leaf = adj(leaf, (v - 1) * 12)
        surf.fill((120, 82, 56), (px + 6, py + 8, 4, 7))
        pygame.draw.circle(surf, leaf, (px + 8, py + 6), 7 if v else 6)
        pygame.draw.circle(surf, adj(leaf, 38), (px + 6, py + 4), 3)
    elif k == "rock":
        pygame.draw.polygon(surf, (150, 152, 165), [(px + 2, py + 14), (px + 4, py + 6), (px + 10, py + 3), (px + 14, py + 8), (px + 14, py + 14)])
        surf.fill((190, 192, 205), (px + 6, py + 6, 3, 2))
    elif k == "ore":
        pygame.draw.polygon(surf, (84, 86, 110), [(px + 2, py + 14), (px + 3, py + 6), (px + 9, py + 2), (px + 14, py + 7), (px + 14, py + 14)])
        for ox, oy in ((5, 7), (9, 9), (7, 12)):
            surf.fill((120, 230, 240), (px + ox, py + oy, 2, 2))
    else:
        for ox, oy in ((4, 9), (8, 7), (11, 10)):
            pygame.draw.circle(surf, (70, 170, 90), (px + ox, py + oy + 2), 3)
        surf.fill((250, 150, 190), (px + 8, py + 6, 2, 2))


def draw_ground(surf, g, tx, ty, px, py, r, t):
    ter, h, vil = g["ter"][ty][tx], hsh(tx, ty), g["vil"]
    if (tx, ty) in g["water"]:
        col = lerp_c((70, 134, 204), r["floor"], 0.12)
        surf.fill(col, (px, py, T, T))
        if (tx * 3 + ty * 5 + int(t * 1.5)) % 6 == 0:
            surf.fill(adj(col, 40), (px + 3 + h % 5, py + 5 + h % 6, 5, 1))
        if (tx * 5 + ty * 3 + int(t * 1.5) + 3) % 9 == 0:
            surf.fill(adj(col, 28), (px + 8, py + 11, 4, 1))
        return
    invil = bool(vil) and inrect(tx, ty, vil)
    if invil:
        base = (214, 196, 150) if g["shade"][ty][tx] > 0.5 else (206, 188, 142)
    elif ter == 2:
        base = lerp_c(r["floor"], (238, 224, 178), 0.78)
    elif ter == 3:
        base = lerp_c(r["floor"], (196, 166, 118), 0.85)
    elif ter == 4:
        base = lerp_c(r["floor"], (186, 182, 198), 0.6)
    elif ter == 5:
        base = lerp_c(r["floor"], (28, 64, 40), 0.55)
    elif ter == 7:
        base = (156, 112, 74)
    else:
        base = r["floor"] if g["shade"][ty][tx] > 0.5 else r["floor2"]
    col = adj(base, (h % 5 - 2) * 2)
    surf.fill(col, (px, py, T, T))
    if ter == 0 and not invil:
        if g["shade"][ty][tx] > 0.64 and h % 3 != 1:           # 키 큰 풀 (야생 느낌)
            for k in range(3):
                bx = px + 3 + (h >> k) % 10
                surf.fill(adj(col, -34 + k * 8), (bx, py + 4 + (h >> (k + 2)) % 5, 1, 7))
        elif h % 7 == 0:
            surf.fill(adj(col, -26), (px + 4, py + 8, 1, 3))
            surf.fill(adj(col, -18), (px + 6, py + 6, 1, 4))
            surf.fill(adj(col, 16), (px + 9, py + 9, 1, 2))
        elif h % 41 == 0:
            surf.fill(((250, 240, 150), (250, 150, 190), (255, 255, 255))[h % 3], (px + 7, py + 8, 2, 2))
        elif h % 53 == 0:                                      # 버섯
            surf.fill((235, 235, 225), (px + 7, py + 10, 2, 3))
            surf.fill((220, 70, 70), (px + 6, py + 8, 4, 2))
    elif ter == 3 and h % 4 == 0:
        surf.fill(adj(col, -30), (px + 3 + h % 8, py + 4 + h % 7, 2, 1))
    elif ter == 4:
        surf.fill(adj(col, -22), (px, py + 7, T, 1))
        surf.fill(adj(col, -22), (px + 7, py, 1, T))
        if h % 3 == 0:
            surf.fill(adj(col, -34), (px + 2 + h % 9, py + 10, 3, 1))
        if h % 5 == 0:                                         # 고대 문명의 룬: 은은하게 맥동하는 청록빛
            rc = lerp_c(col, (120, 232, 232), 0.4 + 0.4 * math.sin(t * 2 + h))
            surf.fill(rc, (px + 7, py + 4, 2, 3))
            surf.fill(rc, (px + 7, py + 9, 2, 3))
            surf.fill(rc, (px + 4, py + 7, 3, 2))
            surf.fill(rc, (px + 9, py + 7, 3, 2))
    elif ter == 5:                                             # 빽빽한 덤불
        for k in range(2):
            bx, by = px + 4 + (h >> k) % 8, py + 4 + (h >> (k + 3)) % 8
            pygame.draw.circle(surf, adj(col, -14 + k * 10), (bx, by), 4)
            surf.fill(adj(col, 22), (bx - 1, by - 2, 2, 1))
    elif ter == 7:                                             # 나무 다리
        for k in range(0, T, 4):
            surf.fill(adj(col, -34), (px, py + k, T, 1))


def draw_exit(surf, g, ex, cx, cy, t):
    c, wt, ht = (ex["a"] + ex["b"] + 1) / 2 * T, g["wt"], g["ht"]
    off, s = (t * 16) % 12, ex["side"]
    for k in range(3):
        d = 26 + k * 12 - off
        if s == "w":
            x, y, pts = d, c, [(d + 4, c - 5), (d, c), (d + 4, c + 5)]
        elif s == "e":
            x, y = wt * T - d, c
            pts = [(x - 4, y - 5), (x, y), (x - 4, y + 5)]
        elif s == "n":
            x, y, pts = c, d, [(c - 5, d + 4), (c, d), (c + 5, d + 4)]
        else:
            x, y = c, ht * T - d
            pts = [(x - 5, y - 4), (x, y), (x + 5, y - 4)]
        pygame.draw.lines(surf, (255, 240, 150), False, [(px - cx, py - cy) for px, py in pts], 2)


def draw_portal(surf, p, cx, cy, t):
    x, y = int(p["x"]) - cx, int(p["y"]) - cy
    boss = p.get("boss")
    surf.blit(SHADOW, (x - 6, y + 8))
    pygame.draw.circle(surf, (130, 70, 70) if boss else (96, 84, 130), (x, y), 12)
    pygame.draw.circle(surf, (40, 30, 70), (x, y), 9)
    r = 6 + int(1.5 * math.sin(t * 4))
    pygame.draw.circle(surf, (255, 120, 100) if boss else (120, 210, 255), (x, y), r)
    pygame.draw.circle(surf, (255, 235, 220) if boss else (230, 250, 255), (x, y), max(1, r - 4))
    for i in range(4):
        a = t * 3 + i * 1.5708
        surf.fill((255, 255, 255), (x + int(math.cos(a) * 11), y + int(math.sin(a) * 11), 2, 2))


# ---- 중간보스 그리기
def draw_oculus(surf, e, x, y, alpha=255):
    """떠 있는 거대한 눈. 눈동자는 플레이어를 쫓고, 조준 중에는 붉게 번쩍인다"""
    s = pygame.Surface((48, 48), pygame.SRCALPHA)
    fl = e["fl"] > 0
    cx_, cy_ = 24, 26 + round(math.sin(e["an"] * 2.5) * 1.5)
    for i in range(4):                                         # 궤도를 도는 황동 장갑판
        a = e["an"] * 1.2 + i * 1.5708
        s.fill((214, 170, 86), (int(cx_ + math.cos(a) * 16) - 1, int(cy_ + math.sin(a) * 11) - 1, 3, 3))
    pygame.draw.circle(s, (255, 255, 255) if fl else (238, 238, 248), (cx_, cy_), 10)
    pygame.draw.circle(s, (60, 66, 96), (cx_, cy_), 10, 1)
    pygame.draw.line(s, (232, 150, 150), (cx_ - 9, cy_ - 2), (cx_ - 5, cy_ - 1))
    pygame.draw.line(s, (232, 150, 150), (cx_ + 9, cy_ + 3), (cx_ + 5, cy_ + 2))
    ix, iy = int(cx_ + math.cos(e["lk"]) * 4), int(cy_ + math.sin(e["lk"]) * 4)
    aiming = e["st"] in ("aim", "fire") and int(e["an"] * 14) % 2
    pygame.draw.circle(s, (255, 80, 80) if aiming else (90, 170, 230), (ix, iy), 5)
    pygame.draw.circle(s, (24, 20, 36), (ix, iy), 2)
    s.fill((255, 255, 255), (ix - 2, iy - 3, 1, 1))
    s.set_alpha(alpha)
    surf.blit(s, (x - 24, y - 36))


def draw_gaia(surf, e, x, y):
    t, fl = e["an"], e["fl"] > 0
    by = y - 8
    pygame.draw.circle(surf, (40, 90, 56), (x, by), 13)
    pygame.draw.circle(surf, (255, 255, 255) if fl else (70, 140, 80), (x, by), 11)
    for i in range(8):                                         # 잎사귀 꽃잎
        a = i * 0.785 + t * 0.3
        pygame.draw.circle(surf, (110, 190, 100), (int(x + math.cos(a) * 13), int(by + math.sin(a) * 13)), 3)
    pygame.draw.circle(surf, (250, 170, 200), (x, by), 5)
    pygame.draw.circle(surf, (255, 230, 120), (x, by), 2)
    surf.fill((24, 20, 36), (x - 6, by - 4, 2, 2))
    surf.fill((24, 20, 36), (x + 4, by - 4, 2, 2))
    if e["st"] == "whip" and e["wl"] > 0:                      # 회전하는 가시 채찍
        arms = 3 if e["hp"] <= e["mhp"] / 2 else 2
        for i in range(arms):
            a = e["wa"] + i * 6.283 / arms
            ca, sa = math.cos(a), math.sin(a)
            pts = []
            for j in range(5):
                f = j / 4 * e["wl"]
                w = math.sin(j * 1.3 + t * 8) * 2
                pts.append((x + ca * f - sa * w, by + sa * f + ca * w))
            pygame.draw.lines(surf, (86, 168, 72), False, pts, 2)
            for px_, py_ in pts[1:]:
                surf.fill((240, 240, 150), (int(px_ - sa * 2), int(py_ + ca * 2), 1, 1))
                surf.fill((240, 240, 150), (int(px_ + sa * 2), int(py_ - ca * 2), 1, 1))
            pygame.draw.circle(surf, (230, 90, 120), (int(pts[-1][0]), int(pts[-1][1])), 3)
    if e["sc"] > 0:                                            # 보호막
        s = pygame.Surface((46, 46), pygame.SRCALPHA)
        pygame.draw.circle(s, (120, 240, 220, 60), (23, 23), 19)
        pygame.draw.circle(s, (170, 255, 240, 170), (23, 23), 19, 1)
        surf.blit(s, (x - 23, by - 23))
        for i in range(e["sc"]):
            a = t * 1.5 + i * 1.5708
            pygame.draw.circle(surf, (210, 255, 245), (int(x + math.cos(a) * 19), int(by + math.sin(a) * 19)), 2)


def draw_nova(surf, e, x, y):
    t, fl = e["an"], e["fl"] > 0
    cy_ = y - 10 + round(math.sin(t * 2) * 1.5)
    if e["st"] in ("pull", "push"):                            # 중력장: 안으로 모이거나 밖으로 퍼지는 고리
        ph = (t * 0.9) % 1
        for i in range(4):
            f = (i / 4 + ph) % 1
            rr = int(150 * ((1 - f) if e["st"] == "pull" else f))
            if rr > 6:
                pygame.draw.circle(surf, (150, 100, 230), (x, cy_), rr, 1)
    pygame.draw.ellipse(surf, (150, 120, 220), (x - 16, cy_ - 5, 32, 10), 1)
    w = int(abs(math.cos(t)) * 26) + 4
    pygame.draw.ellipse(surf, (150, 120, 220), (x - w // 2, cy_ - 14, w, 28), 1)
    pygame.draw.circle(surf, (30, 18, 56), (x, cy_), 10)
    pygame.draw.circle(surf, (255, 255, 255) if fl else (70, 40, 120), (x, cy_), 8)
    pygame.draw.circle(surf, (170, 120, 255), (x, cy_), 4)
    surf.fill((255, 255, 255), (x - 1, cy_ - 1, 2, 2))
    for i in range(3):
        a = t * 2 + i * 2.094
        pygame.draw.circle(surf, (200, 180, 255), (int(x + math.cos(a) * 16), int(cy_ + math.sin(a) * 9)), 2)
    if e["st"] == "meteor":                                    # 유성을 부르는 중: 머리 위에 붉은 빛
        pygame.draw.circle(surf, (255, 120, 90), (x, cy_ - 16), 2 + int(abs(math.sin(t * 10)) * 2))


def draw_enemy(surf, e, cx, cy, t, g):
    x, y = int(e["x"]) - cx, int(e["y"]) - cy
    k, st = e["kind"], e["st"]
    if k in SPR:                                               # 일반 적
        fr = int(e["an"] * 8) % 2 if e["mv"] else 0
        by = -fr if e["mv"] else round(math.sin(e["an"] * 3.5))
        ox, img = 0, SPR[k][fr]
        if st in ("wind", "fuse", "aim"):
            ox = (int(e["an"] * 50) % 2 * 2 - 1) if st == "wind" else 0
            if int(e["an"] * 14) % 2:
                img = SPR_R[k][fr]
        elif st in ("dash", "slam"):
            surf.blit(SPR_R[k][1], (x - 5 - int(e["lx"] * 6), y - 6 - int(e["ly"] * 6)))
            img = SPR_R[k][1]
        if e["fl"] > 0:
            img = SPR_F[k][fr]
        surf.blit(SHADOW, (x - 6, y - 1))
        if k == "gunner" and st == "aim":                      # 포격 조준선
            for i in range(2, 14):
                if i % 2:
                    surf.fill((255, 90, 90), (x + int(e["lx"] * i * 7), y - 3 + int(e["ly"] * i * 7), 1, 1))
        surf.blit(img, (x - 5 + ox, y - 6 + by))
        if k == "guard":                                       # 방패: 올리면 정면을 막고, 내리면 약점이 드러난다
            fx, fy = e["fx"], e["fy"]
            if e["sh"]:
                cxs, cys = x + fx * 9, y - 2 + fy * 7
                p, q = -fy * 6, fx * 6
                pygame.draw.line(surf, (60, 66, 96), (cxs + p, cys + q), (cxs - p, cys - q), 4)
                pygame.draw.line(surf, (205, 215, 240), (cxs + p, cys + q), (cxs - p, cys - q), 2)
            else:
                pygame.draw.line(surf, (150, 156, 180), (x + 7, y + 1), (x + 9, y + 6), 2)
        if k == "bomber" and st == "fuse" and int(e["an"] * 14) % 2:
            pygame.draw.circle(surf, (255, 120, 60), (x, y - 2), 32, 1)
        if st in ("wind", "aim") or e["al"] > 0:
            surf.fill((255, 230, 80), (x - 1, y - 16, 2, 5))
            surf.fill((255, 230, 80), (x - 1, y - 10, 2, 2))
        return
    if k == "seed":
        gr = e["gr"]
        r = int(2 + 4 * gr)
        surf.blit(SHADOW, (x - 6, y - 1))
        surf.fill((60, 120, 60), (x - 1, y - 4 - int(4 * gr), 2, 5 + int(4 * gr)))
        col = (255, 255, 255) if e["fl"] > 0 else (250, 170, 200) if gr >= 1 and e["acd"] < 0.5 else (96, 180, 96)
        pygame.draw.circle(surf, col, (x, y - 5 - int(4 * gr)), r)
        pygame.draw.circle(surf, (44, 38, 60), (x, y - 5 - int(4 * gr)), r, 1)
        for i in range(4):
            a = i * 1.5708 + e["an"]
            surf.fill((240, 240, 150), (x + int(math.cos(a) * (r + 2)), y - 5 - int(4 * gr) + int(math.sin(a) * (r + 2)), 1, 1))
        return
    if k == "illu" or (k == "mid" and e["id"] == 0):           # 오큘러스(와 그 환영)
        if st == "aim":                                        # 레이저 조준선: 마지막 0.3초는 번쩍이며 고정
            ex2, ey2 = ray_end(g, e["x"], e["y"], e["lz"], 260)
            late = e["stt"] < 0.3
            col = (255, 255, 255) if late and int(e["an"] * 30) % 2 else (255, 70, 70)
            pygame.draw.line(surf, col, (x, y), (int(ex2) - cx, int(ey2) - cy), 2 if late else 1)
        surf.blit(pygame.transform.scale(SHADOW, (22, 7)), (x - 11, y + 1))
        draw_oculus(surf, e, x, y, 255 if k == "mid" else 120 + int(40 * math.sin(e["an"] * 9)))
        if k == "illu":
            return
    elif e["id"] == 1:
        surf.blit(pygame.transform.scale(SHADOW, (26, 8)), (x - 13, y + 1))
        draw_gaia(surf, e, x, y)
    else:
        surf.blit(pygame.transform.scale(SHADOW, (22, 7)), (x - 11, y + 1))
        draw_nova(surf, e, x, y)
    if e["ph2"]:                                               # 폭주 상태: 붉은 기운
        pygame.draw.circle(surf, (255, 80, 80), (x, y - 10), 20 + int(2 * math.sin(e["an"] * 10)), 1)
    if e["inv"] > 0 and int(e["an"] * 24) % 2:
        pygame.draw.circle(surf, (255, 255, 255), (x, y - 10), 17, 2)
    pygame.draw.rect(surf, PAL["k"], (x - 13, y - 34, 26, 4))
    pygame.draw.rect(surf, (235, 70, 70), (x - 12, y - 33, 24 * e["hp"] // e["mhp"], 2))
    if e["al"] > 0:
        surf.fill((255, 230, 80), (x - 1, y - 44, 2, 5))
        surf.fill((255, 230, 80), (x - 1, y - 38, 2, 2))


def draw_arena(surf, g, cx, cy):
    """보스방 바닥 문양과 화로 불꽃 (보스방마다 다른 분위기)"""
    kind = g["spec"].get("arena")
    if not kind:
        return
    t = g["t"]
    bx, by = 17 * T + 8 - cx, 11 * T + 8 - cy
    if kind == "eye":                                          # 관측자의 눈 문양
        col = (250, 224, 170)
        for r in (30, 62, 94):
            pygame.draw.circle(surf, col, (bx, by), r, 1)
        for i in range(16):
            a = i * 0.3927 + t * 0.15
            pygame.draw.line(surf, col, (bx + math.cos(a) * 30, by + math.sin(a) * 30),
                             (bx + math.cos(a) * 94, by + math.sin(a) * 94), 1)
        pygame.draw.circle(surf, (214, 170, 86), (bx, by), 7)
    elif kind == "grav":                                       # 중력장 문양: 안쪽으로 빨려드는 점
        for i in range(5):
            pygame.draw.circle(surf, (120, 110, 210), (bx, by), 24 + i * 22, 1)
        for i in range(12):
            a = i * 0.5236
            r = 110 - (t * 16 + i * 9) % 90
            pygame.draw.line(surf, (90, 84, 170), (bx + math.cos(a) * 24, by + math.sin(a) * 24),
                             (bx + math.cos(a) * 110, by + math.sin(a) * 110), 1)
            surf.fill((200, 190, 255), (int(bx + math.cos(a) * r), int(by + math.sin(a) * r), 2, 2))
    else:                                                      # 덩굴
        for d in g["deco"]:
            if d[0] == "vine":
                x, y, r = d[1] - cx, d[2] - cy, d[3]
                pygame.draw.circle(surf, (44, 100, 64), (x, y), r)
                pygame.draw.circle(surf, (70, 150, 86), (x - 1, y - 1), max(1, r - 3))
                if r > 6:
                    surf.fill((240, 150, 190), (x + 1, y, 2, 2))
    for d in g["deco"]:
        if d[0] == "brazier":
            x, y = d[1] * T + 8 - cx, d[2] * T + 2 - cy
            fl = int(math.sin(t * 12 + d[1]) * 2)
            pygame.draw.circle(surf, (255, 120, 50), (x, y - 3), 5 + fl)
            pygame.draw.circle(surf, (255, 200, 90), (x, y - 3), 3)
            surf.fill((255, 250, 200), (x - 1, y - 4, 2, 2))
            for i in range(2):
                surf.fill((255, 190, 90), (x + int(math.sin(t * 3 + i * 3) * 5), y - 8 - int((t * 14 + i * 6) % 10), 1, 1))


def draw(surf, g):
    cx, cy = camera(g)
    tx0, ty0 = cx // T, cy // T
    wt, ht = g["wt"], g["ht"]
    closed = set(g["tgate"]) if not g["topen"] else set()
    for z in g["pz"]:
        if not z["done"]:
            closed |= z["gate"]
    if g["lock"]:
        closed |= ARENA_DOOR
    sol, ntile, water = g["solid"], g["ntile"], g["water"]
    for ty in range(ty0, min(ty0 + H // T + 2, ht)):
        for tx in range(tx0, min(tx0 + W // T + 2, wt)):
            r = REGIONS[tile_reg(g, tx, ty)]
            px, py = tx * T - cx, ty * T - cy
            draw_ground(surf, g, tx, ty, px, py, r, g["t"])
            if (tx, ty) in g["houses"]:
                roof = g["houses"][(tx, ty)]
                surf.fill((190, 80, 70) if roof else (236, 224, 200), (px, py, T, T))
                surf.fill((140, 50, 50) if roof else (200, 188, 164), (px, py + 12, T, 4))
            elif (tx, ty) in sol and (tx, ty) not in ntile and (tx, ty) not in water:
                w = r["wall"]
                surf.fill(w, (px, py, T, T))
                surf.fill(tuple(c - 30 for c in w), (px, py + 12, T, 4))
                surf.fill(tuple(min(255, c + 25) for c in w), (px, py, T, 2))
                if hsh(tx, ty) % 4 == 0:
                    surf.fill((96, 150, 92), (px + 3, py + 2, 6, 2))
                    surf.fill((96, 150, 92), (px + 11, py + 8, 2, 3))
                elif hsh(tx, ty) % 6 == 1:                     # 벽에 새겨진 맥동하는 룬
                    rc = lerp_c(w, (120, 232, 232), 0.45 + 0.4 * math.sin(g["t"] * 2 + tx))
                    surf.fill(rc, (px + 7, py + 4, 2, 5))
                    surf.fill(rc, (px + 5, py + 6, 6, 1))
                if (tx, ty) in closed:
                    surf.fill((220, 180, 70) if (tx, ty) in g["tgate"] else (170, 130, 90), (px + 1, py + 1, T - 2, T - 1))
                    gc = (250, 240, 150)                       # 고대 기계 문의 톱니 문양
                    pygame.draw.circle(surf, gc, (px + 8, py + 8), 4, 1)
                    for ox, oy in ((0, -6), (0, 5), (-6, 0), (5, 0)):
                        surf.fill(gc, (px + 7 + ox, py + 7 + oy, 2, 2))
                    surf.fill(gc, (px + 7, py + 7, 2, 2))
    draw_arena(surf, g, cx, cy)
    for ex in g["exits"]:
        draw_exit(surf, g, ex, cx, cy, g["t"])
    for n in g["nodes"]:
        if n["alive"] and tx0 - 1 <= n["tx"] <= tx0 + W // T + 2 and ty0 - 1 <= n["ty"] <= ty0 + H // T + 2:
            draw_node(surf, n, n["tx"] * T - cx, n["ty"] * T - cy, tile_reg(g, n["tx"], n["ty"]))
    for p in g["portals"]:
        draw_portal(surf, p, cx, cy, g["t"])
    for z in g["pz"]:
        for s in z["sw"]:
            x, y = int(s["x"]) - cx, int(s["y"]) - cy
            surf.fill((150, 152, 165), (x - 5, y + 5, 11, 3))                      # 석제 받침
            surf.fill((104, 106, 124), (x - 5, y + 7, 11, 1))
            pc = (250, 220, 110) if s["on"] else (120, 170, 230)
            pygame.draw.circle(surf, lerp_c(pc, (24, 20, 36), 0.55), (x, y), 8 + int(1.5 * math.sin(g["t"] * 3 + s["idx"])), 1)   # 맥동하는 빛무리
            pts = [(x, y - 6), (x + 5, y), (x, y + 6), (x - 5, y)]
            pygame.draw.polygon(surf, pc, pts)
            pygame.draw.polygon(surf, PAL["k"], pts, 1)
            surf.fill((255, 255, 255), (x - 1, y - 3, 1, 2))
            if z["mode"] == "order":
                for i in range(s["idx"] + 1):
                    surf.fill((255, 255, 255), (x - s["idx"] - 1 + i * 3, y - 11, 2, 2))
    for k, tx, ty in g["npcs"]:
        if k == "cart":
            surf.blit(CART_IMG, (tx * T - 9 - cx, ty * T - 5 - cy))
        elif k == "bench":
            surf.blit(SHADOW, (tx * T + 2 - cx, ty * T + 11 - cy))
            surf.blit(BENCH_IMG, (tx * T - 2 - cx, ty * T - 3 - cy))
            for i in range(2):                                 # 모루 위로 피어오르는 불씨
                a_ = g["t"] * 2.2 + i * 3.1
                surf.fill((255, 170 + 40 * i, 70), (tx * T + 8 - cx + int(math.sin(a_) * 4), ty * T - 4 - cy - int((g["t"] * 12 + i * 6) % 12), 1, 1))
        else:
            surf.blit(SHADOW, (tx * T + 2 - cx, ty * T + 11 - cy))
            surf.blit(NPC_IMG[k], (tx * T + 3 - cx, ty * T - 2 - cy))
    if g["core"] and g["boss"]["hp"] > 0:
        x, y, b = g["core"][0] - cx, g["core"][1] - cy, g["boss"]
        pr = 14 + int(2 * math.sin(g["t"] * 4))
        for i in range(10):                                    # 회전하는 톱니 고리
            a = g["t"] * 0.8 + i * 0.6283
            pygame.draw.circle(surf, (170, 180, 195), (x + int(math.cos(a) * (pr + 6)), y + int(math.sin(a) * (pr + 6))), 2)
        pygame.draw.circle(surf, (110, 110, 130), (x, y), pr + 4)
        pygame.draw.circle(surf, (255, 255, 255) if b["fl"] > 0 else (235, 70, 70), (x, y), pr)
        pygame.draw.circle(surf, (255, 230, 120), (x, y), 5)
        pygame.draw.rect(surf, PAL["k"], (x - 17, y - 29, 34, 5))
        pygame.draw.rect(surf, (235, 70, 70), (x - 16, y - 28, 32 * b["hp"] // b["mhp"], 3))
    for m in g["met"]:                                         # 노바의 유성: 예고 원 + 낙하
        x, y = int(m[0]) - cx, int(m[1]) - cy
        p = 1 - m[2] / m[3]
        pygame.draw.circle(surf, (255, 90, 70), (x, y), m[4], 1)
        pygame.draw.circle(surf, (255, 150, 90), (x, y), max(1, int(m[4] * p)), 1)
        if m[2] < 0.3:
            fy = y - int(m[2] / 0.3 * 70)
            pygame.draw.line(surf, (255, 200, 120), (x, fy - 10), (x, fy), 2)
            pygame.draw.circle(surf, (255, 230, 160), (x, fy), 4)
    for r in g["rings"]:                                       # 폭발 충격파
        pygame.draw.circle(surf, r[4], (int(r[0]) - cx, int(r[1]) - cy), max(1, int(r[3] * r[2] / 0.35)), 2)
    for e in g["en"]:
        draw_enemy(surf, e, cx, cy, g["t"], g)
    if g["aim"] or g["booms"]:                                 # 사거리 강화가 눈에 보이도록 점선 사거리 원을 그린다
        rr, rc = MAXD * (1 + 0.15 * g["lv"]["rng"]), (190, 215, 245)
        for i in range(36 + 8 * g["lv"]["rng"]):
            a_ = i * 6.283 / (36 + 8 * g["lv"]["rng"])
            if i % 2:
                surf.fill(rc, (int(g["x"] - cx + math.cos(a_) * rr), int(g["y"] - cy + math.sin(a_) * rr), 1, 1))
    draw_reticle(surf, g, cx, cy)
    if not (g["iv"] > 0 and int(g["t"] * 20) % 2):
        frame_ = int(g["t"] * 8) % 2 if g["moving"] else 0
        bob = -1 if g["moving"] and frame_ else 0
        surf.blit(SHADOW, (int(g["x"]) - 6 - cx, int(g["y"]) + 1 - cy))
        if g["lv"]["hp"] >= 3:                                 # 갑옷 3단계부터 몸을 감싸는 기운
            pygame.draw.circle(surf, ARMOR_C[g["lv"]["hp"]], (int(g["x"]) - cx, int(g["y"]) - 4 - cy),
                               9 + int(math.sin(g["t"] * 5)), 1)
        surf.blit(player_set(g["lv"]["hp"], g["lv"]["spd"])[g["face"]][frame_], (int(g["x"]) - 5 - cx, int(g["y"]) - 10 + bob - cy))
    for b in g["booms"]:
        a, x, y, al = b["a"], b["x"] - cx, b["y"] - cy, g["lv"]["atk"]       # 날 강화: 더 크고 더 빛나는 부메랑
        ln, col = 5 + al, BOOM_COL[al]
        if al >= 4:
            pygame.draw.circle(surf, adj(col, -70), (int(x), int(y)), ln + 2, 1)
        pygame.draw.lines(surf, col, False, [(x + math.cos(a) * ln, y + math.sin(a) * ln), (x, y),
                                             (x + math.cos(a + 2) * ln, y + math.sin(a + 2) * ln)], 2 if al < 3 else 3)
    for s in g["shots"]:
        x, y, kd = int(s[0]) - cx, int(s[1]) - cy, s[5]
        if kd == 1:                                            # 청록 저격탄 (꼬리가 있다)
            pygame.draw.line(surf, (90, 220, 240), (x, y), (x - int(s[2] * 0.035), y - int(s[3] * 0.035)), 3)
            pygame.draw.line(surf, (255, 255, 255), (x, y), (x - int(s[2] * 0.02), y - int(s[3] * 0.02)), 1)
        elif kd == 2:                                          # 초록 씨앗
            pygame.draw.circle(surf, (44, 38, 60), (x, y), 4)
            pygame.draw.circle(surf, (140, 230, 110), (x, y), 3)
        elif kd == 3:                                          # 주황 포탄
            pygame.draw.circle(surf, (44, 38, 60), (x, y), 4)
            pygame.draw.circle(surf, (255, 170, 70), (x, y), 3)
            surf.fill((255, 240, 180), (x - 1, y - 1, 1, 1))
        else:
            pygame.draw.circle(surf, (255, 110, 90), (x, y), 2)
    for p in g["parts"]:
        surf.fill(p[5], (int(p[0]) - cx, int(p[1]) - cy, 2, 2))


# ---------------------------------------------------------------- UI: 고대 기계 문명의 황동 석판 테마
D = pygame.draw
INK, BRASS, BRASS_D, BRASS_L = (24, 20, 36), (214, 170, 86), (150, 108, 56), (250, 226, 150)
NAVY1, NAVY2, CYAN, CORAL = (26, 32, 58), (46, 58, 98), (120, 232, 232), (240, 108, 116)
CREAM, MUTED, GOLD, GREEN = (246, 238, 214), (150, 158, 182), (255, 226, 120), (150, 235, 150)
ICON_RES = dict(gold="coin", wood="wood", stone="stone", ore="ore", herb="herb", part="part", potion="potion")


def _ic_coin(s):
    D.circle(s, (170, 110, 30), (4, 4), 4)
    D.circle(s, (255, 214, 80), (4, 4), 3)
    s.fill((255, 246, 170), (2, 2, 2, 1))
    s.fill((200, 140, 40), (4, 3, 1, 3))


def _ic_heart(s):
    D.circle(s, (235, 70, 90), (2, 3), 2)
    D.circle(s, (235, 70, 90), (6, 3), 2)
    D.polygon(s, (235, 70, 90), [(0, 4), (8, 4), (4, 8)])
    s.fill((255, 170, 180), (1, 2, 2, 1))


def _ic_shard(s):
    D.polygon(s, CYAN, [(4, 0), (8, 4), (4, 8), (0, 4)])
    D.polygon(s, (60, 150, 190), [(4, 2), (6, 4), (4, 6), (2, 4)])
    s.fill((255, 255, 255), (3, 2, 1, 1))


def _ic_shard0(s):
    D.polygon(s, (80, 90, 124), [(4, 0), (8, 4), (4, 8), (0, 4)], 1)


def _ic_wood(s):
    D.rect(s, (150, 108, 70), (0, 2, 9, 5))
    D.rect(s, (96, 64, 44), (0, 6, 9, 1))
    D.ellipse(s, (226, 184, 126), (0, 1, 4, 7))
    D.ellipse(s, (170, 120, 76), (1, 3, 2, 3), 1)


def _ic_stone(s):
    D.polygon(s, (150, 152, 165), [(0, 8), (1, 3), (4, 0), (8, 3), (8, 8)])
    s.fill((210, 214, 226), (3, 2, 3, 1))
    s.fill((104, 106, 124), (1, 7, 7, 1))


def _ic_ore(s):
    D.polygon(s, (84, 86, 110), [(0, 8), (1, 3), (4, 0), (8, 3), (8, 8)])
    for x, y in ((2, 4), (5, 3), (4, 6)):
        s.fill(CYAN, (x, y, 2, 2))


def _ic_herb(s):
    D.ellipse(s, (70, 170, 90), (0, 1, 5, 6))
    D.ellipse(s, (110, 210, 120), (4, 0, 5, 6))
    D.line(s, (50, 120, 70), (4, 8), (4, 4))
    s.fill((250, 150, 190), (6, 6, 2, 2))


def _ic_part(s):
    for r in ((3, 0, 3, 2), (3, 7, 3, 2), (0, 3, 2, 3), (7, 3, 2, 3)):
        s.fill((150, 158, 176), r)
    D.circle(s, (180, 188, 206), (4, 4), 3)
    D.circle(s, (60, 66, 96), (4, 4), 1)


def _ic_potion(s):
    s.fill((230, 220, 200), (3, 0, 3, 2))
    s.fill((190, 150, 110), (3, 0, 3, 1))
    D.circle(s, (235, 70, 90), (4, 6), 3)
    s.fill((255, 170, 180), (2, 5, 1, 2))


def _ic_boom(s):
    D.lines(s, (255, 214, 80), False, [(0, 2), (4, 7), (8, 2)], 2)
    D.lines(s, (255, 246, 170), False, [(0, 1), (4, 6), (8, 1)], 1)


def _ic_pierce(s):
    s.fill((130, 134, 160), (3, 0, 2, 9))
    D.line(s, CYAN, (0, 4), (6, 4))
    D.polygon(s, CYAN, [(5, 1), (8, 4), (5, 7)])


def _ic_twin(s):
    D.lines(s, (255, 214, 80), False, [(0, 0), (3, 3), (7, 0)], 2)
    D.lines(s, (255, 214, 80), False, [(1, 5), (4, 8), (8, 5)], 2)


def _ic_ghost(s):
    D.ellipse(s, (225, 232, 255), (1, 0, 7, 6))
    s.fill((225, 232, 255), (1, 3, 7, 5))
    for x in (2, 4, 6):
        s.fill((0, 0, 0, 0), (x, 7, 1, 2))
    s.fill(INK, (3, 3, 1, 2))
    s.fill(INK, (6, 3, 1, 2))


def _ic_range(s):
    D.circle(s, CYAN, (4, 4), 4, 1)
    D.circle(s, CYAN, (4, 4), 2, 1)
    s.fill((255, 255, 255), (4, 4, 1, 1))


def _ic_boot(s):
    s.fill((150, 108, 70), (2, 0, 3, 6))
    s.fill((150, 108, 70), (2, 5, 6, 3))
    s.fill((200, 150, 96), (2, 0, 1, 6))
    s.fill((96, 64, 44), (2, 7, 6, 1))


def _ic_pin(s):
    D.polygon(s, CORAL, [(1, 4), (7, 4), (4, 8)])
    D.circle(s, CORAL, (4, 3), 3)
    D.circle(s, (255, 230, 230), (4, 3), 1)


ICON_FN = dict(coin=_ic_coin, heart=_ic_heart, shard=_ic_shard, shard0=_ic_shard0, wood=_ic_wood, stone=_ic_stone,
               ore=_ic_ore, herb=_ic_herb, part=_ic_part, potion=_ic_potion, boom=_ic_boom, pierce=_ic_pierce,
               twin=_ic_twin, ghost=_ic_ghost, range=_ic_range, boot=_ic_boot, pin=_ic_pin)
_ICB, _ICS, _FONTS, _VIG = {}, {}, {}, {}


def icon(name, k=1, dim=False):
    """9x9 픽셀 아이콘을 k배(정수) 확대. dim이면 흐리게."""
    key = (name, k, dim)
    if key not in _ICS:
        if name not in _ICB:
            b = pygame.Surface((9, 9), pygame.SRCALPHA)
            ICON_FN[name](b)
            _ICB[name] = b
        s = pygame.transform.scale(_ICB[name], (9 * k, 9 * k))
        if dim:
            s.set_alpha(80)
        _ICS[key] = s
    return _ICS[key]


def bigfont(u):
    if u not in _FONTS:
        _FONTS[u] = load_font(int(8.5 * u))
    return _FONTS[u]


def txt(screen, font, s, x, y, col=(255, 255, 255), center=False, u=2):
    img = font.render(s, True, col)
    sh = font.render(s, True, INK)
    x = x - img.get_width() // 2 if center else x
    o = max(1, u // 2)
    screen.blit(sh, (x + o, y + o))
    screen.blit(img, (x, y))
    return img.get_width()


def title_txt(screen, font, s, cx, y, u, col=BRASS_L):
    img, sh = font.render(s, True, col), font.render(s, True, INK)
    x = cx - img.get_width() // 2
    for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1), (1, 1)):
        screen.blit(sh, (x + ox * u, y + oy * u))
    screen.blit(img, (x, y))


def diamond(s, cx, cy, r, col):
    D.polygon(s, col, [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)])


def frame(s, x, y, w, h, u):
    """황동 테두리 + 남색 그라데이션 + 모서리 장식의 큰 패널"""
    D.rect(s, (10, 8, 20), (x + u, y + 2 * u, w, h))
    for i, c in enumerate((INK, BRASS_D, BRASS, BRASS_D, INK)):
        D.rect(s, c, (x + i * u, y + i * u, w - 2 * i * u, h - 2 * i * u))
    n = (h - 10 * u) // u
    for i in range(n):
        D.rect(s, lerp_c(NAVY2, NAVY1, i / max(1, n - 1)), (x + 5 * u, y + (5 + i) * u, w - 10 * u, u))
    D.rect(s, BRASS_L, (x + 2 * u, y + 2 * u, w - 4 * u, u))
    for cx, cy in ((x, y), (x + w - 5 * u, y), (x, y + h - 5 * u), (x + w - 5 * u, y + h - 5 * u)):
        D.rect(s, INK, (cx, cy, 5 * u, 5 * u))
        D.rect(s, BRASS_L, (cx + u, cy + u, 3 * u, 3 * u))
        D.rect(s, BRASS_D, (cx + 2 * u, cy + 2 * u, u, u))


def plate(s, x, y, w, h, u, a=210):
    """HUD용 얇은 반투명 석판"""
    D.rect(s, INK, (x, y, w, h), u)
    D.rect(s, BRASS, (x + u, y + u, w - 2 * u, h - 2 * u), u)
    D.rect(s, INK, (x + 2 * u, y + 2 * u, w - 4 * u, h - 4 * u), u)
    v = pygame.Surface((w - 6 * u, h - 6 * u), pygame.SRCALPHA)
    v.fill(NAVY1 + (a,))
    s.blit(v, (x + 3 * u, y + 3 * u))


def ribbon(screen, f2, text, cx, y, u):
    """패널 윗변에 걸치는 황동 리본 제목"""
    tw = f2.size(text)[0]
    w, h = tw + 30 * u, 15 * u
    x = cx - w // 2
    D.rect(screen, INK, (x, y, w, h))
    D.rect(screen, BRASS_D, (x + u, y + u, w - 2 * u, h - 2 * u))
    D.rect(screen, BRASS, (x + 2 * u, y + 2 * u, w - 4 * u, h - 4 * u))
    D.rect(screen, BRASS_L, (x + 2 * u, y + 2 * u, w - 4 * u, u))
    for dx in (x + 7 * u, x + w - 7 * u):
        diamond(screen, dx, y + h // 2, 2 * u, INK)
    ty = y + (h - f2.get_height()) // 2
    screen.blit(f2.render(text, True, BRASS_L), (cx - tw // 2, ty + u))
    screen.blit(f2.render(text, True, INK), (cx - tw // 2, ty))


def slot(s, x, y, size, u, on=False, name=None, dim=False, k=None):
    """아이콘 칸. on이면 청록빛 테두리로 강조."""
    w = size * u
    if on:
        D.rect(s, (60, 150, 170), (x - u, y - u, w + 2 * u, w + 2 * u), u)
    D.rect(s, INK, (x, y, w, w))
    D.rect(s, CYAN if on else (70, 72, 96) if dim else BRASS_D, (x + u, y + u, w - 2 * u, w - 2 * u), u)
    n = size - 4
    for i in range(n):
        D.rect(s, lerp_c(NAVY2, NAVY1, i / max(1, n - 1)), (x + 2 * u, y + (2 + i) * u, w - 4 * u, u))
    if name:
        ic = icon(name, k or u, dim)
        s.blit(ic, (x + (w - ic.get_width()) // 2, y + (w - ic.get_height()) // 2))


def hp_bar(s, g, x, y, u):
    """체력 1칸 = 하트 1개, 칸 단위로 채워지는 석판 게이지"""
    n = g["mhp"]
    w = (n * 7 + 3) * u
    D.rect(s, INK, (x, y, w, 10 * u))
    D.rect(s, BRASS, (x + u, y + u, w - 2 * u, 8 * u))
    D.rect(s, (46, 22, 38), (x + 2 * u, y + 2 * u, w - 4 * u, 6 * u))
    for i in range(n):
        cx = x + (2 + i * 7) * u
        if i < max(0, g["hp"]):
            D.rect(s, (235, 80, 100), (cx, y + 2 * u, 6 * u, 6 * u))
            D.rect(s, (255, 160, 170), (cx, y + 2 * u, 6 * u, 2 * u))
            D.rect(s, (170, 40, 70), (cx, y + 6 * u, 6 * u, 2 * u))
        else:
            D.rect(s, (66, 36, 58), (cx, y + 3 * u, 6 * u, 4 * u))
    return w


def chips(screen, font, items, right, y, u):
    """[(아이콘, 글자, 색)] 목록을 오른쪽 정렬로 그린다"""
    for name, s, col in reversed(items):
        right -= font.size(s)[0]
        txt(screen, font, s, right, y, col, u=u)
        right -= 11 * u
        screen.blit(icon(name, u), (right, y))
        right -= 4 * u
    return right


def vignette(u):
    """화면 가장자리를 살짝 어둡게 해 신비로운 분위기를 낸다"""
    if u not in _VIG:
        sw, sh = W // 4, H // 4
        v = pygame.Surface((sw, sh), pygame.SRCALPHA)
        for y in range(sh):
            for x in range(sw):
                d = math.hypot((x / sw - 0.5) * 1.25, (y / sh - 0.5) * 1.5)
                v.set_at((x, y), (10, 8, 24, int(max(0, min(1, (d - 0.38) / 0.45)) * 120)))
        _VIG[u] = pygame.transform.smoothscale(v, (W * u, H * u))
    return _VIG[u]


def target_name(a):
    cat, o = a[3], a[2]
    if cat == "e":
        return MID_NAMES[o["id"]].split(" (")[0] if o["kind"] == "mid" else FOE_NAME[o["kind"]]
    if cat == "s":
        return "수정 스위치"
    if cat == "c":
        return "관리 기계의 핵"
    return {"tree": "나무", "rock": "바위", "ore": "철광석", "herb": "약초"}.get(o.get("kind"), "")


def hud(screen, font, g, u):
    inv, SW, SH = g["inv"], W * u, H * u
    w = hp_bar(screen, g, 18 * u, 5 * u, u)                    # 체력
    D.circle(screen, INK, (11 * u, 10 * u), 9 * u)
    D.circle(screen, BRASS, (11 * u, 10 * u), 8 * u)
    D.circle(screen, INK, (11 * u, 10 * u), 6 * u)
    D.circle(screen, (70, 34, 58), (11 * u, 10 * u), 5 * u)
    screen.blit(icon("heart", u), (7 * u, 6 * u))
    txt(screen, font, f"{max(0, g['hp'])}/{g['mhp']}", 18 * u + w + 4 * u, 6 * u, CREAM, u=u)
    txt(screen, font, f"Lv.{g['lvl']}", 5 * u, 20 * u, (140, 200, 255), u=u)                # 레벨 / 경험치
    xw = 44 * u
    D.rect(screen, INK, (30 * u, 23 * u, xw, 5 * u))
    need = need_xp(g["lvl"])
    D.rect(screen, (70, 130, 230), (30 * u + u, 24 * u, (xw - 2 * u) * (g["xp"] if g["lvl"] < LV_MAX else need) // need, 3 * u))
    plate(screen, 4 * u, 31 * u, 62 * u, 25 * u, u)             # 골드 / 열쇠 조각
    screen.blit(icon("coin", u), (9 * u, 34 * u))
    txt(screen, font, str(inv["gold"]), 21 * u, 33 * u, GOLD, u=u)
    for i in range(3):
        screen.blit(icon("shard" if i < g["keys"] else "shard0", u), (9 * u + i * 11 * u, 44 * u))
    txt(screen, font, f"{g['keys']}/3", 45 * u, 43 * u, CREAM if g["keys"] else MUTED, u=u)
    plate(screen, SW - 52 * u, 4 * u, 48 * u, 56 * u, u)        # 재료
    for i, k in enumerate(("wood", "stone", "ore", "herb", "part")):
        screen.blit(icon(k, u), (SW - 47 * u, (8 + i * 10) * u))
        s = str(inv[k])
        txt(screen, font, s, SW - 9 * u - font.size(s)[0], (8 + i * 10) * u, CREAM if inv[k] else MUTED, u=u)
    name = REGIONS[g["reg"]]["name"]                           # 지역 이름판
    pw = font.size(name)[0] + 20 * u
    plate(screen, (SW - pw) // 2, 3 * u, pw, 12 * u, u)
    txt(screen, font, name, SW // 2, 4 * u, GOLD, True, u)
    diamond(screen, (SW - pw) // 2 + 6 * u, 9 * u, 2 * u, BRASS)
    diamond(screen, (SW + pw) // 2 - 6 * u, 9 * u, 2 * u, BRASS)
    if g["toast"][1] > 0 and g["toast"][0] != name:            # 알림
        tw = font.size(g["toast"][0])[0] + 20 * u
        plate(screen, (SW - tw) // 2, 17 * u, tw, 12 * u, u, 235)
        txt(screen, font, g["toast"][0], SW // 2, 18 * u, (255, 240, 170), True, u)
    mb = next((e for e in g["en"] if e["kind"] == "mid" and e["ag"] and e["hp"] > 0), None)
    if mb:                                                     # 중간보스 체력바 (50%에서 페이즈 표시)
        bw = 150 * u
        x0 = (SW - bw) // 2
        plate(screen, x0 - 8 * u, 31 * u, bw + 16 * u, 22 * u, u)
        txt(screen, font, MID_NAMES[mb["id"]] + ("  - 폭주" if mb["ph2"] else ""), SW // 2, 32 * u,
            (255, 120, 110) if mb["ph2"] else CORAL, True, u)
        D.rect(screen, INK, (x0, 43 * u, bw, 7 * u))
        D.rect(screen, (235, 70, 70) if not mb["ph2"] else (255, 120, 60), (x0 + u, 44 * u, (bw - 2 * u) * mb["hp"] // mb["mhp"], 5 * u))
        D.rect(screen, INK, (x0 + bw // 2 - u // 2, 43 * u, max(1, u), 7 * u))
    if g["intro"] > 0:                                         # 보스 등장 연출
        mbi = next((e for e in g["en"] if e["kind"] == "mid"), None)
        if mbi:
            a = max(0.0, min(1.0, g["intro"] / 0.5, (2.6 - g["intro"]) / 0.4))
            band = pygame.Surface((SW, 44 * u), pygame.SRCALPHA)
            band.fill((14, 8, 24, int(215 * a)))
            screen.blit(band, (0, 82 * u))
            if a > 0.3:
                title_txt(screen, bigfont(u), MID_NAMES[mbi["id"]], SW // 2, 88 * u, u, (255, 150, 130))
                txt(screen, font, BOSS_SUB[mbi["id"]], SW // 2, 106 * u, CREAM, True, u)
    if g["lvup"] > 0:                                          # 레벨 업 연출
        title_txt(screen, bigfont(u), f"LEVEL UP!  Lv.{g['lvl']}", SW // 2, (64 - int(10 * (1 - min(1.0, g["lvup"] / 2.4)))) * u, u, (150, 210, 255))
    sx0 = (W - 84) // 2 * u                                    # 핫바: 포션 + 능력 부메랑 3종
    sy = (H - 44) * u
    for i, (nm, key) in enumerate((("potion", "Q"),) + tuple((m[0], MOD_KEYS[j]) for j, m in enumerate(MODS))):
        x = sx0 + i * 22 * u
        mod = i > 0
        owned, on = (nm in g["own"], nm in g["act"]) if mod else (inv["potion"] > 0, False)
        slot(screen, x, sy, 18, u, on=on, name=nm, dim=not owned)
        if not mod:
            s = str(inv["potion"])
            txt(screen, font, s, x + 17 * u - font.size(s)[0], sy + 10 * u, CREAM if owned else MUTED, u=u)
        txt(screen, font, key, x + 9 * u, sy + 19 * u, GOLD if on else MUTED, True, u)
    npc, a, ex = near_npc(g), g["aim"], near_exit(g)
    if npc and npc[0] == "bench":
        hint = "[E] 모루에서 강화하기"
    elif npc:
        hint = f"[E] {npc[1]} 이용하기"
    elif a:
        hint = f"[Space] 부메랑 발사  ·  조준: {target_name(a)}"
    elif ex:
        hint = f"길을 따라 이동 → {ZONES[ex['to']]['name']}"
    else:
        hint = "[Space] 부메랑 발사 (바라보는 방향)"
    hw = font.size(hint)[0] + 18 * u
    plate(screen, (SW - hw) // 2, SH - 13 * u, hw, 11 * u, u)
    txt(screen, font, hint, SW // 2, SH - 12 * u, CREAM, True, u)


def item_icon(it):
    k, key = it["kind"], it["key"]
    if k == "mod":
        return key
    if k == "potion":
        return "potion"
    if k == "give":
        return key[0]
    if k == "sell1":
        return key
    return "coin" if k == "sellall" else "pin"


def draw_shop(screen, font, g, u):
    SW, SH = W * u, H * u
    kind, tab, cur = g["ui"], g["tab"], g["cur"]
    items, tabs, inv = shop_items(g, kind, tab), shop_tabs(kind), g["inv"]
    f2, rh = bigfont(u), 14 * u
    pw, ph = int(SW * 0.9), (31 + len(items) * 14 + 43) * u
    px, py = (SW - pw) // 2, max(10 * u, (SH - ph) // 2)
    frame(screen, px, py, pw, ph, u)
    ribbon(screen, f2, NPC_LABEL[kind], px + pw // 2, py - 6 * u, u)
    gs = str(inv["gold"])
    gw = font.size(gs)[0]
    txt(screen, font, gs, px + pw - 10 * u - gw, py + 10 * u, GOLD, u=u)
    screen.blit(icon("coin", u), (px + pw - 22 * u - gw, py + 10 * u))
    x = px + 10 * u
    for i, name in enumerate(tabs):                            # 탭 버튼
        tw = font.size(name)[0] + 14 * u
        on = i == tab
        D.rect(screen, INK, (x, py + 17 * u, tw, 11 * u))
        D.rect(screen, BRASS if on else NAVY2, (x + u, py + 18 * u, tw - 2 * u, 9 * u))
        screen.blit(font.render(name, True, INK if on else MUTED), (x + (tw - font.size(name)[0]) // 2, py + 18 * u))
        x += tw + 4 * u
    y0 = py + 31 * u
    for i, it in enumerate(items):
        ry = y0 + i * rh
        if i == cur:
            D.rect(screen, (58, 78, 128), (px + 7 * u, ry, pw - 14 * u, rh - u))
            D.rect(screen, CYAN, (px + 7 * u, ry, pw - 14 * u, rh - u), u)
        slot(screen, px + 10 * u, ry + u, 12, u, on=(i == cur), name=item_icon(it), dim=it["done"] and it["kind"] != "mod")
        txt(screen, font, it["label"], px + 26 * u, ry + 3 * u, MUTED if it["done"] else CREAM, u=u)
        lst = [(ICON_RES[k], str(v), GREEN if inv[k] >= v else CORAL) for k, v in it["cost"].items()]
        if it["gain"]:
            lst.append(("coin", f"+{it['gain']}", GOLD))
        chips(screen, font, lst, px + pw - 12 * u, ry + 3 * u, u)
    fy = y0 + len(items) * rh + 3 * u
    sel = items[min(cur, len(items) - 1)]
    D.rect(screen, INK, (px + 8 * u, fy, pw - 16 * u, 11 * u))
    D.rect(screen, (34, 42, 74), (px + 9 * u, fy + u, pw - 18 * u, 9 * u))
    txt(screen, font, sel["desc"], px + 12 * u, fy + 2 * u, (200, 206, 226), u=u)
    m, ok = g["smsg"]
    if m:
        txt(screen, font, m, px + 12 * u, fy + 13 * u, GREEN if ok else CORAL, u=u)
    x = px + 12 * u                                            # 보유 재료
    for k in ("wood", "stone", "ore", "herb", "part"):
        screen.blit(icon(k, u), (x, fy + 24 * u))
        x += 11 * u
        s = str(inv[k])
        x += txt(screen, font, s, x, fy + 24 * u, CREAM if inv[k] else MUTED, u=u) + 7 * u
    hp_ = "W/S 선택  ·  A/D 탭  ·  Enter 확인  ·  E 닫기"
    txt(screen, font, hp_, px + pw - 12 * u - font.size(hp_)[0], fy + 24 * u, MUTED, u=u)


def draw_inventory(screen, font, g, u):
    SW, SH = W * u, H * u
    inv, L, f2 = g["inv"], g["lv"], bigfont(u)
    pw, ph = int(SW * 0.8), 200 * u
    px, py = (SW - pw) // 2, (SH - ph) // 2
    frame(screen, px, py, pw, ph, u)
    ribbon(screen, f2, "인벤토리", px + pw // 2, py - 6 * u, u)
    txt(screen, font, "I · ESC 닫기", px + pw - 12 * u - font.size("I · ESC 닫기")[0], py + 9 * u, MUTED, u=u)
    mats = ("wood", "stone", "ore", "herb", "part", "potion")
    for i, k in enumerate(mats):                               # 재료 칸
        x = px + 16 * u + i * 40 * u
        slot(screen, x, py + 18 * u, 24, u, name=k, k=2 * u, dim=inv[k] == 0)
        s = str(inv[k])
        txt(screen, font, s, x + 22 * u - font.size(s)[0], py + 31 * u, CREAM if inv[k] else MUTED, u=u)
        txt(screen, font, NAMES[k], x + 12 * u, py + 44 * u, MUTED, True, u)
    D.rect(screen, BRASS_D, (px + 12 * u, py + 57 * u, pw - 24 * u, u))
    txt(screen, font, "능력 부메랑", px + 14 * u, py + 60 * u, GOLD, u=u)
    cw = (pw - 28 * u) // 3
    for i, (key, label, cost) in enumerate(MODS):              # 능력 카드
        x = px + 14 * u + i * cw
        own, on = key in g["own"], key in g["act"]
        plate(screen, x, py + 71 * u, cw - 4 * u, 32 * u, u)
        slot(screen, x + 5 * u, py + 76 * u, 22, u, on=on, name=key, k=2 * u, dim=not own)
        txt(screen, font, label, x + 31 * u, py + 76 * u, CREAM if own else MUTED, u=u)
        st, sc = ("켜짐", CYAN) if on else ("꺼짐", MUTED) if own else ("미제작", CORAL)
        txt(screen, font, st, x + 31 * u, py + 86 * u, sc, u=u)
        txt(screen, font, f"[{MOD_KEYS[i]}]", x + cw - 10 * u - font.size(f"[{MOD_KEYS[i]}]")[0], py + 76 * u, GOLD, u=u)
    D.rect(screen, BRASS_D, (px + 12 * u, py + 108 * u, pw - 24 * u, u))
    txt(screen, font, "성장", px + 14 * u, py + 111 * u, GOLD, u=u)                           # 레벨 / 경험치
    lvl, need = g["lvl"], need_xp(g["lvl"])
    txt(screen, font, f"Lv.{lvl}", px + 14 * u, py + 122 * u, (140, 200, 255), u=u)
    bx, bw = px + 46 * u, pw - 150 * u
    D.rect(screen, INK, (bx, py + 123 * u, bw, 7 * u))
    D.rect(screen, (70, 130, 230), (bx + u, py + 124 * u, (bw - 2 * u) * (g["xp"] if lvl < LV_MAX else need) // need, 5 * u))
    xt = f"{g['xp']} / {need} EXP" if lvl < LV_MAX else "MAX"
    txt(screen, font, xt, bx + bw + 6 * u, py + 122 * u, CREAM, u=u)
    txt(screen, font, f"레벨 보너스: 최대 체력 +{lvl // 3}  ·  피해 +{(lvl - 1) // 4}", px + 14 * u, py + 134 * u, MUTED, u=u)
    D.rect(screen, BRASS_D, (px + 12 * u, py + 146 * u, pw - 24 * u, u))
    txt(screen, font, "강화 현황", px + 14 * u, py + 149 * u, GOLD, u=u)
    hint = "마을의 모루 작업대에서 강화"
    txt(screen, font, hint, px + pw - 14 * u - font.size(hint)[0], py + 149 * u, MUTED, u=u)
    cw5 = (pw - 28 * u) // 5
    for i, (key, label, desc, base) in enumerate(ENH):
        x = px + 14 * u + i * cw5
        x0 = x + (cw5 - 16 * u) // 2
        slot(screen, x0, py + 159 * u, 16, u, on=L[key] >= ENH_MAX, name=ENH_ICON[key], dim=L[key] == 0)
        lvs = "MAX" if L[key] >= ENH_MAX else f"+{L[key]}"
        txt(screen, font, lvs, x0 + 15 * u - font.size(lvs)[0], py + 166 * u, GOLD if L[key] else MUTED, u=u)
        txt(screen, font, label, x + cw5 // 2, py + 177 * u, CREAM if L[key] else MUTED, True, u)
        txt(screen, font, stat_line(g, key, L[key]), x + cw5 // 2, py + 187 * u, GREEN if L[key] else MUTED, True, u)


def draw_forge(screen, font, g, u):
    """모루 단련 화면: 장비 선택 -> 달궈진 금속 -> 타이밍 망치질(히트스톱, 불꽃, 충격파) -> 결과 연출"""
    f = g["forge"]
    if not f:
        return
    SW, SH = W * u, H * u
    f2, inv, st = bigfont(u), g["inv"], f["stage"]
    pw, ph = int(SW * 0.76), 200 * u
    px, py = (SW - pw) // 2, (SH - ph) // 2
    veil = pygame.Surface((SW, SH), pygame.SRCALPHA)
    veil.fill((28, 10, 4, 170))
    screen.blit(veil, (0, 0))
    frame(screen, px, py, pw, ph, u)
    ribbon(screen, f2, "모루 단련", px + pw // 2, py - 6 * u, u)
    lx = px + 12 * u
    if st == "select":                                         # 왼쪽: 어떤 강화를 할지 고른다
        for i, (key, label, desc, base) in enumerate(ENH):
            ry, n = py + 14 * u + i * 19 * u, g["lv"][key]
            cur = i == f["cur"]
            if cur:
                D.rect(screen, (58, 78, 128), (px + 8 * u, ry, 138 * u, 18 * u))
                D.rect(screen, CYAN, (px + 8 * u, ry, 138 * u, 18 * u), u)
            slot(screen, lx, ry + u, 16, u, on=cur, name=ENH_ICON[key], dim=n >= ENH_MAX)
            txt(screen, font, label, lx + 20 * u, ry + 2 * u, CREAM if cur else MUTED, u=u)
            s = "MAX" if n >= ENH_MAX else f"+{n}"
            txt(screen, font, s, lx + 128 * u - font.size(s)[0], ry + 2 * u, GOLD if n else MUTED, u=u)
            for j in range(ENH_MAX):
                D.rect(screen, GOLD if j < n else (60, 64, 92), (lx + (20 + j * 6) * u, ry + 11 * u, 5 * u, 3 * u))
        key, label, desc, base = ENH[f["cur"]]
        n = g["lv"][key]
        txt(screen, font, desc, lx, py + 112 * u, (200, 206, 226), u=u)
        if n < ENH_MAX:
            w_ = txt(screen, font, stat_line(g, key, n) + " → ", lx, py + 122 * u, CREAM, u=u)
            txt(screen, font, stat_line(g, key, n + 1), lx + w_, py + 122 * u, GREEN, u=u)
            txt(screen, font, "재료", lx, py + 132 * u, MUTED, u=u)
            chips(screen, font, [(ICON_RES[k], str(v), GREEN if inv[k] >= v else CORAL) for k, v in enh_cost(g, key).items()],
                  lx + 132 * u, py + 132 * u, u)
            txt(screen, font, f"기본 성공 {int(ENH_RATE[n] * 100)}%  ·  타이밍 보너스", lx, py + 142 * u, MUTED, u=u)
        else:
            txt(screen, font, "더 이상 강화할 수 없다", lx, py + 122 * u, MUTED, u=u)
    else:                                                      # 왼쪽: 단련 중인 장비 정보
        key, lv0 = f["key"], f["lv0"]
        label = next(l for k, l, _, _ in ENH if k == key)
        slot(screen, lx, py + 14 * u, 24, u, on=True, name=ENH_ICON[key], k=2 * u)
        txt(screen, font, label, lx + 30 * u, py + 18 * u, CREAM, u=u)
        stxt = f"+{lv0} 달성" if f["res"] == "ok" else f"+{lv0} 유지" if f["res"] == "fail" else f"+{lv0} → +{lv0 + 1}"
        txt(screen, font, stxt, lx + 30 * u, py + 29 * u, GOLD, u=u)
        rate = min(1.0, ENH_RATE[lv0] + forge_bonus(f))
        txt(screen, font, f"성공률 {int(rate * 100)}%", lx, py + 48 * u, CYAN, u=u)
        txt(screen, font, f"(타이밍 +{int(forge_bonus(f) * 100)}%)", lx, py + 59 * u, GREEN, u=u)
        txt(screen, font, "필요 재료", lx, py + 78 * u, MUTED, u=u)
        for i, (k, v) in enumerate(f["cost"].items()):
            col = CREAM if f["paid"] else (GREEN if inv[k] >= v else CORAL)
            screen.blit(icon(ICON_RES[k], u), (lx, py + (89 + i * 11) * u))
            txt(screen, font, f"{NAMES[k]} {v}", lx + 12 * u, py + (89 + i * 11) * u, col, u=u)

    sx, sy, sw_, sh_ = px + 150 * u, py + 14 * u, pw - 162 * u, 130 * u      # 오른쪽: 모루 장면
    D.rect(screen, INK, (sx - u, sy - u, sw_ + 2 * u, sh_ + 2 * u))
    D.rect(screen, (26, 18, 26), (sx, sy, sw_, sh_))
    screen.set_clip((sx, sy, sw_, sh_))
    shake = f["shake"] > 0
    amp = f["amp"] if shake else 0
    ox = random.randint(-amp, amp) * u if shake else 0
    oy = random.randint(0, amp) * u if shake else 0
    acx, by = sx + sw_ // 2 + ox, sy + sh_ - 26 * u + oy
    heat = max(0.0, min(1.3, f["heat"]))
    glow = pygame.Surface((sw_, sh_), pygame.SRCALPHA)         # 화로 불빛
    for i in range(5, -1, -1):
        D.circle(glow, (255, 120 + i * 10, 40, int((10 + 16 * min(1.0, heat)) * (6 - i))),
                 (acx - sx, by - 31 * u - sy), (22 + i * 11) * u)
    screen.blit(glow, (sx, sy))
    D.rect(screen, (46, 36, 40), (sx, by + 14 * u, sw_, sh_))
    D.rect(screen, (96, 64, 44), (acx - 18 * u, by, 36 * u, 14 * u))                      # 그루터기
    D.rect(screen, (136, 96, 62), (acx - 18 * u, by, 36 * u, 2 * u))
    D.rect(screen, (90, 94, 116), (acx - 20 * u, by - 8 * u, 40 * u, 8 * u))              # 모루
    D.rect(screen, (76, 80, 102), (acx - 12 * u, by - 18 * u, 24 * u, 10 * u))
    D.polygon(screen, (124, 128, 150), [(acx - 24 * u, by - 26 * u), (acx - 42 * u, by - 22 * u), (acx - 24 * u, by - 18 * u)])
    D.rect(screen, (124, 128, 150), (acx - 24 * u, by - 26 * u, 48 * u, 8 * u))
    D.rect(screen, (176, 180, 202), (acx - 24 * u, by - 26 * u, 48 * u, 2 * u))
    ic = lerp_c((150, 152, 172), (255, 150, 50), min(1.0, heat))                          # 달궈지는 금속
    if heat > 1.0:
        ic = lerp_c(ic, (255, 240, 180), min(1.0, (heat - 1.0) / 0.3))
    flat = 1 + f["n"] * 0 if st != "strike" else 1
    D.rect(screen, ic, (acx - 12 * u, by - 31 * u, 24 * u, 5 * u))
    D.rect(screen, adj(ic, 40), (acx - 12 * u, by - 31 * u, 24 * u, u))
    if st == "result" and f["res"] == "ok":                    # 성공: 빛줄기와 떠오르는 장비
        for i in range(12):
            a_ = f["rt"] * 0.8 + i * 0.5236
            ln = (34 + 20 * math.sin(f["rt"] * 6 + i)) * u
            D.line(screen, (255, 236, 150), (acx + math.cos(a_) * 10 * u, by - 28 * u + math.sin(a_) * 4 * u),
                   (acx + math.cos(a_) * ln, by - 28 * u + math.sin(a_) * ln * 0.8), u)
        bob = int(math.sin(f["rt"] * 4) * 2 * u)
        D.circle(screen, (255, 240, 170), (acx, by - 56 * u + bob), 14 * u, u)
        screen.blit(icon(ENH_ICON[f["key"]], 3 * u), (acx - 13 * u, by - 69 * u + bob))
    elif st == "result":                                       # 실패: 식은 금속 위로 연기
        for i in range(5):
            yy = (f["rt"] * 26 + i * 9) % 44
            D.circle(screen, (96, 92, 104), (acx - 8 * u + i * 4 * u, int(by - 33 * u - yy * u)), (3 + i % 3) * u)
    el = 0.42 - f["sw"] if f["sw"] > 0 else 9.0               # 망치: 내리치고 -> 잠시 멈추고 -> 되돌아간다
    if el < 0.09:
        phi = 20 + 70 * (el / 0.09)
    elif el < 0.16:
        phi = 90.0
    elif el < 0.42:
        phi = 90 - 70 * ((el - 0.16) / 0.26)
    else:
        phi = 20 + 3 * math.sin(f["t"] * 3)
    ph_ = math.radians(phi)
    pvx, pvy, L_ = acx + 26 * u, by - 30 * u, 26 * u
    dxv, dyv = -math.sin(ph_), -math.cos(ph_)
    ex_, ey_ = pvx + dxv * L_, pvy + dyv * L_
    D.line(screen, (150, 108, 70), (pvx - dxv * 8 * u, pvy - dyv * 8 * u), (ex_, ey_), 3 * u)
    nx, ny = -dyv, dxv
    head = [(ex_ + nx * 7 * u + dxv * 4 * u, ey_ + ny * 7 * u + dyv * 4 * u),
            (ex_ + nx * 7 * u - dxv * 4 * u, ey_ + ny * 7 * u - dyv * 4 * u),
            (ex_ - nx * 7 * u - dxv * 4 * u, ey_ - ny * 7 * u - dyv * 4 * u),
            (ex_ - nx * 7 * u + dxv * 4 * u, ey_ - ny * 7 * u + dyv * 4 * u)]
    D.polygon(screen, (150, 156, 180), head)
    D.polygon(screen, INK, head, u)
    for r in f["rg"]:                                          # 타격 충격파
        if r[0] > 0:
            D.circle(screen, (255, 236, 150) if r[1] == 2 else (255, 180, 90) if r[1] == 1 else (150, 140, 150),
                     (acx, by - 28 * u), int((6 + r[0] / 0.45 * 62) * u), max(1, (r[1] + 1) * u // 2))
    for s in f["sp"]:                                          # 튀는 불꽃
        c = lerp_c((255, 230, 140), (255, 110, 40), 1 - min(1.0, s[4] / 0.7))
        D.rect(screen, c, (acx + int(s[0] * u), by + int(s[1] * u), u, u))
    for p in f["pop"]:
        txt(screen, font, p[0], acx + p[1] * u, by + int(p[2] * u), p[4], True, u)
    if f["flash"] > 0:                                         # 완벽한 타격의 섬광
        fl = pygame.Surface((sw_, sh_), pygame.SRCALPHA)
        fl.fill((255, 250, 220, int(200 * f["flash"] / 0.3)))
        screen.blit(fl, (sx, sy))
    if st == "result" and f["rt"] > 0.35:
        title_txt(screen, f2, "강화 성공!" if f["res"] == "ok" else "강화 실패...", sx + sw_ // 2, sy + 8 * u, u,
                  GOLD if f["res"] == "ok" else CORAL)
        if f["res"] == "ok":
            txt(screen, font, f["before"], sx + sw_ // 2, sy + 24 * u, MUTED, True, u)
            txt(screen, font, "↓", sx + sw_ // 2, sy + 32 * u, CREAM, True, u)
            txt(screen, font, f["after"], sx + sw_ // 2, sy + 40 * u, GREEN, True, u)
        else:
            txt(screen, font, "재료가 사라졌다...", sx + sw_ // 2, sy + 26 * u, MUTED, True, u)
        txt(screen, font, f"단련 경험 +{f['xp']} EXP", sx + sw_ // 2, sy + sh_ - 10 * u, (140, 200, 255), True, u)
    screen.set_clip(None)

    bw, bh = int(pw * 0.62), 10 * u                            # 타이밍 게이지
    bx, byb = px + (pw - bw) // 2, py + 152 * u
    D.rect(screen, INK, (bx - u, byb - u, bw + 2 * u, bh + 2 * u))
    D.rect(screen, (34, 42, 74), (bx, byb, bw, bh))
    if st in ("ready", "strike"):
        zx0 = bx + int((f["zc"] - f["zw"] / 2) * bw)
        D.rect(screen, (60, 170, 110), (zx0, byb, int(f["zw"] * bw), bh))
        pz_ = int(f["zw"] * 0.34 * bw)
        D.rect(screen, (240, 230, 120), (bx + int(f["zc"] * bw) - pz_ // 2, byb, max(2, pz_), bh))   # 완벽 구간
        mx = bx + int(f["pos"] * bw)
        D.rect(screen, BRASS_L, (mx - u, byb - 2 * u, 2 * u, bh + 4 * u))
        diamond(screen, mx, byb - 3 * u, 2 * u, BRASS_L)
    for i in range(3):                                         # 타격 결과 표시
        col = ((CORAL, GREEN, GOLD)[f["hits"][i]]) if i < len(f["hits"]) else (70, 72, 96)
        diamond(screen, px + pw // 2 + (i - 1) * 14 * u, py + 170 * u, 4 * u, col)
    if f["combo"] >= 2 and st == "strike":
        txt(screen, font, f"콤보 x{f['combo']}", bx + bw + 6 * u, byb, CYAN, u=u)
    if st == "select":
        msg, mc = (f["msg"], CORAL) if f["msg"] else ("W/S 선택  ·  Enter 장비 확정  ·  E 닫기", CREAM)
    elif st == "ready":
        msg, mc = (f["msg"], CORAL) if f["msg"] else ("Enter: 단련 시작 (재료 소모)  ·  A/E: 다른 장비 고르기", CREAM)
    elif st == "strike":
        msg, mc = "Space: 표식이 초록 구간에 올 때 내리친다!  (노란 중앙 = 완벽)", CREAM
    else:
        msg, mc = (f"최종 성공률 {int(f['rate'] * 100)}%  ·  Enter: 계속 단련  ·  E: 닫기" if f["rt"] > 0.5 else "", MUTED)
    txt(screen, font, msg, px + pw // 2, py + 181 * u, mc, True, u)


def draw_end(screen, font, g, u):
    SW, SH = W * u, H * u
    f2 = bigfont(u)
    veil = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    veil.fill((14, 10, 28, 185))
    screen.blit(veil, (0, 0))
    dead = g["mode"] == "dead"
    lines = ["R: 마을에서 부활 (골드 20% 손실)   ESC: 종료"] if dead else \
        ["벽화의 마지막 기록이 떠올랐다.", "문명을 무너뜨린 것은 외부의 적이 아니라", "스스로 만든 기계의 폭주였다.", "R: 새 게임   ESC: 종료"]
    pw, ph = int(SW * 0.62), (34 + len(lines) * 11 + 10) * u
    px, py = (SW - pw) // 2, (SH - ph) // 2
    frame(screen, px, py, pw, ph, u)
    title_txt(screen, f2, "쓰러졌다..." if dead else "핵이 멈췄다", SW // 2, py + 12 * u, u, CORAL if dead else GOLD)
    D.rect(screen, BRASS_D, (px + 20 * u, py + 27 * u, pw - 40 * u, u))
    diamond(screen, SW // 2, py + 27 * u, 3 * u, BRASS)
    for i, s in enumerate(lines):
        last = i == len(lines) - 1
        txt(screen, font, s, SW // 2, py + (33 + i * 11) * u, MUTED if last else CREAM, True, u)


def overlay(screen, font, g, u):
    if g["ui"] == "inv":
        draw_inventory(screen, font, g, u)
    elif g["ui"] in ("smith", "shop", "cart"):
        draw_shop(screen, font, g, u)
    elif g["ui"] == "bench":
        draw_forge(screen, font, g, u)
    if g["mode"] != "play":
        draw_end(screen, font, g, u)


def render(screen, surf, font, g, u):
    draw(surf, g)
    ox = oy = 0
    if g["shake"] > 0:                                         # 큰 사건(보스 봉인·폭주·처치)의 화면 흔들림
        a = 1 + int(min(1.0, g["shake"] * 3) * 2)
        ox, oy = random.randint(-a, a) * u // 2, random.randint(-a, a) * u // 2
        screen.fill((0, 0, 0))
    screen.blit(pygame.transform.scale(surf, (W * u, H * u)), (ox, oy))
    screen.blit(vignette(u), (0, 0))
    cx, cy = camera(g)
    for s, x, y, life, col in g["ft"]:
        txt(screen, font, s, int((x - cx) * u) + ox, int((y - cy) * u) + oy, col, True, u)
    hud(screen, font, g, u)
    overlay(screen, font, g, u)
    if g["tr"]:                                                # 구역 이동 페이드
        t = g["tr"]["t"]
        a = t / 0.25 if t < 0.25 else max(0, (0.5 - t) / 0.25)
        veil = pygame.Surface(screen.get_size())
        veil.set_alpha(int(255 * min(1, a)))
        screen.blit(veil, (0, 0))


def load_font(size):
    for name in ("malgungothic", "applegothic", "nanumgothic", "notosanscjkkr", "notosanscjk"):
        path = pygame.font.match_font(name)
        if path:
            return pygame.font.Font(path, size)
    return pygame.font.Font(None, size)


def read_input(k):
    return (int(k[pygame.K_RIGHT] or k[pygame.K_d]) - int(k[pygame.K_LEFT] or k[pygame.K_a]),
            int(k[pygame.K_DOWN] or k[pygame.K_s]) - int(k[pygame.K_UP] or k[pygame.K_w]), bool(k[pygame.K_SPACE]))


def on_key(g, k):
    """키 입력 처리. 새 게임 상태를 돌려주거나 종료 시 None."""
    if k == pygame.K_ESCAPE:
        if g["ui"] == "bench" and g["forge"] and g["forge"]["stage"] == "strike":
            return g                                           # 단련 도중에는 멈출 수 없다
        if g["ui"]:
            g["ui"], g["forge"] = None, None
            return g
        return None
    if k == pygame.K_m:
        toggle_mute(g)
        return g
    if g["mode"] == "dead" and k == pygame.K_r:
        return respawn(g)
    if g["mode"] == "ending" and k == pygame.K_r:
        return new_state()
    if g["mode"] != "play" or g["tr"]:
        return g
    if g["ui"] == "bench":                                     # 모루 단련
        return forge_key(g, k)
    if g["ui"] in ("smith", "shop", "cart"):                   # 상점·대장간·마차 조작
        items = shop_items(g, g["ui"], g["tab"])
        nt = len(shop_tabs(g["ui"]))
        if k in (pygame.K_UP, pygame.K_w):
            g["cur"] = (g["cur"] - 1) % len(items)
            play("ui")
        elif k in (pygame.K_DOWN, pygame.K_s):
            g["cur"] = (g["cur"] + 1) % len(items)
            play("ui")
        elif k in (pygame.K_LEFT, pygame.K_a, pygame.K_RIGHT, pygame.K_d) and nt > 1:
            g["tab"], g["cur"], g["smsg"] = (g["tab"] + 1) % nt, 0, ("", True)
            play("ui")
        elif k in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            buy(g, items[min(g["cur"], len(items) - 1)])
        elif pygame.K_1 <= k <= pygame.K_9 and k - pygame.K_1 < len(items):
            g["cur"] = k - pygame.K_1
        elif k == pygame.K_e:
            g["ui"] = None
        return g
    if g["ui"] == "inv" and k != pygame.K_i:                   # 인벤토리: 보기 전용
        if k == pygame.K_q:
            use_potion(g)
        return g
    if k == pygame.K_i:
        g["ui"] = "inv" if g["ui"] is None else None
        g["smsg"] = ("", True)
    elif g["ui"] is not None:
        return g
    elif k == pygame.K_e:
        npc = near_npc(g)
        if npc and npc[0] == "bench":
            open_forge(g)
        elif npc:
            g["ui"], g["tab"], g["cur"], g["smsg"] = npc[0], 0, 0, ("", True)
            play("ui")
    elif k == pygame.K_q:
        use_potion(g)
    elif k in (pygame.K_z, pygame.K_x, pygame.K_c):
        toggle_mod(g, (pygame.K_z, pygame.K_x, pygame.K_c).index(k))
    return g


def main():
    pygame.init()
    init_sound()
    try:
        dw, dh = pygame.display.get_desktop_sizes()[0]
    except Exception:
        dw, dh = 1280, 720
    u = max(2, min(dw * 9 // 10 // W, dh * 9 // 10 // H))      # 화면 크기에 맞춰 정수 배율 선택
    screen = pygame.display.set_mode((W * u, H * u))
    pygame.display.set_caption("Pixel Ruins v8")
    surf, font, clock = pygame.Surface((W, H)), load_font(6 * u), pygame.time.Clock()
    g = new_state()
    while True:
        dt = min(clock.tick(60) / 1000, 0.05)
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit()
                return
            if ev.type == pygame.KEYDOWN:
                g = on_key(g, ev.key)
                if g is None:
                    pygame.quit()
                    return
        if g["mode"] == "play" and g["ui"] is None:
            update(g, read_input(pygame.key.get_pressed()), dt)
        elif g["mode"] == "play" and g["ui"] == "bench":
            update_forge(g, dt)
        render(screen, surf, font, g, u)
        pygame.display.flip()


if __name__ == "__main__":
    main()