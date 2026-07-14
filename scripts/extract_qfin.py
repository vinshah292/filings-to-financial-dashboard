"""Extract quarterly (FY22Q1-FY26Q4) financials for every model line from XBRL company facts.
Flows via YTD-differencing (self-ties to annual); balance sheet via quarter-end instants."""
import json, datetime as dt
SP=r"C:\Users\vinsh\OneDrive\Documents\Claude\Projects\Github Finance Outputs\Houlihan Lokey Trend Analysis Project\data"
G=json.load(open(SP+r"\hli_facts.json",encoding="utf-8"))["facts"]["us-gaap"]
FYS=[2022,2023,2024,2025,2026]; QS=[1,2,3,4]
def days(a,b): return (dt.date.fromisoformat(b)-dt.date.fromisoformat(a)).days
QEND={}
for fy in FYS:
    QEND[(fy,1)]=f"{fy-1}-06-30"; QEND[(fy,2)]=f"{fy-1}-09-30"; QEND[(fy,3)]=f"{fy-1}-12-31"; QEND[(fy,4)]=f"{fy}-03-31"

def byend(tag,unit="USD"):
    """{end_date: {duration_days: val}} for durations; and annual FY values."""
    node=G.get(tag);  dur={}; inst={}; ann={}
    if not node: return dur,inst,ann
    for r in node["units"].get(unit,[]):
        if "start" in r:
            d=days(r["start"],r["end"]); dur.setdefault(r["end"],{})[d]=r["val"]
            if r.get("form")=="10-K" and r.get("fp")=="FY" and d>350: ann[r["end"]]=r["val"]
        else:
            inst[r["end"]]=r["val"]
    return dur,inst,ann

def qflow(tag,unit="USD"):
    """3-month values via YTD differencing. Q1=YTD90; Q2=YTD182-YTD90; Q3=YTD274-YTD182; Q4=annual-YTD274."""
    dur,inst,ann=byend(tag,unit); out={}
    def ytd(end,tgt):
        return next((v for dd,v in dur.get(end,{}).items() if abs(dd-tgt)<10),None)
    for fy in FYS:
        junE,sepE,decE,marE=f"{fy-1}-06-30",f"{fy-1}-09-30",f"{fy-1}-12-31",f"{fy}-03-31"
        y1,y2,y3=ytd(junE,90),ytd(sepE,182),ytd(decE,274); a=ann.get(marE)
        if y1 is not None: out[(fy,1)]=y1
        if y2 is not None and y1 is not None: out[(fy,2)]=y2-y1
        if y3 is not None and y2 is not None: out[(fy,3)]=y3-y2
        if a is not None and y3 is not None: out[(fy,4)]=a-y3
    return out

def qinst(tag):
    dur,inst,ann=byend(tag); out={}
    for fy in FYS:
        for q in QS:
            e=QEND[(fy,q)]
            if e in inst: out[(fy,q)]=inst[e]
            elif q==4 and ann.get(e) is not None: out[(fy,q)]=ann[e]
    return out

def resid(anchor_q, comp_qs):
    out={}
    for k,v in anchor_q.items():
        s=sum(cq.get(k,0) for cq in comp_qs); out[k]=v-s
    return out

IS_EXP=["LaborAndRelatedExpense","TravelAndEntertainmentExpense","OperatingLeaseExpense",
        "DepreciationAndAmortization","CommunicationsAndInformationTechnology","ProfessionalFees","OtherCostAndExpenseOperating"]
lines={}
# income statement (flows)
lines["rev"]=qflow("RevenueFromContractWithCustomerExcludingAssessedTax")
for k,t in [("comp","LaborAndRelatedExpense"),("te","TravelAndEntertainmentExpense"),("rent","OperatingLeaseExpense"),
            ("it","CommunicationsAndInformationTechnology"),("prof","ProfessionalFees"),("othx","OtherCostAndExpenseOperating"),
            ("da","DepreciationAndAmortization"),("oinc","NonoperatingIncomeExpense"),("tax","IncomeTaxExpenseBenefit"),
            ("nci","NetIncomeLossAttributableToNoncontrollingInterest")]:
    lines[k]=qflow(t)
opex=qflow("OperatingExpenses")
lines["acq"]=resid(opex,[qflow(t) for t in IS_EXP])
lines["dsh"]=qflow("WeightedAverageNumberOfDilutedSharesOutstanding","shares")  # weighted avg (annual handled separately)
# balance sheet (instants)
for k,t in [("cash","CashAndCashEquivalentsAtCarryingValue"),("rcash","RestrictedCashAndCashEquivalents"),
            ("binv","MarketableSecurities"),("ar","AccountsReceivableNet"),("ppe","PropertyPlantAndEquipmentNet"),
            ("rou","OperatingLeaseRightOfUseAsset"),("gw","Goodwill"),("inta","OtherIntangibleAssetsNet"),
            ("dta","DeferredIncomeTaxAssetsNet"),("accr","EmployeeRelatedLiabilitiesCurrentAndNoncurrent"),
            ("ap","AccountsPayableAndAccruedLiabilitiesCurrentAndNoncurrent"),("oll","OperatingLeaseLiability"),
            ("divp","DividendsPayableCurrentAndNoncurrent"),("rnci","RedeemableNoncontrollingInterestEquityCarryingAmount"),
            ("apic","AdditionalPaidInCapital"),("re","RetainedEarningsAccumulatedDeficit"),
            ("aoci","AccumulatedOtherComprehensiveIncomeLossNetOfTax")]:
    lines[k]=qinst(t)
A=qinst("Assets"); L=qinst("Liabilities"); E=qinst("StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest")
lines["oasset"]=resid(A,[lines[k] for k in ["cash","rcash","binv","ar","ppe","rou","gw","inta","dta"]])
lines["oliab"]=resid(L,[lines[k] for k in ["accr","ap","oll","divp"]])
lines["oeq"]=resid(E,[lines[k] for k in ["apic","re","aoci"]])
# cash flow (flows/YTD)
for k,t in [("cf_da","DepreciationDepletionAndAmortization"),("cf_ami","AmortizationOfIntangibleAssets"),
            ("cf_sbc","AllocatedShareBasedCompensationExpense"),("cf_pda","ProvisionForDoubtfulAccounts"),
            ("cf_dt","DeferredIncomeTaxExpenseBenefit")]:
    lines[k]=qflow(t)
ni=qflow("ProfitLoss"); lines["cf_ni"]=ni
cfo=qflow("NetCashProvidedByUsedInOperatingActivities")
lines["cf_wc"]=resid(cfo,[ni]+[lines[k] for k in ["cf_da","cf_ami","cf_sbc","cf_pda","cf_dt"]])
capx=qflow("PaymentsToAcquirePropertyPlantAndEquipment"); acqb=qflow("PaymentsToAcquireBusinessesNetOfCashAcquired")
binv=qflow("PaymentsToAcquireInvestments"); sinv=qflow("ProceedsFromSaleMaturityAndCollectionsOfInvestments")
lines["cf_capx"]={k:-v for k,v in capx.items()}; lines["cf_acq"]={k:-v for k,v in acqb.items()}
lines["cf_binv"]={k:-v for k,v in binv.items()}; lines["cf_sinv"]=sinv
cfi=qflow("NetCashProvidedByUsedInInvestingActivities")
lines["cf_oinv"]={k: cfi[k]-(sinv.get(k,0)-capx.get(k,0)-acqb.get(k,0)-binv.get(k,0)) for k in cfi}
div=qflow("PaymentsOfDividends"); buy=qflow("PaymentsForRepurchaseOfCommonStock"); txw=qflow("PaymentsRelatedToTaxWithholdingForShareBasedCompensation")
lines["cf_div"]={k:-v for k,v in div.items()}; lines["cf_buy"]={k:-v for k,v in buy.items()}; lines["cf_txw"]={k:-v for k,v in txw.items()}
cff=qflow("NetCashProvidedByUsedInFinancingActivities")
lines["cf_ofin"]={k: cff[k]-(-div.get(k,0)-buy.get(k,0)-txw.get(k,0)) for k in cff}
lines["cf_fx"]=qflow("EffectOfExchangeRateOnCashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents")

# save (keys as "fy-q")
out={ln:{f"{fy}-{q}":round(v/1e6,3) for (fy,q),v in d.items()} for ln,d in lines.items()}
json.dump(out,open(SP+r"\hli_qfin.json","w"),indent=0)
# VERIFY: quarterly sum vs annual for key flows; Q4 vs FY-end for BS
def ann(tag):
    _,_,a=byend(tag); return {fy:a.get(f"{fy}-03-31") for fy in FYS}
print("=== VERIFY flows: sum(4 quarters) vs reported annual ($mm) ===")
for ln,tag in [("rev","RevenueFromContractWithCustomerExcludingAssessedTax"),("comp","LaborAndRelatedExpense"),
               ("tax","IncomeTaxExpenseBenefit"),("cf_ni","ProfitLoss")]:
    A2=ann(tag)
    for fy in FYS:
        qs=sum(lines[ln].get((fy,q),0) for q in QS)/1e6
        a=(A2[fy] or 0)/1e6
        print(f"  {ln} FY{fy}: Qsum {qs:9.1f} vs annual {a:9.1f}  {'OK' if abs(qs-a)<1 else 'DIFF'}")
print("\n=== VERIFY BS: Q4 vs FY-end ($mm) ===")
Aq=qinst("Assets"); Aa=ann("Assets")
for fy in FYS:
    q4=(Aq.get((fy,4)) or 0)/1e6; fyv=(Aa[fy] or 0)/1e6
    print(f"  Assets FY{fy}: Q4 {q4:9.1f} vs FY-end {fyv:9.1f}  {'OK' if abs(q4-fyv)<1 else 'DIFF'}")
print("\nsaved hli_qfin.json ; lines:",len(out),"; FY22 rev present:", any((2022,q) in lines['rev'] for q in QS))
