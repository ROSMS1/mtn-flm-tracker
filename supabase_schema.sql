-- ════════════════════════════════════════════════════════
--  MTN FLM Tracker — Script SQL Supabase
--  Coller dans : Supabase Dashboard > SQL Editor > New query
-- ════════════════════════════════════════════════════════

-- ── Table techniciens ────────────────────────────────────
CREATE TABLE IF NOT EXISTS techniciens (
    id         uuid        DEFAULT gen_random_uuid() PRIMARY KEY,
    nom        text        NOT NULL,
    created_at timestamptz DEFAULT now(),
    CONSTRAINT techniciens_nom_unique UNIQUE (nom)
);

-- ── Table snags ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS snags (
    id             uuid        DEFAULT gen_random_uuid() PRIMARY KEY,
    technicien     text        NOT NULL,
    site_nom       text        NOT NULL,
    site_id        text        DEFAULT '',
    site_priorite  text        NOT NULL DEFAULT 'P4',
    categorie      text        NOT NULL DEFAULT 'DG',
    action         text        NOT NULL DEFAULT 'closed'
                               CHECK (action IN ('raised','closed','both')),
    date_snag      date        NOT NULL,
    description    text        DEFAULT '',
    points         numeric     NOT NULL DEFAULT 0,
    annee          integer     NOT NULL,
    mois           integer     NOT NULL,
    created_at     timestamptz DEFAULT now()
);

-- ── Index pour accélérer les requêtes par période ────────
CREATE INDEX IF NOT EXISTS snags_periode_idx
    ON snags (annee, mois);

CREATE INDEX IF NOT EXISTS snags_technicien_idx
    ON snags (technicien);

-- ── Row Level Security (RLS) — optionnel ─────────────────
-- Décommentez si vous souhaitez sécuriser l'accès :
--
-- ALTER TABLE techniciens ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE snags       ENABLE ROW LEVEL SECURITY;
--
-- CREATE POLICY "Accès public lecture"
--     ON techniciens FOR SELECT USING (true);
-- CREATE POLICY "Accès public écriture"
--     ON techniciens FOR ALL USING (true);
--
-- CREATE POLICY "Accès public lecture snags"
--     ON snags FOR SELECT USING (true);
-- CREATE POLICY "Accès public écriture snags"
--     ON snags FOR ALL USING (true);

-- ── Vérification ─────────────────────────────────────────
SELECT 'Tables créées avec succès ✓' AS statut;
