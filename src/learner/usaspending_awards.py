"""Download 5 award từ USAspending và lưu vào bảng Unity Catalog."""

import argparse
import sys
from pathlib import Path

# File nằm ở src/learner/ => phải thêm src/ (parents[1]) vào path để import common.
try:
    _SRC_DIR = Path(__file__).resolve().parents[1]
except NameError:  # serverless chạy qua exec(), không có __file__
    _SRC_DIR = Path(sys.argv[0]).resolve().parents[1]
sys.path.insert(0, str(_SRC_DIR))

from pyspark.sql import DataFrame, SparkSession  # noqa: E402
from pyspark.sql import functions as F  # noqa: E402
from pyspark.sql.types import DoubleType, LongType, StringType, StructField, StructType  # noqa: E402

from common.download import fetch_json  # noqa: E402
from learner.schemas import AWARDS_API_COLUMNS, AWARDS_RAW_SCHEMA, AWARDS_TABLE

URL = "https://api.usaspending.gov/api/v2/search/spending_by_award/"

# Tên field trong API  ->  tên cột trong bảng
# COLUMNS = {
#     "internal_id": "internal_id",
#     "Award ID": "award_id",
#     "Recipient Name": "recipient_name",
#     "Award Amount": "award_amount",
#     "Awarding Agency": "awarding_agency",
#     "Start Date": "start_date",
#     "End Date": "end_date",
#     "Description": "description",
# }

# RAW_SCHEMA = StructType([
#     StructField("internal_id", LongType()),
#     StructField("award_id", StringType()),
#     StructField("recipient_name", StringType()),
#     StructField("award_amount", DoubleType()),
#     StructField("awarding_agency", StringType()),
#     StructField("start_date", StringType()),
#     StructField("end_date", StringType()),
#     StructField("description", StringType()),
# ])


def fetch_awards(limit: int = 5) -> list[dict]:
    """Gọi API (giống lệnh curl) và trả về list các award."""
    body = {
        "filters": {
            "award_type_codes": ["A", "B", "C", "D"],
            "time_period": [{"start_date": "2025-10-01", "end_date": "2026-09-30"}],
        },
        "fields": [k for k in COLUMNS if k != "internal_id"],  # internal_id API tự trả về
        "limit": limit,
        "page": 1,
    }
    return fetch_json(URL, json_body=body)["results"]


def to_dataframe(spark: SparkSession, records: list[dict]) -> DataFrame:
    """Logic thuần (không gọi mạng) => unit test được."""
    rows = []
    for r in records:
        row = {new: r.get(old) for old, new in COLUMNS.items()}
        if row["award_amount"] is not None:
            row["award_amount"] = float(row["award_amount"])
        rows.append(row)

    return (
        spark.createDataFrame(rows, schema=RAW_SCHEMA)
        .withColumn("start_date", F.to_date("start_date"))
        .withColumn("end_date", F.to_date("end_date"))
        .withColumn("ingested_at", F.current_timestamp())
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--schema", required=True)
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    spark = SparkSession.builder.getOrCreate()
    df = to_dataframe(spark, fetch_awards(args.limit))

    target = f"{args.catalog}.{args.schema}.{AWARDS_TABLE}"
    df.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable(target)
    print(f"Wrote {df.count()} rows to {target}")


if __name__ == "__main__":
    main()
