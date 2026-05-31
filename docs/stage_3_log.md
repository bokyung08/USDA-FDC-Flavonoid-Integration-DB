# Stage 3 — xlsx 임시 테이블 적재 (실시간 사고 로그)

## 0. 목적과 전략

### 무엇을
`USDA food flavonoid.xlsx` 3개 시트 → `tmp_flavdesc` / `tmp_mainfooddesc` / `tmp_flavval` 임시 테이블 적재.

| 시트 | 데이터 행 | 대상 테이블 | 후속 역할 |
|---|---:|---|---|
| FLAVDESC | 37 | tmp_flavdesc | Stage 4 — nutrient INSERT 원본 |
| MAINFOODDESC | 7,083 | tmp_mainfooddesc | food_code 사전 (2017년 버전) |
| FLAVVAL | 262,071 | tmp_flavval | Stage 5 — food_nutrient 통합 INSERT 원본 |

### 왜 임시 테이블로 분리?
- xlsx의 `food_code`는 USDA **2017년 버전** / `survey_fndds_food` 는 **2021년 버전** → 버전 불일치.
- 일단 임시 테이블에 모두 수용 → Stage 5에서 JOIN → Stage 6에서 unmatched 분리.

### Stage 2 lessons learned (이번 단계 선반영)

| 학습 | Stage 3 반영 |
|---|---|
| LOAD DATA INFILE은 quoted field 내 임베디드 newline에서 silent skip | 처음부터 Python(openpyxl + executemany) 사용 |
| TRUNCATE이 FK 참조 테이블에서 차단 | `DELETE FROM` 사용 (tmp_*는 사실 FK 자식이 없지만 일관성 유지) |
| 예약어 alias | `rows` → `row_cnt` |
| `sql_mode=''`, `foreign_key_checks=0` | 세션 설정 그대로 |
| 빈 셀 = NULL | `to_int/to_str/to_date/to_decimal` 변환 함수에서 일관 처리 |

## 1. 진행 상태 — ✅ Stage 3 완료

| 항목 | 상태 |
|---|:-:|
| xlsx 구조 점검 | ✅ |
| tmp_* DDL 확인 | ✅ |
| xlsx → CSV 추출 (산출물) | ✅ |
| tmp_flavdesc 적재 | ✅ 37 / 0.00s |
| tmp_mainfooddesc 적재 | ✅ 7,083 / 0.25s |
| tmp_flavval 적재 | ✅ 262,071 / 9.17s |
| 교차 검증 7개 | ✅ 모두 통과 |
| Stage 4·5 사전 예상치 일치 | ✅ 186,073 / 75,998 정확 일치 |

## 2. 사고 흐름

### 2-1. xlsx 구조 점검 (단계 1)
openpyxl read_only로 시트별 dimension/header/샘플 행 확인.

```text
FLAVDESC      max_row=38  cols=6  header=['Nutrient_code','Flavonoid_description','Flavonoid_class','Tagname','Unit','Decimals']
MAINFOODDESC  max_row=7084  cols=4  header=['Food_code','Start_date','End_date','Main_food_description']
FLAVVAL       max_row=262072  cols=5  header=['Food_code','Nutrient_Code','Start_date','End_date','Nutrient_value']
```

발견:
- 모든 시트에 헤더가 있음 → `max_row - 1` 이 실제 데이터 행수
- `Start_date`/`End_date` 는 datetime 객체로 들어옴 → MySQL DATE로 변환 필요
- `Tagname`은 일부 행에서 빈 문자열 `''` → NULL 처리 대상

### 2-2. DDL 점검 (단계 2)
| 테이블 | 컬럼 | 비고 |
|---|---|---|
| tmp_flavdesc | nutrient_code(PK) / flavonoid_description / flavonoid_class / tagname / unit / decimals | 일대일 매핑 |
| tmp_mainfooddesc | food_code(PK) / start_date / end_date / main_food_description | 일대일 매핑 |
| tmp_flavval | **id(auto_increment PK)** / food_code / nutrient_code / start_date / end_date / nutrient_value | id는 INSERT 시 생략 |

DDL에서 tmp_flavval에 `(food_code, nutrient_code)` UNIQUE 제약은 없음 → 중복 가능성 확인 필요 (검증 ⑦에서 0건 확인).

### 2-3. 추출+적재 합치기 결정 (단계 3)
명세서엔 "xlsx → CSV → 적재"라고 적혀 있지만, 데이터 정확성을 위해 **openpyxl로 읽으면서 동시에 (a) CSV 저장과 (b) DB INSERT를 모두 수행**하기로 결정.

- 장점: 인코딩 변환 단계가 줄고, CSV 산출물도 동시 확보 → 산출물(`scripts/_run/xlsx_csv/*.csv`) 보고서에 첨부 가능.
- 코드: [scripts/05_extract_and_load_xlsx.py](../scripts/05_extract_and_load_xlsx.py)

### 2-4. ❗ 1행 차이 이슈 → 명세 표기 차이로 결론 (단계 4)
첫 실행 결과:
```
[tmp_flavdesc]    inserted=37   table_count=37   elapsed=0.00s   (기대 38)
[tmp_mainfooddesc]inserted=7,083 table_count=7,083 elapsed=0.25s (기대 7,083)
[tmp_flavval]     inserted=262,071 table_count=262,071 elapsed=9.17s (기대 262,071)
```

FLAVDESC만 -1 차이 발생. 원본 시트 전체 dump 결과:
- row 1 = 헤더 / row 2~38 = 데이터 37행
- 명세 "FLAVDESC 38행"은 **헤더 포함 raw row 수**, 실제 데이터는 37행.
- MAINFOODDESC/FLAVVAL는 명세 수치가 데이터 행수와 일치 (헤더 미포함).

**결론**: 데이터 손실 없음. 명세서 표기 차이일 뿐. 37행 정확.

### 2-5. 교차 검증 (단계 5) — Stage 4/5 사전 예상치 검증

| 검증 | 쿼리 의도 | 결과 | 평가 |
|---|---|---:|---|
| ① 행수 | tmp_* 3개 행 수 | 37 / 7,083 / 262,071 | ✓ |
| ② nutrient 충돌 | tmp_flavdesc.nutrient_code ∩ nutrient.id | **0** | Stage 4 안전 ✓ |
| ③ Stage 5 매칭 | tmp_flavval JOIN survey_fndds_food | **matched 186,073 / unmatched 75,998** | **명세 정확 일치 ✓** |
| ④ 영양소 수 | distinct nutrient_code (flavval ↔ flavdesc) | 37 vs 37 | ✓ |
| ⑤ orphan | flavval.nutrient_code 중 flavdesc에 없는 것 | **0** | 무결성 ✓ |
| ⑥ 버전 비교 | MAINFOODDESC(2017) vs survey(2021) 공통 food_code | 5,029 / 7,083 | 2,054건 2017→2021 폐기 추정 |
| ⑦ 중복 | (food_code, nutrient_code) 동일 조합 | **0** | tmp_flavval에 자연 UNIQUE 성립 |

**핵심 결과**: 명세서가 예고한 **186,073행 INSERT + 75,998행 unmatched** 수치가 정확히 재현됨 → Stage 5에서 그대로 진행하면 됨.

## 3. 트러블슈팅 로그

이번 Stage는 Stage 2의 lessons learned 선반영 덕에 큰 사고 없음. 발생한 1건만 기록.

### T-3-1. FLAVDESC 행수 1 부족 (해프닝)
- 증상: 명세 "38행" vs 적재 37행
- 진단: 시트의 max_row=38, row 1=헤더, 데이터=37행. 명세는 헤더 포함 raw row 수치였음.
- 결정: 적재 결과 37이 정확. 문서에 명시.

(이외 LOAD DATA 한계, TRUNCATE FK 차단, 예약어 등은 Stage 2에서 이미 해결되어 본 단계에서 재발 없음.)

## 4. 산출물

| 파일 | 역할 |
|---|---|
| [../scripts/05_extract_and_load_xlsx.py](../scripts/05_extract_and_load_xlsx.py) | xlsx → CSV → tmp_* 통합 스크립트 |
| [../scripts/_run/stage3_verify.sql](../scripts/_run/stage3_verify.sql) | 교차 검증 쿼리 7종 |
| `../scripts/_run/xlsx_csv/flavdesc.csv` | FLAVDESC CSV 산출물 |
| `../scripts/_run/xlsx_csv/mainfooddesc.csv` | MAINFOODDESC CSV 산출물 |
| `../scripts/_run/xlsx_csv/flavval.csv` | FLAVVAL CSV 산출물 |

## 5. 성능

| 시트 | 행 수 | 시간 | 행/초 |
|---|---:|---:|---:|
| FLAVDESC | 37 | 0.00s | — |
| MAINFOODDESC | 7,083 | 0.25s | 28,332 |
| FLAVVAL | 262,071 | 9.17s | 28,579 |
| **합계** | **269,191** | **9.42s** | **28,572** |

## 6. 데이터 품질 평가

| 항목 | 결과 |
|---|---|
| 적재 정확성 | 명세 일치 (FLAVDESC는 헤더 표기 차이) |
| NULL 처리 | 빈 셀(`tagname=''` 등) → NULL 변환 OK |
| 날짜 변환 | datetime → DATE 정상 |
| 중복 | tmp_flavval에 (food_code, nutrient_code) 자연 UNIQUE |
| Stage 4/5 사전 시뮬레이션 | 0 충돌 / 186,073 매칭 / 75,998 unmatched — 명세 정확 일치 |

## 7. 다음 단계 — Stage 4 진입

**Stage 4 — nutrient 테이블 확장**:
1. `nutrient` 테이블에 `is_flavonoid` (이미 DDL 포함, default 0) / `flavonoid_class` 컬럼 → DDL 확인 완료, 이미 존재.
2. **충돌 검증**: `tmp_flavdesc.nutrient_code ∩ nutrient.id` = 0 ✓ 사전 확인 완료.
3. INSERT:
   ```sql
   INSERT INTO nutrient (id, name, unit_name, is_flavonoid, flavonoid_class)
   SELECT nutrient_code, flavonoid_description, unit, 1, flavonoid_class
   FROM tmp_flavdesc;
   ```
   기대: 37행 INSERT.
4. 검증: nutrient 총 행수 477 + 37 = **514**, `WHERE is_flavonoid=1` 37건.
