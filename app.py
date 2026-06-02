from flask import Flask, jsonify, request
import os
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

try:
    from flasgger import Swagger
except ImportError:  # Keeps app runnable even if Swagger is not installed yet.
    Swagger = None

load_dotenv()

app = Flask(__name__)

app.config["SWAGGER"] = {
    "title": "MetroWorks WFM API",
    "uiversion": 3,
}

if Swagger:
    Swagger(app)

DB_SERVER = os.getenv("DB_SERVER", "localhost")
DB_NAME = os.getenv("DB_NAME", "wfm_project")
DB_DRIVER = os.getenv("DB_DRIVER", "ODBC Driver 17 for SQL Server")

engine = create_engine(
    f"mssql+pyodbc://{DB_SERVER}/{DB_NAME}"
    f"?driver={DB_DRIVER.replace(' ', '+')}"
    "&trusted_connection=yes"
    "&TrustServerCertificate=yes"
)


# -------------------------
# Helpers
# -------------------------

def clean_df(df: pd.DataFrame) -> pd.DataFrame:
    """Convert NaN/NaT values to None so Flask can serialize clean JSON."""
    return df.where(pd.notnull(df), None)


def run_query(query: str, params: dict | None = None) -> pd.DataFrame:
    return clean_df(pd.read_sql(text(query), engine, params=params or {}))


def to_json(query: str, params: dict | None = None):
    df = run_query(query, params)
    return jsonify(df.to_dict(orient="records"))


def to_paginated_json(
    data_query: str,
    count_query: str,
    params: dict | None = None,
    default_limit: int = 100,
    max_limit: int = 1000,
):
    limit, offset = get_pagination(default_limit=default_limit, max_limit=max_limit)
    query_params = params.copy() if params else {}
    query_params.update({"limit": limit, "offset": offset})

    data = run_query(data_query, query_params).to_dict(orient="records")
    count_df = run_query(count_query, query_params)
    total_records = int(count_df.iloc[0, 0]) if not count_df.empty else 0

    return jsonify({
        "total_records": total_records,
        "limit": limit,
        "offset": offset,
        "returned_records": len(data),
        "data": data,
    })


def get_pagination(default_limit: int = 100, max_limit: int = 1000):
    """Validated pagination so users cannot request the entire database at once."""
    try:
        limit = int(request.args.get("limit", default_limit))
        offset = int(request.args.get("offset", 0))
    except ValueError:
        limit, offset = default_limit, 0

    limit = max(1, min(limit, max_limit))
    offset = max(0, offset)
    return limit, offset


def single_record_or_404(query: str, params: dict):
    df = run_query(query, params)
    if df.empty:
        return jsonify({"error": "Record not found"}), 404
    return jsonify(df.iloc[0].to_dict())


# -------------------------
# Root / Health
# -------------------------

@app.route("/", methods=["GET"])
def index():
    """MetroWorks API index.
    ---
    responses:
      200:
        description: API index with available endpoints.
    """
    return jsonify({
        "api": "MetroWorks WFM API",
        "version": "2.1",
        "description": "Synthetic workforce-management API backed by SQL Server.",
        "docs": "/apidocs" if Swagger else "Install flasgger and restart to enable /apidocs",
        "health": "/health",
        "operational_endpoints": [
            "/agents",
            "/managers",
            "/cmdb",
            "/tickets?limit=100&offset=0",
            "/tickets/INC0000001",
            "/tickets/search?category=VPN%20Issue&limit=100&offset=0",
            "/contact_logs?limit=100&offset=0",
            "/surveys?limit=100&offset=0",
            "/transfers?limit=100&offset=0",
            "/outages",
            "/schedules?limit=100&offset=0",
        ],
        "kpi_endpoints": [
            "/kpi/summary",
            "/kpi/sla",
            "/kpi/csat",
            "/kpi/fcr",
            "/kpi/volume?grain=month",
        ],
    })


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint.
    ---
    responses:
      200:
        description: API and database health status.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return jsonify({"status": "healthy", "database": "connected"})
    except Exception as exc:
        return jsonify({"status": "unhealthy", "database": "disconnected", "error": str(exc)}), 500


# -------------------------
# Operational Endpoints
# -------------------------

@app.route("/agents", methods=["GET"])
def get_agents():
    return to_json("SELECT * FROM dbo.Agents ORDER BY technician_id")


@app.route("/managers", methods=["GET"])
def get_managers():
    return to_json("SELECT * FROM dbo.Managers ORDER BY manager_id")


@app.route("/cmdb", methods=["GET"])
def get_cmdb():
    return to_json("SELECT * FROM dbo.CMDB ORDER BY cmdb_item")


@app.route("/tickets", methods=["GET"])
def get_tickets():
    data_query = """
        SELECT *
        FROM dbo.Tickets
        ORDER BY opened_datetime DESC
        OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY;
    """
    count_query = "SELECT COUNT(*) AS total_records FROM dbo.Tickets;"
    return to_paginated_json(data_query, count_query)


@app.route("/tickets/<ticket_id>", methods=["GET"])
def get_ticket_by_id(ticket_id):
    query = """
        SELECT *
        FROM dbo.Tickets
        WHERE ticket_id = :ticket_id;
    """
    return single_record_or_404(query, {"ticket_id": ticket_id})


@app.route("/tickets/search", methods=["GET"])
def search_tickets():
    """Search tickets by common filter fields.

    Supported query params:
    - category
    - priority
    - source_channel
    - technician_id: searches opened/assigned/resolved agent fields
    - cmdb_item
    - escalated: 0 or 1
    - keyword: searches short_description, description, and close_notes
    - limit
    - offset
    """
    filters = []
    params = {}

    exact_fields = {
        "category": "category",
        "priority": "priority",
        "source_channel": "source_channel",
        "cmdb_item": "cmdb_item",
    }

    for arg_name, column_name in exact_fields.items():
        value = request.args.get(arg_name)
        if value:
            filters.append(f"{column_name} = :{arg_name}")
            params[arg_name] = value

    escalated = request.args.get("escalated")
    if escalated in {"0", "1"}:
        filters.append("escalated = :escalated")
        params["escalated"] = int(escalated)

    technician_id = request.args.get("technician_id")
    if technician_id:
        filters.append("""
            (
                opened_by_agent_id = :technician_id
                OR assigned_to_agent_id = :technician_id
                OR resolved_by_agent_id = :technician_id
            )
        """)
        params["technician_id"] = technician_id

    keyword = request.args.get("keyword")
    if keyword:
        filters.append("""
            (
                short_description LIKE :keyword
                OR description LIKE :keyword
                OR close_notes LIKE :keyword
            )
        """)
        params["keyword"] = f"%{keyword}%"

    where_clause = "WHERE " + " AND ".join(filters) if filters else ""

    data_query = f"""
        SELECT *
        FROM dbo.Tickets
        {where_clause}
        ORDER BY opened_datetime DESC
        OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY;
    """

    count_query = f"""
        SELECT COUNT(*) AS total_records
        FROM dbo.Tickets
        {where_clause};
    """

    return to_paginated_json(data_query, count_query, params)


@app.route("/contact_logs", methods=["GET"])
def get_contact_logs():
    data_query = """
        SELECT *
        FROM dbo.Contact_Logs
        ORDER BY contact_datetime DESC
        OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY;
    """
    count_query = "SELECT COUNT(*) AS total_records FROM dbo.Contact_Logs;"
    return to_paginated_json(data_query, count_query)


@app.route("/surveys", methods=["GET"])
def get_surveys():
    data_query = """
        SELECT *
        FROM dbo.Surveys
        ORDER BY survey_datetime DESC
        OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY;
    """
    count_query = "SELECT COUNT(*) AS total_records FROM dbo.Surveys;"
    return to_paginated_json(data_query, count_query)


@app.route("/transfers", methods=["GET"])
def get_transfers():
    data_query = """
        SELECT *
        FROM dbo.Ticket_Transfers
        ORDER BY transfer_datetime DESC
        OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY;
    """
    count_query = "SELECT COUNT(*) AS total_records FROM dbo.Ticket_Transfers;"
    return to_paginated_json(data_query, count_query)


@app.route("/outages", methods=["GET"])
def get_outages():
    return to_json("SELECT * FROM dbo.Outages ORDER BY outage_start DESC")


@app.route("/schedules", methods=["GET"])
def get_schedules():
    data_query = """
        SELECT *
        FROM dbo.Schedules
        ORDER BY work_date DESC, agent_id
        OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY;
    """
    count_query = "SELECT COUNT(*) AS total_records FROM dbo.Schedules;"
    return to_paginated_json(data_query, count_query)


# -------------------------
# KPI Endpoints
# -------------------------

@app.route("/kpi/sla", methods=["GET"])
def kpi_sla():
    query = """
        SELECT
            CAST(ROUND(100.0 * AVG(CAST(sla_met AS FLOAT)), 2) AS DECIMAL(10,2)) AS sla_percent,
            COUNT(*) AS ticket_count
        FROM dbo.Tickets;
    """
    return to_json(query)


@app.route("/kpi/csat", methods=["GET"])
def kpi_csat():
    query = """
        SELECT
            CAST(ROUND(AVG(overall_experience_score), 2) AS DECIMAL(10,2)) AS avg_csat_score,
            CAST(ROUND(AVG(overall_experience_score) * 20, 2) AS DECIMAL(10,2)) AS csat_percent,
            COUNT(*) AS survey_count
        FROM dbo.Surveys;
    """
    return to_json(query)


@app.route("/kpi/fcr", methods=["GET"])
def kpi_fcr():
    query = """
        SELECT
            CAST(ROUND(100.0 * AVG(CAST(resolved_on_first_contact AS FLOAT)), 2) AS DECIMAL(10,2)) AS fcr_percent,
            COUNT(*) AS eligible_contacts
        FROM dbo.Contact_Logs
        WHERE abandoned_flag = 0;
    """
    return to_json(query)


@app.route("/kpi/volume", methods=["GET"])
def kpi_volume():
    grain = request.args.get("grain", "month").lower()

    if grain == "day":
        date_expr = "CAST(opened_datetime AS DATE)"
    elif grain == "year":
        date_expr = "DATEFROMPARTS(YEAR(opened_datetime), 1, 1)"
    else:
        date_expr = "DATEFROMPARTS(YEAR(opened_datetime), MONTH(opened_datetime), 1)"

    query = f"""
        SELECT
            {date_expr} AS period_start,
            COUNT(*) AS opened_tickets,
            SUM(CASE WHEN escalated = 1 THEN 1 ELSE 0 END) AS escalated_tickets,
            SUM(CASE WHEN sla_breached = 1 THEN 1 ELSE 0 END) AS sla_breaches
        FROM dbo.Tickets
        GROUP BY {date_expr}
        ORDER BY period_start;
    """
    return to_json(query)


@app.route("/kpi/summary", methods=["GET"])
def kpi_summary():
    query = """
        SELECT
            (SELECT COUNT(*) FROM dbo.Tickets) AS ticket_count,
            (SELECT COUNT(*) FROM dbo.Contact_Logs) AS contact_count,
            (SELECT COUNT(*) FROM dbo.Surveys) AS survey_count,
            (SELECT CAST(ROUND(100.0 * AVG(CAST(sla_met AS FLOAT)), 2) AS DECIMAL(10,2)) FROM dbo.Tickets) AS sla_percent,
            (SELECT CAST(ROUND(100.0 * AVG(CAST(resolved_on_first_contact AS FLOAT)), 2) AS DECIMAL(10,2)) FROM dbo.Contact_Logs WHERE abandoned_flag = 0) AS fcr_percent,
            (SELECT CAST(ROUND(AVG(overall_experience_score) * 20, 2) AS DECIMAL(10,2)) FROM dbo.Surveys) AS csat_percent;
    """
    return to_json(query)


if __name__ == "__main__":
    app.run(debug=True)
