"""Job ETL mẫu: tạo một bảng nhỏ trong Unity Catalog."""

import argparse
import sys
from pathlib import Path

# Cho phép `from common.download import ...` khi chạy dưới dạng spark_python_task.
# Serverless chạy file qua exec() nên không có __file__; đường dẫn nằm ở sys.argv[0].
try:
    _SRC_DIR = Path(__file__).resolve().parent
except NameError:
    _SRC_DIR = Path(sys.argv[0]).resolve().parent
sys.path.insert(0, str(_SRC_DIR))

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F


def transform(df: DataFrame) -> DataFrame:
    """Logic thuần, tách riêng để unit test chạy được trên GitHub runner."""
    return df.withColumn("amount_vat", F.round(F.col("amount") * 1.1, 2))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--schema", required=True)
    args = parser.parse_args()

    spark = SparkSession.builder.getOrCreate()
    source = spark.createDataFrame([(1, 10.0), (2, 20.5), (3, 99.9)], ["id", "amount"])

    target = f"{args.catalog}.{args.schema}.sample_sales"
    transform(source).write.mode("overwrite").saveAsTable(target)
    print(f"Wrote {target}")


if __name__ == "__main__":
    main()
