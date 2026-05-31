-- ============================================================
-- Stage 2 적재 검증
--   ① 테이블별 행 수
--   ② FK 정합성 (고아 행 0 검증)
--   ③ NULL/유효성 표본 검사
-- ============================================================
USE usda_fdc;

-- ① 행 수 (보고서 표 1 자료)
SELECT 'food'              AS tbl, COUNT(*) AS row_cnt FROM food
UNION ALL SELECT 'nutrient',           COUNT(*) FROM nutrient
UNION ALL SELECT 'survey_fndds_food',  COUNT(*) FROM survey_fndds_food
UNION ALL SELECT 'sr_legacy_food',     COUNT(*) FROM sr_legacy_food
UNION ALL SELECT 'branded_food',       COUNT(*) FROM branded_food
UNION ALL SELECT 'food_nutrient',      COUNT(*) FROM food_nutrient;

-- 기대 행수 비교 가이드
-- food                : 2,085,340
-- nutrient            :       477
-- survey_fndds_food   :     5,432
-- sr_legacy_food      :     7,793
-- branded_food        : (브랜드 식품 수, CSV 행 수와 일치해야 함)
-- food_nutrient       : (CSV 행 수와 일치해야 함)

-- ② FK 정합성 — 고아 행이 있으면 0이 아님
SELECT
  (SELECT COUNT(*) FROM survey_fndds_food s LEFT JOIN food f ON s.fdc_id=f.fdc_id WHERE f.fdc_id IS NULL)        AS orphan_survey_fndds,
  (SELECT COUNT(*) FROM sr_legacy_food    s LEFT JOIN food f ON s.fdc_id=f.fdc_id WHERE f.fdc_id IS NULL)        AS orphan_sr_legacy,
  (SELECT COUNT(*) FROM branded_food      b LEFT JOIN food f ON b.fdc_id=f.fdc_id WHERE f.fdc_id IS NULL)        AS orphan_branded,
  (SELECT COUNT(*) FROM food_nutrient    fn LEFT JOIN food f ON fn.fdc_id=f.fdc_id WHERE f.fdc_id IS NULL)        AS orphan_fn_food,
  (SELECT COUNT(*) FROM food_nutrient    fn LEFT JOIN nutrient n ON fn.nutrient_id=n.id WHERE n.id IS NULL)       AS orphan_fn_nutrient;

-- ③ NULL 표본 — food_nutrient 의 NULL 컬럼 비율 (적재 정상성 확인)
SELECT
  SUM(amount IS NULL)              AS null_amount,
  SUM(data_points IS NULL)         AS null_data_points,
  SUM(derivation_id IS NULL)       AS null_derivation_id,
  SUM(`min` IS NULL)               AS null_min,
  SUM(`max` IS NULL)               AS null_max,
  SUM(median IS NULL)              AS null_median,
  SUM(loq IS NULL)                 AS null_loq,
  SUM(footnote IS NULL)            AS null_footnote,
  SUM(min_year_acquired IS NULL)   AS null_min_year,
  SUM(percent_daily_value IS NULL) AS null_pct_dv
FROM food_nutrient;

-- ④ data_type 별 food 분포 (참고)
SELECT data_type, COUNT(*) AS cnt
FROM food
GROUP BY data_type
ORDER BY cnt DESC;
