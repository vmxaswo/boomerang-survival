"""pixelfx 이펙트 스프라이트 시트 생성기 (gen_fx.py)
  python gen_fx.py            ->  fx_sheets/<이름>.png + <이름>.json 을 만든다 (게임은 이 파일만 읽으므로 Node 가 없어도 실행된다)
  python gen_fx.py 이름 ...    ->  그 시트만 다시 만든다
탑다운 전용 이펙트(pixelfx/src/fx/topdown/td-*.js)를 보스별 색·스타일·크기로 렌더링한다.
pixelfx 저장소는 이 폴더 옆(바탕 화면/pixelfx)에 둔다. 이펙트를 고치면 이 스크립트를 다시 실행한다."""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "fx_sheets")
PFX = os.path.join(os.path.dirname(HERE), "pixelfx")
NODE = shutil.which("node") or r"C:\Program Files\nodejs\node.exe"
FPS = 30

# 보스별 테마: (스타일, 팔레트 어두움 -> 밝음 7단)
THEMES = dict(
    earth=("earth", ["#1c140e", "#3a2a1c", "#6a4a2c", "#a4702e", "#d89a3c", "#f2c45a", "#fff0c0"]),     # 수문장 벌크스틸: 금속 파편·먼지
    acid=("acid", ["#07160c", "#0e3018", "#27903a", "#54cc4c", "#a0f070", "#d8ffb0", "#ffffff"]),      # 공장장 알케미스트: 산성 방울
    fire=("fire", ["#2a0c10", "#7a1a14", "#cc3a1a", "#f2701f", "#ffae35", "#ffe27a", "#fff8d6"]),      # 수석 정비관 오버히트: 불꽃
    ice=("ice", ["#0c1430", "#1f4f94", "#2f7fcc", "#58b4ec", "#9bdcff", "#d8f4ff", "#ffffff"]),        # 오버히트 빙결 패턴
    digital=("digital", ["#1a0508", "#4a0a14", "#cc2038", "#f04860", "#ff90a0", "#ffd8de", "#ffffff"]),  # 빅 브라더: 데이터 조각
    storm=("ice", ["#0a1030", "#163070", "#2a5cc0", "#4aa0ff", "#8ad8ff", "#d0f4ff", "#ffffff"]),        # 필드 보스 탈라소르: 얼음 + 전기
    lava=("fire", ["#14060a", "#380a10", "#8a1a10", "#d23a14", "#ff7a24", "#ffc04a", "#fff0c0"]),      # 화룡: 용암
)
SIZES = dict(s=16, m=30, l=48, xl=72)

SPECS = []


def add(name, fid, **opts):
    SPECS.append((name, fid, opts))


for th, (style, pal) in THEMES.items():
    for sz, reach in SIZES.items():
        add(f"blast_{th}_{sz}", "topdown/td-blast", palette=pal, style=style, reach=reach)
    add(f"strip_{th}_h", "topdown/td-strip", palette=pal, style=style, width=26)
    add(f"strip_{th}_v", "topdown/td-strip", palette=pal, style=style, width=26, angle=1.5707963)
    for w in (16, 28):                                                   # 띠 장판이 살아 있는 동안의 표면 (48px 타일)
        add(f"field_{th}_{w}_h", "topdown/td-field", palette=pal, style=style, width=w)
        add(f"field_{th}_{w}_v", "topdown/td-field", palette=pal, style=style, width=w, angle=1.5707963)
    if th == "ice":
        continue
    add(f"muzzle_{th}", "topdown/td-muzzle", palette=pal, reach=9)        # 레이저 발사구 / 끝점 (반복)
    add(f"beamend_{th}", "topdown/td-beamend", palette=pal, reach=11)
    add(f"dashkick_{th}", "topdown/td-dash", palette=pal, style=style, mode="kick", reach=16)
    add(f"dashtrail_{th}", "topdown/td-dash", palette=pal, style=style, mode="trail", reach=12)
    add(f"hit_{th}", "topdown/td-blast", palette=pal, style=style, reach=9, seed=11)
    add(f"nova_{th}", "topdown/td-nova", palette=pal, style=style, reach=80)
    add(f"death_{th}", "topdown/td-nova", palette=pal, style=style, reach=96, big=True, seed=9)
    add(f"charge_{th}", "topdown/td-charge", palette=pal, reach=14)
    add(f"blinkout_{th}", "topdown/td-blink", palette=pal, reach=22, mode="out")
    add(f"blinkin_{th}", "topdown/td-blink", palette=pal, reach=22, mode="in")
    add(f"summon_{th}", "topdown/td-summon", palette=pal, reach=14)
    add(f"implode_{th}", "topdown/td-implode", palette=pal, reach=70)


BREATH_DIRS = 24
for i in range(BREATH_DIRS):                                             # 화룡 브레스: 24방향으로 돌려 뽑는다
    add(f"breath_{i:02d}", "topdown/td-flame", palette=THEMES["lava"][1], length=104, angle=i * 6.2831853 / BREATH_DIRS)


for i in range(BREATH_DIRS):                                             # 탈라소르의 냉기·번개 브레스
    add(f"kbreath_{i:02d}", "topdown/td-frostbreath", palette=THEMES["storm"][1], length=108, angle=i * 6.2831853 / BREATH_DIRS)
add("gust_storm", "topdown/td-gust", palette=THEMES["storm"][1], reach=110)


def main(only=None):
    os.makedirs(OUT, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="pfx_")
    ok = 0
    todo = [s for s in SPECS if not only or s[0] in only]
    for name, fid, opts in todo:
        cmd = [NODE, "tools/render.mjs", fid, "--sheet", "--fps", str(FPS), "--out", tmp, "--opts", json.dumps(opts)]
        r = subprocess.run(cmd, cwd=PFX, capture_output=True, text=True, encoding="utf-8")
        base = fid.split("/")[-1]
        src = os.path.join(tmp, *fid.split("/"), base)
        if r.returncode != 0 or not os.path.exists(src + ".png"):
            print("FAIL", name, fid, (r.stderr or r.stdout)[-300:])
            continue
        shutil.copyfile(src + ".png", os.path.join(OUT, name + ".png"))
        shutil.copyfile(src + ".json", os.path.join(OUT, name + ".json"))
        os.remove(src + ".png")
        ok += 1
        print("ok", name)
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"{ok}/{len(todo)} sheets -> {OUT}")


if __name__ == "__main__":
    main(set(sys.argv[1:]) or None)
