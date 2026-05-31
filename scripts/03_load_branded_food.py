"""
Stage 2 (방법 C) : Python(pandas + mysql-connector)으로 branded_food 적재
- ingredients TEXT 컬럼이 콤마/따옴표/줄바꿈을 포함 → CSV 표준 파서로 안전 처리
- chunksize 단위로 스트리밍 적재 (메모리 절약)
- 적재 시간 측정 출력 (보고서용)

사용법:
    python 03_load_branded_food.py --host localhost --user root --password <pw>

DB는 usda_fdc 가 이미 존재하고, branded_food 테이블이 비어 있다는 전제.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import pandas as pd
import mysql.connector
from mysql.connector import errorcode


DEFAULT_CSV_PATH = Path("data/raw/branded_food.csv")
CHUNK = 20_000  # 20k 단위 적재

COLUMNS = [
    "fdc_id", "brand_owner", "brand_name", "subbrand_name", "gtin_upc",
    "ingredients", "not_a_significant_source_of", "serving_size",
    "serving_size_unit", "household_serving_fulltext", "branded_food_category",
    "data_source", "package_weight", "modified_date", "available_date",
    "market_country", "discontinued_date", "preparation_state_code",
    "trade_channel", "short_description", "material_code",
]

INSERT_SQL = f"""
INSERT INTO branded_food
({", ".join(COLUMNS)})
VALUES ({", ".join(["%s"] * len(COLUMNS))})
"""

DATE_COLS = ("modified_date", "available_date", "discontinued_date")
NUMERIC_COLS = ("serving_size",)


def normalize(row: pd.Series) -> tuple:
    out = []
    for c in COLUMNS:
        v = row[c]
        if pd.isna(v) or v == "":
            out.append(None)
            continue
        if c in DATE_COLS:
            try:
                out.append(pd.to_datetime(v).date())
            except Exception:
                out.append(None)
            continue
        if c in NUMERIC_COLS:
            try:
                out.append(float(v))
            except Exception:
                out.append(None)
            continue
        out.append(v)
    return tuple(out)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="localhost")
    p.add_argument("--port", type=int, default=3306)
    p.add_argument("--user", default="root")
    p.add_argument("--password", required=True)
    p.add_argument("--db", default="usda_fdc")
    p.add_argument("--csv", type=Path, default=DEFAULT_CSV_PATH)
    args = p.parse_args()
    csv_path = args.csv

    cnx = mysql.connector.connect(
        host=args.host, port=args.port,
        user=args.user, password=args.password,
        database=args.db, charset="utf8mb4", autocommit=False,
        use_pure=True,
    )
    cur = cnx.cursor()
    cur.execute("SET SESSION sql_mode=''")
    cur.execute("SET SESSION foreign_key_checks=0")
    cur.execute("SET SESSION unique_checks=0")
    cur.execute("TRUNCATE TABLE branded_food")
    cnx.commit()

    print(f"[INFO] reading {csv_path}")
    t0 = time.perf_counter()
    total = 0

    reader = pd.read_csv(
        csv_path,
        chunksize=CHUNK,
        dtype=str,
        keep_default_na=False,  # 빈 문자열 유지
        na_values=[],
        quoting=0,              # csv.QUOTE_MINIMAL 대응
        engine="c",
        encoding="utf-8",
    )

    for i, chunk in enumerate(reader, start=1):
        chunk = chunk[COLUMNS]  # 컬럼 순서 강제
        rows = [normalize(r) for _, r in chunk.iterrows()]
        cur.executemany(INSERT_SQL, rows)
        cnx.commit()
        total += len(rows)
        print(f"  chunk {i:>4}  cum_rows={total:>10,}  elapsed={time.perf_counter()-t0:7.1f}s")

    cur.execute("SET SESSION foreign_key_checks=1")
    cur.execute("SET SESSION unique_checks=1")
    cur.execute("SELECT COUNT(*) FROM branded_food")
    (cnt,) = cur.fetchone()
    cur.close()
    cnx.close()

    print(f"[DONE] branded_food rows_loaded={cnt:,}  total_time={time.perf_counter()-t0:.1f}s")


if __name__ == "__main__":
    try:
        main()
    except mysql.connector.Error as e:
        if e.errno == errorcode.ER_NO_SUCH_TABLE:
            print("[FATAL] branded_food 테이블이 없습니다. DDL을 먼저 실행하세요.")
        raise
