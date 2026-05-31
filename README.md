# USDA FDC Flavonoid Integration DB

> Research and service-oriented database project that integrates USDA FoodData Central nutrition data with flavonoid composition data, validates relational integrity, and produces analytical queries for nutrient and flavonoid exploration.

[![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?style=flat-square&logo=mysql&logoColor=white)](https://www.mysql.com/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![SQL](https://img.shields.io/badge/SQL-DDL%20%7C%20ETL%20%7C%20Validation-336791?style=flat-square&logo=postgresql&logoColor=white)]()
[![InnoDB](https://img.shields.io/badge/Engine-InnoDB-005C84?style=flat-square&logo=mysql&logoColor=white)]()
[![ETL](https://img.shields.io/badge/ETL-CSV%20%7C%20XLSX%20%7C%20Bulk%20Load-2E8B57?style=flat-square)]()
[![Portfolio](https://img.shields.io/badge/Portfolio-Data%20Engineering%20%26%20Database%20Design-6A5ACD?style=flat-square)]()

## Overview

This repository contains a database systems project for building an integrated food nutrition and flavonoid database.

The project combines USDA FoodData Central CSV tables with the USDA flavonoid Excel workbook, then loads, expands, validates, and analyzes the integrated dataset in MySQL. The workflow covers schema design, large CSV ingestion, Python-based ETL for irregular files, Excel sheet extraction, referential-integrity checks, unmatched-record handling, and final analytical verification queries.

The project is structured as a portfolio-ready research database: raw public datasets are excluded from Git because of size, while SQL/Python ETL scripts and validation documentation remain reproducible.

## Tech Stack

| Category | Tools / Concepts |
| --- | --- |
| DBMS | MySQL 8.0 |
| Storage Engine | InnoDB |
| SQL | DDL, DML, `LOAD DATA LOCAL INFILE`, JOIN, aggregation, validation queries |
| Python ETL | pandas, openpyxl, mysql-connector-python |
| Source Data | USDA FoodData Central CSV, USDA flavonoid workbook |
| Data Modeling | Relational schema, foreign keys, staging tables, unmatched table |
| Integrity | PK, FK, uniqueness, orphan checks, row-count validation |
| Performance | Bulk loading, chunked inserts, session-level load tuning |
| Documentation | Stage logs, verification SQL, progress report |

## Repository Layout

```text
DB_A/
  README.md                       Project overview and execution guide
  requirements.txt                Python dependencies for ETL scripts
  .gitignore                      Excludes raw datasets, generated outputs, local files
  data/
    raw/                          Place downloaded USDA CSV/XLSX source files here
  scripts/
    01_load_large_tables.sql       Bulk-load food and food_nutrient tables
    02_load_small_tables.sql       Load nutrient, survey, and SR legacy tables
    03_load_branded_food.py        Chunked Python loader for branded_food.csv
    04_verify_stage_2.sql          Stage 2 row-count and FK validation
    05_extract_and_load_xlsx.py    Extract flavonoid workbook sheets and load tmp tables
    06_final_verification.sql      Final analytical verification queries
    README_stage2.md              Stage 2 execution notes
  docs/
    PROGRESS.md                   Master progress and design decisions
    stage_2_log.md                CSV loading result and troubleshooting log
    stage_3_log.md                XLSX extraction and staging log
    stage_4_log.md                Nutrient expansion log
    stage_5_log.md                Flavonoid integration insert log
    stage_6_log.md                Unmatched flavonoid separation log
    stage_7_log.md                Final verification report log
```

## Data Sources

| Source File | Target / Role | Git Policy |
| --- | --- | --- |
| `food.csv` | master food table | ignored |
| `nutrient.csv` | nutrient metadata | ignored |
| `survey_fndds_food.csv` | survey food-code mapping | ignored |
| `sr_legacy_food.csv` | SR Legacy mapping | ignored |
| `branded_food.csv` | branded food details | ignored |
| `food_nutrient.csv` | nutrient measurements | ignored |
| `USDA food flavonoid.xlsx` | flavonoid reference workbook | ignored |

Raw files should be placed under `data/raw/`. They are excluded from version control because the combined source data is multiple GB.

## Database Model

| Table | Type | Primary Key | Description |
| --- | --- | --- | --- |
| `food` | Core entity | `fdc_id` | FoodData Central food master records |
| `nutrient` | Core entity | `id` | Nutrient metadata extended with flavonoid markers |
| `food_nutrient` | Fact table | `id` | Nutrient amount per food item |
| `branded_food` | Subtype/detail | `fdc_id` | Brand, serving, and ingredient details |
| `survey_fndds_food` | Mapping table | `fdc_id` | FNDDS food-code mapping |
| `sr_legacy_food` | Mapping table | `fdc_id` | SR Legacy NDB mapping |
| `tmp_flavdesc` | Staging table | `nutrient_code` | Flavonoid nutrient definitions from Excel |
| `tmp_mainfooddesc` | Staging table | `food_code` | Flavonoid workbook food descriptions |
| `tmp_flavval` | Staging table | source rows | Flavonoid amount values |
| `unmatched_flavonoid` | Audit table | generated id | Flavonoid rows that could not be mapped to FDC foods |

## Integration Workflow

| Stage | Goal | Main Artifacts |
| --- | --- | --- |
| 1 | Design relational schema and constraints | design documents, DDL |
| 2 | Load USDA FoodData Central CSV files | `01_load_large_tables.sql`, `02_load_small_tables.sql`, `03_load_branded_food.py` |
| 3 | Extract and stage USDA flavonoid Excel sheets | `05_extract_and_load_xlsx.py` |
| 4 | Expand `nutrient` with flavonoid metadata | stage SQL and logs |
| 5 | Insert mapped flavonoid values into `food_nutrient` | integration SQL and logs |
| 6 | Separate unmapped flavonoid records | unmatched audit table |
| 7 | Produce final verification queries and evidence | `06_final_verification.sql`, `docs/stage_7_log.md` |

## Installation

Install MySQL 8.0 or later and Python 3.10 or later.

```bash
mysql --version
python --version
```

Install the Python dependencies.

```bash
pip install -r requirements.txt
```

Enable local file loading when using the MySQL CLI.

```bash
mysql --local-infile=1 -u root -p
```

## Quick Start

Place the source files in `data/raw/`.

```text
data/raw/food.csv
data/raw/nutrient.csv
data/raw/survey_fndds_food.csv
data/raw/sr_legacy_food.csv
data/raw/branded_food.csv
data/raw/food_nutrient.csv
data/raw/USDA food flavonoid.xlsx
```

Run the table loaders from the repository root.

```bash
mysql --local-infile=1 -u root -p usda_fdc < scripts/01_load_large_tables.sql
mysql --local-infile=1 -u root -p usda_fdc < scripts/02_load_small_tables.sql
```

Load `branded_food.csv` with chunked Python inserts.

```bash
python scripts/03_load_branded_food.py --user root --password <password>
```

Extract and load the flavonoid workbook.

```bash
python scripts/05_extract_and_load_xlsx.py --user root --password <password>
```

Run verification queries.

```bash
mysql -u root -p usda_fdc < scripts/04_verify_stage_2.sql
mysql -u root -p usda_fdc < scripts/06_final_verification.sql
```

## Validation

| Validation Target | Method |
| --- | --- |
| Row-count integrity | table-level count checks after each load stage |
| Referential integrity | orphan checks between child tables and `food` / `nutrient` |
| Flavonoid mapping coverage | matched vs unmatched flavonoid row counts |
| Data loss prevention | unmatched flavonoid rows preserved in a separate audit table |
| Analytical correctness | Daidzein top foods, flavonoid class averages, per-food nutrient joins |

Final validation evidence is documented in `docs/stage_7_log.md` and reproduced by `scripts/06_final_verification.sql`.

## Research / Service Value

| Area | Value |
| --- | --- |
| Nutrition research | Enables integrated lookup of general nutrients and flavonoid compounds |
| Data engineering | Demonstrates multi-source ingestion, staging, reconciliation, and validation |
| Database design | Uses relational modeling, constraints, and staged integration tables |
| Service readiness | Provides query foundations for food search, nutrient profiling, and flavonoid analytics |

## Notes

- Run loaders from the repository root so relative paths such as `data/raw/food.csv` resolve correctly.
- MySQL `local_infile` must be enabled for `LOAD DATA LOCAL INFILE`.
- Raw datasets, generated CSV extracts, local reports, and runtime artifacts are intentionally excluded through `.gitignore`.
- The database name used in the scripts is `usda_fdc`.
