# Stage 5 — food_nutrient 통합 INSERT (실시간 사고 로그)

## 0. 목적과 채점 비중

**채점 20점** (가장 큰 비중 중 하나). 명세서 핵심 쿼리를 실행해 USDA FDC의 일반 영양소 데이터와 USDA Flavonoid 데이터를 **`food_nutrient` 단일 사실(fact) 테이블에 통합**.

```sql
INSERT INTO food_nutrient (fdc_id, nutrient_id, amount)
SELECT s.fdc_id, f.nutrient_code, f.nutrient_value
FROM tmp_flavval f
JOIN survey_fndds_food s ON f.food_code = s.food_code;
```

**예상**: 186,073행 INSERT (Stage 3에서 정확히 시뮬레이션 확인).

## 1. 사고 흐름 — 사전 점검 우선 (천천히, 정확히)

### 1-1. 점검해야 할 위험 요소

| # | 위험 | 점검 방법 |
|---|---|---|
| R-1 | food_nutrient에 이미 동일 (fdc_id, nutrient_id) 조합이 있을 수 있음 (Stage 2 적재한 행과 중복) | INSERT 전에 LEFT JOIN으로 0건 확인 |
| R-2 | INSERT가 FK 제약을 위반할 가능성: fdc_id가 food 테이블에 있는지, nutrient_id가 nutrient에 있는지 | sub-query로 LEFT JOIN 확인 |
| R-3 | amount(=nutrient_value) 데이터 타입 안전성 — tmp_flavval은 decimal(10,4), food_nutrient.amount는 decimal(14,4) | precision 충분 (확장 방향) |
| R-4 | NULL nutrient_value 처리 — INSERT 시 amount NULL 허용 여부 | DDL상 amount NULL 허용 ✓ |
| R-5 | tmp_flavval 의 (food_code, nutrient_code) 조합이 unique인지 (Stage 3 ⑦에서 0 확인) | 이미 확인 ✓ |
| R-6 | survey_fndds_food의 food_code 가 unique인지 (1:N JOIN으로 행 증가 방지) | 점검 필요 |
| R-7 | 트랜잭션 크기 — 186k INSERT는 한 트랜잭션 가능 | autocommit=0 + COMMIT |
| R-8 | INSERT 후 통계 확인을 위한 BEFORE 행수 기록 | 측정 |

### 1-2. 천천히, 정확하게 — 5단계 워크플로
1. **사전 점검 SQL** 실행 → R-1~R-6, R-8 모두 확인
2. **DRY-RUN**: 같은 JOIN을 `SELECT COUNT(*)` 로 미리 확인 (186,073 재확인)
3. **INSERT 실행** + 시간/행수 측정
4. **사후 검증**: 행수 증가량 / FK 정합성 / 임의 샘플 조회 / amount 분포
5. **검증 5번(보고서)용 샘플 쿼리** — 한 fdc_id 의 일반 영양소 + 플라보노이드 통합 조회 미리 실행해 결과 첨부

## 2. 진행 상태 — ✅ Stage 5 완료 (채점 20점)

| 단계 | 결과 |
|---|---|
| 사전 점검 8개 항목 | 모두 통과 (R-1~R-8) |
| DRY-RUN | 186,073행 (명세 정확) |
| INSERT | **186,073행 / 6.929초 / warns 0** |
| 사후 검증 7개 항목 | 모두 통과 |

## 3. 트러블슈팅

### T-5-1. ★ AUTO_INCREMENT 누락
- **증상**: 첫 INSERT 시도 시 `ERROR 1062 (23000): Duplicate entry '0' for key 'food_nutrient.PRIMARY'`
- **진단**:
  ```
  SHOW CREATE TABLE food_nutrient;
  -- `id` bigint unsigned NOT NULL COMMENT '...',
  -- PRIMARY KEY (`id`)
  -- ↑ AUTO_INCREMENT 없음!
  ```
  Stage 2 적재에서는 CSV의 id 컬럼 값을 그대로 받아 동작했음. 그러나 Stage 5의 `INSERT INTO ... SELECT` 는 id 미지정 → 기본값 0 → PK 충돌.
- **선택지 비교**:
  - (A) DDL ALTER 로 AUTO_INCREMENT 추가 → DDL 변경, Stage 1 산출물 영향
  - (B) INSERT 에서 ROW_NUMBER 로 id 수동 부여 → DDL 그대로, INSERT 만 변경
- **결정**: (B) ROW_NUMBER 채택 (사용자 confirm).
- **해결 코드**:
  ```sql
  SELECT MAX(id) INTO @offset FROM food_nutrient;
  INSERT INTO food_nutrient (id, fdc_id, nutrient_id, amount)
  SELECT @offset + ROW_NUMBER() OVER (), s.fdc_id, f.nutrient_code, f.nutrient_value
  FROM tmp_flavval f
  JOIN survey_fndds_food s ON f.food_code = s.food_code;
  ```
- 결과: 정상 186,073행 INSERT, max_id 34,969,298 → 35,155,371.

## 4. 사전 점검 결과 (참고)

| 위험 ID | 항목 | 결과 |
|---|---|---|
| R-1 | (fdc_id, nutrient_id) 사전 중복 | 0 ✓ |
| R-2a | fdc_id FK 누락 | 0 ✓ |
| R-2b | nutrient_id FK 누락 | 0 ✓ (Stage 4 INSERT 효과) |
| R-3 | amount precision | tmp_flavval(10,4) → food_nutrient(14,4) 확장 |
| R-4 | NULL amount | 0건 |
| R-5 | (food_code, nutrient_code) tmp 중복 | 0 (Stage 3) |
| R-6 | survey_fndds_food.food_code 유일성 | 0 중복 ✓ |
| R-7 | 트랜잭션 크기 | 186k 한 트랜잭션 가능 |
| R-8 | BEFORE 행수 | 27,094,027 |

## 5. INSERT 결과

| 항목 | 값 |
|---|---:|
| food_nutrient 적재 전 | 27,094,027 |
| INSERT 행수 | **186,073** ✓ |
| food_nutrient 적재 후 | **27,280,100** ✓ |
| 소요 시간 | 6.929 s |
| 행/초 | 26,856 |
| warnings | 0 |
| 신규 id 범위 | 34,969,299 ~ 35,155,371 |

## 6. 사후 검증 7개

| # | 검증 | 결과 |
|---|---|---:|
| A | 행수 증가 (delta) | **+186,073** ✓ |
| B | 새 행 distinct fdc_id / nutrient_id | 5,029 / 37 ✓ |
| B | amount min/max/avg | 0.0 / 7331.2 / 0.4795 |
| C | FK orphan (food/nutrient 두 방향) | 0 / 0 ✓ |
| D | 새 행 100% is_flavonoid=1 | 186,073 / 0 ✓ |
| E | 새 행 (fdc_id, nutrient_id) 중복 | 0 ✓ |
| F | 검증 5번 보고서 자료 추출 | (아래 §7) |

## 7. 검증 5번 보고서 자료 (Stage 7에서 사용)

### 7-1. Daidzein(nutrient_id=710) 함량 TOP 5

| fdc_id | description | amount (mg) |
|---:|---|---:|
| 2707451 | Textured vegetable protein, dry | 64.55 |
| 2707466 | Bacon bits | 64.37 |
| 2707433 | Soy nuts | 61.42 |
| 2710732 | Nutritional powder mix (EAS Soy Protein Powder) | 30.07 |
| 2710743 | Nutritional powder mix, protein, soy based, NFS | 30.07 |

→ 모두 콩 단백질 기반 식품. 데이터 신뢰성 인증 (Daidzein은 isoflavone 으로 콩에 다량 존재).

### 7-2. Flavonoid 클래스별 평균 함량

| flavonoid_class | 행수 | 평균(mg) | 최대(mg) |
|---|---:|---:|---:|
| (NULL — Total flavonoids 등) | 5,029 | 5.5913 | 7,331.20 |
| Flavonols | 25,145 | 0.5132 | 697.85 |
| Flavan-3-ols | 65,377 | 0.4491 | 6,633.35 |
| Anthocyanidins | 35,203 | 0.3018 | 324.43 |
| Isoflavones | 20,116 | 0.2178 | 166.94 |
| Flavanones | 20,116 | 0.1194 | 101.45 |
| Flavones | 15,087 | 0.0945 | 216.55 |

### 7-3. fdc_id 1건의 통합 조회 예시 — fdc_id=2707451 ("Textured vegetable protein, dry")
- 일반 영양소(`is_flavonoid=0`): **65행**
- 플라보노이드(`is_flavonoid=1`): **37행** (Daidzein 64.55mg / Genistein 87.31mg / Glycitein 15.08mg 등 isoflavone 풍부)

→ Stage 7 최종 보고서에 이 fdc_id 의 전체 결과를 시각화/표화하면 통합 DB의 가치 시현으로 좋음.

## 8. 산출물

| 파일 | 역할 |
|---|---|
| [../scripts/_run/stage5_precheck.sql](../scripts/_run/stage5_precheck.sql) | 사전 점검 8개 |
| [../scripts/_run/stage5_insert.sql](../scripts/_run/stage5_insert.sql) | 본 INSERT (ROW_NUMBER 사용) |
| [../scripts/_run/stage5_postcheck.sql](../scripts/_run/stage5_postcheck.sql) | 사후 검증 7개 + 보고서 자료 |

## 9. 다음 단계 — Stage 6

**Stage 6 — unmatched_flavonoid 분리 (채점 10점)**:
- tmp_flavval 중 survey_fndds_food와 매칭 실패한 **75,998행** → `unmatched_flavonoid` 테이블 이관
- `unmatch_reason = 'No matching food_code in survey_fndds_food (version mismatch)'`
- 매칭 실패 원인: MAINFOODDESC(2017년 버전) vs survey_fndds_food(2021년 버전) — 2017에 있지만 2021에 없는 food_code = 2,054 (Stage 3 ⑥에서 확인).

