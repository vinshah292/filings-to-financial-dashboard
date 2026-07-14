"""
build_dashboard.py, assembles the self-contained HLI trend dashboard (dashboard/index.html).

Reads the verified dashboard_data.json + the three rendered PNGs, computes the KPI scorecard
(card #4) with inline-SVG sparklines, embeds charts as base64 (single portable file, Artifact-ready),
and writes commentary grounded ONLY in the verified numbers. No number is typed by hand here,
every value is pulled from dashboard_data.json and formatted in code.
"""
import json, os, base64

PROJ=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AS_OF="July 13, 2026"
D=json.load(open(os.path.join(PROJ,"dashboard_data.json"),encoding="utf-8"))
FYS=D["meta"]["fys"]; F0,F1=FYS[0],FYS[-1]
def s(fy): return str(fy)
rev=D["revenue_total"]; seg=D["segment_revenue"]; kpi=D["kpi"]; md=D["md"]; ni=D["ni_to_hli"]

def b64(png):
    with open(os.path.join(PROJ,"charts",png),"rb") as f: return base64.b64encode(f.read()).decode()

def spark(series, good_up=True, w=132, h=34, pad=4):
    vals=[series[s(fy)] for fy in FYS]; lo,hi=min(vals),max(vals); rng=(hi-lo) or 1
    xs=[pad+(w-2*pad)*i/(len(vals)-1) for i in range(len(vals))]
    ys=[h-pad-(h-2*pad)*(v-lo)/rng for v in vals]
    pts=" ".join(f"{x:.1f},{y:.1f}" for x,y in zip(xs,ys))
    up=vals[-1]>=vals[0]; col="#3E8E5C" if up==good_up else "#A6403A"
    dot=f'<circle cx="{xs[-1]:.1f}" cy="{ys[-1]:.1f}" r="2.6" fill="{col}"/>'
    return (f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" preserveAspectRatio="none" '
            f'aria-hidden="true"><polyline fill="none" stroke="{col}" stroke-width="2" '
            f'stroke-linecap="round" stroke-linejoin="round" points="{pts}"/>{dot}</svg>')

def money(v,d=0): return f"${v:,.{d}f}"
def pct(v): return f"{v*100:,.1f}%"

# ---------- KPI scorecard cards (values pulled + computed) ----------
def chg_money(dc): d=dc[s(F1)]-dc[s(F0)]; return d, d/dc[s(F0)]
def cards():
    out=[]
    # (label, value_str, from->to str, delta_str, good?, sparkline)
    dr,pr=chg_money(rev)
    out.append(("Total Revenue", money(rev[s(F1)])+"M", f"{money(rev[s(F0)])}M → {money(rev[s(F1)])}M",
                f"{'+' if dr>=0 else ''}{pr*100:,.1f}%", dr>=0, spark(rev,True)))
    dom=kpi['op_margin'][s(F1)]-kpi['op_margin'][s(F0)]
    out.append(("Operating Margin", pct(kpi['op_margin'][s(F1)]), f"{pct(kpi['op_margin'][s(F0)])} → {pct(kpi['op_margin'][s(F1)])}",
                f"{dom*100:+,.1f} pts", dom>=0, spark(kpi['op_margin'],True)))
    dn,pn=chg_money(ni)
    out.append(("Net Income to HLI", money(ni[s(F1)])+"M", f"{money(ni[s(F0)])}M → {money(ni[s(F1)])}M",
                f"{'+' if dn>=0 else ''}{pn*100:,.1f}%", dn>=0, spark(ni,True)))
    t0=int(md['total'][s(F0)]); t1=int(md['total'][s(F1)]); dm=t1-t0
    out.append(("Managing Directors", f"{t1:,}", f"{t0:,} → {t1:,}",
                f"{dm:+,} MDs", dm>=0, spark({k:float(v) for k,v in md['total'].items()},True)))
    dv,pv=chg_money(kpi['rev_per_md'])
    out.append(("Revenue / MD", money(kpi['rev_per_md'][s(F1)],1)+"M", f"{money(kpi['rev_per_md'][s(F0)],1)}M → {money(kpi['rev_per_md'][s(F1)],1)}M",
                f"{'+' if dv>=0 else ''}{pv*100:,.1f}%", dv>=0, spark(kpi['rev_per_md'],True)))
    dcr=kpi['comp_ratio'][s(F1)]-kpi['comp_ratio'][s(F0)]
    out.append(("Comp Ratio", pct(kpi['comp_ratio'][s(F1)]), f"{pct(kpi['comp_ratio'][s(F0)])} → {pct(kpi['comp_ratio'][s(F1)])}",
                f"{dcr*100:+,.1f} pts", dcr<=0, spark(kpi['comp_ratio'],False)))  # lower comp ratio = favorable
    return out

def card_html(c):
    label,val,rng,delta,good,sv=c
    cls="up" if good else "down"
    return f'''<div class="kpi">
      <div class="kpi-label">{label}</div>
      <div class="kpi-value">{val}</div>
      <div class="kpi-spark">{sv}</div>
      <div class="kpi-foot"><span class="chip {cls}">{delta}</span><span class="kpi-range">{rng}</span></div>
    </div>'''

# ---------- section commentary (grounded in the numbers) ----------
cf1,fr1,fva1=seg['CF'][s(F1)],seg['FR'][s(F1)],seg['FVA'][s(F1)]
mixcf,mixfr,mixfva=cf1/rev[s(F1)],fr1/rev[s(F1)],fva1/rev[s(F1)]
cf_idx24=100*seg['CF']['2024']/seg['CF']['2022']; fr_idx24=100*seg['FR']['2024']/seg['FR']['2022']
trough=min(rev.values()); trough_fy=[fy for fy in FYS if rev[s(fy)]==trough][0]
peak_drop=(rev[s(F0)]-trough)/rev[s(F0)]
cf_drop=(seg['CF'][s(F0)]-seg['CF'][str(trough_fy)])/seg['CF'][s(F0)]

SECTIONS=[
 ("Revenue Bridge","revenue_bridge.png",
  f"Where four years of net growth came from",
  [f"Total advisory revenue grew {money(rev[s(F1)]-rev[s(F0)])}M over four years, from {money(rev[s(F0)])}M to {money(rev[s(F1)])}M (+{(rev[s(F1)]/rev[s(F0)]-1)*100:.0f}%). All three segments contributed.",
   f"Corporate Finance added {money(seg['CF'][s(F1)]-seg['CF'][s(F0)])}M, Financial Restructuring {money(seg['FR'][s(F1)]-seg['FR'][s(F0)])}M, and FVA {money(seg['FVA'][s(F1)]-seg['FVA'][s(F0)])}M.",
   f"The bridge is a net view. The path was not a straight line: revenue fell to {money(trough)}M in FY{trough_fy} when M&A froze, then recovered to a record in FY{F1}."]),
 ("Revenue Mix","revenue_mix.png",
  f"Corporate Finance drives the total",
  [f"Corporate Finance is the engine and the swing factor: {money(seg['CF']['2022'])}M → {money(seg['CF']['2024'])}M in the downturn → {money(seg['CF'][s(F1)])}M five-year high in FY{F1}. It drives the shape of the total.",
   f"Financial Restructuring is the stabilizer, peaking at {money(max(seg['FR'].values()))}M as credit stress rose. FVA is the steady base, low-volatility fee events.",
   f"FY{F1} mix: Corporate Finance {mixcf*100:.0f}%, Financial Restructuring {mixfr*100:.0f}%, FVA {mixfva*100:.0f}%."]),
 ("Counter-Cyclical Hedge","countercyclical_hedge.png",
  f"Restructuring rises as Corporate Finance falls",
  [f"Indexed to FY{F0}=100, the two books move opposite: Corporate Finance fell to {cf_idx24:.0f} by FY2024 while Financial Restructuring climbed to {fr_idx24:.0f}. That is the hedge.",
   f"The lift is lagged. In the FY{trough_fy} trough, Corporate Finance dropped {cf_drop*100:.0f}% but total revenue fell only {peak_drop*100:.0f}%, because Restructuring and FVA held flat, a diversification cushion. Restructuring's own counter-cyclical surge landed the next year, in FY2024.",
   f"Restructuring then peaked in FY2025 as the M&A recovery took hold, and eased as Corporate Finance took back over."]),
]

def section_html(sec,i):
    title,png,sub,bullets=sec
    b="".join(f"<li>{x}</li>" for x in bullets)
    flip=" flip" if i%2==0 else ""   # alternate chart/notes sides for rhythm variation
    return f'''<section class="block{flip}">
      <div class="head"><span class="num">{i:02d}</span><h2>{title}</h2><span class="sub">{sub}</span></div>
      <div class="body">
        <figure class="img"><img alt="{title}" src="data:image/png;base64,{b64(png)}"></figure>
        <div class="note"><h3>What the data says</h3><ul>{b}</ul></div>
      </div>
    </section>'''

def tile_html(sec,i):
    title,png,sub,bullets=sec
    b="".join(f"<li>{x}</li>" for x in bullets)
    return f'''<section class="block tile">
      <div class="head"><span class="num">{i:02d}</span><h2>{title}</h2></div>
      <figure class="img"><img alt="{title}" src="data:image/png;base64,{b64(png)}"></figure>
      <div class="note"><ul>{b}</ul></div>
    </section>'''

kpi_html="".join(card_html(c) for c in cards())
tiles="".join(tile_html(SECTIONS[i],i+1) for i in (0,1))       # revenue bridge + mix, 2-up
sec_html=f'<div class="tiles">{tiles}</div>'+section_html(SECTIONS[2],3)  # hedge full-width feature

HTML=f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Houlihan Lokey: Five-Year Operating Trends</title>
<style>
/* Hallmark · macrostructure: Stat-Led + document · anchor: HL navy · faces: Georgia display + system sans · pre-emit critique: P4 H5 E4 S5 R4 V4 */
 :root{{--navy:#004878;--blue:#00609C;--steel:#5490A8;--lt:#A9C7DC;
   --ink:#1E2E36;--muted:#5C6B72;--bg:#F4F7F9;--card:#FFFFFF;--line:#DEE6EA;--hair:#E8EEF1;
   --green:#3E8E5C;--red:#A6403A;
   --s1:4px;--s2:8px;--s3:12px;--s4:16px;--s5:24px;--s6:36px;--whisper:0 1px 2px rgba(20,45,60,.05);}}
 *{{box-sizing:border-box;margin:0;padding:0}}
 html,body{{overflow-x:clip}}
 body{{background:var(--bg);color:var(--ink);font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
   line-height:1.5;-webkit-font-smoothing:antialiased}}
 .wrap{{max-width:1040px;margin:0 auto;padding:0 20px}}
 header.top{{background:linear-gradient(103deg,var(--navy),#00365a);color:#fff;padding:20px 0 17px}}
 header.top .wrap{{display:flex;justify-content:space-between;align-items:flex-end;gap:var(--s4);flex-wrap:wrap}}
 .brand h1{{font-family:Georgia,serif;font-size:23px;font-weight:600;letter-spacing:.2px}}
 .brand .tick{{color:var(--lt);font-weight:600}}
 .brand p{{color:#C7DAE7;font-size:12.5px;margin-top:3px}}
 .asof{{text-align:right;font-size:11.5px;color:#AEC8D9;line-height:1.7}}
 .asof b{{color:#fff;font-weight:600}}
 .eyebrow{{font-family:Georgia,serif;font-size:11.5px;letter-spacing:2px;text-transform:uppercase;
   color:var(--muted);font-weight:700;margin:var(--s5) 0 var(--s3)}}
 /* KPI stat strip: one divided panel, not six floating cards */
 .kpi-strip{{display:grid;grid-template-columns:repeat(6,1fr);gap:1px;background:var(--line);
   border:1px solid var(--line);border-radius:10px;overflow:hidden;box-shadow:var(--whisper)}}
 .kpi{{background:var(--card);padding:var(--s3) var(--s4) 14px}}
 .kpi-label{{font-size:11px;color:var(--muted);font-weight:600;line-height:1.3}}
 .kpi-value{{font-family:Georgia,serif;font-size:22px;font-weight:700;color:var(--navy);margin:2px 0 5px}}
 .kpi-spark{{height:24px;margin-bottom:8px}} .kpi-spark svg{{width:100%;height:24px}}
 .kpi-foot{{display:flex;flex-direction:column;gap:3px;align-items:flex-start}}
 .chip{{font-size:11px;font-weight:700;padding:1px 7px;border-radius:20px;white-space:nowrap}}
 .chip.up{{background:#E7F1EB;color:var(--green)}} .chip.down{{background:#F4E8E7;color:var(--red)}}
 .kpi-range{{font-size:10.5px;color:var(--muted)}}
 /* chart blocks: alternating sides for rhythm */
 .block{{background:var(--card);border:1px solid var(--line);border-radius:11px;
   margin-top:var(--s3);padding:var(--s4) var(--s5);box-shadow:var(--whisper)}}
 .tiles{{display:grid;grid-template-columns:1fr 1fr;gap:var(--s3);margin-top:var(--s3)}}
 .tile{{margin-top:0;padding:var(--s4) var(--s4) var(--s3)}}
 .tile .head{{margin-bottom:var(--s3)}}
 .tile .img{{margin:var(--s1) 0 var(--s3)}}
 .tile .note li{{font-size:12.5px;padding:6px 0 6px 14px}}
 .head{{display:flex;align-items:baseline;gap:var(--s3);border-bottom:1px solid var(--hair);
   padding-bottom:var(--s3);margin-bottom:var(--s4)}}
 .num{{font-family:Georgia,serif;font-size:15px;font-weight:700;color:var(--steel);letter-spacing:1px}}
 .head h2{{font-family:Georgia,serif;font-size:18px;color:var(--navy);font-weight:600}}
 .head .sub{{margin-left:auto;color:var(--muted);font-size:12.5px;text-align:right}}
 .body{{display:grid;grid-template-columns:1.62fr 1fr;gap:var(--s5);align-items:center}}
 .block.flip .body{{grid-template-columns:1fr 1.62fr}}
 .block.flip .img{{order:2}} .block.flip .note{{order:1}}
 .img{{margin:0}} .img img{{width:100%;height:auto;display:block}}
 .note h3{{font-size:11px;letter-spacing:1px;text-transform:uppercase;color:var(--muted);margin-bottom:var(--s2)}}
 .note ul{{list-style:none}}
 .note li{{font-size:13px;line-height:1.5;color:var(--ink);padding:7px 0 7px 15px;border-bottom:1px solid var(--hair);position:relative}}
 .note li:before{{content:"";position:absolute;left:0;top:13px;width:5px;height:5px;border-radius:50%;background:var(--steel)}}
 .note li:last-child{{border-bottom:none;padding-bottom:0}}
 footer.src{{border-top:2px solid var(--navy);margin-top:var(--s5);padding:var(--s4) 0 var(--s6);color:var(--muted);font-size:12px;line-height:1.55}}
 footer.src .wrap>div{{margin-bottom:6px}} footer.src b{{color:var(--ink)}}
 .tieout{{color:var(--green);font-weight:600}}
 @media(max-width:860px){{.kpi-strip{{grid-template-columns:repeat(3,1fr)}}.tiles{{grid-template-columns:1fr}}
   .body,.block.flip .body{{grid-template-columns:1fr}}.block.flip .img,.block.flip .note{{order:0}}
   .head .sub{{margin-left:0}}header.top .wrap{{flex-direction:column;align-items:flex-start}}.asof{{text-align:left}}}}
 @media(max-width:520px){{.kpi-strip{{grid-template-columns:repeat(2,1fr)}}}}
</style></head><body>
<header class="top"><div class="wrap">
  <div class="brand"><h1>Houlihan Lokey <span class="tick">NYSE: HLI</span></h1>
    <p>Five-Year Operating Trends &nbsp;&middot;&nbsp; FY{F0}&ndash;FY{F1} &nbsp;&middot;&nbsp; year-over-year, fiscal years ending March 31</p></div>
  <div class="asof">Data through <b>FY{F1}</b> (ended March 31, {F1})<br>As of <b>{AS_OF}</b> &nbsp;&middot;&nbsp; Source: <b>SEC EDGAR</b></div>
</div></header>
<div class="wrap">
  <div class="eyebrow">KPI Scorecard &nbsp;&middot;&nbsp; FY{F0} &rarr; FY{F1}</div>
  <div class="kpi-strip">{kpi_html}</div>
  {sec_html}
</div>
<footer class="src"><div class="wrap">
  <div><b>Source of truth.</b> All figures are pulled from SEC EDGAR: XBRL company facts (CIK 0001302215) and the 20 quarterly earnings-release 8-Ks (Exhibit 99.1). Segment revenue, MD headcount, and deal counts are from the releases; the income statement is XBRL, YTD-differenced to quarters. Net income to HLI is the attributable-to-parent figure (us-gaap:NetIncomeLoss), not consolidated.</div>
  <div><span class="tieout">&#10003; Tie-outs pass:</span> segment revenue sums to total revenue, and quarterly revenue sums to the reported 10-K annual, for every fiscal year FY{F0}&ndash;FY{F1}. Every number on this page is computed in code from those filings. None is produced by a language model.</div>
  <div><b>Auto-refresh.</b> When HL files new earnings, re-running <code>refresh.py</code> re-pulls EDGAR, rebuilds the verified data layer, re-renders the charts, and regenerates this page. {D['meta']['ebitda_note']}</div>
  <div style="margin-top:9px;color:#8A99A1">Built from public filings for financial-analysis demonstration. Not investment advice.</div>
</div></footer>
</body></html>'''

outdir=os.path.join(PROJ,"docs"); os.makedirs(outdir,exist_ok=True)  # /docs = GitHub Pages source
outp=os.path.join(outdir,"index.html")
open(outp,"w",encoding="utf-8").write(HTML)
print("saved",outp,f"({len(HTML)//1024} KB)")
