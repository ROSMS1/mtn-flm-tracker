# ════════════════════════════════════════════════════════════════
#  FieldPerform · Viewer — Lecture seule pour les techniciens
#  Aucune modification possible — affichage uniquement
# ════════════════════════════════════════════════════════════════
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, date, timedelta
import calendar

from supabase_manager import (
    fetch_techs, fetch_snags_manager,
    fetch_rca, fetch_asset, fetch_blockers,
)
from styles_manager import (
    GLOBAL_CSS, F, MONTHS_FR, CATEGORIES, SUB_SCORES,
    ACTION_FACTOR, ACTION_LABEL, ACTION_COLOR,
    calc_pts, obj_for_month, obj_color, obj_bar_html,
    kpi_card, section_label, badge, status_badge_rca, status_badge_snag,
)

st.set_page_config(
    page_title="FieldPerform · Viewer",
    page_icon="👁",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

# Bannière lecture seule bien visible
st.html(f"""<div style="background:#1E3A5F;border-radius:10px;padding:10px 18px;
    margin-bottom:12px;display:flex;align-items:center;gap:12px;">
    <span style="font-size:20px;">👁</span>
    <div>
        <div style="font-size:13px;font-weight:800;color:#FFFFFF;{F}">Mode Lecture Seule</div>
        <div style="font-size:11px;color:#93C5FD;{F}">
            Consultation uniquement — aucune modification autorisée
        </div>
    </div>
</div>""")

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
            <div style="font-size:10px;color:#9CA3AF;{F}">SOUTH REGION · Viewer</div>
        </div>
    </div><div style="height:1px;background:#E5E7EB;margin-bottom:16px;"></div>""")

    st.html(f'<div style="font-size:10px;color:#9CA3AF;font-weight:700;letter-spacing:.08em;margin-bottom:8px;{F}">PÉRIODE</div>')
    col_m, col_y = st.columns(2)
    with col_m:
        sel_m = st.selectbox("Mois", range(1,13),
                             format_func=lambda x: MONTHS_FR[x-1],
                             index=CUR_M-1, label_visibility="collapsed")
    with col_y:
        sel_y = st.selectbox("Année", [2024,2025,2026,2027],
                             index=[2024,2025,2026,2027].index(CUR_Y),
                             label_visibility="collapsed")

    period_label = f"{MONTHS_FR[sel_m-1]} {sel_y}"
    obj_pts      = obj_for_month(sel_m)

    st.html(f"""<div style="background:#F0FDF4;border:1px solid #BBF7D0;border-radius:8px;
        padding:8px 12px;margin:8px 0;">
        <div style="font-size:10px;color:#166534;font-weight:700;{F}">🎯 OBJECTIF DU MOIS</div>
        <div style="font-size:20px;font-weight:800;color:#166534;{F}">{obj_pts} pts</div>
        <div style="font-size:10px;color:#9CA3AF;{F}">Objectif progressif +10%/mois</div>
    </div>""")

    st.html(f'<div style="height:1px;background:#E5E7EB;margin:12px 0;"></div>')
    st.html(f"""<div style="background:#FEF2F2;border:1px solid #FECACA;border-radius:8px;
        padding:8px 12px;text-align:center;">
        <div style="font-size:11px;font-weight:700;color:#DC2626;{F}">🔒 ACCÈS RESTREINT</div>
        <div style="font-size:10px;color:#9CA3AF;margin-top:2px;{F}">Consultation uniquement</div>
    </div>""")

# ════════════════ DONNÉES ════════════════
@st.cache_data(ttl=60, show_spinner=False)
def load_snags(y, m): return fetch_snags_manager(y, m)
@st.cache_data(ttl=60, show_spinner=False)
def load_rca(y, m): return fetch_rca(y, m)
@st.cache_data(ttl=60, show_spinner=False)
def load_asset(y, m): return fetch_asset(y, m)
@st.cache_data(ttl=60, show_spinner=False)
def load_blockers(y, m): return fetch_blockers(y, m)
@st.cache_data(ttl=60, show_spinner=False)
def load_techs(): return fetch_techs()

snags_data = load_snags(sel_y, sel_m)
rca_data   = load_rca(sel_y, sel_m)
asset_data = load_asset(sel_y, sel_m)
blockers_d = load_blockers(sel_y, sel_m)
techs_list = load_techs()

# ── Leaderboard ──────────────────────────────────────────────────
def build_lb(snags):
    if not snags: return []
    df = pd.DataFrame(snags)
    lb = []
    for tech in df["technicien"].unique():
        td     = df[df["technicien"]==tech]
        total  = round(td["points"].sum(), 1)
        n      = len(td)
        closed = int(td["action"].isin(["closed","both"]).sum())
        raised = int(td["action"].eq("raised").sum())
        bonus  = 5 if n>=8 else 3 if n>=5 else 0
        ml_pct = round(min(100,(closed+raised*0.5)/n*100+bonus),1) if n else 0
        txn    = int(td["categorie"].isin(["TXN","IPRAN","MW_FADING","MW_EQUIPMENT"]).sum())
        lb.append({"name":tech,"total":total,"n":n,"closed":closed,"ml_pct":ml_pct,"txn_snags":txn})
    lb.sort(key=lambda x: -x["total"])
    for i,t in enumerate(lb):
        t["rank"] = i+1
        pct = round(t["total"]/obj_pts*100,1) if obj_pts else 0
        t["obj_pct"] = pct
        if pct>=80:   t["cluster"]={"label":"Elite","color":"#D97706","bg":"#FFFBEB","border":"#FDE68A"}
        elif pct>=60: t["cluster"]={"label":"Performant","color":"#6366F1","bg":"#EEF2FF","border":"#C7D2FE"}
        elif pct>=40: t["cluster"]={"label":"En progression","color":"#10B981","bg":"#ECFDF5","border":"#6EE7B7"}
        else:         t["cluster"]={"label":"Actif","color":"#9CA3AF","bg":"#F9FAFB","border":"#E5E7EB"}
    return lb

lb        = build_lb(snags_data)
total_pts = sum(t["total"] for t in lb)
mid_month = (now.day >= 15) if (sel_y==CUR_Y and sel_m==CUR_M) else True
alert_set = {t["name"] for t in lb if t["ml_pct"]<30 and mid_month}

# ════════════════ HEADER ════════════════
st.html(f"""<div style="background:linear-gradient(135deg,#111827,#1F2937);
    border-radius:14px;padding:18px 24px;margin-bottom:14px;">
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;">
        <div>
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">
                <span style="background:#FFD200;color:#111827;font-size:12px;font-weight:800;
                    padding:3px 10px;border-radius:6px;{F}">MTN</span>
                <span style="font-size:24px;font-weight:800;color:#FFFFFF;{F}">FieldPerform</span>
                <span style="font-size:10px;color:#6B7280;background:#374151;
                    padding:3px 8px;border-radius:6px;{F}">👁 Viewer</span>
            </div>
            <div style="font-size:12px;color:#9CA3AF;{F}">
                {period_label} · South Region · Objectif : {obj_pts} pts
            </div>
        </div>
        <div style="background:#374151;border-radius:8px;padding:6px 14px;
            font-size:11px;color:#D1D5DB;font-weight:600;{F}">
            {len(lb)} techniciens · {round(total_pts,1)} pts
        </div>
    </div>
</div>""")

# ════════════════ ONGLETS ════════════════
(tab_overview, tab_class, tab_snags,
 tab_mgmt, tab_blockers, tab_bareme) = st.tabs([
    "📊 Vue globale",
    "🏆 Classement",
    "🔧 Snags",
    "📄 RCA & ASSET",
    "🚧 Points bloquants",
    "📋 Barème",
])

# ══════════════════════════════════════════════════════════════════
#  TAB 1 — VUE GLOBALE
# ══════════════════════════════════════════════════════════════════
with tab_overview:
    team_pct = round(total_pts/obj_pts*100,1) if obj_pts else 0
    tc = obj_color(team_pct)
    st.html(f"""<div style="background:#FFFFFF;border:1px solid #E5E7EB;border-radius:10px;
        padding:14px 18px;margin-bottom:12px;">
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

    c1,c2,c3,c4 = st.columns(4)
    closed_n = sum(1 for s in snags_data if s.get("action") in ["closed","both"]) if snags_data else 0
    cats_n   = len({s["categorie"] for s in snags_data}) if snags_data else 0
    c1.html(kpi_card("Points équipe", str(round(total_pts,1)), f"obj. {obj_pts} pts","#D97706"))
    c2.html(kpi_card("Techniciens actifs", str(len(lb)), "ce mois"))
    c3.html(kpi_card("Snags enregistrés", str(len(snags_data)), f"{closed_n} fermés"))
    c4.html(kpi_card("Catégories actives", str(cats_n), "sur 28 disponibles"))

    if lb:
        st.html(section_label("PROGRESSION INDIVIDUELLE"))
        for t in lb:
            t_pct   = t["obj_pct"]
            t_col   = obj_color(t_pct)
            is_alrt = t["name"] in alert_set
            bdr     = "border:1.5px solid #FECACA;" if is_alrt else "border:1px solid #E5E7EB;"
            bg      = "background:#FFF5F5;" if is_alrt else "background:#FFFFFF;"
            medal   = "🥇" if t["rank"]==1 else "🥈" if t["rank"]==2 else "🥉" if t["rank"]==3 else f"#{t['rank']}"
            cl_     = t["cluster"]
            alrt_tag = f"<span style='background:#FEE2E2;color:#DC2626;font-size:9px;font-weight:700;border-radius:4px;padding:2px 6px;{F}'>⚠ Alerte</span>" if is_alrt else ""
            st.html(f"""<div style="{bg}{bdr}border-radius:10px;padding:10px 14px;margin-bottom:6px;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                    <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
                        <span style="font-size:13px;font-weight:700;
                            color:{'#DC2626' if is_alrt else '#111827'};{F}">{medal} {t['name']}</span>
                        {alrt_tag}
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
                    {t['n']} snags · {t['closed']} fermés · {t['ml_pct']}% fermeture · TXN: {t['txn_snags']}
                </div>
            </div>""")

    # Graphiques
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
                orientation="h", marker=dict(color=bar_colors, cornerradius=5),
                text=[f"  {t['total']} pts" for t in lb],
                textposition="inside", insidetextanchor="end",
                textfont=dict(size=11, color="#1F2937", family="Plus Jakarta Sans", weight="bold"),
            ))
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#FAFAFA",
                height=max(280,len(lb)*50), margin=dict(l=10,r=60,t=6,b=6),
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
                for idx,(cat,pts) in enumerate(cp.items()):
                    c_ = bcs[idx%len(bcs)]
                    st.html(f"""<div style="display:flex;align-items:center;gap:8px;margin-bottom:7px;">
                        <div style="font-size:11px;color:#374151;width:110px;flex-shrink:0;
                            overflow:hidden;text-overflow:ellipsis;white-space:nowrap;{F}">{cat}</div>
                        <div style="flex:1;background:#F1F5F9;border-radius:99px;height:7px;overflow:hidden;">
                            <div style="width:{pts/mx*100:.1f}%;height:100%;background:{c_};border-radius:99px;"></div></div>
                        <div style="font-size:11px;font-weight:700;color:{c_};width:30px;text-align:right;{F}">{pts:.0f}</div>
                    </div>""")


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
        if len(lb) >= 2:
            pod    = [lb[1], lb[0]] + ([lb[2]] if len(lb)>2 else [])
            h_map  = {1:160,2:120,3:90}
            tc_map = {1:"#D97706",2:"#6B7280",3:"#92400E"}
            bc_map = {1:"#FFD200",2:"#E5E7EB",3:"#FDE68A"}
            mc_map = {1:"🥇",2:"🥈",3:"🥉"}
            pod_html = '<div style="display:flex;justify-content:center;align-items:flex-end;gap:16px;margin-bottom:28px;padding:20px;">'
            for t in pod:
                r = t["rank"]
                pod_html += f"""<div style="text-align:center;width:150px;">
                    <div style="font-size:28px;margin-bottom:4px;">{mc_map[r]}</div>
                    <div style="font-size:13px;font-weight:700;color:#111827;{F}">{t['name']}</div>
                    <div style="font-size:20px;font-weight:800;color:{tc_map[r]};margin:4px 0;{F}">{t['total']} pts</div>
                    <div style="font-size:11px;color:#9CA3AF;margin-bottom:8px;{F}">{t['obj_pct']}% objectif</div>
                    <div style="height:{h_map[r]}px;background:#F9FAFB;border:2px solid {bc_map[r]};
                        border-radius:12px 12px 0 0;display:flex;align-items:flex-end;
                        justify-content:center;padding-bottom:12px;">
                        <div style="font-size:28px;font-weight:800;color:{tc_map[r]};{F}">{r}</div>
                    </div>
                </div>"""
            pod_html += '</div>'
            st.html(pod_html)

        st.html(section_label(f"CLASSEMENT COMPLET — {period_label}"))
        hdr = st.columns([0.4,2,0.8,0.8,0.8,0.8,0.8,1.2])
        for col,h in zip(hdr,["#","TECHNICIEN","POINTS","% OBJ","SNAGS","FERMÉS","TXN","CLUSTER"]):
            col.markdown(f"<div style='font-size:9px;font-weight:700;color:#9CA3AF;letter-spacing:.06em;text-transform:uppercase;padding:6px 0;{F}'>{h}</div>",unsafe_allow_html=True)

        for t in lb:
            is_alrt = t["name"] in alert_set
            bg_row  = "#FFF5F5" if is_alrt else "#FFFFFF"
            row     = st.columns([0.4,2,0.8,0.8,0.8,0.8,0.8,1.2])
            medal   = "🥇" if t["rank"]==1 else "🥈" if t["rank"]==2 else "🥉" if t["rank"]==3 else f"#{t['rank']}"
            t_col   = obj_color(t["obj_pct"])
            cl_     = t["cluster"]
            cl_bg   = cl_["bg"]; cl_co = cl_["color"]; cl_bd = cl_["border"]; cl_lb = cl_["label"]

            row[0].markdown(f"<div style='padding:10px 0;font-size:11px;color:#9CA3AF;{F}'>{medal}</div>",unsafe_allow_html=True)
            row[1].markdown(f"<div style='padding:10px 0;font-size:12px;font-weight:700;color:{'#DC2626' if is_alrt else '#111827'};{F}'>{'⚠ ' if is_alrt else ''}{t['name']}</div>",unsafe_allow_html=True)
            row[2].markdown(f"<div style='padding:10px 0;font-size:14px;font-weight:800;color:#D97706;text-align:center;{F}'>{t['total']}</div>",unsafe_allow_html=True)
            row[3].markdown(f"<div style='padding:10px 0;font-size:13px;font-weight:700;color:{t_col};text-align:center;{F}'>{t['obj_pct']}%</div>",unsafe_allow_html=True)
            row[4].markdown(f"<div style='padding:10px 0;font-size:12px;color:#374151;text-align:center;{F}'>{t['n']}</div>",unsafe_allow_html=True)
            row[5].markdown(f"<div style='padding:10px 0;font-size:12px;color:#6366F1;font-weight:700;text-align:center;{F}'>{t['closed']}</div>",unsafe_allow_html=True)
            txn_c = "#EF4444" if t["txn_snags"]==0 else "#10B981"
            row[6].markdown(f"<div style='padding:10px 0;font-size:12px;font-weight:700;color:{txn_c};text-align:center;{F}'>{t['txn_snags']}</div>",unsafe_allow_html=True)
            row[7].html(f"<div style='padding:8px 0;'><span style='background:{cl_bg};color:{cl_co};border:1px solid {cl_bd};font-size:10px;font-weight:700;border-radius:20px;padding:3px 9px;{F}'>{cl_lb}</span></div>")
            st.html('<div style="height:1px;background:#F3F4F6;"></div>')

        # Graphique ML
        st.html('<div style="height:16px;"></div>')
        st.html(section_label("SCORE ML — TAUX DE FERMETURE"))
        ml_df = pd.DataFrame([{"Technicien":t["name"],"Score (%)":t["ml_pct"],"Cluster":t["cluster"]["label"]} for t in lb])
        fig_ml = px.bar(ml_df, x="Score (%)", y="Technicien", orientation="h", color="Cluster",
                        color_discrete_map={"Elite":"#F59E0B","Performant":"#6366F1",
                                            "En progression":"#10B981","Actif":"#9CA3AF"},
                        text="Score (%)")
        fig_ml.add_vline(x=30, line_dash="dash", line_color="#EF4444", line_width=1.5,
                         annotation_text="Seuil 30%",
                         annotation_font=dict(size=9,color="#EF4444",family="Plus Jakarta Sans"))
        fig_ml.update_traces(texttemplate="%{text}%", textposition="outside", marker_line_width=0)
        fig_ml.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#FAFAFA",
            height=max(260,len(lb)*44), margin=dict(l=0,r=60,t=8,b=8),
            xaxis=dict(gridcolor="#F3F4F6",range=[0,115],ticksuffix="%",
                       tickfont=dict(size=10,family="Plus Jakarta Sans")),
            yaxis=dict(gridcolor="rgba(0,0,0,0)",
                       tickfont=dict(size=12,family="Plus Jakarta Sans"),autorange="reversed"),
            legend=dict(font=dict(size=11,family="Plus Jakarta Sans"),bgcolor="rgba(0,0,0,0)"),
        )
        st.plotly_chart(fig_ml, use_container_width=True, config={"displayModeBar":False})


# ══════════════════════════════════════════════════════════════════
#  TAB 3 — SNAGS (lecture seule)
# ══════════════════════════════════════════════════════════════════
with tab_snags:
    st.html(f"""<div style="background:#FFFBEB;border:1px solid #FDE68A;border-radius:8px;
        padding:8px 14px;margin-bottom:12px;font-size:11px;color:#92400E;{F}">
        👁 Consultation uniquement — la saisie et modification des snags est réservée au manager.
    </div>""")

    # Snags en retard
    overdue = [s for s in snags_data
               if s.get("action") in ["raised","both"] and not s.get("date_ferme")
               and (TODAY - date.fromisoformat(str(s["date_snag"]))).days > 7]
    if overdue:
        st.html(section_label(f"🔴 SNAGS EN RETARD (>7j) — {len(overdue)} cas"))
        for s in overdue:
            days_o = (TODAY - date.fromisoformat(str(s["date_snag"]))).days
            aud = f"· Auditeur : <strong>{s['auditeur']}</strong>" if s.get("auditeur") else ""
            st.html(f"""<div style="background:#FEF2F2;border:1px solid #FECACA;border-radius:8px;
                padding:8px 14px;margin-bottom:6px;display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <span style="font-size:12px;font-weight:700;color:#DC2626;{F}">{s['technicien']}</span>
                    <span style="font-size:11px;color:#6B7280;{F}"> · {s['site_nom']} · {s['categorie']}</span>
                    <div style="font-size:11px;color:#9CA3AF;margin-top:2px;{F}">Depuis le {s['date_snag']} {aud}</div>
                </div>
                {status_badge_snag(days_o)}
            </div>""")

    st.html(section_label(f"TOUS LES SNAGS — {period_label} ({len(snags_data)})"))
    if snags_data:
        hdr = st.columns([1,1.5,1.5,1,1,1,0.7])
        for col,h in zip(hdr,["DATE","TECHNICIEN","SITE","CATÉGORIE","ACTION","AUDITEUR","PTS"]):
            col.markdown(f"<div style='font-size:10px;font-weight:700;color:#9CA3AF;letter-spacing:.06em;text-transform:uppercase;{F}'>{h}</div>",unsafe_allow_html=True)

        for idx, s in enumerate(snags_data):
            d0        = date.fromisoformat(str(s["date_snag"]))
            days_open = (TODAY - d0).days
            bg_r      = "#FFF5F5" if days_open>7 and s["action"] in ["raised","both"] and not s.get("date_ferme") else ("#FAFBFC" if idx%2 else "#FFFFFF")
            row = st.columns([1,1.5,1.5,1,1,1,0.7])
            row[0].markdown(f"<div style='font-size:11px;color:#9CA3AF;padding:7px 0;background:{bg_r};{F}'>{s['date_snag']}</div>",unsafe_allow_html=True)
            row[1].markdown(f"<div style='font-size:12px;font-weight:600;color:#111827;padding:7px 0;background:{bg_r};{F}'>{s['technicien']}</div>",unsafe_allow_html=True)
            row[2].markdown(f"<div style='font-size:11px;color:#374151;padding:7px 0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;background:{bg_r};{F}'>{s['site_nom']}</div>",unsafe_allow_html=True)
            row[3].markdown(f"<div style='font-size:11px;padding:7px 0;background:{bg_r};{F}'>{s['categorie']}</div>",unsafe_allow_html=True)
            ac_ = ACTION_COLOR.get(s["action"],"#9CA3AF")
            row[4].html(f"<div style='padding:7px 0;background:{bg_r};'><span style='background:{ac_}22;color:{ac_};font-size:10px;font-weight:700;border-radius:12px;padding:2px 7px;{F}'>{ACTION_LABEL.get(s['action'],s['action'])}</span></div>")
            row[5].markdown(f"<div style='font-size:11px;color:#6B7280;padding:7px 0;background:{bg_r};{F}'>{s.get('auditeur') or '—'}</div>",unsafe_allow_html=True)
            row[6].markdown(f"<div style='font-size:13px;font-weight:800;color:#D97706;padding:7px 0;text-align:center;background:{bg_r};{F}'>{s['points']}</div>",unsafe_allow_html=True)
            st.html('<div style="height:1px;background:#F3F4F6;"></div>')
    else:
        st.html(f"""<div style="background:#F9FAFB;border:2px dashed #E5E7EB;border-radius:10px;
            padding:30px;text-align:center;">
            <div style="font-size:12px;color:#9CA3AF;{F}">Aucun snag pour {period_label}</div>
        </div>""")


# ══════════════════════════════════════════════════════════════════
#  TAB 4 — RCA & ASSET (lecture seule)
# ══════════════════════════════════════════════════════════════════
with tab_mgmt:
    st.html(f"""<div style="background:#FFFBEB;border:1px solid #FDE68A;border-radius:8px;
        padding:8px 14px;margin-bottom:12px;font-size:11px;color:#92400E;{F}">
        👁 Consultation uniquement — la saisie est réservée au manager.
    </div>""")

    rca_tab, asset_tab = st.tabs(["📄 Suivi RCA","📦 Suivi ASSET"])

    with rca_tab:
        st.html(section_label(f"LISTE RCA — {period_label} ({len(rca_data)})"))
        st.html(f"""<div style="margin-bottom:10px;">
            <span style="background:#FEE2E2;color:#DC2626;border-radius:12px;padding:3px 10px;font-size:11px;font-weight:700;margin-right:6px;">🔴 ≥72h</span>
            <span style="background:#FEF3C7;color:#92400E;border-radius:12px;padding:3px 10px;font-size:11px;font-weight:700;margin-right:6px;">🟠 48–72h</span>
            <span style="background:#D1FAE5;color:#065F46;border-radius:12px;padding:3px 10px;font-size:11px;font-weight:700;">🟢 Dans les délais</span>
        </div>""")
        if rca_data:
            for r in rca_data:
                d_inc = datetime.fromisoformat(str(r["date_incident"]).replace("Z",""))
                hrs   = (datetime.fromisoformat(str(r["date_rca"]).replace("Z",""))-d_inc).total_seconds()/3600 if r.get("date_rca") else (datetime.now()-d_inc).total_seconds()/3600
                bg_r  = "#FEF2F2" if hrs>=72 else "#FFFBEB" if hrs>=48 else "#F0FDF4"
                sc1,sc2,sc3 = st.columns([2.5,2,1.5])
                sc1.html(f"""<div style="background:{bg_r};border-radius:8px;padding:8px 12px;margin-bottom:4px;">
                    <div style="font-size:12px;font-weight:700;color:#111827;{F}">{r['responsable']}</div>
                    <div style="font-size:11px;color:#6B7280;{F}">{r['site_nom']} · {r['incident']}</div>
                    <div style="font-size:10px;color:#9CA3AF;margin-top:2px;{F}">Incident: {d_inc.strftime('%d/%m %H:%M')}</div>
                </div>""")
                sc2.html(f"""<div style="padding:8px 0;">
                    <div style="font-size:11px;color:#6B7280;{F}">{"Soumis" if r.get("date_rca") else "Non soumis"}</div>
                    {'<div style="font-size:10px;color:#9CA3AF;">'+str(r["date_rca"])[:16]+'</div>' if r.get("date_rca") else '<div style="font-size:10px;color:#DC2626;font-weight:700;">RCA non livré</div>'}
                </div>""")
                sc3.html(f"<div style='padding:10px 0;'>{status_badge_rca(hrs)}</div>")
                st.html('<div style="height:1px;background:#F3F4F6;"></div>')
        else:
            st.html(f"""<div style="background:#F9FAFB;border:2px dashed #E5E7EB;border-radius:10px;
                padding:24px;text-align:center;"><div style="font-size:12px;color:#9CA3AF;{F}">Aucun RCA pour {period_label}</div></div>""")

    with asset_tab:
        deadline_asset  = date(sel_y, sel_m, 20)
        days_left_asset = (deadline_asset - TODAY).days
        badge_color     = "#EF4444" if days_left_asset<=3 else "#F59E0B" if days_left_asset<=7 else "#10B981"
        submitted_c = sum(1 for a in asset_data if a.get("soumis"))

        st.html(f"""<div style="background:#FFFBEB;border:1.5px solid #FDE68A;border-radius:10px;
            padding:12px 16px;margin-bottom:12px;display:flex;justify-content:space-between;align-items:center;">
            <div style="font-size:12px;font-weight:700;color:#92400E;{F}">📦 Deadline ASSET : {deadline_asset.strftime('%d %B %Y')}</div>
            <span style="background:{badge_color}22;color:{badge_color};border:1px solid {badge_color}44;
                font-size:12px;font-weight:700;border-radius:8px;padding:4px 12px;{F}">
                {'J-'+str(days_left_asset) if days_left_asset>=0 else '⚠ Dépassé'}
            </span>
        </div>""")

        ac1,ac2,ac3 = st.columns(3)
        ac1.html(kpi_card("Total ASSET",str(len(asset_data)),period_label))
        ac2.html(kpi_card("Soumis",str(submitted_c),"dans les délais","#10B981"))
        ac3.html(kpi_card("En attente",str(len(asset_data)-submitted_c),"non soumis","#EF4444" if len(asset_data)-submitted_c else "#10B981"))

        st.html(section_label(f"LISTE ASSET — {period_label}"))
        if asset_data:
            for a in asset_data:
                sc1,sc2,sc3 = st.columns([2,1.2,1.8])
                bg_a = "#F0FDF4" if a.get("soumis") else "#FFFBEB"
                sc1.html(f"""<div style="background:{bg_a};border-radius:8px;padding:8px 12px;margin-bottom:4px;">
                    <div style="font-size:12px;font-weight:700;color:#111827;{F}">{a['nom']}</div>
                    <div style="font-size:11px;color:#6B7280;{F}">{a['region']} · {a['site_count']} sites</div>
                </div>""")
                sc2.html(f"<div style='padding:10px 0;'>{'<span style=\"background:#D1FAE5;color:#065F46;border-radius:12px;padding:3px 10px;font-size:11px;font-weight:700;\">✓ Soumis</span>' if a.get('soumis') else '<span style=\"background:#FEF3C7;color:#92400E;border-radius:12px;padding:3px 10px;font-size:11px;font-weight:700;\">⏳ En attente</span>'}</div>")
                sc3.html(f"<div style='font-size:11px;color:#9CA3AF;padding:10px 0;{F}'>{('Le '+str(a['date_soumis'])) if a.get('date_soumis') else 'Non soumis'}</div>")
                st.html('<div style="height:1px;background:#F3F4F6;"></div>')
        else:
            st.html(f"""<div style="background:#F9FAFB;border:2px dashed #E5E7EB;border-radius:10px;
                padding:24px;text-align:center;"><div style="font-size:12px;color:#9CA3AF;{F}">Aucun ASSET pour {period_label}</div></div>""")


# ══════════════════════════════════════════════════════════════════
#  TAB 5 — POINTS BLOQUANTS (lecture seule)
# ══════════════════════════════════════════════════════════════════
with tab_blockers:
    st.html(f"""<div style="background:#FFFBEB;border:1px solid #FDE68A;border-radius:8px;
        padding:8px 14px;margin-bottom:12px;font-size:11px;color:#92400E;{F}">
        👁 Consultation uniquement — le signalement est réservé au manager.
    </div>""")

    open_blk   = [b for b in blockers_d if not b.get("resolu")]
    closed_blk = [b for b in blockers_d if b.get("resolu")]

    bk1,bk2 = st.columns(2)
    bk1.html(kpi_card("Blocages ouverts",str(len(open_blk)),"action en cours","#EF4444" if open_blk else "#10B981"))
    bk2.html(kpi_card("Résolus ce mois",str(len(closed_blk)),f"sur {len(blockers_d)} total","#10B981"))

    if open_blk:
        st.html(section_label(f"🔴 BLOCAGES OUVERTS ({len(open_blk)})"))
        for b in open_blk:
            days_blk = (TODAY - date.fromisoformat(str(b["date_signal"]))).days
            st.html(f"""<div style="background:#FEF2F2;border:1px solid #FECACA;border-radius:8px;
                padding:8px 14px;margin-bottom:6px;display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <div style="font-size:12px;font-weight:700;color:#DC2626;{F}">🔒 {b['technicien']} — {b['site_nom']}
                        {f'<span style="font-size:10px;background:#FEE2E2;border-radius:4px;padding:1px 6px;margin-left:6px;">{b["categorie"]}</span>' if b.get("categorie") else ''}</div>
                    <div style="font-size:11px;color:#374151;margin-top:3px;{F}">{b['description']}</div>
                    <div style="font-size:10px;color:#9CA3AF;margin-top:2px;{F}">Signalé le {b['date_signal']} · {days_blk} jours ouverts</div>
                </div>
                <span style="background:#FEE2E2;color:#DC2626;font-size:11px;font-weight:700;border-radius:8px;padding:4px 10px;{F}">J+{days_blk}</span>
            </div>""")

    if closed_blk:
        with st.expander(f"✅ Blocages résolus ({len(closed_blk)})"):
            for b in closed_blk:
                st.html(f"""<div style="background:#F0FDF4;border:1px solid #BBF7D0;border-radius:8px;padding:8px 12px;margin-bottom:6px;">
                    <div style="font-size:12px;font-weight:700;color:#166534;{F}">✓ {b['technicien']} — {b['site_nom']}</div>
                    <div style="font-size:11px;color:#374151;{F}">{b['description']}</div>
                    <div style="font-size:10px;color:#9CA3AF;{F}">Résolu le {b.get('date_resolu','—')}</div>
                </div>""")

    if not open_blk and not closed_blk:
        st.html(f"""<div style="background:#F0FDF4;border:1px solid #BBF7D0;border-radius:10px;
            padding:30px;text-align:center;">
            <div style="font-size:13px;color:#166534;font-weight:700;{F}">✅ Aucun point bloquant pour {period_label}</div>
        </div>""")


# ══════════════════════════════════════════════════════════════════
#  TAB 6 — BARÈME (lecture seule)
# ══════════════════════════════════════════════════════════════════
with tab_bareme:
    st.html(section_label("RÈGLES DE CALCUL DES POINTS"))
    rc1,rc2,rc3 = st.columns(3)
    for col_,(act,val,sub,bg_,col_txt,bdr) in zip([rc1,rc2,rc3],[
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
            <strong style="color:#374151;">🎯 Objectif {period_label} : </strong><strong style="color:#D97706;">{obj_pts} pts</strong> (+10%/mois)<br>
            <strong style="color:#EF4444;">⚠ Alerte : </strong>taux &lt;30% après le 15 du mois → rouge automatique
        </div>
    </div>""")

    st.html(section_label("POINTS BASE PAR CATÉGORIE — 28 CATÉGORIES"))
    groups = {
        "⚡ ÉNERGIE":       ["DG","Battery","Rectifier","ATS","ENERGY_OTHER"],
        "📡 TRANSMISSION":  ["TXN","IPRAN","MW_FADING","MW_EQUIPMENT"],
        "📶 RAN / RADIO":   ["RAN","ANTENNA","FEEDER","BTS_HW","BTS_SW","PARAMETER"],
        "🏗 CIVIL / ACCÈS": ["ACCESS","CIVIL","SECURITY","POWER_CABLE","EARTHING"],
        "❄ INFRASTRUCTURE":["COOLING","SHELTER","FIBER","SWITCH","ROUTER"],
        "🔧 AUTRES":        ["TRANSPORT","MONITORING","OTHER"],
    }
    bcs = ["#FFD200","#6366F1","#10B981","#F59E0B","#EC4899","#8B5CF6"]
    for gi,(grp_name,cats) in enumerate(groups.items()):
        gc = bcs[gi%len(bcs)]
        st.html(f'<div style="font-size:11px;font-weight:700;color:{gc};letter-spacing:.05em;margin:14px 0 6px;{F}">{grp_name}</div>')
        cols = st.columns(len(cats))
        for col_,cat in zip(cols,cats):
            pts = SUB_SCORES[cat]
            col_.html(f"""<div style="background:#FFFFFF;border:1px solid #E5E7EB;
                border-radius:8px;padding:10px 8px;text-align:center;margin-bottom:4px;">
                <div style="font-size:10px;font-weight:700;color:#374151;margin-bottom:6px;
                    overflow:hidden;text-overflow:ellipsis;white-space:nowrap;{F}">{cat}</div>
                <div style="font-size:22px;font-weight:800;color:{gc};{F}">{pts}</div>
                <div style="font-size:9px;color:#9CA3AF;margin-top:4px;{F}">pts base</div>
                <div style="height:1px;background:#F3F4F6;margin:6px 0;"></div>
                <div style="font-size:9px;color:#6B7280;{F}">↑{round(pts*.4,1)} · ✓{round(pts*.6,1)} · ⟳{pts}</div>
            </div>""")

    # Simulateur (lecture seule — pas de saisie, juste visualisation)
    st.html(section_label("🧮 SIMULATEUR DE POINTS"))
    sim1,sim2,sim3 = st.columns(3)
    with sim1:
        sim_cat = st.selectbox("Catégorie",CATEGORIES,
                               format_func=lambda x:f"{x}  ({SUB_SCORES[x]} pts base)",
                               key="viewer_sim_cat")
    with sim2:
        sim_act = st.selectbox("Action",["raised","closed","both"],
                               format_func=lambda x:{"raised":"↑ Remonté (40%)","closed":"✓ Fermé (60%)","both":"⟳ R+F (100%)"}[x],
                               key="viewer_sim_act")
    with sim3:
        sim_pts = calc_pts(sim_cat,sim_act)
        ac_     = ACTION_COLOR.get(sim_act,"#6B7280")
        st.html(f"""<div style="background:{ac_}11;border:2px solid {ac_}44;
            border-radius:10px;padding:14px;text-align:center;margin-top:4px;">
            <div style="font-size:11px;color:{ac_};font-weight:700;{F}">POINTS CALCULÉS</div>
            <div style="font-size:40px;font-weight:800;color:{ac_};{F}">{sim_pts}</div>
            <div style="font-size:10px;color:#9CA3AF;{F}">{SUB_SCORES[sim_cat]} × {ACTION_FACTOR[sim_act]}</div>
        </div>""")
