"""보스 모델 시트 (tools/boss_sheet.py) - 보스마다 페이즈 x (방향·동작) 격자로 그려 PNG 로 저장한다.

  python tools/boss_sheet.py                 -> docs/boss_sheets/*.png
  python tools/boss_sheet.py 출력폴더

보스 모델을 고친 뒤 모든 페이즈·방향을 한눈에 확인할 때 쓴다 (창 없이 그린다). 자세한 설명은 docs/BOSS_MODELING.md"""
import math, os, sys, traceback
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"
GAME = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(GAME, "docs", "boss_sheets")
os.makedirs(OUT, exist_ok=True)
sys.path.insert(0, GAME)
sys.argv = ["game_v9.py"]
import pygame
import game_v9 as m
G, ui = m.build()
pygame.init()
pygame.display.set_mode((64, 64))
import v9_ba_bulk, v9_ba_alch, v9_ba_heat, v9_ba_core, v9_ba_r3 as R3
import v9_dragon_rig as DR, v9_dragon_fx as DF, v9_kaiju_rig as KR, v9_kaiju_fx as KF
font = G.load_font(12)
FRONT, RIGHT, BACK, LEFTD = math.pi / 2, 0.0, -math.pi / 2, math.pi * 0.8


def sheet(name, rows, cols, cell, draw_fn, scale=2):
    cw, ch = cell
    W_, H_ = (90 + cw * len(cols)) * 1, (24 + ch * len(rows))
    s = pygame.Surface((W_, H_))
    s.fill((34, 30, 46))
    for j, c in enumerate(cols):
        s.blit(font.render(c, False, (250, 226, 150)), (90 + j * cw + 4, 4))
    for i, r in enumerate(rows):
        s.blit(font.render(r, False, (250, 226, 150)), (4, 24 + i * ch + ch // 2 - 6))
        for j, c in enumerate(cols):
            pygame.draw.rect(s, (46, 42, 60), (90 + j * cw, 24 + i * ch, cw - 2, ch - 2))
            try:
                img = draw_fn(i, j)
                s.blit(img, (90 + j * cw + (cw - img.get_width()) // 2, 24 + i * ch + (ch - img.get_height()) // 2))
            except Exception:
                s.blit(font.render("ERR", False, (255, 90, 90)), (90 + j * cw + 4, 24 + i * ch + 4))
                print(name, r, c, traceback.format_exc().splitlines()[-1])
    pygame.image.save(pygame.transform.scale(s, (W_ * scale, H_ * scale)), os.path.join(OUT, name + ".png"))
    print("saved", name)


def mid(i, phase, st, hd, t=1.3, **kw):
    e = dict(phase=phase, an=t, st=st, fa=hd, fa2=hd, lk=hd, mv=False, fl=0, exp=0, x=0.0, y=0.0, stun=0.0, heat=40.0,
             lift=0, inv=0.0, id=i)
    e.update(kw)
    st_ = R3.anim(e, "_r3")[0]
    st_["hd"] = hd
    fn = (v9_ba_bulk.draw, v9_ba_alch.draw, v9_ba_heat.draw, v9_ba_core.draw)[i]
    return fn(e).copy()


# ---- 벌크스틸
cols = ["정면", "오른쪽", "뒷면", "돌진 준비(wind)", "기절(stun)", "포탑(turret)"]
spec = [(None, FRONT), (None, RIGHT), (None, BACK), ("wind", FRONT), ("stun", FRONT), ("turret", LEFTD)]
sheet("boss_bulksteel", ["1 녹슨 철벽", "2 요새화 거포", "3 제한 해제"], cols, (224, 194),
      lambda r, c: mid(0, r + 1, spec[c][0] or "idle", spec[c][1]))
# ---- 알케미스트
cols = ["정면", "오른쪽", "뒷면", "주문(cast)", "왼쪽 아래", "다른 순간"]
spec = [("idle", FRONT, 1.3), ("idle", RIGHT, 1.3), ("idle", BACK, 1.3), ("cast", FRONT, 1.3), ("idle", LEFTD, 1.3), ("idle", FRONT, 2.9)]
sheet("boss_alchemist", ["1 컨베이어 조종", "2 용융 제련", "3 자원 재활용", "4 자폭 시퀀스"], cols, (224, 194),
      lambda r, c: mid(1, r + 1, spec[c][0], spec[c][1], spec[c][2]))
# ---- 오버히트
cols = ["정면", "오른쪽", "뒷면", "분사(torch)", "기절(stun)", "과열 최대"]
spec = [(dict(), FRONT), (dict(), RIGHT), (dict(), BACK), (dict(st="torch"), FRONT), (dict(stun=1.0), FRONT), (dict(heat=100.0), LEFTD)]
sheet("boss_overheat", ["1 과열", "2 극저온", "3 열폭주", "4 초고온 플라즈마"], cols, (224, 194),
      lambda r, c: mid(2, r + 1, spec[c][0].get("st", "idle"), spec[c][1], **{k: v for k, v in spec[c][0].items() if k != "st"}))
# ---- 빅 브라더
cols = ["정면", "오른쪽", "뒷면", "왼쪽 아래", "박동 순간"]
spec = [(FRONT, 1.0), (RIGHT, 1.0), (BACK, 1.0), (LEFTD, 1.0), (FRONT, 2.15)]
sheet("boss_bigbrother", ["1 외곽 시스템", "2 본체 노출", "3 시스템 해킹", "4 멸망 프로토콜"], cols, (224, 194),
      lambda r, c: mid(3, r + 1, "idle", spec[c][0], spec[c][1], _alive=4))


# ---- 화룡 / 탈라소르: 리그 + 포즈
def rig_draw(Rm, Fm, st_name, ph, hd, armor=None, t=1.0):
    rig = Rm.new_state()
    e = dict(cue=None, phase=ph, an=t, st=st_name, armor=armor or 0, hp=1, mhp=1)
    for k in range(40):
        tg = Fm.build_pose(st_name, e, 0.3 + k * 0.02, t + k * 0.02, ph, None)
        Rm.update(rig, tg, 1 / 30, 9, 0.0, 0.0, 0.0)
    img = pygame.Surface((Rm.CW, Rm.CH), pygame.SRCALPHA)
    if armor is None:
        Rm.draw(img, rig, Fm.PALS[ph], ph, t, hd)
    else:
        Rm.draw(img, rig, Fm.PALS[ph], ph, t, hd, armor)
    bb = img.get_bounding_rect()
    return img.subsurface(bb).copy() if bb.w else img


print("dragon states:", sorted(DF.BASE))
print("kaiju states:", sorted(KF.BASE))
dcols = [s for s in ("idle", "breath_w", "breath", "charge", "erupt", "fly", "stun", "roar") if s in DF.BASE][:6]
sheet("boss_dragon", ["1페이즈", "2페이즈", "3페이즈"], ["정면"] + dcols[1:6] + ["오른쪽"], (260, 230),
      lambda r, c: rig_draw(DR, DF, "idle" if c in (0, len(dcols)) else dcols[c], r + 1, FRONT if c < len(dcols) else RIGHT))
kcols = [s for s in ("idle", "rear_w", "slam", "coil_w", "sweep", "crawl_w", "glow_w", "roar", "sleep", "takeoff") if s in KF.BASE][:6]
sheet("boss_thalassor", ["1 장갑 3장", "2 약점 노출", "3 발광 폭주"], ["정면"] + kcols[1:6] + ["오른쪽"], (300, 250),
      lambda r, c: rig_draw(KR, KF, "idle" if c in (0, len(kcols)) else kcols[c], r + 1, FRONT if c < len(kcols) else RIGHT,
                            armor=(3, 0, 0)[r]))
