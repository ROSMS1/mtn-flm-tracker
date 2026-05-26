# ════════════════════════════════════════════════════════
#  MTN FLM Tracker — Supabase Client (REST API direct)
#  Compatible Python 3.14+ — pas de dépendance websockets
# ════════════════════════════════════════════════════════
import streamlit as st
import requests
import pandas as pd
from datetime import date


def _headers():
    key = st.secrets["supabase"]["key"]
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

def _url(table: str) -> str:
    base = st.secrets["supabase"]["url"].rstrip("/")
    return f"{base}/rest/v1/{table}"


# ── TECHNICIENS ──────────────────────────────────────────

def fetch_techniciens() -> list[str]:
    try:
        r = requests.get(
            _url("flm_techniciens"),
            headers=_headers(),
            params={"select": "nom", "order": "nom.asc"},
            timeout=10,
        )
        r.raise_for_status()
        return [row["nom"] for row in r.json()]
    except Exception as e:
        st.error(f"Erreur chargement techniciens : {e}")
        return []


def add_technicien(nom: str) -> bool:
    try:
        r = requests.post(
            _url("flm_techniciens"),
            headers=_headers(),
            json={"nom": nom.strip()},
            timeout=10,
        )
        r.raise_for_status()
        return True
    except Exception as e:
        st.error(f"Erreur ajout technicien : {e}")
        return False


def rename_technicien(old_nom: str, new_nom: str) -> bool:
    try:
        h = _headers()
        # Renommer dans flm_techniciens
        r1 = requests.patch(
            _url("flm_techniciens"),
            headers={**h, "Prefer": "return=minimal"},
            params={"nom": f"eq.{old_nom}"},
            json={"nom": new_nom.strip()},
            timeout=10,
        )
        r1.raise_for_status()
        # Mettre à jour les saisies
        r2 = requests.patch(
            _url("flm_snags"),
            headers={**h, "Prefer": "return=minimal"},
            params={"technicien": f"eq.{old_nom}"},
            json={"technicien": new_nom.strip()},
            timeout=10,
        )
        r2.raise_for_status()
        return True
    except Exception as e:
        st.error(f"Erreur renommage : {e}")
        return False


def delete_technicien(nom: str) -> bool:
    try:
        r = requests.delete(
            _url("flm_techniciens"),
            headers={**_headers(), "Prefer": "return=minimal"},
            params={"nom": f"eq.{nom}"},
            timeout=10,
        )
        r.raise_for_status()
        return True
    except Exception as e:
        st.error(f"Erreur suppression technicien : {e}")
        return False


# ── SNAGS ────────────────────────────────────────────────

def fetch_snags(annee: int, mois: int) -> pd.DataFrame:
    try:
        r = requests.get(
            _url("flm_snags"),
            headers=_headers(),
            params={
                "select": "*",
                "annee": f"eq.{annee}",
                "mois": f"eq.{mois}",
                "order": "date_snag.desc",
            },
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        if not data:
            return pd.DataFrame()
        df = pd.DataFrame(data)
        df["date_snag"] = pd.to_datetime(df["date_snag"]).dt.date
        df["points"]    = df["points"].astype(float)
        return df
    except Exception as e:
        st.error(f"Erreur chargement snags : {e}")
        return pd.DataFrame()


def insert_snag(row: dict) -> bool:
    try:
        r = requests.post(
            _url("flm_snags"),
            headers=_headers(),
            json=row,
            timeout=10,
        )
        r.raise_for_status()
        return True
    except Exception as e:
        st.error(f"Erreur insertion snag : {e}")
        return False


def update_snag(snag_id: str, row: dict) -> bool:
    try:
        r = requests.patch(
            _url("flm_snags"),
            headers={**_headers(), "Prefer": "return=minimal"},
            params={"id": f"eq.{snag_id}"},
            json=row,
            timeout=10,
        )
        r.raise_for_status()
        return True
    except Exception as e:
        st.error(f"Erreur mise à jour snag : {e}")
        return False


def delete_snag(snag_id: str) -> bool:
    try:
        r = requests.delete(
            _url("flm_snags"),
            headers={**_headers(), "Prefer": "return=minimal"},
            params={"id": f"eq.{snag_id}"},
            timeout=10,
        )
        r.raise_for_status()
        return True
    except Exception as e:
        st.error(f"Erreur suppression snag : {e}")
        return False
