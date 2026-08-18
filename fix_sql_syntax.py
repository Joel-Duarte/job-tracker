with open("backend/app/services/analytics.py", "r") as f:
    content = f.read()

content = content.replace(
    "date_trunc('week', :start_date::timestamp)",
    "date_trunc('week', CAST(:start_date AS TIMESTAMP))"
)
content = content.replace(
    "date_trunc('week', :end_date::timestamp)",
    "date_trunc('week', CAST(:end_date AS TIMESTAMP))"
)
content = content.replace(
    "'1 week'::interval",
    "INTERVAL '1 week'"
)

with open("backend/app/services/analytics.py", "w") as f:
    f.write(content)
