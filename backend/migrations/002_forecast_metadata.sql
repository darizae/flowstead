ALTER TABLE app.forecast_issuances
    ADD COLUMN IF NOT EXISTS source_revision text;

ALTER TABLE app.forecast_issuances
    ADD COLUMN IF NOT EXISTS physical_bound_rule text;
