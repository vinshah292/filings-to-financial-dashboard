"""
refresh.py — one command rebuilds the whole HLI dashboard.

  python scripts/refresh.py            rebuild charts + dashboard from local verified data/
  python scripts/refresh.py --fetch    also re-pull SEC EDGAR and re-extract first (new-filing path)

Pipeline:  [fetch_edgar -> extract_qfin -> extract_quarterly] -> build_dashboard_data
           (tie-outs) -> render_charts -> build_dashboard -> dashboard/index.html
Any step that fails (including a tie-out assertion) stops the run — a broken number never
reaches the dashboard.
"""
import subprocess, sys, os

HERE=os.path.dirname(os.path.abspath(__file__))
def run(name):
    print(f"\n{'='*60}\n  {name}\n{'='*60}")
    r=subprocess.run([sys.executable, os.path.join(HERE,name)])
    if r.returncode!=0: sys.exit(f"\nFAILED at {name} (exit {r.returncode}) — dashboard NOT updated.")

steps=["build_dashboard_data.py","render_charts.py","build_dashboard.py","build_excel.py"]
if "--fetch" in sys.argv:
    steps=["fetch_edgar.py","extract_qfin.py","extract_quarterly.py"]+steps

for st in steps: run(st)
print("\n[OK] refreshed -> docs/index.html (dashboard) + Houlihan Lokey - Financial Model.xlsx")
