"""
render_charts.py, code-rendered charts, Houlihan Lokey palette, CW-advisor level polish.
Fully data-driven off dashboard_data.json (the verified SEC layer). Numbers never hand-typed.

Locked style: NO chart title, NO gridlines, NO y-axis title, legend below the x-axis,
NO decimals, legible data labels (zeros suppressed), non-neon HL colors,
GREEN increases / RED decreases / NAVY totals, REAL soft drop shadows, clean whitespace.
"""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import rcParams
import matplotlib.patheffects as pe
from matplotlib.patches import Patch
import numpy as np
from scipy.ndimage import gaussian_filter
import json, os

HL_NAVY="#004878"; HL_BLUE="#00609C"; HL_STEEL="#5490A8"; HL_LT="#A9C7DC"
GREEN="#3E8E5C"; RED="#A6403A"; HL_GREY="#5A6B72"; INK="#22333B"
rcParams.update({"font.family":"DejaVu Sans","font.size":11,"text.color":INK,
                 "axes.edgecolor":"#C9D2D8","axes.labelcolor":INK,"xtick.color":INK,"ytick.color":INK})
PROJ=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTDIR=os.path.join(PROJ,"charts"); os.makedirs(OUTDIR,exist_ok=True)
D=json.load(open(os.path.join(PROJ,"dashboard_data.json"),encoding="utf-8"))
FYS=D["meta"]["fys"]; SEG=D["segment_revenue"]
def s(fy): return str(fy)
def _white(): return [pe.withStroke(linewidth=2.4,foreground="white")]

# ---- real soft drop shadow (matplotlib agg_filter + gaussian blur) ----
class _Base:
    def get_pad(self,dpi): return 0
    def __call__(self,im,dpi):
        pad=self.get_pad(dpi); src=np.pad(im,[(pad,pad),(pad,pad),(0,0)],"constant")
        return self.process(src,dpi),-pad,-pad
class DropShadow(_Base):
    def __init__(self,sigma=5,alpha=0.55,offset=(6,7),color=(0.13,0.15,0.17)):
        self.sigma=sigma; self.alpha=alpha; self.offset=offset; self.color=color
    def get_pad(self,dpi): return int((self.sigma*3+max(self.offset))/72*dpi)
    def process(self,src,dpi):
        a=gaussian_filter(src[:,:,-1]*self.alpha,self.sigma/72*dpi)
        ox=int(self.offset[0]/72*dpi); oy=int(self.offset[1]/72*dpi)
        a=np.roll(np.roll(a,ox,axis=1),oy,axis=0)
        tgt=np.zeros_like(src)
        for i,c in enumerate(self.color): tgt[:,:,i]=c
        tgt[:,:,3]=a; return tgt

def _clean(ax):
    ax.spines[["top","right"]].set_visible(False); ax.grid(False); ax.tick_params(length=0)
def _legend_below(ax,handles,n):
    ax.legend(handles=handles,loc="upper center",bbox_to_anchor=(0.5,-0.09),ncol=n,frameon=False,fontsize=10)
def _shadow_full(ax,x,heights,bottoms=None,width=0.62):
    """Shadow layer that matches each bar's real geometry (bottom+height), so floating
    waterfall bars cast a shadow only behind the floating segment, not down to zero."""
    if bottoms is None: bottoms=[0]*len(list(x))
    sh=ax.bar(x,heights,bottom=bottoms,color="black",width=width,zorder=2)
    for b in sh: b.set_agg_filter(DropShadow())

# ============================ 1) REVENUE BRIDGE ============================
def revenue_bridge(out):
    start=SEG["CF"][s(FYS[0])]+SEG["FR"][s(FYS[0])]+SEG["FVA"][s(FYS[0])]
    deltas=[SEG[k][s(FYS[-1])]-SEG[k][s(FYS[0])] for k in ("CF","FR","FVA")]
    labels=["Corporate\nFinance","Financial\nRestructuring","Financial &\nValuation Advisory"]
    end=start+sum(deltas); cats=[f"FY{FYS[0]}"]+labels+[f"FY{FYS[-1]}"]
    bottoms=[0]; heights=[start]; colors=[HL_NAVY]; texts=[start]; run=start; tops=[start]; cum=[start]
    for d in deltas:
        bottoms.append(min(run,run+d)); heights.append(abs(d)); colors.append(GREEN if d>=0 else RED)
        texts.append(d); run+=d; tops.append(run); cum.append(run)
    bottoms.append(0); heights.append(end); colors.append(HL_NAVY); texts.append(end)
    x=list(range(len(cats)))
    fig,ax=plt.subplots(figsize=(8.8,4.7),dpi=170)
    _shadow_full(ax,x,heights,bottoms)
    ax.bar(x,heights,bottom=bottoms,color=colors,width=0.62,zorder=3)
    for i in range(len(cats)-1):
        ax.plot([i+0.31,i+1-0.31],[cum[i],cum[i]],color="#9AA7AE",lw=1,ls=(0,(3,3)),zorder=2.6)
    for i,(b,h,t) in enumerate(zip(bottoms,heights,texts)):
        lbl=(f"${t:,.0f}" if i in (0,len(cats)-1) else ("+" if t>=0 else "−")+f"{abs(t):,.0f}")
        ax.annotate(lbl,(i,b+h),xytext=(0,8),textcoords="offset points",ha="center",va="bottom",
                    fontsize=11.5,fontweight="bold",
                    color=(INK if i in (0,len(cats)-1) else (GREEN if t>=0 else RED)),zorder=5)
    ax.set_xticks(x); ax.set_xticklabels(cats,fontsize=10); ax.set_ylim(0,max(tops+[end])*1.15)
    ax.yaxis.set_major_formatter(lambda v,_:f"${v:,.0f}"); _clean(ax)
    _legend_below(ax,[Patch(color=HL_NAVY,label="Total"),Patch(color=GREEN,label="Increase"),Patch(color=RED,label="Decrease")],3)
    fig.savefig(out,bbox_inches="tight",facecolor="white",pad_inches=0.28); plt.close(fig); print("saved",os.path.basename(out))

# ============================ 2) REVENUE MIX (stacked $) ============================
def revenue_mix(out):
    cf=[SEG["CF"][s(fy)] for fy in FYS]; fr=[SEG["FR"][s(fy)] for fy in FYS]; fva=[SEG["FVA"][s(fy)] for fy in FYS]
    tot=[a+b+c for a,b,c in zip(cf,fr,fva)]; x=list(range(len(FYS)))
    fig,ax=plt.subplots(figsize=(8.8,4.7),dpi=170)
    _shadow_full(ax,x,tot,width=0.6)
    ax.bar(x,cf,width=0.6,color=HL_NAVY,zorder=3)
    ax.bar(x,fr,bottom=cf,width=0.6,color=HL_BLUE,zorder=3)
    ax.bar(x,fva,bottom=[a+b for a,b in zip(cf,fr)],width=0.6,color=HL_STEEL,zorder=3)
    for i in x:
        for val,base in [(cf[i],0),(fr[i],cf[i]),(fva[i],cf[i]+fr[i])]:
            ax.annotate(f"{val:,.0f}",(i,base+val/2),ha="center",va="center",color="white",
                        fontsize=10,fontweight="bold",zorder=5)
        ax.annotate(f"${tot[i]:,.0f}",(i,tot[i]),xytext=(0,8),textcoords="offset points",
                    ha="center",va="bottom",fontsize=11.5,fontweight="bold",color=INK,zorder=5)
    ax.set_xticks(x); ax.set_xticklabels([f"FY{fy}" for fy in FYS],fontsize=10)
    ax.set_ylim(0,max(tot)*1.15); ax.yaxis.set_major_formatter(lambda v,_:f"${v:,.0f}"); _clean(ax)
    _legend_below(ax,[Patch(color=HL_NAVY,label="Corporate Finance"),Patch(color=HL_BLUE,label="Financial Restructuring"),
                      Patch(color=HL_STEEL,label="Financial & Valuation Advisory")],3)
    fig.savefig(out,bbox_inches="tight",facecolor="white",pad_inches=0.28); plt.close(fig); print("saved",os.path.basename(out))

# ============================ 3) COUNTER-CYCLICAL HEDGE (indexed) ============================
def countercyclical_hedge(out):
    cf=[SEG["CF"][s(fy)] for fy in FYS]; fr=[SEG["FR"][s(fy)] for fy in FYS]
    icf=[100*v/cf[0] for v in cf]; ifr=[100*v/fr[0] for v in fr]; x=list(range(len(FYS)))
    fig,ax=plt.subplots(figsize=(8.8,4.7),dpi=170)
    # highlight the FY22->FY24 M&A downturn where the hedge engages
    ax.axvspan(-0.35,2,color="#EEF2F5",zorder=0)
    ax.annotate("M&A downturn",(0.9,ax.get_ylim()[1]),xytext=(0.9,145),ha="center",va="top",
                fontsize=9.5,color=HL_GREY,style="italic",zorder=1)
    ax.axhline(100,color="#C9D2D8",lw=1,ls=(0,(4,4)),zorder=1)
    def line(y,color,marker,label):
        ax.plot(x,y,color=color,lw=2.8,marker=marker,ms=8,mfc=color,mec="white",mew=1.4,zorder=4,label=label,
                path_effects=[pe.SimpleLineShadow(offset=(1.5,-1.5),alpha=0.18),pe.Normal()])
    line(icf,HL_NAVY,"o","Corporate Finance"); line(ifr,HL_STEEL,"s","Financial Restructuring")
    for xi,yv in zip(x,icf):
        ax.annotate(f"{yv:,.0f}",(xi,yv),xytext=(0,-16),textcoords="offset points",ha="center",
                    fontsize=10,fontweight="bold",color=HL_NAVY,zorder=5,path_effects=_white())
    for xi,yv in zip(x,ifr):
        ax.annotate(f"{yv:,.0f}",(xi,yv),xytext=(0,11),textcoords="offset points",ha="center",
                    fontsize=10,fontweight="bold",color=HL_STEEL,zorder=5,path_effects=_white())
    ax.set_xticks(x); ax.set_xticklabels([f"FY{fy}" for fy in FYS],fontsize=10)
    ax.set_xlim(-0.4,len(FYS)-0.6); ax.set_ylim(55,155)
    ax.yaxis.set_major_formatter(lambda v,_:f"{v:,.0f}"); _clean(ax)
    _legend_below(ax,[plt.Line2D([],[],color=HL_NAVY,lw=2.8,marker="o",ms=8,mec="white",label="Corporate Finance"),
                      plt.Line2D([],[],color=HL_STEEL,lw=2.8,marker="s",ms=8,mec="white",label="Financial Restructuring")],2)
    fig.savefig(out,bbox_inches="tight",facecolor="white",pad_inches=0.28); plt.close(fig); print("saved",os.path.basename(out))

if __name__=="__main__":
    revenue_bridge(os.path.join(OUTDIR,"revenue_bridge.png"))
    revenue_mix(os.path.join(OUTDIR,"revenue_mix.png"))
    countercyclical_hedge(os.path.join(OUTDIR,"countercyclical_hedge.png"))
