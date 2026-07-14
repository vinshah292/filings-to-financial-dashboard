"""
fetch_edgar.py — pull the latest SEC EDGAR data for Houlihan Lokey (CIK 0001302215) into data/.

1. Refreshes XBRL company facts (auto-includes any newly reported fiscal period).
2. Scans the submissions feed for earnings-release 8-Ks (Item 2.02) not yet in
   extract_quarterly.py's ingest list, and prints the accession lines to add.

SEC is free; be polite (declared User-Agent, no hammering). Run via `refresh.py --fetch`.
"""
import urllib.request, json, os

UA="fpa-portfolio-research vinshah292@icloud.com"
CIK="0001302215"
HERE=os.path.dirname(os.path.abspath(__file__))
DATA=os.path.join(os.path.dirname(HERE),"data"); os.makedirs(DATA,exist_ok=True)

def get(url):
    req=urllib.request.Request(url,headers={"User-Agent":UA})
    return urllib.request.urlopen(req,timeout=90).read()

# 1) company facts (full XBRL history — new periods appear automatically)
facts=get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{CIK}.json")
open(os.path.join(DATA,"hli_facts.json"),"wb").write(facts)
print(f"refreshed data/hli_facts.json ({len(facts)//1024} KB)")

# 2) detect earnings 8-Ks (Item 2.02 = Results of Operations) not yet ingested
subs=json.loads(get(f"https://data.sec.gov/submissions/CIK{CIK}.json"))
rec=subs["filings"]["recent"]
known=open(os.path.join(HERE,"extract_quarterly.py"),encoding="utf-8").read().replace("-","")
items=rec.get("items",[""]*len(rec["form"]))
new=[]
for form,acc,date,it in zip(rec["form"],rec["accessionNumber"],rec["filingDate"],items):
    if form=="8-K" and "2.02" in it and acc.replace("-","") not in known:
        new.append((date,acc))
if new:
    print("\nNEW earnings 8-K(s) not yet ingested — add these to extract_quarterly.py RELS:")
    for d,a in sorted(new,reverse=True): print(f'  ("{d}","{a}"),')
else:
    print("ingest list is current — no new earnings 8-Ks since last build")
