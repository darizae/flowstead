"""Local forecast maintenance CLI (database-dependent).

Kept out of the pure ``forecast`` domain module so calculations stay free of
database concerns. Invoked via ``python -m flowstead_api.forecast`` or directly.
"""

from __future__ import annotations

from ..database import Database
from ..forecast import SYNTHETIC_BACKTEST_NOTICE, backtest


def main() -> int:
    """Run the local build for every approved Plant; no network or scheduler is used."""
    database = Database()
    print(f"backtest_notice={SYNTHETIC_BACKTEST_NOTICE}")
    for plant_id in sorted(database.public_plant_ids):
        result = database.build_forecast(plant_id)
        state = "available" if result.available else f"unavailable:{result.unavailable_reason}"
        issued_at = result.issued_at_utc.isoformat() if result.issued_at_utc is not None else "none"
        receipt = backtest(database.flow_observations(plant_id))
        print(
            f"{plant_id} {state} issued_at={issued_at} "
            f"mae_gal_h={receipt.model_mae_gal_h} "
            f"eligible={receipt.model_eligible_count} "
            f"persistence_mae_gal_h={receipt.persistence_mae_gal_h} "
            f"persistence_eligible={receipt.persistence_eligible_count}"
        )
    return 0
