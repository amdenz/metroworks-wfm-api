import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

random.seed(42)
np.random.seed(42)

# =========================
# CONFIG
# =========================

TOTAL_TICKETS = 150_000
TOTAL_SURVEYS = 30_000

START_DATE = datetime(2023, 1, 1)
END_DATE = datetime(2026, 5, 22)

load_dotenv()

DATABASE_NAME = os.getenv("DB_NAME", "wfm_project")
DB_SERVER = os.getenv("DB_SERVER", "localhost")
DB_DRIVER = os.getenv("DB_DRIVER", "ODBC Driver 17 for SQL Server")

engine = create_engine(
    f"mssql+pyodbc://{DB_SERVER}/{DATABASE_NAME}"
    f"?driver={DB_DRIVER.replace(' ', '+')}"
    "&trusted_connection=yes"
    "&TrustServerCertificate=yes"
)

def random_datetime(start, end):
    seconds = int((end - start).total_seconds())
    return start + timedelta(seconds=random.randint(0, seconds))

def weighted_choice(values, probs):
    return np.random.choice(values, p=probs)


def ticket_text(category, cmdb_item, priority, escalated):
    templates = {
        "Password Reset": [
            ("User requested Windows password reset", "User unable to sign in after password expiration. Verified identity and reset Windows/AD password.", "Password reset completed and user confirmed successful login."),
            ("Password expired after weekend", "Caller reported expired credentials and failed login attempts at workstation.", "Reset credentials in Active Directory and advised user to update cached sign-in."),
        ],
        "Account Unlock": [
            ("Windows account locked", "User locked out after multiple failed sign-in attempts. MFA verification completed.", "Unlocked account and confirmed access restored."),
            ("AD account unlock request", "User cannot access workstation or business applications due to locked Active Directory account.", "Account unlocked and login validated with user."),
        ],
        "VPN Issue": [
            ("VPN connection failure", "User unable to connect to VPN after MFA approval. Client returned timeout after credential validation.", "Cleared stale session, refreshed VPN profile, and confirmed connection."),
            ("Remote access VPN error", "VPN client failed during authentication while user was working remotely.", "Resolved by reauthenticating profile and validating MFA prompt."),
        ],
        "Email Issue": [
            ("Outlook not syncing", "User reported missing recent email and delayed mailbox sync in Outlook desktop client.", "Rebuilt Outlook profile and confirmed mailbox sync completed."),
            ("Email delivery delay", "User reported expected messages not appearing in inbox.", "Checked mailbox status and confirmed mail flow restored."),
        ],
        "Printer Issue": [
            ("Printer unavailable", "User unable to print to assigned department printer. Queue showed stuck jobs.", "Cleared print queue, re-added printer, and test page printed successfully."),
            ("Printer mapping request", "User needed access to nearby network printer after workstation replacement.", "Mapped printer and confirmed successful test print."),
        ],
        "Application Issue": [
            ("Business application error", "User received application error while opening core business application.", "Cleared cache and confirmed application launched successfully."),
            ("Application access failure", "User could not access application module required for daily workflow.", "Validated permissions and restored access."),
        ],
        "Device Issue": [
            ("Laptop performance issue", "User reported slow laptop performance and repeated freezing during login.", "Performed basic troubleshooting and escalated if hardware review was required."),
            ("Workstation hardware issue", "Endpoint reported docking or peripheral problem impacting user productivity.", "Updated drivers and confirmed workstation stable."),
        ],
        "Network Issue": [
            ("Network connectivity issue", "User reported intermittent connectivity and failed access to internal resources.", "Validated network path and confirmed connectivity restored."),
            ("Unable to reach internal site", "User could not reach internal application due to suspected network issue.", "Flushed DNS and confirmed site access."),
        ],
        "Access Issue": [
            ("Access request", "User requested access to shared resource or security group for business function.", "Validated approval path and completed access update."),
            ("Permission denied error", "User received permission denied message when accessing required resource.", "Adjusted group membership and confirmed access."),
        ],
        "Software Issue": [
            ("Software install request", "User requested approved software installation for workstation.", "Installed approved package and confirmed application launched."),
            ("Software update failure", "Application update failed and user could not continue workflow.", "Repaired installation and confirmed software opened correctly."),
        ],
    }
    short_description, description, close_notes = random.choice(templates.get(category, templates["Application Issue"]))
    if escalated == 1:
        close_notes += " Escalated to Tier 2 for advanced troubleshooting."
    if priority in ["High", "Critical"]:
        description += f" Priority set to {priority} due to business impact."
    return short_description, description, close_notes

# =========================
# MANAGERS
# =========================

managers = pd.DataFrame([
    ["MGR-T1-001", "Rebecca Lawson", "Tier 1 Service Desk", "Tier 1"],
    ["MGR-T2-001", "Anthony Mercer", "Tier 2 Incident & Requests", "Tier 2"],
    ["MGR-T2-002", "Sonia Patel", "Tier 2 Field Services", "Tier 2"],
    ["MGR-T2-003", "David Romero", "Tier 2 Builds", "Tier 2"],
], columns=["manager_id", "manager_name", "department", "tier"])

# =========================
# AGENTS
# =========================

tier1_names = [
    "Marcus Reed","Elena Torres","Jordan Hayes","Sofia Patel","Daniel Brooks",
    "Maya Thompson","Adrian Foster","Chloe Bennett","Luis Martinez","Hannah Price",
    "Ethan Walker","Isabella Cruz","Ryan Mitchell","Zoe Richardson","Caleb Murphy",
    "Natalie Rivera","Xavier Collins","Leah Simmons","Tyler Jenkins","Ava Morales",
    "Brandon Cooper","Mia Peterson","Nathan Bailey","Grace Ramirez","Justin Ward",
    "Emily Rogers","Cameron Diaz","Olivia Sanders","Kevin Bryant","Sarah Nguyen",
    "Jason Bell","Victoria Perry","Eric Coleman","Madison Flores","Aaron Kelly",
    "Jasmine Brooks","Dylan Cook","Vanessa Ortiz","Trevor Hughes","Paige Bennett"
]

tier2_names = [
    "Rachel Kim","Adrian Lewis","Luis Hernandez","Monica Alvarez","Derek Sullivan",
    "Priya Shah","Jonathan Miles","Erica Daniels","Gabriel Flores","Nicole Bennett",
    "Steven Carter","Allison Reed","Marcus Jennings","Tiffany Nguyen","Brandon Ellis",
    "Christina Lopez","Victor Ramirez","Samuel Price","Courtney Hayes","Nicholas Foster"
]

agents_data = []

for i, name in enumerate(tier1_names, start=1):
    agents_data.append([
        f"T1-{i:03d}", name, "Tier 1", "Tier 1 Service Desk",
        "Service Desk Analyst", "MGR-T1-001"
    ])

for i, name in enumerate(tier2_names, start=1):
    if i <= 12:
        dept, manager, role = "Tier 2 Incident & Requests", "MGR-T2-001", "Incident & Requests"
    elif i <= 17:
        dept, manager, role = "Tier 2 Field Services", "MGR-T2-002", "Field Services"
    else:
        dept, manager, role = "Tier 2 Builds", "MGR-T2-003", "Builds"

    agents_data.append([
        f"T2-{i:03d}", name, "Tier 2", dept, role, manager
    ])

agents = pd.DataFrame(
    agents_data,
    columns=["technician_id", "technician_name", "tier", "department", "role", "manager_id"]
)

tier1_agents = agents[agents["tier"] == "Tier 1"]["technician_id"].tolist()
tier2_agents = agents[agents["tier"] == "Tier 2"]["technician_id"].tolist()
all_agents = agents["technician_id"].tolist()

# =========================
# CMDB
# =========================

cmdb = pd.DataFrame([
    ["Active Directory", "Identity Services", "Critical"],
    ["MFA", "Identity Services", "Critical"],
    ["VPN", "Network Services", "High"],
    ["Email", "Messaging Team", "High"],
    ["Printer", "Endpoint Services", "Medium"],
    ["Laptop", "Endpoint Services", "Medium"],
    ["Desktop", "Endpoint Services", "Medium"],
    ["Network", "Network Services", "Critical"],
    ["Business Application", "Application Support", "Critical"],
    ["Mobile Device", "Endpoint Services", "Low"],
], columns=["cmdb_item", "application_owner", "business_criticality"])

# =========================
# TICKETS
# =========================

categories = [
    "Password Reset",
    "Account Unlock",
    "VPN Issue",
    "Email Issue",
    "Printer Issue",
    "Application Issue",
    "Device Issue",
    "Network Issue",
    "Access Issue",
    "Software Issue"
]

ticket_rows = []
transfer_rows = []

for i in range(1, TOTAL_TICKETS + 1):
    ticket_id = f"INC{i:07d}"
    opened_datetime = random_datetime(START_DATE, END_DATE)

    source_channel = weighted_choice(
        ["Call", "Chat", "Self-Service"],
        [0.60, 0.25, 0.15]
    )

    opened_by_agent_id = random.choice(tier1_agents)

    category = random.choice(categories)

    if category in ["Password Reset", "Account Unlock"]:
        cmdb_item = random.choice(["Active Directory", "MFA"])
    else:
        cmdb_item = random.choice(cmdb["cmdb_item"].tolist())

    priority = weighted_choice(
        ["Low", "Medium", "High", "Critical"],
        [0.25, 0.55, 0.17, 0.03]
    )

    escalated = int(weighted_choice([0, 1], [0.82, 0.18]))

    if escalated == 1:
        assigned_to_agent_id = random.choice(tier2_agents)
        resolved_by_agent_id = assigned_to_agent_id
    else:
        assigned_to_agent_id = opened_by_agent_id
        resolved_by_agent_id = opened_by_agent_id

    sla_target_hours = weighted_choice([4, 8, 24, 48], [0.10, 0.25, 0.50, 0.15])
    resolution_hours = float(np.random.gamma(shape=2.1, scale=6.8))

    if priority == "Critical":
        resolution_hours *= 0.75
    elif priority == "Low":
        resolution_hours *= 1.25

    if escalated == 1:
        resolution_hours *= 1.20

    resolved_datetime = opened_datetime + timedelta(hours=resolution_hours)

    sla_met = 1 if resolution_hours <= sla_target_hours else 0
    sla_breached = 0 if sla_met == 1 else 1

    reopened = int(weighted_choice([0, 1], [0.94, 0.06]))
    outage_related = int(weighted_choice([0, 1], [0.93, 0.07]))
    short_description, description, close_notes = ticket_text(category, cmdb_item, priority, escalated)

    ticket_rows.append([
        ticket_id,
        opened_datetime,
        resolved_datetime,
        "Incident",
        source_channel,
        "Tier 1",
        "Service Desk",
        opened_by_agent_id,
        assigned_to_agent_id,
        resolved_by_agent_id,
        priority,
        category,
        cmdb_item,
        sla_target_hours,
        round(resolution_hours, 2),
        sla_met,
        sla_breached,
        escalated,
        reopened,
        outage_related,
        short_description,
        description,
        close_notes
    ])

    if escalated == 1:
        transfer_rows.append([
            f"TR{len(transfer_rows)+1:08d}",
            ticket_id,
            opened_by_agent_id,
            assigned_to_agent_id,
            opened_datetime + timedelta(minutes=random.randint(10, 240)),
            random.choice([
                "Escalated to Tier 2",
                "Specialist Required",
                "Field Support Required",
                "Incorrect Assignment",
                "Advanced Troubleshooting Required"
            ])
        ])

tickets = pd.DataFrame(ticket_rows, columns=[
    "ticket_id",
    "opened_datetime",
    "resolved_datetime",
    "ticket_type",
    "source_channel",
    "tier",
    "assignment_group",
    "opened_by_agent_id",
    "assigned_to_agent_id",
    "resolved_by_agent_id",
    "priority",
    "category",
    "cmdb_item",
    "sla_target_hours",
    "resolution_hours",
    "sla_met",
    "sla_breached",
    "escalated",
    "reopened",
    "outage_related",
    "short_description",
    "description",
    "close_notes"
])

ticket_transfers = pd.DataFrame(transfer_rows, columns=[
    "transfer_id",
    "ticket_id",
    "from_agent_id",
    "to_agent_id",
    "transfer_datetime",
    "transfer_reason"
])

# =========================
# CONTACT LOGS
# Call + Chat only
# Contact handled by opened_by for normal tickets, assigned/resolved agent for escalated tickets
# =========================

contact_source = tickets[tickets["source_channel"].isin(["Call", "Chat"])]

contact_rows = []

for i, row in enumerate(contact_source.itertuples(), start=1):
    channel = row.source_channel
    abandoned_flag = int(weighted_choice([0, 1], [0.96, 0.04]))

    agent_id = row.opened_by_agent_id

    if channel == "Call":
        asa_seconds = max(10, int(np.random.gamma(shape=2.2, scale=12)))
        base_aht = int(np.random.gamma(shape=3.0, scale=170))
    else:
        asa_seconds = max(8, int(np.random.gamma(shape=2.0, scale=8)))
        base_aht = int(np.random.gamma(shape=2.5, scale=120))

    if abandoned_flag == 1:
        aht_seconds = None
        seconds_to_abandon = max(10, int(np.random.gamma(shape=2.0, scale=22)))
        escalated_flag = 0
        escalated_after_15_min = 0
        resolved_on_first_contact = 0
    else:
        aht_seconds = max(45, base_aht)
        seconds_to_abandon = None
        escalated_flag = row.escalated
        escalated_after_15_min = 1 if row.escalated == 1 and aht_seconds >= 900 else 0
        resolved_on_first_contact = 0 if row.escalated == 1 else int(weighted_choice([1, 0], [0.85, 0.15]))

    contact_datetime = row.opened_datetime + timedelta(minutes=random.randint(1, 180))

    contact_rows.append([
        f"CT{i:08d}",
        row.ticket_id,
        agent_id,
        channel,
        contact_datetime,
        asa_seconds,
        aht_seconds,
        abandoned_flag,
        seconds_to_abandon,
        escalated_flag,
        escalated_after_15_min,
        resolved_on_first_contact
    ])

contact_logs = pd.DataFrame(contact_rows, columns=[
    "contact_id",
    "ticket_id",
    "agent_id",
    "channel",
    "contact_datetime",
    "asa_seconds",
    "aht_seconds",
    "abandoned_flag",
    "seconds_to_abandon",
    "escalated_flag",
    "escalated_after_15_min",
    "resolved_on_first_contact"
])

# =========================
# SURVEYS
# =========================

survey_sample = tickets.sample(n=TOTAL_SURVEYS, random_state=42)
survey_rows = []

for i, row in enumerate(survey_sample.itertuples(), start=1):
    base = np.random.normal(4.7, 0.35)
    scores = [round(min(5, max(1, np.random.normal(base, 0.25))), 1) for _ in range(5)]

    survey_rows.append([
        f"SV{i:08d}",
        row.ticket_id,
        row.resolved_by_agent_id,
        row.resolved_datetime + timedelta(days=random.randint(0, 5)),
        *scores
    ])

surveys = pd.DataFrame(survey_rows, columns=[
    "survey_id",
    "ticket_id",
    "agent_id",
    "survey_datetime",
    "courtesy_score",
    "technical_skill_score",
    "communication_score",
    "issue_resolved_score",
    "overall_experience_score"
])

# =========================
# OUTAGES
# =========================

outage_rows = []

for i in range(1, 26):
    start = random_datetime(START_DATE, END_DATE)
    cmdb_item = random.choice(["VPN", "Email", "Network", "Business Application", "Active Directory"])

    outage_rows.append([
        f"OUT{i:04d}",
        cmdb_item,
        start,
        start + timedelta(hours=random.randint(1, 12)),
        random.choice(["Low", "Medium", "High", "Critical"]),
        random.choice(["Vendor Issue", "Network Failure", "Application Failure", "Authentication Failure"])
    ])

outages = pd.DataFrame(outage_rows, columns=[
    "outage_id",
    "cmdb_item",
    "outage_start",
    "outage_end",
    "impact_level",
    "root_cause"
])

# =========================
# SCHEDULES
# =========================

schedule_rows = []
work_dates = pd.date_range(START_DATE, END_DATE, freq="B")

for agent in all_agents:
    selected_dates = np.random.choice(work_dates, size=min(500, len(work_dates)), replace=False)

    for work_date in selected_dates:
        scheduled_start = pd.Timestamp(work_date) + pd.Timedelta(hours=8)
        scheduled_end = scheduled_start + pd.Timedelta(hours=8)

        late_minutes = int(max(0, np.random.normal(3, 8)))
        absence = int(weighted_choice([0, 1], [0.97, 0.03]))

        if absence == 1:
            actual_start = None
            actual_end = None
            adherence = 0
            late_flag = 0
        else:
            actual_start = scheduled_start + pd.Timedelta(minutes=late_minutes)
            actual_end = scheduled_end
            adherence = round(max(0.80, min(1.00, np.random.normal(0.94, 0.04))), 3)
            late_flag = 1 if late_minutes > 5 else 0

        schedule_rows.append([
            f"SCH{len(schedule_rows)+1:08d}",
            agent,
            pd.Timestamp(work_date).date(),
            scheduled_start,
            scheduled_end,
            actual_start,
            actual_end,
            late_minutes,
            absence,
            adherence,
            late_flag
        ])

schedules = pd.DataFrame(schedule_rows, columns=[
    "schedule_id",
    "agent_id",
    "work_date",
    "scheduled_start",
    "scheduled_end",
    "actual_start",
    "actual_end",
    "late_minutes",
    "absence",
    "adherence",
    "late_flag"
])

# =========================
# TARGETS
# =========================

targets = pd.DataFrame([
    ["CSAT", 4.7, "Average customer survey score target"],
    ["SLA Compliance", 0.95, "Target percent of tickets meeting SLA"],
    ["ASA Seconds", 60, "Target average speed of answer"],
    ["Abandon Rate", 0.05, "Target abandoned contact rate"],
], columns=["metric_name", "target_value", "description"])

# =========================
# DROP FOREIGN KEYS THEN TABLES
# =========================

drop_fk_sql = """
DECLARE @sql NVARCHAR(MAX) = N'';

SELECT @sql +=
    'ALTER TABLE ' + QUOTENAME(SCHEMA_NAME(t.schema_id)) + '.' + QUOTENAME(t.name) +
    ' DROP CONSTRAINT ' + QUOTENAME(fk.name) + ';' + CHAR(13)
FROM sys.foreign_keys fk
JOIN sys.tables t
    ON fk.parent_object_id = t.object_id;

EXEC sp_executesql @sql;
"""

drop_sql = """
IF OBJECT_ID('dbo.Ticket_Transfers', 'U') IS NOT NULL DROP TABLE dbo.Ticket_Transfers;
IF OBJECT_ID('dbo.Contact_Logs', 'U') IS NOT NULL DROP TABLE dbo.Contact_Logs;
IF OBJECT_ID('dbo.Surveys', 'U') IS NOT NULL DROP TABLE dbo.Surveys;
IF OBJECT_ID('dbo.Schedules', 'U') IS NOT NULL DROP TABLE dbo.Schedules;
IF OBJECT_ID('dbo.Outages', 'U') IS NOT NULL DROP TABLE dbo.Outages;
IF OBJECT_ID('dbo.Tickets', 'U') IS NOT NULL DROP TABLE dbo.Tickets;
IF OBJECT_ID('dbo.Agents', 'U') IS NOT NULL DROP TABLE dbo.Agents;
IF OBJECT_ID('dbo.Managers', 'U') IS NOT NULL DROP TABLE dbo.Managers;
IF OBJECT_ID('dbo.CMDB', 'U') IS NOT NULL DROP TABLE dbo.CMDB;
IF OBJECT_ID('dbo.Targets', 'U') IS NOT NULL DROP TABLE dbo.Targets;
"""

with engine.begin() as conn:
    conn.execute(text(drop_fk_sql))
    conn.execute(text(drop_sql))

# =========================
# LOAD TO SQL
# =========================

managers.to_sql("Managers", engine, schema="dbo", if_exists="replace", index=False)
agents.to_sql("Agents", engine, schema="dbo", if_exists="replace", index=False)
cmdb.to_sql("CMDB", engine, schema="dbo", if_exists="replace", index=False)
tickets.to_sql("Tickets", engine, schema="dbo", if_exists="replace", index=False)
contact_logs.to_sql("Contact_Logs", engine, schema="dbo", if_exists="replace", index=False)
surveys.to_sql("Surveys", engine, schema="dbo", if_exists="replace", index=False)
ticket_transfers.to_sql("Ticket_Transfers", engine, schema="dbo", if_exists="replace", index=False)
outages.to_sql("Outages", engine, schema="dbo", if_exists="replace", index=False)
schedules.to_sql("Schedules", engine, schema="dbo", if_exists="replace", index=False)
targets.to_sql("Targets", engine, schema="dbo", if_exists="replace", index=False)

# =========================
# PK / FK CONSTRAINTS
# =========================

constraint_sql = """
ALTER TABLE dbo.Managers ALTER COLUMN manager_id VARCHAR(20) NOT NULL;
ALTER TABLE dbo.Managers ADD CONSTRAINT PK_Managers PRIMARY KEY (manager_id);

ALTER TABLE dbo.Agents ALTER COLUMN technician_id VARCHAR(10) NOT NULL;
ALTER TABLE dbo.Agents ALTER COLUMN manager_id VARCHAR(20) NULL;
ALTER TABLE dbo.Agents ADD CONSTRAINT PK_Agents PRIMARY KEY (technician_id);
ALTER TABLE dbo.Agents ADD CONSTRAINT FK_Agents_Managers FOREIGN KEY (manager_id) REFERENCES dbo.Managers(manager_id);

ALTER TABLE dbo.CMDB ALTER COLUMN cmdb_item VARCHAR(100) NOT NULL;
ALTER TABLE dbo.CMDB ADD CONSTRAINT PK_CMDB PRIMARY KEY (cmdb_item);

ALTER TABLE dbo.Tickets ALTER COLUMN ticket_id VARCHAR(50) NOT NULL;
ALTER TABLE dbo.Tickets ALTER COLUMN opened_by_agent_id VARCHAR(10) NULL;
ALTER TABLE dbo.Tickets ALTER COLUMN assigned_to_agent_id VARCHAR(10) NULL;
ALTER TABLE dbo.Tickets ALTER COLUMN resolved_by_agent_id VARCHAR(10) NULL;
ALTER TABLE dbo.Tickets ALTER COLUMN cmdb_item VARCHAR(100) NULL;
ALTER TABLE dbo.Tickets ADD CONSTRAINT PK_Tickets PRIMARY KEY (ticket_id);
ALTER TABLE dbo.Tickets ADD CONSTRAINT FK_Tickets_OpenedBy FOREIGN KEY (opened_by_agent_id) REFERENCES dbo.Agents(technician_id);
ALTER TABLE dbo.Tickets ADD CONSTRAINT FK_Tickets_AssignedTo FOREIGN KEY (assigned_to_agent_id) REFERENCES dbo.Agents(technician_id);
ALTER TABLE dbo.Tickets ADD CONSTRAINT FK_Tickets_ResolvedBy FOREIGN KEY (resolved_by_agent_id) REFERENCES dbo.Agents(technician_id);
ALTER TABLE dbo.Tickets ADD CONSTRAINT FK_Tickets_CMDB FOREIGN KEY (cmdb_item) REFERENCES dbo.CMDB(cmdb_item);

ALTER TABLE dbo.Contact_Logs ALTER COLUMN contact_id VARCHAR(50) NOT NULL;
ALTER TABLE dbo.Contact_Logs ALTER COLUMN ticket_id VARCHAR(50) NOT NULL;
ALTER TABLE dbo.Contact_Logs ALTER COLUMN agent_id VARCHAR(10) NULL;
ALTER TABLE dbo.Contact_Logs ADD CONSTRAINT PK_Contact_Logs PRIMARY KEY (contact_id);
ALTER TABLE dbo.Contact_Logs ADD CONSTRAINT FK_ContactLogs_Tickets FOREIGN KEY (ticket_id) REFERENCES dbo.Tickets(ticket_id);
ALTER TABLE dbo.Contact_Logs ADD CONSTRAINT FK_ContactLogs_Agents FOREIGN KEY (agent_id) REFERENCES dbo.Agents(technician_id);

ALTER TABLE dbo.Surveys ALTER COLUMN survey_id VARCHAR(50) NOT NULL;
ALTER TABLE dbo.Surveys ALTER COLUMN ticket_id VARCHAR(50) NOT NULL;
ALTER TABLE dbo.Surveys ALTER COLUMN agent_id VARCHAR(10) NULL;
ALTER TABLE dbo.Surveys ADD CONSTRAINT PK_Surveys PRIMARY KEY (survey_id);
ALTER TABLE dbo.Surveys ADD CONSTRAINT FK_Surveys_Tickets FOREIGN KEY (ticket_id) REFERENCES dbo.Tickets(ticket_id);
ALTER TABLE dbo.Surveys ADD CONSTRAINT FK_Surveys_Agents FOREIGN KEY (agent_id) REFERENCES dbo.Agents(technician_id);

ALTER TABLE dbo.Ticket_Transfers ALTER COLUMN transfer_id VARCHAR(50) NOT NULL;
ALTER TABLE dbo.Ticket_Transfers ALTER COLUMN ticket_id VARCHAR(50) NOT NULL;
ALTER TABLE dbo.Ticket_Transfers ALTER COLUMN from_agent_id VARCHAR(10) NULL;
ALTER TABLE dbo.Ticket_Transfers ALTER COLUMN to_agent_id VARCHAR(10) NULL;
ALTER TABLE dbo.Ticket_Transfers ADD CONSTRAINT PK_Ticket_Transfers PRIMARY KEY (transfer_id);
ALTER TABLE dbo.Ticket_Transfers ADD CONSTRAINT FK_Transfers_Tickets FOREIGN KEY (ticket_id) REFERENCES dbo.Tickets(ticket_id);
ALTER TABLE dbo.Ticket_Transfers ADD CONSTRAINT FK_Transfers_FromAgent FOREIGN KEY (from_agent_id) REFERENCES dbo.Agents(technician_id);
ALTER TABLE dbo.Ticket_Transfers ADD CONSTRAINT FK_Transfers_ToAgent FOREIGN KEY (to_agent_id) REFERENCES dbo.Agents(technician_id);

ALTER TABLE dbo.Outages ALTER COLUMN outage_id VARCHAR(50) NOT NULL;
ALTER TABLE dbo.Outages ALTER COLUMN cmdb_item VARCHAR(100) NULL;
ALTER TABLE dbo.Outages ADD CONSTRAINT PK_Outages PRIMARY KEY (outage_id);
ALTER TABLE dbo.Outages ADD CONSTRAINT FK_Outages_CMDB FOREIGN KEY (cmdb_item) REFERENCES dbo.CMDB(cmdb_item);

ALTER TABLE dbo.Schedules ALTER COLUMN schedule_id VARCHAR(50) NOT NULL;
ALTER TABLE dbo.Schedules ALTER COLUMN agent_id VARCHAR(10) NOT NULL;
ALTER TABLE dbo.Schedules ADD CONSTRAINT PK_Schedules PRIMARY KEY (schedule_id);
ALTER TABLE dbo.Schedules ADD CONSTRAINT FK_Schedules_Agents FOREIGN KEY (agent_id) REFERENCES dbo.Agents(technician_id);
"""

with engine.begin() as conn:
    conn.execute(text(constraint_sql))



# =========================
# PERFORMANCE INDEXES
# =========================

index_sql = """
CREATE INDEX IX_Tickets_OpenedDate ON dbo.Tickets(opened_datetime DESC);
CREATE INDEX IX_Tickets_ResolvedAgent ON dbo.Tickets(resolved_by_agent_id);
CREATE INDEX IX_Tickets_CMDB ON dbo.Tickets(cmdb_item);
CREATE INDEX IX_ContactLogs_ContactDate ON dbo.Contact_Logs(contact_datetime DESC);
CREATE INDEX IX_ContactLogs_Agent ON dbo.Contact_Logs(agent_id);
CREATE INDEX IX_Surveys_Agent ON dbo.Surveys(agent_id);
CREATE INDEX IX_Schedules_WorkDate ON dbo.Schedules(work_date DESC);
"""

with engine.begin() as conn:
    conn.execute(text(index_sql))

# =========================
# EXCEL EXPORT
# =========================

excel_path = "metroworks_wfm_clean_v2.xlsx"

with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
    agents.to_excel(writer, sheet_name="Agents", index=False)
    managers.to_excel(writer, sheet_name="Managers", index=False)
    cmdb.to_excel(writer, sheet_name="CMDB", index=False)
    tickets.to_excel(writer, sheet_name="Tickets", index=False)
    contact_logs.to_excel(writer, sheet_name="Contact_Logs", index=False)
    surveys.to_excel(writer, sheet_name="Surveys", index=False)
    ticket_transfers.to_excel(writer, sheet_name="Ticket_Transfers", index=False)
    outages.to_excel(writer, sheet_name="Outages", index=False)
    schedules.to_excel(writer, sheet_name="Schedules", index=False)
    targets.to_excel(writer, sheet_name="Targets", index=False)

print("DONE")
print("Loaded into SQL database:", DATABASE_NAME)
print("Excel saved as:", excel_path)
print()
print("Tickets:", len(tickets))
print("Contact Logs:", len(contact_logs))
print("Surveys:", len(surveys))
print("Transfers:", len(ticket_transfers))
print("Schedules:", len(schedules))
print()
print("Ticket source split:")
print(tickets["source_channel"].value_counts())
print()
print("Resolved by tier:")
print(
    tickets.merge(
        agents[["technician_id", "tier"]],
        left_on="resolved_by_agent_id",
        right_on="technician_id",
        how="left"
    )["tier"].value_counts()
)
print()
print("Contact channel split:")
print(contact_logs["channel"].value_counts())
print()
print("Abandon rate:", round(contact_logs["abandoned_flag"].mean(), 4))