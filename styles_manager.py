"""Styles & helpers — FieldPerform v6.2 · Nouveau système de scoring"""

F = "font-family:'Plus Jakarta Sans',sans-serif;"

MONTHS_FR = ["Janvier","Février","Mars","Avril","Mai","Juin",
             "Juillet","Août","Septembre","Octobre","Novembre","Décembre"]

# ── Catégories & barème ──────────────────────────────────────────
CATEGORIES = [
    "TXN","IPRAN","MW_FADING","MW_EQUIPMENT",
    "RAN","ANTENNA","FEEDER","BTS_HW","BTS_SW","PARAMETER",
    "DG","Battery","Rectifier","ATS","ENERGY_OTHER",
    "ACCESS","CIVIL","SECURITY","POWER_CABLE","EARTHING",
    "COOLING","SHELTER","FIBER","SWITCH","ROUTER",
    "TRANSPORT","MONITORING","OTHER"
]

SUB_SCORES = {
    "TXN":8,"IPRAN":8,"MW_FADING":8,"MW_EQUIPMENT":8,
    "RAN":8,"ANTENNA":6,"FEEDER":6,"BTS_HW":7,"BTS_SW":7,"PARAMETER":5,
    "DG":5,"Battery":5,"Rectifier":5,"ATS":4,"ENERGY_OTHER":3,
    "ACCESS":4,"CIVIL":4,"SECURITY":4,"POWER_CABLE":4,"EARTHING":4,
    "COOLING":4,"SHELTER":3,"FIBER":6,"SWITCH":6,"ROUTER":6,
    "TRANSPORT":5,"MONITORING":5,"OTHER":3
}

# Points symboliques à l'ouverture (très faibles)
OPEN_PTS = {
    "TXN":1.0,"IPRAN":1.0,"MW_FADING":1.0,"MW_EQUIPMENT":1.0,
    "RAN":1.0,"ANTENNA":0.5,"FEEDER":0.5,"BTS_HW":1.0,"BTS_SW":1.0,"PARAMETER":0.5,
    "DG":0.5,"Battery":0.5,"Rectifier":0.5,"ATS":0.5,"ENERGY_OTHER":0.5,
    "ACCESS":0.5,"CIVIL":0.5,"SECURITY":0.5,"POWER_CABLE":0.5,"EARTHING":0.5,
    "COOLING":0.5,"SHELTER":0.5,"FIBER":0.5,"SWITCH":0.5,"ROUTER":0.5,
    "TRANSPORT":0.5,"MONITORING":0.5,"OTHER":0.5
}

# Facteurs de fermeture selon délai
CLOSE_FACTORS = {
    "bonus":  {"label":"≤ 3j — Bonus rapidité",    "factor":1.5, "color":"#10B981","bg":"#D1FAE5","border":"#6EE7B7"},
    "normal": {"label":"4–7j — Dans les délais",   "factor":1.0, "color":"#3B6D11","bg":"#EAF3DE","border":"#C0DD97"},
    "late1":  {"label":"8–14j — Retard modéré",    "factor":0.6, "color":"#BA7517","bg":"#FEF3C7","border":"#FDE68A"},
    "late2":  {"label":">14j — Retard grave",      "factor":0.3, "color":"#DC2626","bg":"#FEE2E2","border":"#FECACA"},
    "none":   {"label":"Non fermé — symbolique",   "factor":0.0, "color":"#9CA3AF","bg":"#F9FAFB","border":"#E5E7EB"},
}

ACTION_LABEL = {"raised":"Remonté","closed":"Fermé","both":"R+F"}
ACTION_COLOR = {"raised":"#6366F1","closed":"#10B981","both":"#F59E0B"}

def get_close_factor_key(days: int) -> str:
    if days is None:   return "none"
    if days <= 3:      return "bonus"
    if days <= 7:      return "normal"
    if days <= 14:     return "late1"
    return "late2"

def calc_open_pts(categorie: str) -> float:
    """Points symboliques à l'ouverture du ticket."""
    return OPEN_PTS.get(categorie, 0.5)

def calc_close_pts(categorie: str, days_to_close) -> float:
    """Points à la fermeture selon délai."""
    base   = SUB_SCORES.get(categorie, 3)
    key    = get_close_factor_key(days_to_close)
    factor = CLOSE_FACTORS[key]["factor"]
    return round(base * factor, 2)

def calc_pts(categorie: str, action: str, days_to_close=5) -> float:
    """Calcul total : ouverture + fermeture selon action."""
    if action == "raised":
        return calc_open_pts(categorie)
    elif action == "closed":
        return calc_close_pts(categorie, days_to_close)
    elif action == "both":
        return round(calc_open_pts(categorie) + calc_close_pts(categorie, days_to_close), 2)
    return 0.0

def obj_for_month(mois: int) -> int:
    """Objectif progressif : base 100 en janvier, +10% par mois."""
    return round(100 * (1.10 ** (mois - 1)))

def obj_color(pct: float) -> str:
    if pct >= 70:   return "#10B981"
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

def delay_badge_html(days) -> str:
    """Badge coloré selon le délai de fermeture."""
    key = get_close_factor_key(days)
    cf  = CLOSE_FACTORS[key]
    label = f"J+{days}" if days is not None else "En cours"
    return (f'<span style="background:{cf["bg"]};color:{cf["color"]};'
            f'border:1px solid {cf["border"]};border-radius:20px;'
            f'padding:2px 9px;font-size:11px;font-weight:600;{F}">{label}</span>')

# ── Composants HTML ──────────────────────────────────────────────

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

def status_badge_rca(hrs) -> str:
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

def get_cluster(obj_pct: float) -> dict:
    if obj_pct >= 80:
        return {"label":"Elite","color":"#D97706","bg":"#FFFBEB","border":"#FDE68A"}
    elif obj_pct >= 60:
        return {"label":"Performant","color":"#6366F1","bg":"#EEF2FF","border":"#C7D2FE"}
    elif obj_pct >= 40:
        return {"label":"En progression","color":"#10B981","bg":"#ECFDF5","border":"#6EE7B7"}
    else:
        return {"label":"Alerte","color":"#EF4444","bg":"#FEF2F2","border":"#FECACA"}

def get_perf_status(close_rate: float, avg_delay) -> dict:
    """Statut basé sur taux de fermeture et délai moyen."""
    delay = avg_delay or 99
    if close_rate >= 85 and delay <= 7:
        return {"label":"Elite","color":"#D97706","bg":"#FFFBEB","border":"#FDE68A","icon":"🏆"}
    elif close_rate >= 70:
        return {"label":"Performant","color":"#3B6D11","bg":"#EAF3DE","border":"#C0DD97","icon":"⭐"}
    elif close_rate >= 50:
        return {"label":"En progression","color":"#BA7517","bg":"#FEF3C7","border":"#FDE68A","icon":"📈"}
    else:
        return {"label":"Alerte","color":"#DC2626","bg":"#FEE2E2","border":"#FECACA","icon":"🔴"}

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
