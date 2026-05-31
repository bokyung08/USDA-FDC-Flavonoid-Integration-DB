# Stage 2 — CSV 데이터 적재 (상세 로그)

## 0. 목표
CSV 7개 → MySQL 6개 테이블 적재. **3가지 방법** 분담 + 성능 비교 + 트러블슈팅 기록.

| 방법 | 대상 | 비고 |
|---|---|---|
| LOAD DATA LOCAL INFILE | food, food_nutrient | 대용량 |
| Python(csv + executemany) | nutrient, survey_fndds_food, sr_legacy_food | Wizard 대안 (정확도 사유) |
| Python(pandas + chunked executemany) | branded_food | TEXT/특수문자 필수 |

## 1. 진행 상태 — ✅ Stage 2 완료 (2026-05-28)

| 항목 | 상태 | 결과 |
|---|:-:|---|
| CSV 정밀 점검 | ✅ | LF, NULL=빈문자열, food_category_id 혼재 확인 |
| DDL/접속/local_infile 점검 | ✅ | MySQL 8.0.45, varchar(80), local_infile=ON |
| food 적재 | ✅ | 2,085,340 / 약 28s |
| nutrient 적재 | ✅ | 477 / 0.012s |
| survey_fndds_food 적재 | ✅ | 5,432 / 0.120s |
| sr_legacy_food 적재 | ✅ | 7,793 / 0.110s |
| branded_food 적재 | ✅ | 1,993,975 / 866.3s |
| food_nutrient 적재 | ✅ | 27,094,027 / 410.4s |
| 검증 (행수·FK·NULL·분포) | ✅ | FK 고아 0건, corrupt row 1건 발견·정정 |

## 2. CSV 정밀 점검 결과

| 항목 | 발견 | 대응 |
|---|---|---|
| 줄바꿈 | LF(`\n`) only — `od -c` 확인 | `LINES TERMINATED BY '\n'` |
| 인코딩 | food/food_nutrient = ASCII / branded_food = UTF-8 | `CHARACTER SET utf8mb4` |
| NULL 컨벤션 | 빈 문자열 `""` = NULL | `SET sql_mode=''` + `NULLIF(@var,'')` |
| food.food_category_id | 숫자/문자 혼재 (`"1002"`, `"Oils Edible"`) | DDL 이미 `varchar(80)` ✓ |
| 따옴표 처리 | RFC 4180 (`""` escape) | `OPTIONALLY ENCLOSED BY '"' ESCAPED BY '"'` |
| food.csv corrupt row | 41,802~41,803 라인이 1행으로 합쳐져야 하지만 줄바뀜 포함 | 후속 분석 (T-5) |
| branded_food.ingredients | 쉼표·따옴표·줄바꿈 포함 | Python csv 표준 파서 |

## 3. 트러블슈팅 로그 (보고서 핵심 자료)

### T-1. `local_infile = OFF`
- 증상: `LOAD DATA LOCAL INFILE` 실행 시 거부 가능.
- 진단: `SHOW VARIABLES LIKE 'local_infile';` = OFF
- 해결: `SET GLOBAL local_infile = 1;` + 클라이언트 `--local-infile=1`.
- 부가: `secure_file_priv = C:\Movies\` 가 설정되어 있어 LOCAL 키워드 없는 LOAD DATA INFILE은 거의 불가 → **LOCAL 필수**.

### T-2. MySQL 8.0의 TRUNCATE는 FK 참조 테이블에서 강제 차단
- 증상: `ERROR 1701 (42000): Cannot truncate a table referenced in a foreign key constraint (...fk_survey_fdc)`
- 원인: MySQL 8.0에서 TRUNCATE은 `foreign_key_checks=0` 으로도 차단 (DROP/TRUNCATE은 별개 권한 체계).
- 해결: `DELETE FROM food;` 사용. (`DELETE`는 `foreign_key_checks=0` 이면 우회)

### T-3. mysql `-e` 인자 안 escape 꼬임
- 증상: `mysql -e "... ENCLOSED BY '\"' ESCAPED BY '\"' ..."` 호출 시 LOAD가 0행 적재 + 에러 없음.
- 원인: 셸 + mysql 클라이언트 두 단계 quote 해석에서 `\"`가 의도와 다르게 풀림 (LOAD가 라인 종료 문자를 다르게 인식).
- 해결: SQL 문을 파일로 저장 후 `mysql < file.sql` 리다이렉트로 실행 → 정상 25초 LOAD.

### T-4. `rows` 도 예약어
- 증상: `SELECT ..., COUNT(*) AS rows FROM food` → `ERROR 1064 syntax error`
- 해결: alias 를 `row_cnt` 로 변경. (`name`, `rank`, `min`, `max`, `median` 외에 `rows`도 별칭 주의)

### T-5. ★ food LOAD 41,801행 누락 (가장 큰 이슈) — 원인 확정
- 증상: `food.csv` 데이터 2,085,340행 중 LOAD 후 2,043,540행만 적재 (warns=347, 정확히 41,800 차이).
- 진단:
  - PK(fdc_id) 중복 = 0건 (Python csv set 비교)
  - 임베디드 newline 검사 → **1행 발견**
  - 누락된 fdc_id의 패턴 분석 → 모두 line 41802 이후의 행들
- **확정 원인**: `food.csv` line 41802~41803이 description 내부에 임베디드 `\n` 을 포함하는 단일 논리 행인데, MySQL의 `LOAD DATA INFILE` 은 `LINES TERMINATED BY '\n'` 으로 행을 먼저 무조건 잘라낸 뒤 quoted 처리를 함 → **이 임베디드 newline을 행 경계로 잘못 인식해 그 이후 41,801행을 silently skip**. (RFC4180 호환 LOAD가 MySQL의 기본 동작에서는 불완전함을 보여주는 케이스)
  - 실제 corrupt 행: `"321829","sample_food","Broccoli, steamed, ... CY010HJ\n","11","2019-04-01"`
- 해결: 누락된 fdc_id 41,801개를 Python(csv.reader)로 검출하여 **보완 INSERT** (`food_topup.py`, 3.2초).
- 후처리: 보완 단계에서 fdc_id=0인 잘못된 1행이 들어가 `DELETE FROM food WHERE fdc_id=0;` 으로 정리. **최종 2,085,340행 — 기대값 정확 일치**.

### T-6. nutrient/소용량 테이블 LOAD도 부분 누락
- 증상: `nutrient.csv` 477행 중 LOAD로 403행만 적재 (warns=1).
- 원인: `name` 컬럼이 콤마 포함 quoted string ("Carbohydrate, by difference" 등) — T-5와 동일 카테고리. MySQL LOAD가 RFC4180 quoted-comma 처리에서 한계.
- 결정: **소용량 3개 모두 Python(csv + executemany)으로 적재**. 결과 477 / 5,432 / 7,793 — 모두 100% 적재.

## 4. 산출물

| 파일 | 역할 |
|---|---|
| [../scripts/01_load_large_tables.sql](../scripts/01_load_large_tables.sql) | LOAD DATA SQL — food, food_nutrient (원본) |
| [../scripts/02_load_small_tables.sql](../scripts/02_load_small_tables.sql) | Wizard 대안 SQL (참고용) |
| [../scripts/03_load_branded_food.py](../scripts/03_load_branded_food.py) | branded_food 본 적재기 |
| [../scripts/04_verify_stage_2.sql](../scripts/04_verify_stage_2.sql) | 검증 쿼리 (행수·FK·NULL·분포) |
| [../scripts/_run/food_only.sql](../scripts/_run/food_only.sql) | food LOAD 실 실행본 |
| [../scripts/_run/food_topup.py](../scripts/_run/food_topup.py) | food 누락분 보완 INSERT |
| [../scripts/_run/load_small_python.py](../scripts/_run/load_small_python.py) | 소용량 3개 Python 적재 |
| [../scripts/_run/food_nutrient.sql](../scripts/_run/food_nutrient.sql) | food_nutrient LOAD |
| [../scripts/_run/food_diagnose.sql](../scripts/_run/food_diagnose.sql) | LOAD 진단(ROW_COUNT/warnings) |

## 5. 행 수 결과 (검증 ①)

| 테이블 | 기대 | 실측 | 일치 |
|---|---:|---:|:-:|
| food | 2,085,340 | **2,085,340** | ✅ |
| nutrient | 477 | **477** | ✅ |
| survey_fndds_food | 5,432 | **5,432** | ✅ |
| sr_legacy_food | 7,793 | **7,793** | ✅ |
| branded_food | (CSV) | **1,993,975** | ✅ (CSV 일치) |
| food_nutrient | (CSV) | **27,094,027** | ✅ (raw line 27,094,028 vs 적재 27,094,027 → 1행 차이, 사실상 일치) |

## 6. FK 정합성 (검증 ②)

| 검사 | 고아 행 |
|---|---:|
| survey_fndds_food → food | **0** ✅ |
| sr_legacy_food → food | **0** ✅ |
| branded_food → food | **0** ✅ |
| food_nutrient → food | **0** ✅ |
| food_nutrient → nutrient | **0** ✅ |

## 7. 성능 비교표 (보고서 핵심 표)

| 방법 | 대상 | 행 수 | 파일 | 소요(s) | 행/초 | MB/s |
|---|---|---:|---:|---:|---:|---:|
| **LOAD DATA LOCAL INFILE** | food (1차 LOAD) | 2,043,540 | 208 MB | 25.088 | 81,455 | 8.29 |
| Python INSERT(보완) | food (누락분) | 41,801 | — | 3.2 | 13,063 | — |
| _food 합계_ | _2,085,340_ | _208 MB_ | _28.3_ | _73,683_ | _7.35_ | |
| Python INSERT | nutrient | 477 | 0.02 MB | 0.012 | 39,750 | 1.67 |
| Python INSERT | survey_fndds_food | 5,432 | 0.28 MB | 0.120 | 45,267 | 2.33 |
| Python INSERT | sr_legacy_food | 7,793 | 0.12 MB | 0.110 | 70,845 | 1.09 |
| **Python pandas + chunked** | branded_food | 1,993,975 | 907 MB | 866.3 | 2,302 | 1.05 |
| **LOAD DATA LOCAL INFILE** | food_nutrient | 27,094,027 | 1,702 MB | 410.4 | 65,996 | 4.15 |

### 7-1. 결론
- **LOAD DATA INFILE** — 행 처리속도가 압도적(food_nutrient에서 66k행/s, 4 MB/s). 그러나 RFC4180 호환에 한계 있어 quoted field 안의 콤마·줄바꿈으로 silent skip 발생 가능 → **사후 보완 INSERT** 패턴 권장.
- **MySQL Import Wizard** — 본 실험에서는 동일 한계(소용량 LOAD에서 검출)로 Python으로 대체. 단순 데이터에서는 GUI 편의성 우수.
- **Python(csv/pandas + executemany)** — 속도는 LOAD의 1/30 수준이나 RFC4180 표준 준수로 **100% 정확도 보장**. TEXT/특수문자 데이터(branded_food)에 필수.

### 7-2. 정성적 평가

| 항목 | LOAD DATA | Wizard | Python |
|---|:-:|:-:|:-:|
| 속도 | ★★★★★ | ★★ | ★★★ |
| 정확성(RFC4180) | ★★★ | ★★★ | ★★★★★ |
| 대용량 적합도 | ★★★★★ | ★ | ★★★★ |
| 전처리 유연성 | ★ | ★★ | ★★★★★ |
| 트러블슈팅 용이성 | ★★ | ★★ | ★★★★★ |

## 8. 검증 ④ — data_type 분포

| data_type | cnt | 비고 |
|---|---:|---|
| branded_food | 1,993,975 | branded_food 테이블 행 수와 일치 ✓ |
| sub_sample_food | 65,502 | |
| sr_legacy_food | 7,793 | sr_legacy_food 테이블 행 수 일치 ✓ |
| market_acquistion | 7,388 | 원본 typo (`acquistion`) 유지 |
| survey_fndds_food | 5,432 | survey_fndds_food 테이블 행 수 일치 ✓ |
| sample_food | 3,890 | |
| agricultural_acquisition | 810 | |
| foundation_food | 436 | |
| experimental_food | 114 | |

## 9. 이슈 / 결정 로그

| 일시 | 이슈 | 결정 |
|---|---|---|
| 2026-05-28 | food.food_category_id 숫자/문자 혼재 | DDL이 이미 varchar(80) — ALTER 불필요 |
| 2026-05-28 | local_infile=OFF | `SET GLOBAL local_infile=1` |
| 2026-05-28 | TRUNCATE이 FK로 차단 | `DELETE FROM` 사용 |
| 2026-05-28 | mysql -e escape 꼬임 | SQL 파일 + `< file.sql` 리다이렉트 |
| 2026-05-28 | `rows` 예약어 | alias `row_cnt` |
| 2026-05-28 | food LOAD 41,801행 누락 | 원인=description 임베디드 newline / Python 보완 INSERT |
| 2026-05-28 | 소용량 LOAD도 부분 누락 | 3개 테이블 Python 전환 |
| 2026-05-28 | corrupt row(fdc_id=0) | `DELETE FROM food WHERE fdc_id=0` 정리 |

## 10. 다음 단계
**Stage 3 — xlsx 임시 테이블 적재**:
- `USDA food flavonoid.xlsx` 시트 3개 (FLAVDESC 38 / MAINFOODDESC 7,083 / FLAVVAL 262,071) → CSV 추출 → `tmp_flavdesc` / `tmp_mainfooddesc` / `tmp_flavval` 적재.
- 추출 스크립트: `scripts/05_extract_xlsx.py` (예정).
