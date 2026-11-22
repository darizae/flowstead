"""Explicit authorization scopes used by application queries."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PublicAccess:
    """Anonymous access to the bounded public demonstration set."""


@dataclass(frozen=True, slots=True)
class OperatorAccess:
    subject_id: str


AccessScope = PublicAccess | OperatorAccess
