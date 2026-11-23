"""Định nghĩa bảng dùng chung cho các job learner."""

from pyspark.sql.types import (
    DateType, DoubleType, LongType, StringType, StructField, StructType, TimestampType,
)

AWARDS_TABLE = "usaspending_awards"

# Field trong API  ->  cột trong bảng
AWARDS_API_COLUMNS = {
    "internal_id": "internal_id",
    "Award ID": "award_id",
    "Recipient Name": "recipient_name",
    "Award Amount": "award_amount",
    "Awarding Agency": "awarding_agency",
    "Start Date": "start_date",
    "End Date": "end_date",
    "Description": "description",
}

# Dữ liệu thô từ API (ngày tháng còn là chuỗi)
AWARDS_RAW_SCHEMA = StructType([
    StructField("internal_id", LongType()),
    StructField("award_id", StringType()),
    StructField("recipient_name", StringType()),
    StructField("award_amount", DoubleType()),
    StructField("awarding_agency", StringType()),
    StructField("start_date", StringType()),
    StructField("end_date", StringType()),
    StructField("description", StringType()),
])

# Cấu trúc cuối cùng của bảng trong Unity Catalog
AWARDS_TABLE_SCHEMA = StructType([
    StructField("internal_id", LongType(), nullable=False, metadata={"comment": "ID nội bộ USAspending"}),
    StructField("award_id", StringType()),
    StructField("recipient_name", StringType()),
    StructField("award_amount", DoubleType(), metadata={"comment": "USD"}),
    StructField("awarding_agency", StringType()),
    StructField("start_date", DateType()),
    StructField("end_date", DateType()),
    StructField("description", StringType()),
    StructField("ingested_at", TimestampType()),
])
