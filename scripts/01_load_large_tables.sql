-- ============================================================
-- Stage 2 (방법 A) : LOAD DATA INFILE — 대용량 테이블
-- 대상: food (2,085,341행), food_nutrient (≈수천만행)
-- 적재 순서: food → (nutrient/survey/sr_legacy/branded) → food_nutrient
-- ============================================================

-- 사전 설정: 세션 단위 최적화
USE usda_fdc;

SET SESSION sql_mode = '';                 -- 빈 문자열을 0이 아닌 NULL로 처리하기 위해 STRICT 해제
SET SESSION unique_checks = 0;             -- 적재 중 유니크 검사 끔
SET SESSION foreign_key_checks = 0;        -- 적재 중 FK 검사 끔 (적재 후 다시 켜고 검증)
SET SESSION autocommit = 0;                -- 트랜잭션 묶음
SET GLOBAL  local_infile = 1;              -- LOCAL INFILE 허용 (서버측). 권한 필요.

-- ------------------------------------------------------------
-- 1) food.csv  (1순위)
--    컬럼: fdc_id, data_type, description, food_category_id, publication_date
--    NULL 표기: 빈 문자열 ""
-- ------------------------------------------------------------
TRUNCATE TABLE food;

LOAD DATA LOCAL INFILE 'data/raw/food.csv'
INTO TABLE food
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(fdc_id, data_type, @description, @food_category_id, @publication_date)
SET
  description       = NULLIF(@description, ''),
  food_category_id  = NULLIF(@food_category_id, ''),
  publication_date  = NULLIF(@publication_date, '');

COMMIT;

-- 적재 직후 행 수
SELECT 'food' AS tbl, COUNT(*) AS rows_loaded FROM food;
-- 예상: 2,085,340 행

-- ------------------------------------------------------------
-- 2) food_nutrient.csv  (★ 최후 적재 — 부모 테이블 모두 적재된 뒤 실행)
--    컬럼:
--    id, fdc_id, nutrient_id, amount, data_points, derivation_id,
--    min, max, median, loq, footnote, min_year_acquired, percent_daily_value
--    NULL 표기: 빈 문자열 ""
--    백틱 컬럼: `min`, `max`, `median`
-- ------------------------------------------------------------
-- ※ 이 블록은 nutrient/survey_fndds_food/sr_legacy_food/branded_food 적재가 끝난 뒤 실행할 것

TRUNCATE TABLE food_nutrient;

LOAD DATA LOCAL INFILE 'data/raw/food_nutrient.csv'
INTO TABLE food_nutrient
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
( id, fdc_id, nutrient_id, amount,
  @data_points, @derivation_id,
  @min_val, @max_val, @median_val,
  @loq, @footnote, @min_year_acquired, @pct_dv )
SET
  data_points         = NULLIF(@data_points, ''),
  derivation_id       = NULLIF(@derivation_id, ''),
  `min`               = NULLIF(@min_val, ''),
  `max`               = NULLIF(@max_val, ''),
  median              = NULLIF(@median_val, ''),
  loq                 = NULLIF(@loq, ''),
  footnote            = NULLIF(@footnote, ''),
  min_year_acquired   = NULLIF(@min_year_acquired, ''),
  percent_daily_value = NULLIF(@pct_dv, '');

COMMIT;

-- 적재 직후 행 수
SELECT 'food_nutrient' AS tbl, COUNT(*) AS rows_loaded FROM food_nutrient;

-- 세션 원복
SET SESSION foreign_key_checks = 1;
SET SESSION unique_checks      = 1;
SET SESSION autocommit         = 1;
