import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from learner.usaspending_awards import to_dataframe  # noqa: E402
from tests.test_etl import spark  # noqa: E402,F401  (dùng lại fixture Spark)


def test_to_dataframe_from_sample(spark):
    records = json.loads((ROOT / "sample.json").read_text())["results"]
    df = to_dataframe(spark, records)
    assert df.count() == len(records)
    assert dict(df.dtypes)["start_date"] == "date"
    assert " " not in "".join(df.columns)
