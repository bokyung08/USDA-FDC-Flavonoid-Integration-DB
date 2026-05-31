-- ============================================================
-- Stage 7 — 최종 검증 5개 항목 (보고서 본문 자료)
-- 실행: mysql --defaults-extra-file=C:/Users/bokyu/.my.cnf -t < 06_final_verification.sql
-- ============================================================
USE usda_fdc;

-- ============================================================
-- ① 테이블별 적재 행 수 (10개 테이블 전부)
-- ============================================================
SELECT '① 테이블별 적재 행 수' AS section;

SELECT 'food'                AS table_name, COUNT(*) AS row_cnt FROM food
UNION ALL SELECT 'nutrient',              COUNT(*) FROM nutrient
UNION ALL SELECT 'survey_fndds_food',     COUNT(*) FROM survey_fndds_food
UNION ALL SELECT 'sr_legacy_food',        COUNT(*) FROM sr_legacy_food
UNION ALL SELECT 'branded_food',          COUNT(*) FROM branded_food
UNION ALL SELECT 'food_nutrient',         COUNT(*) FROM food_nutrient
UNION ALL SELECT 'tmp_flavdesc',          COUNT(*) FROM tmp_flavdesc
UNION ALL SELECT 'tmp_mainfooddesc',      COUNT(*) FROM tmp_mainfooddesc
UNION ALL SELECT 'tmp_flavval',           COUNT(*) FROM tmp_flavval
UNION ALL SELECT 'unmatched_flavonoid',   COUNT(*) FROM unmatched_flavonoid;

-- ============================================================
-- ② Flavonoid 매핑 실패율
-- ============================================================
SELECT '② Flavonoid 매핑 실패율' AS section;

SELECT
  (SELECT COUNT(*) FROM tmp_flavval)                              AS total_flavval,
  (SELECT COUNT(*) FROM food_nutrient
        JOIN nutrient n ON food_nutrient.nutrient_id = n.id
        WHERE n.is_flavonoid = 1)                                 AS matched_in_food_nutrient,
  (SELECT COUNT(*) FROM unmatched_flavonoid)                      AS unmatched,
  ROUND(
    (SELECT COUNT(*) FROM unmatched_flavonoid) * 100.0
      / (SELECT COUNT(*) FROM tmp_flavval),
    2
  )                                                                AS unmatched_pct,
  ROUND(
    (SELECT COUNT(*) FROM food_nutrient
        JOIN nutrient n ON food_nutrient.nutrient_id = n.id
        WHERE n.is_flavonoid = 1) * 100.0
      / (SELECT COUNT(*) FROM tmp_flavval),
    2
  )                                                                AS matched_pct;

-- ============================================================
-- ③ Daidzein (nutrient_id=710) 함량 TOP 5
-- ============================================================
SELECT '③ Daidzein TOP 5' AS section;

SELECT
  fn.fdc_id,
  f.description,
  fn.amount AS daidzein_mg
FROM food_nutrient fn
JOIN food f ON fn.fdc_id = f.fdc_id
WHERE fn.nutrient_id = 710
ORDER BY fn.amount DESC
LIMIT 5;

-- ============================================================
-- ④ Flavonoid 클래스별 평균 함량
-- ============================================================
SELECT '④ Flavonoid 클래스별 평균 함량' AS section;

SELECT
  COALESCE(n.flavonoid_class, '(Total)') AS flavonoid_class,
  COUNT(*) AS row_cnt,
  ROUND(AVG(fn.amount), 4) AS avg_amount_mg,
  ROUND(MIN(fn.amount), 4) AS min_amount_mg,
  ROUND(MAX(fn.amount), 4) AS max_amount_mg
FROM food_nutrient fn
JOIN nutrient n ON fn.nutrient_id = n.id
WHERE n.is_flavonoid = 1 AND fn.amount IS NOT NULL
GROUP BY n.flavonoid_class
ORDER BY avg_amount_mg DESC;

-- ============================================================
-- ⑤ fdc_id 1건의 일반 영양소 + 플라보노이드 통합 조회
--   샘플: fdc_id = 2707451 (Textured vegetable protein, dry)
--   - 일반 영양소 65행 + 플라보노이드 37행 = 102행 보유
-- ============================================================
SELECT '⑤ fdc_id=2707451 통합 조회 (일반+플라보노이드)' AS section;

-- ⑤-1: 요약
SELECT
  f.fdc_id,
  f.description AS food_description,
  SUM(CASE WHEN n.is_flavonoid = 0 THEN 1 ELSE 0 END) AS normal_nutrients,
  SUM(CASE WHEN n.is_flavonoid = 1 THEN 1 ELSE 0 END) AS flavonoid_nutrients,
  COUNT(*) AS total_rows
FROM food_nutrient fn
JOIN food f ON fn.fdc_id = f.fdc_id
JOIN nutrient n ON fn.nutrient_id = n.id
WHERE fn.fdc_id = 2707451
GROUP BY f.fdc_id, f.description;

-- ⑤-2: 일반 영양소 TOP 15 (amount 기준)
SELECT '⑤-2 일반 영양소 TOP 15' AS subsection;
SELECT
  n.id AS nutrient_id,
  n.name AS nutrient_name,
  n.unit_name,
  fn.amount,
  n.is_flavonoid,
  n.flavonoid_class
FROM food_nutrient fn
JOIN nutrient n ON fn.nutrient_id = n.id
WHERE fn.fdc_id = 2707451 AND n.is_flavonoid = 0 AND fn.amount IS NOT NULL
ORDER BY fn.amount DESC
LIMIT 15;

-- ⑤-3: 플라보노이드 전체 (amount > 0 우선)
SELECT '⑤-3 플라보노이드 함량 (값 있는 것 우선)' AS subsection;
SELECT
  n.id AS nutrient_id,
  n.name AS nutrient_name,
  n.unit_name,
  fn.amount,
  n.is_flavonoid,
  n.flavonoid_class
FROM food_nutrient fn
JOIN nutrient n ON fn.nutrient_id = n.id
WHERE fn.fdc_id = 2707451 AND n.is_flavonoid = 1
ORDER BY fn.amount DESC, n.flavonoid_class, n.name;
