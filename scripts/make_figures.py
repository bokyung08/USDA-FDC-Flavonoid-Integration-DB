# -*- coding: utf-8 -*-
"""
ALL.md 보고서용 시각자료 생성 스크립트.
모든 수치는 보고서(usda_fdc DB 라이브 검증값)에서 직접 가져왔다.
출력: docs/assets/*.png
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

# 한글 폰트
plt.rcParams["font.family"] = "Malgun Gothic"
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 120

OUT = os.path.join(os.path.dirname(__file__), "..", "docs", "assets")
os.makedirs(OUT, exist_ok=True)

NAVY = "#27496d"
TEAL = "#0c7b93"
ORANGE = "#e1701a"
GRAY = "#b8c1cc"
GREEN = "#2e8b57"


def save(fig, name):
    path = os.path.join(OUT, name)
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print("saved", os.path.normpath(path))


# ── fig1. 테이블별 적재 행 수 (log scale) ───────────────────────────
def fig_table_rows():
    data = [
        ("food_nutrient", 27_280_100),
        ("food", 2_085_340),
        ("branded_food", 1_993_975),
        ("tmp_flavval", 262_071),
        ("unmatched_flavonoid", 75_998),
        ("sr_legacy_food", 7_793),
        ("tmp_mainfooddesc", 7_083),
        ("survey_fndds_food", 5_432),
        ("nutrient", 514),
        ("tmp_flavdesc", 37),
    ]
    labels = [d[0] for d in data]
    vals = [d[1] for d in data]
    colors = [NAVY if "tmp" not in l and l != "unmatched_flavonoid" else GRAY for l in labels]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    bars = ax.barh(labels, vals, color=colors)
    ax.set_xscale("log")
    ax.invert_yaxis()
    ax.set_xlabel("행 수 (log scale)")
    ax.set_title("테이블별 적재 행 수 — 총 34,402,883행", fontweight="bold")
    for b, v in zip(bars, vals):
        ax.text(v * 1.1, b.get_y() + b.get_height() / 2, f"{v:,}",
                va="center", fontsize=8)
    ax.margins(x=0.18)
    save(fig, "fig1_table_rows.png")


# ── fig2. Flavonoid 매핑률 도넛 ──────────────────────────────────
def fig_match_rate():
    fig, ax = plt.subplots(figsize=(5.2, 5.2))
    sizes = [186_073, 75_998]
    labels = ["통합 성공\n186,073행 (71.00%)", "미매핑 분리\n75,998행 (29.00%)"]
    wedges, _ = ax.pie(sizes, colors=[TEAL, ORANGE], startangle=90,
                       counterclock=False, wedgeprops=dict(width=0.42, edgecolor="white"))
    ax.legend(wedges, labels, loc="center", frameon=False, fontsize=10)
    ax.set_title("Flavonoid 함량 통합 매핑률\n(tmp_flavval 262,071행 기준)", fontweight="bold")
    save(fig, "fig2_match_rate.png")


# ── fig3. 클래스별 측정 빈도 vs 평균 함량 (이중축) ──────────────────
def fig_class():
    rows = [
        ("Flavan-3-ols", 65_377, 0.4491),
        ("Anthocyanidins", 35_203, 0.3018),
        ("Flavonols", 25_145, 0.5132),
        ("Isoflavones", 20_116, 0.2178),
        ("Flavanones", 20_116, 0.1194),
        ("Flavones", 15_087, 0.0945),
        ("(Total)", 5_029, 5.5913),
    ]
    labels = [r[0] for r in rows]
    freq = [r[1] for r in rows]
    avg = [r[2] for r in rows]
    x = range(len(labels))
    fig, ax1 = plt.subplots(figsize=(8.5, 4.6))
    ax1.bar([i - 0.2 for i in x], freq, width=0.4, color=NAVY, label="측정 빈도(행수)")
    ax1.set_ylabel("측정 빈도 (행수)", color=NAVY)
    ax1.tick_params(axis="y", labelcolor=NAVY)
    ax1.set_xticks(list(x))
    ax1.set_xticklabels(labels, rotation=20, ha="right")
    ax2 = ax1.twinx()
    ax2.bar([i + 0.2 for i in x], avg, width=0.4, color=ORANGE, label="평균 함량(mg)")
    ax2.set_ylabel("평균 함량 (mg)", color=ORANGE)
    ax2.tick_params(axis="y", labelcolor=ORANGE)
    ax1.set_title("Flavonoid 클래스별 측정 빈도 vs 평균 함량\n(빈도 최다 Flavan-3-ols, 평균 최고 Flavonols — 두 축은 별개)",
                  fontweight="bold")
    save(fig, "fig3_class_freq_vs_avg.png")


# ── fig4. Daidzein TOP5 ─────────────────────────────────────────
def fig_daidzein():
    rows = [
        ("Textured vegetable protein, dry", 64.55),
        ("Bacon bits", 64.37),
        ("Soy nuts", 61.42),
        ("Nutritional powder mix (EAS Soy)", 30.07),
        ("Nutritional powder mix, soy NFS", 30.07),
    ]
    labels = [r[0] for r in rows]
    vals = [r[1] for r in rows]
    fig, ax = plt.subplots(figsize=(8, 3.8))
    bars = ax.barh(labels, vals, color=GREEN)
    ax.invert_yaxis()
    ax.set_xlabel("Daidzein 함량 (mg/100g)")
    ax.set_title("Daidzein(nutrient_id=710) 함량 TOP 5 — 전부 콩 기반 식품", fontweight="bold")
    for b, v in zip(bars, vals):
        ax.text(v + 0.6, b.get_y() + b.get_height() / 2, f"{v:.2f}", va="center", fontsize=9)
    ax.margins(x=0.12)
    save(fig, "fig4_daidzein_top5.png")


# ── fig5. food.data_type 분포 ───────────────────────────────────
def fig_datatype():
    rows = [
        ("branded_food", 1_993_975),
        ("sub_sample_food", 65_502),
        ("sr_legacy_food", 7_793),
        ("market_acquistion", 7_388),
        ("survey_fndds_food", 5_432),
        ("sample_food", 3_890),
        ("agricultural_acquisition", 810),
        ("foundation_food", 436),
        ("experimental_food", 114),
    ]
    total = sum(r[1] for r in rows)
    labels = [r[0] for r in rows]
    vals = [r[1] for r in rows]
    colors = [ORANGE if l == "survey_fndds_food" else NAVY for l in labels]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    bars = ax.barh(labels, vals, color=colors)
    ax.set_xscale("log")
    ax.invert_yaxis()
    ax.set_xlabel("식품 수 (log scale)")
    ax.set_title("food.data_type 분포 (9종) — branded 95.6% 압도,\n통합 브릿지 survey는 0.3%(주황)이나 결정적",
                 fontweight="bold")
    for b, v in zip(bars, vals):
        ax.text(v * 1.1, b.get_y() + b.get_height() / 2,
                f"{v:,} ({v/total*100:.1f}%)", va="center", fontsize=8)
    ax.margins(x=0.22)
    save(fig, "fig5_datatype.png")


# ── fig6. 단일 식품 isoflavone 구성 (fdc_id 2707451) ─────────────
def fig_single_food():
    comps = [("Genistein", 87.31), ("Daidzein", 64.55), ("Glycitein", 15.08)]
    fig, ax = plt.subplots(figsize=(7.5, 2.4))
    left = 0
    palette = [NAVY, TEAL, ORANGE]
    for (name, val), c in zip(comps, palette):
        ax.barh(0, val, left=left, color=c, edgecolor="white")
        ax.text(left + val / 2, 0, f"{name}\n{val:.2f}", ha="center", va="center",
                color="white", fontsize=9, fontweight="bold")
        left += val
    ax.set_xlim(0, 166.94)
    ax.set_yticks([])
    ax.set_xlabel("함량 (mg/100g)")
    ax.set_title("단일 식품 통합 조회 — Textured vegetable protein (fdc_id 2707451)\n"
                 "Total isoflavones 166.94 = Genistein + Daidzein + Glycitein (합산 정확 일치)",
                 fontweight="bold")
    save(fig, "fig6_single_food_isoflavone.png")


# ── fig7. Stage 2 적재 처리량 (행/초) ───────────────────────────
def fig_load_perf():
    rows = [
        ("food\n(LOAD)", 81_455, NAVY),
        ("sr_legacy\n(Python)", 70_845, TEAL),
        ("food_nutrient\n(LOAD)", 65_996, NAVY),
        ("survey\n(Python)", 45_267, TEAL),
        ("nutrient\n(Python)", 39_750, TEAL),
        ("branded_food\n(pandas)", 2_302, ORANGE),
    ]
    labels = [r[0] for r in rows]
    vals = [r[1] for r in rows]
    colors = [r[2] for r in rows]
    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    bars = ax.bar(labels, vals, color=colors)
    ax.set_ylabel("처리량 (행/초)")
    ax.set_title("Stage 2 적재 처리량 — LOAD(파랑) 최고속,\nbranded_food(pandas, 주황)는 정확성 위해 속도 희생",
                 fontweight="bold")
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 1500, f"{v:,}", ha="center", fontsize=8)
    ax.margins(y=0.15)
    save(fig, "fig7_load_perf.png")


if __name__ == "__main__":
    fig_table_rows()
    fig_match_rate()
    fig_class()
    fig_daidzein()
    fig_datatype()
    fig_single_food()
    fig_load_perf()
    print("done")
