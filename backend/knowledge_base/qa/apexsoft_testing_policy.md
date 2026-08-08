# ApexSoft Solutions - Testing and QA Policy

Quality assurance is integral to our SDLC process. All developers and QA engineers must enforce these standards:

## 1. Test Framework
*   We strictly use **`pytest`** for all Python test suites.
*   Test files must be located inside the `tests/` subfolder, prefixed with `test_` (e.g. `tests/test_routes.py`).
*   Test functions must start with `test_` (e.g. `def test_endpoint_success()`).

## 2. Test Structure
*   Always test edge cases, database failures, and validation errors, not just successful paths.
*   Use mock interfaces or separate databases (e.g. temporary SQLite files or in-memory sqlite databases `sqlite:///:memory:`) to ensure unit tests are isolated and do not modify production files.
*   Aim for at least 80% code coverage.
