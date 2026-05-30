"""
Supabase client — MTN FLM Manager Dashboard
Tables: manager_techs, manager_snags, manager_rca, manager_asset, manager_blockers
"""
import os
import streamlit as st
from supabase import create_client, Client

@st.cache_resource
def get_client() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

# ─── DDL auto-création des tables ─────────────────────────────────────
def ensure_tables():
    """Appeler une fois au démarrage pour créer les tables si absentes."""
    sb = get_client()
    # On vérifie l'existence en faisant un select silencieux
    try:
        sb.table("manager_techs").select("id").limit(1).execute()
    except Exception:
        pass  # La table sera créée via Supabase SQL Editor

# ─── TECHNICIENS ──────────────────────────────────────────────────────
def fetch_techs():
    try:
        r = get_client().table("manager_techs").select("*").order("nom").execute()
        return r.data or []
    except Exception as e:
        st.error(f"Erreur fetch_techs: {e}")
        return []

def add_tech(nom: str, region: str = "South", equipe: str = "FLM"):
    try:
        get_client().table("manager_techs").insert(
            {"nom": nom, "region": region, "equipe": equipe}
        ).execute()
        return True
    except Exception as e:
        st.error(f"Erreur add_tech: {e}")
        return False

def delete_tech(tech_id: int):
    try:
        get_client().table("manager_techs").delete().eq("id", tech_id).execute()
        return True
    except Exception as e:
        st.error(f"Erreur delete_tech: {e}")
        return False

def update_tech(tech_id: int, nom: str, region: str, equipe: str):
    try:
        get_client().table("manager_techs").update(
            {"nom": nom, "region": region, "equipe": equipe}
        ).eq("id", tech_id).execute()
        return True
    except Exception as e:
        st.error(f"Erreur update_tech: {e}")
        return False

# ─── SNAGS MANAGER ────────────────────────────────────────────────────
def fetch_snags_manager(annee: int, mois: int):
    try:
        r = (get_client().table("manager_snags")
             .select("*")
             .eq("annee", annee).eq("mois", mois)
             .order("date_snag", desc=True)
             .execute())
        return r.data or []
    except Exception as e:
        st.error(f"Erreur fetch_snags_manager: {e}")
        return []

def fetch_snags_6months(tech_nom: str):
    try:
        r = (get_client().table("manager_snags")
             .select("annee,mois,points,action")
             .eq("technicien", tech_nom)
             .execute())
        return r.data or []
    except Exception as e:
        return []

def insert_snag_manager(row: dict):
    try:
        get_client().table("manager_snags").insert(row).execute()
        return True
    except Exception as e:
        st.error(f"Erreur insert_snag: {e}")
        return False

def update_snag_manager(snag_id: int, row: dict):
    try:
        get_client().table("manager_snags").update(row).eq("id", snag_id).execute()
        return True
    except Exception as e:
        st.error(f"Erreur update_snag: {e}")
        return False

def delete_snag_manager(snag_id: int):
    try:
        get_client().table("manager_snags").delete().eq("id", snag_id).execute()
        return True
    except Exception as e:
        st.error(f"Erreur delete_snag: {e}")
        return False

# ─── RCA ──────────────────────────────────────────────────────────────
def fetch_rca(annee: int, mois: int):
    try:
        r = (get_client().table("manager_rca")
             .select("*")
             .eq("annee", annee).eq("mois", mois)
             .order("date_incident", desc=True)
             .execute())
        return r.data or []
    except Exception as e:
        st.error(f"Erreur fetch_rca: {e}")
        return []

def insert_rca(row: dict):
    try:
        get_client().table("manager_rca").insert(row).execute()
        return True
    except Exception as e:
        st.error(f"Erreur insert_rca: {e}")
        return False

def update_rca(rca_id: int, row: dict):
    try:
        get_client().table("manager_rca").update(row).eq("id", rca_id).execute()
        return True
    except Exception as e:
        st.error(f"Erreur update_rca: {e}")
        return False

def delete_rca(rca_id: int):
    try:
        get_client().table("manager_rca").delete().eq("id", rca_id).execute()
        return True
    except Exception as e:
        st.error(f"Erreur delete_rca: {e}")
        return False

# ─── ASSET ────────────────────────────────────────────────────────────
def fetch_asset(annee: int, mois: int):
    try:
        r = (get_client().table("manager_asset")
             .select("*")
             .eq("annee", annee).eq("mois", mois)
             .order("nom")
             .execute())
        return r.data or []
    except Exception as e:
        st.error(f"Erreur fetch_asset: {e}")
        return []

def insert_asset(row: dict):
    try:
        get_client().table("manager_asset").insert(row).execute()
        return True
    except Exception as e:
        st.error(f"Erreur insert_asset: {e}")
        return False

def update_asset(asset_id: int, row: dict):
    try:
        get_client().table("manager_asset").update(row).eq("id", asset_id).execute()
        return True
    except Exception as e:
        st.error(f"Erreur update_asset: {e}")
        return False

def delete_asset(asset_id: int):
    try:
        get_client().table("manager_asset").delete().eq("id", asset_id).execute()
        return True
    except Exception as e:
        st.error(f"Erreur delete_asset: {e}")
        return False

# ─── POINTS BLOQUANTS ─────────────────────────────────────────────────
def fetch_blockers(annee: int, mois: int):
    try:
        r = (get_client().table("manager_blockers")
             .select("*")
             .eq("annee", annee).eq("mois", mois)
             .order("date_signal", desc=True)
             .execute())
        return r.data or []
    except Exception as e:
        st.error(f"Erreur fetch_blockers: {e}")
        return []

def insert_blocker(row: dict):
    try:
        get_client().table("manager_blockers").insert(row).execute()
        return True
    except Exception as e:
        st.error(f"Erreur insert_blocker: {e}")
        return False

def update_blocker(blocker_id: int, row: dict):
    try:
        get_client().table("manager_blockers").update(row).eq("id", blocker_id).execute()
        return True
    except Exception as e:
        st.error(f"Erreur update_blocker: {e}")
        return False

def delete_blocker(blocker_id: int):
    try:
        get_client().table("manager_blockers").delete().eq("id", blocker_id).execute()
        return True
    except Exception as e:
        st.error(f"Erreur delete_blocker: {e}")
        return False
