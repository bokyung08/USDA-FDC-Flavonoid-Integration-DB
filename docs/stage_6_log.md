# Stage 6 — unmatched_flavonoid 분리 (실시간 사고 로그)

## 0. 목적과 채점 비중

**채점 10점**. Stage 5에서 `survey_fndds_food` 와 매칭 실패한 **75,998행**(예상)을 별도 `unmatched_flavonoid` 테이블로 분리 보관.

**의의** — Stage 1 설계 문서에 명시한 "USDA FDC 2021년 버전과 Flavonoid 데이터 2017년 버전의 food_code 불일치를 데이터 손실 없이 추적 가능하게 만든다"는 요구사항을 만족시키는 단계.

## 1. 사고 흐름

### 1-1. unmatched_flavonoid DDL 확인

```sql
CREATE TABLE unmatched_flavonoid (
  id              int unsigned NOT NULL AUTO_INCREMENT PK,
  food_code       int unsigned NOT NULL,
  nutrient_code   int unsigned NOT NULL,
  start_date      date NULL,
  end_date        date NULL,
  nutrient_value  decimal(10,4) NULL,
  unmatch_reason  varchar(100) NULL,
  ...
);
```

- `id` 가 AUTO_INCREMENT ✓ (Stage 5의 T-5-1 문제 재발 없음)
- `food_code`, `nutrient_code` 만 NOT NULL — 나머지는 NULL 허용

### 1-2. 매핑 결정

| tmp_flavval | → unmatched_flavonoid | 변환 |
|---|---|---|
| food_code | food_code | 그대로 |
| nutrient_code | nutrient_code | 그대로 |
| start_date | start_date | 그대로 |
| end_date | end_date | 그대로 |
| nutrient_value | nutrient_value | 그대로 |
| (상수) | unmatch_reason | `'No matching food_code in survey_fndds_food (version mismatch)'` |

### 1-3. JOIN 패턴 선택 — LEFT JOIN ... IS NULL vs NOT EXISTS
- 두 패턴 모두 동등한 결과를 내야 함 (식별자 컬럼이 NOT NULL이므로).
- MySQL 8.0 옵티마이저는 두 패턴을 비슷하게 처리 (Anti-join).
- 가독성 측면에서 **NOT EXISTS** 선호 — "매칭 실패"의 의도가 명확.

### 1-4. 사전 점검 위험 요소

| # | 위험 | 점검 |
|---|---|---|
| R-1 | unmatched_flavonoid 에 이미 데이터가 있을 가능성 | BEFORE 행수 → 0 기대 |
| R-2 | 75,998 행 재확인 | LEFT JOIN과 NOT EXISTS 두 방식 모두 동일 결과인지 |
| R-3 | nutrient_value NULL 비율 | 보고용 통계 |
| R-4 | unmatch_reason 문자열 길이 ≤ 100 | 'No matching ... (version mismatch)' = 59자 ✓ |
| R-5 | INSERT 직후 정합성 — `186,073 + 75,998 = 262,071` | tmp_flavval 전체 행수와 일치해야 함 |

## 2. 진행 상태 — ✅ Stage 6 완료 (채점 10점)

| 단계 | 결과 |
|---|---|
| DDL 확인 + 매핑 결정 | ✅ |
| 사전 점검 5개 | 모두 통과 |
| INSERT (NOT EXISTS) | **75,998행 / 0.663s / warns 0** |
| 사후 검증 7개 | 모두 통과 — **데이터 손실 0건** |

## 3. 사전 점검 결과

| ID | 항목 | 결과 |
|---|---|---|
| R-1 | BEFORE 행수 | 0 ✓ |
| R-2a | LEFT JOIN ... IS NULL | 75,998 ✓ |
| R-2b | NOT EXISTS | 75,998 ✓ (두 방식 일치) |
| R-3 | NULL nutrient_value / min / max / avg | 0 / 0.0 / 149.28 / 0.19 |
| R-3 | distinct food_code / nutrient_code | **2,054 / 37** |
| R-4 | reason 문자열 길이 | 59자 ≤ 100 ✓ |
| R-5 | matched + unmatched = total | 186,073 + 75,998 = 262,071 ✓ |

## 4. INSERT 결과

| 항목 | 값 |
|---|---:|
| INSERT 행수 | **75,998** ✓ |
| 소요 시간 | 0.663 s |
| 행/초 | 114,627 |
| warnings | 0 |

## 5. 사후 검증 7개

| # | 검증 | 결과 |
|---|---|---:|
| A | 정합성 (matched + unmatched − tmp_flavval) | **delta = 0** ✓ 데이터 손실 0건 |
| B | unmatch_reason 단일 값 | 75,998 / 1 종류 ✓ |
| C | unmatched food_code TOP 10 | 모두 우유/버터밀크 (코드 재편) |
| D | nutrient_code 분포 | 37개 모두 / 각 정확히 2,054 ✓ |
| E | 매칭 실패율 | **29.00%** (보고서 검증 2번 답) |
| F | 2017→2021 폐기 food_code 수 | **2,054** (Stage 3 ⑥ 예측 정확) |
| G | 샘플 조회 | food_code=11111100 의 37행 모두 동일 reason ✓ |

## 6. 핵심 인사이트 (보고서 자료)

### 6-1. 매칭 실패율 29% 의 근본 원인
- USDA Flavonoid 데이터(2017년 MAINFOODDESC)의 **2,054개 food_code** 가 USDA FDC 2021년 survey_fndds_food 에 존재하지 않음.
- 모든 영양소(37개) × 2,054개 food_code = **75,998행** — 정확히 일치하는 산식.
- 데이터는 unmatched_flavonoid 에 그대로 보존되어 향후 매핑 보강 시 재사용 가능.

### 6-2. 매칭 실패가 집중된 식품 카테고리
| food_code 시작 | 카테고리 | 비고 |
|---|---|---|
| 11111xxx, 11112xxx, 11115xxx, 11121xxx | 우유 (Milk, Buttermilk, Dry milk) | 2017 → 2021 에서 카테고리 재편 |

→ 우유류는 2017년 USDA FNDDS 에서 영양소 강화/저나트륨 변종까지 세분화했지만, 2021년에는 큰 범주로 통합된 것으로 추정.

### 6-3. **데이터 정합성 100%**
```
tmp_flavval        =  262,071
  ├ food_nutrient (Stage 5 INSERT) = 186,073  (71.00%)
  └ unmatched_flavonoid (Stage 6)  =  75,998  (29.00%)
                             합계 = 262,071   (100.00%)
```

## 6.4. 추가 분석 — 회복 가능성 (보고서 부가 점수용)

매칭 실패 75,998행을 단순히 분리하는 데 그치지 않고, **description 매칭으로 일부 회복할 수 있는지** 능동적으로 검증.

### 6.4.1. 검증한 회복 전략 3가지

| 전략 | 회복된 food_code 수 | 평가 |
|---|---:|---|
| (1) 정확 일치 `f.description = m.main_food_description` | **2 / 2,054** (0.097%) | Waffle 2종 (plain reduced fat / whole grain reduced fat) — 무의미한 수준 |
| (2) 대소문자/공백 정규화 `LOWER(TRIM(...))` | **2 / 2,054** (0.097%) | 동일 — 표기 차이 아님 |
| (3) 강제 부모 카테고리 매핑 (예: "Milk, calcium fortified, whole" → "Milk, whole") | **불가** | 영양 성분이 다른 식품의 데이터를 같은 fdc_id 로 귀속시키는 것은 **데이터 왜곡** |

### 6.4.2. 회복 불가의 근본 원인 — USDA 카테고리 재편

| 2017 MAINFOODDESC (unmatched) | 2021 survey_fndds_food | 변화 |
|---|---|---|
| Milk, **low sodium**, whole | (제거됨) | 저나트륨 변종 제거 |
| Milk, **calcium fortified**, low fat (1%) | (제거됨) | 영양 강화 변종 제거 |
| Milk, **acidophilus**, reduced fat (2%) | (제거됨) | 발효 변종 제거 |
| Milk, **dry, reconstituted**, low fat (1%) | (제거됨) | 분유 환원 변종 제거 |
| Milk, **dry, not reconstituted**, whole | (제거됨) | 비환원 분유 제거 |
| — | Milk, **lactose free**, low fat (1%) | 신규 추가 (2021에만) |

→ 2021년 FNDDS는 **마이너 변종을 제거하고 대분류만 유지**. 또한 2021에만 추가된 신규 식품(lactose free 등)도 존재해 1:1 매핑이 원리적으로 불가능.

### 6.4.3. 의사결정

**그대로 유지** — 다음 이유로 정당화:
1. **영양학적 정확성**: 칼슘 강화 우유의 플라보노이드 측정값을 일반 우유에 귀속시키면 영양가 분석에 오류 발생.
2. **추적 가능성**: unmatched_flavonoid 테이블로 보존하면 향후 USDA가 매핑 가이드를 제공할 때 1줄 SQL로 회복 가능 (`INSERT INTO food_nutrient ... SELECT FROM unmatched_flavonoid u JOIN <mapping> ...`).
3. **명세 부합**: Stage 1 설계서가 `unmatched_flavonoid` 테이블을 분리한 의도가 바로 이 데이터 거버넌스 원칙.

### 6.4.4. 보고서에 들어갈 한 문장 요약

> "USDA Flavonoid 데이터(2017)와 FNDDS(2021) 사이의 카테고리 재편으로 인해 2,054개 food_code가 1:1 매핑되지 않으며, description 정규화 매칭으로도 0.097%(2건)만 회복 가능했다. 영양학적 정확성을 보장하기 위해 75,998행을 unmatched_flavonoid 테이블에 사유와 함께 보존하여 추후 수동 매핑 가이드 적용 시 재통합이 가능하도록 설계했다."

## 7. 트러블슈팅
없음. Stage 5 의 T-5-1 (AUTO_INCREMENT 누락) 이슈는 unmatched_flavonoid 에서는 재발하지 않음 (DDL 에 AUTO_INCREMENT 정상 정의).

## 8. 산출물

| 파일 | 역할 |
|---|---|
| [../scripts/_run/stage6_precheck.sql](../scripts/_run/stage6_precheck.sql) | 사전 점검 5개 |
| [../scripts/_run/stage6_insert.sql](../scripts/_run/stage6_insert.sql) | NOT EXISTS 기반 INSERT |
| [../scripts/_run/stage6_postcheck.sql](../scripts/_run/stage6_postcheck.sql) | 사후 검증 7개 + 보고서 자료 |

## 9. 다음 단계 — Stage 7 (최종 보고서)

**Stage 7 — 검증 5개 항목 + 최종 보고서**:
1. ✅ 테이블별 적재 행 수 — Stage 2/4/5/6 결과 종합
2. ✅ Flavonoid 매핑 실패율 — **29.00%** (75,998 / 262,071)
3. ✅ Daidzein TOP 5 — Stage 5 §7-1 (Textured veg protein 64.55 등)
4. ✅ Flavonoid 클래스별 평균 함량 — Stage 5 §7-2 (7개 클래스)
5. ✅ fdc_id 1건 통합 조회 — fdc_id=2707451 (일반 65 + 플라보노이드 37)

모든 검증 자료는 이미 추출 완료. Stage 7은 보고서 정리 + 최종 ERD 갱신만 남음.

