"""Add forecast provenance metadata.

Revision ID: 002_forecast_metadata
Revises: 001_initial
"""

from alembic import op


revision = "002_forecast_metadata"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    connection.exec_driver_sql(
        "ALTER TABLE app.forecast_issuances ADD COLUMN IF NOT EXISTS source_revision text"
    )
    connection.exec_driver_sql(
        "ALTER TABLE app.forecast_issuances ADD COLUMN IF NOT EXISTS physical_bound_rule text"
    )
    connection.exec_driver_sql(
        "INSERT INTO public.schema_migrations (version) VALUES ('002_forecast_metadata')"
    )


def downgrade() -> None:
    connection = op.get_bind()
    connection.exec_driver_sql(
        "ALTER TABLE app.forecast_issuances DROP COLUMN IF EXISTS physical_bound_rule"
    )
    connection.exec_driver_sql(
        "ALTER TABLE app.forecast_issuances DROP COLUMN IF EXISTS source_revision"
    )
    connection.exec_driver_sql(
        "DELETE FROM public.schema_migrations WHERE version = '002_forecast_metadata'"
    )
