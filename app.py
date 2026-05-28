# ════════════════════════════════════════════════════════
#  MTN FLM Performance Tracker — South Region  v5.0
#  Nouveautés : Objectif + Progression + Évolution + Alertes
# ════════════════════════════════════════════════════════
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, date
import calendar
import io

from scoring import (
    SUB_SCORES, ACTION_FACTOR, ACTION_LABEL, ACTION_COLOR,
    ACTION_LIGHT, ACTION_BORDER,
    CATEGORIES, MONTHS_FR, calc_pts, build_leaderboard
)
from supabase_client import (
    fetch_techniciens, add_technicien, rename_technicien, delete_technicien,
    fetch_snags, insert_snag, update_snag, delete_snag
)
from styles import (
    GLOBAL_CSS, kpi_card, section_label, badge, progress_bar,
    tech_row_card, winner_banner, action_badge_html, card, F
)

st.set_page_config(page_title="MTN FLM Tracker", page_icon="📊",
                   layout="wide", initial_sidebar_state="expanded")
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

now   = datetime.now()
CUR_Y = now.year
CUR_M = now.month

# ════════════════ HELPERS OBJECTIF ════════════════
def obj_color(pct):
    if pct >= 70:  return "#10B981"   # vert
    elif pct >= 40: return "#F59E0B"  # orange
    else:           return "#EF4444"  # rouge

def obj_bar_html(pct, height=10):
    c = obj_color(pct)
    p = min(pct, 100)
    bg = "#DCFCE7" if pct >= 70 else "#FEF3C7" if pct >= 40 else "#FEE2E2"
    return (
        f'<div style="background:{bg};border-radius:99px;height:{height}px;overflow:hidden;">'
        f'<div style="width:{p}%;height:100%;background:{c};border-radius:99px;'
        f'box-shadow:0 0 6px {c}55;transition:width .5s;"></div></div>'
    )

# ════════════════ SIDEBAR ════════════════
with st.sidebar:
    st.html(f"""<div style="display:flex;align-items:center;gap:12px;padding:20px 0 16px;">
        <div style="background:#FFD200;width:44px;height:44px;border-radius:10px;
            display:flex;align-items:center;justify-content:center;font-weight:800;
            font-size:11px;color:#111827;box-shadow:0 2px 8px rgba(255,210,0,.4);{F};">MTN</div>
        <div>
            <div style="font-size:14px;font-weight:800;color:#111827;{F};">FLM TRACKER</div>
            <div style="font-size:10px;color:#9CA3AF;letter-spacing:.06em;{F};">SOUTH REGION · v5.0</div>
        </div>
    </div><div style="height:1px;background:#E5E7EB;margin-bottom:20px;"></div>""")

    st.html(f'<div style="font-size:10px;color:#9CA3AF;letter-spacing:.08em;text-transform:uppercase;font-weight:700;margin-bottom:8px;{F};">PÉRIODE</div>')
    col_m, col_y = st.columns(2)
    with col_m:
        sel_m = st.selectbox("Mois", range(1, 13), format_func=lambda x: MONTHS_FR[x-1],
                             index=CUR_M-1, key="sel_m", label_visibility="collapsed")
    with col_y:
        sel_y = st.selectbox("Année", [2024, 2025, 2026, 2027, 2028],
                             index=[2024, 2025, 2026, 2027, 2028].index(CUR_Y),
                             key="sel_y", label_visibility="collapsed")

    period_label       = f"{MONTHS_FR[sel_m-1]} {sel_y}"
    last_day_of_month  = calendar.monthrange(sel_y, sel_m)[1]

    if sel_y == CUR_Y and sel_m == CUR_M:
        days_left = max(0, last_day_of_month - now.day + 1)
        st.html(f"""<div style="background:#FFFBEB;border:1px solid #FDE68A;border-radius:8px;
            padding:8px 14px;font-size:11px;color:#92400E;font-weight:700;letter-spacing:.04em;
            text-align:center;margin:8px 0;{F};">⏳ J-{days_left} fin du mois</div>""")

    # ── OBJECTIF MENSUEL ──
    st.html('<div style="height:16px;"></div>')
    st.html(f'<div style="font-size:10px;color:#9CA3AF;letter-spacing:.08em;text-transform:uppercase;font-weight:700;margin-bottom:6px;{F};">🎯 OBJECTIF MENSUEL</div>')
    obj_pts = st.number_input("Objectif (pts)", min_value=10, max_value=2000,
                              value=100, step=10, label_visibility="collapsed", key="obj_pts")
    st.html(f'<div style="font-size:9px;color:#D1D5DB;margin-bottom:4px;{F};">Cible de points / technicien / mois</div>')

    st.html('<div style="height:12px;"></div>')
    st.html(f'<div style="font-size:10px;color:#9CA3AF;letter-spacing:.08em;text-transform:uppercase;font-weight:700;margin-bottom:8px;{F};">ACTIONS</div>')
    if st.button("✚  Nouveau snag", key="sb_new", use_container_width=True):
        st.session_state["edit_id"] = None
        st.rerun()
    st.html('<div style="height:8px;"></div>')

    @st.cache_data(ttl=30, show_spinner=False)
    def load_export(y, m): return fetch_snags(y, m)
    df_export = load_export(sel_y, sel_m)
    if not df_export.empty:
        buf = io.BytesIO()
        df_export.to_csv(buf, index=False, encoding="utf-8-sig")
        st.download_button("↓  Exporter CSV", buf.getvalue(),
            f"MTN_FLM_{MONTHS_FR[sel_m-1]}_{sel_y}.csv", mime="text/csv",
            use_container_width=True, key="sb_csv")

    st.html(f"""<div style="height:1px;background:#E5E7EB;margin:20px 0 12px;"></div>
    <div style="font-size:10px;color:#D1D5DB;text-align:center;{F};">Stocké sur Supabase PostgreSQL</div>""")

# ════════════════ DONNÉES ════════════════
@st.cache_data(ttl=30, show_spinner=False)
def load_data(y, m): return fetch_snags(y, m)
@st.cache_data(ttl=30, show_spinner=False)
def load_techs(): return fetch_techniciens()

df      = load_data(sel_y, sel_m)
lb      = build_leaderboard(df)
techs   = load_techs()
max_pts = lb[0]["total"] if lb else 1

# ════════════════ LOGIQUE ALERTES ════════════════
is_current_period = (sel_y == CUR_Y and sel_m == CUR_M)
mid_month_reached = (now.day >= 15) if is_current_period else True   # passé → toujours visible
alert_techs       = {t["name"] for t in lb if t["ml_pct"] < 30 and mid_month_reached}

# ════════════════ TOTAUX & PROGRESSION ÉQUIPE ════════════════
total_pts  = round(df["points"].sum(), 1) if not df.empty else 0
team_pct   = round(total_pts / obj_pts * 100, 1) if obj_pts > 0 else 0
team_color = obj_color(team_pct)
alert_tag  = (f"<div style='background:#FEE2E2;border:1px solid #FECACA;border-radius:8px;"
              f"padding:6px 14px;font-size:11px;color:#DC2626;font-weight:700;'>⚠ "
              f"{len(alert_techs)} alerte{'s' if len(alert_techs)>1 else ''}</div>"
              if alert_techs else "")

# ════════════════ HEADER + PROGRESSION ÉQUIPE ════════════════
st.html(f"""<div style="background:#FFFFFF;border:1px solid #E5E7EB;border-radius:12px;
    padding:18px 22px;margin-bottom:16px;box-shadow:0 1px 3px rgba(0,0,0,.05);">
    <div style="display:flex;justify-content:space-between;align-items:center;
        flex-wrap:wrap;gap:10px;margin-bottom:14px;">
        <div>
            <div style="font-size:20px;font-weight:800;color:#111827;{F};">Suivi Performance FLM</div>
            <div style="font-size:12px;color:#9CA3AF;margin-top:2px;{F};">{period_label} · South Region</div>
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
            {alert_tag}
            <div style="background:#F3F4F6;border-radius:8px;padding:6px 14px;
                font-size:11px;color:#374151;font-weight:600;{F};">
                {len(lb)} technicien{"s" if len(lb)!=1 else ""} actif{"s" if len(lb)!=1 else ""}
            </div>
            <div style="background:#FFFBEB;border:1px solid #FDE68A;border-radius:8px;
                padding:6px 14px;font-size:11px;color:#92400E;font-weight:600;{F};">
                {total_pts} / {obj_pts} pts
            </div>
        </div>
    </div>
    <div>
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:5px;">
            <div style="font-size:10px;font-weight:700;color:#6B7280;letter-spacing:.06em;
                text-transform:uppercase;{F};">🎯 PROGRESSION ÉQUIPE VERS OBJECTIF MENSUEL</div>
            <div style="font-size:16px;font-weight:800;color:{team_color};{F};">{team_pct}%</div>
        </div>
        {obj_bar_html(team_pct, 14)}
        <div style="display:flex;justify-content:space-between;margin-top:5px;">
            <div style="font-size:10px;color:#9CA3AF;{F};">{total_pts} pts accumulés</div>
            <div style="font-size:10px;color:#9CA3AF;{F};">Objectif : {obj_pts} pts</div>
        </div>
    </div>
</div>""")

# ════════════════ ONGLETS ════════════════
tab_db, tab_saisie, tab_class, tab_techs, tab_bareme = st.tabs([
    "📊  TABLEAU", "✚  SAISIE", "🏆  CLASSEMENT", "👷  TECHNICIENS", "📋  BARÈME"
])

# ══════════════ TAB 1 — TABLEAU ══════════════
with tab_db:
    if lb:
        st.html(winner_banner(lb[0], period_label))
    else:
        st.html(f"""<div style="background:#F9FAFB;border:2px dashed #E5E7EB;border-radius:12px;
            padding:40px;text-align:center;margin-bottom:20px;">
            <div style="font-size:36px;margin-bottom:10px;opacity:.3;">📋</div>
            <div style="font-size:14px;font-weight:600;color:#374151;{F};">Aucune donnée pour {period_label}</div>
            <div style="font-size:12px;color:#9CA3AF;margin-top:4px;{F};">Commencez dans l'onglet SAISIE</div>
        </div>""")

    closed_n = int((df["action"].isin(["closed","both"])).sum()) if not df.empty else 0
    cats_n   = df["categorie"].nunique() if not df.empty else 0
    c1, c2, c3, c4 = st.columns(4)
    c1.html(kpi_card("Points totaux", str(total_pts), f"obj. {obj_pts} pts", "#D97706"))
    c2.html(kpi_card("Techniciens actifs", str(len(lb)), "ce mois"))
    c3.html(kpi_card("Snags enregistrés", str(len(df)), f"{closed_n} fermés"))
    c4.html(kpi_card("Catégories actives", str(cats_n), "sur 28 disponibles"))

    # ── BLOC ALERTES MI-MOIS ──────────────────────────────────────────
    if alert_techs:
        rows_html = ""
        for name in sorted(alert_techs):
            td = next((t for t in lb if t["name"] == name), None)
            ml  = td["ml_pct"] if td else 0
            tot = td["total"]  if td else 0
            n   = td["n"]      if td else 0
            rows_html += f"""
            <div style="background:#FFFFFF;border:1px solid #FECACA;border-radius:8px;
                padding:8px 14px;display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
                <div style="width:10px;height:10px;background:#EF4444;border-radius:50%;
                    flex-shrink:0;box-shadow:0 0 4px #EF4444;"></div>
                <div style="font-size:13px;font-weight:700;color:#DC2626;flex:1;{F};">{name}</div>
                <div style="font-size:11px;color:#9CA3AF;{F};">{n} snags · {tot} pts</div>
                <div style="background:#FEE2E2;border-radius:6px;padding:3px 10px;
                    font-size:12px;font-weight:800;color:#DC2626;{F};">
                    {ml}% fermeture
                </div>
            </div>"""
        mid_label = f"mi-mois ({now.day}/{last_day_of_month})" if is_current_period else "fin de mois"
        st.html(f"""
        <div style="background:#FEF2F2;border:1.5px solid #FECACA;border-radius:12px;
            padding:16px 18px;margin:16px 0;">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">
                <div style="font-size:18px;">🚨</div>
                <div>
                    <div style="font-size:12px;font-weight:800;color:#DC2626;
                        letter-spacing:.06em;text-transform:uppercase;{F};">
                        ALERTES PERFORMANCE — {mid_label}
                    </div>
                    <div style="font-size:11px;color:#9CA3AF;margin-top:1px;{F};">
                        Taux de fermeture &lt; 30% — action corrective requise
                    </div>
                </div>
            </div>
            <div style="display:flex;flex-direction:column;gap:6px;">{rows_html}</div>
        </div>""")

    # ── PROGRESSION INDIVIDUELLE VERS OBJECTIF ───────────────────────
    if lb:
        st.html('<div style="height:8px;"></div>')
        st.html(section_label("PROGRESSION INDIVIDUELLE VERS OBJECTIF"))
        for t in lb:
            t_pct    = round(t["total"] / obj_pts * 100, 1) if obj_pts > 0 else 0
            t_col    = obj_color(t_pct)
            is_alrt  = t["name"] in alert_techs
            bdr      = "border:1.5px solid #FECACA;" if is_alrt else "border:1px solid #E5E7EB;"
            bg       = "background:#FFF5F5;" if is_alrt else "background:#FFFFFF;"
            alrt_tag = (f"<div style='font-size:9px;font-weight:700;color:#DC2626;"
                        f"background:#FEE2E2;border-radius:4px;padding:2px 6px;{F};'>⚠ Alerte</div>"
                        if is_alrt else "")
            medal    = "🥇" if t["rank"]==1 else "🥈" if t["rank"]==2 else "🥉" if t["rank"]==3 else f"#{t['rank']}"
            st.html(f"""
            <div style="{bg}{bdr}border-radius:10px;padding:12px 16px;margin-bottom:8px;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:7px;">
                    <div style="display:flex;align-items:center;gap:8px;">
                        <div style="font-size:13px;font-weight:700;
                            color:{"#DC2626" if is_alrt else "#111827"};{F};">
                            {medal} {t['name']}
                        </div>
                        {alrt_tag}
                    </div>
                    <div style="display:flex;align-items:center;gap:14px;">
                        <div style="font-size:11px;color:#9CA3AF;{F};">{t['total']} / {obj_pts} pts</div>
                        <div style="font-size:15px;font-weight:800;color:{t_col};{F};">{t_pct}%</div>
                    </div>
                </div>
                {obj_bar_html(t_pct, 9)}
            </div>""")

        # ── GRAPHIQUE : ÉVOLUTION CUMULATIVE DU SCORE (LIGNE) ────────
        st.html('<div style="height:12px;"></div>')
        st.html(section_label(f"ÉVOLUTION CUMULATIVE DES SCORES — {period_label}"))
        if not df.empty:
            df_evo = df.copy()
            df_evo["date_snag"] = pd.to_datetime(df_evo["date_snag"])
            df_evo["jour"]      = df_evo["date_snag"].dt.day
            df_daily            = df_evo.groupby(["technicien", "jour"])["points"].sum().reset_index()

            # Limite : jours jusqu'à aujourd'hui si mois courant, sinon dernier jour
            max_day = now.day if is_current_period else last_day_of_month
            all_days = list(range(1, max_day + 1))

            evo_colors = ["#FFD200","#6366F1","#10B981","#F59E0B","#EC4899","#8B5CF6","#14B8A6","#EF4444"]
            fig_evo = go.Figure()

            techs_sorted = sorted(df_daily["technicien"].unique())
            for i, tech in enumerate(techs_sorted):
                tech_series = df_daily[df_daily["technicien"] == tech].set_index("jour")["points"]
                cumul   = []
                running = 0
                for d in all_days:
                    running += tech_series.get(d, 0)
                    cumul.append(round(running, 1))

                c_     = evo_colors[i % len(evo_colors)]
                dashed = (tech in alert_techs)
                fig_evo.add_trace(go.Scatter(
                    x=all_days, y=cumul, name=tech,
                    mode="lines+markers",
                    line=dict(color=c_, width=3 if not dashed else 2,
                              dash="solid" if not dashed else "dot"),
                    marker=dict(size=5, color=c_, symbol="circle"),
                    hovertemplate=f"<b>{tech}</b><br>Jour %{{x}}<br>Cumulé : <b>%{{y}} pts</b><extra></extra>",
                ))

            # Ligne objectif
            fig_evo.add_hline(
                y=obj_pts, line_dash="dash", line_color="#EF4444", line_width=1.5,
                annotation_text=f"🎯 Objectif {obj_pts} pts",
                annotation_position="top right",
                annotation_font=dict(size=10, color="#EF4444", family="Plus Jakarta Sans"),
            )

            # Ligne mi-mois (jour 15) si applicable
            if 15 in all_days:
                fig_evo.add_vline(
                    x=15, line_dash="dot", line_color="#9CA3AF", line_width=1,
                    annotation_text="Mi-mois",
                    annotation_position="top",
                    annotation_font=dict(size=9, color="#9CA3AF", family="Plus Jakarta Sans"),
                )

            fig_evo.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#FAFAFA",
                height=340, margin=dict(l=0, r=90, t=12, b=8),
                xaxis=dict(
                    gridcolor="#F1F5F9", tickmode="linear", dtick=1,
                    range=[0.5, max_day + 0.5],
                    title=dict(text="Jour du mois",
                               font=dict(size=10, color="#9CA3AF", family="Plus Jakarta Sans")),
                    tickfont=dict(size=9, family="Plus Jakarta Sans", color="#94A3B8"),
                ),
                yaxis=dict(
                    gridcolor="#F1F5F9",
                    title=dict(text="Points cumulés",
                               font=dict(size=10, color="#9CA3AF", family="Plus Jakarta Sans")),
                    tickfont=dict(size=10, family="Plus Jakarta Sans", color="#94A3B8"),
                    zeroline=False,
                ),
                legend=dict(
                    font=dict(size=11, family="Plus Jakarta Sans", color="#374151"),
                    bgcolor="rgba(255,255,255,.92)",
                    bordercolor="#E5E7EB", borderwidth=1,
                    orientation="v",
                ),
                hoverlabel=dict(bgcolor="#FFF", font_size=11,
                               font_family="Plus Jakarta Sans"),
            )
            st.plotly_chart(fig_evo, use_container_width=True, config={"displayModeBar": False})
            st.html(f'<div style="font-size:10px;color:#9CA3AF;text-align:center;margin-top:-8px;{F};">'
                    f'Courbes en pointillés = techniciens sous alerte (&lt;30% fermeture mi-mois) · '
                    f'Remise à zéro automatique chaque 1er du mois</div>')

            # ── GRAPHIQUE : POINTS JOURNALIERS (BARRES EMPILÉES) ─────
            st.html('<div style="height:12px;"></div>')
            st.html(section_label(f"POINTS PAR JOUR — {period_label}"))

            fig_daily = go.Figure()
            for i, tech in enumerate(techs_sorted):
                tech_series = df_daily[df_daily["technicien"] == tech].set_index("jour")["points"]
                daily_vals  = [round(tech_series.get(d, 0), 1) for d in all_days]
                c_          = evo_colors[i % len(evo_colors)]
                fig_daily.add_trace(go.Bar(
                    x=all_days, y=daily_vals, name=tech,
                    marker_color=c_, marker_line_width=0,
                    hovertemplate=f"<b>{tech}</b><br>Jour %{{x}} : %{{y}} pts<extra></extra>",
                ))

            fig_daily.update_layout(
                barmode="stack",
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#FAFAFA",
                height=220, margin=dict(l=0, r=20, t=8, b=8),
                xaxis=dict(
                    gridcolor="#F1F5F9", tickmode="linear", dtick=1,
                    range=[0.5, max_day + 0.5],
                    tickfont=dict(size=9, family="Plus Jakarta Sans", color="#94A3B8"),
                ),
                yaxis=dict(
                    gridcolor="#F1F5F9",
                    tickfont=dict(size=9, family="Plus Jakarta Sans", color="#94A3B8"),
                ),
                legend=dict(
                    font=dict(size=10, family="Plus Jakarta Sans", color="#374151"),
                    bgcolor="rgba(255,255,255,.92)",
                    bordercolor="#E5E7EB", borderwidth=1,
                    orientation="h", y=-0.25,
                ),
                hoverlabel=dict(bgcolor="#FFF", font_size=11,
                               font_family="Plus Jakarta Sans", bordercolor="#E5E7EB"),
                bargap=0.2,
            )
            st.plotly_chart(fig_daily, use_container_width=True, config={"displayModeBar": False})
        else:
            st.html(f"""<div style="background:#F9FAFB;border:1px dashed #E5E7EB;
                border-radius:8px;padding:24px;text-align:center;">
                <div style="font-size:12px;color:#9CA3AF;{F};">
                    Aucune donnée pour générer les graphiques d'évolution
                </div></div>""")

    # ── GRAPHIQUES EXISTANTS ──────────────────────────────────────────
    if lb:
        st.html('<div style="height:20px;"></div>')
        cl, cr = st.columns([3, 2])
        with cl:
            st.html(section_label("POINTS PAR TECHNICIEN"))
            rank_colors = {1:"#FFD200", 2:"#6366F1", 3:"#10B981"}
            bar_colors  = [rank_colors.get(t["rank"], "#94A3B8") for t in lb]
            bar_borders = {1:"#F59E0B", 2:"#4338CA", 3:"#059669"}
            bar_bcolors = [bar_borders.get(t["rank"], "#64748B") for t in lb]

            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=[t["total"] for t in lb],
                y=[f"{'🥇' if t['rank']==1 else '🥈' if t['rank']==2 else '🥉' if t['rank']==3 else str(t['rank'])+' '} {t['name']}" for t in lb],
                orientation="h",
                marker=dict(color=bar_colors, line=dict(color=bar_bcolors, width=1.5), cornerradius=6),
                text=[f"  {t['total']} pts  " for t in lb],
                textposition="inside", insidetextanchor="end",
                textfont=dict(size=12, color=["#78350F" if t["rank"]==1 else "#FFFFFF" for t in lb],
                              family="Plus Jakarta Sans", weight="bold"),
                hovertemplate="<b>%{y}</b><br>Points: %{x}<extra></extra>",
            ))
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#FFFFFF",
                height=max(300, len(lb)*52), margin=dict(l=10, r=80, t=8, b=8),
                xaxis=dict(gridcolor="#F1F5F9", color="#94A3B8", showline=False,
                           tickfont=dict(size=10, family="Plus Jakarta Sans", color="#94A3B8"),
                           zeroline=False),
                yaxis=dict(gridcolor="rgba(0,0,0,0)", showgrid=False,
                           tickfont=dict(size=12, family="Plus Jakarta Sans", color="#111827", weight="bold"),
                           autorange="reversed"),
                showlegend=False,
                hoverlabel=dict(bgcolor="#FFF", font_size=12, font_family="Plus Jakarta Sans", bordercolor="#E5E7EB"),
                bargap=0.35,
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        with cr:
            st.html(section_label("TOP 5"))
            for t in lb[:5]:
                st.html(tech_row_card(t["rank"], t, max_pts))

        st.html('<div style="height:8px;"></div>')
        cd, cc = st.columns(2)
        with cd:
            st.html(section_label("RÉPARTITION DES ACTIONS"))
            if not df.empty:
                ac = df["action"].value_counts().reset_index()
                ac.columns = ["action", "count"]
                fig2 = go.Figure(go.Pie(
                    labels=[ACTION_LABEL.get(a, a) for a in ac["action"]],
                    values=ac["count"],
                    marker_colors=[ACTION_COLOR.get(a, "#9CA3AF") for a in ac["action"]],
                    hole=0.6,
                    textfont=dict(size=11, family="Plus Jakarta Sans"),
                ))
                fig2.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)", height=200,
                    margin=dict(l=0, r=0, t=0, b=0),
                    legend=dict(font=dict(size=11, family="Plus Jakarta Sans", color="#374151"),
                                bgcolor="rgba(0,0,0,0)"),
                    hoverlabel=dict(bgcolor="#FFF", font_size=11, font_family="Plus Jakarta Sans"),
                )
                st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar": False})
        with cc:
            st.html(section_label("TOP CATÉGORIES"))
            if not df.empty:
                cp = df.groupby("categorie")["points"].sum().sort_values(ascending=False).head(7)
                mx = cp.max() or 1
                bcs = ["#FFD200","#6366F1","#10B981","#F59E0B","#EC4899","#8B5CF6","#14B8A6"]
                for idx, (cat, pts) in enumerate(cp.items()):
                    c_ = bcs[idx % len(bcs)]
                    st.html(f"""<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
                        <div style="font-size:11px;color:#374151;width:120px;flex-shrink:0;
                            white-space:nowrap;overflow:hidden;text-overflow:ellipsis;{F};">{cat}</div>
                        <div style="flex:1;">{progress_bar(pts/mx*100, c_, 7)}</div>
                        <div style="font-size:11px;font-weight:700;color:{c_};width:32px;text-align:right;{F};">{pts:.0f}</div>
                    </div>""")

# ══════════════ TAB 2 — SAISIE ══════════════
with tab_saisie:
    edit_id   = st.session_state.get("edit_id", None)
    edit_data = {}
    if edit_id and not df.empty:
        rows = df[df["id"] == edit_id]
        if not rows.empty: edit_data = rows.iloc[0].to_dict()

    st.html(section_label(f'{"✎ MODIFIER" if edit_id else "✚ NOUVEAU SNAG"} — {period_label}'))

    st.html(f"""<div style="background:#FFFBEB;border:1.5px solid #FDE68A;border-radius:10px;
        padding:14px 18px;margin-bottom:16px;">
        <div style="font-size:11px;font-weight:700;color:#92400E;letter-spacing:.06em;
            text-transform:uppercase;{F};">👷 Technicien assigné</div>
    </div>""")

    ct1, ct2 = st.columns(2)
    topts = ["— Sélectionner —"] + (techs or [])
    def_i = (techs.index(edit_data.get("technicien", "")) + 1
             if edit_data.get("technicien") in (techs or []) else 0)
    with ct1:
        st.markdown('<div style="font-size:11px;color:#6B7280;font-weight:600;margin-bottom:4px;">Choisir dans la liste</div>', unsafe_allow_html=True)
        sel_tech = st.selectbox("Tech", topts, index=def_i, label_visibility="collapsed", key="f_tech_sel")
    with ct2:
        st.markdown('<div style="font-size:11px;color:#6B7280;font-weight:600;margin-bottom:4px;">Ou saisir manuellement</div>', unsafe_allow_html=True)
        man_tech = st.text_input("Tech man", value=edit_data.get("technicien", ""),
                                 placeholder="Nom complet...", label_visibility="collapsed", key="f_tech_man")

    technician = man_tech.strip() if man_tech.strip() else (sel_tech if sel_tech != "— Sélectionner —" else "")
    if not techs:
        st.info("➜ Ajoutez des techniciens dans l'onglet **👷 TECHNICIENS**")

    cs1, cs2 = st.columns(2)
    with cs1:
        st.markdown('<div style="font-size:11px;color:#6B7280;font-weight:600;margin-bottom:4px;">Nom du site</div>', unsafe_allow_html=True)
        site_nom = st.text_input("Site nom", value=edit_data.get("site_nom", ""),
                                 placeholder="Ex: DOLISIE_CENTRE", label_visibility="collapsed", key="f_site_nom")
    with cs2:
        st.markdown('<div style="font-size:11px;color:#6B7280;font-weight:600;margin-bottom:4px;">Site ID</div>', unsafe_allow_html=True)
        site_id_val = st.text_input("Site ID", value=edit_data.get("site_id", ""),
                                    placeholder="Ex: CG_DOL_001", label_visibility="collapsed", key="f_site_id")

    cc1, cc2 = st.columns(2)
    with cc1:
        st.markdown('<div style="font-size:11px;color:#6B7280;font-weight:600;margin-bottom:4px;">Catégorie de snag</div>', unsafe_allow_html=True)
        cat_def = CATEGORIES.index(edit_data.get("categorie", "DG")) if edit_data.get("categorie", "DG") in CATEGORIES else 0
        categorie = st.selectbox("Cat", CATEGORIES, index=cat_def,
                                 format_func=lambda x: f"{x}  ({SUB_SCORES[x]} pts)",
                                 label_visibility="collapsed", key="f_cat")
    with cc2:
        st.markdown('<div style="font-size:11px;color:#6B7280;font-weight:600;margin-bottom:4px;">Date</div>', unsafe_allow_html=True)
        d_def = edit_data.get("date_snag", date.today())
        if isinstance(d_def, str): d_def = date.fromisoformat(d_def)
        snag_date = st.date_input("Date", value=d_def, label_visibility="collapsed", key="f_date")

    st.markdown('<div style="font-size:11px;color:#6B7280;font-weight:600;margin:12px 0 6px;">Action réalisée</div>', unsafe_allow_html=True)
    act_opts = {"raised": "↑  Remonté  —  40% des points",
                "closed": "✓  Fermé  —  60% des points",
                "both":   "⟳  Remonté + Fermé  —  100% des points"}
    def_act = list(act_opts.keys()).index(edit_data.get("action", "closed")) if edit_data.get("action") in act_opts else 1
    action = st.radio("Action", list(act_opts.keys()), format_func=lambda x: act_opts[x],
                      index=def_act, horizontal=True, label_visibility="collapsed", key="f_action")

    st.markdown('<div style="font-size:11px;color:#6B7280;font-weight:600;margin:12px 0 4px;">Description (optionnel)</div>', unsafe_allow_html=True)
    description = st.text_input("Desc", value=edit_data.get("description", ""),
                                placeholder="Ex: DG battery fault...", label_visibility="collapsed", key="f_desc")

    pts_preview = calc_pts(categorie, action)
    act_col = ACTION_COLOR.get(action, "#6B7280")
    act_bg  = ACTION_LIGHT.get(action, "#F9FAFB")
    act_bdr = ACTION_BORDER.get(action, "#E5E7EB")
    st.html(f"""<div style="background:{act_bg};border:1.5px solid {act_bdr};border-radius:10px;
        padding:14px 18px;margin:14px 0;display:flex;justify-content:space-between;align-items:center;">
        <div>
            <div style="font-size:10px;font-weight:700;color:#6B7280;letter-spacing:.07em;
                text-transform:uppercase;margin-bottom:4px;{F};">POINTS CALCULÉS</div>
            <div style="font-size:12px;color:#9CA3AF;{F};">
                Base : {SUB_SCORES[categorie]} pts × Facteur : {ACTION_FACTOR[action]}
            </div>
        </div>
        <div style="text-align:right;">
            <div style="font-size:38px;font-weight:800;color:{act_col};line-height:1;{F};">{pts_preview}</div>
            <div style="font-size:10px;color:#9CA3AF;{F};">points</div>
        </div>
    </div>""")

    if edit_id:
        bc1, bc2 = st.columns([3, 1])
        with bc1: submitted = st.button("METTRE À JOUR", use_container_width=True, key="btn_submit")
        with bc2:
            if st.button("Annuler", key="btn_cancel", use_container_width=True):
                st.session_state["edit_id"] = None; st.rerun()
    else:
        submitted = st.button("ENREGISTRER LE SNAG", use_container_width=True, key="btn_submit")

    if submitted:
        tech_ = man_tech.strip() if man_tech.strip() else (sel_tech if sel_tech != "— Sélectionner —" else "")
        if not tech_: st.error("⚠ Nom du technicien requis")
        elif not site_nom.strip(): st.error("⚠ Nom du site requis")
        else:
            row = {"technicien": tech_, "site_nom": site_nom.strip(), "site_id": site_id_val.strip(),
                   "categorie": categorie, "action": action, "date_snag": str(snag_date),
                   "description": description.strip(), "points": pts_preview, "annee": sel_y, "mois": sel_m}
            ok = update_snag(edit_id, row) if edit_id else insert_snag(row)
            if ok:
                st.success(f"✓ Snag {'mis à jour' if edit_id else 'enregistré'} (+{pts_preview} pts)")
                st.session_state["edit_id"] = None; st.cache_data.clear(); st.rerun()

    st.html('<div style="height:24px;"></div>')
    df_fresh = load_data(sel_y, sel_m)
    if not df_fresh.empty:
        ts = round(df_fresh["points"].sum(), 1)
        st.html(f"""<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;">
            <div style="font-size:10px;font-weight:700;color:#9CA3AF;letter-spacing:.08em;text-transform:uppercase;{F};">
                {len(df_fresh)} SAISIE{"S" if len(df_fresh)>1 else ""}</div>
            <div style="background:#FFFBEB;border:1px solid #FDE68A;border-radius:6px;
                padding:4px 12px;font-size:11px;font-weight:700;color:#92400E;{F};">{ts} pts total</div>
        </div>""")
        st.html(f"""<div style="background:#F8FAFC;border:1px solid #E5E7EB;border-radius:8px 8px 0 0;
            padding:10px 16px;display:grid;
            grid-template-columns:90px 1.4fr 1.5fr 1.4fr 100px 60px 110px;gap:8px;">
            {"".join(f'<div style="font-size:9px;font-weight:700;color:#9CA3AF;letter-spacing:.07em;text-transform:uppercase;{F};">{h}</div>'
              for h in ["Date","Technicien","Site","Catégorie","Action","Pts","Actions"])}
        </div>""")

        for idx, (_, row) in enumerate(df_fresh.iterrows()):
            bg_row = "#FFFFFF" if idx % 2 == 0 else "#FAFBFC"
            st.html(f"""<div style="background:{bg_row};border-left:1px solid #E5E7EB;
                border-right:1px solid #E5E7EB;border-bottom:1px solid #F1F5F9;
                padding:10px 16px;display:grid;
                grid-template-columns:90px 1.4fr 1.5fr 1.4fr 100px 60px 110px;
                gap:8px;align-items:center;">
                <div style="font-size:11px;color:#9CA3AF;{F};">{row["date_snag"]}</div>
                <div style="font-size:12px;font-weight:600;color:#111827;{F};">{row["technicien"]}</div>
                <div style="font-size:11px;color:#374151;white-space:nowrap;overflow:hidden;
                    text-overflow:ellipsis;{F};">{row["site_nom"]}</div>
                <div style="font-size:11px;color:#374151;white-space:nowrap;overflow:hidden;
                    text-overflow:ellipsis;{F};">{row["categorie"]}</div>
                <div>{action_badge_html(row["action"])}</div>
                <div style="font-size:14px;font-weight:800;color:#D97706;text-align:center;{F};">{row["points"]}</div>
                <div style="font-size:10px;color:#6B7280;{F};">—</div>
            </div>""")
            cb1, cb2, cb3 = st.columns([5.5, 0.9, 1.1])
            with cb2:
                if st.button("✎ Modifier", key=f"e_{row['id']}", use_container_width=True):
                    st.session_state["edit_id"] = row["id"]; st.rerun()
            with cb3:
                confirm_key = f"confirm_del_{row['id']}"
                if st.session_state.get(confirm_key):
                    col_yes, col_no = st.columns(2)
                    with col_yes:
                        if st.button("✓ Oui", key=f"yes_{row['id']}", use_container_width=True):
                            if delete_snag(row["id"]):
                                st.session_state[confirm_key] = False
                                st.cache_data.clear(); st.rerun()
                    with col_no:
                        if st.button("✗ Non", key=f"no_{row['id']}", use_container_width=True):
                            st.session_state[confirm_key] = False; st.rerun()
                else:
                    if st.button("🗑 Supprimer", key=f"d_{row['id']}", use_container_width=True):
                        st.session_state[confirm_key] = True; st.rerun()
            st.html('<div style="height:2px;background:#F1F5F9;margin-bottom:2px;"></div>')

        st.html(f'<div style="background:#F8FAFC;border:1px solid #E5E7EB;border-radius:0 0 8px 8px;'
                f'padding:8px 16px;font-size:11px;color:#9CA3AF;{F};">Total : {len(df_fresh)} entrée'
                f'{"s" if len(df_fresh)>1 else ""} · {ts} points</div>')
    else:
        st.html(f"""<div style="background:#F9FAFB;border:2px dashed #E5E7EB;border-radius:10px;
            padding:30px;text-align:center;margin-top:16px;">
            <div style="font-size:12px;color:#9CA3AF;{F};">Aucun snag pour {period_label}</div>
        </div>""")

# ══════════════ TAB 3 — CLASSEMENT ══════════════
with tab_class:
    if not lb:
        st.html(f"""<div style="background:#F9FAFB;border:2px dashed #E5E7EB;border-radius:12px;
            padding:50px;text-align:center;">
            <div style="font-size:12px;color:#9CA3AF;{F};">Aucune donnée pour {period_label}</div>
        </div>""")
    else:
        if len(lb) >= 2:
            pod = [lb[1], lb[0]] + ([lb[2]] if len(lb) > 2 else [])
            h_map  = {1:160, 2:120, 3:90}
            bg_map = {1:"linear-gradient(135deg,#FFFBEB,#FEF9C3)", 2:"#F9FAFB", 3:"#FEF3C7"}
            bc_map = {1:"#FFD200", 2:"#E5E7EB", 3:"#FDE68A"}
            tc_map = {1:"#D97706", 2:"#6B7280", 3:"#92400E"}
            mc_map = {1:"🥇", 2:"🥈", 3:"🥉"}
            pod_html = '<div style="display:flex;justify-content:center;align-items:flex-end;gap:12px;margin-bottom:28px;">'
            for t in pod:
                r = t["rank"]
                pod_html += f"""<div style="text-align:center;width:140px;">
                    <div style="font-size:12px;font-weight:700;color:{tc_map[r]};margin-bottom:4px;{F};">{mc_map[r]}</div>
                    <div style="font-size:13px;font-weight:700;color:#111827;margin-bottom:2px;{F};">{t['name']}</div>
                    <div style="font-size:18px;font-weight:800;color:{tc_map[r]};margin-bottom:8px;{F};">{t['total']} pts</div>
                    <div style="height:{h_map[r]}px;background:{bg_map[r]};border:2px solid {bc_map[r]};
                        border-radius:10px 10px 0 0;display:flex;flex-direction:column;
                        align-items:center;justify-content:flex-end;padding-bottom:12px;">
                        <div style="font-size:26px;">{mc_map[r]}</div>
                        <div style="font-size:20px;font-weight:800;color:{tc_map[r]};{F};">{r}</div>
                    </div>
                </div>"""
            pod_html += '</div>'
            st.html(pod_html)

        st.html(section_label(f"CLASSEMENT COMPLET — {period_label}"))
        for t in lb:
            is_alrt = t["name"] in alert_techs
            if is_alrt:
                t_pct = round(t["total"] / obj_pts * 100, 1) if obj_pts > 0 else 0
                st.html(f"""
                <div style="background:#FFF5F5;border:1.5px solid #FECACA;border-radius:10px;
                    padding:4px 12px 4px 4px;margin-bottom:6px;display:flex;align-items:center;
                    justify-content:space-between;gap:8px;">
                    <div style="flex:1;">{tech_row_card(t['rank'], t, max_pts)}</div>
                    <div style="flex-shrink:0;text-align:right;">
                        <div style="font-size:9px;font-weight:700;color:#DC2626;
                            background:#FEE2E2;border-radius:4px;padding:2px 7px;margin-bottom:3px;{F};">
                            ⚠ {t['ml_pct']}% fermeture
                        </div>
                        <div style="font-size:10px;color:#9CA3AF;{F};">{t_pct}% obj.</div>
                    </div>
                </div>""")
            else:
                st.html(tech_row_card(t["rank"], t, max_pts))

        st.html('<div style="height:16px;"></div>')
        st.html(section_label("SCORE ML — TAUX DE FERMETURE"))
        ml_df = pd.DataFrame([{"Technicien": t["name"], "Score (%)": t["ml_pct"],
                                "Cluster": t["cluster"]["label"]} for t in lb])
        fig3 = px.bar(ml_df, x="Score (%)", y="Technicien", orientation="h", color="Cluster",
                      color_discrete_map={"Elite":"#F59E0B","Performant":"#6366F1",
                                          "En progression":"#10B981","Actif":"#9CA3AF"},
                      text="Score (%)")
        fig3.add_vline(x=30, line_dash="dash", line_color="#EF4444", line_width=1.5,
                       annotation_text="Seuil alerte 30%",
                       annotation_position="top",
                       annotation_font=dict(size=9, color="#EF4444", family="Plus Jakarta Sans"))
        fig3.update_traces(texttemplate="%{text}%", textposition="outside",
                           textfont=dict(size=11, family="Plus Jakarta Sans", color="#374151"),
                           marker_line_width=0)
        fig3.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#FAFAFA",
            height=max(260, len(lb)*44), margin=dict(l=0, r=60, t=8, b=8),
            xaxis=dict(gridcolor="#F3F4F6", range=[0,115], color="#9CA3AF",
                       tickfont=dict(size=10, family="Plus Jakarta Sans"), ticksuffix="%"),
            yaxis=dict(gridcolor="rgba(0,0,0,0)",
                       tickfont=dict(size=12, family="Plus Jakarta Sans", color="#374151"),
                       autorange="reversed"),
            legend=dict(font=dict(size=11, family="Plus Jakarta Sans", color="#374151"),
                        bgcolor="rgba(0,0,0,0)"),
            hoverlabel=dict(bgcolor="#FFF", font_size=12, font_family="Plus Jakarta Sans"),
        )
        st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar": False})

        st.html(card(f"""<div style="font-size:11px;color:#6B7280;line-height:1.9;{F};">
            <strong style="color:#374151;">Formule ML : </strong>Taux fermeture = (Fermés + R+F) / Total × 100 + Bonus volume<br>
            <strong style="color:#374151;">Bonus : </strong>+5% si ≥8 snags · +3% si ≥5 snags · 0 sinon<br>
            <strong style="color:#374151;">Points : </strong>Base catégorie × Facteur action (Remonté×0.4 · Fermé×0.6 · R+F×1.0)<br>
            <strong style="color:#EF4444;">Alerte : </strong>Taux &lt; 30% après le 15 du mois → marqué en rouge automatiquement
        </div>"""))

# ══════════════ TAB 4 — TECHNICIENS ══════════════
with tab_techs:
    st.html(f"""<div style="background:#FFFBEB;border:1.5px solid #FDE68A;border-radius:10px;
        padding:14px 18px;margin-bottom:20px;">
        <div style="font-size:11px;font-weight:700;color:#92400E;letter-spacing:.06em;
            text-transform:uppercase;{F};">➕ AJOUTER UN TECHNICIEN</div>
    </div>""")
    ca1, ca2 = st.columns([4, 1])
    with ca1:
        new_name = st.text_input("Nom", placeholder="Nom complet...",
                                 label_visibility="collapsed", key="new_tech_input")
    with ca2:
        if st.button("Ajouter", use_container_width=True, key="btn_add_tech"):
            if not new_name.strip(): st.error("Saisir un nom")
            elif new_name.strip().lower() in [t.lower() for t in techs]: st.error("Déjà existant")
            else:
                if add_technicien(new_name):
                    st.success(f"✓ {new_name.strip()} ajouté"); st.cache_data.clear(); st.rerun()

    active_map  = {t["name"]: t for t in lb}
    techs_fresh = load_techs()

    st.html(f"""<div style="display:grid;grid-template-columns:40px 2fr 0.8fr 0.7fr 0.7fr 0.7fr 0.9fr 0.9fr 80px;
        gap:0;border-bottom:2px solid #E5E7EB;padding:8px 12px;margin-bottom:6px;">
        {"".join(f'<div style="font-size:9px;font-weight:700;color:#9CA3AF;letter-spacing:.06em;text-transform:uppercase;{F};">{h}</div>'
          for h in ["#","TECHNICIEN","STATUT","PTS","SNAGS","FERMÉS","SCORE ML","CLUSTER",""])}
    </div>""")

    if not techs_fresh:
        st.html(f"""<div style="background:#F9FAFB;border:2px dashed #E5E7EB;border-radius:10px;
            padding:30px;text-align:center;">
            <div style="font-size:12px;color:#9CA3AF;{F};">Aucun technicien. Ajoutez votre équipe ci-dessus.</div>
        </div>""")
    else:
        for i, name in enumerate(techs_fresh):
            t        = active_map.get(name)
            is_alrt  = name in alert_techs
            row_bg   = "background:#FFF5F5;" if is_alrt else ""
            row_bdr  = "border-left:3px solid #EF4444;border-radius:6px;" if is_alrt else ""

            if is_alrt:
                st.html(f'<div style="{row_bg}{row_bdr}padding:2px 0;margin-bottom:2px;">'
                        f'<div style="font-size:9px;color:#DC2626;font-weight:700;'
                        f'padding:2px 12px;letter-spacing:.05em;{F};">⚠ ALERTE — fermeture &lt; 30%</div></div>')

            ci, cn, cs, cp, csn, ccl, cml, cclb, cact = st.columns([0.5,2,0.8,0.7,0.7,0.7,0.9,0.9,0.7])
            ci.markdown(f'<div style="font-size:11px;color:#9CA3AF;padding:10px 0;{F};">{i+1}</div>', unsafe_allow_html=True)
            name_col = "#DC2626" if is_alrt else ("#111827" if t else "#9CA3AF")
            name_wt  = "700" if is_alrt else ("600" if t else "400")
            cn.markdown(f'<div style="font-size:12px;font-weight:{name_wt};color:{name_col};padding:10px 0;{F};">'
                        f'{"⚠ " if is_alrt else ""}{name}</div>', unsafe_allow_html=True)
            if t:
                cl_ = t["cluster"]
                ml_col = "#DC2626" if is_alrt else cl_["color"]
                cs.html(f'<div style="padding:10px 0;">'
                        f'{badge("Actif","#ECFDF5","#065F46","#6EE7B7")}</div>')
                cp.markdown(f'<div style="font-size:13px;font-weight:700;color:#D97706;'
                            f'padding:10px 0;text-align:center;{F};">{t["total"]}</div>', unsafe_allow_html=True)
                csn.markdown(f'<div style="font-size:12px;color:#374151;'
                             f'padding:10px 0;text-align:center;{F};">{t["n"]}</div>', unsafe_allow_html=True)
                ccl.markdown(f'<div style="font-size:12px;color:#6366F1;font-weight:600;'
                             f'padding:10px 0;text-align:center;{F};">{t["closed"]+t["both"]}</div>', unsafe_allow_html=True)
                cml.markdown(f'<div style="font-size:13px;font-weight:700;color:{ml_col};'
                             f'padding:10px 0;text-align:center;{F};">{t["ml_pct"]}%</div>', unsafe_allow_html=True)
                if is_alrt:
                    cclb.html(f'<div style="padding:10px 0;text-align:center;">'
                              f'{badge("⚠ Alerte","#FEE2E2","#DC2626","#FECACA")}</div>')
                else:
                    cclb.html(f'<div style="padding:10px 0;text-align:center;">'
                              f'{badge(cl_["label"],cl_["bg"],cl_["color"],cl_["border"])}</div>')
            else:
                for col_ in [cp, csn, ccl, cml]:
                    col_.markdown('<div style="color:#D1D5DB;padding:10px 0;text-align:center;">—</div>', unsafe_allow_html=True)
                cs.html(f'<div style="padding:10px 0;">{badge("Inactif","#F9FAFB","#9CA3AF")}</div>')
                cclb.markdown('<div style="color:#D1D5DB;padding:10px 0;text-align:center;">—</div>', unsafe_allow_html=True)

            with cact:
                cr_, cd_ = st.columns(2)
                with cr_:
                    if st.button("✎", key=f"ren_{i}_{name}"):
                        st.session_state[f"renaming_{i}"] = True
                with cd_:
                    if st.button("✕", key=f"del_t_{i}_{name}"):
                        if delete_technicien(name): st.cache_data.clear(); st.rerun()

            if st.session_state.get(f"renaming_{i}"):
                r1, r2, r3 = st.columns([3, 1, 1])
                with r1:
                    new_rn = st.text_input("Renommer", value=name,
                                           label_visibility="collapsed", key=f"rn_input_{i}")
                with r2:
                    if st.button("✓", key=f"rn_ok_{i}", use_container_width=True):
                        if new_rn.strip() and new_rn.strip() != name:
                            if rename_technicien(name, new_rn.strip()):
                                st.session_state[f"renaming_{i}"] = False
                                st.cache_data.clear(); st.rerun()
                with r3:
                    if st.button("✗", key=f"rn_cancel_{i}", use_container_width=True):
                        st.session_state[f"renaming_{i}"] = False; st.rerun()

            st.html('<div style="height:1px;background:#F3F4F6;"></div>')

        extras = [t for t in lb if t["name"] not in techs_fresh]
        if extras:
            st.html(f'<div style="margin-top:16px;">{section_label("NON ENREGISTRÉS")}</div>')
            for t in extras:
                e1, e2 = st.columns([4, 1])
                e1.markdown(f'<div style="font-size:12px;color:#9CA3AF;padding:8px 0;{F};">'
                            f'{t["name"]} — {t["total"]} pts</div>', unsafe_allow_html=True)
                with e2:
                    if st.button("+ Ajouter", key=f"reg_{t['name']}", use_container_width=True):
                        if add_technicien(t["name"]): st.cache_data.clear(); st.rerun()

        st.html('<div style="height:10px;"></div>')
        with st.expander("⚠ Zone dangereuse"):
            if st.button("🗑  Confirmer la suppression de toute la liste", key="clear_all", use_container_width=True):
                for n in techs_fresh: delete_technicien(n)
                st.cache_data.clear(); st.rerun()

    st.html(card(f"""<div style="font-size:11px;color:#6B7280;line-height:1.9;{F};">
        <strong style="color:#374151;">ℹ Info : </strong>Données stockées dans Supabase PostgreSQL.<br>
        Supprimer un technicien <strong style="color:#EF4444;">ne supprime pas</strong> ses saisies.
        Le renommage propage automatiquement sur toutes les saisies.<br>
        <strong style="color:#EF4444;">⚠ Alerte rouge</strong> = taux de fermeture &lt; 30%
        {"après le 15 du mois (mi-mois atteint)" if mid_month_reached else "— seuil mi-mois non encore atteint"}.
    </div>"""))

# ══════════════ TAB 5 — BARÈME ══════════════
with tab_bareme:
    st.html(section_label("RÈGLES DE CALCUL"))
    rc1, rc2, rc3 = st.columns(3)
    for col_, (act, val, sub, bg_, col_txt, bdr) in zip([rc1, rc2, rc3], [
        ("↑  Remonté", "40%", "Identification terrain", "#FEF3C7", "#92400E", "#FDE68A"),
        ("✓  Fermé",   "60%", "Résolution validée",    "#EEF2FF", "#3730A3", "#C7D2FE"),
        ("⟳  R+F",    "100%", "Double valorisation",   "#ECFDF5", "#065F46", "#6EE7B7"),
    ]):
        col_.html(f"""<div style="background:{bg_};border:1.5px solid {bdr};border-radius:10px;
            padding:16px 18px;text-align:center;margin-bottom:12px;">
            <div style="font-size:15px;font-weight:700;color:{col_txt};{F};">{act}</div>
            <div style="font-size:30px;font-weight:800;color:{col_txt};margin:6px 0;{F};">{val}</div>
            <div style="font-size:11px;color:{col_txt};opacity:.8;{F};">{sub}</div>
        </div>""")

    st.html(card(f"""<div style="font-size:12px;color:#6B7280;line-height:2;{F};">
        <strong style="color:#374151;">Formule : </strong>Points = Base catégorie × Facteur action<br>
        <strong style="color:#374151;">Exemple — DG fermé : </strong>5 × 0.6 = <strong style="color:#D97706;">3.0 pts</strong><br>
        <strong style="color:#374151;">Maximum (TXN/RAN/IPRAN · R+F) : </strong>8 × 1.0 = <strong style="color:#D97706;">8.0 pts</strong><br>
        <strong style="color:#374151;">🎯 Objectif mensuel : </strong>configurable dans la sidebar · actuel = <strong style="color:#D97706;">{obj_pts} pts</strong><br>
        <strong style="color:#EF4444;">⚠ Seuil alerte : </strong>taux de fermeture &lt; 30% après le 15 du mois<br>
        <em style="color:#9CA3AF;">⚠ La priorité du site a été supprimée — tous les sites ont la même pondération.</em>
    </div>"""))

    st.html(section_label("POINTS BASE PAR CATÉGORIE — 28 CATÉGORIES"))
    sorted_cats = sorted(SUB_SCORES.items(), key=lambda x: -x[1])
    bcs = ["#FFD200","#6366F1","#10B981","#F59E0B","#EC4899","#8B5CF6","#14B8A6","#EF4444"]
    fig5 = go.Figure(go.Bar(
        x=[s[1] for s in sorted_cats], y=[s[0] for s in sorted_cats],
        orientation="h",
        marker_color=[bcs[i % len(bcs)] for i in range(len(sorted_cats))],
        marker_line_width=0,
        text=[str(s[1]) for s in sorted_cats],
        textposition="outside",
        textfont=dict(size=10, family="Plus Jakarta Sans", color="#374151"),
    ))
    fig5.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#FAFAFA",
        height=560, margin=dict(l=0, r=40, t=8, b=8),
        xaxis=dict(gridcolor="#F3F4F6", range=[0,10], color="#9CA3AF",
                   tickfont=dict(size=10, family="Plus Jakarta Sans")),
        yaxis=dict(gridcolor="rgba(0,0,0,0)",
                   tickfont=dict(size=11, family="Plus Jakarta Sans"), autorange="reversed"),
        showlegend=False,
        hoverlabel=dict(bgcolor="#FFF", font_size=12, font_family="Plus Jakarta Sans"),
    )
    st.plotly_chart(fig5, use_container_width=True, config={"displayModeBar": False})
