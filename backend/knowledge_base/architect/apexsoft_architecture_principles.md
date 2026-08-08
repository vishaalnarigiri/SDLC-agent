# ApexSoft Solutions - System Design and Architecture Principles

All software architecture designs must conform to these standard layout guidelines:

## 1. Modular Separation
All applications must separate business logic, database queries, and routing layers:
*   `src/database.py` (or `db.py`): Manages database connections, schemas, and sessions.
*   `src/models.py`: Defines database schemas or entity classes.
*   `src/routes.py` (or `main.py`): Entrypoint containing endpoints, routing, and controller flows.

## 2. Database Standards
*   For local application storage, we strictly use **SQLite**.
*   Database initializations must happen via SQL queries run on startup (e.g. `CREATE TABLE IF NOT EXISTS`).
*   Include connection pool safety routines (ensure connection close).

## 3. API Conventions
*   All endpoints must return structured JSON objects containing a success key or clean response payloads.
*   Use standard HTTP statuses (e.g., `200 OK`, `201 Created`, `400 Bad Request`, `404 Not Found`).
