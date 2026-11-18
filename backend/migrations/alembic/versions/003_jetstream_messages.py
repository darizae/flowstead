"""Add the application-owned transactional messaging boundary.

Revision ID: 003_jetstream_messages
Revises: 002_forecast_metadata
"""

from alembic import op

revision = "003_jetstream_messages"
down_revision = "002_forecast_metadata"
branch_labels = None
depends_on = None


_UPGRADE = """
CREATE TABLE app.message_outbox (
    event_id uuid PRIMARY KEY,
    subject text NOT NULL CHECK (subject IN (
        'flowstead.v1.ingest.completed',
        'flowstead.v1.forecast.requested',
        'flowstead.v1.forecast.completed',
        'flowstead.v1.forecast.failed'
    )),
    correlation_id uuid NOT NULL,
    plant_id text NOT NULL REFERENCES app.plants (plant_id),
    payload jsonb NOT NULL,
    occurred_at_utc timestamptz NOT NULL,
    status text NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'published')),
    publish_attempts smallint NOT NULL DEFAULT 0
        CHECK (publish_attempts BETWEEN 0 AND 100),
    available_at timestamptz NOT NULL DEFAULT now(),
    published_at timestamptz,
    jetstream_sequence bigint,
    last_error varchar(512),
    created_at timestamptz NOT NULL DEFAULT now(),
    CHECK ((status = 'pending' AND published_at IS NULL)
        OR (status = 'published' AND published_at IS NOT NULL))
);
CREATE INDEX message_outbox_pending_idx
    ON app.message_outbox (available_at, created_at)
    WHERE status = 'pending';
CREATE INDEX message_outbox_correlation_idx
    ON app.message_outbox (correlation_id, created_at);

CREATE TABLE app.message_inbox (
    event_id uuid PRIMARY KEY,
    subject text NOT NULL,
    correlation_id uuid NOT NULL,
    plant_id text NOT NULL REFERENCES app.plants (plant_id),
    delivery_count smallint NOT NULL CHECK (delivery_count BETWEEN 1 AND 100),
    status text NOT NULL CHECK (status IN ('completed', 'failed')),
    diagnostic varchar(512),
    received_at timestamptz NOT NULL DEFAULT now(),
    processed_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX message_inbox_correlation_idx
    ON app.message_inbox (correlation_id, processed_at);

CREATE TABLE app.message_failures (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    stream_sequence bigint,
    subject text NOT NULL,
    event_id uuid,
    payload_sha256 char(64) NOT NULL,
    delivery_count smallint NOT NULL CHECK (delivery_count BETWEEN 1 AND 100),
    diagnostic varchar(512) NOT NULL,
    terminal boolean NOT NULL,
    recorded_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (stream_sequence, payload_sha256)
);

CREATE TABLE app.forecast_jobs (
    request_event_id uuid PRIMARY KEY,
    correlation_id uuid NOT NULL UNIQUE,
    plant_id text NOT NULL REFERENCES app.plants (plant_id),
    requested_by text NOT NULL CHECK (requested_by <> ''),
    source_sha char(40) NOT NULL CHECK (source_sha ~ '^[0-9a-f]{40}$'),
    status text NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued', 'processing', 'completed', 'failed')),
    requested_at timestamptz NOT NULL,
    started_at timestamptz,
    completed_at timestamptz,
    result_event_id uuid,
    diagnostic varchar(512),
    CHECK ((status IN ('queued', 'processing') AND completed_at IS NULL)
        OR (status IN ('completed', 'failed') AND completed_at IS NOT NULL))
);
CREATE INDEX forecast_jobs_plant_requested_idx
    ON app.forecast_jobs (plant_id, requested_at DESC);
"""


def upgrade() -> None:
    connection = op.get_bind()
    connection.exec_driver_sql(_UPGRADE)
    connection.exec_driver_sql(
        "INSERT INTO public.schema_migrations (version) VALUES ('003_jetstream_messages')"
    )


def downgrade() -> None:
    connection = op.get_bind()
    connection.exec_driver_sql("DROP TABLE IF EXISTS app.forecast_jobs")
    connection.exec_driver_sql("DROP TABLE IF EXISTS app.message_failures")
    connection.exec_driver_sql("DROP TABLE IF EXISTS app.message_inbox")
    connection.exec_driver_sql("DROP TABLE IF EXISTS app.message_outbox")
    connection.exec_driver_sql(
        "DELETE FROM public.schema_migrations WHERE version = '003_jetstream_messages'"
    )
