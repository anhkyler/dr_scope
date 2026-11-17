import sys
from pathlib import Path

import pytest
from pyspark.sql import SparkSession

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from etl import transform  # noqa: E402


@pytest.fixture(scope="session")
def spark():
    session = SparkSession.builder.master("local[1]").appName("tests").getOrCreate()
    yield session
    session.stop()


def test_transform_adds_vat(spark):
    df = spark.createDataFrame([(1, 10.0)], ["id", "amount"])
    row = transform(df).collect()[0]
    assert row["amount_vat"] == 11.0
