Full Stack Developer Technical Exercise 

Drone Activity Map Dashboard 

Technology stack: Angular + Python |  

 

1.1. Objective 

Build a small full-stack application that ingests simulated drone telemetry data, processes it in a Python backend, and displays the processed data on a map in an Angular frontend. 

The goal of this exercise is to demonstrate backend API design, data pipeline/orchestration thinking, frontend-map integration, FE/BE communication, clean code structure, and basic testing. 

2.2. Scenario 

The system receives raw drone telemetry records from an input source. Each record represents a detected drone position at a specific time. The backend should validate, normalize, and store the data. The frontend should allow the user to view the drone locations on a map and filter them. 

Important note: The coordinates may be real map coordinates, but the drone activity itself should be simulated and must not represent real drone operations. 

Example drone record 

{ 

"drone_id": "DRONE-001", 

"drone_type": "Quadcopter", 

"operator_id": "OP-123", 

"latitude": 32.0853, 

"longitude": 34.7818, 

"altitude_m": 120, 

"speed_kmh": 45, 

"battery_percent": 76, 

"timestamp": "2026-06-28T10:30:00Z", 

"status": "active" 

} 

3.3. Backend Requirements - Python 

Recommended stack: FastAPI, SQLAlchemy, and PostgreSQL or SQLite. A simple pipeline runner is acceptable; Prefect, Celery, or background workers are optional bonuses. 

3.1 Data Pipeline 

Create a pipeline that reads raw drone records from one of the following sources: 

JSON file 

CSV file 

Mock external API 

Local input folder 

The pipeline should perform the following steps: 

4.Load raw drone records. 

5.Validate required fields and allowed values. 

6.Remove or skip invalid records. 

7.Normalize data where needed. 

8.Store valid records in the database. 

9.Save pipeline run status and processing counters. 

3.2 Pipeline Run Status 

Store a history of pipeline executions. Suggested fields: 

Field 

Description 

id 

Unique pipeline run identifier 

started_at 

Pipeline start time 

finished_at 

Pipeline finish time 

status 

started, completed, or failed 

total_records 

Number of records read from input 

valid_records 

Number of records inserted successfully 

invalid_records 

Number of records skipped due to validation errors 

error_message 

Failure details, if any 

3.3 Validation Rules 

drone_id must not be empty. 

latitude must be between -90 and 90. 

longitude must be between -180 and 180. 

altitude_m must be zero or positive. 

battery_percent must be between 0 and 100. 

timestamp must be a valid date/time value. 

status should be one of: active, landed, lost_signal. 

3.4 API Endpoints 

Expose REST APIs for the Angular frontend. Suggested endpoints: 

Method 

Endpoint 

Purpose 

POST 

/api/pipeline/run 

Trigger the data ingestion pipeline. 

GET 

/api/pipeline/runs 

Return recent pipeline execution history. 

GET 

/api/drones 

Return drone records, with optional filters. 

GET 

/api/drones/{id} 

Return a single drone record. 

GET 

/api/stats 

Optional: return summary statistics. 

The /api/drones endpoint should support filters such as: 

GET /api/drones?drone_type=Quadcopter 

GET /api/drones?status=active 

GET /api/drones?operator_id=OP-123 

GET /api/drones?min_battery=50 

GET /api/drones?from=2026-06-01&to=2026-06-28 

10.4. Frontend Requirements - Angular 

Recommended map library: Leaflet, MapLibre, or OpenLayers. 

4.1 Map Dashboard 

Create a main dashboard page that displays drone records on a map. Each drone should appear as a marker at its latitude/longitude. 

Clicking a marker should open a popup with the following details: 

Drone ID 

Drone type 

Operator ID 

Altitude 

Speed 

Battery percentage 

Status 

Last update timestamp 

4.2 Filters 

Add filters that call the backend API and refresh the map results: 

Drone type 

Status 

Operator ID 

Minimum battery percentage 

Date range 

4.3 Pipeline Control Panel 

Add a small UI section that allows the user to trigger the backend pipeline. 

Data Pipeline 

[Run Pipeline] 

After clicking Run Pipeline, the frontend should call POST /api/pipeline/run and then refresh the drone list and pipeline run table. 

Display recent pipeline runs in a table with date, status, valid records, and invalid records. 

11.5. Sample Input Data 

Use real map coordinates for visibility on the frontend map, but keep the drone records simulated. 

[ 

{ 

"drone_id": "DRONE-001", 

"drone_type": "Quadcopter", 

"operator_id": "OP-123", 

"latitude": 32.0853, 

"longitude": 34.7818, 

"altitude_m": 120, 

"speed_kmh": 45, 

"battery_percent": 76, 

"timestamp": "2026-06-28T10:30:00Z", 

"status": "active" 

}, 

{ 

"drone_id": "DRONE-002", 

"drone_type": "Fixed Wing", 

"operator_id": "OP-456", 

"latitude": 31.7683, 

"longitude": 35.2137, 

"altitude_m": 300, 

"speed_kmh": 90, 

"battery_percent": 42, 

"timestamp": "2026-06-28T10:35:00Z", 

"status": "active" 

}, 

{ 

"drone_id": "DRONE-003", 

"drone_type": "VTOL", 

"operator_id": "OP-789", 

"latitude": 32.7940, 

"longitude": 34.9896, 

"altitude_m": 80, 

"speed_kmh": 20, 

"battery_percent": 15, 

"timestamp": "2026-06-28T10:40:00Z", 

"status": "lost_signal" 

} 

] 

Invalid record example 

{ 

"drone_id": "", 

"drone_type": "Quadcopter", 

"operator_id": "OP-123", 

"latitude": 200, 

"longitude": 34.7818, 

"altitude_m": -50, 

"battery_percent": 150, 

"timestamp": "invalid-date", 

"status": "flying" 

} 

12.6. Expected Deliverables 

Backend source code. 

Frontend source code. 

README with setup and run instructions. 

Database schema or migrations. 

Example input file with valid and invalid records. 

Short explanation of the pipeline flow. 

Basic tests for important backend and frontend logic. 

13.7. Bonus Features 

Show low-battery drones differently when battery is below 20%. 

Highlight lost-signal drones. 

Show only the latest position per drone on the map. 

Show drone path history when selecting a drone. 

Add pagination to the backend drone endpoint. 

Add Docker Compose for frontend, backend, and database. 

Add meaningful unit/integration tests. 

Use Prefect, Celery, or a background worker for pipeline execution. 

14.8. Evaluation Focus 

The submission will be reviewed according to the following areas: 

Area 

What We Look For 

Backend 

Clean FastAPI structure, validation, database modeling, error handling, and API design. 

Pipeline 

Clear ingestion flow, validation, invalid-record handling, status tracking, and reusable logic. 

Frontend 

Clean Angular structure, map integration, API services, filters, loading states, and error states. 

Quality 

Readable code, separation of concerns, setup instructions, and basic tests. 

UX 

Clear dashboard layout, useful marker popups, and understandable pipeline status display. 

15.9. Submission Notes 

Please provide the project source code in a Git repository or compressed archive. 

The README should include all commands required to run the backend, frontend, and database if used. 

The system does not need to be production-ready, but it should be clear, maintainable, and easy to run. 

Assumptions and trade-offs should be documented briefly in the README. 