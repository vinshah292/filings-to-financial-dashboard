"""Pull quarterly segment data (revenue, MDs, deal counts) from all 20 HLI earnings releases."""
import json, re, io, os, urllib.request, time
import pandas as pd

UA="fpa-portfolio-research vinshah292@icloud.com"
SP=r"C:\Users\vinsh\OneDrive\Documents\Claude\Projects\Github Finance Outputs\Houlihan Lokey Trend Analysis Project\data"
BASE="https://www.sec.gov/Archives/edgar/data/1302215"

# (date, accession) for the 20 earnings 8-Ks
RELS=[("2026-05-07","0001302215-26-000014"),("2026-01-29","0001302215-26-000003"),
("2025-10-31","0001302215-25-000108"),("2025-07-30","0001302215-25-000089"),
("2025-05-08","0001302215-25-000019"),("2025-01-29","0001302215-25-000004"),
("2024-10-31","0001302215-24-000107"),("2024-07-31","0001302215-24-000081"),
("2024-05-09","0001302215-24-000010"),("2024-02-02","0001302215-24-000002"),
("2023-10-27","0001302215-23-000083"),("2023-07-28","0001302215-23-000068"),
("2023-05-10","0001302215-23-000013"),("2023-02-01","0001302215-23-000003"),
("2022-10-28","0001302215-22-000073"),("2022-07-29","0001302215-22-000065"),
("2022-05-13","0001302215-22-000015"),("2022-02-08","0001302215-22-000003"),
("2021-10-29","0001302215-21-000083"),("2021-08-03","0001302215-21-000075")]

def fyq(date):
    m=int(date[5:7]); y=int(date[:4])
    return (y+1,1) if m in(7,8) else (y+1,2) if m in(10,11) else (y,3) if m in(1,2) else (y,4)

def get(url):
    req=urllib.request.Request(url,headers={"User-Agent":UA})
    return urllib.request.urlopen(req,timeout=60).read()

def firstnum(row,lo,hi):
    for v in row.values:
        try:
            n=float(str(v).replace(",","").replace("$","").strip())
            if lo<=n<=hi: return n
        except: pass
    return None

data={}
for date,acc in RELS:
    fy,q=fyq(date); a=acc.replace("-","")
    key=f"FY{fy}Q{q}"
    try:
        cache=os.path.join(SP,f"relq_{a}.htm")
        if os.path.exists(cache):
            html=open(cache,encoding="utf-8",errors="ignore").read()
        else:
            idx=json.loads(get(f"{BASE}/{a}/index.json"))
            doc=next(i["name"] for i in idx["directory"]["item"] if "ex99" in i["name"].lower() and i["name"].lower().endswith(".htm"))
            html=get(f"{BASE}/{a}/{doc}").decode("utf-8","ignore")
            open(cache,"w",encoding="utf-8").write(html)
        seg={}
        for tb in pd.read_html(io.StringIO(html)):
            flat=" ".join(str(x) for x in tb.values.flatten())
            if "# of Managing Directors" not in flat: continue
            present=[k for s,k in [("Corporate Finance","CF"),("Financial Restructuring","FR"),("Financial and Valuation","FVA")] if s in flat]
            if len(present)!=1: continue
            name=present[0]
            rev=mds=deals=None
            for _,row in tb.iterrows():
                lab=str(row.iloc[0]).strip()
                if lab=="Revenues": rev=firstnum(row,10000,999999999)
                elif lab.startswith("# of Managing Directors"): mds=firstnum(row,20,400)
                elif lab.startswith(("# of Closed transactions","# of Fee Events")): deals=firstnum(row,1,5000)
            seg[name]={"rev":rev,"mds":mds,"deals":deals}
        data[key]={"date":date,"seg":seg}
        got="  ".join(f"{s}:${seg.get(s,{}).get('rev',0)/1000:.0f}M/{seg.get(s,{}).get('mds')}md/{seg.get(s,{}).get('deals')}d" for s in ["CF","FR","FVA"])
        print(f"{key} ({date}): {got}")
    except Exception as e:
        print(f"{key} ({date}): ERROR {e}")
    time.sleep(0.15)

json.dump(data,open(SP+r"\hli_quarterly.json","w"),indent=1)
print("\nsaved hli_quarterly.json")
# verify: sum of 4 quarters vs known annual segment revenue ($000s)
ANN={2022:{"CF":1593083,"FR":392818,"FVA":284057},2023:{"CF":1127126,"FR":395733,"FVA":286588},
2024:{"CF":1106826,"FR":521984,"FVA":285594},2025:{"CF":1526756,"FR":544478,"FVA":318182},
2026:{"CF":1744634,"FR":528655,"FVA":344227}}
print("\n=== VERIFY: sum of 4 quarters vs reported annual (segment revenue, $000s) ===")
for fy in range(2022,2027):
    for s in ["CF","FR","FVA"]:
        qsum=sum(data.get(f"FY{fy}Q{q}",{}).get("seg",{}).get(s,{}).get("rev") or 0 for q in range(1,5))
        ann=ANN[fy][s]; ok="OK" if abs(qsum-ann)<1500 else f"DIFF {qsum-ann:+.0f}"
        print(f"  FY{fy} {s}: Q-sum {qsum:>10,.0f}  vs annual {ann:>10,}  {ok}")
