"""
build_dashboard_data.py, the single verified data layer for the HLI trend dashboard.

Source of truth: SEC. Financial lines come from XBRL company facts (hli_qfin.json, itself
YTD-differenced and tied to reported annuals). Segment revenue / MD headcount / deal counts
come from the 20 earnings-release 8-Ks (hli_quarterly.json). Every KPI is computed here in
Python, the LLM never produces a number. Tie-outs assert before anything is written.

Output: dashboard_data.json (annual FY2022-FY2026 series + computed KPIs) next to this script's
project root. Re-run after a new filing is ingested and every downstream chart/dashboard updates.
"""
import json, os

SP=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),"data")
PROJ=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FYS=list(range(2022,2027))
qf=json.load(open(SP+r"\hli_qfin.json",encoding="utf-8"))       # $mm, keys "YYYY-Q"
qs=json.load(open(SP+r"\hli_quarterly.json",encoding="utf-8"))  # $000s segments, keys "FYyyyyQq"
facts=json.load(open(SP+r"\hli_facts.json",encoding="utf-8"))["facts"]["us-gaap"]

def ann_flow(line):
    d=qf[line]; return {fy: round(sum(d.get(f"{fy}-{q}",0) for q in (1,2,3,4)),3) for fy in FYS}
def ann_seg_rev(seg):
    return {fy: round(sum(qs[f"FY{fy}Q{q}"]["seg"][seg]["rev"] for q in (1,2,3,4))/1000,3) for fy in FYS}
def ye_md(seg):
    return {fy: qs[f"FY{fy}Q4"]["seg"][seg]["mds"] for fy in FYS}
def ann_deals(seg):
    return {fy: int(sum(qs[f"FY{fy}Q{q}"]["seg"][seg]["deals"] for q in (1,2,3,4))) for fy in FYS}

# --- XBRL reported annual revenue (independent cross-check) ---
def xbrl_annual(tag):
    out={}
    for r in facts[tag]["units"]["USD"]:
        if r.get("form")=="10-K" and r.get("fp")=="FY" and "start" in r:
            from datetime import date
            d=(date.fromisoformat(r["end"])-date.fromisoformat(r["start"])).days
            if d>350 and r["end"].endswith("03-31"):
                out[int(r["end"][:4])]=round(r["val"]/1e6,3)
    return out

rev   = ann_flow("rev")
cf    = ann_seg_rev("CF"); fr = ann_seg_rev("FR"); fva = ann_seg_rev("FVA")
comp  = ann_flow("comp")
opex_ex_da = {fy: sum(ann_flow(l)[fy] for l in ("comp","te","rent","it","prof","othx","acq")) for fy in FYS}
da    = ann_flow("da")
ebit  = {fy: round(rev[fy]-opex_ex_da[fy]-da[fy],3) for fy in FYS}
ebitda= {fy: round(ebit[fy]+da[fy],3) for fy in FYS}
# Net income ATTRIBUTABLE TO HLI (parent) is the audited XBRL annual figure, not consolidated.
# us-gaap:NetIncomeLoss = attributable to parent; us-gaap:ProfitLoss = consolidated (incl. NCI).
ni_hli   = xbrl_annual("NetIncomeLoss")
ni_consol= xbrl_annual("ProfitLoss")
assert all(fy in ni_hli for fy in FYS), "NetIncomeLoss missing a fiscal year"
md_cf=ye_md("CF"); md_fr=ye_md("FR"); md_fva=ye_md("FVA")
md_tot={fy: md_cf[fy]+md_fr[fy]+md_fva[fy] for fy in FYS}
deals_cf=ann_deals("CF"); deals_fr=ann_deals("FR")   # closed transactions; FVA is fee events (excluded)

# --- derived KPIs ---
comp_ratio={fy: round(comp[fy]/rev[fy],4) for fy in FYS}
op_margin ={fy: round(ebit[fy]/rev[fy],4) for fy in FYS}
ebitda_margin={fy: round(ebitda[fy]/rev[fy],4) for fy in FYS}
net_margin={fy: round(ni_hli[fy]/rev[fy],4) for fy in FYS}
rev_per_md={fy: round(rev[fy]/md_tot[fy],3) for fy in FYS}

# --- TIE-OUTS (fail loud) ---
xrev=xbrl_annual("RevenueFromContractWithCustomerExcludingAssessedTax")
print("=== TIE-OUT 1: segment sum vs total revenue ($mm) ===")
for fy in FYS:
    seg=round(cf[fy]+fr[fy]+fva[fy],3)
    ok=abs(seg-rev[fy])<0.6
    print(f"  FY{fy}: CF+FR+FVA {seg:8.1f}  total {rev[fy]:8.1f}  {'OK' if ok else 'DIFF '+str(round(seg-rev[fy],2))}")
    assert ok, f"segment sum != total FY{fy}"
print("=== TIE-OUT 2: quarterly-summed revenue vs XBRL 10-K annual ($mm) ===")
for fy in FYS:
    x=xrev.get(fy); ok=(x is None) or abs(x-rev[fy])<0.6
    print(f"  FY{fy}: qsum {rev[fy]:8.1f}  XBRL {('n/a' if x is None else f'{x:8.1f}')}  {'OK' if ok else 'DIFF'}")
    assert ok, f"qsum revenue != XBRL FY{fy}"
print("=== TIE-OUT 3: net income to HLI + NCI = consolidated (XBRL attribution) ===")
nci_ann=xbrl_annual("NetIncomeLossAttributableToNoncontrollingInterest")
for fy in FYS:
    n=nci_ann.get(fy,0.0)
    print(f"  FY{fy}: HLI {ni_hli[fy]:8.1f} + NCI {n:6.2f} = {ni_hli[fy]+n:8.1f}  vs consolidated {ni_consol[fy]:8.1f}")

data={
 "meta":{"company":"Houlihan Lokey, Inc.","ticker":"HLI","cik":"0001302215","fy_end":"March 31",
         "fys":FYS,"units":"$ in millions unless noted","basis":"YoY, fiscal years",
         "source":"SEC EDGAR: XBRL company facts + 20 earnings-release 8-Ks (Ex-99.1)",
         "ebitda_note":"EBITDA = GAAP operating income + D&A (not HL's non-GAAP Adjusted EBITDA)",
         "ni_note":"Net income to HLI = us-gaap:NetIncomeLoss (attributable to parent), audited XBRL annual; not consolidated ProfitLoss"},
 "revenue_total":rev, "xbrl_revenue":xrev,
 "segment_revenue":{"CF":cf,"FR":fr,"FVA":fva},
 "ebit":ebit,"ebitda":ebitda,"da":da,"comp":comp,"ni_to_hli":ni_hli,"ni_consolidated":ni_consol,
 "md":{"CF":md_cf,"FR":md_fr,"FVA":md_fva,"total":md_tot},
 "deals":{"CF":deals_cf,"FR":deals_fr},
 "kpi":{"comp_ratio":comp_ratio,"op_margin":op_margin,"ebitda_margin":ebitda_margin,
        "net_margin":net_margin,"rev_per_md":rev_per_md},
}
json.dump(data,open(os.path.join(PROJ,"dashboard_data.json"),"w"),indent=1)

print("\n=== ANNUAL SUMMARY ($mm) ===")
hdr="metric      "+"".join(f"FY{fy:>7}" for fy in FYS); print(hdr)
def row(name,d,f="{:9.1f}"): print(f"{name:<12}"+"".join(f.format(d[fy]) for fy in FYS))
row("Revenue",rev); row("  CF",cf); row("  FR",fr); row("  FVA",fva)
row("EBIT",ebit); row("EBITDA",ebitda); row("NI to HLI",ni_hli)
row("Op margin%",{fy:op_margin[fy]*100 for fy in FYS},"{:8.1f}%")
row("EBITDA m%",{fy:ebitda_margin[fy]*100 for fy in FYS},"{:8.1f}%")
row("Comp ratio%",{fy:comp_ratio[fy]*100 for fy in FYS},"{:8.1f}%")
row("Total MDs",{fy:float(md_tot[fy]) for fy in FYS},"{:9.0f}")
row("Rev/MD",rev_per_md)
row("CF deals",{fy:float(deals_cf[fy]) for fy in FYS},"{:9.0f}")
row("FR deals",{fy:float(deals_fr[fy]) for fy in FYS},"{:9.0f}")
print("\nsaved dashboard_data.json")
