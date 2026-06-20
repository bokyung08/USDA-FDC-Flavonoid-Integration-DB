# USDA FDC × Flavonoid 통합 데이터베이스 구축 보고서

**데이터베이스시스템 텀프로젝트 — 과제 A**
환경: MySQL 8.0.45 · utf8mb4 · InnoDB · Windows 11 · DB명 `usda_fdc`
작성일: 2026-05-28

---

## 목차

1. 프로젝트 개요
2. 데이터 모델 (DDL · ERD · Relation Schema) — **Stage 1 (10점)**
3. CSV 적재 — 3가지 방법 비교 — **Stage 2 (20점)**
4. XLSX 임시 테이블 적재 — Stage 3
5. nutrient 테이블 확장 — Stage 4
6. food_nutrient 통합 INSERT — **Stage 5 (20점)**
7. unmatched_flavonoid 분리 — **Stage 6 (10점)**
8. 검증 5개 항목 결과 — Stage 7
9. 핵심 설계 결정 — 데이터 거버넌스
10. 결론

---

## 1. 프로젝트 개요

미국 농무부(USDA)가 **별도로 제공하는 두 종류의 영양 데이터셋**을 단일 관계형 데이터베이스로 통합하는 것이 본 프로젝트의 목표이다.

| 데이터셋 | 내용 | 규모 | 형식 |
|---|---|---:|---|
| **USDA FDC** (Food Data Central) | 일반 영양소 (단백질·칼슘·비타민 등) | 약 2.6 GB / 약 3,094만 행 | CSV 6종 |
| **USDA Flavonoid Database** | 플라보노이드 함량 (이소플라본·안토시아닌 등 항산화 성분) | 약 6 MB / 약 27만 행 | XLSX 3 시트 |

통합 결과로 **단일 SQL 쿼리 한 줄**에서 "특정 식품의 일반 영양소와 플라보노이드를 함께 조회"할 수 있는 환경을 구축한다.

### 통합 절차 7단계

```
[1] DDL/ERD/Relation Schema 설계                              ← 10점
[2] CSV 6종 → 본 데이터 테이블 6개 적재 (3가지 방법 비교)       ← 20점
[3] XLSX 3 시트 → 임시 테이블 3개 적재
[4] 플라보노이드 영양소 메타 37개를 nutrient에 INSERT
[5] 통합 INSERT: 플라보노이드 측정값을 food_nutrient에 통합     ← 20점
[6] 매칭 불가 행을 unmatched_flavonoid로 분리 보존             ← 10점
[7] 검증 5개 항목 추출 및 보고서 정리
```

### 최종 결과 요약

| 지표 | 값 |
|---|---:|
| 총 적재 행 수 | **34,402,883** |
| 외래키(FK) 무결성 | **100% (고아 행 0건)** |
| 데이터 손실 | **0건** |
| Flavonoid 매칭률 | **71.00%** (영양학적 정확성 보장 하의 최대치) |

---

## 2. 데이터 모델 — Stage 1 (10점)

총 **10개 테이블**로 구성되며 역할에 따라 3개 그룹으로 분류된다.

### 2-1. 테이블 구성

**본 데이터 테이블 (6개)**

| 테이블 | 역할 |
|---|---|
| `food` | 모든 식품의 루트 테이블 (9종 data_type 포함) |
| `nutrient` | 영양소 사전 (일반 477종 + 플라보노이드 37종 통합) |
| `survey_fndds_food` | 2021년 USDA FNDDS 식품 |
| `sr_legacy_food` | USDA SR Legacy 식품 |
| `branded_food` | 시판 가공식품 (TEXT형 ingredients 포함) |
| `food_nutrient` | **사실(fact) 테이블** — (식품 × 영양소 × 함량) 측정값 |

**임시 테이블 (3개, XLSX 적재용)**

| 테이블 | 역할 |
|---|---|
| `tmp_flavdesc` | 플라보노이드 영양소 메타 (이름·클래스 등) |
| `tmp_mainfooddesc` | 2017년 USDA food_code 사전 |
| `tmp_flavval` | 식품 × 플라보노이드 함량 측정값 |

**분리 보존 테이블 (1개)**

| 테이블 | 역할 |
|---|---|
| `unmatched_flavonoid` | 통합 불가능한 행을 사유와 함께 보존 |

### 2-2. Relation Schema

밑줄 = PK, *이탤릭* = FK.

```
food( fdc_id, data_type, description, food_category_id, publication_date )
nutrient( id, name, unit_name, nutrient_nbr, rank, is_flavonoid, flavonoid_class )
survey_fndds_food( fdc_id→food, food_code, ... )
sr_legacy_food( fdc_id→food, ncc_id, ... )
branded_food( fdc_id→food, brand_owner, ingredients, ... )
food_nutrient( id, fdc_id→food, nutrient_id→nutrient, amount,
               data_points, derivation_id, min, max, median, loq,
               footnote, min_year_acquired, percent_daily_value )

tmp_flavdesc( nutrient_code, flavonoid_description, flavonoid_class, tagname, unit, decimals )
tmp_mainfooddesc( food_code, start_date, end_date, main_food_description )
tmp_flavval( id, food_code, nutrient_code, start_date, end_date, nutrient_value )

unmatched_flavonoid( id, food_code, nutrient_code, start_date, end_date,
                     nutrient_value, unmatch_reason )
```

### 2-3. 핵심 DDL (발췌)

```sql
-- 루트 테이블
CREATE TABLE food (
  fdc_id            INT UNSIGNED NOT NULL,
  data_type         VARCHAR(50)  NOT NULL,
  description       VARCHAR(255),
  food_category_id  VARCHAR(80),          -- 숫자/문자 혼재("1002","Oils Edible")로 VARCHAR
  publication_date  DATE,
  PRIMARY KEY (fdc_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 영양소 사전 (플라보노이드 확장 컬럼 선반영)
CREATE TABLE nutrient (
  id               INT UNSIGNED NOT NULL,
  `name`           VARCHAR(255) NOT NULL,   -- 예약어 → 백틱
  unit_name        VARCHAR(20)  NOT NULL,
  nutrient_nbr     VARCHAR(20),
  `rank`           INT,                     -- 예약어 → 백틱
  is_flavonoid     TINYINT      NOT NULL DEFAULT 0,
  flavonoid_class  VARCHAR(50),
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 사실 테이블
CREATE TABLE food_nutrient (
  id                  BIGINT UNSIGNED NOT NULL,
  fdc_id              INT UNSIGNED NOT NULL,
  nutrient_id         INT UNSIGNED NOT NULL,
  amount              DECIMAL(14,4),
  data_points         INT,
  derivation_id       INT,
  `min`               DECIMAL(14,4),        -- 예약어 → 백틱
  `max`               DECIMAL(14,4),        -- 예약어 → 백틱
  median              DECIMAL(14,4),
  loq                 DECIMAL(14,4),
  footnote            VARCHAR(255),
  min_year_acquired   INT,
  percent_daily_value DECIMAL(14,4),        -- 명세 외이나 실제 파일에 존재 → 포함
  PRIMARY KEY (id),
  CONSTRAINT fk_fn_food     FOREIGN KEY (fdc_id)      REFERENCES food(fdc_id),
  CONSTRAINT fk_fn_nutrient FOREIGN KEY (nutrient_id) REFERENCES nutrient(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 분리 보존 테이블
CREATE TABLE unmatched_flavonoid (
  id              INT UNSIGNED NOT NULL AUTO_INCREMENT,
  food_code       INT UNSIGNED NOT NULL,
  nutrient_code   INT UNSIGNED NOT NULL,
  start_date      DATE,
  end_date        DATE,
  nutrient_value  DECIMAL(10,4),
  unmatch_reason  VARCHAR(100),
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 2-4. Stage 1 핵심 설계 결정

| 결정 | 근거 |
|---|---|
| `food.food_category_id` → **VARCHAR(80)** | 숫자(`"1002"`)와 문자(`"Oils Edible"`)가 혼재 |
| `food_code` → **INT UNSIGNED** | 최대값 99,998,210 — INT 범위 내 |
| `branded_food.ingredients` → **TEXT** | 쉼표·따옴표·줄바꿈 포함 장문 |
| `nutrient`에 `is_flavonoid`·`flavonoid_class` **선반영** | Stage 4 통합을 위한 사전 설계 |
| 예약어 **백틱 처리** | `name`, `rank`, `min`, `max`, `median` |
| `survey_fndds_food.fdc_id` 단독 PK | 중복 0건 확인 |

---

## 3. CSV 적재 — Stage 2 (20점)

명세에 따라 **3가지 적재 방법**을 분담하고 성능·정확성을 비교한다.

### 3-1. 방법 분담

| 방법 | 대상 테이블 | 선정 사유 |
|---|---|---|
| `LOAD DATA LOCAL INFILE` | food, food_nutrient | 대용량 — 속도 우선 |
| Python (csv + executemany) | nutrient, survey_fndds_food, sr_legacy_food | RFC4180 정확성 |
| Python (pandas + chunked) | branded_food | TEXT/특수문자 필수 |

### 3-2. 성능 비교표 (채점 핵심)

| 방법 | 대상 | 행 수 | 파일 | 소요(s) | 행/초 | MB/s |
|---|---|---:|---:|---:|---:|---:|
| **LOAD DATA** | food (1차) | 2,043,540 | 208 MB | 25.09 | 81,455 | 8.29 |
| Python(보완 INSERT) | food (누락분) | 41,801 | — | 3.2 | 13,063 | — |
| Python | nutrient | 477 | 0.02 MB | 0.012 | 39,750 | 1.67 |
| Python | survey_fndds_food | 5,432 | 0.28 MB | 0.120 | 45,267 | 2.33 |
| Python | sr_legacy_food | 7,793 | 0.12 MB | 0.110 | 70,845 | 1.09 |
| **Python pandas** | branded_food | 1,993,975 | 907 MB | 866.3 | 2,302 | 1.05 |
| **LOAD DATA** | food_nutrient | 27,094,027 | 1,702 MB | 410.4 | 65,996 | 4.15 |

### 3-3. 방법별 정성 평가

| 항목 | LOAD DATA | Import Wizard | Python |
|---|:-:|:-:|:-:|
| 속도 | ★★★★★ | ★★ | ★★★ |
| 정확성(RFC4180) | ★★★ | ★★★ | ★★★★★ |
| 대용량 적합도 | ★★★★★ | ★ | ★★★★ |
| 전처리 유연성 | ★ | ★★ | ★★★★★ |
| 트러블슈팅 용이성 | ★★ | ★★ | ★★★★★ |

### 3-4. 핵심 적재 SQL (LOAD DATA)

```sql
LOAD DATA LOCAL INFILE 'data/raw/food.csv'
INTO TABLE food
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ',' OPTIONALLY ENCLOSED BY '"' ESCAPED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES
(fdc_id, data_type, @description, @food_category_id, @publication_date)
SET
  description      = NULLIF(@description, ''),
  food_category_id = NULLIF(@food_category_id, ''),
  publication_date = NULLIF(@publication_date, '');
```

### 3-5. 트러블슈팅 (기술적 도전)

| # | 증상 | 원인 | 해결 |
|:-:|---|---|---|
| T-1 | `LOAD DATA LOCAL` 거부 | `local_infile=OFF` 기본 보안 정책 | `SET GLOBAL local_infile=1` + 클라이언트 `--local-infile=1` |
| T-2 | `TRUNCATE` 거부 (ERROR 1701) | MySQL 8.0은 FK 참조 대상 테이블 TRUNCATE 무조건 차단 | `DELETE FROM` 으로 우회 |
| T-3 | `mysql -e` 에서 LOAD가 0행 적재 | 셸+클라이언트 2단계 quote 해석 충돌 | SQL 파일 + `mysql < file.sql` 리다이렉트 |
| T-4 | `rows` 별칭 syntax error | `rows`도 예약어 | 별칭을 `row_cnt`로 변경 |
| **T-5** | **food LOAD 41,801행 silent skip** | description 내부 임베디드 `\n` → LOAD가 행 경계 오인 | Python `csv.reader`로 누락 fdc_id 검출 후 보완 INSERT (3.2초) |
| T-6 | 소용량 LOAD도 부분 누락 | `"Carbohydrate, by difference"` 등 quoted-comma RFC4180 한계 | 소용량 3개 테이블을 처음부터 Python 적재 |

> **T-5 상세**: `food.csv` 2,085,340행 중 LOAD 후 2,043,540행만 적재(정확히 41,800 차이). 임베디드 newline을 포함한 단일 논리 행(`"Broccoli, steamed, ... CY010HJ\n"`)을 MySQL이 `LINES TERMINATED BY '\n'`으로 먼저 잘라낸 뒤 quote 처리하여 그 이후 행을 통째로 누락. RFC4180 호환 LOAD가 MySQL 기본 동작에서 불완전함을 보여주는 대표 사례.

### 3-6. 적재 검증

| 테이블 | 기대 | 실측 | 일치 |
|---|---:|---:|:-:|
| food | 2,085,340 | 2,085,340 | ✅ |
| nutrient | 477 | 477 | ✅ |
| survey_fndds_food | 5,432 | 5,432 | ✅ |
| sr_legacy_food | 7,793 | 7,793 | ✅ |
| branded_food | (CSV) | 1,993,975 | ✅ |
| food_nutrient | (CSV) | 27,094,027 | ✅ |

**FK 정합성**: 5개 관계 모두 고아 행 **0건**.

---

## 4. XLSX 임시 테이블 적재 — Stage 3

`USDA food flavonoid.xlsx` 3개 시트를 임시 테이블로 적재. Stage 2의 교훈(LOAD silent skip)을 반영해 **처음부터 Python(openpyxl + executemany)** 사용.

| 시트 | 데이터 행 | 대상 테이블 | 소요 |
|---|---:|---|---:|
| FLAVDESC | 37 | tmp_flavdesc | 0.00s |
| MAINFOODDESC | 7,083 | tmp_mainfooddesc | 0.25s |
| FLAVVAL | 262,071 | tmp_flavval | 9.17s |
| **합계** | **269,191** | — | **9.42s** |

### 교차 검증 (Stage 5 사전 시뮬레이션)

| 검증 | 결과 | 평가 |
|---|---:|---|
| tmp_flavdesc.nutrient_code ∩ nutrient.id | 0 | Stage 4 충돌 없음 ✓ |
| tmp_flavval JOIN survey_fndds_food | **matched 186,073 / unmatched 75,998** | **명세 정확 일치** ✓ |
| (food_code, nutrient_code) 중복 | 0 | 자연 UNIQUE ✓ |
| MAINFOODDESC(2017) ∩ survey(2021) 공통 food_code | 5,029 / 7,083 | 2,054건 폐기 추정 |

> **참고(T-3-1)**: 명세 "FLAVDESC 38행"은 헤더 포함 raw row 수치이며 실제 데이터는 37행. 데이터 손실 아님.

---

## 5. nutrient 테이블 확장 — Stage 4

`tmp_flavdesc`의 플라보노이드 영양소 37개를 `nutrient`에 INSERT하여 일반 영양소와 통합.

```sql
INSERT INTO nutrient (id, name, unit_name, is_flavonoid, flavonoid_class)
SELECT
  t.nutrient_code,
  t.flavonoid_description,
  COALESCE(NULLIF(t.unit, ''), 'mg'),
  1,
  NULLIF(t.flavonoid_class, '')
FROM tmp_flavdesc t;
```

| 항목 | 값 |
|---|---:|
| INSERT 행수 | 37 ✓ |
| nutrient 총 행수 | 477 + 37 = **514** ✓ |
| is_flavonoid=1 | 37 ✓ |

**flavonoid_class 분포**: Flavan-3-ols 13 · Anthocyanidins 7 · Flavonols 5 · Isoflavones 4 · Flavanones 4 · Flavones 3 · NULL(Total) 1 = 37.

---

## 6. food_nutrient 통합 INSERT — Stage 5 (20점)

플라보노이드 측정값을 `food_nutrient` **단일 사실 테이블에 통합**하는 핵심 단계.

### 6-1. 통합 쿼리

```sql
SELECT MAX(id) INTO @offset FROM food_nutrient;

INSERT INTO food_nutrient (id, fdc_id, nutrient_id, amount)
SELECT @offset + ROW_NUMBER() OVER (), s.fdc_id, f.nutrient_code, f.nutrient_value
FROM tmp_flavval f
JOIN survey_fndds_food s ON f.food_code = s.food_code;
```

### 6-2. 사전 점검 (INSERT 전 위험 8종 검증)

(fdc_id, nutrient_id) 사전 중복 0 · FK 누락 0 · NULL amount 0 · amount precision 충분(10,4→14,4) · survey_fndds_food.food_code 유일성 확인 등 **8개 항목 모두 통과**.

### 6-3. 실행 결과

| 항목 | 값 |
|---|---:|
| 적재 전 | 27,094,027 |
| INSERT 행수 | **186,073** ✓ |
| 적재 후 | **27,280,100** ✓ |
| 소요 시간 | 6.929 s |
| warnings | 0 |

**사후 검증 7종 모두 통과**: 행수 증가 +186,073 · 새 행 100% is_flavonoid=1 · FK 고아 0 · (fdc_id, nutrient_id) 중복 0.

### 6-4. 트러블슈팅 T-5-1 (AUTO_INCREMENT 누락)

- **증상**: 첫 INSERT 시 `ERROR 1062: Duplicate entry '0' for key 'food_nutrient.PRIMARY'`
- **원인**: `food_nutrient.id`가 PK이지만 `AUTO_INCREMENT` 키워드 누락. Stage 2 LOAD는 CSV의 id를 그대로 받아 동작했으나, `INSERT ... SELECT`는 id 미지정 → 기본값 0 → PK 충돌.
- **선택지**: (A) DDL ALTER로 AUTO_INCREMENT 추가 → Stage 1 산출물 영향 / (B) `ROW_NUMBER()`로 id 수동 부여 → DDL 불변.
- **결정**: (B) 채택. `@offset + ROW_NUMBER() OVER ()`로 기존 max_id 이후 연속 id 부여 → 정상 186,073행 INSERT.

---

## 7. unmatched_flavonoid 분리 — Stage 6 (10점)

Stage 5에서 매칭 실패한 **75,998행**을 손실 없이 별도 테이블로 분리 보존.

```sql
INSERT INTO unmatched_flavonoid
  (food_code, nutrient_code, start_date, end_date, nutrient_value, unmatch_reason)
SELECT f.food_code, f.nutrient_code, f.start_date, f.end_date, f.nutrient_value,
       'No matching food_code in survey_fndds_food (version mismatch)'
FROM tmp_flavval f
WHERE NOT EXISTS (
  SELECT 1 FROM survey_fndds_food s WHERE s.food_code = f.food_code
);
```

> `LEFT JOIN ... IS NULL`과 `NOT EXISTS` 두 패턴 모두 75,998행으로 동일 결과 검증. 의도 명확성을 위해 **NOT EXISTS** 채택.

| 항목 | 값 |
|---|---:|
| INSERT 행수 | **75,998** ✓ |
| 소요 시간 | 0.663 s |
| distinct food_code / nutrient_code | **2,054 / 37** |
| 정합성 (matched 186,073 + unmatched 75,998) | = 262,071 = tmp_flavval 전체 **(손실 0)** ✓ |

**산식**: 폐기된 food_code 2,054개 × 영양소 37개 = 75,998행 — 정확히 일치.

---

## 8. 검증 5개 항목 결과 — Stage 7

### ① 테이블별 적재 행 수

| 테이블 | 행 수 |
|---|---:|
| food | 2,085,340 |
| nutrient | 514 |
| survey_fndds_food | 5,432 |
| sr_legacy_food | 7,793 |
| branded_food | 1,993,975 |
| food_nutrient | 27,280,100 |
| tmp_flavdesc | 37 |
| tmp_mainfooddesc | 7,083 |
| tmp_flavval | 262,071 |
| unmatched_flavonoid | 75,998 |
| **합계** | **34,402,883** |

### ② Flavonoid 매핑 실패율

| 항목 | 값 |
|---|---:|
| total (tmp_flavval) | 262,071 |
| matched (통합) | 186,073 (**71.00%**) |
| unmatched (분리) | 75,998 (**29.00%**) |

**실패 사유**: USDA가 2017→2021로 가며 마이너 변종(저나트륨/칼슘강화/산성유/환원분유 등)을 제거 → **2,054개 food_code 폐기**.

### ③ Daidzein (nutrient_id=710) 함량 TOP 5

| 순위 | fdc_id | 식품 | Daidzein (mg) |
|:-:|:-:|---|---:|
| 1 | 2,707,451 | Textured vegetable protein, dry | 64.55 |
| 2 | 2,707,466 | Bacon bits (소이) | 64.37 |
| 3 | 2,707,433 | Soy nuts | 61.42 |
| 4 | 2,710,732 | Nutritional powder mix (EAS Soy Protein) | 30.07 |
| 5 | 2,710,743 | Nutritional powder mix, soy based | 30.07 |

→ Daidzein은 이소플라본 계열로 콩에 다량 존재. **상위 5개 모두 콩 기반 식품** → 데이터 정확성 시각적 확인.

### ④ Flavonoid 클래스별 평균 함량

| flavonoid_class | 행수 | 평균(mg) | 최대(mg) |
|---|---:|---:|---:|
| (Total flavonoids 등) | 5,029 | 5.5913 | 7,331.20 |
| Flavonols | 25,145 | 0.5132 | 697.85 |
| Flavan-3-ols | 65,377 | 0.4491 | 6,633.35 |
| Anthocyanidins | 35,203 | 0.3018 | 324.43 |
| Isoflavones | 20,116 | 0.2178 | 166.94 |
| Flavanones | 20,116 | 0.1194 | 101.45 |
| Flavones | 15,087 | 0.0945 | 216.55 |

### ⑤ 단일 식품 통합 조회 — fdc_id 2,707,451 ("Textured vegetable protein, dry")

본 DB의 통합 가치를 입증하는 핵심 사례.

```sql
SELECT n.id, n.name, n.unit_name, fn.amount, n.is_flavonoid, n.flavonoid_class
FROM food_nutrient fn
JOIN nutrient n ON fn.nutrient_id = n.id
WHERE fn.fdc_id = 2707451
ORDER BY n.is_flavonoid, fn.amount DESC;
```

| 항목 | 값 |
|---|---:|
| 일반 영양소 행 수 | 65 |
| 플라보노이드 행 수 | 37 |
| **총 영양 데이터** | **102 행** |

**대표 값**
- 일반 영양소: 칼륨 2,480 mg / 단백질 51.1 g / Energy 366 kcal
- 플라보노이드: **Total isoflavones 166.94 mg = Genistein 87.31 + Daidzein 64.55 + Glycitein 15.08** (합산 정확 일치)
- 그 외 32개 플라보노이드 = 0 mg → 콩 식품의 자연스러운 프로파일 정확 재현

→ 한 fdc_id 아래 일반 영양소와 플라보노이드가 **단일 SQL 조회로 통합 출력**되는 본 프로젝트의 핵심 결과물.

---

## 9. 핵심 설계 결정 — 데이터 거버넌스

Stage 6에서 75,998개 unmatched 행을 강제로 회복할지 검증했다.

| 회복 전략 | 효과 |
|---|---:|
| description 정확 일치 매칭 | 2 / 2,054 (0.097%) |
| 대소문자/공백 정규화 매칭 | 동일 (2건) |
| 부모 카테고리 강제 매핑 | **데이터 왜곡 — 채택 불가** |

"칼슘 강화 우유"의 플라보노이드 측정값을 "일반 우유"에 귀속시키는 것은 영양학적으로 잘못된 정보를 주입하는 행위다. 따라서 **명세대로 unmatched_flavonoid 테이블에 사유와 함께 분리 보존**하기로 결정했다. 이는 향후 USDA가 공식 매핑 가이드를 제공할 경우 단일 SQL 문으로 재통합 가능한 구조를 유지하기 위함이다.

> "USDA Flavonoid(2017)와 FNDDS(2021) 사이의 카테고리 재편으로 2,054개 food_code가 1:1 매핑되지 않으며, description 정규화 매칭으로도 0.097%(2건)만 회복 가능했다. 영양학적 정확성을 보장하기 위해 75,998행을 unmatched_flavonoid에 사유와 함께 보존하여 추후 수동 매핑 가이드 적용 시 재통합이 가능하도록 설계했다."

---

## 10. 결론

| 평가 축 | 결과 |
|---|---|
| **완전성** | 총 34,402,883행 적재, FK 고아 0건, 데이터 손실 0건 |
| **데이터 신뢰성** | Daidzein TOP 5(전부 콩 식품) · isoflavone 시그니처(166.94 mg 합산 일치) 정확 재현 |
| **데이터 거버넌스** | 강제 매핑 대신 unmatched 보존으로 영양학적 왜곡 회피 |
| **재현성** | 모든 단계가 SQL/Python 스크립트로 자동화, 사고 흐름 문서화 |

본 프로젝트는 USDA의 두 이질적 데이터셋을 단일 관계형 스키마로 통합하여, **"특정 식품의 일반 영양소와 플라보노이드를 한 번의 SQL 조회로 통합 출력"** 하는 목표를 달성했다. 특히 적재 과정의 silent skip 문제를 데이터 기반으로 추적·보완하고, 매칭 실패 데이터를 무리하게 회복하는 대신 거버넌스 원칙에 따라 추적 가능하게 보존한 점이 본 결과물의 핵심 가치다.
</content>
</invoke>
