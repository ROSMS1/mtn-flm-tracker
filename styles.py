# ════════════════════════════════════════════════════════
#  MTN FLM Tracker — Design System v4.0
# ════════════════════════════════════════════════════════

GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {
  --yellow:     #FFD200;
  --yellow-d:   #F5C800;
  --yellow-bg:  #FFFBEB;
  --yellow-txt: #78350F;
  --text-1:     #111827;
  --text-2:     #374151;
  --text-3:     #6B7280;
  --text-4:     #9CA3AF;
  --bg-1:       #FFFFFF;
  --bg-2:       #F9FAFB;
  --bg-3:       #F3F4F6;
  --border:     #E5E7EB;
  --border-d:   #D1D5DB;
  --indigo:     #6366F1;
  --indigo-bg:  #EEF2FF;
  --green:      #10B981;
  --green-bg:   #ECFDF5;
  --amber:      #F59E0B;
  --amber-bg:   #FEF3C7;
  --shadow-sm:  0 1px 3px rgba(0,0,0,.06), 0 1px 2px rgba(0,0,0,.04);
  --shadow-md:  0 4px 12px rgba(0,0,0,.08), 0 2px 4px rgba(0,0,0,.04);
  --shadow-lg:  0 8px 24px rgba(0,0,0,.10), 0 4px 8px rgba(0,0,0,.04);
  --radius:     12px;
  --radius-sm:  8px;
  --radius-lg:  16px;
}

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    background-color: #F3F4F6 !important;
    color: var(--text-1) !important;
}
#MainMenu, footer, header { visibility: hidden; }
.block-container {
    padding: 0 2rem 4rem !important;
    max-width: 1080px !important;
}
.stDeployButton, div[data-testid="stToolbar"] { display: none !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: var(--bg-1) !important;
    border-right: 1px solid var(--border) !important;
    box-shadow: var(--shadow-sm) !important;
}
[data-testid="stSidebar"] .block-container {
    padding: 0 1.2rem 2rem !important;
}

/* ── Inputs ── */
input, textarea {
    background: var(--bg-1) !important;
    color: var(--text-1) !important;
    border: 1.5px solid var(--border) !important;
    border-radius: var(--radius-sm) !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 13px !important;
    transition: all .2s !important;
}
input:focus, textarea:focus {
    border-color: var(--yellow) !important;
    box-shadow: 0 0 0 3px rgba(255,210,0,.15) !important;
    outline: none !important;
}

/* ── Selectbox ── */
[data-testid="stSelectbox"] > div > div {
    background: var(--bg-1) !important;
    border: 1.5px solid var(--border) !important;
    border-radius: var(--radius-sm) !important;
    color: var(--text-1) !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 13px !important;
}
[data-testid="stSelectbox"] > div > div:focus-within {
    border-color: var(--yellow) !important;
    box-shadow: 0 0 0 3px rgba(255,210,0,.15) !important;
}

/* ── Text Input ── */
[data-testid="stTextInput"] > div > div > input,
[data-testid="stDateInput"] > div > div > input {
    background: var(--bg-1) !important;
    border: 1.5px solid var(--border) !important;
    border-radius: var(--radius-sm) !important;
    color: var(--text-1) !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}

/* ── Buttons ── */
.stButton > button {
    background: var(--yellow) !important;
    color: var(--text-1) !important;
    border: none !important;
    border-radius: var(--radius-sm) !important;
    font-weight: 700 !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 13px !important;
    padding: 10px 20px !important;
    transition: all .15s !important;
    box-shadow: 0 2px 8px rgba(255,210,0,.35) !important;
}
.stButton > button:hover {
    background: var(--yellow-d) !important;
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 16px rgba(255,210,0,.45) !important;
}
.stButton > button:active { transform: scale(.98) !important; }

/* Bouton supprimer rouge */
[data-testid="stButton"] button[kind="secondary"]:has-text("Supprimer"),
button[title="Supprimer ce snag"] {
    background: #FEF2F2 !important;
    color: #DC2626 !important;
    border: 1px solid #FECACA !important;
    box-shadow: none !important;
    font-size: 11px !important;
}
button[title="Supprimer ce snag"]:hover {
    background: #FEE2E2 !important;
    box-shadow: 0 2px 8px rgba(220,38,38,.15) !important;
}

/* Bouton modifier neutre */
button[title="Modifier ce snag"] {
    background: #F8FAFC !important;
    color: #374151 !important;
    border: 1px solid #E5E7EB !important;
    box-shadow: none !important;
    font-size: 11px !important;
}
button[title="Modifier ce snag"]:hover {
    background: #EEF2FF !important;
    color: #3730A3 !important;
    border-color: #C7D2FE !important;
}

/* ── Tabs ── */
[data-testid="stTabs"] [role="tablist"] {
    background: var(--bg-1) !important;
    border-bottom: 2px solid var(--border) !important;
    padding: 0 !important;
    gap: 0 !important;
    border-radius: var(--radius) var(--radius) 0 0 !important;
}
[data-testid="stTabs"] button[role="tab"] {
    background: transparent !important;
    color: var(--text-3) !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    border-radius: 0 !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 12px !important;
    font-weight: 600 !important;
    letter-spacing: .04em !important;
    padding: 14px 20px !important;
    margin-bottom: -2px !important;
    transition: all .15s !important;
}
[data-testid="stTabs"] button[role="tab"]:hover { color: var(--text-1) !important; }
[data-testid="stTabs"] button[aria-selected="true"] {
    color: var(--text-1) !important;
    border-bottom-color: var(--yellow) !important;
    font-weight: 800 !important;
    background: transparent !important;
}
[data-testid="stTabs"] [role="tabpanel"] {
    background: var(--bg-1) !important;
    padding: 24px !important;
    border: 1px solid var(--border) !important;
    border-top: none !important;
    border-radius: 0 0 var(--radius) var(--radius) !important;
}

/* ── Metric ── */
[data-testid="stMetric"] {
    background: var(--bg-1) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius) !important;
    padding: 16px 18px !important;
    box-shadow: var(--shadow-sm) !important;
}
[data-testid="stMetric"] label {
    color: var(--text-3) !important;
    font-size: 10px !important;
    letter-spacing: .06em !important;
    text-transform: uppercase !important;
    font-weight: 700 !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}
[data-testid="stMetric"] [data-testid="stMetricValue"] {
    color: var(--text-1) !important;
    font-size: 28px !important;
    font-weight: 800 !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}

/* ── Alerts ── */
[data-testid="stAlert"] {
    border-radius: var(--radius-sm) !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 13px !important;
    border: 1px solid var(--border) !important;
}

/* ── Radio ── */
[data-testid="stRadio"] label {
    color: var(--text-1) !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 13px !important;
}

/* ── Expander ── */
[data-testid="stExpander"] {
    background: var(--bg-1) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-sm) !important;
}
[data-testid="stExpander"] summary {
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 13px !important;
    color: var(--text-2) !important;
}

hr { border-color: var(--border) !important; margin: 1rem 0 !important; }

::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: var(--bg-2); }
::-webkit-scrollbar-thumb { background: var(--border-d); border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: #9CA3AF; }

[data-testid="stToast"] {
    background: var(--yellow) !important;
    color: var(--text-1) !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-weight: 700 !important;
    border-radius: var(--radius-sm) !important;
    box-shadow: var(--shadow-md) !important;
}

/* Forcer style bouton 🗑 Supprimer */
div[data-testid="stButton"] button:has-text("🗑") {
    background: #FEF2F2 !important;
    color: #DC2626 !important;
    border: 1.5px solid #FECACA !important;
    box-shadow: none !important;
}
div[data-testid="stButton"] button:has-text("🗑"):hover {
    background: #FEE2E2 !important;
    box-shadow: 0 2px 8px rgba(220,38,38,.2) !important;
    transform: none !important;
}
div[data-testid="stButton"] button:has-text("✎") {
    background: #F8FAFC !important;
    color: #374151 !important;
    border: 1.5px solid #E5E7EB !important;
    box-shadow: none !important;
}
div[data-testid="stButton"] button:has-text("✓ Oui") {
    background: #ECFDF5 !important;
    color: #065F46 !important;
    border: 1.5px solid #6EE7B7 !important;
    box-shadow: none !important;
}
div[data-testid="stButton"] button:has-text("✗ Non") {
    background: #FEF2F2 !important;
    color: #DC2626 !important;
    border: 1.5px solid #FECACA !important;
    box-shadow: none !important;
}
</style>
"""

F = "font-family:'Plus Jakarta Sans',sans-serif"

def card(content, border="#E5E7EB", padding="18px 20px", bg="#FFFFFF"):
    return f"""<div style="background:{bg};border:1px solid {border};border-radius:12px;
        padding:{padding};margin-bottom:12px;box-shadow:0 1px 3px rgba(0,0,0,.06);">
        {content}</div>"""

def kpi_card(label, value, sub="", color="#111827", bg="#FFFFFF", accent=""):
    bar = f'<div style="width:36px;height:3px;background:{accent if accent else "#FFD200"};border-radius:2px;margin-bottom:8px;"></div>' if accent else '<div style="width:36px;height:3px;background:#FFD200;border-radius:2px;margin-bottom:8px;"></div>'
    return f"""<div style="background:{bg};border:1px solid #E5E7EB;border-radius:12px;
        padding:18px 20px;box-shadow:0 1px 3px rgba(0,0,0,.06);height:100%;">
        {bar}
        <div style="font-size:10px;color:#6B7280;letter-spacing:.07em;text-transform:uppercase;
            font-weight:700;margin-bottom:6px;{F};">{label}</div>
        <div style="font-size:28px;font-weight:800;color:{color};{F};line-height:1.1;">{value}</div>
        <div style="font-size:11px;color:#9CA3AF;margin-top:4px;{F};">{sub}</div>
    </div>"""

def section_label(text, color="#6B7280"):
    return f"""<div style="font-size:10px;color:{color};letter-spacing:.08em;text-transform:uppercase;
        margin-bottom:12px;font-weight:700;{F};">{text}</div>"""

def badge(text, bg, color, border="transparent"):
    return f"""<span style="background:{bg};color:{color};border:1px solid {border};font-size:10px;
        padding:3px 10px;border-radius:20px;font-weight:600;letter-spacing:.02em;{F};">{text}</span>"""

def progress_bar(pct, color="#FFD200", height=6, bg="#F3F4F6"):
    w = min(100, max(0, pct))
    return f"""<div style="height:{height}px;background:{bg};border-radius:{height}px;overflow:hidden;margin-top:5px;">
        <div style="height:{height}px;width:{w:.1f}%;background:{color};border-radius:{height}px;transition:width .6s ease;"></div>
    </div>"""

def tech_row_card(rank, tech, max_pts):
    medals = {1:"🥇",2:"🥈",3:"🥉"}
    medal  = medals.get(rank, str(rank))
    colors = {1:"#F59E0B",2:"#9CA3AF",3:"#D97706"}
    col    = colors.get(rank, "#6366F1")
    bg     = "background:linear-gradient(135deg,#FFFBEB,#FEF9C3);" if rank==1 else "background:#FFFFFF;"
    border = "border:2px solid #FFD200;" if rank==1 else "border:1px solid #E5E7EB;"
    pct    = (tech["total"]/max_pts*100) if max_pts>0 else 0
    b      = tech["badge"]
    cl     = tech["cluster"]

    return f"""<div style="{bg}{border}border-radius:12px;padding:14px 18px;margin-bottom:8px;
        box-shadow:0 1px 3px rgba(0,0,0,.06);transition:box-shadow .15s;">
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">
            <div style="width:36px;height:36px;border-radius:50%;background:{'#FEF3C7' if rank<=3 else '#F3F4F6'};
                display:flex;align-items:center;justify-content:center;font-size:{'18' if rank<=3 else '12'}px;
                font-weight:700;color:{col};flex-shrink:0;">{medal}</div>
            <div style="flex:1;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
                    <span style="font-size:14px;font-weight:700;color:#111827;{F};">{tech['name']}</span>
                    <div style="display:flex;align-items:center;gap:8px;">
                        <span style="font-size:20px;font-weight:800;color:{'#D97706' if rank==1 else '#111827'};{F};">{tech['total']}</span>
                        <span style="font-size:10px;color:#9CA3AF;{F};">pts</span>
                        {badge(b['label'],b['bg'],b['color'])}
                    </div>
                </div>
                {progress_bar(pct, col if rank<=3 else "#6366F1")}
            </div>
        </div>
        <div style="display:flex;gap:16px;padding-left:48px;font-size:11px;color:#9CA3AF;
            align-items:center;flex-wrap:wrap;{F};">
            <span style="color:#F59E0B;font-weight:600;">↑ {tech['raised']}</span>
            <span style="color:#6366F1;font-weight:600;">✓ {tech['closed']}</span>
            <span style="color:#10B981;font-weight:600;">⟳ {tech['both']}</span>
            <span>{tech['n']} snags</span>
            <span style="margin-left:auto;display:flex;align-items:center;gap:6px;">
                {badge(cl['label'],cl['bg'],cl['color'],cl['border'])}
                <strong style="color:{cl['color']};{F};">{tech['ml_pct']}%</strong>
            </span>
        </div>
    </div>"""

def winner_banner(tech, period):
    cl = tech["cluster"]
    return f"""<div style="background:linear-gradient(135deg,#FFFBEB 0%,#FEF9C3 60%,#FDE68A 100%);
        border:2px solid #FFD200;border-radius:16px;padding:24px 28px;margin-bottom:20px;
        position:relative;overflow:hidden;box-shadow:0 4px 20px rgba(255,210,0,.25);">
        <div style="position:absolute;right:20px;top:-10px;font-size:80px;opacity:.07;
            pointer-events:none;line-height:1;transform:rotate(15deg);">🏆</div>
        <div style="font-size:10px;letter-spacing:.1em;color:#92400E;margin-bottom:8px;
            text-transform:uppercase;font-weight:700;{F};">🏆 LEADER DU MOIS — {period}</div>
        <div style="font-size:32px;font-weight:800;color:#111827;letter-spacing:-.02em;
            margin-bottom:6px;{F};">{tech['name']}</div>
        <div style="font-size:13px;color:#78350F;{F};">
            <strong>{tech['total']} pts</strong> &nbsp;·&nbsp; {tech['n']} snags &nbsp;·&nbsp;
            {tech['closed']} fermés &nbsp;·&nbsp; {tech['both']} R+F
        </div>
        <div style="display:inline-flex;align-items:center;gap:10px;margin-top:12px;
            padding:8px 14px;background:rgba(255,255,255,.7);border-radius:8px;
            font-size:12px;color:#78350F;border:1px solid #FDE68A;{F};">
            Score ML : <strong style="color:#111827;font-size:16px;">{tech['ml_pct']}%</strong>
            &nbsp;—&nbsp; {badge(cl['label'],cl['bg'],cl['color'],cl['border'])}
        </div>
    </div>"""

def action_badge_html(action):
    styles = {
        "raised": ("#FEF3C7","#92400E","#FDE68A"),
        "closed": ("#EEF2FF","#3730A3","#C7D2FE"),
        "both":   ("#ECFDF5","#065F46","#6EE7B7"),
    }
    bg, col, border = styles.get(action, ("#F9FAFB","#6B7280","#E5E7EB"))
    label = {"raised":"Remonté","closed":"Fermé","both":"R+F"}.get(action, action)
    return badge(label, bg, col, border)
