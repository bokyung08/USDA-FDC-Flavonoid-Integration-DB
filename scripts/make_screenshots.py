# -*- coding: utf-8 -*-
"""
Stage 7 검증 쿼리의 '실제 실행 결과'(scripts/_run/stage7_verification_output.txt)를
터미널(mysql CLI) 화면처럼 렌더링한 스크린샷 이미지를 생성한다.
표 본문은 실제 출력 텍스트를 그대로(전사 오류 0) 사용한다.
출력: docs/assets/shot_v*.png
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties

HERE = os.path.dirname(__file__)
SRC = os.path.join(HERE, "_run", "stage7_live.txt")          # 라이브 실행 출력
PROOF = os.path.join(HERE, "_run", "stage7_proof.txt")       # 버전·시각 증거
OUT = os.path.join(HERE, "..", "docs", "assets")
os.makedirs(OUT, exist_ok=True)

with open(SRC, encoding="utf-8") as f:
    LINES = [ln.rstrip("\n") for ln in f]
with open(PROOF, encoding="utf-8") as f:
    PLINES = [ln.rstrip("\n") for ln in f]

# 한글 제목용 폰트(표 본문은 monospace)
KR = FontProperties(family="Malgun Gothic", size=12, weight="bold")

BG = "#0d1117"      # 터미널 배경
FG = "#e6edf3"      # 본문
PROMPT = "#3fb950"  # 프롬프트(초록)
TITLE = "#58a6ff"   # 제목(파랑)


def block(a, b):
    """1-indexed 줄 범위(a..b)를 실제 파일에서 잘라낸다."""
    return LINES[a - 1:b]


def render(name, kr_title, body_lines, cmd):
    maxlen = max(len(s) for s in body_lines + [cmd])
    nlines = len(body_lines)
    w = maxlen * 0.083 + 0.7
    h = (nlines + 4) * 0.205 + 0.3
    fig = plt.figure(figsize=(w, h), facecolor=BG)
    ax = fig.add_axes([0, 0, 1, 1]); ax.axis("off"); ax.set_facecolor(BG)
    y = 0.97
    # 한글 제목
    ax.text(0.018, y, kr_title, color=TITLE, fontproperties=KR,
            va="top", ha="left", transform=ax.transAxes)
    y -= 1.7 / (nlines + 4)
    # 실제 실행 명령(프롬프트)
    ax.text(0.018, y, cmd, color=PROMPT, family="DejaVu Sans Mono",
            fontsize=10.5, va="top", ha="left", transform=ax.transAxes)
    y -= 1.3 / (nlines + 4)
    # 표 본문(실제 출력 그대로)
    ax.text(0.018, y, "\n".join(body_lines), color=FG, family="DejaVu Sans Mono",
            fontsize=11, va="top", ha="left", transform=ax.transAxes, linespacing=1.25)
    path = os.path.join(OUT, name)
    fig.savefig(path, facecolor=BG, bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)
    print("saved", os.path.normpath(path))


CMD = "$ mysql -u root -p usda_fdc -t < scripts/06_final_verification.sql"

render("shot_v0_proof.png", "Stage 7 검증 라이브 실행 증거 (MySQL 8.0.45 · 2026-06-20)",
       PLINES, "$ mysql -u root -p usda_fdc -t -e \"SELECT VERSION(), NOW(), DATABASE(); ...\"")
render("shot_v1_rows.png", "① 테이블별 적재 행 수 (합계 34,402,883)",
       block(6, 19), CMD)
render("shot_v2_matchrate.png", "② Flavonoid 매핑 실패율 (71.00% / 29.00%)",
       block(25, 29), CMD)
render("shot_v3_daidzein.png", "③ Daidzein(nutrient_id=710) 함량 TOP 5",
       block(35, 43), CMD)
render("shot_v4_class.png", "④ Flavonoid 클래스별 평균 함량",
       block(49, 59), CMD)
render("shot_v5_summary.png", "⑤ 단일 식품 통합 조회 — fdc_id 2707451 (일반 65 + 플라보노이드 37 = 102행)",
       block(65, 69), CMD)
render("shot_v5_flav.png", "⑤-2 플라보노이드 37종 함량 (이소플라본만 양수, 나머지 0)",
       block(99, 139), CMD)

print("done")
