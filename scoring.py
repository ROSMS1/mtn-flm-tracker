# ════════════════════════════════════════════════════════
#  MTN FLM Tracker — Scoring Engine (sans priorité site)
# ════════════════════════════════════════════════════════

SUB_SCORES = {
    "TXN/RAN/IPRAN": 8, "Active Hardware": 6,
    "DG": 5, "Battery backup": 5, "ATS": 5, "Rectifier": 5,
    "SPD": 4, "DG Battery": 4, "Breaker": 4, "Control Panel": 4,
    "Static charger": 4, "AirCon": 4, "Cooling": 4,
    "AVR": 3, "Aviation light": 3, "Automation": 3, "Monitoring": 3,
    "Earthing": 3, "PWR Dimen": 3, "SNE": 3, "Fiber": 3,
    "Solar": 3, "Tank Cover": 3,
    "Tank cleaning": 2, "Rack": 2, "backup batteries": 2,
    "Environmental": 2, "Others": 2,
}

ACTION_FACTOR  = {"raised": 0.4, "closed": 0.6, "both": 1.0}
ACTION_LABEL   = {"raised": "Remonté", "closed": "Fermé", "both": "R+F"}
ACTION_COLOR   = {"raised": "#F59E0B", "closed": "#6366F1", "both": "#10B981"}
ACTION_LIGHT   = {"raised": "#FEF3C7", "closed": "#EEF2FF", "both": "#D1FAE5"}
ACTION_BORDER  = {"raised": "#FDE68A", "closed": "#C7D2FE", "both": "#6EE7B7"}

CATEGORIES = sorted(SUB_SCORES.keys())
MONTHS_FR  = ["Janvier","Février","Mars","Avril","Mai","Juin",
               "Juillet","Août","Septembre","Octobre","Novembre","Décembre"]


def calc_pts(sub: str, act: str) -> float:
    """Points = Base catégorie × Facteur action (priorité supprimée)"""
    b = SUB_SCORES.get(sub, 2)
    f = ACTION_FACTOR.get(act, 0.6)
    return round(b * f, 1)


def get_cluster(ml_pct: float, n: int) -> dict:
    if ml_pct >= 75 and n >= 5:
        return {"label":"Elite",          "color":"#92400E","bg":"#FEF3C7","border":"#FDE68A"}
    if ml_pct >= 55 and n >= 3:
        return {"label":"Performant",     "color":"#3730A3","bg":"#EEF2FF","border":"#C7D2FE"}
    if ml_pct >= 35:
        return {"label":"En progression", "color":"#065F46","bg":"#ECFDF5","border":"#6EE7B7"}
    return     {"label":"Actif",          "color":"#374151","bg":"#F9FAFB","border":"#E5E7EB"}


def badge_def(rank: int, total: float, max_pts: float) -> dict:
    ratio = (total / max_pts * 100) if max_pts > 0 else 0
    if rank == 1: return {"label":"Champion 🏆","bg":"#FFD200","color":"#78350F"}
    if rank == 2: return {"label":"Vice-champ", "bg":"#F3F4F6","color":"#374151"}
    if rank == 3: return {"label":"3ème",        "bg":"#FEF3C7","color":"#92400E"}
    if ratio >= 70: return {"label":"Excellent", "bg":"#ECFDF5","color":"#065F46"}
    if ratio >= 40: return {"label":"Bon",       "bg":"#EEF2FF","color":"#3730A3"}
    return {"label":"En cours","bg":"#F9FAFB","color":"#6B7280"}


def build_leaderboard(df) -> list:
    if df.empty:
        return []
    lb = []
    for name, grp in df.groupby("technicien"):
        total  = round(grp["points"].sum(), 1)
        raised = int((grp["action"] == "raised").sum())
        closed = int((grp["action"] == "closed").sum())
        both   = int((grp["action"] == "both").sum())
        n      = len(grp)
        closed_ratio = (closed + both) / n if n > 0 else 0
        bonus  = 5 if n >= 8 else (3 if n >= 5 else 0)
        ml_pct = min(100, round(closed_ratio * 100 + bonus))
        lb.append({"name":name,"total":total,"raised":raised,
                   "closed":closed,"both":both,"n":n,
                   "ml_pct":ml_pct,"cluster":get_cluster(ml_pct,n)})
    lb.sort(key=lambda x: x["total"], reverse=True)
    for i, t in enumerate(lb):
        t["rank"]  = i + 1
        t["badge"] = badge_def(i+1, t["total"], lb[0]["total"])
    return lb
