# MetroWorks WFM API — Portfolio Version

Synthetic workforce-management data engineering project using Python, SQL Server, and Flask.

## What this demonstrates

- Python data generation
- SQL Server loading with `pandas.to_sql`
- Primary keys, foreign keys, and indexes
- API endpoints with pagination metadata
- REST-style ticket lookup by ID
- Search/filter endpoint for operational ticket analysis
- KPI endpoints for SLA, CSAT, FCR, and ticket volume
- Realistic ticket text fields for keyword/NLP-style analysis
- Swagger API documentation through `/apidocs`
- Health check endpoint for basic API/database status

## Setup

```bash
pip install -r requirements.txt
```

Create a `.env` file:

```env
DB_SERVER=localhost
DB_NAME=wfm_project
DB_DRIVER=ODBC Driver 17 for SQL Server
```

Generate and load the database:

```bash
python generate_data.py
```

Run the API:

```bash
python app.py
```

Open:

```text
http://localhost:5000/
```

Swagger UI:

```text
http://localhost:5000/apidocs
```

Health check:

```text
http://localhost:5000/health
```

## Example endpoints

```text
/tickets?limit=100&offset=0
/tickets/INC0000001
/tickets/search?category=VPN%20Issue&limit=100&offset=0
/tickets/search?technician_id=T1-001&limit=100&offset=0
/tickets/search?keyword=MFA&limit=100&offset=0
/contact_logs?limit=100&offset=0
/schedules?limit=100&offset=0
/kpi/summary
/kpi/sla
/kpi/csat
/kpi/fcr
/kpi/volume?grain=month
```

## Example paginated response

```json
{
  "total_records": 150000,
  "limit": 100,
  "offset": 0,
  "returned_records": 100,
  "data": [
    {
      "ticket_id": "INC0000001",
      "category": "VPN Issue",
      "priority": "Medium",
      "source_channel": "Call"
    }
  ]
}
```

## Example KPI response

Endpoint:

```text
/kpi/summary
```

Example shape:

```json
[
  {
    "ticket_count": 150000,
    "contact_count": 127534,
    "survey_count": 30000,
    "sla_percent": 72.41,
    "fcr_percent": 69.85,
    "csat_percent": 93.77
  }
]
```

## Suggested portfolio wording

MetroWorks WFM API is a synthetic workforce-management data engineering project built with Python, SQL Server, and Flask. The project generates 150,000 realistic IT support tickets, contact logs, survey records, schedules, outages, and ticket transfers. It loads the data into SQL Server with relational constraints, performance indexes,. A Flask API exposes paginated operational records, record-level ticket lookup, searchable ticket filters, health checks, Swagger documentation, and KPI endpoints for SLA compliance, CSAT, first-contact resolution, and ticket volume trends.
