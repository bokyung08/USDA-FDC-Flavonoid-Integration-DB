# Stage 4 — nutrient 테이블 확장 (실시간 사고 로그)

## 0. 목적

`tmp_flavdesc` 37개 플라보노이드 영양소를 `nutrient` 테이블에 INSERT.
- `is_flavonoid = 1` 마킹
- `flavonoid_class` 값 채움
- 기존 477개 일반 영양소와 통합 → 총 514행

## 1. 사고 흐름

### 1-1. 사전 조건
- nutrient 테이블엔 이미 `is_flavonoid` (default 0), `flavonoid_class` 컬럼이 DDL에 포함됨 (Stage 1에서 선반영).
- Stage 3 검증 ②에서 **`tmp_flavdesc.nutrient_code ∩ nutrient.id = 0`** → PK 충돌 없음 확정.
- 그러므로 단순 `INSERT ... SELECT` 한 번으로 끝남.

### 1-2. 매핑 결정

| tmp_flavdesc 컬럼 | → nutrient 컬럼 | 변환 |
|---|---|---|
| nutrient_code | id | INT UNSIGNED |
| flavonoid_description | name | varchar(255) |
| unit | unit_name | varchar(20) ('mg' 그대로) |
| flavonoid_class | flavonoid_class | varchar(50) |
| (상수) | is_flavonoid | 1 |
| (미적용) | nutrient_nbr | NULL (FLAVDESC에 해당 컬럼 없음) |
| (미적용) | rank | NULL (FLAVDESC에 해당 컬럼 없음) |
| tagname / decimals | (사용 안 함) | tmp_flavdesc에만 보존 |

DDL의 `nutrient.name`은 `NOT NULL`이라 모두 값이 있어야 함 → flavonoid_description 비어있지 않은지 확인.
DDL의 `nutrient.unit_name`도 `NOT NULL` → unit이 모두 'mg'이므로 OK.

### 1-3. 충돌 / 사이드이펙트 점검
- nutrient는 다른 테이블의 FK 참조 대상 (food_nutrient.nutrient_id → nutrient.id). INSERT는 추가만 하므로 영향 없음.
- 기존 nutrient 477행에 `is_flavonoid=0` 기본값. 일부 행이 실수로 1로 되어있지 않은지 사전 확인 권장.

## 2. 실행 계획

```sql
-- 사전: 충돌 0 재확인 + 기존 is_flavonoid 분포
SELECT
  (SELECT COUNT(*) FROM nutrient)                           AS nutrient_before,
  (SELECT COUNT(*) FROM nutrient WHERE is_flavonoid=1)      AS already_flavonoid,
  (SELECT COUNT(*) FROM tmp_flavdesc t
        JOIN nutrient n ON t.nutrient_code = n.id)          AS conflicts;

-- 본 INSERT
INSERT INTO nutrient (id, name, unit_name, is_flavonoid, flavonoid_class)
SELECT
  t.nutrient_code,
  t.flavonoid_description,
  COALESCE(NULLIF(t.unit, ''), 'mg'),
  1,
  NULLIF(t.flavonoid_class, '')
FROM tmp_flavdesc t;

-- 사후: 행수/분포 검증
SELECT
  (SELECT COUNT(*) FROM nutrient)                           AS nutrient_after,
  (SELECT COUNT(*) FROM nutrient WHERE is_flavonoid=1)      AS flavonoid_total,
  (SELECT COUNT(DISTINCT flavonoid_class) FROM nutrient
        WHERE is_flavonoid=1)                                AS distinct_classes;
```

## 3. 진행 상태 — ✅ Stage 4 완료

| 항목 | 상태 |
|---|:-:|
| 사전 점검 (충돌/기존 flavonoid 분포) | ✅ |
| INSERT 실행 | ✅ |
| 사후 검증 (행수/매칭/분포) | ✅ |

## 4. 실행 결과

### 4-1. BEFORE
| 항목 | 값 |
|---|---:|
| nutrient_before | 477 |
| already_flavonoid | 0 |
| conflicts | **0** ✓ |

### 4-2. INSERT
| 항목 | 값 |
|---|---:|
| inserted_rows | **37** ✓ |
| elapsed_sec | < 0.001 (밀리초 미만) |

### 4-3. AFTER
| 항목 | 값 |
|---|---:|
| nutrient_after | **514** ✓ (477 + 37) |
| flavonoid_total | **37** ✓ |
| distinct_classes | **6** (+ NULL 1) |

### 4-4. flavonoid_class 분포 (검증 5번 보고서 자료)

| flavonoid_class | 영양소 수 |
|---|---:|
| Flavan-3-ols | 13 |
| Anthocyanidins | 7 |
| Flavonols | 5 |
| Isoflavones | 4 |
| Flavanones | 4 |
| Flavones | 3 |
| NULL (Total flavonoids) | 1 |
| **합계** | **37** |

### 4-5. 적재 정확성 교차 검증
| 항목 | 값 |
|---|---:|
| matched_37 (nutrient JOIN tmp_flavdesc) | 37 ✓ |
| missing_from_nutrient | 0 ✓ |

## 5. 트러블슈팅
없음. Stage 3에서 충돌 0건 사전 확인 → 단일 INSERT로 완료.

## 6. 산출물
| 파일 | 역할 |
|---|---|
| [../scripts/_run/stage4_nutrient_expand.sql](../scripts/_run/stage4_nutrient_expand.sql) | BEFORE/INSERT/AFTER + 분포·교차 검증 |

## 7. 다음 단계 — Stage 5

**Stage 5 — food_nutrient 통합 INSERT (채점 20점)**:
```sql
INSERT INTO food_nutrient (fdc_id, nutrient_id, amount)
SELECT s.fdc_id, f.nutrient_code, f.nutrient_value
FROM tmp_flavval f
JOIN survey_fndds_food s ON f.food_code = s.food_code;
```

사전 시뮬레이션(Stage 3): **186,073행 INSERT 예상, unmatched 75,998행**.

주의:
- food_nutrient.id 는 bigint auto_increment PK → INSERT 시 미지정.
- nutrient_id 는 514행 nutrient에 모두 존재 확인 필요 (37개 flavonoid id가 새로 들어갔으므로).
- 현재 food_nutrient 행수 27,094,027 → 186,073 추가 시 **27,280,100** 예상.

