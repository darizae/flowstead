"""Explicit and immutable public/operator Plant authorization contexts.

Private reads must carry a verified operator subject and remain scoped in SQL.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PublicAccess:
    """Public demo access, limited by allowlist and public_demo flag."""


@dataclass(frozen=True, slots=True)
class OperatorAccess:
    """Private access, with Plant grants checked in PostgreSQL."""

    subject_id: str


AccessScope = PublicAccess | OperatorAccess
PUBLIC_ACCESS = PublicAccess()
