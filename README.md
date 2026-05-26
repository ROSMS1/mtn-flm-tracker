# MTN FLM Performance Tracker — v3.1
**Streamlit + Supabase · South Region**

---

## 🚀 Déploiement en 5 étapes

### Étape 1 — Créer le projet Supabase
1. Aller sur [supabase.com](https://supabase.com) → **New project**
2. Choisir un nom : `mtn-flm-tracker`
3. Définir un mot de passe fort pour la base
4. Région : choisir la plus proche (ex: `eu-west-2`)
5. Attendre la création (~2 min)

### Étape 2 — Créer les tables SQL
1. Dans Supabase Dashboard → **SQL Editor** → **New query**
2. Coller le contenu du fichier `supabase_schema.sql`
3. Cliquer **Run** → vous verrez `Tables créées avec succès ✓`

### Étape 3 — Récupérer les clés Supabase
Dans **Settings > API** :
- **Project URL** : `https://xxxxxxxx.supabase.co`
- **anon public key** : `eyJhbGci...` (clé longue)

### Étape 4 — Configurer les secrets
Créer le fichier `.streamlit/secrets.toml` (copier le template) :
```toml
[supabase]
url = "https://VOTRE_PROJECT_ID.supabase.co"
key = "VOTRE_ANON_KEY"
```
⚠ **Ne jamais committer ce fichier sur GitHub** (ajoutez-le au `.gitignore`)

### Étape 5 — Lancer l'application

**En local :**
```bash
pip install -r requirements.txt
streamlit run app.py
```

**Sur Streamlit Cloud :**
1. Pousser le code sur GitHub (sans `secrets.toml`)
2. [share.streamlit.io](https://share.streamlit.io) → **New app**
3. Sélectionner le repo → fichier `app.py`
4. **Settings > Secrets** → coller le contenu du `secrets.toml`
5. **Deploy** ✓

---

## 📁 Structure des fichiers

```
mtn_flm_tracker/
├── app.py                    ← Application principale
├── scoring.py                ← Moteur de calcul ML
├── supabase_client.py        ← Accès base de données
├── styles.py                 ← CSS & composants HTML
├── requirements.txt          ← Dépendances Python
├── supabase_schema.sql       ← Script création tables
├── README.md                 ← Ce fichier
└── .streamlit/
    ├── config.toml           ← Thème dark MTN
    └── secrets.toml.template ← Template clés Supabase
```

---

## 🗄️ Schéma base de données

### Table `techniciens`
| Colonne    | Type   | Description          |
|------------|--------|----------------------|
| id         | uuid   | Clé primaire         |
| nom        | text   | Nom du technicien    |
| created_at | timestamp | Date création     |

### Table `snags`
| Colonne       | Type    | Description              |
|---------------|---------|--------------------------|
| id            | uuid    | Clé primaire             |
| technicien    | text    | Nom du technicien        |
| site_nom      | text    | Nom du site              |
| site_id       | text    | Identifiant site         |
| site_priorite | text    | P1/P2/TIS/P3/P4          |
| categorie     | text    | Type de snag             |
| action        | text    | raised/closed/both       |
| date_snag     | date    | Date de l'action         |
| description   | text    | Description libre        |
| points        | numeric | Points calculés          |
| annee         | integer | Année de la saisie       |
| mois          | integer | Mois de la saisie (1-12) |
| created_at    | timestamp | Date insertion         |

---

## 📊 Formule de scoring

```
Points = Base catégorie × Multiplicateur priorité × Facteur action

Facteurs action : Remonté×0.4 · Fermé×0.6 · R+F×1.0
Multiplicateurs : P1×2.0 · P2×1.5 · TIS×1.5 · P3×1.2 · P4×1.0

Score ML = Taux fermeture × 100 + Bonus volume
Clusters : Elite ≥75% · Performant ≥55% · En progression ≥35% · Actif
```

---

## 🔧 Dépendances

```
streamlit>=1.35.0
supabase>=2.4.0
pandas>=2.0.0
plotly>=5.18.0
```
