# GitHub (Free) → Databricks Free Edition: CI/CD bằng Asset Bundles

```
 Dev (máy cá nhân)            GitHub (Free)                       Databricks Free Edition (1 workspace)
 ─────────────────            ─────────────                       ─────────────────────────────────────
 code + bundle  ──push──▶  feature branch ──PR──▶ CI (ci.yml)
 databricks bundle                                 • pytest (Spark local)
   deploy -t dev ─────────────────────────────────────────────────▶ target dev  (/Users/<you>/.bundle/...)
                                                   • bundle validate         schema: [dev_<you>_]demo
                           merge main ──▶ CD (deploy.yml)
                                                   • pytest
                                                   • bundle deploy -t prod ─▶ target prod (/Users/<sp-id>/.bundle/...)
                                                     (OAuth M2M = SP)         schema: demo_prod, job: etl_job
```

## Thiết lập một lần

### 1. Databricks Free Edition
1. Đăng nhập workspace → **Settings → Identity and access → Service principals → Add new**, đặt tên `github-cicd`.
2. Mở SP vừa tạo → tab **Secrets → Generate secret** → copy **Client ID** và **Secret** (secret chỉ hiện một lần).
3. Cho SP quyền dùng catalog `workspace`: chạy trong SQL editor
   ```sql
   GRANT USE CATALOG, CREATE SCHEMA ON CATALOG workspace TO `<client-id-của-SP>`;
   ```
4. Copy URL workspace (dạng `https://dbc-fac00343-a7e8.cloud.databricks.com`).

> Nếu workspace không cho tạo SP/OAuth secret: dùng phương án dự phòng là Personal Access Token
> (User Settings → Developer → Access tokens) và đổi biến môi trường trong workflow thành `DATABRICKS_TOKEN`.

### 2. GitHub repo
- **Settings → Environments → New environment** tên `prod`.
- Trong environment `prod` (và cả ở mức repo để `ci.yml` dùng được):
  - Variable `DATABRICKS_HOST` = URL workspace
  - Secret `DATABRICKS_CLIENT_ID`, `DATABRICKS_CLIENT_SECRET`
- **Settings → Branches**: bảo vệ `main`, bắt buộc PR + check `CI` pass.

### 3. Sửa placeholder
- `databricks.yml`: đã điền sẵn host `dbc-fac00343-a7e8` và email `hieuphso@gmail.com`.

### 4. (Tuỳ chọn) Git folder cho dev tương tác
Workspace → **Settings → Linked accounts → GitHub** → tạo Git folder trỏ tới repo để sửa notebook trên UI.
Git folder chỉ dùng để **dev**; prod luôn deploy qua bundle từ CI.

## Dùng hằng ngày
```bash
databricks auth login --host https://dbc-fac00343-a7e8.cloud.databricks.com   # một lần
databricks bundle deploy -t dev       # deploy bản dev của bạn
databricks bundle run etl_job -t dev  # chạy thử
pytest -q                             # test local
```
Mở PR → `CI` chạy test + validate. Merge vào `main` → `Deploy to Databricks` deploy prod.
Muốn chạy job prod sau deploy: Actions → *Deploy to Databricks* → *Run workflow* → tick smoke test.

## Lưu ý giới hạn Free Edition
- Chỉ serverless: không khai báo `new_cluster`/`job_clusters` trong job.
- Quota ngày: vượt quota thì compute bị tắt tới hết ngày → hạn chế chạy job trong CI.
- Tối đa 5 task job chạy đồng thời / account; 1 workspace / account.
- Chỉ cho mục đích phi thương mại; không SLA.
