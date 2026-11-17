ALTER TABLE app.forecast_issuances
    DROP COLUMN IF EXISTS physical_bound_rule;

ALTER TABLE app.forecast_issuances
    DROP COLUMN IF EXISTS source_revision;
