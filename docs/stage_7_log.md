# Stage 7 — 최종 검증 5개 항목 + 보고서 정리

## 0. 목적
명세서 §검증 5개 항목의 결과를 추출하여 보고서 본문에 그대로 첨부.

## 1. 검증 ① 테이블별 적재 행 수

| 테이블 | 행 수 | 비고 |
|---|---:|---|
| food | **2,085,340** | 모든 data_type 포함 (branded/sr_legacy/survey/sample 등 9종) |
| nutrient | **514** | 일반 영양소 477 + 플라보노이드 37 (Stage 4 INSERT) |
| survey_fndds_food | **5,432** | 2021년 USDA FNDDS |
| sr_legacy_food | **7,793** | USDA SR Legacy |
| branded_food | **1,993,975** | branded foods (TEXT ingredients) |
| food_nutrient | **27,280,100** | Stage 2 LOAD 27,094,027 + Stage 5 INSERT 186,073 |
| tmp_flavdesc | **37** | Flavonoid 영양소 메타 (37 = 명세 "38행" 헤더 포함 의미) |
| tmp_mainfooddesc | **7,083** | 2017년 USDA food_code 사전 |
| tmp_flavval | **262,071** | xlsx FLAVVAL 시트 |
| unmatched_flavonoid | **75,998** | Stage 6 분리 |
| **합계** | **34,402,883** | — |

**FK 정합성**: 모든 FK 5개 (`food_nutrient↔food`, `food_nutrient↔nutrient`, `survey_fndds_food↔food`, `sr_legacy_food↔food`, `branded_food↔food`) — 고아 행 0건.

## 2. 검증 ② Flavonoid 매핑 실패율

| 항목 | 값 |
|---|---:|
| total_flavval (xlsx FLAVVAL) | 262,071 |
| matched (food_nutrient 에 통합) | 186,073 |
| unmatched (unmatched_flavonoid) | 75,998 |
| **매칭률** | **71.00%** |
| **실패율** | **29.00%** |

**실패 사유 (단일)**: `No matching food_code in survey_fndds_food (version mismatch)`

**근본 원인**: USDA Flavonoid 데이터(2017 MAINFOODDESC)의 **2,054개 food_code** 가 2021년 FNDDS에 존재하지 않음.
- 우유/버터밀크 변종(저나트륨/칼슘강화/산성유/환원분유 등)이 2021년에 제거됨.
- description 매칭으로 회복 가능한 것은 단 2건(0.097%) — 강제 매핑은 데이터 왜곡이라 미시행 (자세히는 [stage_6_log.md §6.4](stage_6_log.md)).

## 3. 검증 ③ Daidzein (nutrient_id=710) 함량 TOP 5

| 순위 | fdc_id | description | Daidzein (mg) |
|:-:|:-:|---|---:|
| 1 | 2,707,451 | Textured vegetable protein, dry | **64.55** |
| 2 | 2,707,466 | Bacon bits (소이 베이컨 비츠) | 64.37 |
| 3 | 2,707,433 | Soy nuts | 61.42 |
| 4 | 2,710,732 | Nutritional powder mix (EAS Soy Protein Powder) | 30.07 |
| 5 | 2,710,743 | Nutritional powder mix, protein, soy based, NFS | 30.07 |

**해석**: Daidzein 은 isoflavone 계열로 콩 단백질이 농축된 식품에서 자연스럽게 가장 높게 나타남. **5개 모두 콩 기반 식품** — 데이터 신뢰성 시각적 확인.

## 4. 검증 ④ Flavonoid 클래스별 평균 함량

| flavonoid_class | 데이터 행수 | 평균(mg) | 최소(mg) | 최대(mg) |
|---|---:|---:|---:|---:|
| (Total: Total flavonoids 등) | 5,029 | **5.5913** | 0.00 | 7,331.20 |
| **Flavonols** | 25,145 | **0.5132** | 0.00 | 697.85 |
| **Flavan-3-ols** | 65,377 | 0.4491 | 0.00 | 6,633.35 |
| **Anthocyanidins** | 35,203 | 0.3018 | 0.00 | 324.43 |
| **Isoflavones** | 20,116 | 0.2178 | 0.00 | 166.94 |
| **Flavanones** | 20,116 | 0.1194 | 0.00 | 101.45 |
| **Flavones** | 15,087 | 0.0945 | 0.00 | 216.55 |

**해석**:
- Total 합산 값을 제외하면 **Flavonols가 평균 함량 가장 높음** (양파/베리/녹차류).
- Flavan-3-ols는 행수(65,377) 가 가장 많아 측정 빈도가 높은 카테고리.
- 최대값 6,633 mg (Flavan-3-ols) → 차/카카오 종류 추정.

## 5. 검증 ⑤ fdc_id 1건의 일반 영양소 + 플라보노이드 통합 조회

### 5-1. 대상 식품
| fdc_id | description | 일반 영양소 | 플라보노이드 | 총 행수 |
|:-:|---|---:|---:|---:|
| **2,707,451** | Textured vegetable protein, dry | **65** | **37** | **102** |

### 5-2. 일반 영양소 TOP 15 (amount DESC)

| nutrient_id | nutrient_name | unit | amount | is_flavonoid |
|---:|---|:-:|---:|:-:|
| 1092 | Potassium, K | MG | 2,480.00 | 0 |
| 1091 | Phosphorus, P | MG | 726.00 | 0 |
| 1008 | Energy | KCAL | 366.00 | 0 |
| 1087 | Calcium, Ca | MG | 338.00 | 0 |
| 1090 | Magnesium, Mg | MG | 313.00 | 0 |
| 1177 | Folate, total | UG | 305.00 | 0 |
| 1187 | Folate, food | UG | 305.00 | 0 |
| 1190 | Folate, DFE | UG | 305.00 | 0 |
| 1003 | Protein | G | 51.10 | 0 |
| 1103 | Selenium, Se | UG | 45.80 | 0 |
| 1005 | Carbohydrate, by difference | G | 32.90 | 0 |
| 1107 | Carotene, beta | UG | 24.00 | 0 |
| 1079 | Fiber, total dietary | G | 17.50 | 0 |
| 2000 | Total Sugars | G | 16.42 | 0 |
| 1180 | Choline, total | MG | 11.30 | 0 |

### 5-3. 플라보노이드 함량 (값 있는 것 우선)

| nutrient_id | nutrient_name | unit | amount | is_flavonoid | flavonoid_class |
|---:|---|:-:|---:|:-:|---|
| 7000 | **Total flavonoids** | mg | **166.94** | 1 | (Total) |
| 7700 | **Total isoflavones** | mg | **166.94** | 1 | Isoflavones |
| 711 | **Genistein** | mg | **87.31** | 1 | Isoflavones |
| 710 | **Daidzein** | mg | **64.55** | 1 | Isoflavones |
| 712 | **Glycitein** | mg | **15.08** | 1 | Isoflavones |
| (그 외 32개 플라보노이드) | (Anthocyanidins, Flavan-3-ols, Flavanones, Flavones, Flavonols) | mg | 0.00 | 1 | — |

**해석**:
- 콩 단백질 농축 식품답게 **isoflavone 3종(Daidzein/Genistein/Glycitein) 의 합계 166.94 mg** 이 Total flavonoids 와 Total isoflavones 양쪽에 정확히 일치.
- 나머지 32개 플라보노이드(차/베리/감귤류 시그니처)는 모두 0 mg — **콩 식품의 자연스러운 플라보노이드 프로파일** 정확히 재현.
- 일반 영양소(칼륨 2,480 mg, 단백질 51.1 g 등)와 플라보노이드가 **한 fdc_id 아래 통합 조회** 되는 것이 본 프로젝트의 핵심 가치 시현.

## 6. Stage 7 종합 평가

### 6-1. 정량 결과
| 항목 | 값 |
|---|---|
| 총 적재 행수 | 34,402,883 |
| FK 고아 행 | 0건 |
| 데이터 손실 | 0건 |
| 매칭률 | 71.00% (영양학적 정확성 보장 하의 최대치) |
| 보고서 검증 5개 | 모두 완료 |

### 6-2. 정성 결과
- **데이터 신뢰성**: Daidzein TOP 5 (모두 콩 식품) / isoflavone 시그니처 정확 재현 → 데이터 정확성 시각적 확인.
- **데이터 거버넌스**: 강제 매핑 대신 unmatched_flavonoid 로 보존 → 영양학적 왜곡 회피.
- **재현성**: 모든 단계가 SQL/Python 스크립트로 자동화 + 사고 흐름 docs/ 에 기록.

## 7. 산출물 (Stage 7)

| 파일 | 역할 |
|---|---|
| [../scripts/06_final_verification.sql](../scripts/06_final_verification.sql) | 최종 5개 검증 쿼리 (재실행 가능) |
| [../scripts/_run/stage7_verification_output.txt](../scripts/_run/stage7_verification_output.txt) | 실행 raw 결과 (보고서 그대로 첨부 가능) |

## 8. 보고서 (외부 docx) 작성용 권장 순서

1. **표지 / 팀 정보** (기존)
2. **개요 + ERD + Relation Schema** (Stage 1 산출물)
3. **Stage 2 — CSV 적재 (20점)**
   - 3가지 방법 분담 표 + 성능 비교표 → [stage_2_log.md §7](stage_2_log.md)
   - 트러블슈팅 T-1~T-6 → 보고서의 "기술적 도전" 섹션
4. **Stage 3 — xlsx 적재**
   - 269,191행 적재 + 명세 정확 일치 (186,073 / 75,998 사전 시뮬레이션 통과) → [stage_3_log.md](stage_3_log.md)
5. **Stage 4 — nutrient 확장**
   - 37행 INSERT, flavonoid_class 6종 → [stage_4_log.md](stage_4_log.md)
6. **Stage 5 — food_nutrient 통합 INSERT (20점)**
   - 186,073행 INSERT
   - **T-5-1 트러블슈팅 (AUTO_INCREMENT 누락 → ROW_NUMBER 우회)** → [stage_5_log.md](stage_5_log.md)
7. **Stage 6 — unmatched_flavonoid 분리 (10점)**
   - 75,998행 분리 + 매칭률 71.00%
   - **회복 가능성 분석 (강제 매핑 미시행 근거)** → [stage_6_log.md §6.4](stage_6_log.md)
8. **검증 5개 결과** (본 문서 §1~§5)
9. **결론** — 영양학적 정확성을 보장하는 데이터 거버넌스의 가치

## 9. 다음 액션
보고서(docx) 작성에 본 문서의 §1~§5 표·해석을 그대로 사용. 추가로 stage_2/5/6 의 트러블슈팅 섹션을 인용.
