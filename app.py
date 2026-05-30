# ════════════════════════════════════════════════════════════════
#  FieldPerform — MTN FLM Performance Platform  v6.2
#  Nouveau scoring : ouverture symbolique + fermeture selon délai
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
    GLOBAL_CSS, F, MONTHS_FR, CATEGORIES, SUB_SCORES, OPEN_PTS,
    CLOSE_FACTORS, ACTION_LABEL, ACTION_COLOR,
    calc_pts, calc_open_pts, calc_close_pts,
    get_close_factor_key, obj_for_month, obj_color, obj_bar_html,
    delay_badge_html, kpi_card, section_label, badge,
    status_badge_rca, status_badge_snag, get_cluster, get_perf_status,
)

st.set_page_config(page_title="FieldPerform · MTN FLM", page_icon="⚡",
                   layout="wide", initial_sidebar_state="expanded")
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
            <div style="font-size:16px;font-weight:800;color:#111827;{F}">FieldPerform</div>
            <div style="font-size:10px;color:#9CA3AF;{F}">SOUTH REGION · v6.2</div>
        </div>
    </div><div style="height:1px;background:#E5E7EB;margin-bottom:16px;"></div>""")

    col_m, col_y = st.columns(2)
    with col_m:
        sel_m = st.selectbox("Mois", range(1,13),
                             format_func=lambda x: MONTHS_FR[x-1],
                             index=CUR_M-1, label_visibility="collapsed")
    with col_y:
        sel_y = st.selectbox("Année",[2024,2025,2026,2027],
                             index=[2024,2025,2026,2027].index(CUR_Y),
                             label_visibility="collapsed")

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

    st.html(f"""<div style="background:#EEF2FF;border:1px solid #C7D2FE;border-radius:8px;
        padding:8px 12px;margin:8px 0;font-size:10px;color:#3730A3;{F}">
        <strong>Scoring v6.2 :</strong><br>
        Ouverture = pts symboliques<br>
        Fermeture ≤3j = ×1.5 🏆<br>
        Fermeture 4–7j = ×1.0 ✅<br>
        Fermeture 8–14j = ×0.6 ⚠<br>
        Fermeture >14j = ×0.3 🔴
    </div>""")
    st.html(f'<div style="height:1px;background:#E5E7EB;margin:12px 0;"></div>')
    st.html(f'<div style="font-size:10px;color:#9CA3AF;text-align:center;{F}">FieldPerform · Supabase</div>')

# ════════════════ DONNÉES ════════════════
@st.cache_data(ttl=30, show_spinner=False)
def load_techs_c(): return fetch_techs()
@st.cache_data(ttl=30, show_spinner=False)
def load_snags_c(y,m): return fetch_snags_manager(y,m)
@st.cache_data(ttl=30, show_spinner=False)
def load_rca_c(y,m): return fetch_rca(y,m)
@st.cache_data(ttl=30, show_spinner=False)
def load_asset_c(y,m): return fetch_asset(y,m)
@st.cache_data(ttl=30, show_spinner=False)
def load_blockers_c(y,m): return fetch_blockers(y,m)

techs_list = load_techs_c()
techs_noms = [t["nom"] for t in techs_list]
snags_data = load_snags_c(sel_y, sel_m)
rca_data   = load_rca_c(sel_y, sel_m)
asset_data = load_asset_c(sel_y, sel_m)
blockers_d = load_blockers_c(sel_y, sel_m)

# ── Leaderboard avec nouveau scoring ────────────────────────────
def build_leaderboard(snags):
    if not snags: return []
    df  = pd.DataFrame(snags)
    lb  = []
    for tech in df["technicien"].unique():
        td      = df[df["technicien"]==tech]
        n       = len(td)
        # Points selon nouveau système
        total   = round(td["points"].sum(), 1)
        # Stats fermeture
        closed_rows = td[td["action"].isin(["closed","both"])]
        opened_rows = td[td["action"].isin(["raised","both"])]
        n_closed = len(closed_rows)
        n_opened = len(opened_rows) + len(td[td["action"]=="raised"])
        # Délai moyen de fermeture
        delays = td["days_to_close"].dropna().tolist() if "days_to_close" in td.columns else []
        avg_delay = round(sum(delays)/len(delays),1) if delays else None
        # Taux de fermeture
        close_rate = round(n_closed/n*100,1) if n else 0
        # Catégories
        txn  = int(td["categorie"].isin(["TXN","IPRAN","MW_FADING","MW_EQUIPMENT"]).sum())
        egy  = int(td["categorie"].isin(["DG","Battery","Rectifier","ATS","ENERGY_OTHER"]).sum())
        ran  = int(td["categorie"].isin(["RAN","ANTENNA","FEEDER","BTS_HW","BTS_SW"]).sum())
        lb.append({
            "name":tech,"total":total,"n":n,
            "n_closed":n_closed,"n_opened":n,
            "close_rate":close_rate,"avg_delay":avg_delay,
            "txn_snags":txn,"energy_snags":egy,"ran_snags":ran,
        })
    lb.sort(key=lambda x: -x["total"])
    for i,t in enumerate(lb):
        t["rank"] = i+1
        pct = round(t["total"]/obj_pts*100,1) if obj_pts else 0
        t["obj_pct"]  = pct
        t["cluster"]  = get_cluster(pct)
        t["perf_st"]  = get_perf_status(t["close_rate"], t["avg_delay"])
    return lb

lb        = build_leaderboard(snags_data)
total_pts = round(sum(t["total"] for t in lb), 1)
mid_month = (now.day >= 15) if is_current_period else True
# Alerte si taux fermeture < 50% après mi-mois
alert_set = {t["name"] for t in lb if t["close_rate"] < 50 and mid_month}
drop_set  = set()
for t in lb:
    hist = fetch_snags_6months(t["name"])
    if len(hist) >= 2:
        hdf = pd.DataFrame(hist)
        hdf["ym"] = hdf["annee"]*100+hdf["mois"]
        monthly = hdf.groupby("ym")["points"].sum().sort_index()
        vals = list(monthly.values)
        if len(vals)>=2 and vals[-2]>0 and (vals[-2]-vals[-1])/vals[-2]>=0.30:
            drop_set.add(t["name"])

# Snags en retard
overdue_snags = []
if snags_data:
    for s in snags_data:
        if s.get("action") in ["raised","both"] and not s.get("date_ferme"):
            d0   = date.fromisoformat(str(s["date_snag"]))
            diff = (TODAY - d0).days
            if diff > 7:
                overdue_snags.append({**s,"days_open":diff})

rca_alerts = sum(
    1 for r in rca_data if not r.get("date_rca") and
    (datetime.now()-datetime.fromisoformat(str(r["date_incident"]).replace("Z",""))).total_seconds()/3600 >= 48
)

asset_dline   = date(sel_y, sel_m, 20)
days_to_asset = (asset_dline - TODAY).days
pending_asset = sum(1 for a in asset_data if not a.get("soumis"))

# ════════════════ HEADER ════════════════
n_alerts = len(alert_set) + rca_alerts + len(overdue_snags)
ac = "#DC2626" if n_alerts else "#10B981"

st.html(f"""<div style="background:linear-gradient(135deg,#111827,#1F2937);
    border-radius:14px;padding:18px 24px;margin-bottom:14px;">
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;">
        <div>
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">
                <span style="background:#FFD200;color:#111827;font-size:12px;font-weight:800;
                    padding:3px 10px;border-radius:6px;{F}">MTN</span>
                <span style="font-size:24px;font-weight:800;color:#FFFFFF;{F}">FieldPerform</span>
                <span style="font-size:10px;color:#6B7280;background:#374151;
                    padding:3px 8px;border-radius:6px;{F}">v6.2</span>
            </div>
            <div style="font-size:12px;color:#9CA3AF;{F}">
                {period_label} · South Region · Objectif : {obj_pts} pts
            </div>
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
            <div style="background:{ac}22;border:1px solid {ac}55;border-radius:8px;
                padding:6px 14px;font-size:11px;color:{ac};font-weight:700;{F}">
                {'⚠ ' if n_alerts else '✓ '}{n_alerts} alerte{'s' if n_alerts!=1 else ''}
            </div>
            <div style="background:#374151;border-radius:8px;padding:6px 14px;
                font-size:11px;color:#D1D5DB;font-weight:600;{F}">
                {len(lb)} tech · {total_pts} pts
            </div>
        </div>
    </div>
</div>""")

# ════════════════ ONGLETS ════════════════
(tab_overview, tab_class, tab_bareme, tab_techs,
 tab_snags, tab_mgmt, tab_blockers, tab_trend, tab_ai) = st.tabs([
    "📊 Vue globale","🏆 Classement","📋 Barème",
    "👷 Techniciens","🔧 Snags","📄 RCA & ASSET",
    "🚧 Blocages","📈 Tendances 6 mois","🤖 Analyse IA",
])

# ══════════════════════════════════════════════════════════════════
#  TAB 1 — VUE GLOBALE
# ══════════════════════════════════════════════════════════════════
with tab_overview:
    c1,c2,c3,c4,c5 = st.columns(5)
    avg_rate = round(sum(t["close_rate"] for t in lb)/len(lb),1) if lb else 0
    c1.html(kpi_card("Tickets ouverts",
                     str(sum(t["n"] for t in lb)),f"{period_label}"))
    c2.html(kpi_card("Tickets fermés",
                     str(sum(t["n_closed"] for t in lb)),
                     "ce mois","#10B981"))
    c3.html(kpi_card("Taux fermeture équipe",f"{avg_rate}%",
                     "objectif ≥ 80%",
                     "#10B981" if avg_rate>=80 else "#F59E0B" if avg_rate>=50 else "#EF4444"))
    c4.html(kpi_card("Points équipe",str(total_pts),
                     f"obj. {obj_pts} pts","#D97706"))
    c5.html(kpi_card("Alertes actives",str(n_alerts),
                     "fermeture+RCA+retard",
                     "#EF4444" if n_alerts else "#10B981"))

    # Progression équipe
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
            <div style="font-size:11px;color:#9CA3AF;{F}">{total_pts} pts · taux fermeture équipe : {avg_rate}%</div>
            <div style="font-size:11px;color:#9CA3AF;{F}">Objectif : {obj_pts} pts</div>
        </div>
    </div>""")

    # Tableau individuel
    if lb:
        st.html(section_label("PERFORMANCE INDIVIDUELLE — OUVERTURE & FERMETURE"))
        for t in lb:
            t_pct   = t["obj_pct"]
            t_col   = obj_color(t_pct)
            is_alrt = t["name"] in alert_set
            is_drop = t["name"] in drop_set
            no_txn  = t["txn_snags"] == 0
            ps      = t["perf_st"]
            bdr     = f"border:1.5px solid {ps['border']};"
            bg      = f"background:{ps['bg']}22;"
            medal   = "🥇" if t["rank"]==1 else "🥈" if t["rank"]==2 else "🥉" if t["rank"]==3 else f"#{t['rank']}"
            tags = ""
            if is_drop: tags += f"<span style='background:#FEF3C7;color:#92400E;font-size:9px;font-weight:700;border-radius:4px;padding:2px 6px;{F}'>📉 Chute</span>&nbsp;"
            if no_txn:  tags += f"<span style='background:#EEF2FF;color:#3730A3;font-size:9px;font-weight:700;border-radius:4px;padding:2px 6px;{F}'>0 TXN</span>&nbsp;"
            delay_str = f"délai moy. {t['avg_delay']}j" if t['avg_delay'] else "aucune fermeture"
            st.html(f"""<div style="{bg}{bdr}border-radius:10px;padding:10px 14px;margin-bottom:6px;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                    <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
                        <span style="font-size:13px;font-weight:700;color:{ps['color']};{F}">{ps['icon']} {medal} {t['name']}</span>
                        <span style="background:{ps['bg']};color:{ps['color']};border:1px solid {ps['border']};
                            font-size:9px;font-weight:700;border-radius:20px;padding:2px 7px;{F}">{ps['label']}</span>
                        {tags}
                    </div>
                    <div style="display:flex;align-items:center;gap:14px;">
                        <span style="font-size:11px;color:#9CA3AF;{F}">{t['total']} pts · {t['n_closed']}/{t['n']} fermés</span>
                        <span style="font-size:14px;font-weight:800;color:{ps['color']};{F}">{t['close_rate']}%</span>
                    </div>
                </div>
                {obj_bar_html(t['close_rate'], 8)}
                <div style="font-size:10px;color:#9CA3AF;margin-top:4px;{F}">
                    Score : {t['total']} pts · {delay_str}
                    · TXN:{t['txn_snags']} · Énergie:{t['energy_snags']} · RAN:{t['ran_snags']}
                </div>
            </div>""")

        # Graphiques
        cl, cr = st.columns([3,2])
        with cl:
            st.html(section_label("TICKETS OUVERTS vs FERMÉS"))
            fig = go.Figure()
            names = [t["name"] for t in lb]
            fig.add_trace(go.Bar(
                name="Ouverts", y=names, x=[t["n"] for t in lb],
                orientation="h", marker_color="#B5D4F4", marker_line_width=0,
            ))
            fig.add_trace(go.Bar(
                name="Fermés", y=names, x=[t["n_closed"] for t in lb],
                orientation="h", marker_color="#10B981", marker_line_width=0,
            ))
            fig.update_layout(
                barmode="overlay", paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="#FAFAFA", height=max(280,len(lb)*52),
                margin=dict(l=10,r=40,t=6,b=6),
                xaxis=dict(gridcolor="#F1F5F9",tickfont=dict(size=10,family="Plus Jakarta Sans")),
                yaxis=dict(gridcolor="rgba(0,0,0,0)",
                           tickfont=dict(size=11,family="Plus Jakarta Sans",weight="bold"),
                           autorange="reversed"),
                legend=dict(font=dict(size=11,family="Plus Jakarta Sans"),
                            bgcolor="rgba(255,255,255,.9)",bordercolor="#E5E7EB",borderwidth=1),
                bargap=0.3,
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

        with cr:
            st.html(section_label("TAUX DE FERMETURE PAR TECH."))
            rate_colors = ["#10B981" if t["close_rate"]>=70 else "#F59E0B" if t["close_rate"]>=50 else "#EF4444" for t in lb]
            fig2 = go.Figure(go.Bar(
                x=[t["close_rate"] for t in lb],
                y=[t["name"] for t in lb],
                orientation="h",
                marker_color=rate_colors, marker_line_width=0,
                text=[f"{t['close_rate']}%" for t in lb],
                textposition="outside",
                textfont=dict(size=11,family="Plus Jakarta Sans"),
            ))
            fig2.add_vline(x=50, line_dash="dash", line_color="#EF4444", line_width=1.5,
                           annotation_text="Seuil alerte 50%",
                           annotation_font=dict(size=9,color="#EF4444",family="Plus Jakarta Sans"))
            fig2.add_vline(x=80, line_dash="dot", line_color="#10B981", line_width=1,
                           annotation_text="Objectif 80%",
                           annotation_font=dict(size=9,color="#10B981",family="Plus Jakarta Sans"))
            fig2.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#FAFAFA",
                height=max(280,len(lb)*52), margin=dict(l=10,r=80,t=6,b=6),
                xaxis=dict(gridcolor="#F1F5F9",range=[0,120],ticksuffix="%",
                           tickfont=dict(size=10,family="Plus Jakarta Sans")),
                yaxis=dict(gridcolor="rgba(0,0,0,0)",
                           tickfont=dict(size=11,family="Plus Jakarta Sans",weight="bold"),
                           autorange="reversed"),
                showlegend=False, bargap=0.3,
            )
            st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar":False})


# ══════════════════════════════════════════════════════════════════
#  TAB 2 — CLASSEMENT
# ══════════════════════════════════════════════════════════════════
with tab_class:
    if not lb:
        st.html(f"""<div style="background:#F9FAFB;border:2px dashed #E5E7EB;border-radius:12px;
            padding:50px;text-align:center;">
            <div style="font-size:13px;color:#9CA3AF;{F}">Aucune donnée pour {period_label}</div>
        </div>""")
    else:
        # Podium
        if len(lb) >= 2:
            pod    = [lb[1], lb[0]] + ([lb[2]] if len(lb)>2 else [])
            h_map  = {1:160,2:120,3:90}
            mc_map = {1:"🥇",2:"🥈",3:"🥉"}
            pod_html = '<div style="display:flex;justify-content:center;align-items:flex-end;gap:16px;margin-bottom:28px;padding:20px;">'
            for t in pod:
                r  = t["rank"]
                ps = t["perf_st"]
                pod_html += f"""<div style="text-align:center;width:150px;">
                    <div style="font-size:28px;margin-bottom:4px;">{mc_map[r]}</div>
                    <div style="font-size:13px;font-weight:700;color:#111827;{F}">{t['name']}</div>
                    <div style="font-size:18px;font-weight:800;color:{ps['color']};margin:4px 0;{F}">{t['total']} pts</div>
                    <div style="font-size:11px;color:#9CA3AF;{F}">{t['close_rate']}% fermeture</div>
                    <div style="font-size:11px;color:#9CA3AF;margin-bottom:8px;{F}">{t['obj_pct']}% objectif</div>
                    <div style="height:{h_map[r]}px;background:{ps['bg']};border:2px solid {ps['border']};
                        border-radius:12px 12px 0 0;display:flex;align-items:flex-end;
                        justify-content:center;padding-bottom:12px;">
                        <div style="font-size:28px;font-weight:800;color:{ps['color']};{F}">{r}</div>
                    </div>
                </div>"""
            pod_html += '</div>'
            st.html(pod_html)

        st.html(section_label(f"CLASSEMENT COMPLET — {period_label}"))
        hdr = st.columns([0.4,2,0.7,0.7,0.8,0.8,0.8,0.8,1.3])
        for col,h in zip(hdr,["#","TECHNICIEN","PTS","% OBJ","OUVERTS","FERMÉS","TAUX","DÉL. MOY","STATUT"]):
            col.markdown(f"<div style='font-size:9px;font-weight:700;color:#9CA3AF;letter-spacing:.06em;text-transform:uppercase;padding:6px 0;{F}'>{h}</div>",unsafe_allow_html=True)

        for t in lb:
            is_drop = t["name"] in drop_set
            no_txn  = t["txn_snags"] == 0
            ps      = t["perf_st"]
            row     = st.columns([0.4,2,0.7,0.7,0.8,0.8,0.8,0.8,1.3])
            medal   = "🥇" if t["rank"]==1 else "🥈" if t["rank"]==2 else "🥉" if t["rank"]==3 else f"#{t['rank']}"
            bg_row  = f"background:{ps['bg']}22;"

            row[0].markdown(f"<div style='padding:10px 0;font-size:11px;color:#9CA3AF;{bg_row}{F}'>{medal}</div>",unsafe_allow_html=True)
            name_extra = (" 📉" if is_drop else "") + (" 📡" if no_txn else "")
            row[1].markdown(f"<div style='padding:10px 0;font-size:12px;font-weight:700;color:{ps['color']};{bg_row}{F}'>{t['name']}{name_extra}</div>",unsafe_allow_html=True)
            row[2].markdown(f"<div style='padding:10px 0;font-size:14px;font-weight:800;color:#D97706;text-align:center;{bg_row}{F}'>{t['total']}</div>",unsafe_allow_html=True)
            t_col = obj_color(t["obj_pct"])
            row[3].markdown(f"<div style='padding:10px 0;font-size:13px;font-weight:700;color:{t_col};text-align:center;{bg_row}{F}'>{t['obj_pct']}%</div>",unsafe_allow_html=True)
            row[4].markdown(f"<div style='padding:10px 0;font-size:12px;color:#374151;text-align:center;{bg_row}{F}'>{t['n']}</div>",unsafe_allow_html=True)
            row[5].markdown(f"<div style='padding:10px 0;font-size:12px;color:#10B981;font-weight:700;text-align:center;{bg_row}{F}'>{t['n_closed']}</div>",unsafe_allow_html=True)
            rate_col = "#10B981" if t["close_rate"]>=70 else "#F59E0B" if t["close_rate"]>=50 else "#DC2626"
            row[6].markdown(f"<div style='padding:10px 0;font-size:13px;font-weight:700;color:{rate_col};text-align:center;{bg_row}{F}'>{t['close_rate']}%</div>",unsafe_allow_html=True)
            delay_str = f"{t['avg_delay']}j" if t['avg_delay'] else "—"
            delay_col = "#10B981" if t['avg_delay'] and t['avg_delay']<=7 else "#F59E0B" if t['avg_delay'] and t['avg_delay']<=14 else "#EF4444"
            row[7].markdown(f"<div style='padding:10px 0;font-size:12px;font-weight:600;color:{delay_col};text-align:center;{bg_row}{F}'>{delay_str}</div>",unsafe_allow_html=True)
            ps_bg = ps['bg']; ps_co = ps['color']; ps_bd = ps['border']; ps_lb = ps['label']; ps_ic = ps['icon']
            row[8].html(f"<div style='padding:8px 0;{bg_row}'><span style='background:{ps_bg};color:{ps_co};border:1px solid {ps_bd};font-size:10px;font-weight:700;border-radius:20px;padding:3px 9px;{F}'>{ps_ic} {ps_lb}</span></div>")
            st.html('<div style="height:1px;background:#F3F4F6;"></div>')

        # Graphique taux fermeture
        st.html('<div style="height:16px;"></div>')
        st.html(section_label("TAUX DE FERMETURE — VUE GLOBALE"))
        ml_df = pd.DataFrame([{"Technicien":t["name"],"Taux (%)":t["close_rate"],"Statut":t["perf_st"]["label"]} for t in lb])
        fig_ml = px.bar(ml_df, x="Taux (%)", y="Technicien", orientation="h", color="Statut",
                        color_discrete_map={"Elite":"#D97706","Performant":"#10B981",
                                            "En progression":"#F59E0B","Alerte":"#EF4444"},
                        text="Taux (%)")
        fig_ml.add_vline(x=50, line_dash="dash", line_color="#EF4444", line_width=1.5,
                         annotation_text="Seuil alerte 50%",
                         annotation_font=dict(size=9,color="#EF4444",family="Plus Jakarta Sans"))
        fig_ml.add_vline(x=80, line_dash="dot", line_color="#10B981", line_width=1,
                         annotation_text="Objectif 80%",
                         annotation_font=dict(size=9,color="#10B981",family="Plus Jakarta Sans"))
        fig_ml.update_traces(texttemplate="%{text}%", textposition="outside", marker_line_width=0)
        fig_ml.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#FAFAFA",
            height=max(260,len(lb)*44), margin=dict(l=0,r=80,t=8,b=8),
            xaxis=dict(gridcolor="#F3F4F6",range=[0,120],ticksuffix="%",
                       tickfont=dict(size=10,family="Plus Jakarta Sans")),
            yaxis=dict(gridcolor="rgba(0,0,0,0)",
                       tickfont=dict(size=12,family="Plus Jakarta Sans"),autorange="reversed"),
            legend=dict(font=dict(size=11,family="Plus Jakarta Sans"),bgcolor="rgba(0,0,0,0)"),
        )
        st.plotly_chart(fig_ml, use_container_width=True, config={"displayModeBar":False})

        # Légende statuts
        st.html(f"""<div style="background:#F9FAFB;border:1px solid #E5E7EB;border-radius:10px;
            padding:14px 18px;margin-top:8px;">
            <div style="font-size:10px;font-weight:700;color:#9CA3AF;letter-spacing:.08em;
                text-transform:uppercase;margin-bottom:10px;{F}">LÉGENDE STATUTS</div>
            <div style="display:flex;flex-wrap:wrap;gap:10px;margin-bottom:10px;">
                <span style="background:#FFFBEB;color:#D97706;border:1px solid #FDE68A;font-size:11px;font-weight:700;border-radius:20px;padding:4px 12px;{F}">🏆 Elite — ≥85% fermeture + délai ≤7j</span>
                <span style="background:#EAF3DE;color:#3B6D11;border:1px solid #C0DD97;font-size:11px;font-weight:700;border-radius:20px;padding:4px 12px;{F}">⭐ Performant — ≥70% fermeture</span>
                <span style="background:#FEF3C7;color:#BA7517;border:1px solid #FDE68A;font-size:11px;font-weight:700;border-radius:20px;padding:4px 12px;{F}">📈 En progression — ≥50%</span>
                <span style="background:#FEE2E2;color:#DC2626;border:1px solid #FECACA;font-size:11px;font-weight:700;border-radius:20px;padding:4px 12px;{F}">🔴 Alerte — &lt;50% fermeture</span>
            </div>
            <div style="font-size:11px;color:#6B7280;line-height:1.9;{F}">
                <strong style="color:#374151;">Formule score : </strong>Σ(pts ouverture symboliques) + Σ(base × facteur délai)<br>
                <strong style="color:#374151;">Facteurs : </strong>≤3j ×1.5 🏆 · 4–7j ×1.0 ✅ · 8–14j ×0.6 ⚠ · >14j ×0.3 🔴 · non fermé = 0<br>
                <strong style="color:#374151;">Points ouverture : </strong>TXN/IPRAN/RAN = 1pt · Autres = 0.5pt (symbolique uniquement)<br>
                <strong style="color:#EF4444;">📡 0 TXN = signal d'alerte</strong> · <strong style="color:#92400E;">📉 Chute = baisse ≥30% vs mois précédent</strong>
            </div>
        </div>""")


# ══════════════════════════════════════════════════════════════════
#  TAB 3 — BARÈME
# ══════════════════════════════════════════════════════════════════
with tab_bareme:
    st.html(section_label("NOUVEAU SYSTÈME DE SCORING — OUVERTURE + FERMETURE"))

    # Cartes facteurs
    rc1,rc2,rc3,rc4,rc5 = st.columns(5)
    facteur_cards = [
        ("↑ Ouverture","Symbolique","TXN:1pt · Autres:0.5pt","#EEF2FF","#3730A3","#C7D2FE"),
        ("≤ 3j — Fermé","× 1.5","Bonus rapidité","#FFFBEB","#D97706","#FDE68A"),
        ("4–7j — Fermé","× 1.0","Dans les délais","#EAF3DE","#3B6D11","#C0DD97"),
        ("8–14j — Fermé","× 0.6","Retard modéré","#FEF3C7","#BA7517","#FDE68A"),
        (">14j — Fermé","× 0.3","Retard grave","#FEE2E2","#DC2626","#FECACA"),
    ]
    for col_,(titre,val,sub,bg_,ct,bdr) in zip([rc1,rc2,rc3,rc4,rc5],facteur_cards):
        col_.html(f"""<div style="background:{bg_};border:1.5px solid {bdr};border-radius:10px;
            padding:14px;text-align:center;margin-bottom:12px;">
            <div style="font-size:11px;font-weight:700;color:{ct};{F}">{titre}</div>
            <div style="font-size:26px;font-weight:800;color:{ct};margin:6px 0;{F}">{val}</div>
            <div style="font-size:10px;color:{ct};opacity:.8;{F}">{sub}</div>
        </div>""")

    st.html(f"""<div style="background:#F9FAFB;border:1px solid #E5E7EB;border-radius:10px;
        padding:14px 18px;margin-bottom:20px;">
        <div style="font-size:12px;color:#6B7280;line-height:2;{F}">
            <strong style="color:#374151;">Formule : </strong>Score = Pts ouverture + (Base catégorie × Facteur délai fermeture)<br>
            <strong style="color:#374151;">Exemple TXN fermé en 5j : </strong>1 pt (ouv.) + 8 × 1.0 = <strong style="color:#D97706;">9.0 pts ✅</strong><br>
            <strong style="color:#374151;">Exemple TXN fermé en 2j : </strong>1 pt (ouv.) + 8 × 1.5 = <strong style="color:#D97706;">13.0 pts 🏆 (bonus rapidité)</strong><br>
            <strong style="color:#374151;">Exemple TXN fermé en 20j : </strong>1 pt (ouv.) + 8 × 0.3 = <strong style="color:#EF4444;">3.4 pts 🔴 (−5.6 pts vs délai normal)</strong><br>
            <strong style="color:#374151;">Exemple TXN non fermé : </strong>1 pt (ouv.) + 0 = <strong style="color:#9CA3AF;">1.0 pt ❌ (symbolique seulement)</strong>
        </div>
    </div>""")

    # Simulateur
    st.html(section_label("🧮 SIMULATEUR DE POINTS"))
    sim1,sim2,sim3 = st.columns([2,2,1])
    with sim1:
        sim_cat = st.selectbox("Catégorie", CATEGORIES,
                               format_func=lambda x:f"{x}  (base {SUB_SCORES[x]} pts)",
                               key="sim_cat_v2")
    with sim2:
        sim_act = st.selectbox("Action",["raised","closed_fast","closed_normal","closed_late1","closed_late2"],
                               format_func=lambda x:{
                                   "raised":"↑ Ouverture seulement",
                                   "closed_fast":"✓ Fermé ≤ 3j (×1.5)",
                                   "closed_normal":"✓ Fermé 4–7j (×1.0)",
                                   "closed_late1":"✓ Fermé 8–14j (×0.6)",
                                   "closed_late2":"✓ Fermé >14j (×0.3)",
                               }[x], key="sim_act_v2")
    with sim3:
        delay_map = {"raised":None,"closed_fast":2,"closed_normal":5,
                     "closed_late1":10,"closed_late2":20}
        d = delay_map[sim_act]
        open_p = calc_open_pts(sim_cat)
        close_p = calc_close_pts(sim_cat, d) if d is not None else 0
        total_sim = round(open_p + close_p, 2)
        cf_key = get_close_factor_key(d) if d is not None else "none"
        cf = CLOSE_FACTORS[cf_key]
        st.html(f"""<div style="background:{cf['bg']};border:2px solid {cf['border']};
            border-radius:10px;padding:14px;text-align:center;margin-top:4px;">
            <div style="font-size:10px;color:{cf['color']};font-weight:700;{F}">POINTS</div>
            <div style="font-size:36px;font-weight:800;color:{cf['color']};{F}">{total_sim}</div>
            <div style="font-size:10px;color:#9CA3AF;{F}">{open_p} ouv. + {close_p} ferm.</div>
        </div>""")

    # Tableau barème par catégorie
    st.html(section_label("POINTS BASE PAR CATÉGORIE — 28 CATÉGORIES"))
    groups = {
        "📡 TRANSMISSION":  ["TXN","IPRAN","MW_FADING","MW_EQUIPMENT"],
        "📶 RAN / RADIO":   ["RAN","ANTENNA","FEEDER","BTS_HW","BTS_SW","PARAMETER"],
        "⚡ ÉNERGIE":       ["DG","Battery","Rectifier","ATS","ENERGY_OTHER"],
        "🏗 CIVIL / ACCÈS": ["ACCESS","CIVIL","SECURITY","POWER_CABLE","EARTHING"],
        "❄ INFRASTRUCTURE":["COOLING","SHELTER","FIBER","SWITCH","ROUTER"],
        "🔧 AUTRES":        ["TRANSPORT","MONITORING","OTHER"],
    }
    bcs = ["#6366F1","#10B981","#FFD200","#F59E0B","#14B8A6","#8B5CF6"]
    for gi,(grp_name,cats) in enumerate(groups.items()):
        gc = bcs[gi%len(bcs)]
        st.html(f'<div style="font-size:11px;font-weight:700;color:{gc};letter-spacing:.05em;margin:14px 0 6px;{F}">{grp_name}</div>')
        cols = st.columns(len(cats))
        for col_,cat in zip(cols,cats):
            base   = SUB_SCORES[cat]
            op_pts = OPEN_PTS[cat]
            col_.html(f"""<div style="background:#FFFFFF;border:1px solid #E5E7EB;
                border-radius:8px;padding:10px 8px;text-align:center;margin-bottom:4px;">
                <div style="font-size:10px;font-weight:700;color:#374151;margin-bottom:4px;
                    overflow:hidden;text-overflow:ellipsis;white-space:nowrap;{F}">{cat}</div>
                <div style="font-size:20px;font-weight:800;color:{gc};{F}">{base}</div>
                <div style="font-size:9px;color:#9CA3AF;{F}">base ferm.</div>
                <div style="height:1px;background:#F3F4F6;margin:5px 0;"></div>
                <div style="font-size:9px;color:#6B7280;{F}">ouv.={op_pts}</div>
                <div style="font-size:9px;color:#10B981;{F}">≤3j={round(base*1.5,1)}</div>
                <div style="font-size:9px;color:#3B6D11;{F}">4-7j={base}</div>
                <div style="font-size:9px;color:#BA7517;{F}">8-14j={round(base*.6,1)}</div>
                <div style="font-size:9px;color:#DC2626;{F}">>14j={round(base*.3,1)}</div>
            </div>""")


# ══════════════════════════════════════════════════════════════════
#  TAB 4 — TECHNICIENS
# ══════════════════════════════════════════════════════════════════
with tab_techs:
    st.html(section_label("AJOUTER UN TECHNICIEN"))
    with st.form("form_add_tech", clear_on_submit=True):
        ca1,ca2,ca3,ca4 = st.columns([3,2,2,1])
        with ca1: new_nom    = st.text_input("Nom complet",placeholder="Prénom NOM…")
        with ca2: new_region = st.selectbox("Région",["South","Brazzaville","Pool","Nord","Dolisie","Autre"])
        with ca3: new_equipe = st.selectbox("Équipe",["FLM","FME","NOC","Back Office","Sous-traitant"])
        with ca4:
            st.markdown("<br>",unsafe_allow_html=True)
            add_btn = st.form_submit_button("✚ Ajouter",use_container_width=True)
        if add_btn:
            if not new_nom.strip(): st.error("Nom requis")
            elif new_nom.strip().lower() in [t.lower() for t in techs_noms]: st.error("Déjà existant")
            else:
                if add_tech(new_nom.strip(),new_region,new_equipe):
                    st.success(f"✓ {new_nom.strip()} ajouté")
                    st.cache_data.clear(); st.rerun()

    st.html(section_label(f"LISTE DES TECHNICIENS ({len(techs_list)})"))
    if not techs_list:
        st.html(f"""<div style="background:#F9FAFB;border:2px dashed #E5E7EB;border-radius:10px;
            padding:40px;text-align:center;">
            <div style="font-size:13px;color:#9CA3AF;{F}">Aucun technicien. Ajoutez votre équipe ci-dessus.</div>
        </div>""")
    else:
        hdr_t = st.columns([0.4,2.2,1.2,1.2,1,0.8,0.8,0.8,0.8])
        for col,h in zip(hdr_t,["#","NOM","RÉGION","ÉQUIPE","PTS","OUVERTS","FERMÉS","TAUX",""]):
            col.markdown(f"<div style='font-size:10px;font-weight:700;color:#9CA3AF;letter-spacing:.06em;text-transform:uppercase;{F}'>{h}</div>",unsafe_allow_html=True)
        active_map = {t["name"]:t for t in lb}
        for i,tech in enumerate(techs_list):
            t   = active_map.get(tech["nom"])
            row = st.columns([0.4,2.2,1.2,1.2,1,0.8,0.8,0.8,0.8])
            ps  = t["perf_st"] if t else None
            is_alrt = tech["nom"] in alert_set
            row[0].markdown(f"<div style='padding:8px 0;font-size:11px;color:#9CA3AF;{F}'>{i+1}</div>",unsafe_allow_html=True)
            nc = ps["color"] if ps else ("#DC2626" if is_alrt else "#111827")
            row[1].markdown(f"<div style='padding:8px 0;font-size:12px;font-weight:700;color:{nc};{F}'>{ps['icon']+' ' if ps else ''}{tech['nom']}</div>",unsafe_allow_html=True)
            row[2].markdown(f"<div style='padding:8px 0;font-size:11px;color:#6B7280;{F}'>{tech['region']}</div>",unsafe_allow_html=True)
            row[3].markdown(f"<div style='padding:8px 0;font-size:11px;color:#6B7280;{F}'>{tech['equipe']}</div>",unsafe_allow_html=True)
            if t:
                rate_c = "#10B981" if t["close_rate"]>=70 else "#F59E0B" if t["close_rate"]>=50 else "#DC2626"
                row[4].markdown(f"<div style='padding:8px 0;font-size:13px;font-weight:800;color:#D97706;{F}'>{t['total']}</div>",unsafe_allow_html=True)
                row[5].markdown(f"<div style='padding:8px 0;font-size:12px;color:#374151;text-align:center;{F}'>{t['n']}</div>",unsafe_allow_html=True)
                row[6].markdown(f"<div style='padding:8px 0;font-size:12px;color:#10B981;font-weight:700;text-align:center;{F}'>{t['n_closed']}</div>",unsafe_allow_html=True)
                row[7].markdown(f"<div style='padding:8px 0;font-size:12px;font-weight:700;color:{rate_c};text-align:center;{F}'>{t['close_rate']}%</div>",unsafe_allow_html=True)
            else:
                for c_ in [row[4],row[5],row[6],row[7]]: c_.markdown(f"<div style='color:#D1D5DB;padding:8px 0;text-align:center;{F}'>—</div>",unsafe_allow_html=True)
            with row[8]:
                sb1,sb2 = st.columns(2)
                with sb1:
                    if st.button("✎",key=f"ren_{tech['id']}"): st.session_state[f"renaming_{tech['id']}"]=True
                with sb2:
                    if st.button("✕",key=f"del_{tech['id']}"): delete_tech(tech["id"]); st.cache_data.clear(); st.rerun()
            if st.session_state.get(f"renaming_{tech['id']}"):
                with st.form(f"ren_{tech['id']}"):
                    rn1,rn2,rn3,rn4 = st.columns([2.5,1.5,1.5,0.8])
                    new_rnom = rn1.text_input("Nom",value=tech["nom"],label_visibility="collapsed")
                    reg_opts = ["South","Brazzaville","Pool","Nord","Dolisie","Autre"]
                    eq_opts  = ["FLM","FME","NOC","Back Office","Sous-traitant"]
                    new_rreg = rn2.selectbox("Région",reg_opts,
                                             index=reg_opts.index(tech["region"]) if tech["region"] in reg_opts else 0,
                                             label_visibility="collapsed")
                    new_req  = rn3.selectbox("Équipe",eq_opts,
                                             index=eq_opts.index(tech["equipe"]) if tech["equipe"] in eq_opts else 0,
                                             label_visibility="collapsed")
                    if rn4.form_submit_button("✓"):
                        update_tech(tech["id"],new_rnom.strip(),new_rreg,new_req)
                        st.session_state[f"renaming_{tech['id']}"]=False
                        st.cache_data.clear(); st.rerun()
            st.html('<div style="height:1px;background:#F3F4F6;"></div>')
        with st.expander("⚠ Zone dangereuse"):
            if st.button("🗑 Supprimer tous les techniciens",use_container_width=True):
                for t in techs_list: delete_tech(t["id"])
                st.cache_data.clear(); st.rerun()


# ══════════════════════════════════════════════════════════════════
#  TAB 5 — SNAGS (avec délai de fermeture)
# ══════════════════════════════════════════════════════════════════
with tab_snags:
    edit_snag_id   = st.session_state.get("edit_snag_id",None)
    edit_snag_data = {}
    if edit_snag_id and snags_data:
        rows = [s for s in snags_data if s["id"]==edit_snag_id]
        if rows: edit_snag_data = rows[0]

    st.html(section_label(f"{'✎ MODIFIER' if edit_snag_id else '✚ NOUVEAU SNAG'} — {period_label}"))
    with st.form("form_snag"):
        sr1,sr2 = st.columns(2)
        with sr1:
            tech_opts = ["— Sélectionner —"] + techs_noms
            def_ti = (techs_noms.index(edit_snag_data.get("technicien",""))+1
                      if edit_snag_data.get("technicien") in techs_noms else 0)
            sel_tech = st.selectbox("Technicien",tech_opts,index=def_ti)
            man_tech = st.text_input("Ou saisir manuellement",
                                     value=edit_snag_data.get("technicien",""),
                                     placeholder="Nom complet…")
        with sr2:
            auditeur = st.text_input("Auditeur (si remonté par un tiers)",
                                     value=edit_snag_data.get("auditeur",""),
                                     placeholder="Nom de l'auditeur…")
            site_nom = st.text_input("Site",value=edit_snag_data.get("site_nom",""),
                                     placeholder="DOLISIE_CENTRE")

        sr3,sr4,sr5 = st.columns(3)
        with sr3:
            cat_def = CATEGORIES.index(edit_snag_data.get("categorie","TXN")) if edit_snag_data.get("categorie","TXN") in CATEGORIES else 0
            cat = st.selectbox("Catégorie",CATEGORIES,index=cat_def,
                               format_func=lambda x:f"{x}  (base {SUB_SCORES[x]} pts)")
        with sr4:
            d_def = edit_snag_data.get("date_snag",TODAY)
            if isinstance(d_def,str): d_def = date.fromisoformat(d_def)
            snag_date = st.date_input("Date ouverture",value=d_def)
        with sr5:
            site_id_v = st.text_input("Site ID",value=edit_snag_data.get("site_id",""),placeholder="CG_DOL_001")

        # Action
        act_opts = {"raised":"↑ Remonté (ouverture seulement)","closed":"✓ Fermé","both":"⟳ Ouvert + Fermé"}
        def_act  = list(act_opts.keys()).index(edit_snag_data.get("action","raised")) if edit_snag_data.get("action") in act_opts else 0
        action   = st.radio("Action",list(act_opts.keys()),
                            format_func=lambda x:act_opts[x],index=def_act,horizontal=True)

        # Date de fermeture si fermé
        date_ferme = None
        days_to_close = None
        if action in ["closed","both"]:
            df_def = edit_snag_data.get("date_ferme",TODAY)
            if isinstance(df_def,str) and df_def: df_def = date.fromisoformat(df_def)
            elif not df_def: df_def = TODAY
            date_ferme    = st.date_input("Date de fermeture",value=df_def)
            days_to_close = max(0,(date_ferme - snag_date).days)
            cf_key = get_close_factor_key(days_to_close)
            cf     = CLOSE_FACTORS[cf_key]
            st.html(f"""<div style="background:{cf['bg']};border:1px solid {cf['border']};
                border-radius:8px;padding:8px 14px;font-size:12px;color:{cf['color']};font-weight:700;{F}">
                {cf['label']} — délai : {days_to_close} jours
            </div>""")

        desc = st.text_input("Description",value=edit_snag_data.get("description",""),placeholder="Description optionnelle…")

        # Calcul points
        if action == "raised":
            pts_prev = calc_open_pts(cat)
        elif action == "closed":
            pts_prev = calc_close_pts(cat, days_to_close)
        else:
            pts_prev = round(calc_open_pts(cat) + calc_close_pts(cat, days_to_close), 2)

        cf_key = get_close_factor_key(days_to_close) if days_to_close is not None else "none"
        cf     = CLOSE_FACTORS[cf_key]
        detail = f"ouv.{calc_open_pts(cat)} + ferm.{calc_close_pts(cat,days_to_close)} (×{cf['factor']})" if action in ["closed","both"] else f"symbolique ouverture"
        st.html(f"""<div style="background:{cf['bg']};border:1.5px solid {cf['border']};border-radius:8px;
            padding:10px 14px;display:flex;justify-content:space-between;align-items:center;">
            <div style="font-size:11px;color:{cf['color']};{F}">{detail}</div>
            <div style="font-size:30px;font-weight:800;color:{cf['color']};{F}">{pts_prev} pts</div>
        </div>""")

        if edit_snag_id:
            sb1,sb2 = st.columns([3,1])
            with sb1: submitted = st.form_submit_button("METTRE À JOUR",use_container_width=True)
            with sb2:
                if st.form_submit_button("Annuler"):
                    st.session_state["edit_snag_id"]=None; st.rerun()
        else:
            submitted = st.form_submit_button("ENREGISTRER LE SNAG",use_container_width=True)

        if submitted:
            tech_ = man_tech.strip() if man_tech.strip() else (sel_tech if sel_tech!="— Sélectionner —" else "")
            if not tech_: st.error("Technicien requis")
            elif not site_nom.strip(): st.error("Site requis")
            else:
                row = {"technicien":tech_,"site_nom":site_nom.strip(),"site_id":site_id_v.strip(),
                       "categorie":cat,"action":action,"date_snag":str(snag_date),
                       "date_ferme":str(date_ferme) if date_ferme else None,
                       "days_to_close":days_to_close,
                       "auditeur":auditeur.strip() or None,
                       "description":desc.strip(),"points":pts_prev,"annee":sel_y,"mois":sel_m}
                ok = update_snag_manager(edit_snag_id,row) if edit_snag_id else insert_snag_manager(row)
                if ok:
                    st.success(f"✓ Snag enregistré (+{pts_prev} pts)")
                    st.session_state["edit_snag_id"]=None
                    st.cache_data.clear(); st.rerun()

    # Snags en retard
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

    # Liste
    st.html(section_label(f"TOUS LES SNAGS — {period_label} ({len(snags_data)})"))
    if snags_data:
        hdr2 = st.columns([0.9,1.4,1.4,1,0.9,0.8,0.8,0.7,1])
        for col,h in zip(hdr2,["DATE","TECH.","SITE","CAT.","ACTION","DÉLAI","AUDITEUR","PTS",""]):
            col.markdown(f"<div style='font-size:10px;font-weight:700;color:#9CA3AF;letter-spacing:.06em;text-transform:uppercase;{F}'>{h}</div>",unsafe_allow_html=True)
        for s in snags_data:
            d0  = date.fromisoformat(str(s["date_snag"]))
            do  = (TODAY-d0).days
            row = st.columns([0.9,1.4,1.4,1,0.9,0.8,0.8,0.7,1])
            row[0].markdown(f"<div style='font-size:11px;color:#9CA3AF;padding:6px 0;{F}'>{s['date_snag']}</div>",unsafe_allow_html=True)
            row[1].markdown(f"<div style='font-size:12px;font-weight:600;color:#111827;padding:6px 0;{F}'>{s['technicien']}</div>",unsafe_allow_html=True)
            row[2].markdown(f"<div style='font-size:11px;color:#374151;padding:6px 0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;{F}'>{s['site_nom']}</div>",unsafe_allow_html=True)
            row[3].markdown(f"<div style='font-size:11px;padding:6px 0;{F}'>{s['categorie']}</div>",unsafe_allow_html=True)
            ac_ = ACTION_COLOR.get(s["action"],"#9CA3AF")
            row[4].html(f"<div style='padding:6px 0;'><span style='background:{ac_}22;color:{ac_};font-size:10px;font-weight:700;border-radius:12px;padding:2px 7px;{F}'>{ACTION_LABEL.get(s['action'],s['action'])}</span></div>")
            dtc = s.get("days_to_close")
            row[5].html(f"<div style='padding:6px 0;'>{delay_badge_html(dtc) if s.get('action') in ['closed','both'] else status_badge_snag(do) if s.get('action')=='raised' else ''}</div>")
            row[6].markdown(f"<div style='font-size:11px;color:#6B7280;padding:6px 0;{F}'>{s.get('auditeur') or '—'}</div>",unsafe_allow_html=True)
            row[7].markdown(f"<div style='font-size:13px;font-weight:800;color:#D97706;padding:6px 0;text-align:center;{F}'>{s['points']}</div>",unsafe_allow_html=True)
            with row[8]:
                b1,b2 = st.columns(2)
                with b1:
                    if st.button("✎",key=f"e_snag_{s['id']}"): st.session_state["edit_snag_id"]=s["id"]; st.rerun()
                with b2:
                    ck = f"cdel_{s['id']}"
                    if st.session_state.get(ck):
                        c1_,c2_ = st.columns(2)
                        if c1_.button("✓",key=f"yes_{s['id']}"): delete_snag_manager(s["id"]); st.session_state[ck]=False; st.cache_data.clear(); st.rerun()
                        if c2_.button("✗",key=f"no_{s['id']}"): st.session_state[ck]=False; st.rerun()
                    else:
                        if st.button("🗑",key=f"d_snag_{s['id']}"): st.session_state[ck]=True; st.rerun()
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
            RCA : délai 48h · alerte rouge à 72h · ASSET : deadline le 20 du mois
        </div>
    </div>""")
    rca_tab, asset_tab = st.tabs(["📄 Suivi RCA","📦 Suivi ASSET"])

    with rca_tab:
        edit_rca_id = st.session_state.get("edit_rca_id",None)
        edit_rca    = {}
        if edit_rca_id and rca_data:
            rows = [r for r in rca_data if r["id"]==edit_rca_id]
            if rows: edit_rca = rows[0]

        st.html(section_label(f"{'✎ MODIFIER' if edit_rca_id else '✚ NOUVEAU'} RCA"))
        with st.form("form_rca"):
            fr1,fr2 = st.columns(2)
            with fr1:
                rca_opts = ["— Choisir —"] + techs_noms
                def_ri = (techs_noms.index(edit_rca.get("responsable",""))+1 if edit_rca.get("responsable") in techs_noms else 0)
                rca_resp_sel = st.selectbox("Responsable (liste)",rca_opts,index=def_ri)
                rca_resp_man = st.text_input("Ou saisir manuellement",value=edit_rca.get("responsable",""),placeholder="Prénom NOM…")
            with fr2:
                rca_site = st.text_input("Site",value=edit_rca.get("site_nom",""))
                rca_inc  = st.text_input("Incident",value=edit_rca.get("incident",""))
            fr3,fr4,fr5 = st.columns(3)
            with fr3:
                d_inc = edit_rca.get("date_incident",datetime.now())
                if isinstance(d_inc,str): d_inc = datetime.fromisoformat(d_inc.replace("Z",""))
                rca_date_inc = st.date_input("Date incident",value=d_inc.date() if hasattr(d_inc,"date") else TODAY)
                rca_time_inc = st.time_input("Heure",value=d_inc.time() if hasattr(d_inc,"time") else datetime.now().time())
            with fr4:
                rca_sub = st.checkbox("RCA soumis",value=bool(edit_rca.get("date_rca")))
                rca_date_sub = None; rca_time_sub = None
                if rca_sub:
                    d_rca = edit_rca.get("date_rca",datetime.now())
                    if isinstance(d_rca,str): d_rca = datetime.fromisoformat(d_rca.replace("Z",""))
                    rca_date_sub = st.date_input("Date soumission",value=d_rca.date() if hasattr(d_rca,"date") else TODAY)
                    rca_time_sub = st.time_input("Heure soumission",value=d_rca.time() if hasattr(d_rca,"time") else datetime.now().time())
            with fr5:
                rca_statut  = st.selectbox("Statut",["pending","submitted","validated"],
                                           format_func=lambda x:{"pending":"En attente","submitted":"Soumis","validated":"Validé"}[x],
                                           index=["pending","submitted","validated"].index(edit_rca.get("statut","pending")))
                rca_comment = st.text_input("Commentaire",value=edit_rca.get("commentaire",""))
            if edit_rca_id:
                rb1,rb2 = st.columns([3,1])
                with rb1: rca_ok = st.form_submit_button("METTRE À JOUR",use_container_width=True)
                with rb2:
                    if st.form_submit_button("Annuler"): st.session_state["edit_rca_id"]=None; st.rerun()
            else:
                rca_ok = st.form_submit_button("ENREGISTRER RCA",use_container_width=True)
            if rca_ok:
                resp_ = rca_resp_man.strip() if rca_resp_man.strip() else (rca_resp_sel if rca_resp_sel!="— Choisir —" else "")
                if not resp_: st.error("Responsable requis")
                elif not rca_site.strip(): st.error("Site requis")
                else:
                    d_rca_str = str(datetime.combine(rca_date_sub,rca_time_sub)) if rca_sub and rca_date_sub else None
                    row = {"responsable":resp_,"site_nom":rca_site.strip(),"incident":rca_inc.strip(),
                           "date_incident":str(datetime.combine(rca_date_inc,rca_time_inc)),
                           "date_rca":d_rca_str,"statut":rca_statut,
                           "commentaire":rca_comment.strip(),"annee":sel_y,"mois":sel_m}
                    ok = update_rca(edit_rca_id,row) if edit_rca_id else insert_rca(row)
                    if ok:
                        st.success("✓ RCA enregistré"); st.session_state["edit_rca_id"]=None
                        st.cache_data.clear(); st.rerun()

        st.html(section_label(f"LISTE RCA ({len(rca_data)})"))
        if rca_data:
            for r in rca_data:
                d_inc = datetime.fromisoformat(str(r["date_incident"]).replace("Z",""))
                hrs   = (datetime.fromisoformat(str(r["date_rca"]).replace("Z",""))-d_inc).total_seconds()/3600 if r.get("date_rca") else (datetime.now()-d_inc).total_seconds()/3600
                bg_r  = "#FEF2F2" if hrs>=72 else "#FFFBEB" if hrs>=48 else "#F0FDF4"
                sc1,sc2,sc3,sc4 = st.columns([2.5,2,1.5,0.8])
                sc1.html(f"""<div style="background:{bg_r};border-radius:8px;padding:8px 12px;margin-bottom:4px;">
                    <div style="font-size:12px;font-weight:700;color:#111827;{F}">{r['responsable']}</div>
                    <div style="font-size:11px;color:#6B7280;{F}">{r['site_nom']} · {r['incident']}</div>
                    <div style="font-size:10px;color:#9CA3AF;{F}">{d_inc.strftime('%d/%m %H:%M')}</div>
                </div>""")
                sc2.html(f"""<div style="padding:8px 0;">
                    <div style="font-size:11px;{F}">{"Soumis" if r.get("date_rca") else "<span style='color:#DC2626;font-weight:700;'>Non livré</span>"}</div>
                </div>""")
                sc3.html(f"<div style='padding:10px 0;'>{status_badge_rca(hrs)}</div>")
                with sc4:
                    rb_e,rb_d = st.columns(2)
                    if rb_e.button("✎",key=f"e_rca_{r['id']}"): st.session_state["edit_rca_id"]=r["id"]; st.rerun()
                    if rb_d.button("🗑",key=f"d_rca_{r['id']}"): delete_rca(r["id"]); st.cache_data.clear(); st.rerun()
                st.html('<div style="height:1px;background:#F3F4F6;"></div>')
        else:
            st.html(f"""<div style="background:#F9FAFB;border:2px dashed #E5E7EB;border-radius:10px;
                padding:24px;text-align:center;"><div style="font-size:12px;color:#9CA3AF;{F}">Aucun RCA pour {period_label}</div></div>""")

    with asset_tab:
        dl_asset    = date(sel_y, sel_m, 20)
        dl_left     = (dl_asset - TODAY).days
        badge_color = "#EF4444" if dl_left<=3 else "#F59E0B" if dl_left<=7 else "#10B981"
        st.html(f"""<div style="background:#FFFBEB;border:1.5px solid #FDE68A;border-radius:10px;
            padding:12px 16px;margin-bottom:12px;display:flex;justify-content:space-between;align-items:center;">
            <div style="font-size:12px;font-weight:700;color:#92400E;{F}">📦 Deadline ASSET : {dl_asset.strftime('%d %B %Y')}</div>
            <span style="background:{badge_color}22;color:{badge_color};border:1px solid {badge_color}44;
                font-size:12px;font-weight:700;border-radius:8px;padding:4px 12px;{F}">
                {'J-'+str(dl_left) if dl_left>=0 else '⚠ Dépassé'}
            </span>
        </div>""")

        edit_ast_id = st.session_state.get("edit_ast_id",None)
        edit_ast    = {}
        if edit_ast_id and asset_data:
            rows = [a for a in asset_data if a["id"]==edit_ast_id]
            if rows: edit_ast = rows[0]

        with st.form("form_asset"):
            fa1,fa2,fa3 = st.columns([2,1.5,1])
            with fa1:
                ast_opts = ["— Choisir —"] + techs_noms
                def_ai = (techs_noms.index(edit_ast.get("nom",""))+1 if edit_ast.get("nom") in techs_noms else 0)
                ast_nom_sel = st.selectbox("Responsable",ast_opts,index=def_ai)
                ast_nom_man = st.text_input("Ou saisir",value=edit_ast.get("nom",""),placeholder="Prénom NOM…")
            with fa2:
                reg_opts   = ["South","Brazzaville","Pool","Nord","Dolisie","Autre"]
                ast_region = st.selectbox("Région",reg_opts,
                                          index=reg_opts.index(edit_ast.get("region","South")) if edit_ast.get("region","South") in reg_opts else 0)
                ast_sites  = st.number_input("Nb sites",min_value=0,max_value=500,value=edit_ast.get("site_count",0))
            with fa3:
                ast_soumis      = st.checkbox("Soumis",value=bool(edit_ast.get("soumis",False)))
                ast_date_soumis = None
                if ast_soumis:
                    d_ast = edit_ast.get("date_soumis",TODAY)
                    if isinstance(d_ast,str): d_ast = date.fromisoformat(d_ast)
                    ast_date_soumis = st.date_input("Date soumission",value=d_ast)
            ast_comment = st.text_input("Commentaire",value=edit_ast.get("commentaire",""))
            if edit_ast_id:
                ab1,ab2 = st.columns([3,1])
                with ab1: ast_ok = st.form_submit_button("METTRE À JOUR ASSET",use_container_width=True)
                with ab2:
                    if st.form_submit_button("Annuler"): st.session_state["edit_ast_id"]=None; st.rerun()
            else:
                ast_ok = st.form_submit_button("ENREGISTRER ASSET",use_container_width=True)
            if ast_ok:
                nom_ = ast_nom_man.strip() if ast_nom_man.strip() else (ast_nom_sel if ast_nom_sel!="— Choisir —" else "")
                if not nom_: st.error("Nom requis")
                else:
                    row = {"nom":nom_,"region":ast_region,"site_count":ast_sites,"soumis":ast_soumis,
                           "date_soumis":str(ast_date_soumis) if ast_soumis and ast_date_soumis else None,
                           "commentaire":ast_comment.strip(),"annee":sel_y,"mois":sel_m}
                    ok = update_asset(edit_ast_id,row) if edit_ast_id else insert_asset(row)
                    if ok:
                        st.success("✓ ASSET enregistré"); st.session_state["edit_ast_id"]=None
                        st.cache_data.clear(); st.rerun()

        sub_c = sum(1 for a in asset_data if a.get("soumis"))
        ac1,ac2,ac3 = st.columns(3)
        ac1.html(kpi_card("Total",str(len(asset_data)),period_label))
        ac2.html(kpi_card("Soumis",str(sub_c),"dans les délais","#10B981"))
        ac3.html(kpi_card("En attente",str(len(asset_data)-sub_c),"non soumis","#EF4444" if len(asset_data)-sub_c else "#10B981"))

        if asset_data:
            for a in asset_data:
                sc1,sc2,sc3,sc4 = st.columns([2,1.2,1.5,0.8])
                bg_a = "#F0FDF4" if a.get("soumis") else "#FFFBEB"
                sc1.html(f"""<div style="background:{bg_a};border-radius:8px;padding:8px 12px;margin-bottom:4px;">
                    <div style="font-size:12px;font-weight:700;{F}">{a['nom']}</div>
                    <div style="font-size:11px;color:#6B7280;{F}">{a['region']} · {a['site_count']} sites</div>
                </div>""")
                sc2.html(f"<div style='padding:10px 0;'>{'<span style=\"background:#D1FAE5;color:#065F46;border-radius:12px;padding:3px 10px;font-size:11px;font-weight:700;\">✓ Soumis</span>' if a.get('soumis') else '<span style=\"background:#FEF3C7;color:#92400E;border-radius:12px;padding:3px 10px;font-size:11px;font-weight:700;\">⏳ En attente</span>'}</div>")
                sc3.html(f"<div style='font-size:11px;color:#9CA3AF;padding:10px 0;{F}'>{('Le '+str(a['date_soumis'])) if a.get('date_soumis') else '—'}</div>")
                with sc4:
                    ae1,ae2 = st.columns(2)
                    if ae1.button("✎",key=f"e_ast_{a['id']}"): st.session_state["edit_ast_id"]=a["id"]; st.rerun()
                    if ae2.button("🗑",key=f"d_ast_{a['id']}"): delete_asset(a["id"]); st.cache_data.clear(); st.rerun()
                st.html('<div style="height:1px;background:#F3F4F6;"></div>')


# ══════════════════════════════════════════════════════════════════
#  TAB 7 — BLOCAGES
# ══════════════════════════════════════════════════════════════════
with tab_blockers:
    edit_blk_id = st.session_state.get("edit_blk_id",None)
    edit_blk    = {}
    if edit_blk_id and blockers_d:
        rows = [b for b in blockers_d if b["id"]==edit_blk_id]
        if rows: edit_blk = rows[0]

    open_blk   = [b for b in blockers_d if not b.get("resolu")]
    closed_blk = [b for b in blockers_d if b.get("resolu")]
    bk1,bk2 = st.columns(2)
    bk1.html(kpi_card("Blocages ouverts",str(len(open_blk)),"action requise","#EF4444" if open_blk else "#10B981"))
    bk2.html(kpi_card("Résolus",str(len(closed_blk)),f"sur {len(blockers_d)} total","#10B981"))

    with st.form("form_blocker"):
        bb1,bb2 = st.columns(2)
        with bb1:
            blk_tech_opts = ["— Choisir —"] + techs_noms
            def_bi = (techs_noms.index(edit_blk.get("technicien",""))+1 if edit_blk.get("technicien") in techs_noms else 0)
            blk_tech_sel = st.selectbox("Technicien",blk_tech_opts,index=def_bi)
            blk_tech_man = st.text_input("Ou saisir",value=edit_blk.get("technicien",""),placeholder="Prénom NOM…")
        with bb2:
            blk_site = st.text_input("Site",value=edit_blk.get("site_nom",""))
            blk_cat  = st.selectbox("Catégorie",["—"]+CATEGORIES,
                                    index=CATEGORIES.index(edit_blk.get("categorie","TXN"))+1 if edit_blk.get("categorie") in CATEGORIES else 0)
        blk_desc  = st.text_area("Description",value=edit_blk.get("description",""),height=80)
        bb3,bb4,_ = st.columns(3)
        with bb3:
            d_blk = edit_blk.get("date_signal",TODAY)
            if isinstance(d_blk,str): d_blk = date.fromisoformat(d_blk)
            blk_date = st.date_input("Date signalement",value=d_blk)
        with bb4:
            blk_resolu   = st.checkbox("Résolu",value=bool(edit_blk.get("resolu",False)))
            blk_date_res = None
            if blk_resolu:
                d_res = edit_blk.get("date_resolu",TODAY)
                if isinstance(d_res,str) and d_res: d_res = date.fromisoformat(d_res)
                blk_date_res = st.date_input("Date résolution",value=d_res or TODAY)
        if edit_blk_id:
            pb1,pb2 = st.columns([3,1])
            with pb1: blk_ok = st.form_submit_button("METTRE À JOUR",use_container_width=True)
            with pb2:
                if st.form_submit_button("Annuler"): st.session_state["edit_blk_id"]=None; st.rerun()
        else:
            blk_ok = st.form_submit_button("ENREGISTRER",use_container_width=True)
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
                ok = update_blocker(edit_blk_id,row) if edit_blk_id else insert_blocker(row)
                if ok:
                    st.success("✓ Blocage enregistré"); st.session_state["edit_blk_id"]=None
                    st.cache_data.clear(); st.rerun()

    if open_blk:
        st.html(section_label(f"🔴 OUVERTS ({len(open_blk)})"))
        for b in open_blk:
            days_blk = (TODAY-date.fromisoformat(str(b["date_signal"]))).days
            bc1,bc2,bc3 = st.columns([3,1,0.8])
            bc1.html(f"""<div style="background:#FEF2F2;border:1px solid #FECACA;border-radius:8px;padding:8px 12px;margin-bottom:4px;">
                <div style="font-size:12px;font-weight:700;color:#DC2626;{F}">🔒 {b['technicien']} — {b['site_nom']}</div>
                <div style="font-size:11px;color:#374151;{F}">{b['description']}</div>
                <div style="font-size:10px;color:#9CA3AF;{F}">Signalé le {b['date_signal']} · {days_blk}j</div>
            </div>""")
            bc2.html(f"<div style='padding:12px 0;'><span style='background:#FEE2E2;color:#DC2626;font-size:11px;font-weight:700;border-radius:8px;padding:4px 10px;{F}'>J+{days_blk}</span></div>")
            with bc3:
                be1,be2 = st.columns(2)
                if be1.button("✎",key=f"e_blk_{b['id']}"): st.session_state["edit_blk_id"]=b["id"]; st.rerun()
                if be2.button("🗑",key=f"d_blk_{b['id']}"): delete_blocker(b["id"]); st.cache_data.clear(); st.rerun()
    if closed_blk:
        with st.expander(f"✅ Résolus ({len(closed_blk)})"):
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
        d = date(CUR_Y,CUR_M,1)-timedelta(days=30*i)
        months_6.append((d.year,d.month))
    labels_6 = [MONTHS_FR[m-1][:3]+f" {y}" for y,m in months_6]
    obj_6    = [obj_for_month(m) for y,m in months_6]

    @st.cache_data(ttl=120,show_spinner=False)
    def load_6m():
        return {(y,m): fetch_snags_manager(y,m) for y,m in months_6}

    data_6m   = load_6m()
    all_techs = set()
    for data in data_6m.values():
        for s in data: all_techs.add(s["technicien"])
    top_techs = list(all_techs)[:8]
    COLORS_6  = ["#FFD200","#6366F1","#10B981","#F59E0B","#EC4899","#8B5CF6","#14B8A6","#EF4444"]

    st.html(section_label("SCORE MENSUEL — 6 DERNIERS MOIS"))
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
    st.plotly_chart(fig_trend,use_container_width=True,config={"displayModeBar":False})

    # Taux de fermeture mensuel
    st.html(section_label("TAUX DE FERMETURE MENSUEL — 6 MOIS"))
    close_rates = []
    for y,m in months_6:
        data    = data_6m[(y,m)]
        n_total = len(data)
        n_close = sum(1 for s in data if s.get("action") in ["closed","both"])
        close_rates.append(round(n_close/n_total*100,1) if n_total else 0)
    fig_close = go.Figure()
    fig_close.add_trace(go.Scatter(x=labels_6,y=close_rates,mode="lines+markers+text",
                                   line=dict(color="#10B981",width=2.5),
                                   marker=dict(size=8,color=close_rates,
                                               colorscale=[[0,"#EF4444"],[0.5,"#F59E0B"],[1,"#10B981"]]),
                                   text=[f"{v}%" for v in close_rates],textposition="top center",
                                   fill="tozeroy",fillcolor="rgba(16,185,129,0.06)"))
    fig_close.add_hline(y=80,line_dash="dot",line_color="#10B981",line_width=1,
                        annotation_text="Objectif 80%",
                        annotation_font=dict(size=9,color="#10B981",family="Plus Jakarta Sans"))
    fig_close.add_hline(y=50,line_dash="dash",line_color="#EF4444",line_width=1,
                        annotation_text="Seuil alerte 50%",
                        annotation_font=dict(size=9,color="#EF4444",family="Plus Jakarta Sans"))
    fig_close.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="#FAFAFA",height=220,
                            margin=dict(l=0,r=20,t=20,b=8),showlegend=False,
                            xaxis=dict(tickfont=dict(size=11,family="Plus Jakarta Sans")),
                            yaxis=dict(gridcolor="#F1F5F9",range=[0,115],ticksuffix="%",
                                       tickfont=dict(size=10,family="Plus Jakarta Sans")))
    st.plotly_chart(fig_close,use_container_width=True,config={"displayModeBar":False})

    # Barres groupées
    st.html(section_label("PERFORMANCE PAR TECHNICIEN — BARRES GROUPÉES"))
    fig_bar_g = go.Figure()
    for i,tech in enumerate(top_techs):
        vals = [round(sum(s["points"] for s in data_6m[(y,m)] if s["technicien"]==tech),1) for y,m in months_6]
        c_   = COLORS_6[i%len(COLORS_6)]
        fig_bar_g.add_trace(go.Bar(name=tech,x=labels_6,y=vals,marker_color=c_,marker_line_width=0))
    fig_bar_g.update_layout(barmode="group",paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="#FAFAFA",
                            height=300,margin=dict(l=0,r=20,t=8,b=8),
                            xaxis=dict(tickfont=dict(size=11,family="Plus Jakarta Sans")),
                            yaxis=dict(gridcolor="#F1F5F9",tickfont=dict(size=10,family="Plus Jakarta Sans")),
                            legend=dict(font=dict(size=10,family="Plus Jakarta Sans"),
                                        bgcolor="rgba(255,255,255,.9)",bordercolor="#E5E7EB",borderwidth=1,
                                        orientation="h",y=-0.25),
                            bargap=0.15,bargroupgap=0.05)
    st.plotly_chart(fig_bar_g,use_container_width=True,config={"displayModeBar":False})

    # Objectif progressif
    st.html(section_label("OBJECTIF PROGRESSIF — +10%/MOIS"))
    fig_obj = go.Figure()
    fig_obj.add_trace(go.Bar(x=labels_6,y=obj_6,
                             marker_color=["#FFD200" if (y,m)==(CUR_Y,CUR_M) else "#E5E7EB" for y,m in months_6],
                             marker_line_width=0,text=[f"{v} pts" for v in obj_6],textposition="outside"))
    fig_obj.update_layout(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="#FAFAFA",height=180,
                          margin=dict(l=0,r=20,t=8,b=8),showlegend=False,
                          xaxis=dict(tickfont=dict(size=11,family="Plus Jakarta Sans")),
                          yaxis=dict(gridcolor="#F1F5F9",tickfont=dict(size=10,family="Plus Jakarta Sans")))
    st.plotly_chart(fig_obj,use_container_width=True,config={"displayModeBar":False})


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
                Analyse ouverture/fermeture · Détection anomalies · Recommandations · Question libre
            </div>
        </div>
    </div>""")

    ai_col1,ai_col2 = st.columns([1,1])
    with ai_col1:
        st.html(section_label("ANALYSE D'UN PROFIL TECHNICIEN"))
        ai_tech_opts = ["— Choisir —"] + (techs_noms if techs_noms else [t["name"] for t in lb])
        sel_ai = st.selectbox("Technicien",ai_tech_opts,key="ai_tech")
        if st.button("🔍 Analyser",use_container_width=True,key="btn_analyze"):
            if sel_ai == "— Choisir —": st.error("Sélectionnez un technicien")
            else:
                td = next((t for t in lb if t["name"]==sel_ai),None)
                rca_count = sum(1 for r in rca_data if r.get("responsable")==sel_ai)
                blk_count = sum(1 for b in blockers_d if b.get("technicien")==sel_ai and not b.get("resolu"))
                if td:
                    avg_d = td['avg_delay']
                    facteur_str = f"×{CLOSE_FACTORS[get_close_factor_key(avg_d)]['factor']}" if avg_d else "N/A"
                    prompt = f"""Tu es un manager expert terrain telecom MTN Congo, plateforme FieldPerform v6.2.

NOUVEAU SYSTÈME DE SCORING (explique-le si pertinent) :
- Ouverture ticket = points symboliques (TXN:1pt, autres:0.5pt)
- Fermeture ≤3j = base×1.5 (bonus), 4-7j = ×1.0, 8-14j = ×0.6, >14j = ×0.3, non fermé = 0
- Le score récompense PRINCIPALEMENT la fermeture et la RAPIDITÉ

PROFIL {sel_ai} — {period_label} :
- Score total : {td['total']} / {obj_pts} pts ({td['obj_pct']}% objectif)
- Statut : {td['perf_st']['label']}
- Tickets : {td['n']} ouverts · {td['n_closed']} fermés · {td['close_rate']}% taux fermeture
- Délai moyen fermeture : {td['avg_delay']}j → facteur {facteur_str}
- TXN/IPRAN/MW : {td['txn_snags']} tickets
- Énergie : {td['energy_snags']} · RAN : {td['ran_snags']}
- Chute productivité : {'OUI ≥30%' if sel_ai in drop_set else 'NON'}
- RCA en charge : {rca_count} · Blocages ouverts : {blk_count}

Produis une analyse structurée (max 400 mots) :
1. **Évaluation globale** — sur le taux de fermeture et la rapidité
2. **Points forts** 
3. **Axes critiques** — insiste sur délai, 0 TXN si applicable
4. **Action managériale concrète**

En français, professionnel et bienveillant."""
                else:
                    prompt = f"""{sel_ai} n'a aucune donnée pour {period_label}.
Analyse la situation : technicien sans ticket ce mois. Cause probable + action manager. Max 200 mots, français."""

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
        ai_q = st.text_area("Question",
                             placeholder="Ex: Qui est en danger ce mois ?\nEx: Quels techniciens ferment trop lentement ?\nEx: Analyse les points bloquants.",
                             height=110,key="ai_free_q",label_visibility="collapsed")
        if st.button("💬 Envoyer",use_container_width=True,key="btn_free_ai"):
            if not ai_q.strip(): st.error("Saisissez une question")
            else:
                top_perf = sorted(lb, key=lambda x: -x["close_rate"])[:3]
                worst    = sorted(lb, key=lambda x: x["close_rate"])[:3]
                ctx = f"""FieldPerform v6.2 · MTN Congo FLM South · {period_label}
SCORING : ouverture symbolique + fermeture ×1.5/1.0/0.6/0.3 selon délai
- {len(lb)} techniciens · {total_pts} pts · taux fermeture équipe : {avg_rate}%
- Top fermeture : {', '.join(f"{t['name']} ({t['close_rate']}%)" for t in top_perf)}
- Alertes fermeture (<50%) : {', '.join(alert_set) or 'aucune'}
- Chutes : {', '.join(drop_set) or 'aucune'}
- 0 TXN : {', '.join(t['name'] for t in lb if t['txn_snags']==0) or 'aucun'}
- Snags retard : {len(overdue_snags)} · RCA : {rca_alerts} · Blocages : {len([b for b in blockers_d if not b.get('resolu')])}
Question : {ai_q.strip()}
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
    st.html(section_label("DÉTECTIONS AUTOMATIQUES"))
    detections = []
    for t in lb:
        if t["txn_snags"]==0:
            detections.append({"type":"warn","icon":"📡","tech":t["name"],"msg":"Aucun ticket TXN/IPRAN/MW ce mois — infrastructure critique non couverte"})
        if t["name"] in drop_set:
            detections.append({"type":"danger","icon":"📉","tech":t["name"],"msg":f"Chute de productivité ≥30% vs mois précédent"})
        if t["name"] in alert_set:
            detections.append({"type":"danger","icon":"🔴","tech":t["name"],"msg":f"Taux fermeture {t['close_rate']}% — en dessous du seuil 50%"})
        if t["avg_delay"] and t["avg_delay"] > 14:
            detections.append({"type":"danger","icon":"⏱","tech":t["name"],"msg":f"Délai moyen fermeture : {t['avg_delay']}j — facteur ×0.3 appliqué (retard grave)"})
        elif t["avg_delay"] and t["avg_delay"] > 7:
            detections.append({"type":"warn","icon":"⏳","tech":t["name"],"msg":f"Délai moyen fermeture : {t['avg_delay']}j — facteur ×0.6 (retard modéré)"})

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
