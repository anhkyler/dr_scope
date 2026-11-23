import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from learner.customers_download import check_zip, ensure_volume, volume_path  # noqa: E402


class _FakeSpark:
    """Giả lập spark.sql: SHOW VOLUMES trả về các volume có sẵn, ghi lại lệnh CREATE."""

    def __init__(self, volumes):
        self.volumes = volumes
        self.created = []

    def sql(self, query):
        spark = self

        class _Result:
            def collect(self):
                return [{"database": "demo", "volume_name": v} for v in spark.volumes]

        if query.startswith("CREATE VOLUME"):
            self.created.append(query)
        return _Result()


def test_ensure_volume_skips_when_exists():
    spark = _FakeSpark(["raw"])
    assert ensure_volume(spark, "workspace", "demo", "raw") is False
    assert spark.created == []


def test_ensure_volume_creates_when_missing():
    spark = _FakeSpark(["other"])
    assert ensure_volume(spark, "workspace", "demo", "raw") is True
    assert spark.created == ["CREATE VOLUME IF NOT EXISTS `workspace`.`demo`.`raw`"]


def test_volume_path():
    assert volume_path("workspace", "dev_hieuphso_demo", "raw", "customers-100.zip") == Path(
        "/Volumes/workspace/dev_hieuphso_demo/raw/customers-100.zip"
    )


def test_check_zip_lists_members(tmp_path):
    path = tmp_path / "data.zip"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("customers-100.csv", "id,name\n1,a\n")
    assert check_zip(path) == ["customers-100.csv"]


def test_check_zip_rejects_html(tmp_path):
    path = tmp_path / "data.zip"
    path.write_text("<html>Google Drive can't scan this file for viruses</html>")
    with pytest.raises(ValueError, match="not a zip"):
        check_zip(path)
    assert not path.exists()
