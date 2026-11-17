"""Create the observed Flowstead baseline schema.

Revision ID: 001_initial
Revises:
"""

from alembic import op


revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


_INITIAL_SCHEMA = """
CREATE SCHEMA IF NOT EXISTS app;

CREATE TABLE IF NOT EXISTS app.ingest_batches (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    content_sha256 char(64) NOT NULL UNIQUE,
    source_sha char(40) NOT NULL,
    schema_version text NOT NULL,
    generator_version text NOT NULL,
    seed integer NOT NULL,
    manifest_sha256 char(64) NOT NULL,
    row_count integer NOT NULL CHECK (row_count > 0 AND row_count <= 43800),
    content_bytes integer NOT NULL CHECK (content_bytes > 0 AND content_bytes <= 4247080),
    imported_at timestamptz NOT NULL DEFAULT now(),
    CHECK (source_sha ~ '^[0-9a-f]{40}$'),
    CHECK (content_sha256 ~ '^[0-9a-f]{64}$'),
    CHECK (manifest_sha256 ~ '^[0-9a-f]{64}$')
);

CREATE TABLE IF NOT EXISTS app.plants (
    plant_id text PRIMARY KEY,
    name text NOT NULL,
    city text NOT NULL,
    state_code text NOT NULL CHECK (state_code = 'FL'),
    timezone text NOT NULL,
    latitude numeric(8,5) NOT NULL CHECK (latitude BETWEEN 24.3 AND 31.1),
    longitude numeric(8,5) NOT NULL CHECK (longitude BETWEEN -88.0 AND -79.5),
    hydraulic_capacity_gal_h numeric(14,2) NOT NULL CHECK (hydraulic_capacity_gal_h > 0),
    public_demo boolean NOT NULL DEFAULT false,
    CHECK (plant_id <> '')
);

CREATE TABLE IF NOT EXISTS app.hourly_readings (
    plant_id text NOT NULL REFERENCES app.plants (plant_id),
    timestamp_utc timestamptz NOT NULL,
    influent_flow numeric,
    influent_flow_quality text NOT NULL,
    rainfall numeric,
    rainfall_quality text NOT NULL,
    dissolved_oxygen numeric,
    dissolved_oxygen_quality text NOT NULL,
    effluent_ph numeric,
    effluent_ph_quality text NOT NULL,
    source_batch_id bigint NOT NULL REFERENCES app.ingest_batches (id),
    PRIMARY KEY (plant_id, timestamp_utc),
    CONSTRAINT hourly_readings_utc CHECK (
        extract(minute FROM timestamp_utc) = 0
        AND extract(second FROM timestamp_utc) = 0
    ),
    CONSTRAINT hourly_readings_influent_quality CHECK (
        (influent_flow_quality = 'missing' AND influent_flow IS NULL)
        OR (influent_flow_quality IN ('valid', 'invalid') AND influent_flow IS NOT NULL
            AND influent_flow::text NOT IN ('NaN', 'Infinity', '-Infinity'))
    ),
    CONSTRAINT hourly_readings_rainfall_quality CHECK (
        (rainfall_quality = 'missing' AND rainfall IS NULL)
        OR (rainfall_quality IN ('valid', 'invalid') AND rainfall IS NOT NULL
            AND rainfall::text NOT IN ('NaN', 'Infinity', '-Infinity'))
    ),
    CONSTRAINT hourly_readings_do_quality CHECK (
        (dissolved_oxygen_quality = 'missing' AND dissolved_oxygen IS NULL)
        OR (dissolved_oxygen_quality IN ('valid', 'invalid') AND dissolved_oxygen IS NOT NULL
            AND dissolved_oxygen::text NOT IN ('NaN', 'Infinity', '-Infinity'))
    ),
    CONSTRAINT hourly_readings_ph_quality CHECK (
        (effluent_ph_quality = 'missing' AND effluent_ph IS NULL)
        OR (effluent_ph_quality IN ('valid', 'invalid') AND effluent_ph IS NOT NULL
            AND effluent_ph::text NOT IN ('NaN', 'Infinity', '-Infinity'))
    )
);

CREATE INDEX IF NOT EXISTS hourly_readings_timestamp_idx
    ON app.hourly_readings (timestamp_utc);
CREATE INDEX IF NOT EXISTS hourly_readings_plant_time_idx
    ON app.hourly_readings (plant_id, timestamp_utc DESC);

CREATE TABLE IF NOT EXISTS app.operator_plant_access (
    subject_id text NOT NULL,
    plant_id text NOT NULL REFERENCES app.plants (plant_id),
    PRIMARY KEY (subject_id, plant_id),
    CHECK (subject_id <> '')
);

CREATE TABLE IF NOT EXISTS app.forecast_issuances (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    plant_id text NOT NULL REFERENCES app.plants (plant_id),
    issued_at timestamptz NOT NULL,
    model_version text NOT NULL,
    UNIQUE (plant_id, issued_at)
);

CREATE TABLE IF NOT EXISTS app.forecast_hours (
    issuance_id bigint NOT NULL REFERENCES app.forecast_issuances (id) ON DELETE CASCADE,
    target_time timestamptz NOT NULL,
    predicted_flow numeric NOT NULL CHECK (predicted_flow::text NOT IN ('NaN', 'Infinity', '-Infinity')),
    hour_number smallint NOT NULL CHECK (hour_number BETWEEN 1 AND 12),
    PRIMARY KEY (issuance_id, target_time),
    UNIQUE (issuance_id, hour_number)
);

CREATE INDEX IF NOT EXISTS forecast_hours_target_idx
    ON app.forecast_hours (target_time);
"""


def upgrade() -> None:
    connection = op.get_bind()
    connection.exec_driver_sql(
        "CREATE TABLE IF NOT EXISTS public.schema_migrations ("
        "version text PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now()"
        ")"
    )
    connection.exec_driver_sql(_INITIAL_SCHEMA)
    connection.exec_driver_sql(
        "INSERT INTO public.schema_migrations (version) VALUES ('001_initial')"
    )


def downgrade() -> None:
    connection = op.get_bind()
    connection.exec_driver_sql("DROP SCHEMA IF EXISTS app CASCADE")
    connection.exec_driver_sql(
        "DELETE FROM public.schema_migrations WHERE version = '001_initial'"
    )
