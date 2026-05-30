"""Styles & helpers — MTN FLM Manager Dashboard"""

F = "font-family:'Plus Jakarta Sans',sans-serif;"

MONTHS_FR = ["Janvier","Février","Mars","Avril","Mai","Juin",
             "Juillet","Août","Septembre","Octobre","Novembre","Décembre"]

CATEGORIES = [
    "DG","Battery","Rectifier","ATS","ENERGY_OTHER",
    "TXN","IPRAN","RAN","MW_FADING","MW_EQUIPMENT",
    "ANTENNA","FEEDER","BTS_HW","BTS_SW","PARAMETER",
    "ACCESS","CIVIL","SECURITY","POWER_CABLE","EARTHING",
    "COOLING","SHELTER","FIBER","SWITCH","ROUTER",
    "TRANSPORT","MONITORING","OTHER"
]

SUB_SCORES = {
    "DG":5,"Battery":5,"Rectifier":5,"ATS":4,"ENERGY_OTHER":3,
    "TXN":8,"IPRAN":8,"RAN":8,"MW_FADING":7,"MW_EQUIPMENT":7,
    "ANTENNA":6,"FEEDER":6,"BTS_HW":7,"BTS_SW":7,"PARAMETER":5,
    "ACCESS":4,"CIVIL":4,"SECURITY":4,"POWER_CABLE":4,"EARTHING":4,
    "COOLING":4,"SHELTER":3,"FIBER":6,"SWITCH":6,"ROUTER":6,
    "TRANSPORT":5,"MONITORING":5,"OTHER":3
}

ACTION_FACTOR = {"raised": 0.4, "closed": 0.6, "both": 1.0}
ACTION_LABEL  = {"raised": "Remonté", "closed": "Fermé", "both": "R+F"}
ACTION_COLOR  = {"raised": "#F59E0B", "closed": "#10B981", "both": "#6366F1"}

def calc_pts(cat: str, action: str) -> float:
    return round(SUB_SCORES.get(cat, 3) * ACTION_FACTOR.get(action, 0.6), 2)

def obj_for_month(mois: int) -> int:
    """Objectif progressif : base 100 en janvier, +10% par mois."""
    base = 100
    return round(base * (1.10 ** (mois - 1)))

def obj_color(pct: float) -> str:
    if pct >= 70:  return "#10B981"
    elif pct >= 40: return "#F59E0B"
    else:           return "#EF4444"

def obj_bar_html(pct: float, height: int = 8) -> str:
    c  = obj_color(pct)
    p  = min(pct, 100)
    bg = "#DCFCE7" if pct >= 70 else "#FEF3C7" if pct >= 40 else "#FEE2E2"
    return (
        f'<div style="background:{bg};border-radius:99px;height:{height}px;overflow:hidden;">'
        f'<div style="width:{p}%;height:100%;background:{c};border-radius:99px;"></div></div>'
    )

# ── Composants HTML ──────────────────────────────────────────────────

def kpi_card(label: str, value: str, sub: str = "", accent: str = "#D97706") -> str:
    return f"""<div style="background:#FFFFFF;border:1px solid #E5E7EB;border-radius:10px;
        padding:14px 16px;min-width:0;">
        <div style="font-size:10px;font-weight:700;color:#9CA3AF;letter-spacing:.07em;
            text-transform:uppercase;margin-bottom:6px;{F}">{label}</div>
        <div style="font-size:26px;font-weight:800;color:{accent};line-height:1;{F}">{value}</div>
        {f'<div style="font-size:11px;color:#9CA3AF;margin-top:4px;{F};">{sub}</div>' if sub else ''}
    </div>"""

def section_label(text: str) -> str:
    return f"""<div style="font-size:10px;font-weight:700;color:#9CA3AF;letter-spacing:.08em;
        text-transform:uppercase;margin:16px 0 8px;{F}">{text}</div>"""

def badge(text: str, bg: str = "#F3F4F6", color: str = "#374151",
          border: str = "#E5E7EB") -> str:
    return (f'<span style="background:{bg};color:{color};border:1px solid {border};'
            f'border-radius:20px;padding:2px 9px;font-size:11px;font-weight:600;{F};">{text}</span>')

def status_badge_rca(hrs: float) -> str:
    if hrs is None:
        return badge("En attente","#FEF3C7","#92400E","#FDE68A")
    if hrs >= 72:
        return badge(f"🔴 {hrs:.0f}h","#FEE2E2","#DC2626","#FECACA")
    elif hrs >= 48:
        return badge(f"🟠 {hrs:.0f}h","#FEF3C7","#92400E","#FDE68A")
    else:
        return badge(f"🟢 {hrs:.0f}h","#D1FAE5","#065F46","#6EE7B7")

def status_badge_snag(days_open: int) -> str:
    if days_open > 7:
        return badge(f"🔴 J+{days_open}","#FEE2E2","#DC2626","#FECACA")
    elif days_open >= 5:
        return badge(f"🟠 J+{days_open}","#FEF3C7","#92400E","#FDE68A")
    else:
        return badge(f"🟢 J+{days_open}","#D1FAE5","#065F46","#6EE7B7")

GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif !important; }
.stTabs [data-baseweb="tab-list"] { gap: 4px; background: #F9FAFB;
    border-radius: 10px; padding: 4px; border: 1px solid #E5E7EB; }
.stTabs [data-baseweb="tab"] { border-radius: 8px; font-weight: 700;
    font-size: 12px; padding: 6px 14px; color: #6B7280; }
.stTabs [aria-selected="true"] { background: #FFFFFF !important;
    color: #111827 !important; box-shadow: 0 1px 3px rgba(0,0,0,.08); }
.stButton > button { border-radius: 8px; font-weight: 700; font-size: 12px;
    transition: all .15s; }
div[data-testid="stExpander"] { border: 1px solid #E5E7EB !important;
    border-radius: 10px !important; }
</style>
"""
