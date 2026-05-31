# Stage 2 — CSV 적재 가이드 & 성능 비교 보고서 템플릿

## 1. 실행 순서 (FK 의존성 준수)

```
food  →  nutrient  →  survey_fndds_food  →  sr_legacy_food  →  branded_food  →  food_nutrient
```

| Step | 방법 | 대상 | 스크립트 |
|---|---|---|---|
| 1 | LOAD DATA INFILE | food | `01_load_large_tables.sql` (앞부분) |
| 2 | Import Wizard *(대안: SQL)* | nutrient, survey_fndds_food, sr_legacy_food | `02_load_small_tables.sql` |
| 3 | Python | branded_food | `03_load_branded_food.py` |
| 4 | LOAD DATA INFILE | food_nutrient | `01_load_large_tables.sql` (뒷부분) |
| 5 | 검증 | 전체 | `04_verify_stage_2.sql` |

## 2. 사전 환경 점검

### 2-1. LOCAL INFILE 활성화 (LOAD DATA LOCAL INFILE 사용 시 필수)
서버 측:
```sql
SHOW VARIABLES LIKE 'local_infile';   -- ON 이어야 함
SET GLOBAL local_infile = 1;
```
클라이언트 측 (mysql CLI):
```
mysql --local-infile=1 -u root -p
```
VS Code MySQL extension(cweijan): 연결 옵션에서 `allowLoadLocalInfile=true` 또는 connect string에 `--local-infile=1` 추가.

### 2-2. secure_file_priv (LOCAL 안 쓰고 LOAD DATA INFILE 사용 시)
```sql
SHOW VARIABLES LIKE 'secure_file_priv';
```
값이 디렉터리(예: `C:/ProgramData/MySQL/MySQL Server 8.0/Uploads/`)면 CSV를 그 경로로 복사하고 SQL의 경로도 그곳으로 바꿔야 함.
값이 빈 문자열이면 어디든 가능.
값이 NULL이면 LOAD DATA INFILE 자체 비활성 → LOCAL 사용 필수.

### 2-3. Python 의존성
```
pip install pandas mysql-connector-python
```

## 3. 실행 명령

```powershell
# (1) 대용량: food
mysql --local-infile=1 -u root -p usda_fdc < scripts\01_load_large_tables.sql
#  ↑ 파일 내 food_nutrient 블록은 (2)(3) 끝난 뒤 다시 실행하는 것을 권장.
#    또는 파일을 두 부분으로 분리하여 1차/2차 실행.

# (2) 소용량 — Workbench Wizard 권장(보고서 비교 위해)
#    GUI: 좌측 schema tree → 테이블 우클릭 → Table Data Import Wizard
#    또는 SQL로 동등 실행:
mysql --local-infile=1 -u root -p usda_fdc < scripts\02_load_small_tables.sql

# (3) Python — branded_food
python scripts\03_load_branded_food.py --user root --password <pw>

# (4) food_nutrient — (1)의 후반부 재실행
mysql --local-infile=1 -u root -p usda_fdc < scripts\01_load_large_tables.sql

# (5) 검증
mysql -u root -p usda_fdc < scripts\04_verify_stage_2.sql
```

## 4. 성능 비교표 (보고서 표 2 — 실측값으로 채워서 제출)

> 실행 시간은 `SET @t = NOW(3); ... SELECT TIMESTAMPDIFF(MICROSECOND, @t, NOW(3))/1e6 AS sec;` 또는
> mysql CLI 옵션 `--show-warnings` 후 명령 실행 시간으로 측정.
> Wizard는 GUI에 표시되는 경과 시간 또는 시작/종료 시각을 수동 기록.

| 방법 | 적재 대상 | 행 수 | 파일 크기 | 소요시간(s) | 행/초 | MB/s | 메모 |
|---|---|---:|---:|---:|---:|---:|---|
| LOAD DATA INFILE | food | 2,085,340 | 208 MB | _____ | _____ | _____ | LOCAL 사용/미사용 표기 |
| LOAD DATA INFILE | food_nutrient | ____ | 1,702 MB | _____ | _____ | _____ | |
| MySQL Import Wizard | nutrient | 477 | 0.02 MB | _____ | _____ | _____ | |
| MySQL Import Wizard | survey_fndds_food | 5,432 | 0.28 MB | _____ | _____ | _____ | |
| MySQL Import Wizard | sr_legacy_food | 7,793 | 0.12 MB | _____ | _____ | _____ | |
| Python (pandas+connector) | branded_food | ____ | 907 MB | _____ | _____ | _____ | chunk=20,000, executemany |

### 4-1. 결론(예시 문구 — 실측 후 정리)
- **LOAD DATA INFILE**: 단일 트랜잭션 + 서버 측 직렬 파싱으로 *XX MB/s*. 대용량(food, food_nutrient)에 압도적.
- **Import Wizard**: 내부적으로 행 단위 INSERT를 묶어 발행하므로 소량(<1만 행)에서만 실용적.
- **Python(pandas + mysql-connector)**: `executemany` + chunk로 LOAD DATA의 ~1/X 속도. 단, TEXT 컬럼의 quoting/줄바꿈을 안전하게 전처리할 수 있어 `branded_food` 같은 비정형 데이터에 유리.

## 5. 트러블슈팅 자주 발생 케이스

| 증상 | 원인 / 해결 |
|---|---|
| `ERROR 1148 (42000): The used command is not allowed` | 서버/클라이언트 `local_infile` 모두 ON 필요 |
| `ERROR 1290 (HY000): --secure-file-priv` | CSV를 `secure_file_priv` 디렉터리로 옮기거나, `LOAD DATA LOCAL INFILE` 사용 |
| FK 위반 | 적재 순서 위반. 부모 테이블 먼저 적재. 또는 `SET foreign_key_checks=0` 일시 해제 |
| `Incorrect integer value: ''` | `sql_mode` STRICT 켜진 상태 → `SET sql_mode=''` 후 NULLIF 사용 |
| food_category_id 적재 실패 | DDL이 INT면 ALTER로 VARCHAR(50)으로 바꿔야 함 (텍스트 카테고리 혼재 확인됨) |
| 한글 깨짐 | 클라이언트 charset=utf8mb4, LOAD 문에 `CHARACTER SET utf8mb4` 명시 |

## 6. 다음 단계 (Stage 3 예고)
- `USDA food flavonoid.xlsx`를 시트별 CSV로 추출 → `tmp_flavdesc`, `tmp_mainfooddesc`, `tmp_flavval`에 적재.
- 추출 스크립트는 `05_extract_xlsx.py`로 별도 제공 예정.
