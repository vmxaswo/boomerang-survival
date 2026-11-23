"""v9 소리 모듈 (v9_audio.py)
 - 배경음악: 지역마다 화음 진행 + 베이스 + 아르페지오 + 패드 + 가벼운 타악기를 겹친 12.8초 루프 (기존: 멜로디 한 줄 + 베이스)
   들판은 밝고 느긋하게, 노을 회랑은 따뜻하게, 밤 정원은 단조로 고요하게, 새벽 유적은 맑게, 사원은 신비롭게,
   보스방은 빠르고 묵직하게 (북 + 낮은 베이스)
 - 새 효과음: 발소리(step) · 봉인 해제(unlock) · 안내 완료(tut) · 메뉴 확인(ok) · 메뉴 취소(back) · 지역 진입(region)
 - 음량: set_volumes(배경음, 효과음) 으로 바꾼다 (v9_menu 설정에서 부른다). 배경음은 0번 채널 음량으로 조절
음악은 처음 필요할 때 백그라운드 스레드에서 만든다 (topdown_rpg.set_music 그대로)."""
import array
import math
import random

import pygame

G = None
VOL = dict(music=0.8, sfx=0.8)
# 지역 번호 -> (근음 Hz, 음계, 화음 진행(음계 도수), 템포(1박 초), 성격)
MAJ, MIN, DOR, LYD = (0, 2, 4, 5, 7, 9, 11), (0, 2, 3, 5, 7, 8, 10), (0, 2, 3, 5, 7, 9, 10), (0, 2, 4, 6, 7, 9, 11)
STYLE = {0: (196.0, MAJ, (0, 4, 5, 3), 0.40, "calm"),          # 마을 초원
         1: (174.6, DOR, (0, 3, 6, 4), 0.40, "warm"),          # 노을 회랑
         2: (164.8, MIN, (0, 5, 3, 6), 0.50, "night"),         # 밤 정원
         3: (220.0, LYD, (0, 1, 4, 0), 0.45, "airy"),          # 새벽 유적
         4: (185.0, MAJ, (0, 3, 4, 0), 0.40, "calm"),
         5: (146.8, MIN, (0, 5, 6, 4), 0.50, "myst"),          # 사원 터 / 타이틀
         6: (110.0, MIN, (0, 0, 5, 6), 0.30, "boss"),          # 보스방들
         7: (116.5, MIN, (0, 3, 5, 4), 0.30, "boss"),
         8: (103.8, MIN, (0, 6, 5, 4), 0.30, "boss")}


def _osc(kind, ph):
    p = ph % 1.0
    if kind == "tri":
        return 4 * abs(p - 0.5) - 1
    if kind == "sq":
        return 0.6 if p < 0.5 else -0.6
    if kind == "saw":
        return 2 * p - 1
    return math.sin(ph * 6.283185307)


def compose(reg):
    SR = G.SR
    root, scale, prog, beat, mood = STYLE.get(reg, STYLE[6] if reg >= 9 else STYLE[0])
    r = random.Random(reg * 131 + 7)
    bars, bpb = 8, 8                                              # 8마디 x 8박 (8분음표): 진행을 두 번, 뒤쪽은 변주
    prog = tuple(prog) + tuple(prog[:3]) + (prog[0],)
    step = beat / 2
    N = int(SR * step * bars * bpb)
    buf = [0.0] * N

    def f_of(deg, octv=0):
        o, d = divmod(deg, len(scale))
        return root * 2 ** ((scale[d] + 12 * (o + octv)) / 12)

    def note(t0, f, dur, kind, vol, dec, att=0.01):
        i0, n = int(t0 * SR), int(dur * SR)
        ph, a = 0.0, max(1, int(att * SR))
        inc = f / SR
        for i in range(n):
            ph += inc
            env = min(1.0, i / a) * math.exp(-dec * i / n)
            buf[(i0 + i) % N] += vol * env * _osc(kind, ph)

    def noise(t0, dur, vol, dec, lp=0.0):
        i0, n, prev = int(t0 * SR), int(dur * SR), 0.0
        for i in range(n):
            v = r.uniform(-1, 1)
            prev = prev * lp + v * (1 - lp)
            buf[(i0 + i) % N] += vol * math.exp(-dec * i / n) * prev

    boss = mood == "boss"
    for b, chord in enumerate(prog):
        t_bar = b * bpb * step
        tones = [chord, chord + 2, chord + 4]
        pad_kind = "saw" if boss else "tri"
        for k, d in enumerate(tones):                             # 패드: 화음을 길게
            note(t_bar, f_of(d, 0), bpb * step, pad_kind, 0.035 if boss else 0.045, 0.6, att=0.25)
        for s in range(bpb):                                      # 베이스
            if boss or s % 4 == 0:
                note(t_bar + s * step, f_of(chord, -1 if not boss else -2) * (2 if boss and s % 2 else 1),
                     step * (0.9 if boss else 3.6), "sq" if boss else "sine", 0.12 if boss else 0.16, 3 if boss else 1.2)
        arp = [tones[i % 3] + (len(scale) if i % 6 >= 3 else 0) for i in range(8)]
        if mood in ("night", "myst"):
            arp = arp[::2] + arp[::2]
        for s in range(bpb):                                      # 아르페지오
            if mood == "night" and s % 2:
                continue
            note(t_bar + s * step, f_of(arp[s], 1), step * 1.6, "tri" if not boss else "sq", 0.05 if not boss else 0.035, 4)
        if not boss and r.random() < 0.8:                         # 짧은 멜로디 조각 (뒤쪽 4마디는 더 촘촘하게)
            for s in range(0, bpb, 2):
                if r.random() < (0.75 if b >= 4 else 0.45):
                    note(t_bar + s * step, f_of(chord + r.choice((0, 2, 4, 5, 7)), 2), step * 1.8, "sine", 0.045, 3)
        for s in range(bpb):                                      # 타악기
            if boss:
                if s % 4 == 0:
                    note(t_bar + s * step, 55.0, 0.18, "sine", 0.35, 6)
                if s % 4 == 2:
                    noise(t_bar + s * step, 0.12, 0.16, 9, 0.3)
                noise(t_bar + s * step, 0.03, 0.05, 20, 0.0)
            elif mood in ("calm", "warm", "airy") and s % 2 == 1:
                noise(t_bar + s * step, 0.025, 0.025, 20, 0.0)
    peak = max(1e-6, max(abs(v) for v in buf))
    k = 0.9 / peak
    return array.array("h", [int(max(-1.0, min(1.0, v * k)) * 32767 * 0.5) for v in buf])


def make_sfx():
    tone, layer, seq, rest = G.tone, G.layer, G.seq, G.rest
    return dict(
        step=tone(0, 0, 0.05, "noise", 0.07, 14),
        unlock=seq(layer(tone(90, 60, 0.5, "saw", 0.22, 1.8), tone(0, 0, 0.4, "noise", 0.08, 3)),
                   *[tone(f, f, 0.1, "tri", 0.24, 2) for f in (392, 523, 659, 784)],
                   tone(1047, 1047, 0.35, "tri", 0.24, 2)),
        tut=seq(tone(784, 784, 0.06, "tri", 0.18, 2), tone(1175, 1175, 0.12, "tri", 0.18, 3)),
        ok=seq(tone(660, 660, 0.04, "sq", 0.12, 2), tone(990, 990, 0.07, "sq", 0.12, 3)),
        back=tone(520, 330, 0.08, "sq", 0.12, 3),
        region=seq(tone(523, 523, 0.12, "tri", 0.16, 1.5), tone(784, 784, 0.25, "tri", 0.16, 1.5)),
    )


def set_volumes(music=None, sfx=None):
    if music is not None:
        VOL["music"] = max(0.0, min(1.0, music))
    if sfx is not None:
        VOL["sfx"] = max(0.0, min(1.0, sfx))
    try:
        for s in G.SND.values():
            s.set_volume(VOL["sfx"])
        if pygame.mixer.get_init():
            pygame.mixer.Channel(0).set_volume(VOL["music"])
    except Exception:
        pass


def install(g_mod):
    global G
    G = g_mod
    old_init = G.init_sound

    def init_sound():
        old_init()
        try:
            if pygame.mixer.get_init():
                for k, arr in make_sfx().items():
                    G.SND[k] = pygame.mixer.Sound(buffer=arr.tobytes())
                set_volumes()
        except Exception:
            G.v9_log("audio-sfx")
    G.init_sound = init_sound
    G.make_track = compose
