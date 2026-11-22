"""Compatibility imports for legacy unit tests; implementation is in scripts/."""

from scripts.db_lifecycle import (  # noqa: F401
    COMPOSE_FILE,
    PROJECT_ROOT,
    DatabaseLifecycleError,
    _check_url,
    ensure_database,
    main,
)

if __name__ == "__main__":
    raise SystemExit(main())
