---
name: bq-readonly-pull
description: Use whenever data must be read from BigQuery (pull, snapshot, refresh inputs, query a table). Triggers - "ดึงข้อมูลจาก BQ", "pull BigQuery", "query BQ", "ดึง CDT ใหม่", "refresh data", "snapshot table".
---

# Read-only BigQuery pull

Purpose: get BigQuery data into local files safely: SELECT only, cost known before running, every result saved
with a manifest so later work (and workers) reads files, not BigQuery.

Pattern scripts (copy, do not re-invent):
- Folder of `.sql` files + dry run / `--go`:
  `~/Documents/projects_cj/npd-comparables/data/work/prompt_sim/report/bu_identity/pull.py`
  (queries in `queries/*.sql`, output `inputs/*.parquet`)
- Whole dataset snapshot into a dated folder + `manifest.json`:
  `~/Documents/projects_cj/npd-comparables/data/work/cdt_master/pull_cdt_master.py`
- Credentials with Drive scope:
  `~/Documents/projects_cj/npd-comparables/src/npd_comparables/adapters/outbound/bigquery/client.py`

## Procedure

1. Write each query as its own `.sql` file and show the SQL to the user before running (user decision, memory
   v3-prompt-state).
2. Refuse anything but reads: the script asserts no `INSERT / DELETE / CREATE / UPDATE / MERGE / DROP` word.
3. Dry run first (`QueryJobConfig(dry_run=True, use_query_cache=False)`), print bytes per query, report the total
   to the user and wait for the go.
4. Run with `maximum_bytes_billed` set (the scripts use 5 GB), only with an explicit flag (`--go`).
5. Save each result as parquet in a dated folder (`<area>/<YYYY-MM-DD>/`) with `manifest.json`: rows, columns,
   table type, SQL, `_pulled_at`. Keep the `.sql` files and the pull script next to the data.
6. Record the pull (files, rows, GB scanned, date) in the README / session log that uses it.

## Auth

- ADC: `gcloud auth application-default login` when it has expired (seen 2026-10-06: Vertex ADC expired).
- Sheet-backed tables (e.g. `pre_screen_product_submission`, `cdt_path`) are EXTERNAL tables over Google Sheets:
  log in with `gcloud auth login --enable-gdrive-access --update-adc`, and create the client with scopes
  `cloud-platform` + `drive.readonly` (`google.auth.default(scopes=...)`).

## Hard rules

- BigQuery is read-only in exploration work. Writes exist only in the project's guarded `publish --target bq`
  (dry run unless `--no-dry-run`, `--replace-existing` for delete+insert), tested against `stg_npd_engine` with
  `--env stg`, never against `npd_engine` (npd-comparables CLAUDE.md).
- Workers (Codex, sub-agents) never query BigQuery; the orchestrator pulls and hands them files (codex-harness).
- No query runs before the user has seen the SQL and the dry-run bytes.

## Done when

- Every query has a dry-run line and a saved parquet with row count; manifest written; files listed for the user.

## Pitfalls (when reading the pulled data, npd-comparables lessons)

- `cdt_path` skips empty layers: read `layer1_detail..layer8_detail` (P3).
- CDT sits on one barcode per material: aggregate by `material_code` (P4).
- Layer labels change between pulls (`consumer` -> `customer`): compare with the previous pull before use (P1).
