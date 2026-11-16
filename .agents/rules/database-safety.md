# Database Safety Rules

- **NEVER run tests (`pytest`, `conftest.py`, or schema resets) against a running production or development database** (such as `job-tracker-postgresdb`, port `10556`, or database `postgres`). `conftest.py` drops and recreates all tables on `TEST_DATABASE_URL`.
- **Always use an isolated test database:**
  - Prefer **Tier 1 (Testcontainers)** (`uv run pytest` with no `TEST_DATABASE_URL`), which spins up a disposable `pgvector/pgvector:pg16` container automatically.
  - If an explicit `TEST_DATABASE_URL` is ever required, create and target a dedicated disposable database (e.g. `job_tracker_test`) — never `postgres`.
- **Production/Dev Inspection:** Only run read-only `SELECT` queries against `job-tracker-postgresdb`. Never execute `DROP`, `TRUNCATE`, `DELETE`, or `drop_all` on it.
