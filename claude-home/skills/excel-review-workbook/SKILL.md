---
name: excel-review-workbook
description: Use when preparing an Excel file for the user or a BU to review or fill in (review scores, CDT checks, version compare, part breakdowns). Triggers - "ทำเป็น excel", "ไฟล์ให้ BU ตรวจ", "ให้ฉันรีวิว", "review file", "compare sheet", "xlsx".
---

# Excel review workbook

Purpose: the user reviews by hand in Excel (no paid judges) and the BU fills in checks; the file must be readable
without explanation, verified before sending, and reproducible from a script.

Builders to copy (all openpyxl):
- Review with blank score columns: `~/Documents/projects_cj/npd-comparables/data/work/prompt_sim/v3/build_review_pcb_all.py`
- Interactive compare with legend + navigation: `.../data/work/prompt_sim/v3/build_quick_compare.py`
- BU fill-in with dropdown: `.../data/work/prompt_sim/v3/build_cdt_conflicts.py`,
  `.../data/work/prompt_sim/report/bu_identity/build_conflicts_xlsx.py`
- Merge + independent checks: `.../report/bu_identity/build_parts_xlsx.py`, `build_core_identity_xlsx.py`,
  `build_prompt_compare.py`

## Procedure

1. Builder script lives next to the output xlsx; docstring says inputs, "no BQ / LLM / embedding", and the run line
   `uv run --with openpyxl [--with pyyaml] python <builder>.py`.
2. Sheet 1 `README` in Thai (for the user / BU): what the file is, how to use each sheet, what to fill, how
   columns were derived (rules, not hand work), counts, data source + date, builder path.
3. Data sheets: bold header with a fill, wrapped text, set column widths, `freeze_panes` below the header (and
   left of the id columns), `auto_filter` over the table.
4. Input columns for the reviewer are blank and highlighted (yellow `FFF2CC` / `FFF9C4`), with a `DataValidation`
   dropdown where the answer is a choice (e.g. `CDT ผิด,CDT ถูก,ไม่แน่ใจ`; `review_score (0-3)` + `comment`).
5. Colours: one meaning per colour, written in a legend box or the README (e.g. red bold = same brand, grey = also
   in v1, green = new vs v1, amber = pack/tier differs). Do not reuse a colour for a second meaning.
6. Add a summary / pivot sheet (counts per BU / category / type) and a data_notes sheet for non-row issues.
7. Verify before sending: recompute counts from the source data, check every quoted span / value with code (split
   " | " pieces, L8), show check columns in the sheet and print misses; assert expected totals.
8. `open <file>.xlsx` for the user and give a short Thai summary, not a long terminal table.

## Hard rules

- Plain Excel only: INDEX/MATCH, IFERROR, COUNTIF; no FILTER / XLOOKUP / LET (build_quick_compare.py).
- A hyperlink cannot change a cell value (it cannot set the dropdown cell); for "jump to item" write static
  per-item blocks on their own sheet and link to their anchors (`#by_npd!A<row>`), with a "← overview" link back.
- Scores are comparable only within one version; say so in the legend.
- Diagnostic what-if data is labelled as simulation (จำลอง) wherever it appears.
- No hand edits of product text or CDT in the workbook (memory no-hand-edits-separate-parts).

## Done when

- File opens, README first, filters + frozen panes work, dropdowns on input columns, check columns show no
  unexplained misses, counts in README equal the printed counts.

## Pitfalls

- Whole-cell span check on " | " packed cells gives false NOT FOUND (L8).
- Long terminal tables instead of a file: the user prefers Excel opened with `open` (memory
  review-and-agents-workflow).
