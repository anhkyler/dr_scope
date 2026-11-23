"""Download file zip customers từ Google Drive và lưu vào Unity Catalog volume.

Chạy trên job:  --catalog pilot_so_hieu --schema dev_hieuphso_demo --volume raw
=> file được lưu tại /Volumes/pilot_so_hieu/dev_hieuphso_demo/raw/customers-100.zip
"""

import argparse
import sys
import zipfile
from pathlib import Path

# File nằm ở src/learner/ => phải thêm src/ (parents[1]) vào path để import common.
try:
    _SRC_DIR = Path(__file__).resolve().parents[1]
except NameError:  # serverless chạy qua exec(), không có __file__
    _SRC_DIR = Path(sys.argv[0]).resolve().parents[1]
sys.path.insert(0, str(_SRC_DIR))

from common.download import download_file  # noqa: E402

DEFAULT_URL = "https://drive.google.com/uc?id=1yyL20BNKv3PxJRJVjJ_2Q-HidvIUis45&export=download"
DEFAULT_FILE_NAME = "customers-100.zip"


def volume_path(catalog: str, schema: str, volume: str, file_name: str) -> Path:
    """Đường dẫn file trong volume: /Volumes/<catalog>/<schema>/<volume>/<file>."""
    return Path("/Volumes") / catalog / schema / volume / file_name


def check_zip(path: Path) -> list[str]:
    """Đảm bảo file tải về là zip hợp lệ (Google Drive có thể trả về trang HTML
    cảnh báo virus-scan với file lớn). Trả về danh sách file bên trong zip."""
    if not zipfile.is_zipfile(path):
        head = path.read_bytes()[:200]
        path.unlink(missing_ok=True)
        raise ValueError(f"{path} is not a zip file (first bytes: {head!r})")
    with zipfile.ZipFile(path) as zf:
        return zf.namelist()


def volume_exists(spark, catalog: str, schema: str, volume: str) -> bool:
    """True nếu volume đã có trong schema (SHOW VOLUMES trả về cột volume_name)."""
    rows = spark.sql(f"SHOW VOLUMES IN `{catalog}`.`{schema}`").collect()
    return any(r["volume_name"] == volume for r in rows)


def ensure_volume(spark, catalog: str, schema: str, volume: str) -> bool:
    """Volume đã có => không tạo nữa. Chưa có => tạo managed volume.
    Trả về True nếu vừa tạo mới. Schema do bundle tạo sẵn."""
    full_name = f"{catalog}.{schema}.{volume}"
    if volume_exists(spark, catalog, schema, volume):
        print(f"Volume {full_name} already exists, skip creating")
        return False
    # IF NOT EXISTS: phòng trường hợp job khác vừa tạo cùng lúc
    spark.sql(f"CREATE VOLUME IF NOT EXISTS `{catalog}`.`{schema}`.`{volume}`")
    print(f"Created volume {full_name}")
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--schema", required=True)
    parser.add_argument("--volume", default="raw")
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--file-name", default=DEFAULT_FILE_NAME)
    args = parser.parse_args()

    from pyspark.sql import SparkSession

    spark = SparkSession.builder.getOrCreate()
    # Bước 1: đảm bảo volume có sẵn TRƯỚC khi tải file
    ensure_volume(spark, args.catalog, args.schema, args.volume)
    # Bước 2: tải file vào volume
    dest = volume_path(args.catalog, args.schema, args.volume, args.file_name)
    download_file(args.url, dest)
    members = check_zip(dest)
    print(f"Saved {dest} ({dest.stat().st_size} bytes), contains: {members}")


if __name__ == "__main__":
    main()
