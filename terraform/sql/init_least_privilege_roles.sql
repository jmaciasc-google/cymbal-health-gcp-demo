-- =============================================================================
-- Cymbal Health IPS — PostgreSQL 15 Least Privilege Schema & Agent Read-Only View
-- Target Instance : cymbal-health-pg-main (cymbal_health_db)
-- Security Rule   : cymbal-health-agent-sa receives SELECT ONLY on the
--                   sanitized clinical_orders_public_v view. Zero write verbs,
--                   zero access to confidential = 1 Ley 1581 restricted rows.
-- =============================================================================

BEGIN;

CREATE TABLE IF NOT EXISTS public.clinical_orders (
    id                  SERIAL PRIMARY KEY,
    order_code          VARCHAR(32) UNIQUE NOT NULL,
    folio_number        VARCHAR(48) NOT NULL,
    patient_alias       VARCHAR(140) NOT NULL,
    document_masked     VARCHAR(64) NOT NULL,
    eps_name            VARCHAR(96) NOT NULL DEFAULT 'EPS Sanitas / Red Adscrita',
    specialty           VARCHAR(80) NOT NULL,
    cups_code           VARCHAR(16) NOT NULL DEFAULT '895001',
    cie10_code          VARCHAR(16) NOT NULL DEFAULT 'I10X',
    procedure_name      VARCHAR(180) NOT NULL,
    center_city         VARCHAR(64) NOT NULL,
    attending_physician VARCHAR(120) NOT NULL DEFAULT 'Dra. Valeria Montoya - RM 76412-CO',
    status              VARCHAR(32) NOT NULL,
    priority            VARCHAR(24) NOT NULL,
    support_pdf_object  VARCHAR(255) NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    clinical_summary    TEXT NOT NULL,
    patient_preparation TEXT NOT NULL DEFAULT 'Presentar documento de identidad original y orden vigente 20 minutos antes.',
    confidential        INTEGER NOT NULL DEFAULT 0
);

CREATE OR REPLACE VIEW public.clinical_orders_public_v AS
SELECT
    order_code,
    folio_number,
    patient_alias,
    document_masked,
    eps_name,
    specialty,
    cups_code,
    cie10_code,
    procedure_name,
    center_city,
    attending_physician,
    status,
    priority,
    support_pdf_object,
    created_at,
    clinical_summary,
    patient_preparation
FROM public.clinical_orders
WHERE confidential = 0;

REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM PUBLIC;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'cymbal_portal_rw') THEN
        CREATE ROLE cymbal_portal_rw NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'cymbal_agent_readonly') THEN
        CREATE ROLE cymbal_agent_readonly NOLOGIN;
    END IF;
END
$$;

GRANT SELECT, INSERT, UPDATE ON TABLE public.clinical_orders TO cymbal_portal_rw;
GRANT USAGE, SELECT ON SEQUENCE public.clinical_orders_id_seq TO cymbal_portal_rw;
GRANT SELECT ON public.clinical_orders_public_v TO cymbal_portal_rw;
REVOKE DELETE, TRUNCATE ON TABLE public.clinical_orders FROM cymbal_portal_rw;

REVOKE ALL ON TABLE public.clinical_orders FROM cymbal_agent_readonly;
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON public.clinical_orders_public_v FROM cymbal_agent_readonly;
GRANT SELECT ON public.clinical_orders_public_v TO cymbal_agent_readonly;

DO $$
DECLARE
    portal_iam_role TEXT;
    agent_iam_role  TEXT;
BEGIN
    SELECT rolname INTO portal_iam_role
    FROM pg_roles
    WHERE rolname LIKE 'cymbal-health-portal-sa@%.iam'
    LIMIT 1;

    IF portal_iam_role IS NOT NULL THEN
        EXECUTE format('GRANT cymbal_portal_rw TO %I', portal_iam_role);
    END IF;

    SELECT rolname INTO agent_iam_role
    FROM pg_roles
    WHERE rolname LIKE 'cymbal-health-agent-sa@%.iam'
    LIMIT 1;

    IF agent_iam_role IS NOT NULL THEN
        EXECUTE format('REVOKE ALL ON TABLE public.clinical_orders FROM %I', agent_iam_role);
        EXECUTE format('GRANT cymbal_agent_readonly TO %I', agent_iam_role);
    END IF;
END
$$;

COMMIT;
