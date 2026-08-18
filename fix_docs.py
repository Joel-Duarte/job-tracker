with open("AGENTS.md", "r") as f:
    content = f.read()

# I don't see a specific section about analytics endpoints in AGENTS.md, maybe I can just append it or not modify it. The plan says "Update AGENTS.md to reflect new /activity endpoints." Let's append a note to the end of the file.
new_docs = """
### 5. Analytics Module & API
- The Analytics service (`/api/v1/analytics`) strictly separates Market Intelligence endpoints (`/overview`, `/work-model-breakdown`, `/funnel`) from Search Velocity & Activity endpoints (`/activity`, `/activity/history`).
- Activity analytics aggregate counts and bounded time ranges using `this_week`, `last_week`, `this_month`, `last_month`, or `custom` UTC boundaries natively in Postgres via SQLAlchemy.
"""
content += new_docs

with open("AGENTS.md", "w") as f:
    f.write(content)
