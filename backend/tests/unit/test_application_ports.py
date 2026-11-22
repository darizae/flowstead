"""Application ports must match the concrete persistence implementations.

This guards the refactor regression that shipped `application/ports`
Protocols whose signatures did not match the real repositories (and so were
never usable/wired). Each Protocol method is checked against the concrete
adapter method it must be satisfied by.
"""

from __future__ import annotations

import inspect

from flowstead_api.application.ports.repositories import (
    ForecastRepository as ForecastRepositoryPort,
)
from flowstead_api.application.ports.repositories import PlantRepository as PlantRepositoryPort
from flowstead_api.application.ports.unit_of_work import UnitOfWork as UnitOfWorkPort
from flowstead_api.infrastructure.persistence.forecast_repository import ForecastRepository
from flowstead_api.infrastructure.persistence.plant_repository import PlantRepository
from flowstead_api.infrastructure.persistence.unit_of_work import UnitOfWork

PORT_TO_CONCRETE = {
    PlantRepositoryPort: PlantRepository,
    ForecastRepositoryPort: ForecastRepository,
    UnitOfWorkPort: UnitOfWork,
}


def _params(signature: inspect.Signature) -> list[tuple[str, object]]:
    return [
        (name, parameter.kind) for name, parameter in signature.parameters.items() if name != "self"
    ]


def test_every_port_method_matches_its_concrete_adapter() -> None:
    for port, concrete in PORT_TO_CONCRETE.items():
        concrete_methods = {
            name
            for name, member in inspect.getmembers(concrete)
            if not name.startswith("_") and callable(member)
        }
        for name, member in inspect.getmembers(port):
            if name.startswith("_") or not callable(member):
                continue
            assert name in concrete_methods, f"{concrete.__name__} lacks port method {name}"
            assert _params(inspect.signature(port.__dict__[name])) == _params(
                inspect.signature(getattr(concrete, name))
            ), f"{concrete.__name__}.{name} does not match port {port.__name__}.{name} signature"


def test_unit_of_work_port_shape_matches_concrete() -> None:
    # The UoW port's members (connection + context-manager protocol) must exist
    # on the concrete adapter with compatible signatures.
    for name in ("__enter__", "__exit__"):
        assert hasattr(UnitOfWork, name)
        assert _params(inspect.signature(getattr(UnitOfWorkPort, name))) == _params(
            inspect.signature(getattr(UnitOfWork, name))
        )
    assert "connection" in UnitOfWorkPort.__annotations__
