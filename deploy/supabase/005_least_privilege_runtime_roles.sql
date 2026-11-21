-- Flowstead T-019 live Supabase demo security boundary, 2026-11-21.
-- Applies ONLY to existing flowstead-demo. NO LOGIN/password created here.
-- Application data lives in private app schema, not exposed to Data API.
BEGIN;

-- Retire overly broad existing role privileges BEFORE enabling any login.
ALTER ROLE flowstead_runtime NOLOGIN;
REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA app FROM flowstead_runtime;
REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA app FROM flowstead_runtime;
REVOKE ALL PRIVILEGES ON SCHEMA app FROM flowstead_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA app
    REVOKE ALL ON TABLES FROM flowstead_runtime;
ALTER DEFAULT PRIVILEGES FOR ROLE postgres IN SCHEMA app
    REVOKE ALL ON SEQUENCES FROM flowstead_runtime;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'flowstead_api')
     OR EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'flowstead_worker') THEN
    RAISE EXCEPTION 'A live Flowstead role already exists; review before applying';
  END IF;
  CREATE ROLE flowstead_api NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB
    NOCREATEROLE NOREPLICATION CONNECTION LIMIT 6;
  CREATE ROLE flowstead_worker NOLOGIN NOINHERIT NOSUPERUSER NOCREATEDB
    NOCREATEROLE NOREPLICATION CONNECTION LIMIT 4;
END $$;

GRANT CONNECT ON DATABASE postgres TO flowstead_api, flowstead_worker;
GRANT USAGE ON SCHEMA app TO flowstead_api, flowstead_worker;

-- API: reads and authorization-scoped queue submissions only.
GRANT SELECT ON TABLE
    app.plants, app.hourly_readings, app.ingest_batches,
    app.operator_plant_access, app.forecast_issuances,
    app.forecast_hours, app.forecast_jobs
    TO flowstead_api;
GRANT INSERT ON TABLE app.forecast_jobs, app.message_outbox
    TO flowstead_api;

-- Worker: durable dispatch, result generation, and job completion.
GRANT SELECT ON TABLE
    app.plants, app.hourly_readings, app.ingest_batches,
    app.operator_plant_access, app.forecast_issuances,
    app.forecast_hours, app.forecast_jobs, app.message_outbox,
    app.message_inbox, app.message_failures
    TO flowstead_worker;
GRANT INSERT ON TABLE
    app.forecast_issuances, app.forecast_hours, app.message_outbox,
    app.message_inbox, app.message_failures
    TO flowstead_worker;
GRANT UPDATE ON TABLE
    app.forecast_jobs, app.message_outbox, app.message_failures
    TO flowstead_worker;
GRANT USAGE, SELECT ON SEQUENCE
    app.forecast_issuances_id_seq, app.message_failures_id_seq
    TO flowstead_worker;

-- Public migration marker tables: RLS as an extra deny layer.
ALTER TABLE public.schema_migrations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.alembic_version ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.schema_migrations, public.alembic_version
    FROM anon, authenticated, flowstead_api, flowstead_worker;

ALTER ROLE flowstead_api SET statement_timeout = '15s';
ALTER ROLE flowstead_api SET idle_in_transaction_session_timeout = '15s';
ALTER ROLE flowstead_worker SET statement_timeout = '30s';
ALTER ROLE flowstead_worker SET idle_in_transaction_session_timeout = '30s';
COMMIT;
