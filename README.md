# Houlihan Lokey — Five-Year Operating Trends

A self-updating FP&A dashboard for **Houlihan Lokey (NYSE: HLI)**, built end-to-end from SEC filings.
Every number is computed in Python and tied out to the filings. AI writes only the commentary — never a number.

**Data flow:** SEC EDGAR → verified data layer (with tie-outs) → charts → web dashboard. When HL files new
earnings, one command re-pulls EDGAR and regenerates everything.

---

## The thesis

> **AI narrates, deterministic code calculates, tie-outs prove the prose matches the math.**

No figure on the dashboard comes from a language model. Segment revenue, headcount, and deal counts are parsed
from the earnings releases; the income statement is XBRL, YTD-differenced to quarters. The build **fails loud** if
the numbers stop tying out, so a broken figure can never reach the dashboard.

## What it demonstrates (FP&A skill set)

- Pulling and normalizing **primary-source** data (SEC EDGAR XBRL + 20 earnings-release 8-Ks)
- Building a verified quarterly + annual dataset that reconciles to the reported financials
- Segment analysis, KPI design, and a countercyclical read of the business model
- Turning it into an **executive-ready dashboard** with an automation loop for new filings

## The four outputs

| # | Output | What it shows |
|---|--------|---------------|
| 1 | **KPI Scorecard** | Revenue, operating margin, net income, MDs, revenue/MD, comp ratio — FY2022 → FY2026, with sparklines |
| 2 | **Revenue Bridge** | Where four years of net revenue growth came from, by segment |
| 3 | **Revenue Mix** | Stacked segment revenue in dollars (CF / FR / FVA) |
| 4 | **Counter-Cyclical Hedge** | Corporate Finance vs Financial Restructuring, indexed — the restructuring hedge in action |

## Architecture

```
SEC EDGAR  (XBRL company facts + earnings-release 8-Ks, CIK 0001302215)
   │
   ├─ fetch_edgar.py          pull latest XBRL facts, detect new earnings 8-Ks
   ├─ extract_qfin.py         income statement → quarterly, YTD-differenced   → data/hli_qfin.json
   ├─ extract_quarterly.py    segment revenue / MDs / deals from 20 releases  → data/hli_quarterly.json
   │
   ├─ build_dashboard_data.py compute annual series + KPIs, ASSERT tie-outs   → dashboard_data.json
   ├─ render_charts.py        four outputs, Houlihan Lokey palette            → charts/*.png
   ├─ build_dashboard.py      self-contained web page                        → docs/index.html
   └─ build_excel.py          auditable workbook, ties to the dashboard       → Houlihan Lokey - Financial Model.xlsx
```

The **Excel workbook** is the human-readable hub: a Cover, an Operating Model (annual, with live ratio
formulas), and a Quarterly Detail audit trail. Every figure ties to the same verified data as the dashboard.

## Verification (tie-outs that must pass before a build ships)

- **Segment revenue sums to total revenue** — every fiscal year, FY2022–FY2026.
- **Quarterly revenue sums to the reported 10-K annual** — every fiscal year.
- Headline figures were independently checked against the primary filings (revenue, segment revenue, MD
  headcount, operating margin, net income, comp ratio).

## Run it

```bash
python scripts/refresh.py            # rebuild charts + dashboard from local verified data
python scripts/refresh.py --fetch    # re-pull SEC EDGAR + re-extract first (run after a new filing)
```

Then open `docs/index.html` (the dashboard) or the Excel workbook.

## What the data says

- **Revenue is a V.** $2.27B (FY2022 peak) → $1.81B (FY2023, the M&A freeze) → a record **$2.62B in FY2026**.
- **The countercyclical hedge.** As Corporate Finance revenue fell ~31% into FY2024, Financial Restructuring rose
  ~33%. The restructuring book is what kept the peak-to-trough revenue drop to ~20% instead of collapsing with the
  M&A cycle.
- **Comp discipline.** The compensation ratio held at ~61.5% of revenue every year.
- **Honest caveat.** Operating margin and revenue per MD sit below their FY2022 levels — FY2022 was a GCA-boosted
  M&A boom, and HL kept adding Managing Directors (289 → 354) through the downturn. Record revenue, but on a larger,
  lower-productivity base than the peak.

---

*Source: SEC EDGAR, Houlihan Lokey, Inc. (CIK 0001302215). Fiscal year ends March 31. EBITDA shown is GAAP
operating income + D&A, not HL's non-GAAP Adjusted EBITDA. Built from public filings for financial-analysis
demonstration. Not investment advice.*
