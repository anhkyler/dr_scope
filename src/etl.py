"""Job ETL mẫu: tạo một bảng nhỏ trong Unity Catalog."""

import argparse

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
