import os; os.chdir(os.path.dirname(os.path.abspath(__file__)))
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

def box(ax,x,y,w,h,title,body,fc,ec="#1f2937"):
    ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.01,rounding_size=0.015",fc=fc,ec=ec,lw=1.2))
    ax.text(x+0.012,y+h-0.018,title,fontsize=10.5,weight="bold",va="top",color="#111827")
    ax.text(x+0.012,y+h-0.058,body,fontsize=8.3,va="top",color="#1f2937",linespacing=1.35)

# Figure 1: methodology
stages=[("1. Problem grounding","Hackathon brief, CAG audit,\nHDI 2022-23, DVDMS field\nliterature"),
("2. Literature survey","16-study structured table,\n5 research threads"),
("3. Requirements","Functional + non-functional;\nmeds, beds, staff"),
("4. Eval protocol (frozen 1st)","Held-out splits, sealed\ngenerator, metrics, baselines\ncommitted before modelling"),
("5. Data acquisition","HMIS, HFR, IDSP, IMD,\nNLEM + sealed synthetic\nledger generator"),
("6. Module design","5 layers mapped to\nGoogle Cloud services"),
("7. Implementation","Capture, extraction,\nforecasting, solver, agent,\nfederation"),
("8. Integration","End-to-end loop:\nvoice/photo to transfer order"),
("9. Held-out evaluation","Test window & held-out\ndistrict/state touched once;\nreal vs synthetic reported apart")]
fig,ax=plt.subplots(figsize=(13,6.2)); ax.set_xlim(0,1); ax.set_ylim(0,1); ax.axis("off")
w,h=0.29,0.25
for i,(t,b) in enumerate(stages):
    r,c=divmod(i,3); c=c if r%2==0 else 2-c
    x=0.03+c*0.33; y=0.70-r*0.33
    fc="#fde68a" if i in (3,8) else "#dbeafe"
    box(ax,x,y,w,h,t,b,fc)
    if i<8:
        r2,c2=divmod(i+1,3); c2=c2 if r2%2==0 else 2-c2
        if r2==r:
            x0=x+w if c2>c else x; x1=0.03+c2*0.33+(0 if c2>c else w)
            ax.annotate("",xy=(x1,y+h/2),xytext=(x0,y+h/2),arrowprops=dict(arrowstyle="-|>",lw=1.6))
        else:
            ax.annotate("",xy=(x+w/2,y-0.08),xytext=(x+w/2,y),arrowprops=dict(arrowstyle="-|>",lw=1.6))
ax.text(0.5,0.985,"AushadhiNet design methodology (highlighted: evaluation protocol fixed before any model is trained)",ha="center",fontsize=11.5,weight="bold")
fig.savefig("fig1_methodology.png",dpi=200,bbox_inches="tight"); plt.close(fig)

# Figure 2: architecture
layers=[
("Module 1 — Interface & Capture","WhatsApp Business (voice note / register photo / geo-tagged staff check-in / bed census)  ·  IVR via Dialogflow CX telephony for feature phones\nOfficer PWA on Firebase Hosting (offline-first)  ·  Map dashboard on Google Maps Platform  ·  Captures: MEDICINES · BEDS · STAFF ATTENDANCE","#dbeafe"),
("Module 2 — Ingestion & Extraction","Chirp 2 (Cloud Speech-to-Text v2) multilingual ASR  ·  Gemini multimodal structured extraction with per-field confidence  ·  Cloud Translation\nVertex AI Vector Search: NLEM drug-name normalisation  ·  Confidence gate: one-tap confirmation  ·  Pub/Sub → Firestore (live) + BigQuery (history)","#e0e7ff"),
("Module 3 — Intelligence","Hierarchical forecasting: TimesFM + LightGBM (Vertex AI) + Croston-SBA for intermittent drugs, BigQuery ML ARIMA_PLUS baseline\nBed-occupancy & staff-gap forecasts  ·  Anomaly detection  ·  OR-Tools min-cost-flow redistribution (drugs + staff deputation + patient referral)\nGemini function-calling officer agent (Agent Development Kit)","#dcfce7"),
("Module 4 — Federation","One GCP project per state (data plane; raw rows never leave)  ·  Flower federated server on Vertex AI (model plane)\nFedProx aggregation for non-IID states  ·  DP-SGD update clipping + noise  ·  Secure aggregation\nPublished ingestion contract for DVDMS / state HMIS adapters","#fef3c7"),
("Module 5 — Action & Delivery","Signed transfer orders (Cloud KMS) with batch manifest  ·  Local-language WhatsApp + Text-to-Speech voice alerts\nGoogle Maps Routes API route plans  ·  Escalation ladder (Cloud Workflows + Scheduler): facility → block → district → state\nPublic aggregate transparency view (Looker Studio)","#fee2e2")]
fig,ax=plt.subplots(figsize=(14,8.4)); ax.set_xlim(0,1); ax.set_ylim(0,1); ax.axis("off")
for i,(t,b,fc) in enumerate(layers):
    y=0.80-i*0.175
    box(ax,0.03,y,0.80,0.145,t,b,fc)
    if i<4: ax.annotate("",xy=(0.43,y-0.028),xytext=(0.43,y),arrowprops=dict(arrowstyle="-|>",lw=1.6))
ax.add_patch(FancyBboxPatch((0.855,0.10),0.12,0.845,boxstyle="round,pad=0.01",fc="#f3f4f6",ec="#1f2937"))
ax.text(0.915,0.93,"Cross-cutting",ha="center",va="top",fontsize=10,weight="bold")
ax.text(0.915,0.88,"Cloud Run\nIAM + VPC-SC\nCloud Audit Logs\nABDM HFR IDs\nFHIR R4\nexport\nSecret Manager\nCloud\nMonitoring\nCI/CD:\nCloud Build",ha="center",va="top",fontsize=8.5,linespacing=1.6)
ax.annotate("approvals & alerts flow upward",xy=(0.015,0.94),xytext=(0.015,0.12),arrowprops=dict(arrowstyle="-|>",lw=1.2,color="#6b7280"),rotation=90,fontsize=8,color="#6b7280",va="bottom",ha="center")
ax.text(0.43,0.985,"AushadhiNet layered architecture on Google Cloud",ha="center",fontsize=12,weight="bold")
fig.savefig("fig2_architecture.png",dpi=200,bbox_inches="tight"); plt.close(fig)
