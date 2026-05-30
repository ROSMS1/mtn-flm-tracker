# ════════════════════════════════════════════════════════════════
#  MTN FLM Manager Dashboard  v6.0
#  Modules : Techniciens · Snags · RCA · ASSET · Blockers · IA
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
    page_title="MTN FLM Manager",
    page_icon="📊",
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
            <div style="font-size:14px;font-weight:800;color:#111827;{F}">MANAGER DASHBOARD</div>
            <div style="font-size:10px;color:#9CA3AF;letter-spacing:.06em;{F}">SOUTH REGION · v6.0</div>
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
        <div style="font-size:10px;color:#9CA3AF;{F}">+10%/mois · Base 100 en janvier</div>
    </div>""")

    st.html(f'<div style="height:1px;background:#E5E7EB;margin:12px 0;"></div>')
    st.html(f'<div style="font-size:10px;color:#9CA3AF;text-align:center;{F}">Supabase PostgreSQL</div>')

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
        td = df[df["technicien"] == tech]
        total   = round(td["points"].sum(), 1)
        n       = len(td)
        closed  = int(td["action"].isin(["closed","both"]).sum())
        raised  = int(td["action"].eq("raised").sum())
        bonus   = 5 if n >= 8 else 3 if n >= 5 else 0
        ml_pct  = round(min(100, (closed + raised*0.5) / n * 100 + bonus), 1) if n else 0
        txn     = int(td["categorie"].isin(["TXN","IPRAN","MW_FADING","MW_EQUIPMENT"]).sum())
        lb.append({"name":tech,"total":total,"n":n,"closed":closed,"ml_pct":ml_pct,
                   "txn_snags":txn,"trend":[]})
    lb.sort(key=lambda x: -x["total"])
    for i, t in enumerate(lb): t["rank"] = i+1
    return lb

lb        = build_leaderboard(snags_data)
total_pts = sum(t["total"] for t in lb)
mid_month = (now.day >= 15) if is_current_period else True
alert_set = {t["name"] for t in lb if t["ml_pct"] < 30 and mid_month}
drop_set  = set()

# Détection chute brutale (6 mois)
if lb:
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

# Snags en retard (> 7 jours)
overdue_snags = []
if snags_data:
    for s in snags_data:
        if s.get("action") in ["raised", "both"] and not s.get("date_ferme"):
            d0 = date.fromisoformat(str(s["date_snag"]))
            diff = (TODAY - d0).days
            if diff > 7:
                overdue_snags.append({**s, "days_open": diff})

# Alertes RCA
rca_alerts = 0
for r in rca_data:
    if not r.get("date_rca"):
        d0 = datetime.fromisoformat(str(r["date_incident"]))
        hrs = (datetime.now() - d0).total_seconds() / 3600
        if hrs >= 48:
            rca_alerts += 1

# ASSET deadline
asset_day    = 20
asset_dline  = date(sel_y, sel_m, asset_day)
days_to_asset = (asset_dline - TODAY).days
pending_asset = sum(1 for a in asset_data if not a.get("soumis"))

# ════════════════ HEADER ════════════════
n_alerts_total = len(alert_set) + rca_alerts + len(overdue_snags)
alert_color    = "#DC2626" if n_alerts_total > 0 else "#10B981"

st.html(f"""<div style="background:#FFFFFF;border:1px solid #E5E7EB;border-radius:12px;
    padding:16px 22px;margin-bottom:12px;box-shadow:0 1px 3px rgba(0,0,0,.05);">
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;">
        <div>
            <div style="font-size:22px;font-weight:800;color:#111827;{F}">
                MTN FLM — Tableau de Bord Manager
            </div>
            <div style="font-size:12px;color:#9CA3AF;margin-top:2px;{F}">
                {period_label} · South Region · Objectif : {obj_pts} pts
            </div>
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
            <div style="background:{alert_color}18;border:1px solid {alert_color}44;
                border-radius:8px;padding:6px 14px;font-size:11px;
                color:{alert_color};font-weight:700;{F}">
                {'⚠ ' if n_alerts_total else '✓ '}{n_alerts_total} alerte{'s' if n_alerts_total!=1 else ''} active{'s' if n_alerts_total!=1 else ''}
            </div>
            <div style="background:#FFFBEB;border:1px solid #FDE68A;border-radius:8px;
                padding:6px 14px;font-size:11px;color:#92400E;font-weight:600;{F}">
                {len(lb)} technicien{'s' if len(lb)!=1 else ''} · {round(total_pts,1)} pts
            </div>
        </div>
    </div>
</div>""")

# ════════════════ ONGLETS ════════════════
(tab_overview, tab_techs, tab_snags,
 tab_mgmt, tab_blockers, tab_trend, tab_ai) = st.tabs([
    "📊 Vue globale",
    "👷 Techniciens",
    "🔧 Snags",
    "📋 RCA & ASSET",
    "🚧 Points bloquants",
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

    # Progression équipe
    team_pct = round(total_pts / obj_pts * 100, 1) if obj_pts else 0
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

    # Tableau individuel
    if lb:
        st.html(section_label("PROGRESSION INDIVIDUELLE"))
        for t in lb:
            t_pct   = round(t["total"]/obj_pts*100, 1) if obj_pts else 0
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
            st.html(f"""<div style="{bg}{bdr}border-radius:10px;padding:10px 14px;margin-bottom:6px;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                    <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
                        <span style="font-size:13px;font-weight:700;
                            color:{'#DC2626' if is_alrt else '#111827'};{F}">{medal} {t['name']}</span>
                        {tags}
                    </div>
                    <div style="display:flex;align-items:center;gap:14px;">
                        <span style="font-size:11px;color:#9CA3AF;{F}">{t['total']} / {obj_pts} pts</span>
                        <span style="font-size:15px;font-weight:800;color:{t_col};{F}">{t_pct}%</span>
                    </div>
                </div>
                {obj_bar_html(t_pct, 8)}
                <div style="font-size:10px;color:#9CA3AF;margin-top:4px;{F}">
                    {t['n']} snags · {t['closed']} fermés · {t['ml_pct']}% fermeture · {t['txn_snags']} TXN
                </div>
            </div>""")

    # Graphiques
    if lb:
        cl, cr = st.columns([3,2])
        with cl:
            st.html(section_label("POINTS PAR TECHNICIEN"))
            rank_colors = {1:"#FFD200",2:"#6366F1",3:"#10B981"}
            bar_colors  = [rank_colors.get(t["rank"],"#94A3B8") for t in lb]
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=[t["total"] for t in lb],
                y=[f"{'🥇' if t['rank']==1 else '🥈' if t['rank']==2 else '🥉' if t['rank']==3 else str(t['rank'])+' '} {t['name']}" for t in lb],
                orientation="h",
                marker=dict(color=bar_colors, cornerradius=5),
                text=[f"  {t['total']} pts" for t in lb],
                textposition="inside", insidetextanchor="end",
                textfont=dict(size=11, color=["#78350F" if t["rank"]==1 else "#FFFFFF" for t in lb],
                              family="Plus Jakarta Sans", weight="bold"),
            ))
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#FFFFFF",
                height=max(280, len(lb)*48), margin=dict(l=10,r=60,t=6,b=6),
                xaxis=dict(gridcolor="#F1F5F9", tickfont=dict(size=10,family="Plus Jakarta Sans")),
                yaxis=dict(gridcolor="rgba(0,0,0,0)",
                           tickfont=dict(size=11,family="Plus Jakarta Sans",weight="bold"),
                           autorange="reversed"),
                showlegend=False, bargap=0.3,
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})

        with cr:
            st.html(section_label("RÉPARTITION CATÉGORIES"))
            if snags_data:
                df_s = pd.DataFrame(snags_data)
                cp = df_s.groupby("categorie")["points"].sum().sort_values(ascending=False).head(8)
                mx = cp.max() or 1
                bcs = ["#FFD200","#6366F1","#10B981","#F59E0B","#EC4899","#8B5CF6","#14B8A6","#EF4444"]
                for idx, (cat, pts) in enumerate(cp.items()):
                    c_ = bcs[idx % len(bcs)]
                    pct_bar = pts/mx*100
                    st.html(f"""<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
                        <div style="font-size:11px;color:#374151;width:100px;flex-shrink:0;
                            overflow:hidden;text-overflow:ellipsis;white-space:nowrap;{F}">{cat}</div>
                        <div style="flex:1;background:#F1F5F9;border-radius:99px;height:6px;overflow:hidden;">
                            <div style="width:{pct_bar:.1f}%;height:100%;background:{c_};border-radius:99px;"></div></div>
                        <div style="font-size:11px;font-weight:700;color:{c_};width:28px;text-align:right;{F}">{pts:.0f}</div>
                    </div>""")


# ══════════════════════════════════════════════════════════════════
#  TAB 2 — TECHNICIENS (saisie / gestion)
# ══════════════════════════════════════════════════════════════════
with tab_techs:
    st.html(section_label("AJOUTER UN TECHNICIEN"))
    with st.form("form_add_tech", clear_on_submit=True):
        ca1, ca2, ca3, ca4 = st.columns([3,2,2,1])
        with ca1:
            new_nom    = st.text_input("Nom complet", placeholder="Prénom NOM…")
        with ca2:
            new_region = st.selectbox("Région", ["South","Brazzaville","Pool","Nord","Dolisie","Autre"])
        with ca3:
            new_equipe = st.selectbox("Équipe", ["FLM","FME","NOC","Back Office","Sous-traitant"])
        with ca4:
            st.markdown("<br>", unsafe_allow_html=True)
            add_btn = st.form_submit_button("✚ Ajouter", use_container_width=True)
        if add_btn:
            if not new_nom.strip():
                st.error("Nom requis")
            elif new_nom.strip().lower() in [t.lower() for t in techs_noms]:
                st.error("Ce technicien existe déjà")
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
        hdr = st.columns([0.4, 2.2, 1.2, 1.2, 1, 0.8, 0.8, 0.8])
        for col, h in zip(hdr, ["#","NOM","RÉGION","ÉQUIPE","POINTS","SNAGS","FERMÉS",""]):
            col.markdown(f"<div style='font-size:10px;font-weight:700;color:#9CA3AF;letter-spacing:.06em;text-transform:uppercase;{F}'>{h}</div>", unsafe_allow_html=True)

        active_map = {t["name"]: t for t in lb}

        for i, tech in enumerate(techs_list):
            t   = active_map.get(tech["nom"])
            row = st.columns([0.4, 2.2, 1.2, 1.2, 1, 0.8, 0.8, 0.8])
            row[0].markdown(f"<div style='padding:8px 0;font-size:11px;color:#9CA3AF;{F}'>{i+1}</div>", unsafe_allow_html=True)
            is_alrt = tech["nom"] in alert_set
            name_col = "#DC2626" if is_alrt else "#111827"
            row[1].markdown(f"<div style='padding:8px 0;font-size:12px;font-weight:700;color:{name_col};{F}'>{'⚠ ' if is_alrt else ''}{tech['nom']}</div>", unsafe_allow_html=True)
            row[2].markdown(f"<div style='padding:8px 0;font-size:11px;color:#6B7280;{F}'>{tech['region']}</div>", unsafe_allow_html=True)
            row[3].markdown(f"<div style='padding:8px 0;font-size:11px;color:#6B7280;{F}'>{tech['equipe']}</div>", unsafe_allow_html=True)

            if t:
                row[4].markdown(f"<div style='padding:8px 0;font-size:13px;font-weight:800;color:#D97706;{F}'>{t['total']}</div>", unsafe_allow_html=True)
                row[5].markdown(f"<div style='padding:8px 0;font-size:12px;color:#374151;text-align:center;{F}'>{t['n']}</div>", unsafe_allow_html=True)
                row[6].markdown(f"<div style='padding:8px 0;font-size:12px;color:#6366F1;font-weight:700;text-align:center;{F}'>{t['closed']}</div>", unsafe_allow_html=True)
            else:
                for col_ in [row[4], row[5], row[6]]:
                    col_.markdown(f"<div style='color:#D1D5DB;padding:8px 0;text-align:center;{F}'>—</div>", unsafe_allow_html=True)

            with row[7]:
                sub1, sub2 = st.columns(2)
                with sub1:
                    if st.button("✎", key=f"ren_tech_{tech['id']}", help="Renommer"):
                        st.session_state[f"renaming_tech_{tech['id']}"] = True
                with sub2:
                    if st.button("✕", key=f"del_tech_{tech['id']}", help="Supprimer"):
                        delete_tech(tech["id"])
                        st.cache_data.clear(); st.rerun()

            if st.session_state.get(f"renaming_tech_{tech['id']}"):
                with st.form(f"ren_form_{tech['id']}"):
                    rn1, rn2, rn3, rn4 = st.columns([2.5, 1.5, 1.5, 0.8])
                    new_rnom  = rn1.text_input("Nom", value=tech["nom"], label_visibility="collapsed")
                    new_rreg  = rn2.selectbox("Région", ["South","Brazzaville","Pool","Nord","Dolisie","Autre"],
                                              index=["South","Brazzaville","Pool","Nord","Dolisie","Autre"].index(tech["region"]) if tech["region"] in ["South","Brazzaville","Pool","Nord","Dolisie","Autre"] else 0,
                                              label_visibility="collapsed")
                    new_req   = rn3.selectbox("Équipe", ["FLM","FME","NOC","Back Office","Sous-traitant"],
                                              index=["FLM","FME","NOC","Back Office","Sous-traitant"].index(tech["equipe"]) if tech["equipe"] in ["FLM","FME","NOC","Back Office","Sous-traitant"] else 0,
                                              label_visibility="collapsed")
                    ok = rn4.form_submit_button("✓ OK")
                    if ok:
                        update_tech(tech["id"], new_rnom.strip(), new_rreg, new_req)
                        st.session_state[f"renaming_tech_{tech['id']}"] = False
                        st.cache_data.clear(); st.rerun()

            st.html('<div style="height:1px;background:#F3F4F6;"></div>')

        with st.expander("⚠ Zone dangereuse"):
            if st.button("🗑 Supprimer tous les techniciens", use_container_width=True):
                for t in techs_list:
                    delete_tech(t["id"])
                st.cache_data.clear(); st.rerun()

    # Techniciens avec données mais non enregistrés
    extras = [t for t in lb if t["name"] not in techs_noms]
    if extras:
        st.html(section_label("TECHNICIENS AVEC DONNÉES MAIS NON ENREGISTRÉS"))
        for t in extras:
            xe1, xe2 = st.columns([4,1])
            xe1.markdown(f"<div style='font-size:12px;color:#9CA3AF;padding:6px 0;{F}'>{t['name']} — {t['total']} pts</div>", unsafe_allow_html=True)
            with xe2:
                if st.button("+ Enregistrer", key=f"reg_{t['name']}"):
                    add_tech(t["name"])
                    st.cache_data.clear(); st.rerun()


# ══════════════════════════════════════════════════════════════════
#  TAB 3 — SNAGS
# ══════════════════════════════════════════════════════════════════
with tab_snags:
    edit_snag_id   = st.session_state.get("edit_snag_id", None)
    edit_snag_data = {}
    if edit_snag_id and snags_data:
        rows = [s for s in snags_data if s["id"] == edit_snag_id]
        if rows: edit_snag_data = rows[0]

    st.html(section_label(f"{'✎ MODIFIER' if edit_snag_id else '✚ NOUVEAU SNAG'} — {period_label}"))

    with st.form("form_snag"):
        sr1, sr2 = st.columns(2)
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

        sr3, sr4, sr5 = st.columns(3)
        with sr3:
            site_id_v = st.text_input("Site ID", value=edit_snag_data.get("site_id",""),
                                      placeholder="CG_DOL_001")
        with sr4:
            cat_def = CATEGORIES.index(edit_snag_data.get("categorie","DG")) if edit_snag_data.get("categorie","DG") in CATEGORIES else 0
            cat = st.selectbox("Catégorie",CATEGORIES,index=cat_def,
                               format_func=lambda x:f"{x}  ({SUB_SCORES[x]} pts)")
        with sr5:
            d_def = edit_snag_data.get("date_snag", TODAY)
            if isinstance(d_def, str): d_def = date.fromisoformat(d_def)
            snag_date = st.date_input("Date", value=d_def)

        act_opts = {"raised":"↑ Remonté — 40%","closed":"✓ Fermé — 60%","both":"⟳ R+F — 100%"}
        def_act = list(act_opts.keys()).index(edit_snag_data.get("action","closed")) if edit_snag_data.get("action") in act_opts else 1
        action = st.radio("Action", list(act_opts.keys()),
                          format_func=lambda x: act_opts[x],
                          index=def_act, horizontal=True)

        desc = st.text_input("Description", value=edit_snag_data.get("description",""),
                             placeholder="Description optionnelle…")

        pts_prev = calc_pts(cat, action)
        ac = ACTION_COLOR.get(action,"#6B7280")
        st.html(f"""<div style="background:#F9FAFB;border:1px solid #E5E7EB;border-radius:8px;
            padding:10px 14px;display:flex;justify-content:space-between;align-items:center;">
            <div style="font-size:11px;color:#6B7280;{F}">
                Base : {SUB_SCORES[cat]} pts × {ACTION_FACTOR[action]}
            </div>
            <div style="font-size:28px;font-weight:800;color:{ac};{F}">{pts_prev} pts</div>
        </div>""")

        if edit_snag_id:
            sb1, sb2 = st.columns([3,1])
            with sb1: submitted = st.form_submit_button("METTRE À JOUR", use_container_width=True)
            with sb2:
                if st.form_submit_button("Annuler", use_container_width=True):
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
                       "auditeur":auditeur.strip() or None,
                       "description":desc.strip(),"points":pts_prev,"annee":sel_y,"mois":sel_m}
                ok = update_snag_manager(edit_snag_id, row) if edit_snag_id else insert_snag_manager(row)
                if ok:
                    st.success(f"✓ Snag {'mis à jour' if edit_snag_id else 'enregistré'} (+{pts_prev} pts)")
                    st.session_state["edit_snag_id"] = None
                    st.cache_data.clear(); st.rerun()

    # Snags en retard
    if overdue_snags:
        st.html(section_label(f"🔴 SNAGS EN RETARD (>{7}j) — {len(overdue_snags)} cas"))
        for s in overdue_snags:
            aud = f"· Auditeur : <strong>{s['auditeur']}</strong>" if s.get("auditeur") else ""
            st.html(f"""<div style="background:#FEF2F2;border:1px solid #FECACA;border-radius:8px;
                padding:8px 14px;margin-bottom:6px;display:flex;justify-content:space-between;align-items:center;">
                <div>
                    <span style="font-size:12px;font-weight:700;color:#DC2626;{F}">{s['technicien']}</span>
                    <span style="font-size:11px;color:#6B7280;{F}"> · {s['site_nom']} · {s['categorie']}</span>
                    <div style="font-size:11px;color:#9CA3AF;margin-top:2px;{F}">
                        Depuis le {s['date_snag']} {aud}
                    </div>
                </div>
                {status_badge_snag(s['days_open'])}
            </div>""")

    # Liste des snags
    st.html(section_label(f"TOUS LES SNAGS — {period_label} ({len(snags_data)})"))
    if snags_data:
        hdr2 = st.columns([1,1.5,1.5,1,1,1,0.7,1])
        for col, h in zip(hdr2, ["DATE","TECH.","SITE","CAT.","ACTION","AUDITEUR","PTS",""]):
            col.markdown(f"<div style='font-size:10px;font-weight:700;color:#9CA3AF;letter-spacing:.06em;text-transform:uppercase;{F}'>{h}</div>", unsafe_allow_html=True)

        for s in snags_data:
            d0 = date.fromisoformat(str(s["date_snag"]))
            days_open = (TODAY - d0).days
            bg = "#FFF5F5" if days_open > 7 and s["action"] in ["raised","both"] and not s.get("date_ferme") else "#FFFFFF"

            row = st.columns([1,1.5,1.5,1,1,1,0.7,1])
            row[0].markdown(f"<div style='font-size:11px;color:#9CA3AF;padding:6px 0;{F}'>{s['date_snag']}</div>", unsafe_allow_html=True)
            row[1].markdown(f"<div style='font-size:12px;font-weight:600;color:#111827;padding:6px 0;{F}'>{s['technicien']}</div>", unsafe_allow_html=True)
            row[2].markdown(f"<div style='font-size:11px;color:#374151;padding:6px 0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;{F}'>{s['site_nom']}</div>", unsafe_allow_html=True)
            row[3].markdown(f"<div style='font-size:11px;padding:6px 0;{F}'>{s['categorie']}</div>", unsafe_allow_html=True)
            ac_ = ACTION_COLOR.get(s["action"],"#9CA3AF")
            row[4].html(f"<div style='padding:6px 0;'><span style='background:{ac_}22;color:{ac_};font-size:10px;font-weight:700;border-radius:12px;padding:2px 7px;{F}'>{ACTION_LABEL.get(s['action'],s['action'])}</span></div>")
            aud_str = s.get("auditeur") or "—"
            row[5].markdown(f"<div style='font-size:11px;color:#6B7280;padding:6px 0;{F}'>{aud_str}</div>", unsafe_allow_html=True)
            row[6].markdown(f"<div style='font-size:13px;font-weight:800;color:#D97706;padding:6px 0;text-align:center;{F}'>{s['points']}</div>", unsafe_allow_html=True)

            with row[7]:
                btn1, btn2 = st.columns(2)
                with btn1:
                    if st.button("✎", key=f"e_snag_{s['id']}"):
                        st.session_state["edit_snag_id"] = s["id"]; st.rerun()
                with btn2:
                    ck = f"confirm_del_snag_{s['id']}"
                    if st.session_state.get(ck):
                        cc1, cc2 = st.columns(2)
                        if cc1.button("✓", key=f"yes_snag_{s['id']}"):
                            delete_snag_manager(s["id"])
                            st.session_state[ck] = False
                            st.cache_data.clear(); st.rerun()
                        if cc2.button("✗", key=f"no_snag_{s['id']}"):
                            st.session_state[ck] = False; st.rerun()
                    else:
                        if st.button("🗑", key=f"d_snag_{s['id']}"):
                            st.session_state[ck] = True; st.rerun()
            st.html('<div style="height:1px;background:#F3F4F6;"></div>')
    else:
        st.html(f"""<div style="background:#F9FAFB;border:2px dashed #E5E7EB;
            border-radius:10px;padding:30px;text-align:center;">
            <div style="font-size:12px;color:#9CA3AF;{F}">Aucun snag pour {period_label}</div>
        </div>""")


# ══════════════════════════════════════════════════════════════════
#  TAB 4 — RCA & ASSET (Management)
# ══════════════════════════════════════════════════════════════════
with tab_mgmt:
    st.html(f"""<div style="background:#EFF6FF;border:1.5px solid #BFDBFE;border-radius:10px;
        padding:12px 16px;margin-bottom:16px;">
        <div style="font-size:11px;font-weight:700;color:#1D4ED8;letter-spacing:.06em;text-transform:uppercase;{F}">
            📋 RUBRIQUE MANAGEMENT — RCA & ASSET
        </div>
        <div style="font-size:11px;color:#3B82F6;margin-top:3px;{F}">
            RCA : délai 48h · alerte rouge à 72h &nbsp;|&nbsp;
            ASSET : deadline le 20 de chaque mois
        </div>
    </div>""")

    rca_tab, asset_tab = st.tabs(["📄 Suivi RCA","📦 Suivi ASSET"])

    # ── RCA ──────────────────────────────────────────────────────
    with rca_tab:
        edit_rca_id = st.session_state.get("edit_rca_id", None)
        edit_rca    = {}
        if edit_rca_id and rca_data:
            rows = [r for r in rca_data if r["id"] == edit_rca_id]
            if rows: edit_rca = rows[0]

        st.html(section_label(f"{'✎ MODIFIER RCA' if edit_rca_id else '✚ NOUVEAU RCA'} — {period_label}"))

        with st.form("form_rca"):
            fr1, fr2 = st.columns(2)
            with fr1:
                rca_resp_opts = ["— Choisir —"] + techs_noms
                def_ri = (techs_noms.index(edit_rca.get("responsable",""))+1
                          if edit_rca.get("responsable") in techs_noms else 0)
                rca_resp_sel = st.selectbox("Responsable RCA (liste)", rca_resp_opts, index=def_ri)
                rca_resp_man = st.text_input("Ou saisir manuellement",
                                             value=edit_rca.get("responsable",""),
                                             placeholder="Prénom NOM…")
            with fr2:
                rca_site = st.text_input("Site", value=edit_rca.get("site_nom",""),
                                         placeholder="Nom du site")
                rca_inc  = st.text_input("Description incident",
                                         value=edit_rca.get("incident",""),
                                         placeholder="Ex : Panne DG totale")

            fr3, fr4, fr5 = st.columns(3)
            with fr3:
                d_inc_def = edit_rca.get("date_incident", datetime.now())
                if isinstance(d_inc_def, str):
                    d_inc_def = datetime.fromisoformat(d_inc_def.replace("Z",""))
                rca_date_inc = st.date_input("Date incident", value=d_inc_def.date() if hasattr(d_inc_def,"date") else d_inc_def)
                rca_time_inc = st.time_input("Heure incident", value=d_inc_def.time() if hasattr(d_inc_def,"time") else datetime.now().time())
            with fr4:
                rca_submitted = st.checkbox("RCA soumis", value=bool(edit_rca.get("date_rca")))
                if rca_submitted:
                    d_rca_def = edit_rca.get("date_rca", datetime.now())
                    if isinstance(d_rca_def, str):
                        d_rca_def = datetime.fromisoformat(d_rca_def.replace("Z",""))
                    rca_date_sub = st.date_input("Date soumission RCA", value=d_rca_def.date() if hasattr(d_rca_def,"date") else TODAY)
                    rca_time_sub = st.time_input("Heure soumission", value=d_rca_def.time() if hasattr(d_rca_def,"time") else datetime.now().time())
                else:
                    rca_date_sub = None; rca_time_sub = None
            with fr5:
                rca_statut = st.selectbox("Statut", ["pending","submitted","validated"],
                                          format_func=lambda x:{"pending":"En attente","submitted":"Soumis","validated":"Validé"}[x],
                                          index=["pending","submitted","validated"].index(edit_rca.get("statut","pending")))
                rca_comment = st.text_input("Commentaire", value=edit_rca.get("commentaire",""))

            if edit_rca_id:
                rb1, rb2 = st.columns([3,1])
                with rb1: rca_ok = st.form_submit_button("METTRE À JOUR RCA", use_container_width=True)
                with rb2:
                    if st.form_submit_button("Annuler"):
                        st.session_state["edit_rca_id"] = None; st.rerun()
            else:
                rca_ok = st.form_submit_button("ENREGISTRER RCA", use_container_width=True)

            if rca_ok:
                resp_ = rca_resp_man.strip() if rca_resp_man.strip() else (rca_resp_sel if rca_resp_sel != "— Choisir —" else "")
                if not resp_: st.error("Responsable requis")
                elif not rca_site.strip(): st.error("Site requis")
                elif not rca_inc.strip(): st.error("Incident requis")
                else:
                    d_rca_str = (str(datetime.combine(rca_date_sub, rca_time_sub)) if rca_submitted and rca_date_sub else None)
                    row = {"responsable":resp_,"site_nom":rca_site.strip(),
                           "incident":rca_inc.strip(),
                           "date_incident":str(datetime.combine(rca_date_inc, rca_time_inc)),
                           "date_rca":d_rca_str,"statut":rca_statut,
                           "commentaire":rca_comment.strip(),"annee":sel_y,"mois":sel_m}
                    ok = update_rca(edit_rca_id, row) if edit_rca_id else insert_rca(row)
                    if ok:
                        st.success("✓ RCA enregistré")
                        st.session_state["edit_rca_id"] = None
                        st.cache_data.clear(); st.rerun()

        # Liste RCA
        st.html(section_label(f"LISTE RCA — {period_label} ({len(rca_data)})"))
        if rca_data:
            for r in rca_data:
                d_inc = datetime.fromisoformat(str(r["date_incident"]).replace("Z",""))
                if r.get("date_rca"):
                    d_rca = datetime.fromisoformat(str(r["date_rca"]).replace("Z",""))
                    hrs   = (d_rca - d_inc).total_seconds() / 3600
                else:
                    hrs   = (datetime.now() - d_inc).total_seconds() / 3600
                    if r.get("statut") == "validated": hrs = None

                statut_map = {"pending":"En attente","submitted":"Soumis","validated":"Validé"}
                sc1, sc2, sc3, sc4 = st.columns([2.5, 2, 1.5, 0.8])
                bg_rca = "#FEF2F2" if (hrs and hrs >= 72) else "#FFFBEB" if (hrs and hrs >= 48) else "#F0FDF4"
                sc1.html(f"""<div style="background:{bg_rca};border-radius:8px;padding:8px 12px;margin-bottom:4px;">
                    <div style="font-size:12px;font-weight:700;color:#111827;{F}">{r['responsable']}</div>
                    <div style="font-size:11px;color:#6B7280;{F}">{r['site_nom']} · {r['incident']}</div>
                    <div style="font-size:10px;color:#9CA3AF;margin-top:3px;{F}">Incident: {d_inc.strftime('%d/%m %H:%M')}</div>
                </div>""")
                sc2.html(f"""<div style="padding:8px 0;">
                    <div style="font-size:11px;color:#6B7280;{F}">{statut_map.get(r.get('statut','pending'),'—')}</div>
                    {f'<div style="font-size:10px;color:#9CA3AF;{F}">RCA: {datetime.fromisoformat(str(r["date_rca"]).replace(chr(90),"")).strftime("%d/%m %H:%M")}</div>' if r.get("date_rca") else f'<div style="font-size:10px;color:#DC2626;font-weight:700;{F}">RCA non soumis</div>'}
                    {f'<div style="font-size:10px;color:#9CA3AF;{F}">{r["commentaire"]}</div>' if r.get("commentaire") else ''}
                </div>""")
                sc3.html(f"<div style='padding:10px 0;'>{status_badge_rca(hrs)}</div>")
                with sc4:
                    rb_e, rb_d = st.columns(2)
                    if rb_e.button("✎", key=f"e_rca_{r['id']}"):
                        st.session_state["edit_rca_id"] = r["id"]; st.rerun()
                    if rb_d.button("🗑", key=f"d_rca_{r['id']}"):
                        delete_rca(r["id"]); st.cache_data.clear(); st.rerun()
                st.html('<div style="height:1px;background:#F3F4F6;"></div>')
        else:
            st.html(f"""<div style="background:#F9FAFB;border:2px dashed #E5E7EB;border-radius:10px;
                padding:24px;text-align:center;">
                <div style="font-size:12px;color:#9CA3AF;{F}">Aucun RCA pour {period_label}</div>
            </div>""")

    # ── ASSET ─────────────────────────────────────────────────────
    with asset_tab:
        deadline_asset = date(sel_y, sel_m, 20)
        days_left_asset = (deadline_asset - TODAY).days
        badge_color = "#EF4444" if days_left_asset <= 3 else "#F59E0B" if days_left_asset <= 7 else "#10B981"
        st.html(f"""<div style="background:#FFFBEB;border:1.5px solid #FDE68A;border-radius:10px;
            padding:12px 16px;margin-bottom:12px;display:flex;justify-content:space-between;align-items:center;">
            <div style="font-size:12px;font-weight:700;color:#92400E;{F}">
                📦 Deadline ASSET : {deadline_asset.strftime('%d %B %Y')}
            </div>
            <span style="background:{badge_color}22;color:{badge_color};border:1px solid {badge_color}44;
                font-size:12px;font-weight:700;border-radius:8px;padding:4px 12px;{F}">
                {'J-'+str(days_left_asset) if days_left_asset >= 0 else '⚠ Dépassé'}
            </span>
        </div>""")

        edit_ast_id = st.session_state.get("edit_ast_id", None)
        edit_ast    = {}
        if edit_ast_id and asset_data:
            rows = [a for a in asset_data if a["id"] == edit_ast_id]
            if rows: edit_ast = rows[0]

        st.html(section_label(f"{'✎ MODIFIER' if edit_ast_id else '✚ AJOUTER'} — ASSET"))
        with st.form("form_asset"):
            fa1, fa2, fa3 = st.columns([2, 1.5, 1])
            with fa1:
                ast_nom_opts = ["— Choisir —"] + techs_noms
                def_ai = (techs_noms.index(edit_ast.get("nom",""))+1
                          if edit_ast.get("nom") in techs_noms else 0)
                ast_nom_sel = st.selectbox("Responsable ASSET (liste)", ast_nom_opts, index=def_ai)
                ast_nom_man = st.text_input("Ou saisir manuellement",
                                            value=edit_ast.get("nom",""),
                                            placeholder="Prénom NOM…")
            with fa2:
                ast_region = st.selectbox("Région",
                                          ["South","Brazzaville","Pool","Nord","Dolisie","Autre"],
                                          index=["South","Brazzaville","Pool","Nord","Dolisie","Autre"].index(edit_ast.get("region","South")) if edit_ast.get("region","South") in ["South","Brazzaville","Pool","Nord","Dolisie","Autre"] else 0)
                ast_sites = st.number_input("Nb de sites", min_value=0, max_value=500,
                                            value=edit_ast.get("site_count",0))
            with fa3:
                ast_soumis = st.checkbox("Soumis", value=bool(edit_ast.get("soumis",False)))
                if ast_soumis:
                    d_ast_def = edit_ast.get("date_soumis", TODAY)
                    if isinstance(d_ast_def, str): d_ast_def = date.fromisoformat(d_ast_def)
                    ast_date_soumis = st.date_input("Date soumission", value=d_ast_def)
                else:
                    ast_date_soumis = None
            ast_comment = st.text_input("Commentaire", value=edit_ast.get("commentaire",""))

            if edit_ast_id:
                ab1, ab2 = st.columns([3,1])
                with ab1: ast_ok = st.form_submit_button("METTRE À JOUR ASSET", use_container_width=True)
                with ab2:
                    if st.form_submit_button("Annuler"):
                        st.session_state["edit_ast_id"] = None; st.rerun()
            else:
                ast_ok = st.form_submit_button("ENREGISTRER ASSET", use_container_width=True)

            if ast_ok:
                nom_ = ast_nom_man.strip() if ast_nom_man.strip() else (ast_nom_sel if ast_nom_sel != "— Choisir —" else "")
                if not nom_: st.error("Nom requis")
                else:
                    row = {"nom":nom_,"region":ast_region,"site_count":ast_sites,
                           "soumis":ast_soumis,
                           "date_soumis":str(ast_date_soumis) if ast_soumis and ast_date_soumis else None,
                           "commentaire":ast_comment.strip(),"annee":sel_y,"mois":sel_m}
                    ok = update_asset(edit_ast_id, row) if edit_ast_id else insert_asset(row)
                    if ok:
                        st.success("✓ ASSET enregistré")
                        st.session_state["edit_ast_id"] = None
                        st.cache_data.clear(); st.rerun()

        # Liste ASSET
        submitted_c = sum(1 for a in asset_data if a.get("soumis"))
        pending_c   = len(asset_data) - submitted_c
        ac1, ac2, ac3 = st.columns(3)
        ac1.html(kpi_card("Total ASSET", str(len(asset_data)), f"{period_label}"))
        ac2.html(kpi_card("Soumis", str(submitted_c), "dans les délais","#10B981"))
        ac3.html(kpi_card("En attente", str(pending_c), "non soumis","#EF4444" if pending_c else "#10B981"))

        st.html(section_label(f"LISTE ASSET — {period_label} ({len(asset_data)})"))
        if asset_data:
            for a in asset_data:
                sc1, sc2, sc3, sc4 = st.columns([2, 1.2, 1.5, 0.8])
                bg_a = "#F0FDF4" if a.get("soumis") else "#FFFBEB"
                sc1.html(f"""<div style="background:{bg_a};border-radius:8px;padding:8px 12px;margin-bottom:4px;">
                    <div style="font-size:12px;font-weight:700;color:#111827;{F}">{a['nom']}</div>
                    <div style="font-size:11px;color:#6B7280;{F}">{a['region']} · {a['site_count']} sites</div>
                </div>""")
                sc2.html(f"<div style='padding:10px 0;'>"
                         f"{'<span style=\"background:#D1FAE5;color:#065F46;border-radius:12px;padding:3px 10px;font-size:11px;font-weight:700;\">✓ Soumis</span>' if a.get('soumis') else '<span style=\"background:#FEF3C7;color:#92400E;border-radius:12px;padding:3px 10px;font-size:11px;font-weight:700;\">⏳ En attente</span>'}"
                         f"</div>")
                sc3.html(f"<div style='font-size:11px;color:#9CA3AF;padding:10px 0;{F}'>"
                         f"{('Le '+str(a['date_soumis'])) if a.get('date_soumis') else 'Date soumission non renseignée'}"
                         f"{'<br>'+a['commentaire'] if a.get('commentaire') else ''}"
                         f"</div>")
                with sc4:
                    ae1, ae2 = st.columns(2)
                    if ae1.button("✎", key=f"e_ast_{a['id']}"):
                        st.session_state["edit_ast_id"] = a["id"]; st.rerun()
                    if ae2.button("🗑", key=f"d_ast_{a['id']}"):
                        delete_asset(a["id"]); st.cache_data.clear(); st.rerun()
                st.html('<div style="height:1px;background:#F3F4F6;"></div>')
        else:
            st.html(f"""<div style="background:#F9FAFB;border:2px dashed #E5E7EB;border-radius:10px;
                padding:24px;text-align:center;">
                <div style="font-size:12px;color:#9CA3AF;{F}">Aucun ASSET enregistré pour {period_label}</div>
            </div>""")


# ══════════════════════════════════════════════════════════════════
#  TAB 5 — POINTS BLOQUANTS
# ══════════════════════════════════════════════════════════════════
with tab_blockers:
    edit_blk_id = st.session_state.get("edit_blk_id", None)
    edit_blk    = {}
    if edit_blk_id and blockers_d:
        rows = [b for b in blockers_d if b["id"] == edit_blk_id]
        if rows: edit_blk = rows[0]

    open_blk   = [b for b in blockers_d if not b.get("resolu")]
    closed_blk = [b for b in blockers_d if b.get("resolu")]

    bk1, bk2 = st.columns(2)
    bk1.html(kpi_card("Points bloquants ouverts", str(len(open_blk)), "action requise",
                       "#EF4444" if open_blk else "#10B981"))
    bk2.html(kpi_card("Résolus ce mois", str(len(closed_blk)), f"sur {len(blockers_d)} total","#10B981"))

    st.html(section_label(f"{'✎ MODIFIER' if edit_blk_id else '✚ SIGNALER'} UN POINT BLOQUANT"))
    with st.form("form_blocker"):
        bb1, bb2 = st.columns(2)
        with bb1:
            blk_tech_opts = ["— Choisir —"] + techs_noms
            def_bi = (techs_noms.index(edit_blk.get("technicien",""))+1
                      if edit_blk.get("technicien") in techs_noms else 0)
            blk_tech_sel = st.selectbox("Technicien concerné (liste)", blk_tech_opts, index=def_bi)
            blk_tech_man = st.text_input("Ou saisir manuellement",
                                         value=edit_blk.get("technicien",""),
                                         placeholder="Prénom NOM…")
        with bb2:
            blk_site = st.text_input("Site", value=edit_blk.get("site_nom",""),
                                     placeholder="Nom du site")
            blk_cat  = st.selectbox("Catégorie", ["—"] + CATEGORIES,
                                    index=CATEGORIES.index(edit_blk.get("categorie","DG"))+1
                                    if edit_blk.get("categorie") in CATEGORIES else 0)

        blk_desc = st.text_area("Description du blocage", value=edit_blk.get("description",""),
                                placeholder="Expliquer pourquoi le snag ne peut pas être fermé…",
                                height=80)

        bb3, bb4, bb5 = st.columns(3)
        with bb3:
            d_blk_def = edit_blk.get("date_signal", TODAY)
            if isinstance(d_blk_def, str): d_blk_def = date.fromisoformat(d_blk_def)
            blk_date = st.date_input("Date signalement", value=d_blk_def)
        with bb4:
            blk_resolu = st.checkbox("Résolu", value=bool(edit_blk.get("resolu",False)))
            if blk_resolu:
                d_res_def = edit_blk.get("date_resolu", TODAY)
                if isinstance(d_res_def, str) and d_res_def: d_res_def = date.fromisoformat(d_res_def)
                blk_date_res = st.date_input("Date résolution", value=d_res_def or TODAY)
            else:
                blk_date_res = None
        with bb5:
            st.markdown("<br>", unsafe_allow_html=True)

        if edit_blk_id:
            pb1, pb2 = st.columns([3,1])
            with pb1: blk_ok = st.form_submit_button("METTRE À JOUR", use_container_width=True)
            with pb2:
                if st.form_submit_button("Annuler"):
                    st.session_state["edit_blk_id"] = None; st.rerun()
        else:
            blk_ok = st.form_submit_button("ENREGISTRER LE BLOCAGE", use_container_width=True)

        if blk_ok:
            tech_ = blk_tech_man.strip() if blk_tech_man.strip() else (blk_tech_sel if blk_tech_sel != "— Choisir —" else "")
            if not tech_: st.error("Technicien requis")
            elif not blk_desc.strip(): st.error("Description requise")
            elif not blk_site.strip(): st.error("Site requis")
            else:
                row = {"technicien":tech_,"site_nom":blk_site.strip(),
                       "categorie":blk_cat if blk_cat != "—" else None,
                       "description":blk_desc.strip(),"date_signal":str(blk_date),
                       "resolu":blk_resolu,
                       "date_resolu":str(blk_date_res) if blk_resolu and blk_date_res else None,
                       "annee":sel_y,"mois":sel_m}
                ok = update_blocker(edit_blk_id, row) if edit_blk_id else insert_blocker(row)
                if ok:
                    st.success("✓ Point bloquant enregistré")
                    st.session_state["edit_blk_id"] = None
                    st.cache_data.clear(); st.rerun()

    if open_blk:
        st.html(section_label(f"🔴 BLOCAGES OUVERTS ({len(open_blk)})"))
        for b in open_blk:
            days_blk = (TODAY - date.fromisoformat(str(b["date_signal"]))).days
            bc1, bc2, bc3 = st.columns([3, 1, 0.8])
            bc1.html(f"""<div style="background:#FEF2F2;border:1px solid #FECACA;
                border-radius:8px;padding:8px 12px;margin-bottom:4px;">
                <div style="font-size:12px;font-weight:700;color:#DC2626;{F}">
                    🔒 {b['technicien']} — {b['site_nom']}
                    {f'<span style="font-size:10px;background:#FEE2E2;border-radius:4px;padding:1px 6px;margin-left:6px;">{b["categorie"]}</span>' if b.get('categorie') else ''}
                </div>
                <div style="font-size:11px;color:#374151;margin-top:3px;{F}">{b['description']}</div>
                <div style="font-size:10px;color:#9CA3AF;margin-top:3px;{F}">Signalé le {b['date_signal']} · {days_blk} jours ouverts</div>
            </div>""")
            bc2.html(f"<div style='padding:12px 0;'><span style='background:#FEE2E2;color:#DC2626;font-size:11px;font-weight:700;border-radius:8px;padding:4px 10px;{F}'>J+{days_blk}</span></div>")
            with bc3:
                be1, be2 = st.columns(2)
                if be1.button("✎", key=f"e_blk_{b['id']}"):
                    st.session_state["edit_blk_id"] = b["id"]; st.rerun()
                if be2.button("🗑", key=f"d_blk_{b['id']}"):
                    delete_blocker(b["id"]); st.cache_data.clear(); st.rerun()

    if closed_blk:
        with st.expander(f"✅ Blocages résolus ({len(closed_blk)})"):
            for b in closed_blk:
                st.html(f"""<div style="background:#F0FDF4;border:1px solid #BBF7D0;
                    border-radius:8px;padding:8px 12px;margin-bottom:6px;">
                    <div style="font-size:12px;font-weight:700;color:#166534;{F}">
                        ✓ {b['technicien']} — {b['site_nom']}
                    </div>
                    <div style="font-size:11px;color:#374151;{F}">{b['description']}</div>
                    <div style="font-size:10px;color:#9CA3AF;{F}">Résolu le {b.get('date_resolu','—')}</div>
                </div>""")


# ══════════════════════════════════════════════════════════════════
#  TAB 6 — TENDANCES 6 MOIS
# ══════════════════════════════════════════════════════════════════
with tab_trend:
    st.html(section_label("ÉVOLUTION CUMULATIVE — 6 DERNIERS MOIS"))

    # Calculer les 6 derniers mois
    months_6 = []
    for i in range(5, -1, -1):
        d = date(CUR_Y, CUR_M, 1) - timedelta(days=30*i)
        months_6.append((d.year, d.month))

    labels_6 = [MONTHS_FR[m-1][:3]+f" {y}" for y,m in months_6]
    obj_6    = [obj_for_month(m) for y,m in months_6]

    # Récupérer les données pour chaque mois
    @st.cache_data(ttl=120, show_spinner=False)
    def load_6months():
        all_data = {}
        for y, m in months_6:
            data = fetch_snags_manager(y, m)
            all_data[(y,m)] = data
        return all_data

    data_6m = load_6months()

    # Techniciens actifs sur la période
    all_techs_6m = set()
    for data in data_6m.values():
        for s in data:
            all_techs_6m.add(s["technicien"])

    top_techs = list(all_techs_6m)[:8]  # max 8 pour lisibilité
    COLORS_6  = ["#FFD200","#6366F1","#10B981","#F59E0B","#EC4899","#8B5CF6","#14B8A6","#EF4444"]

    # Graphique évolution 6 mois
    fig_trend = go.Figure()
    for i, tech in enumerate(top_techs):
        y_vals = []
        for y, m in months_6:
            tech_pts = sum(s["points"] for s in data_6m[(y,m)] if s["technicien"] == tech)
            y_vals.append(round(tech_pts, 1))
        c_ = COLORS_6[i % len(COLORS_6)]
        fig_trend.add_trace(go.Scatter(
            x=labels_6, y=y_vals, name=tech,
            mode="lines+markers",
            line=dict(color=c_, width=2.5),
            marker=dict(size=7, color=c_),
            hovertemplate=f"<b>{tech}</b><br>%{{x}} : <b>%{{y}} pts</b><extra></extra>",
        ))

    # Ligne objectif progressif
    fig_trend.add_trace(go.Scatter(
        x=labels_6, y=obj_6, name="Objectif",
        mode="lines", line=dict(color="#EF4444", dash="dash", width=1.5),
        hovertemplate="Objectif : <b>%{y} pts</b><extra></extra>",
    ))

    fig_trend.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#FAFAFA",
        height=360, margin=dict(l=0, r=20, t=10, b=8),
        xaxis=dict(gridcolor="#F1F5F9", tickfont=dict(size=11, family="Plus Jakarta Sans")),
        yaxis=dict(gridcolor="#F1F5F9", tickfont=dict(size=11, family="Plus Jakarta Sans"), zeroline=False),
        legend=dict(font=dict(size=11, family="Plus Jakarta Sans"),
                    bgcolor="rgba(255,255,255,.92)", bordercolor="#E5E7EB", borderwidth=1),
        hoverlabel=dict(bgcolor="#FFF", font_size=11, font_family="Plus Jakarta Sans"),
    )
    st.plotly_chart(fig_trend, use_container_width=True, config={"displayModeBar":False})
    st.html(f'<div style="font-size:10px;color:#9CA3AF;text-align:center;margin-top:-6px;{F}">Courbe rouge pointillée = objectif progressif (+10%/mois)</div>')

    # Objectif progressif
    st.html(section_label("OBJECTIF PROGRESSIF — ÉVOLUTION AUTOMATIQUE"))
    fig_obj = go.Figure()
    fig_obj.add_trace(go.Bar(
        x=labels_6, y=obj_6,
        marker_color=["#FFD200" if (y,m)==(CUR_Y,CUR_M) else "#E5E7EB" for y,m in months_6],
        marker_line_width=0,
        text=[f"{v} pts" for v in obj_6],
        textposition="outside",
        textfont=dict(size=11, family="Plus Jakarta Sans"),
    ))
    fig_obj.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#FAFAFA",
        height=200, margin=dict(l=0, r=20, t=8, b=8),
        xaxis=dict(tickfont=dict(size=11, family="Plus Jakarta Sans")),
        yaxis=dict(gridcolor="#F1F5F9", tickfont=dict(size=10, family="Plus Jakarta Sans")),
        showlegend=False,
    )
    st.plotly_chart(fig_obj, use_container_width=True, config={"displayModeBar":False})

    # Taux de fermeture
    st.html(section_label("TAUX DE FERMETURE ÉQUIPE — 6 MOIS"))
    close_rates = []
    for y, m in months_6:
        data = data_6m[(y,m)]
        if data:
            n_total  = len(data)
            n_closed = sum(1 for s in data if s["action"] in ["closed","both"])
            close_rates.append(round(n_closed / n_total * 100, 1))
        else:
            close_rates.append(0)

    fig_close = go.Figure()
    fig_close.add_trace(go.Scatter(
        x=labels_6, y=close_rates, mode="lines+markers+text",
        line=dict(color="#10B981", width=2.5),
        marker=dict(size=8, color=close_rates, colorscale=[[0,"#EF4444"],[0.5,"#F59E0B"],[1,"#10B981"]]),
        text=[f"{v}%" for v in close_rates], textposition="top center",
        textfont=dict(size=11, family="Plus Jakarta Sans"),
        fill="tozeroy", fillcolor="rgba(16,185,129,0.06)",
    ))
    fig_close.add_hline(y=70, line_dash="dash", line_color="#6366F1", line_width=1,
                         annotation_text="Cible 70%",
                         annotation_font=dict(size=10, color="#6366F1", family="Plus Jakarta Sans"))
    fig_close.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#FAFAFA",
        height=220, margin=dict(l=0, r=20, t=20, b=8),
        xaxis=dict(tickfont=dict(size=11, family="Plus Jakarta Sans")),
        yaxis=dict(gridcolor="#F1F5F9", range=[0,115],
                   tickfont=dict(size=10, family="Plus Jakarta Sans"), ticksuffix="%"),
        showlegend=False,
    )
    st.plotly_chart(fig_close, use_container_width=True, config={"displayModeBar":False})

    # Diagramme en barres groupées
    st.html(section_label("PERFORMANCE PAR TECHNICIEN — DIAGRAMME EN BARRES"))
    monthly_totals = {}
    for tech in top_techs:
        monthly_totals[tech] = []
        for y, m in months_6:
            pts = sum(s["points"] for s in data_6m[(y,m)] if s["technicien"] == tech)
            monthly_totals[tech].append(round(pts,1))

    fig_bar_g = go.Figure()
    for i, tech in enumerate(top_techs):
        c_ = COLORS_6[i % len(COLORS_6)]
        fig_bar_g.add_trace(go.Bar(
            name=tech, x=labels_6, y=monthly_totals[tech],
            marker_color=c_, marker_line_width=0,
            hovertemplate=f"<b>{tech}</b><br>%{{x}} : %{{y}} pts<extra></extra>",
        ))
    fig_bar_g.update_layout(
        barmode="group",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#FAFAFA",
        height=300, margin=dict(l=0, r=20, t=8, b=8),
        xaxis=dict(tickfont=dict(size=11, family="Plus Jakarta Sans")),
        yaxis=dict(gridcolor="#F1F5F9", tickfont=dict(size=10, family="Plus Jakarta Sans")),
        legend=dict(font=dict(size=10, family="Plus Jakarta Sans"),
                    bgcolor="rgba(255,255,255,.9)", bordercolor="#E5E7EB", borderwidth=1,
                    orientation="h", y=-0.25),
        bargap=0.15, bargroupgap=0.05,
    )
    st.plotly_chart(fig_bar_g, use_container_width=True, config={"displayModeBar":False})


# ══════════════════════════════════════════════════════════════════
#  TAB 7 — ANALYSE IA (Claude)
# ══════════════════════════════════════════════════════════════════
with tab_ai:
    st.html(f"""<div style="background:#EFF6FF;border:1.5px solid #BFDBFE;border-radius:10px;
        padding:14px 16px;margin-bottom:16px;display:flex;align-items:center;gap:12px;">
        <div style="font-size:24px;">🤖</div>
        <div>
            <div style="font-size:13px;font-weight:700;color:#1D4ED8;{F}">Analyse IA — Propulsé par Claude (Anthropic)</div>
            <div style="font-size:11px;color:#3B82F6;margin-top:2px;{F}">
                Analyse de profil technicien · Détection anomalies · Recommandations managériales
            </div>
        </div>
    </div>""")

    ai_col1, ai_col2 = st.columns([1,1])

    with ai_col1:
        st.html(section_label("ANALYSE D'UN PROFIL TECHNICIEN"))
        ai_tech_opts = ["— Choisir un technicien —"] + (techs_noms if techs_noms else [t["name"] for t in lb])
        sel_ai_tech = st.selectbox("Technicien à analyser", ai_tech_opts, key="ai_tech_sel")

        if st.button("🔍 Analyser ce profil", use_container_width=True, key="btn_analyze"):
            if sel_ai_tech == "— Choisir un technicien —":
                st.error("Sélectionnez un technicien")
            else:
                td = next((t for t in lb if t["name"] == sel_ai_tech), None)
                rca_count = sum(1 for r in rca_data if r.get("responsable") == sel_ai_tech)
                blk_count = sum(1 for b in blockers_d if b.get("technicien") == sel_ai_tech and not b.get("resolu"))
                asset_ok  = any(a for a in asset_data if a.get("nom") == sel_ai_tech and a.get("soumis"))

                if td:
                    t_pct = round(td["total"] / obj_pts * 100, 1) if obj_pts else 0
                    is_drop = sel_ai_tech in drop_set
                    prompt = f"""Tu es un manager expert en performance terrain télécom MTN Congo, région South.

Analyse le profil FLM de {sel_ai_tech} pour {period_label} :

MÉTRIQUES :
- Points : {td['total']} / {obj_pts} pts (objectif progressif) → {t_pct}%
- Snags total : {td['n']} | Fermés : {td['closed']} | Taux fermeture : {td['ml_pct']}%
- Snags catégorie TXN/IPRAN/MW : {td['txn_snags']}
- Alerte fermeture : {'OUI (<30%)' if sel_ai_tech in alert_set else 'NON'}
- Chute de productivité détectée : {'OUI (baisse ≥30%)' if is_drop else 'NON'}
- RCA en charge : {rca_count}
- Points bloquants ouverts : {blk_count}
- ASSET soumis : {'OUI' if asset_ok else 'NON'}

RÈGLES D'ALERTE :
- 0 snag TXN → manque d'intervention sur infrastructure critique
- Taux fermeture <30% après le 15 du mois → alerte rouge
- Snag ouvert >7 jours → délai dépassé

Produis une analyse structurée (max 400 mots) avec :
1. **Évaluation globale** (1-2 phrases directes)
2. **Points forts** identifiés
3. **Axes d'amélioration critiques** (sois précis sur les lacunes ex: 0 TXN)
4. **Recommandation managériale** (action concrète à mener)

Ton : professionnel, factuel, bienveillant mais direct. En français."""
                else:
                    prompt = f"""Technicien {sel_ai_tech} n'a aucune donnée pour {period_label}. 
Analyse cette situation : technicien sans aucun snag enregistré ce mois.
Quelles peuvent être les causes ? Quelle action manager recommandes-tu ? (max 200 mots, en français)"""

                with st.spinner("Claude analyse le profil…"):
                    try:
                        client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
                        msg = client.messages.create(
                            model="claude-sonnet-4-20250514",
                            max_tokens=600,
                            messages=[{"role":"user","content":prompt}]
                        )
                        result = msg.content[0].text
                        st.session_state["ai_profile_result"] = result
                    except Exception as e:
                        st.error(f"Erreur API Claude : {e}")

        if "ai_profile_result" in st.session_state:
            st.html(f'<div style="background:#F9FAFB;border:1px solid #E5E7EB;border-radius:8px;padding:14px 16px;margin-top:10px;font-size:13px;line-height:1.7;color:#111827;{F}">{st.session_state["ai_profile_result"].replace(chr(10),"<br>")}</div>')

    with ai_col2:
        st.html(section_label("QUESTION LIBRE AU MANAGER IA"))
        ai_question = st.text_area(
            "Question",
            placeholder="Ex: Pourquoi Rosly n'a pas de snag TXN ce mois ?\nEx: Quels techniciens sont en danger ce mois ?\nEx: Analyse les blocages récurrents de l'équipe.",
            height=100, key="ai_free_q",
            label_visibility="collapsed"
        )

        if st.button("💬 Envoyer la question", use_container_width=True, key="btn_free_ai"):
            if not ai_question.strip():
                st.error("Saisissez une question")
            else:
                summary = f"""Contexte MTN Congo FLM South Region — {period_label} :
- Techniciens actifs : {len(lb)}
- Total points équipe : {round(total_pts,1)} / {obj_pts} pts
- Alertes fermeture : {len(alert_set)} ({', '.join(alert_set) or 'aucune'})
- Chutes productivité : {len(drop_set)} ({', '.join(drop_set) or 'aucune'})
- Snags en retard : {len(overdue_snags)}
- RCA en attente : {rca_alerts}
- Points bloquants ouverts : {len(open_blk)}
- ASSET en attente : {pending_c} / {len(asset_data)}
- Techniciens sans TXN : {', '.join(t['name'] for t in lb if t['txn_snags']==0) or 'aucun'}

Question du manager : {ai_question.strip()}

Réponds en français, de façon concise et opérationnelle (max 300 mots)."""

                with st.spinner("Claude réfléchit…"):
                    try:
                        client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
                        msg = client.messages.create(
                            model="claude-sonnet-4-20250514",
                            max_tokens=500,
                            messages=[{"role":"user","content":summary}]
                        )
                        result = msg.content[0].text
                        st.session_state["ai_free_result"] = result
                    except Exception as e:
                        st.error(f"Erreur API Claude : {e}")

        if "ai_free_result" in st.session_state:
            st.html(f'<div style="background:#F9FAFB;border:1px solid #E5E7EB;border-radius:8px;padding:14px 16px;margin-top:10px;font-size:13px;line-height:1.7;color:#111827;{F}">{st.session_state["ai_free_result"].replace(chr(10),"<br>")}</div>')

    # Détections automatiques
    st.html(section_label("DÉTECTIONS AUTOMATIQUES IA"))
    detections = []
    for t in lb:
        if t["txn_snags"] == 0:
            detections.append({"type":"warning","icon":"📡","tech":t["name"],
                "msg":f"Aucun snag TXN/IPRAN/MW enregistré ce mois — infrastructure critique non couverte"})
        if t["name"] in drop_set:
            detections.append({"type":"danger","icon":"📉","tech":t["name"],
                "msg":f"Chute brutale de productivité détectée (baisse ≥30% vs mois précédent)"})
        if t["name"] in alert_set:
            detections.append({"type":"danger","icon":"🔴","tech":t["name"],
                "msg":f"Taux de fermeture {t['ml_pct']}% — seuil critique <30% atteint"})

    if detections:
        for d in detections:
            bg = "#FEF2F2" if d["type"]=="danger" else "#FFFBEB"
            bc = "#FECACA" if d["type"]=="danger" else "#FDE68A"
            tc = "#DC2626" if d["type"]=="danger" else "#92400E"
            st.html(f"""<div style="background:{bg};border:1px solid {bc};border-radius:8px;
                padding:8px 14px;margin-bottom:6px;display:flex;align-items:center;gap:10px;">
                <span style="font-size:16px;">{d['icon']}</span>
                <div>
                    <span style="font-size:12px;font-weight:700;color:{tc};{F}">{d['tech']}</span>
                    <span style="font-size:11px;color:#6B7280;{F}"> — {d['msg']}</span>
                </div>
            </div>""")
    else:
        st.html(f"""<div style="background:#F0FDF4;border:1px solid #BBF7D0;border-radius:8px;
            padding:12px 16px;text-align:center;">
            <div style="font-size:12px;color:#166534;font-weight:700;{F}">
                ✅ Aucune anomalie automatique détectée pour {period_label}
            </div>
        </div>""")
