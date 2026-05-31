# DB_A 프로젝트 진행 현황 (Master)

USDA FDC × Flavonoid 통합 DB 구축 — 데이터베이스시스템 텀프로젝트 과제 A
MySQL 8.0+ / utf8mb4 / InnoDB / DB명 `usda_fdc`

> 본 문서는 **단계별 마스터 인덱스**입니다. 세부 로그는 각 `stage_*_log.md` 참조.
> 진행마다 본 문서 + 해당 stage 로그 두 곳을 함께 갱신합니다.

## 1. 단계별 상태

| Stage | 내용 | 채점 | 상태 | 산출물 | 상세 로그 |
|---|---|:-:|:-:|---|---|
| 1 | DDL · ERD · Relation Schema | 10 | ✅ 완료 | 테이블 10개, FK/INDEX, 예약어 백틱 | (외부 docx) |
| 2 | CSV 적재 (3가지 방법) | 20 | ✅ 완료 | 총 31,189,044행 적재, FK 고아 0 | [stage_2_log.md](stage_2_log.md) |
| 3 | xlsx → tmp_* 적재 | — | ✅ 완료 | [scripts/05_extract_and_load_xlsx.py](../scripts/05_extract_and_load_xlsx.py) | [stage_3_log.md](stage_3_log.md) |
| 4 | nutrient 확장 + FLAVDESC INSERT | — | ✅ 완료 | 37행 INSERT → nutrient 514행 | [stage_4_log.md](stage_4_log.md) |
| 5 | food_nutrient 통합 INSERT | 20 | ✅ 완료 | 186,073행 INSERT → 27,280,100 | [stage_5_log.md](stage_5_log.md) |
| 6 | unmatched_flavonoid 분리 | 10 | ✅ 완료 | 75,998행 분리 / 손실 0건 | [stage_6_log.md](stage_6_log.md) |
| 7 | 검증 5개 항목 → 보고서 | — | ✅ 완료 | 5개 모두 추출, 보고서 자료 정리 | [stage_7_log.md](stage_7_log.md) |

상태 기호: ✅완료 · 🟡진행중 · ⬜대기 · ❌이슈

## 2. 환경

- OS: Windows 11 Education
- DB: MySQL 8.0+ (charset utf8mb4)
- IDE: VS Code + MySQL extension (cweijan)
- 작업 경로: `c:\Users\bokyu\Desktop\DB_A\`
  - 원본 CSV/xlsx: 루트 (총 ~2.9 GB)
  - 스크립트: `scripts/`
  - 진행 문서: `docs/` (본 폴더)

## 3. 데이터 파일

| 파일 | 행 수 (예상) | 용량 | 적재 방법 | 대상 테이블 |
|---|---:|---:|---|---|
| food.csv | 2,085,340 | 208 MB | LOAD DATA INFILE | food |
| nutrient.csv | 477 | 0.02 MB | Import Wizard | nutrient |
| survey_fndds_food.csv | 5,432 | 0.28 MB | Import Wizard | survey_fndds_food |
| sr_legacy_food.csv | 7,793 | 0.12 MB | Import Wizard | sr_legacy_food |
| branded_food.csv | (수십만) | 907 MB | Python | branded_food |
| food_nutrient.csv | (수천만) | 1,702 MB | LOAD DATA INFILE | food_nutrient |
| USDA food flavonoid.xlsx | 38 + 7,083 + 262,071 | 6.2 MB | 추출→CSV→LOAD | tmp_flavdesc / tmp_mainfooddesc / tmp_flavval |

## 4. 핵심 설계 결정사항 (Stage 1 결과)

- `survey_fndds_food.fdc_id` : 단독 PK (중복 0건 확인)
- `food_code` : INT UNSIGNED (max 99,998,210 — INT 범위 충분)
- `branded_food.ingredients` : TEXT
- `food.food_category_id` : **VARCHAR 필요** — Stage 2 점검 중 숫자/문자 혼재 확인 (`"1002"`, `"Oils Edible"`)
- `percent_daily_value` : 명세 외이나 실제 파일에 존재 → DDL 포함
- 예약어 백틱 적용: `name`, `rank`, `min`, `max`, `median`

## 5. 핵심 적재 순서 (FK 의존성)

```
food  →  nutrient  →  survey_fndds_food  →  sr_legacy_food  →  branded_food  →  food_nutrient
```

## 6. 핵심 통합 쿼리 (Stage 5 예고)

```sql
INSERT INTO food_nutrient (fdc_id, nutrient_id, amount)
SELECT s.fdc_id, f.nutrient_code, f.nutrient_value
FROM tmp_flavval f
JOIN survey_fndds_food s ON f.food_code = s.food_code;
-- 예상: 186,073행 INSERT, 75,998행 매칭 실패 → unmatched_flavonoid
-- 원인: survey_fndds_food(2021) vs MAINFOODDESC(2017) 버전 불일치
```

## 7. 보고서 검증 5개 항목 (Stage 7)

1. 테이블별 적재 행 수
2. Flavonoid 매핑 실패율
3. Daidzein(nutrient_id=710) 함량 TOP 5
4. Flavonoid 클래스별 평균 함량
5. fdc_id 1건 일반 영양소 + 플라보노이드 통합 조회 (`is_flavonoid` 포함)

## 8. 변경 이력 (최신순)

| 날짜 | 단계 | 변경 |
|---|---|---|
| 2026-05-28 | Stage 7 ✅ | 검증 5개 항목 모두 추출 + 보고서 자료 정리. 매칭률 71%·실패율 29%·Daidzein TOP 5(콩 식품)·flavonoid 7개 클래스 평균·통합 조회 샘플(fdc_id 2,707,451) 확보. |
| 2026-05-28 | Stage 6 + | 회복 가능성 추가 분석. exact 매칭 2건/2,054 (0.097%) — USDA 카테고리 재편이 근본 원인. 강제 매핑은 데이터 왜곡이므로 명세대로 unmatched 유지 결정. |
| 2026-05-28 | Stage 6 ✅ | 매칭 실패 75,998행 → unmatched_flavonoid 이관. 매칭 실패율 29.00% / deprecated food_code 2,054개 (우유류 재편). 데이터 손실 0건 확인. |
| 2026-05-28 | Stage 5 ✅ | INSERT...SELECT 로 food_nutrient 186,073행 통합. T-5-1: AUTO_INCREMENT 누락 → ROW_NUMBER 로 수동 id 부여. 보고서 검증 5번 자료 모두 추출. |
| 2026-05-28 | Stage 4 ✅ | tmp_flavdesc 37행 → nutrient (514행) INSERT. is_flavonoid=1 마킹. flavonoid_class 6종 분포 확인. |
| 2026-05-28 | Stage 3 ✅ | xlsx 3개 시트 → tmp_* 269,191행 적재. 교차 검증 7개 통과. Stage 5 사전 시뮬레이션(매칭 186,073 / unmatched 75,998) 명세 정확 일치. |
| 2026-05-28 | Stage 2 ✅ | 6개 테이블 31,189,044행 적재 완료. FK 고아 0건. 트러블슈팅 7건 기록 (T-1~T-6 + corrupt row 정리). |
| 2026-05-28 | Stage 2 | food LOAD 41,801행 누락 → 원인 확정(description 임베디드 newline) + Python 보완 패턴 정립 |
| 2026-05-28 | Stage 2 | 적재 스크립트 5개 생성 (`01~04` SQL/Py, README). docs/ 폴더 신설. |
| 2026-05-28 | Stage 2 | CSV 점검 — `food_category_id` 숫자/문자 혼재, 줄바꿈 LF, 빈 문자열=NULL 컨벤션 확인 |
