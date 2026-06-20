# USDA FDC × Flavonoid 통합 데이터베이스 구축 — 프로젝트 개요

데이터베이스시스템 텀프로젝트 과제 A · MySQL 8.0 · 2026년 5월 완료

> 본 문서는 프로젝트를 처음 접하는 사람이 **전체 그림과 결과를 한 페이지에서 이해**할 수 있도록 작성되었습니다.
> 단계별 상세 로그는 [PROGRESS.md](PROGRESS.md) → 각 [stage_N_log.md](.) 로 이어집니다.

---

## 1. 프로젝트 목적

미국 농무부(USDA)가 별도로 제공하는 두 종류의 영양 데이터셋을 단일 관계형 데이터베이스로 통합하는 것이 본 프로젝트의 목표이다.

| 데이터셋 | 출처 | 규모 | 특징 |
|---|---|---:|---|
| **USDA FDC** (Food Data Central) | 일반 영양소 데이터 (CSV 6종) | 약 2.6 GB / 약 3,094만 행 | 식품 × 일반 영양소 (단백질, 칼슘, 비타민 등) |
| **USDA Flavonoid Database** | 플라보노이드 함량 데이터 (XLSX, 3 시트) | 약 6 MB / 약 27만 행 | 식품 × 플라보노이드 (이소플라본, 안토시아닌 등 항산화 성분) |

통합의 결과로 **단일 SQL 쿼리 한 줄**에서 "특정 식품의 일반 영양소와 플라보노이드를 모두 함께 조회"할 수 있는 환경을 구축한다.

---

## 2. 데이터 모델

총 10개 테이블로 구성된다. 역할에 따라 3개 그룹으로 분류된다.

### 2-1. 본 데이터 테이블 (6개)

| 테이블 | 역할 |
|---|---|
| `food` | 모든 식품의 루트 테이블 (브랜드, USDA 표준, FNDDS 등 9종 data_type 포함) |
| `nutrient` | 영양소 사전. 본 프로젝트에서 일반 영양소 477종 + 플라보노이드 37종을 통합 |
| `survey_fndds_food` | 2021년 USDA FNDDS 식품 |
| `sr_legacy_food` | USDA SR Legacy 식품 |
| `branded_food` | 시판 가공식품 (TEXT 형 ingredients 컬럼 포함) |
| `food_nutrient` | **사실(fact) 테이블**. (식품 × 영양소 × 함량) 측정값을 저장 |

### 2-2. 임시 테이블 (3개) — XLSX 적재용

| 테이블 | 역할 |
|---|---|
| `tmp_flavdesc` | 플라보노이드 영양소 메타 (이름, 클래스 등) |
| `tmp_mainfooddesc` | 2017년 USDA food_code 사전 |
| `tmp_flavval` | 식품 × 플라보노이드 함량 측정값 |

### 2-3. 분리 보존 테이블 (1개)

| 테이블 | 역할 |
|---|---|
| `unmatched_flavonoid` | 본 데이터 통합이 불가능한 행을 사유와 함께 보존하는 테이블 |

---

## 3. 통합 절차 — 7단계

```
[1] DDL/ERD/Relation Schema 설계
       │
[2] CSV 7개 → 본 데이터 테이블 6개 적재          ← 채점 20점
       │
[3] XLSX 3 시트 → 임시 테이블 3개 적재
       │
[4] 플라보노이드 영양소 메타 37개를 nutrient에 INSERT
       │
[5] 통합 INSERT: 플라보노이드 측정값을 food_nutrient에 통합   ← 채점 20점
       │
[6] 통합 불가능한 행을 unmatched_flavonoid로 분리            ← 채점 10점
       │
[7] 검증 5개 항목 추출 및 보고서 정리
```

각 단계의 결과는 다음 단계의 입력이 되며, 후 단계로 갈수록 앞 단계에서 얻은 학습이 반영된다.

---

## 4. 단계별 결과 요약

| Stage | 작업 | 채점 | 결과 |
|:-:|---|:-:|---|
| 1 | 테이블 10개 설계 | 10 | DDL/ERD/Relation Schema 작성 완료 |
| 2 | CSV → 6 테이블 적재 | 20 | **31,189,044 행** 적재 / FK 고아 0건 |
| 3 | XLSX → 3 임시 테이블 | — | 269,191 행 적재 / 9.4초 |
| 4 | 플라보노이드 영양소 INSERT | — | 37 행 INSERT → nutrient 514 행 |
| 5 | food_nutrient 통합 INSERT | 20 | **186,073 행 INSERT** (매칭률 71.00%) |
| 6 | unmatched 분리 | 10 | **75,998 행** 분리 / 데이터 손실 0건 |
| 7 | 검증 5개 추출 | — | 5개 항목 모두 완료 |

**최종 적재 행 수: 34,402,883** / **외래키 무결성: 100%** / **데이터 손실: 0**

---

## 5. 적재 방법 비교 (Stage 2 — 채점 핵심)

본 프로젝트는 명세에 따라 세 가지 적재 방법을 비교한다.

| 방법 | 처리 속도 | 데이터 정확성 | 적합 대상 |
|---|---:|:-:|---|
| `LOAD DATA LOCAL INFILE` | **최고** (66k~81k 행/초) | RFC4180 한계로 일부 누락 가능 | 대용량 정형 CSV |
| MySQL Import Wizard | 보통 | LOAD와 동일 한계 | GUI 환경의 소용량 데이터 |
| **Python (csv/pandas + executemany)** | 보통 (2k~70k 행/초) | **100% 정확** | 비정형 데이터, 정확성 우선 |

| 테이블 | 적용 방법 | 소요 시간 | 적재 행수 |
|---|---|---:|---:|
| food | LOAD + Python 보완 | 28.3 s | 2,085,340 |
| food_nutrient | LOAD | 410.4 s | 27,094,027 |
| nutrient, survey_fndds_food, sr_legacy_food | Python | < 1 s | 13,702 |
| branded_food | Python (pandas chunked) | 866.3 s | 1,993,975 |

**결론**: 속도와 정확성의 명확한 트레이드오프가 존재한다. 본 프로젝트는 **LOAD를 1차 적재로 사용하고 Python으로 누락분을 보완**하는 하이브리드 패턴을 채택했다.

---

## 6. 트러블슈팅 8건

기술적 도전과 그 해결 과정을 정리한다.

| # | 단계 | 증상 | 원인 | 해결 |
|:-:|:-:|---|---|---|
| T-1 | 2 | `LOAD DATA LOCAL INFILE` 실행 거부 | MySQL의 `local_infile=OFF` 기본 보안 정책 | `SET GLOBAL local_infile=1` + 클라이언트 `--local-infile=1` |
| T-2 | 2 | `TRUNCATE` 실행 거부 | MySQL 8.0은 FK 참조 대상 테이블에서 TRUNCATE을 무조건 차단 | `DELETE FROM` 으로 우회 |
| T-3 | 2 | `mysql -e` 명령에서 LOAD가 0행 적재 | 셸과 mysql 클라이언트의 quote 해석 충돌 | SQL 파일 + `mysql < file.sql` 리다이렉트 방식으로 전환 |
| T-4 | 2 | `rows`를 별칭으로 사용 시 syntax error | `rows`도 MySQL 예약어 | `row_cnt` 등으로 변경 |
| T-5 | 2 | **food LOAD 시 41,801 행 silent skip** | `food.csv` 41,802행의 description 필드 내부에 임베디드 `\n` → LOAD가 행 동기화 상실 | Python `csv.reader` 로 누락 fdc_id를 검출해 보완 INSERT (3.2초) |
| T-6 | 2 | 소용량 테이블 LOAD에서도 부분 누락 | name 컬럼의 quoted-comma (`"Carbohydrate, by difference"`) RFC4180 한계 | 소용량 3개 테이블을 처음부터 Python으로 적재 |
| T-7 | 5 | `INSERT ... SELECT` 시 `Duplicate entry '0'` | `food_nutrient.id` 가 PK이지만 `AUTO_INCREMENT` 키워드 누락 | `@offset + ROW_NUMBER() OVER ()` 로 id 수동 부여 |
| T-8 | 3 | FLAVDESC 적재 행수가 명세(38)와 1행 차이 | 명세의 "38행"이 헤더 포함 표기 | 데이터 손실 없음. 표기 차이로 종결 |

**핵심 패턴**: 모든 트러블슈팅이 **(1) 증상 → (2) 데이터 기반 원인 추적 → (3) 우회 또는 보완 → (4) 검증** 의 4단계로 처리됐다.

---

## 7. 검증 5개 항목 결과 (Stage 7)

### 7-1. 테이블별 적재 행 수
위 §2·§4 참조.

### 7-2. Flavonoid 매핑 실패율
| 항목 | 값 |
|---|---:|
| total (tmp_flavval) | 262,071 |
| matched (food_nutrient 통합) | 186,073 (**71.00%**) |
| unmatched (분리) | 75,998 (**29.00%**) |

**실패 사유**: USDA가 2017년 → 2021년으로 가면서 마이너 변종 식품 카테고리(저나트륨/칼슘강화/산성유/환원분유 등)를 제거. 결과적으로 **2,054개 food_code** 가 2021년 데이터셋에서 폐기됨.

### 7-3. Daidzein 함량 상위 5개 식품

| 순위 | 식품 | Daidzein (mg) |
|:-:|---|---:|
| 1 | Textured vegetable protein, dry | 64.55 |
| 2 | Bacon bits (소이 베이컨 비츠) | 64.37 |
| 3 | Soy nuts | 61.42 |
| 4 | Nutritional powder mix (EAS Soy Protein) | 30.07 |
| 5 | Nutritional powder mix, soy based | 30.07 |

Daidzein은 이소플라본 계열로 콩에 다량 함유된다. 상위 5개 모두 콩 기반 식품이 출력되었다는 점에서 **데이터 정확성이 시각적으로 확인**된다.

### 7-4. Flavonoid 클래스별 평균 함량

| flavonoid_class | 데이터 행수 | 평균(mg) | 최대(mg) |
|---|---:|---:|---:|
| (Total: Total flavonoids 등) | 5,029 | 5.5913 | 7,331.20 |
| Flavonols | 25,145 | 0.5132 | 697.85 |
| Flavan-3-ols | 65,377 | 0.4491 | 6,633.35 |
| Anthocyanidins | 35,203 | 0.3018 | 324.43 |
| Isoflavones | 20,116 | 0.2178 | 166.94 |
| Flavanones | 20,116 | 0.1194 | 101.45 |
| Flavones | 15,087 | 0.0945 | 216.55 |

### 7-5. 단일 식품의 통합 조회 — fdc_id 2,707,451 ("Textured vegetable protein, dry")

본 DB의 통합 가치를 입증하는 핵심 사례.

| 항목 | 값 |
|---|---:|
| 일반 영양소 행 수 | 65 |
| 플라보노이드 행 수 | 37 |
| **총 영양 데이터** | **102 행** |

대표 값:
- 일반 영양소: 칼륨 2,480 mg / 단백질 51.1 g / Energy 366 kcal
- 플라보노이드: **Total isoflavones 166.94 mg** = Genistein 87.31 + Daidzein 64.55 + Glycitein 15.08 (**합산 정확 일치**)
- 그 외 (Anthocyanidins, Flavan-3-ols 등) = 0 mg → 콩 식품의 자연스러운 영양 프로파일

→ 한 fdc_id 아래에서 일반 영양소와 플라보노이드가 **단일 SQL 조회로 통합 출력**되는 본 프로젝트의 핵심 결과물.

---

## 8. 핵심 설계 결정 — 데이터 거버넌스

Stage 6에서 75,998개 unmatched 행을 강제로 회복할지 검증했다.

| 회복 전략 | 효과 |
|---|---:|
| description 정확 일치 매칭 | 2 / 2,054 (0.097%) |
| 대소문자/공백 정규화 매칭 | 동일 (2건) |
| 부모 카테고리 강제 매핑 | **데이터 왜곡 — 채택 불가** |

"칼슘 강화 우유"의 플라보노이드 측정값을 "일반 우유"에 귀속시키는 것은 영양학적으로 잘못된 정보를 데이터베이스에 주입하는 행위이므로 채택할 수 없다. 따라서 **명세대로 unmatched_flavonoid 테이블에 사유와 함께 분리 보존**하는 것을 최종 결정으로 한다. 이는 향후 USDA가 공식 매핑 가이드를 제공할 경우 단일 SQL 문으로 통합 가능한 구조를 유지하기 위함이다.

---

## 9. 산출물 구조

```
DB_A/
├ docs/                           ← 진행 문서
│  ├ OVERVIEW.md                  ← (본 문서)
│  ├ PROGRESS.md                  ← 마스터 인덱스 + 변경 이력
│  └ stage_2_log.md ~ stage_7_log.md   ← 단계별 상세 로그
│
├ scripts/                        ← 재현 가능 코드
│  ├ 01_load_large_tables.sql     ← food, food_nutrient LOAD
│  ├ 02_load_small_tables.sql     ← 소용량 LOAD (Wizard 대안)
│  ├ 03_load_branded_food.py      ← branded_food (pandas)
│  ├ 04_verify_stage_2.sql        ← Stage 2 검증
│  ├ 05_extract_and_load_xlsx.py  ← Stage 3 xlsx 적재
│  ├ 06_final_verification.sql    ← Stage 7 검증 5개
│  ├ README_stage2.md             ← Stage 2 실행 가이드
│  └ _run/                        ← 진단·보완·실 실행본 16개 파일
│
└ (원본 CSV·xlsx 7개)
```

---

## 10. 보고서 (docx) 작성 가이드

[stage_7_log.md §8](stage_7_log.md) 의 권장 순서를 그대로 활용한다.

1. 표지·팀 정보
2. 개요 + ERD + Relation Schema (Stage 1)
3. **Stage 2 — CSV 적재 (20점)** : §5 방법 비교표 + §6 트러블슈팅 T-1~T-6
4. Stage 3 — xlsx 적재 (Stage 5 예측 일치 강조)
5. Stage 4 — nutrient 확장
6. **Stage 5 — food_nutrient 통합 (20점)** : 186,073 행 / **T-7 트러블슈팅**
7. **Stage 6 — unmatched 분리 (10점)** : §8 데이터 거버넌스 결정
8. 검증 5개 결과 (§7 표 그대로)
9. 결론

본 문서의 모든 표·해석은 보고서에 그대로 인용 가능하도록 구성되었다.
