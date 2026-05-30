# ════════════════════════════════════════════════════════════════
#  FieldPerform — MTN FLM Performance Platform  v6.1
#  South Region · Modules complets avec Barème & Classement
# ════════════════════════════════════════════════════════════════
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, date, timedelta
import calendar
import anthropic

from supabase_manager import (
    fetch_techs, add_tech, delete_tech, update_tech,
    fetch_snags_manager, fetch_snags_6months,
    insert_snag_manager, update_snag_manager, delete_snag_manager,
    fetch_rca, insert_rca, update_rca, delete_rca,
    fetch_asset, insert_asset, update_asset, delete_asset,
    fetch_blockers, insert_blocker, update_blocker, delete_blocker,
)
from styles_manager import (
    GLOBAL_CSS, F, MONTHS_FR, CATEGORIES, SUB_SCORES,
    ACTION_FACTOR, ACTION_LABEL, ACTION_COLOR,
    calc_pts, obj_for_month, obj_color, obj_bar_html,
    kpi_card, section_label, badge,
    status_badge_rca, status_badge_snag,
)

# ── Config ──────────────────────────────────────────────────────
st.set_page_config(
    page_title="FieldPerform · MTN FLM",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

now   = datetime.now()
CUR_Y = now.year
CUR_M = now.month
TODAY = date.today()

# ════════════════ SIDEBAR ════════════════
with st.sidebar:
    st.html(f"""<div style="display:flex;align-items:center;gap:12px;padding:16px 0 12px;">
        <div style="background:#FFD200;width:44px;height:44px;border-radius:10px;
            display:flex;align-items:center;justify-content:center;font-weight:800;
            font-size:11px;color:#111827;{F}">MTN</div>
        <div>
            <div style="font-size:16px;font-weight:800;color:#111827;letter-spacing:-.01em;{F}">FieldPerform</div>
            <div style="font-size:10px;color:#9CA3AF;letter-spacing:.06em;{F}">SOUTH REGION · v6.1</div>
        </div>
    </div><div style="height:1px;background:#E5E7EB;margin-bottom:16px;"></div>""")

    st.html(f'<div style="font-size:10px;color:#9CA3AF;font-weight:700;letter-spacing:.08em;margin-bottom:8px;{F}">PÉRIODE</div>')
    col_m, col_y = st.columns(2)
    with col_m:
        sel_m = st.selectbox("Mois", range(1,13),
                             format_func=lambda x: MONTHS_FR[x-1],
                             index=CUR_M-1, key="sel_m",
                             label_visibility="collapsed")
    with col_y:
        sel_y = st.selectbox("Année", [2024,2025,2026,2027],
                             index=[2024,2025,2026,2027].index(CUR_Y),
                             key="sel_y", label_visibility="collapsed")

    period_label      = f"{MONTHS_FR[sel_m-1]} {sel_y}"
    last_day          = calendar.monthrange(sel_y, sel_m)[1]
    obj_pts           = obj_for_month(sel_m)
    is_current_period = (sel_y == CUR_Y and sel_m == CUR_M)

    if is_current_period:
        days_left = max(0, last_day - now.day + 1)
        st.html(f"""<div style="background:#FFFBEB;border:1px solid #FDE68A;border-radius:8px;
            padding:7px 12px;font-size:11px;color:#92400E;font-weight:700;text-align:center;
            margin:8px 0;{F}">⏳ J-{days_left} fin du mois</div>""")

    st.html(f"""<div style="background:#F0FDF4;border:1px solid #BBF7D0;border-radius:8px;
        padding:8px 12px;margin:8px 0;">
        <div style="font-size:10px;color:#166534;font-weight:700;{F}">🎯 OBJECTIF PROGRESSIF</div>
        <div style="font-size:20px;font-weight:800;color:#166534;{F}">{obj_pts} pts</div>
        <div style="font-size:10px;color:#9CA3AF;{F}">+10%/mois · Base 100 jan.</div>
    </div>""")

    st.html(f'<div style="height:1px;background:#E5E7EB;margin:12px 0;"></div>')
    st.html(f'<div style="font-size:10px;color:#9CA3AF;text-align:center;{F}">Supabase PostgreSQL · FieldPerform</div>')

# ════════════════ CHARGEMENT DONNÉES ════════════════
@st.cache_data(ttl=30, show_spinner=False)
def load_techs_cached():
    return fetch_techs()

@st.cache_data(ttl=30, show_spinner=False)
def load_snags_cached(y, m):
    return fetch_snags_manager(y, m)

@st.cache_data(ttl=30, show_spinner=False)
def load_rca_cached(y, m):
    return fetch_rca(y, m)

@st.cache_data(ttl=30, show_spinner=False)
def load_asset_cached(y, m):
    return fetch_asset(y, m)

@st.cache_data(ttl=30, show_spinner=False)
def load_blockers_cached(y, m):
    return fetch_blockers(y, m)

techs_list = load_techs_cached()
techs_noms = [t["nom"] for t in techs_list]
snags_data = load_snags_cached(sel_y, sel_m)
rca_data   = load_rca_cached(sel_y, sel_m)
asset_data = load_asset_cached(sel_y, sel_m)
blockers_d = load_blockers_cached(sel_y, sel_m)

# ── Calculs globaux ──────────────────────────────────────────────
def build_leaderboard(snags):
    if not snags:
        return []
    df = pd.DataFrame(snags)
    lb = []
    for tech in df["technicien"].unique():
        td      = df[df["technicien"] == tech]
        total   = round(td["points"].sum(), 1)
        n       = len(td)
        closed  = int(td["action"].isin(["closed","both"]).sum())
        raised  = int(td["action"].eq("raised").sum())
        bonus   = 5 if n >= 8 else 3 if n >= 5 else 0
        ml_pct  = round(min(100,(closed+raised*0.5)/n*100+bonus),1) if n else 0
        txn     = int(td["categorie"].isin(["TXN","IPRAN","MW_FADING","MW_EQUIPMENT"]).sum())
        energy  = int(td["categorie"].isin(["DG","Battery","Rectifier","ATS","ENERGY_OTHER"]).sum())
        ran_c   = int(td["categorie"].isin(["RAN","ANTENNA","FEEDER","BTS_HW","BTS_SW"]).sum())
        lb.append({"name":tech,"total":total,"n":n,"closed":closed,
                   "raised":raised,"ml_pct":ml_pct,
                   "txn_snags":txn,"energy_snags":energy,"ran_snags":ran_c})
    lb.sort(key=lambda x: -x["total"])
    for i, t in enumerate(lb):
        t["rank"] = i+1
        pct = round(t["total"]/obj_pts*100,1) if obj_pts else 0
        t["obj_pct"] = pct
        if pct >= 80:   t["cluster"] = {"label":"Elite","color":"#D97706","bg":"#FFFBEB","border":"#FDE68A"}
        elif pct >= 60: t["cluster"] = {"label":"Performant","color":"#6366F1","bg":"#EEF2FF","border":"#C7D2FE"}
        elif pct >= 40: t["cluster"] = {"label":"En progression","color":"#10B981","bg":"#ECFDF5","border":"#6EE7B7"}
        else:           t["cluster"] = {"label":"Actif","color":"#9CA3AF","bg":"#F9FAFB","border":"#E5E7EB"}
    return lb

lb        = build_leaderboard(snags_data)
total_pts = sum(t["total"] for t in lb)
mid_month = (now.day >= 15) if is_current_period else True
alert_set = {t["name"] for t in lb if t["ml_pct"] < 30 and mid_month}
drop_set  = set()

for t in lb:
    hist = fetch_snags_6months(t["name"])
    if len(hist) >= 2:
        hdf = pd.DataFrame(hist)
        hdf["ym"] = hdf["annee"]*100 + hdf["mois"]
        monthly = hdf.groupby("ym")["points"].sum().sort_index()
        vals = list(monthly.values)
        if len(vals) >= 2:
            last, prev = vals[-1], vals[-2]
            if prev > 0 and (prev - last) / prev >= 0.30:
                drop_set.add(t["name"])

overdue_snags = []
if snags_data:
    for s in snags_data:
        if s.get("action") in ["raised","both"] and not s.get("date_ferme"):
            d0   = date.fromisoformat(str(s["date_snag"]))
            diff = (TODAY - d0).days
            if diff > 7:
                overdue_snags.append({**s, "days_open": diff})

rca_alerts = 0
for r in rca_data:
    if not r.get("date_rca"):
        d0  = datetime.fromisoformat(str(r["date_incident"]).replace("Z",""))
        hrs = (datetime.now() - d0).total_seconds() / 3600
        if hrs >= 48:
            rca_alerts += 1

asset_day     = 20
asset_dline   = date(sel_y, sel_m, asset_day)
days_to_asset = (asset_dline - TODAY).days
pending_asset = sum(1 for a in asset_data if not a.get("soumis"))

# ════════════════ HEADER ════════════════
n_alerts_total = len(alert_set) + rca_alerts + len(overdue_snags)
alert_color    = "#DC2626" if n_alerts_total > 0 else "#10B981"

st.html(f"""<div style="background:linear-gradient(135deg,#111827 0%,#1F2937 100%);
    border-radius:14px;padding:18px 24px;margin-bottom:14px;">
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;">
        <div>
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">
                <span style="background:#FFD200;color:#111827;font-size:12px;font-weight:800;
                    padding:3px 10px;border-radius:6px;{F}">MTN</span>
                <span style="font-size:24px;font-weight:800;color:#FFFFFF;letter-spacing:-.02em;{F}">FieldPerform</span>
                <span style="font-size:11px;color:#6B7280;background:#374151;
                    padding:3px 8px;border-radius:6px;{F}">v6.1</span>
            </div>
            <div style="font-size:12px;color:#9CA3AF;{F}">
                {period_label} · South Region · Objectif progressif : {obj_pts} pts
            </div>
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
            <div style="background:{alert_color}22;border:1px solid {alert_color}55;
                border-radius:8px;padding:6px 14px;font-size:11px;
                color:{alert_color};font-weight:700;{F}">
                {'⚠ ' if n_alerts_total else '✓ '}{n_alerts_total} alerte{'s' if n_alerts_total!=1 else ''}
            </div>
            <div style="background:#374151;border-radius:8px;padding:6px 14px;
                font-size:11px;color:#D1D5DB;font-weight:600;{F}">
                {len(lb)} tech · {round(total_pts,1)} pts
            </div>
        </div>
    </div>
</div>""")

# ════════════════ ONGLETS ════════════════
(tab_overview, tab_class, tab_bareme, tab_techs, tab_snags,
 tab_mgmt, tab_blockers, tab_trend, tab_ai) = st.tabs([
    "📊 Vue globale",
    "🏆 Classement",
    "📋 Barème",
    "👷 Techniciens",
    "🔧 Snags",
    "📄 RCA & ASSET",
    "🚧 Blocages",
    "📈 Tendances 6 mois",
    "🤖 Analyse IA",
])

# ══════════════════════════════════════════════════════════════════
#  TAB 1 — VUE GLOBALE
# ══════════════════════════════════════════════════════════════════
with tab_overview:
    c1,c2,c3,c4,c5 = st.columns(5)
    c1.html(kpi_card("Techniciens actifs", str(len(lb)), f"{len(techs_list)} enregistrés","#6366F1"))
    c2.html(kpi_card("Alertes fermeture", str(len(alert_set)),
                     "taux <30% mi-mois","#EF4444" if alert_set else "#10B981"))
    c3.html(kpi_card("Snags en retard", str(len(overdue_snags)),
                     ">7 jours sans fermeture","#EF4444" if overdue_snags else "#10B981"))
    c4.html(kpi_card("RCA en attente", str(rca_alerts),
                     "≥48h sans livraison","#EF4444" if rca_alerts else "#10B981"))
    c5.html(kpi_card("ASSET deadline",
                     f"J-{days_to_asset}" if days_to_asset >= 0 else "Dépassé",
                     f"{pending_asset} non soumis",
                     "#EF4444" if days_to_asset <= 5 else "#F59E0B"))

    team_pct = round(total_pts/obj_pts*100,1) if obj_pts else 0
    tc = obj_color(team_pct)
    st.html(f"""<div style="background:#FFFFFF;border:1px solid #E5E7EB;border-radius:10px;
        padding:14px 18px;margin:12px 0;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
            <div style="font-size:10px;font-weight:700;color:#6B7280;letter-spacing:.07em;
                text-transform:uppercase;{F}">🎯 PROGRESSION ÉQUIPE — {period_label}</div>
            <div style="font-size:18px;font-weight:800;color:{tc};{F}">{team_pct}%</div>
        </div>
        {obj_bar_html(team_pct, 12)}
        <div style="display:flex;justify-content:space-between;margin-top:5px;">
            <div style="font-size:11px;color:#9CA3AF;{F}">{round(total_pts,1)} pts cumulés</div>
            <div style="font-size:11px;color:#9CA3AF;{F}">Objectif : {obj_pts} pts</div>
        </div>
    </div>""")

    if lb:
        st.html(section_label("PROGRESSION INDIVIDUELLE"))
        for t in lb:
            t_pct   = t["obj_pct"]
            t_col   = obj_color(t_pct)
            is_alrt = t["name"] in alert_set
            is_drop = t["name"] in drop_set
            no_txn  = t["txn_snags"] == 0
            bdr     = "border:1.5px solid #FECACA;" if is_alrt else "border:1px solid #E5E7EB;"
            bg      = "background:#FFF5F5;" if is_alrt else "background:#FFFFFF;"
            medal   = "🥇" if t["rank"]==1 else "🥈" if t["rank"]==2 else "🥉" if t["rank"]==3 else f"#{t['rank']}"
            tags = ""
            if is_alrt: tags += f"<span style='background:#FEE2E2;color:#DC2626;font-size:9px;font-weight:700;border-radius:4px;padding:2px 6px;{F}'>⚠ Alerte</span>&nbsp;"
            if is_drop: tags += f"<span style='background:#FEF3C7;color:#92400E;font-size:9px;font-weight:700;border-radius:4px;padding:2px 6px;{F}'>📉 Chute</span>&nbsp;"
            if no_txn:  tags += f"<span style='background:#EEF2FF;color:#3730A3;font-size:9px;font-weight:700;border-radius:4px;padding:2px 6px;{F}'>0 TXN</span>&nbsp;"
            cl_ = t["cluster"]
            st.html(f"""<div style="{bg}{bdr}border-radius:10px;padding:10px 14px;margin-bottom:6px;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                    <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
                        <span style="font-size:13px;font-weight:700;
                            color:{'#DC2626' if is_alrt else '#111827'};{F}">{medal} {t['name']}</span>
                        {tags}
                        <span style="background:{cl_['bg']};color:{cl_['color']};border:1px solid {cl_['border']};
                            font-size:9px;font-weight:700;border-radius:20px;padding:2px 7px;{F}">{cl_['label']}</span>
                    </div>
                    <div style="display:flex;align-items:center;gap:14px;">
                        <span style="font-size:11px;color:#9CA3AF;{F}">{t['total']} / {obj_pts} pts</span>
                        <span style="font-size:15px;font-weight:800;color:{t_col};{F}">{t_pct}%</span>
                    </div>
                </div>
                {obj_bar_html(t_pct, 8)}
                <div style="font-size:10px;color:#9CA3AF;margin-top:4px;{F}">
                    {t['n']} snags · {t['closed']} fermés · {t['ml_pct']}% fermeture
                    · TXN:{t['txn_snags']} · Énergie:{t['energy_snags']} · RAN:{t['ran_snags']}
                </div>
            </div>""")

    if lb:
        cl, cr = st.columns([3,2])
        with cl:
            st.html(section_label("POINTS PAR TECHNICIEN"))
            rank_colors = {1:"#FFD200",2:"#C0C0C0",3:"#CD7F32"}
            bar_colors  = [rank_colors.get(t["rank"],"#6366F1") for t in lb]
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=[t["total"] for t in lb],
                y=[f"{'🥇' if t['rank']==1 else '🥈' if t['rank']==2 else '🥉' if t['rank']==3 else str(t['rank'])+' '} {t['name']}" for t in lb],
                orientation="h",
                marker=dict(color=bar_colors, cornerradius=5),
                text=[f"  {t['total']} pts" for t in lb],
                textposition="inside", insidetextanchor="end",
                textfont=dict(size=11, color="#1F2937", family="Plus Jakarta Sans", weight="bold"),
            ))
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#FAFAFA",
                height=max(280, len(lb)*50), margin=dict(l=10,r=60,t=6,b=6),
                xaxis=dict(gridcolor="#F1F5F9", tickfont=dict(size=10,family="Plus Jakarta Sans")),
                yaxis=dict(gridcolor="rgba(0,0,0,0)",
                           tickfont=dict(size=11,family="Plus Jakarta Sans",weight="bold"),
                           autorange="reversed"),
                showlegend=False, bargap=0.3,
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

        with cr:
            st.html(section_label("TOP CATÉGORIES"))
            if snags_data:
                df_s = pd.DataFrame(snags_data)
                cp   = df_s.groupby("categorie")["points"].sum().sort_values(ascending=False).head(8)
                mx   = cp.max() or 1
                bcs  = ["#FFD200","#6366F1","#10B981","#F59E0B","#EC4899","#8B5CF6","#14B8A6","#EF4444"]
                for idx, (cat, pts) in enumerate(cp.items()):
                    c_       = bcs[idx % len(bcs)]
                    pct_bar  = pts/mx*100
                    st.html(f"""<div style="display:flex;align-items:center;gap:8px;margin-bottom:7px;">
                        <div style="font-size:11px;color:#374151;width:110px;flex-shrink:0;
                            overflow:hidden;text-overflow:ellipsis;white-space:nowrap;{F}">{cat}</div>
                        <div style="flex:1;background:#F1F5F9;border-radius:99px;height:7px;overflow:hidden;">
                            <div style="width:{pct_bar:.1f}%;height:100%;background:{c_};border-radius:99px;"></div></div>
                        <div style="font-size:11px;font-weight:700;color:{c_};width:30px;text-align:right;{F}">{pts:.0f}</div>
                    </div>""")


# ══════════════════════════════════════════════════════════════════
#  TAB 2 — CLASSEMENT COMPLET
# ══════════════════════════════════════════════════════════════════
with tab_class:
    if not lb:
        st.html(f"""<div style="background:#F9FAFB;border:2px dashed #E5E7EB;border-radius:12px;
            padding:50px;text-align:center;">
            <div style="font-size:13px;color:#9CA3AF;{F}">Aucune donnée pour {period_label}</div>
        </div>""")
    else:
        # Podium top 3
        if len(lb) >= 2:
            pod    = [lb[1], lb[0]] + ([lb[2]] if len(lb) > 2 else [])
            h_map  = {1:160, 2:120, 3:90}
            bg_map = {1:"#FFFBEB", 2:"#F9FAFB", 3:"#FEF3C7"}
            bc_map = {1:"#FFD200", 2:"#E5E7EB", 3:"#FDE68A"}
            tc_map = {1:"#D97706", 2:"#6B7280", 3:"#92400E"}
            mc_map = {1:"🥇", 2:"🥈", 3:"🥉"}
            pod_html = '<div style="display:flex;justify-content:center;align-items:flex-end;gap:16px;margin-bottom:28px;padding:20px;">'
            for t in pod:
                r = t["rank"]
                pod_html += f"""<div style="text-align:center;width:150px;">
                    <div style="font-size:28px;margin-bottom:4px;">{mc_map[r]}</div>
                    <div style="font-size:13px;font-weight:700;color:#111827;margin-bottom:2px;{F}">{t['name']}</div>
                    <div style="font-size:20px;font-weight:800;color:{tc_map[r]};margin-bottom:8px;{F}">{t['total']} pts</div>
                    <div style="font-size:11px;color:#9CA3AF;margin-bottom:8px;{F}">{t['obj_pct']}% objectif</div>
                    <div style="height:{h_map[r]}px;background:{bg_map[r]};border:2px solid {bc_map[r]};
                        border-radius:12px 12px 0 0;display:flex;align-items:flex-end;
                        justify-content:center;padding-bottom:12px;">
                        <div style="font-size:28px;font-weight:800;color:{tc_map[r]};{F}">{r}</div>
                    </div>
                </div>"""
            pod_html += '</div>'
            st.html(pod_html)

        st.html(section_label(f"CLASSEMENT COMPLET — {period_label}"))

        # En-tête tableau
        hdr_cls = st.columns([0.4,2,0.8,0.8,0.8,0.8,0.8,0.8,1.2])
        for col, h in zip(hdr_cls, ["#","TECHNICIEN","POINTS","% OBJ","SNAGS","FERMÉS","TXN","ÉNERGIE","CLUSTER"]):
            col.markdown(f"<div style='font-size:9px;font-weight:700;color:#9CA3AF;letter-spacing:.06em;text-transform:uppercase;padding:6px 0;{F}'>{h}</div>", unsafe_allow_html=True)

        for t in lb:
            is_alrt = t["name"] in alert_set
            is_drop = t["name"] in drop_set
            bg_row  = "#FFF5F5" if is_alrt else "#FAEEDA" if is_drop else "#FFFFFF"
            row     = st.columns([0.4,2,0.8,0.8,0.8,0.8,0.8,0.8,1.2])
            medal   = "🥇" if t["rank"]==1 else "🥈" if t["rank"]==2 else "🥉" if t["rank"]==3 else f"#{t['rank']}"
            t_col   = obj_color(t["obj_pct"])
            cl_     = t["cluster"]

            row[0].markdown(f"<div style='padding:10px 0;font-size:11px;color:#9CA3AF;background:{bg_row};{F}'>{medal}</div>", unsafe_allow_html=True)
            name_c = "#DC2626" if is_alrt else "#111827"
            name_s = f"{'⚠ ' if is_alrt else '📉 ' if is_drop else ''}{t['name']}"
            row[1].markdown(f"<div style='padding:10px 0;font-size:12px;font-weight:700;color:{name_c};background:{bg_row};{F}'>{name_s}</div>", unsafe_allow_html=True)
            row[2].markdown(f"<div style='padding:10px 0;font-size:14px;font-weight:800;color:#D97706;text-align:center;background:{bg_row};{F}'>{t['total']}</div>", unsafe_allow_html=True)
            row[3].markdown(f"<div style='padding:10px 0;font-size:13px;font-weight:700;color:{t_col};text-align:center;background:{bg_row};{F}'>{t['obj_pct']}%</div>", unsafe_allow_html=True)
            row[4].markdown(f"<div style='padding:10px 0;font-size:12px;color:#374151;text-align:center;background:{bg_row};{F}'>{t['n']}</div>", unsafe_allow_html=True)
            row[5].markdown(f"<div style='padding:10px 0;font-size:12px;color:#6366F1;font-weight:700;text-align:center;background:{bg_row};{F}'>{t['closed']}</div>", unsafe_allow_html=True)
            txn_c = "#EF4444" if t["txn_snags"]==0 else "#10B981"
            row[6].markdown(f"<div style='padding:10px 0;font-size:12px;font-weight:700;color:{txn_c};text-align:center;background:{bg_row};{F}'>{t['txn_snags']}</div>", unsafe_allow_html=True)
            row[7].markdown(f"<div style='padding:10px 0;font-size:12px;color:#374151;text-align:center;background:{bg_row};{F}'>{t['energy_snags']}</div>", unsafe_allow_html=True)
            row[8].html(f"<div style='padding:8px 0;background:{bg_row};'><span style='background:{cl_[\"bg\"]};color:{cl_[\"color\"]};border:1px solid {cl_[\"border\"]};font-size:10px;font-weight:700;border-radius:20px;padding:3px 9px;{F}'>{cl_['label']}</span></div>")
            st.html('<div style="height:1px;background:#F3F4F6;"></div>')

        # Score ML taux fermeture
        st.html('<div style="height:16px;"></div>')
        st.html(section_label("SCORE ML — TAUX DE FERMETURE"))
        ml_df = pd.DataFrame([{"Technicien":t["name"],"Score (%)":t["ml_pct"],"Cluster":t["cluster"]["label"]} for t in lb])
        fig_ml = px.bar(ml_df, x="Score (%)", y="Technicien", orientation="h", color="Cluster",
                        color_discrete_map={"Elite":"#F59E0B","Performant":"#6366F1",
                                            "En progression":"#10B981","Actif":"#9CA3AF"},
                        text="Score (%)")
        fig_ml.add_vline(x=30, line_dash="dash", line_color="#EF4444", line_width=1.5,
                         annotation_text="Seuil 30%",
                         annotation_font=dict(size=9, color="#EF4444", family="Plus Jakarta Sans"))
        fig_ml.update_traces(texttemplate="%{text}%", textposition="outside",
                             textfont=dict(size=11, family="Plus Jakarta Sans"),
                             marker_line_width=0)
        fig_ml.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#FAFAFA",
            height=max(260,len(lb)*44), margin=dict(l=0,r=60,t=8,b=8),
            xaxis=dict(gridcolor="#F3F4F6", range=[0,115], ticksuffix="%",
                       tickfont=dict(size=10,family="Plus Jakarta Sans")),
            yaxis=dict(gridcolor="rgba(0,0,0,0)",
                       tickfont=dict(size=12,family="Plus Jakarta Sans"),autorange="reversed"),
            legend=dict(font=dict(size=11,family="Plus Jakarta Sans"),bgcolor="rgba(0,0,0,0)"),
        )
        st.plotly_chart(fig_ml, use_container_width=True, config={"displayModeBar":False})

        # Légende clusters
        st.html(f"""<div style="background:#F9FAFB;border:1px solid #E5E7EB;border-radius:10px;
            padding:14px 18px;margin-top:8px;">
            <div style="font-size:10px;font-weight:700;color:#9CA3AF;letter-spacing:.08em;
                text-transform:uppercase;margin-bottom:10px;{F}">LÉGENDE CLUSTERS</div>
            <div style="display:flex;flex-wrap:wrap;gap:10px;">
                <span style="background:#FFFBEB;color:#D97706;border:1px solid #FDE68A;
                    font-size:11px;font-weight:700;border-radius:20px;padding:4px 12px;{F}">
                    🏆 Elite — ≥80% objectif</span>
                <span style="background:#EEF2FF;color:#6366F1;border:1px solid #C7D2FE;
                    font-size:11px;font-weight:700;border-radius:20px;padding:4px 12px;{F}">
                    ⭐ Performant — 60–80%</span>
                <span style="background:#ECFDF5;color:#10B981;border:1px solid #6EE7B7;
                    font-size:11px;font-weight:700;border-radius:20px;padding:4px 12px;{F}">
                    📈 En progression — 40–60%</span>
                <span style="background:#F9FAFB;color:#9CA3AF;border:1px solid #E5E7EB;
                    font-size:11px;font-weight:700;border-radius:20px;padding:4px 12px;{F}">
                    🔵 Actif — &lt;40%</span>
            </div>
            <div style="font-size:11px;color:#6B7280;margin-top:10px;line-height:1.8;{F}">
                <strong style="color:#374151;">Formule ML : </strong>
                Taux fermeture = (Fermés + R×0.5) / Total × 100 + Bonus volume<br>
                <strong style="color:#374151;">Bonus : </strong>+5% si ≥8 snags · +3% si ≥5 snags<br>
                <strong style="color:#374151;">Points : </strong>Base catégorie × Facteur action<br>
                <strong style="color:#EF4444;">⚠ Alerte rouge : </strong>Taux &lt;30% après le 15 du mois
            </div>
        </div>""")


# ══════════════════════════════════════════════════════════════════
#  TAB 3 — BARÈME COMPLET
# ══════════════════════════════════════════════════════════════════
with tab_bareme:
    # Règles de calcul
    st.html(section_label("RÈGLES DE CALCUL DES POINTS"))
    rc1, rc2, rc3 = st.columns(3)
    for col_, (act, val, sub, bg_, col_txt, bdr) in zip([rc1,rc2,rc3],[
        ("↑  Remonté","40%","Identification terrain","#FEF3C7","#92400E","#FDE68A"),
        ("✓  Fermé","60%","Résolution validée","#EEF2FF","#3730A3","#C7D2FE"),
        ("⟳  R+F","100%","Double valorisation","#ECFDF5","#065F46","#6EE7B7"),
    ]):
        col_.html(f"""<div style="background:{bg_};border:1.5px solid {bdr};border-radius:10px;
            padding:18px;text-align:center;margin-bottom:12px;">
            <div style="font-size:16px;font-weight:700;color:{col_txt};{F}">{act}</div>
            <div style="font-size:36px;font-weight:800;color:{col_txt};margin:8px 0;{F}">{val}</div>
            <div style="font-size:11px;color:{col_txt};opacity:.8;{F}">{sub}</div>
        </div>""")

    st.html(f"""<div style="background:#F9FAFB;border:1px solid #E5E7EB;border-radius:10px;
        padding:14px 18px;margin-bottom:20px;">
        <div style="font-size:12px;color:#6B7280;line-height:2;{F}">
            <strong style="color:#374151;">Formule : </strong>Points = Base catégorie × Facteur action<br>
            <strong style="color:#374151;">Exemple — DG fermé : </strong>5 × 0.6 = <strong style="color:#D97706;">3.0 pts</strong><br>
            <strong style="color:#374151;">Maximum (TXN/RAN/IPRAN · R+F) : </strong>8 × 1.0 = <strong style="color:#D97706;">8.0 pts</strong><br>
            <strong style="color:#374151;">🎯 Objectif {period_label} : </strong><strong style="color:#D97706;">{obj_pts} pts</strong>
            (progressif +10%/mois · base 100 en janvier)<br>
            <strong style="color:#EF4444;">⚠ Alerte : </strong>taux de fermeture &lt;30% après le 15 du mois → rouge automatique
        </div>
    </div>""")

    # Barème par catégorie groupé
    st.html(section_label("POINTS BASE PAR CATÉGORIE — 28 CATÉGORIES"))

    groups = {
        "⚡ ÉNERGIE": ["DG","Battery","Rectifier","ATS","ENERGY_OTHER"],
        "📡 TRANSMISSION": ["TXN","IPRAN","MW_FADING","MW_EQUIPMENT"],
        "📶 RAN / RADIO": ["RAN","ANTENNA","FEEDER","BTS_HW","BTS_SW","PARAMETER"],
        "🏗 CIVIL / ACCÈS": ["ACCESS","CIVIL","SECURITY","POWER_CABLE","EARTHING"],
        "❄ INFRASTRUCTURE": ["COOLING","SHELTER","FIBER","SWITCH","ROUTER"],
        "🔧 AUTRES": ["TRANSPORT","MONITORING","OTHER"],
    }

    bcs = ["#FFD200","#6366F1","#10B981","#F59E0B","#EC4899","#8B5CF6"]
    for gi, (grp_name, cats) in enumerate(groups.items()):
        gc = bcs[gi % len(bcs)]
        st.html(f'<div style="font-size:11px;font-weight:700;color:{gc};letter-spacing:.05em;margin:14px 0 6px;{F}">{grp_name}</div>')
        cols = st.columns(len(cats))
        for col_, cat in zip(cols, cats):
            pts  = SUB_SCORES[cat]
            ex_r = round(pts * 0.4, 1)
            ex_f = round(pts * 0.6, 1)
            ex_b = round(pts * 1.0, 1)
            col_.html(f"""<div style="background:#FFFFFF;border:1px solid #E5E7EB;
                border-radius:8px;padding:10px 8px;text-align:center;margin-bottom:4px;">
                <div style="font-size:10px;font-weight:700;color:#374151;
                    margin-bottom:6px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;{F}">{cat}</div>
                <div style="font-size:22px;font-weight:800;color:{gc};{F}">{pts}</div>
                <div style="font-size:9px;color:#9CA3AF;margin-top:4px;{F}">pts base</div>
                <div style="height:1px;background:#F3F4F6;margin:6px 0;"></div>
                <div style="font-size:9px;color:#6B7280;{F}">↑{ex_r} · ✓{ex_f} · ⟳{ex_b}</div>
            </div>""")

    # Graphique barème
    st.html('<div style="height:16px;"></div>')
    st.html(section_label("VISUALISATION — POINTS BASE PAR CATÉGORIE"))
    sorted_cats = sorted(SUB_SCORES.items(), key=lambda x: -x[1])
    color_map   = {}
    for gi, (grp_name, cats) in enumerate(groups.items()):
        for cat in cats:
            color_map[cat] = bcs[gi % len(bcs)]

    fig_bar = go.Figure(go.Bar(
        x=[s[1] for s in sorted_cats],
        y=[s[0] for s in sorted_cats],
        orientation="h",
        marker_color=[color_map.get(s[0],"#94A3B8") for s in sorted_cats],
        marker_line_width=0,
        text=[f"{s[1]} pts" for s in sorted_cats],
        textposition="outside",
        textfont=dict(size=10, family="Plus Jakarta Sans", color="#374151"),
    ))
    fig_bar.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#FAFAFA",
        height=600, margin=dict(l=0,r=60,t=8,b=8),
        xaxis=dict(gridcolor="#F3F4F6", range=[0,10],
                   tickfont=dict(size=10,family="Plus Jakarta Sans")),
        yaxis=dict(gridcolor="rgba(0,0,0,0)",
                   tickfont=dict(size=11,family="Plus Jakarta Sans"),autorange="reversed"),
        showlegend=False,
    )
    st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar":False})

    # Simulateur de points
    st.html(section_label("🧮 SIMULATEUR DE POINTS"))
    sim1, sim2, sim3 = st.columns(3)
    with sim1:
        sim_cat = st.selectbox("Catégorie", CATEGORIES,
                               format_func=lambda x: f"{x}  ({SUB_SCORES[x]} pts base)")
    with sim2:
        sim_act = st.selectbox("Action",
                               ["raised","closed","both"],
                               format_func=lambda x: {"raised":"↑ Remonté (40%)","closed":"✓ Fermé (60%)","both":"⟳ R+F (100%)"}[x])
    with sim3:
        sim_pts = calc_pts(sim_cat, sim_act)
        ac_     = ACTION_COLOR.get(sim_act,"#6B7280")
        st.html(f"""<div style="background:{ac_}11;border:2px solid {ac_}44;
            border-radius:10px;padding:14px;text-align:center;margin-top:4px;">
            <div style="font-size:11px;color:{ac_};font-weight:700;{F}">POINTS CALCULÉS</div>
            <div style="font-size:40px;font-weight:800;color:{ac_};{F}">{sim_pts}</div>
            <div style="font-size:10px;color:#9CA3AF;{F}">
                {SUB_SCORES[sim_cat]} × {ACTION_FACTOR[sim_act]}
            </div>
        </div>""")


# ══════════════════════════════════════════════════════════════════
#  TAB 4 — TECHNICIENS
# ══════════════════════════════════════════════════════════════════
with tab_techs:
    st.html(section_label("AJOUTER UN TECHNICIEN"))
    with st.form("form_add_tech", clear_on_submit=True):
        ca1,ca2,ca3,ca4 = st.columns([3,2,2,1])
        with ca1: new_nom    = st.text_input("Nom complet", placeholder="Prénom NOM…")
        with ca2: new_region = st.selectbox("Région",["South","Brazzaville","Pool","Nord","Dolisie","Autre"])
        with ca3: new_equipe = st.selectbox("Équipe",["FLM","FME","NOC","Back Office","Sous-traitant"])
        with ca4:
            st.markdown("<br>", unsafe_allow_html=True)
            add_btn = st.form_submit_button("✚ Ajouter", use_container_width=True)
        if add_btn:
            if not new_nom.strip(): st.error("Nom requis")
            elif new_nom.strip().lower() in [t.lower() for t in techs_noms]: st.error("Déjà existant")
            else:
                if add_tech(new_nom.strip(), new_region, new_equipe):
                    st.success(f"✓ {new_nom.strip()} ajouté")
                    st.cache_data.clear(); st.rerun()

    st.html(section_label(f"LISTE DES TECHNICIENS ({len(techs_list)})"))
    if not techs_list:
        st.html(f"""<div style="background:#F9FAFB;border:2px dashed #E5E7EB;border-radius:10px;
            padding:40px;text-align:center;">
            <div style="font-size:13px;color:#9CA3AF;{F}">Aucun technicien. Ajoutez votre équipe ci-dessus.</div>
        </div>""")
    else:
        hdr_t = st.columns([0.4,2.2,1.2,1.2,1,0.8,0.8,0.8])
        for col,h in zip(hdr_t,["#","NOM","RÉGION","ÉQUIPE","POINTS","SNAGS","FERMÉS",""]):
            col.markdown(f"<div style='font-size:10px;font-weight:700;color:#9CA3AF;letter-spacing:.06em;text-transform:uppercase;{F}'>{h}</div>",unsafe_allow_html=True)

        active_map = {t["name"]:t for t in lb}
        for i, tech in enumerate(techs_list):
            t       = active_map.get(tech["nom"])
            row     = st.columns([0.4,2.2,1.2,1.2,1,0.8,0.8,0.8])
            is_alrt = tech["nom"] in alert_set
            row[0].markdown(f"<div style='padding:8px 0;font-size:11px;color:#9CA3AF;{F}'>{i+1}</div>",unsafe_allow_html=True)
            nc = "#DC2626" if is_alrt else "#111827"
            row[1].markdown(f"<div style='padding:8px 0;font-size:12px;font-weight:700;color:{nc};{F}'>{'⚠ ' if is_alrt else ''}{tech['nom']}</div>",unsafe_allow_html=True)
            row[2].markdown(f"<div style='padding:8px 0;font-size:11px;color:#6B7280;{F}'>{tech['region']}</div>",unsafe_allow_html=True)
            row[3].markdown(f"<div style='padding:8px 0;font-size:11px;color:#6B7280;{F}'>{tech['equipe']}</div>",unsafe_allow_html=True)
            if t:
                row[4].markdown(f"<div style='padding:8px 0;font-size:13px;font-weight:800;color:#D97706;{F}'>{t['total']}</div>",unsafe_allow_html=True)
                row[5].markdown(f"<div style='padding:8px 0;font-size:12px;color:#374151;text-align:center;{F}'>{t['n']}</div>",unsafe_allow_html=True)
                row[6].markdown(f"<div style='padding:8px 0;font-size:12px;color:#6366F1;font-weight:700;text-align:center;{F}'>{t['closed']}</div>",unsafe_allow_html=True)
            else:
                for c_ in [row[4],row[5],row[6]]: c_.markdown(f"<div style='color:#D1D5DB;padding:8px 0;text-align:center;{F}'>—</div>",unsafe_allow_html=True)
            with row[7]:
                sb1,sb2 = st.columns(2)
                with sb1:
                    if st.button("✎", key=f"ren_tech_{tech['id']}"):
                        st.session_state[f"renaming_tech_{tech['id']}"] = True
                with sb2:
                    if st.button("✕", key=f"del_tech_{tech['id']}"):
                        delete_tech(tech["id"]); st.cache_data.clear(); st.rerun()

            if st.session_state.get(f"renaming_tech_{tech['id']}"):
                with st.form(f"ren_form_{tech['id']}"):
                    rn1,rn2,rn3,rn4 = st.columns([2.5,1.5,1.5,0.8])
                    new_rnom = rn1.text_input("Nom", value=tech["nom"], label_visibility="collapsed")
                    reg_opts = ["South","Brazzaville","Pool","Nord","Dolisie","Autre"]
                    eq_opts  = ["FLM","FME","NOC","Back Office","Sous-traitant"]
                    new_rreg = rn2.selectbox("Région", reg_opts,
                                             index=reg_opts.index(tech["region"]) if tech["region"] in reg_opts else 0,
                                             label_visibility="collapsed")
                    new_req  = rn3.selectbox("Équipe", eq_opts,
                                             index=eq_opts.index(tech["equipe"]) if tech["equipe"] in eq_opts else 0,
                                             label_visibility="collapsed")
                    ok = rn4.form_submit_button("✓")
                    if ok:
                        update_tech(tech["id"], new_rnom.strip(), new_rreg, new_req)
                        st.session_state[f"renaming_tech_{tech['id']}"] = False
                        st.cache_data.clear(); st.rerun()
            st.html('<div style="height:1px;background:#F3F4F6;"></div>')

        with st.expander("⚠ Zone dangereuse"):
            if st.button("🗑 Supprimer tous les techniciens", use_container_width=True):
                for t in techs_list: delete_tech(t["id"])
                st.cache_data.clear(); st.rerun()


# ══════════════════════════════════════════════════════════════════
#  TAB 5 — SNAGS
# ══════════════════════════════════════════════════════════════════
with tab_snags:
    edit_snag_id   = st.session_state.get("edit_snag_id", None)
    edit_snag_data = {}
    if edit_snag_id and snags_data:
        rows = [s for s in snags_data if s["id"] == edit_snag_id]
        if rows: edit_snag_data = rows[0]

    st.html(section_label(f"{'✎ MODIFIER' if edit_snag_id else '✚ NOUVEAU SNAG'} — {period_label}"))
    with st.form("form_snag"):
        sr1,sr2 = st.columns(2)
        with sr1:
            tech_options = ["— Sélectionner —"] + techs_noms
            def_ti = (techs_noms.index(edit_snag_data.get("technicien",""))+1
                      if edit_snag_data.get("technicien") in techs_noms else 0)
            sel_tech = st.selectbox("Technicien", tech_options, index=def_ti)
            man_tech = st.text_input("Ou saisir manuellement",
                                     value=edit_snag_data.get("technicien",""),
                                     placeholder="Nom complet…")
        with sr2:
            auditeur = st.text_input("Auditeur (si remonté par un tiers)",
                                     value=edit_snag_data.get("auditeur",""),
                                     placeholder="Nom de l'auditeur…")
            site_nom = st.text_input("Site", value=edit_snag_data.get("site_nom",""),
                                     placeholder="DOLISIE_CENTRE")

        sr3,sr4,sr5 = st.columns(3)
        with sr3: site_id_v = st.text_input("Site ID", value=edit_snag_data.get("site_id",""), placeholder="CG_DOL_001")
        with sr4:
            cat_def = CATEGORIES.index(edit_snag_data.get("categorie","DG")) if edit_snag_data.get("categorie","DG") in CATEGORIES else 0
            cat = st.selectbox("Catégorie", CATEGORIES, index=cat_def,
                               format_func=lambda x: f"{x}  ({SUB_SCORES[x]} pts base)")
        with sr5:
            d_def = edit_snag_data.get("date_snag", TODAY)
            if isinstance(d_def, str): d_def = date.fromisoformat(d_def)
            snag_date = st.date_input("Date", value=d_def)

        act_opts = {"raised":"↑ Remonté — 40%","closed":"✓ Fermé — 60%","both":"⟳ R+F — 100%"}
        def_act  = list(act_opts.keys()).index(edit_snag_data.get("action","closed")) if edit_snag_data.get("action") in act_opts else 1
        action   = st.radio("Action", list(act_opts.keys()),
                            format_func=lambda x: act_opts[x], index=def_act, horizontal=True)
        desc     = st.text_input("Description", value=edit_snag_data.get("description",""), placeholder="Description optionnelle…")
        pts_prev = calc_pts(cat, action)
        ac_      = ACTION_COLOR.get(action,"#6B7280")
        st.html(f"""<div style="background:{ac_}11;border:1px solid {ac_}44;border-radius:8px;
            padding:10px 14px;display:flex;justify-content:space-between;align-items:center;">
            <div style="font-size:11px;color:#6B7280;{F}">
                {cat} · Base {SUB_SCORES[cat]} pts × {ACTION_FACTOR[action]} = {pts_prev} pts
            </div>
            <div style="font-size:30px;font-weight:800;color:{ac_};{F}">{pts_prev} pts</div>
        </div>""")

        if edit_snag_id:
            sb1,sb2 = st.columns([3,1])
            with sb1: submitted = st.form_submit_button("METTRE À JOUR", use_container_width=True)
            with sb2:
                if st.form_submit_button("Annuler"):
                    st.session_state["edit_snag_id"] = None; st.rerun()
        else:
            submitted = st.form_submit_button("ENREGISTRER LE SNAG", use_container_width=True)

        if submitted:
            tech_ = man_tech.strip() if man_tech.strip() else (sel_tech if sel_tech != "— Sélectionner —" else "")
            if not tech_: st.error("Technicien requis")
            elif not site_nom.strip(): st.error("Site requis")
            else:
                row = {"technicien":tech_,"site_nom":site_nom.strip(),"site_id":site_id_v.strip(),
                       "categorie":cat,"action":action,"date_snag":str(snag_date),
                       "auditeur":auditeur.strip() or None,"description":desc.strip(),
                       "points":pts_prev,"annee":sel_y,"mois":sel_m}
                ok = update_snag_manager(edit_snag_id, row) if edit_snag_id else insert_snag_manager(row)
                if ok:
                    st.success(f"✓ Snag {'mis à jour' if edit_snag_id else 'enregistré'} (+{pts_prev} pts)")
                    st.session_state["edit_snag_id"] = None
                    st.cache_data.clear(); st.rerun()

    if overdue_snags:
        st.html(section_label(f"🔴 SNAGS EN RETARD (>7j) — {len(overdue_snags)} cas"))
        for s in overdue_snags:
            aud = f"· Auditeur : <strong>{s['auditeur']}</strong>" if s.get("auditeur") else ""
            st.html(f"""<div style="background:#FEF2F2;border:1px solid #FECACA;border-radius:8px;
                padding:8px 14px;margin-bottom:6px;display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <span style="font-size:12px;font-weight:700;color:#DC2626;{F}">{s['technicien']}</span>
                    <span style="font-size:11px;color:#6B7280;{F}"> · {s['site_nom']} · {s['categorie']}</span>
                    <div style="font-size:11px;color:#9CA3AF;margin-top:2px;{F}">Depuis le {s['date_snag']} {aud}</div>
                </div>
                {status_badge_snag(s['days_open'])}
            </div>""")

    st.html(section_label(f"TOUS LES SNAGS — {period_label} ({len(snags_data)})"))
    if snags_data:
        hdr2 = st.columns([1,1.5,1.5,1,1,1,0.7,1])
        for col,h in zip(hdr2,["DATE","TECH.","SITE","CAT.","ACTION","AUDITEUR","PTS",""]):
            col.markdown(f"<div style='font-size:10px;font-weight:700;color:#9CA3AF;letter-spacing:.06em;text-transform:uppercase;{F}'>{h}</div>",unsafe_allow_html=True)
        for s in snags_data:
            d0        = date.fromisoformat(str(s["date_snag"]))
            days_open = (TODAY - d0).days
            row       = st.columns([1,1.5,1.5,1,1,1,0.7,1])
            row[0].markdown(f"<div style='font-size:11px;color:#9CA3AF;padding:6px 0;{F}'>{s['date_snag']}</div>",unsafe_allow_html=True)
            row[1].markdown(f"<div style='font-size:12px;font-weight:600;color:#111827;padding:6px 0;{F}'>{s['technicien']}</div>",unsafe_allow_html=True)
            row[2].markdown(f"<div style='font-size:11px;color:#374151;padding:6px 0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;{F}'>{s['site_nom']}</div>",unsafe_allow_html=True)
            row[3].markdown(f"<div style='font-size:11px;padding:6px 0;{F}'>{s['categorie']}</div>",unsafe_allow_html=True)
            ac_ = ACTION_COLOR.get(s["action"],"#9CA3AF")
            row[4].html(f"<div style='padding:6px 0;'><span style='background:{ac_}22;color:{ac_};font-size:10px;font-weight:700;border-radius:12px;padding:2px 7px;{F}'>{ACTION_LABEL.get(s['action'],s['action'])}</span></div>")
            row[5].markdown(f"<div style='font-size:11px;color:#6B7280;padding:6px 0;{F}'>{s.get('auditeur') or '—'}</div>",unsafe_allow_html=True)
            row[6].markdown(f"<div style='font-size:13px;font-weight:800;color:#D97706;padding:6px 0;text-align:center;{F}'>{s['points']}</div>",unsafe_allow_html=True)
            with row[7]:
                b1,b2 = st.columns(2)
                with b1:
                    if st.button("✎", key=f"e_snag_{s['id']}"):
                        st.session_state["edit_snag_id"] = s["id"]; st.rerun()
                with b2:
                    ck = f"confirm_del_snag_{s['id']}"
                    if st.session_state.get(ck):
                        c1_,c2_ = st.columns(2)
                        if c1_.button("✓", key=f"yes_snag_{s['id']}"):
                            delete_snag_manager(s["id"]); st.session_state[ck]=False
                            st.cache_data.clear(); st.rerun()
                        if c2_.button("✗", key=f"no_snag_{s['id']}"):
                            st.session_state[ck]=False; st.rerun()
                    else:
                        if st.button("🗑", key=f"d_snag_{s['id']}"):
                            st.session_state[ck]=True; st.rerun()
            st.html('<div style="height:1px;background:#F3F4F6;"></div>')
    else:
        st.html(f"""<div style="background:#F9FAFB;border:2px dashed #E5E7EB;border-radius:10px;
            padding:30px;text-align:center;">
            <div style="font-size:12px;color:#9CA3AF;{F}">Aucun snag pour {period_label}</div>
        </div>""")


# ══════════════════════════════════════════════════════════════════
#  TAB 6 — RCA & ASSET
# ══════════════════════════════════════════════════════════════════
with tab_mgmt:
    st.html(f"""<div style="background:#EFF6FF;border:1.5px solid #BFDBFE;border-radius:10px;
        padding:12px 16px;margin-bottom:16px;">
        <div style="font-size:11px;font-weight:700;color:#1D4ED8;letter-spacing:.06em;text-transform:uppercase;{F}">
            📋 RUBRIQUE MANAGEMENT — RCA & ASSET
        </div>
        <div style="font-size:11px;color:#3B82F6;margin-top:3px;{F}">
            RCA : délai 48h · alerte rouge à 72h &nbsp;|&nbsp; ASSET : deadline le 20 de chaque mois
        </div>
    </div>""")

    rca_tab, asset_tab = st.tabs(["📄 Suivi RCA","📦 Suivi ASSET"])

    with rca_tab:
        edit_rca_id = st.session_state.get("edit_rca_id", None)
        edit_rca    = {}
        if edit_rca_id and rca_data:
            rows = [r for r in rca_data if r["id"] == edit_rca_id]
            if rows: edit_rca = rows[0]

        st.html(section_label(f"{'✎ MODIFIER' if edit_rca_id else '✚ NOUVEAU'} RCA — {period_label}"))
        with st.form("form_rca"):
            fr1,fr2 = st.columns(2)
            with fr1:
                rca_resp_opts = ["— Choisir —"] + techs_noms
                def_ri = (techs_noms.index(edit_rca.get("responsable",""))+1
                          if edit_rca.get("responsable") in techs_noms else 0)
                rca_resp_sel = st.selectbox("Responsable (liste)", rca_resp_opts, index=def_ri)
                rca_resp_man = st.text_input("Ou saisir manuellement",
                                             value=edit_rca.get("responsable",""), placeholder="Prénom NOM…")
            with fr2:
                rca_site = st.text_input("Site", value=edit_rca.get("site_nom",""), placeholder="Nom du site")
                rca_inc  = st.text_input("Description incident", value=edit_rca.get("incident",""), placeholder="Ex: Panne DG totale")

            fr3,fr4,fr5 = st.columns(3)
            with fr3:
                d_inc_def = edit_rca.get("date_incident", datetime.now())
                if isinstance(d_inc_def, str): d_inc_def = datetime.fromisoformat(d_inc_def.replace("Z",""))
                rca_date_inc = st.date_input("Date incident", value=d_inc_def.date() if hasattr(d_inc_def,"date") else TODAY)
                rca_time_inc = st.time_input("Heure incident", value=d_inc_def.time() if hasattr(d_inc_def,"time") else datetime.now().time())
            with fr4:
                rca_submitted = st.checkbox("RCA soumis", value=bool(edit_rca.get("date_rca")))
                if rca_submitted:
                    d_rca_def = edit_rca.get("date_rca", datetime.now())
                    if isinstance(d_rca_def, str): d_rca_def = datetime.fromisoformat(d_rca_def.replace("Z",""))
                    rca_date_sub = st.date_input("Date soumission", value=d_rca_def.date() if hasattr(d_rca_def,"date") else TODAY)
                    rca_time_sub = st.time_input("Heure soumission", value=d_rca_def.time() if hasattr(d_rca_def,"time") else datetime.now().time())
                else:
                    rca_date_sub = None; rca_time_sub = None
            with fr5:
                rca_statut  = st.selectbox("Statut",["pending","submitted","validated"],
                                           format_func=lambda x:{"pending":"En attente","submitted":"Soumis","validated":"Validé"}[x],
                                           index=["pending","submitted","validated"].index(edit_rca.get("statut","pending")))
                rca_comment = st.text_input("Commentaire", value=edit_rca.get("commentaire",""))

            if edit_rca_id:
                rb1,rb2 = st.columns([3,1])
                with rb1: rca_ok = st.form_submit_button("METTRE À JOUR RCA", use_container_width=True)
                with rb2:
                    if st.form_submit_button("Annuler"):
                        st.session_state["edit_rca_id"]=None; st.rerun()
            else:
                rca_ok = st.form_submit_button("ENREGISTRER RCA", use_container_width=True)

            if rca_ok:
                resp_ = rca_resp_man.strip() if rca_resp_man.strip() else (rca_resp_sel if rca_resp_sel!="— Choisir —" else "")
                if not resp_: st.error("Responsable requis")
                elif not rca_site.strip(): st.error("Site requis")
                elif not rca_inc.strip(): st.error("Incident requis")
                else:
                    d_rca_str = str(datetime.combine(rca_date_sub,rca_time_sub)) if rca_submitted and rca_date_sub else None
                    row = {"responsable":resp_,"site_nom":rca_site.strip(),"incident":rca_inc.strip(),
                           "date_incident":str(datetime.combine(rca_date_inc,rca_time_inc)),
                           "date_rca":d_rca_str,"statut":rca_statut,
                           "commentaire":rca_comment.strip(),"annee":sel_y,"mois":sel_m}
                    ok = update_rca(edit_rca_id, row) if edit_rca_id else insert_rca(row)
                    if ok:
                        st.success("✓ RCA enregistré")
                        st.session_state["edit_rca_id"]=None
                        st.cache_data.clear(); st.rerun()

        st.html(section_label(f"LISTE RCA — {period_label} ({len(rca_data)})"))
        if rca_data:
            for r in rca_data:
                d_inc = datetime.fromisoformat(str(r["date_incident"]).replace("Z",""))
                hrs   = (datetime.fromisoformat(str(r["date_rca"]).replace("Z","")) - d_inc).total_seconds()/3600 if r.get("date_rca") else (datetime.now()-d_inc).total_seconds()/3600
                sc1,sc2,sc3,sc4 = st.columns([2.5,2,1.5,0.8])
                bg_rca = "#FEF2F2" if hrs>=72 else "#FFFBEB" if hrs>=48 else "#F0FDF4"
                sc1.html(f"""<div style="background:{bg_rca};border-radius:8px;padding:8px 12px;margin-bottom:4px;">
                    <div style="font-size:12px;font-weight:700;color:#111827;{F}">{r['responsable']}</div>
                    <div style="font-size:11px;color:#6B7280;{F}">{r['site_nom']} · {r['incident']}</div>
                    <div style="font-size:10px;color:#9CA3AF;margin-top:2px;{F}">Incident: {d_inc.strftime('%d/%m %H:%M')}</div>
                </div>""")
                sc2.html(f"""<div style="padding:8px 0;">
                    <div style="font-size:11px;color:#6B7280;{F}">{"Soumis" if r.get("date_rca") else "Non soumis"}</div>
                    {'<div style="font-size:10px;color:#9CA3AF;">'+str(r["date_rca"])[:16]+'</div>' if r.get("date_rca") else '<div style="font-size:10px;color:#DC2626;font-weight:700;">RCA non livré</div>'}
                </div>""")
                sc3.html(f"<div style='padding:10px 0;'>{status_badge_rca(hrs)}</div>")
                with sc4:
                    rb_e,rb_d = st.columns(2)
                    if rb_e.button("✎", key=f"e_rca_{r['id']}"):
                        st.session_state["edit_rca_id"]=r["id"]; st.rerun()
                    if rb_d.button("🗑", key=f"d_rca_{r['id']}"):
                        delete_rca(r["id"]); st.cache_data.clear(); st.rerun()
                st.html('<div style="height:1px;background:#F3F4F6;"></div>')
        else:
            st.html(f"""<div style="background:#F9FAFB;border:2px dashed #E5E7EB;border-radius:10px;
                padding:24px;text-align:center;"><div style="font-size:12px;color:#9CA3AF;{F}">Aucun RCA pour {period_label}</div></div>""")

    with asset_tab:
        deadline_asset  = date(sel_y, sel_m, 20)
        days_left_asset = (deadline_asset - TODAY).days
        badge_color     = "#EF4444" if days_left_asset<=3 else "#F59E0B" if days_left_asset<=7 else "#10B981"
        st.html(f"""<div style="background:#FFFBEB;border:1.5px solid #FDE68A;border-radius:10px;
            padding:12px 16px;margin-bottom:12px;display:flex;justify-content:space-between;align-items:center;">
            <div style="font-size:12px;font-weight:700;color:#92400E;{F}">📦 Deadline ASSET : {deadline_asset.strftime('%d %B %Y')}</div>
            <span style="background:{badge_color}22;color:{badge_color};border:1px solid {badge_color}44;
                font-size:12px;font-weight:700;border-radius:8px;padding:4px 12px;{F}">
                {'J-'+str(days_left_asset) if days_left_asset>=0 else '⚠ Dépassé'}
            </span>
        </div>""")

        edit_ast_id = st.session_state.get("edit_ast_id", None)
        edit_ast    = {}
        if edit_ast_id and asset_data:
            rows = [a for a in asset_data if a["id"]==edit_ast_id]
            if rows: edit_ast = rows[0]

        st.html(section_label(f"{'✎ MODIFIER' if edit_ast_id else '✚ AJOUTER'} ASSET"))
        with st.form("form_asset"):
            fa1,fa2,fa3 = st.columns([2,1.5,1])
            with fa1:
                ast_nom_opts = ["— Choisir —"] + techs_noms
                def_ai = (techs_noms.index(edit_ast.get("nom",""))+1
                          if edit_ast.get("nom") in techs_noms else 0)
                ast_nom_sel = st.selectbox("Responsable (liste)", ast_nom_opts, index=def_ai)
                ast_nom_man = st.text_input("Ou saisir manuellement", value=edit_ast.get("nom",""), placeholder="Prénom NOM…")
            with fa2:
                reg_opts   = ["South","Brazzaville","Pool","Nord","Dolisie","Autre"]
                ast_region = st.selectbox("Région", reg_opts,
                                          index=reg_opts.index(edit_ast.get("region","South")) if edit_ast.get("region","South") in reg_opts else 0)
                ast_sites  = st.number_input("Nb sites", min_value=0, max_value=500, value=edit_ast.get("site_count",0))
            with fa3:
                ast_soumis = st.checkbox("Soumis", value=bool(edit_ast.get("soumis",False)))
                ast_date_soumis = None
                if ast_soumis:
                    d_ast_def = edit_ast.get("date_soumis", TODAY)
                    if isinstance(d_ast_def, str): d_ast_def = date.fromisoformat(d_ast_def)
                    ast_date_soumis = st.date_input("Date soumission", value=d_ast_def)
            ast_comment = st.text_input("Commentaire", value=edit_ast.get("commentaire",""))

            if edit_ast_id:
                ab1,ab2 = st.columns([3,1])
                with ab1: ast_ok = st.form_submit_button("METTRE À JOUR ASSET", use_container_width=True)
                with ab2:
                    if st.form_submit_button("Annuler"):
                        st.session_state["edit_ast_id"]=None; st.rerun()
            else:
                ast_ok = st.form_submit_button("ENREGISTRER ASSET", use_container_width=True)

            if ast_ok:
                nom_ = ast_nom_man.strip() if ast_nom_man.strip() else (ast_nom_sel if ast_nom_sel!="— Choisir —" else "")
                if not nom_: st.error("Nom requis")
                else:
                    row = {"nom":nom_,"region":ast_region,"site_count":ast_sites,"soumis":ast_soumis,
                           "date_soumis":str(ast_date_soumis) if ast_soumis and ast_date_soumis else None,
                           "commentaire":ast_comment.strip(),"annee":sel_y,"mois":sel_m}
                    ok = update_asset(edit_ast_id, row) if edit_ast_id else insert_asset(row)
                    if ok:
                        st.success("✓ ASSET enregistré")
                        st.session_state["edit_ast_id"]=None
                        st.cache_data.clear(); st.rerun()

        submitted_c = sum(1 for a in asset_data if a.get("soumis"))
        ac1,ac2,ac3 = st.columns(3)
        ac1.html(kpi_card("Total ASSET", str(len(asset_data)), period_label))
        ac2.html(kpi_card("Soumis", str(submitted_c), "dans les délais","#10B981"))
        ac3.html(kpi_card("En attente", str(len(asset_data)-submitted_c), "non soumis","#EF4444" if len(asset_data)-submitted_c else "#10B981"))

        st.html(section_label(f"LISTE ASSET — {period_label}"))
        if asset_data:
            for a in asset_data:
                sc1,sc2,sc3,sc4 = st.columns([2,1.2,1.5,0.8])
                bg_a = "#F0FDF4" if a.get("soumis") else "#FFFBEB"
                sc1.html(f"""<div style="background:{bg_a};border-radius:8px;padding:8px 12px;margin-bottom:4px;">
                    <div style="font-size:12px;font-weight:700;color:#111827;{F}">{a['nom']}</div>
                    <div style="font-size:11px;color:#6B7280;{F}">{a['region']} · {a['site_count']} sites</div>
                </div>""")
                sc2.html(f"<div style='padding:10px 0;'>{'<span style=\"background:#D1FAE5;color:#065F46;border-radius:12px;padding:3px 10px;font-size:11px;font-weight:700;\">✓ Soumis</span>' if a.get('soumis') else '<span style=\"background:#FEF3C7;color:#92400E;border-radius:12px;padding:3px 10px;font-size:11px;font-weight:700;\">⏳ En attente</span>'}</div>")
                sc3.html(f"<div style='font-size:11px;color:#9CA3AF;padding:10px 0;{F}'>{('Le '+str(a['date_soumis'])) if a.get('date_soumis') else 'Non soumis'}</div>")
                with sc4:
                    ae1,ae2 = st.columns(2)
                    if ae1.button("✎", key=f"e_ast_{a['id']}"):
                        st.session_state["edit_ast_id"]=a["id"]; st.rerun()
                    if ae2.button("🗑", key=f"d_ast_{a['id']}"):
                        delete_asset(a["id"]); st.cache_data.clear(); st.rerun()
                st.html('<div style="height:1px;background:#F3F4F6;"></div>')


# ══════════════════════════════════════════════════════════════════
#  TAB 7 — BLOCAGES
# ══════════════════════════════════════════════════════════════════
with tab_blockers:
    edit_blk_id = st.session_state.get("edit_blk_id", None)
    edit_blk    = {}
    if edit_blk_id and blockers_d:
        rows = [b for b in blockers_d if b["id"]==edit_blk_id]
        if rows: edit_blk = rows[0]

    open_blk   = [b for b in blockers_d if not b.get("resolu")]
    closed_blk = [b for b in blockers_d if b.get("resolu")]

    bk1,bk2 = st.columns(2)
    bk1.html(kpi_card("Blocages ouverts", str(len(open_blk)), "action requise","#EF4444" if open_blk else "#10B981"))
    bk2.html(kpi_card("Résolus ce mois", str(len(closed_blk)), f"sur {len(blockers_d)} total","#10B981"))

    st.html(section_label(f"{'✎ MODIFIER' if edit_blk_id else '✚ SIGNALER'} UN POINT BLOQUANT"))
    with st.form("form_blocker"):
        bb1,bb2 = st.columns(2)
        with bb1:
            blk_tech_opts = ["— Choisir —"] + techs_noms
            def_bi = (techs_noms.index(edit_blk.get("technicien",""))+1
                      if edit_blk.get("technicien") in techs_noms else 0)
            blk_tech_sel = st.selectbox("Technicien (liste)", blk_tech_opts, index=def_bi)
            blk_tech_man = st.text_input("Ou saisir manuellement", value=edit_blk.get("technicien",""), placeholder="Prénom NOM…")
        with bb2:
            blk_site = st.text_input("Site", value=edit_blk.get("site_nom",""), placeholder="Nom du site")
            blk_cat  = st.selectbox("Catégorie", ["—"]+CATEGORIES,
                                    index=CATEGORIES.index(edit_blk.get("categorie","DG"))+1 if edit_blk.get("categorie") in CATEGORIES else 0)

        blk_desc  = st.text_area("Description du blocage", value=edit_blk.get("description",""),
                                 placeholder="Expliquer pourquoi le snag ne peut pas être fermé…", height=80)
        bb3,bb4,_ = st.columns(3)
        with bb3:
            d_blk_def = edit_blk.get("date_signal", TODAY)
            if isinstance(d_blk_def, str): d_blk_def = date.fromisoformat(d_blk_def)
            blk_date = st.date_input("Date signalement", value=d_blk_def)
        with bb4:
            blk_resolu   = st.checkbox("Résolu", value=bool(edit_blk.get("resolu",False)))
            blk_date_res = None
            if blk_resolu:
                d_res_def = edit_blk.get("date_resolu", TODAY)
                if isinstance(d_res_def, str) and d_res_def: d_res_def = date.fromisoformat(d_res_def)
                blk_date_res = st.date_input("Date résolution", value=d_res_def or TODAY)

        if edit_blk_id:
            pb1,pb2 = st.columns([3,1])
            with pb1: blk_ok = st.form_submit_button("METTRE À JOUR", use_container_width=True)
            with pb2:
                if st.form_submit_button("Annuler"):
                    st.session_state["edit_blk_id"]=None; st.rerun()
        else:
            blk_ok = st.form_submit_button("ENREGISTRER LE BLOCAGE", use_container_width=True)

        if blk_ok:
            tech_ = blk_tech_man.strip() if blk_tech_man.strip() else (blk_tech_sel if blk_tech_sel!="— Choisir —" else "")
            if not tech_: st.error("Technicien requis")
            elif not blk_desc.strip(): st.error("Description requise")
            elif not blk_site.strip(): st.error("Site requis")
            else:
                row = {"technicien":tech_,"site_nom":blk_site.strip(),
                       "categorie":blk_cat if blk_cat!="—" else None,
                       "description":blk_desc.strip(),"date_signal":str(blk_date),
                       "resolu":blk_resolu,
                       "date_resolu":str(blk_date_res) if blk_resolu and blk_date_res else None,
                       "annee":sel_y,"mois":sel_m}
                ok = update_blocker(edit_blk_id, row) if edit_blk_id else insert_blocker(row)
                if ok:
                    st.success("✓ Point bloquant enregistré")
                    st.session_state["edit_blk_id"]=None
                    st.cache_data.clear(); st.rerun()

    if open_blk:
        st.html(section_label(f"🔴 BLOCAGES OUVERTS ({len(open_blk)})"))
        for b in open_blk:
            days_blk = (TODAY - date.fromisoformat(str(b["date_signal"]))).days
            bc1,bc2,bc3 = st.columns([3,1,0.8])
            bc1.html(f"""<div style="background:#FEF2F2;border:1px solid #FECACA;border-radius:8px;padding:8px 12px;margin-bottom:4px;">
                <div style="font-size:12px;font-weight:700;color:#DC2626;{F}">🔒 {b['technicien']} — {b['site_nom']}
                    {f'<span style="font-size:10px;background:#FEE2E2;border-radius:4px;padding:1px 6px;margin-left:6px;">{b["categorie"]}</span>' if b.get("categorie") else ''}</div>
                <div style="font-size:11px;color:#374151;margin-top:3px;{F}">{b['description']}</div>
                <div style="font-size:10px;color:#9CA3AF;margin-top:3px;{F}">Signalé le {b['date_signal']} · {days_blk} jours</div>
            </div>""")
            bc2.html(f"<div style='padding:12px 0;'><span style='background:#FEE2E2;color:#DC2626;font-size:11px;font-weight:700;border-radius:8px;padding:4px 10px;{F}'>J+{days_blk}</span></div>")
            with bc3:
                be1,be2 = st.columns(2)
                if be1.button("✎", key=f"e_blk_{b['id']}"):
                    st.session_state["edit_blk_id"]=b["id"]; st.rerun()
                if be2.button("🗑", key=f"d_blk_{b['id']}"):
                    delete_blocker(b["id"]); st.cache_data.clear(); st.rerun()

    if closed_blk:
        with st.expander(f"✅ Blocages résolus ({len(closed_blk)})"):
            for b in closed_blk:
                st.html(f"""<div style="background:#F0FDF4;border:1px solid #BBF7D0;border-radius:8px;padding:8px 12px;margin-bottom:6px;">
                    <div style="font-size:12px;font-weight:700;color:#166534;{F}">✓ {b['technicien']} — {b['site_nom']}</div>
                    <div style="font-size:11px;color:#374151;{F}">{b['description']}</div>
                    <div style="font-size:10px;color:#9CA3AF;{F}">Résolu le {b.get('date_resolu','—')}</div>
                </div>""")


# ══════════════════════════════════════════════════════════════════
#  TAB 8 — TENDANCES 6 MOIS
# ══════════════════════════════════════════════════════════════════
with tab_trend:
    months_6 = []
    for i in range(5,-1,-1):
        d = date(CUR_Y, CUR_M, 1) - timedelta(days=30*i)
        months_6.append((d.year, d.month))
    labels_6 = [MONTHS_FR[m-1][:3]+f" {y}" for y,m in months_6]
    obj_6    = [obj_for_month(m) for y,m in months_6]

    @st.cache_data(ttl=120, show_spinner=False)
    def load_6months():
        all_data = {}
        for y,m in months_6:
            all_data[(y,m)] = fetch_snags_manager(y,m)
        return all_data

    data_6m   = load_6months()
    all_techs = set()
    for data in data_6m.values():
        for s in data: all_techs.add(s["technicien"])
    top_techs = list(all_techs)[:8]
    COLORS_6  = ["#FFD200","#6366F1","#10B981","#F59E0B","#EC4899","#8B5CF6","#14B8A6","#EF4444"]

    st.html(section_label("ÉVOLUTION CUMULATIVE — 6 DERNIERS MOIS"))
    fig_trend = go.Figure()
    for i,tech in enumerate(top_techs):
        y_vals = [round(sum(s["points"] for s in data_6m[(y,m)] if s["technicien"]==tech),1) for y,m in months_6]
        c_ = COLORS_6[i%len(COLORS_6)]
        fig_trend.add_trace(go.Scatter(x=labels_6,y=y_vals,name=tech,mode="lines+markers",
                                       line=dict(color=c_,width=2.5),marker=dict(size=7,color=c_),
                                       hovertemplate=f"<b>{tech}</b><br>%{{x}} : <b>%{{y}} pts</b><extra></extra>"))
    fig_trend.add_trace(go.Scatter(x=labels_6,y=obj_6,name="Objectif",mode="lines",
                                   line=dict(color="#EF4444",dash="dash",width=1.5)))
    fig_trend.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="#FAFAFA",height=360,
                            margin=dict(l=0,r=20,t=10,b=8),
                            xaxis=dict(gridcolor="#F1F5F9",tickfont=dict(size=11,family="Plus Jakarta Sans")),
                            yaxis=dict(gridcolor="#F1F5F9",tickfont=dict(size=11,family="Plus Jakarta Sans"),zeroline=False),
                            legend=dict(font=dict(size=11,family="Plus Jakarta Sans"),bgcolor="rgba(255,255,255,.92)",bordercolor="#E5E7EB",borderwidth=1))
    st.plotly_chart(fig_trend, use_container_width=True, config={"displayModeBar":False})
    st.html(f'<div style="font-size:10px;color:#9CA3AF;text-align:center;{F}">Courbe rouge = objectif progressif (+10%/mois)</div>')

    st.html(section_label("OBJECTIF PROGRESSIF — ÉVOLUTION AUTOMATIQUE"))
    fig_obj = go.Figure()
    fig_obj.add_trace(go.Bar(x=labels_6,y=obj_6,
                             marker_color=["#FFD200" if (y,m)==(CUR_Y,CUR_M) else "#E5E7EB" for y,m in months_6],
                             marker_line_width=0,text=[f"{v} pts" for v in obj_6],textposition="outside"))
    fig_obj.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="#FAFAFA",height=200,
                          margin=dict(l=0,r=20,t=8,b=8),showlegend=False,
                          xaxis=dict(tickfont=dict(size=11,family="Plus Jakarta Sans")),
                          yaxis=dict(gridcolor="#F1F5F9",tickfont=dict(size=10,family="Plus Jakarta Sans")))
    st.plotly_chart(fig_obj, use_container_width=True, config={"displayModeBar":False})

    st.html(section_label("TAUX DE FERMETURE ÉQUIPE — 6 MOIS"))
    close_rates = []
    for y,m in months_6:
        data = data_6m[(y,m)]
        n_total  = len(data)
        n_closed = sum(1 for s in data if s["action"] in ["closed","both"])
        close_rates.append(round(n_closed/n_total*100,1) if n_total else 0)
    fig_close = go.Figure()
    fig_close.add_trace(go.Scatter(x=labels_6,y=close_rates,mode="lines+markers+text",
                                   line=dict(color="#10B981",width=2.5),
                                   marker=dict(size=8,color=close_rates,
                                               colorscale=[[0,"#EF4444"],[0.5,"#F59E0B"],[1,"#10B981"]]),
                                   text=[f"{v}%" for v in close_rates],textposition="top center",
                                   fill="tozeroy",fillcolor="rgba(16,185,129,0.06)"))
    fig_close.add_hline(y=70,line_dash="dash",line_color="#6366F1",line_width=1,
                        annotation_text="Cible 70%",
                        annotation_font=dict(size=10,color="#6366F1",family="Plus Jakarta Sans"))
    fig_close.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="#FAFAFA",height=220,
                            margin=dict(l=0,r=20,t=20,b=8),showlegend=False,
                            xaxis=dict(tickfont=dict(size=11,family="Plus Jakarta Sans")),
                            yaxis=dict(gridcolor="#F1F5F9",range=[0,115],ticksuffix="%",
                                       tickfont=dict(size=10,family="Plus Jakarta Sans")))
    st.plotly_chart(fig_close, use_container_width=True, config={"displayModeBar":False})

    st.html(section_label("PERFORMANCE PAR TECHNICIEN — DIAGRAMME EN BARRES GROUPÉES"))
    fig_bar_g = go.Figure()
    for i,tech in enumerate(top_techs):
        vals = [round(sum(s["points"] for s in data_6m[(y,m)] if s["technicien"]==tech),1) for y,m in months_6]
        c_   = COLORS_6[i%len(COLORS_6)]
        fig_bar_g.add_trace(go.Bar(name=tech,x=labels_6,y=vals,marker_color=c_,marker_line_width=0,
                                   hovertemplate=f"<b>{tech}</b><br>%{{x}} : %{{y}} pts<extra></extra>"))
    fig_bar_g.update_layout(barmode="group",paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="#FAFAFA",
                            height=300,margin=dict(l=0,r=20,t=8,b=8),
                            xaxis=dict(tickfont=dict(size=11,family="Plus Jakarta Sans")),
                            yaxis=dict(gridcolor="#F1F5F9",tickfont=dict(size=10,family="Plus Jakarta Sans")),
                            legend=dict(font=dict(size=10,family="Plus Jakarta Sans"),
                                        bgcolor="rgba(255,255,255,.9)",bordercolor="#E5E7EB",borderwidth=1,
                                        orientation="h",y=-0.25),
                            bargap=0.15,bargroupgap=0.05)
    st.plotly_chart(fig_bar_g, use_container_width=True, config={"displayModeBar":False})


# ══════════════════════════════════════════════════════════════════
#  TAB 9 — ANALYSE IA
# ══════════════════════════════════════════════════════════════════
with tab_ai:
    st.html(f"""<div style="background:linear-gradient(135deg,#1E1B4B,#312E81);
        border-radius:12px;padding:16px 20px;margin-bottom:16px;display:flex;align-items:center;gap:14px;">
        <div style="font-size:32px;">🤖</div>
        <div>
            <div style="font-size:15px;font-weight:800;color:#FFFFFF;{F}">FieldPerform AI · Propulsé par Claude</div>
            <div style="font-size:11px;color:#A5B4FC;margin-top:3px;{F}">
                Analyse de profil · Détection anomalies · Recommandations managériales · Question libre
            </div>
        </div>
    </div>""")

    ai_col1, ai_col2 = st.columns([1,1])
    with ai_col1:
        st.html(section_label("ANALYSE D'UN PROFIL TECHNICIEN"))
        ai_tech_opts = ["— Choisir —"] + (techs_noms if techs_noms else [t["name"] for t in lb])
        sel_ai_tech  = st.selectbox("Technicien à analyser", ai_tech_opts, key="ai_tech_sel")

        if st.button("🔍 Analyser ce profil", use_container_width=True, key="btn_analyze"):
            if sel_ai_tech == "— Choisir —":
                st.error("Sélectionnez un technicien")
            else:
                td        = next((t for t in lb if t["name"]==sel_ai_tech), None)
                rca_count = sum(1 for r in rca_data if r.get("responsable")==sel_ai_tech)
                blk_count = sum(1 for b in blockers_d if b.get("technicien")==sel_ai_tech and not b.get("resolu"))
                asset_ok  = any(a for a in asset_data if a.get("nom")==sel_ai_tech and a.get("soumis"))

                if td:
                    prompt = f"""Tu es un manager expert performance terrain télécom MTN Congo, plateforme FieldPerform.

Analyse le profil FLM de {sel_ai_tech} pour {period_label} :

MÉTRIQUES :
- Points : {td['total']} / {obj_pts} pts (objectif progressif) → {td['obj_pct']}%
- Cluster : {td['cluster']['label']}
- Snags : {td['n']} total | {td['closed']} fermés | {td['raised']} remontés
- Taux fermeture ML : {td['ml_pct']}%
- Snags TXN/IPRAN/MW : {td['txn_snags']} — CRITIQUE si 0
- Snags Énergie : {td['energy_snags']} | Snags RAN : {td['ran_snags']}
- Alerte fermeture : {'OUI (<30%)' if sel_ai_tech in alert_set else 'NON'}
- Chute productivité : {'OUI (≥30% vs mois préc.)' if sel_ai_tech in drop_set else 'NON'}
- RCA en charge : {rca_count} | Blocages ouverts : {blk_count}
- ASSET soumis : {'OUI' if asset_ok else 'NON'}

Produis une analyse en 4 sections (max 400 mots) :
1. **Évaluation globale** — synthèse directe
2. **Points forts** — ce qui fonctionne
3. **Axes critiques** — lacunes précises (insiste si 0 TXN ou chute)
4. **Recommandation manager** — action concrète immédiate

Ton : professionnel, factuel, bienveillant. En français."""
                else:
                    prompt = f"""{sel_ai_tech} n'a aucune donnée pour {period_label} sur FieldPerform.
Analyse cette situation et donne une recommandation manager. Max 200 mots, en français."""

                with st.spinner("FieldPerform AI analyse…"):
                    try:
                        client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
                        msg    = client.messages.create(model="claude-sonnet-4-20250514",max_tokens=600,
                                                       messages=[{"role":"user","content":prompt}])
                        st.session_state["ai_profile_result"] = msg.content[0].text
                    except Exception as e:
                        st.error(f"Erreur API : {e}")

        if "ai_profile_result" in st.session_state:
            st.html(f'<div style="background:#F9FAFB;border:1px solid #E5E7EB;border-radius:10px;padding:14px 16px;margin-top:10px;font-size:13px;line-height:1.7;color:#111827;{F}">{st.session_state["ai_profile_result"].replace(chr(10),"<br>")}</div>')

    with ai_col2:
        st.html(section_label("QUESTION LIBRE"))
        ai_question = st.text_area("Question",
            placeholder="Ex: Pourquoi Rosly n'a pas de snag TXN ?\nEx: Quels techniciens sont en danger ?\nEx: Analyse les blocages récurrents.",
            height=110, key="ai_free_q", label_visibility="collapsed")

        if st.button("💬 Envoyer", use_container_width=True, key="btn_free_ai"):
            if not ai_question.strip(): st.error("Saisissez une question")
            else:
                ctx = f"""FieldPerform · MTN Congo FLM South · {period_label} :
- {len(lb)} techniciens actifs · {round(total_pts,1)} / {obj_pts} pts
- Alertes fermeture : {', '.join(alert_set) or 'aucune'}
- Chutes productivité : {', '.join(drop_set) or 'aucune'}
- Snags retard : {len(overdue_snags)} · RCA attente : {rca_alerts}
- Blocages ouverts : {len([b for b in blockers_d if not b.get('resolu')])}
- Sans TXN : {', '.join(t['name'] for t in lb if t['txn_snags']==0) or 'aucun'}
Question : {ai_question.strip()}
Réponds en français, concis et opérationnel (max 300 mots)."""
                with st.spinner("FieldPerform AI réfléchit…"):
                    try:
                        client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
                        msg    = client.messages.create(model="claude-sonnet-4-20250514",max_tokens=500,
                                                       messages=[{"role":"user","content":ctx}])
                        st.session_state["ai_free_result"] = msg.content[0].text
                    except Exception as e:
                        st.error(f"Erreur API : {e}")

        if "ai_free_result" in st.session_state:
            st.html(f'<div style="background:#F9FAFB;border:1px solid #E5E7EB;border-radius:10px;padding:14px 16px;margin-top:10px;font-size:13px;line-height:1.7;color:#111827;{F}">{st.session_state["ai_free_result"].replace(chr(10),"<br>")}</div>')

    # Détections automatiques
    st.html(section_label("DÉTECTIONS AUTOMATIQUES — FieldPerform AI"))
    detections = []
    for t in lb:
        if t["txn_snags"]==0:
            detections.append({"type":"warn","icon":"📡","tech":t["name"],"msg":"Aucun snag TXN/IPRAN/MW — infrastructure critique non couverte ce mois"})
        if t["name"] in drop_set:
            detections.append({"type":"danger","icon":"📉","tech":t["name"],"msg":f"Chute de productivité ≥30% vs mois précédent"})
        if t["name"] in alert_set:
            detections.append({"type":"danger","icon":"🔴","tech":t["name"],"msg":f"Taux de fermeture {t['ml_pct']}% — seuil critique <30% atteint"})

    if detections:
        for d in detections:
            bg_ = "#FEF2F2" if d["type"]=="danger" else "#FFFBEB"
            bc_ = "#FECACA" if d["type"]=="danger" else "#FDE68A"
            tc_ = "#DC2626" if d["type"]=="danger" else "#92400E"
            st.html(f"""<div style="background:{bg_};border:1px solid {bc_};border-radius:8px;
                padding:8px 14px;margin-bottom:6px;display:flex;align-items:center;gap:10px;">
                <span style="font-size:16px;">{d['icon']}</span>
                <div><span style="font-size:12px;font-weight:700;color:{tc_};{F}">{d['tech']}</span>
                <span style="font-size:11px;color:#6B7280;{F}"> — {d['msg']}</span></div>
            </div>""")
    else:
        st.html(f"""<div style="background:#F0FDF4;border:1px solid #BBF7D0;border-radius:8px;
            padding:12px 16px;text-align:center;">
            <div style="font-size:12px;color:#166534;font-weight:700;{F}">
                ✅ Aucune anomalie détectée pour {period_label}
            </div>
        </div>""")
