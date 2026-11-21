-- Flowstead live least-privilege review refinement.
-- Worker validates enqueued forecast-job provenance via app.forecast_jobs;
-- it must not inspect operator-to-Plant authorization assignments.
-- API retains only SELECT on assignments to make authorization decisions.
BEGIN;
REVOKE SELECT ON TABLE app.operator_plant_access FROM flowstead_worker;
COMMIT;
