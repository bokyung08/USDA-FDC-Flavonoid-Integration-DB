-- ============================================================
-- Stage 2 (방법 B) : MySQL Import Wizard 사용 — 소용량 테이블
-- 대상: nutrient (477), survey_fndds_food (5,432), sr_legacy_food (7,793)
-- ------------------------------------------------------------
-- ▶ 권장 절차 (MySQL Workbench Wizard):
--   1) 좌측 스키마에서 해당 테이블 우클릭 → "Table Data Import Wizard"
--   2) CSV 파일 선택 → Next
--   3) "Use existing table"의 usda_fdc.<table> 선택 → Next
--   4) Encoding=utf-8, Field Separator=, , Enclose By=" , Line Separator=LF → Next
--   5) Column mapping 확인 (모두 매핑되었는지) → Next → Finish
-- ▶ Wizard 적재 후 검증을 위해 동일한 결과를 내는 SQL을 아래에 함께 포함.
--    (보고서 비교를 위해 Wizard 실행 시간을 별도 기록 필요)
-- ============================================================

USE usda_fdc;

SET SESSION sql_mode = '';
SET SESSION foreign_key_checks = 0;
SET SESSION unique_checks      = 0;
SET SESSION autocommit         = 0;

-- ------------------------------------------------------------
-- A) nutrient.csv (Wizard 대안 SQL — 동등 결과 검증용)
--    컬럼: id, name, unit_name, nutrient_nbr, rank
--    백틱: `name`, `rank`
-- ------------------------------------------------------------
TRUNCATE TABLE nutrient;

LOAD DATA LOCAL INFILE 'data/raw/nutrient.csv'
INTO TABLE nutrient
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
( id, @name, @unit_name, @nutrient_nbr, @rank_val )
SET
  `name`        = NULLIF(@name, ''),
  unit_name     = NULLIF(@unit_name, ''),
  nutrient_nbr  = NULLIF(@nutrient_nbr, ''),
  `rank`        = NULLIF(@rank_val, '');

COMMIT;
SELECT 'nutrient' AS tbl, COUNT(*) AS rows_loaded FROM nutrient;  -- 예상: 477

-- ------------------------------------------------------------
-- B) survey_fndds_food.csv
--    컬럼: fdc_id, food_code, wweia_category_code, start_date, end_date
--    food_code: INT UNSIGNED
-- ------------------------------------------------------------
TRUNCATE TABLE survey_fndds_food;

LOAD DATA LOCAL INFILE 'data/raw/survey_fndds_food.csv'
INTO TABLE survey_fndds_food
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
( fdc_id, food_code, @wweia, @sd, @ed )
SET
  wweia_category_code = NULLIF(@wweia, ''),
  start_date          = NULLIF(@sd, ''),
  end_date            = NULLIF(@ed, '');

COMMIT;
SELECT 'survey_fndds_food' AS tbl, COUNT(*) AS rows_loaded FROM survey_fndds_food;  -- 예상: 5,432

-- ------------------------------------------------------------
-- C) sr_legacy_food.csv
--    컬럼: fdc_id, NDB_number
-- ------------------------------------------------------------
TRUNCATE TABLE sr_legacy_food;

LOAD DATA LOCAL INFILE 'data/raw/sr_legacy_food.csv'
INTO TABLE sr_legacy_food
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
( fdc_id, @ndb )
SET
  NDB_number = NULLIF(@ndb, '');

COMMIT;
SELECT 'sr_legacy_food' AS tbl, COUNT(*) AS rows_loaded FROM sr_legacy_food;  -- 예상: 7,793

-- 세션 원복
SET SESSION foreign_key_checks = 1;
SET SESSION unique_checks      = 1;
SET SESSION autocommit         = 1;
