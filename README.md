# MurderMystiQL — Backend

**Event:** Invente 2026  
**Architecture:** 100% Offline Local LAN Deployment  
**Stack:** Python 3.10+, FastAPI, Uvicorn, PostgreSQL, asyncpg, SQLAlchemy Async, Native WebSockets

---

## 1. Project Purpose

MurderMystiQL is a high-stakes, competitive SQL-based murder mystery game designed for college symposiums. In a controlled offline LAN computer lab environment, participants take on the role of detectives. Using pre-assigned detective IDs and raw SQL queries, teams interrogate evidence, parse suspect alibis, cross-reference phone records, and crack the mystery level by level.

The backend acts as the single source of truth:
- Evaluates answers and administers strict 1-minute submission locks and 5-minute time penalties for incorrect submissions.
- Sandboxes participant SQL queries with read-only execution, statement timeouts, row caps, and absolute isolation from internal game state.
- Computes real-time standings and broadcasts live leaderboard updates to projector screens and participant dashboards over WebSockets.

---

## 2. System Architecture & Dual-Pool Security Model

The system runs on **one local server machine** hosting PostgreSQL and FastAPI, accessed by participant laptops over a Wi-Fi router or Ethernet switch with **zero internet dependency**.

```
  ┌─────────────────────────────────────────────────────────┐
  │                 Participant Laptops (LAN)               │
  │        Browser: http://<SERVER-IP>:8000 (React App)     │
  └────────────────────────────┬────────────────────────────┘
                               │ HTTP REST & WebSockets
                               ▼
  ┌─────────────────────────────────────────────────────────┐
  │             Server Laptop (FastAPI + Uvicorn)           │
  │                                                         │
  │   [POOL 1: game_owner]             [POOL 2: investigator_ro]
  │   - SQLAlchemy Async               - asyncpg (5-10 conns)
  │   - Read/Write Game State          - SET TRANSACTION READ ONLY
  │   - Sessions, Answers,             - 5-sec Statement Timeout
  │     Penalties, Leaderboard         - Max 500 Rows Cap
  └─────────────┬──────────────────────────────┬────────────┘
                │                              │
                ▼                              ▼
  ┌───────────────────────────┐  ┌───────────────────────────┐
  │ PostgreSQL: 'game' Schema │  │ PostgreSQL: 'investigation'
  │ - participants            │  │ - crime_scene_log         │
  │ - levels                  │  │ - suspects                │
  │ - sessions                │  │ - phone_records           │
  │ - submissions             │  │   (Derived from finalized │
  │ - penalties               │  │    story document)        │
  └───────────────────────────┘  └───────────────────────────┘
```

### Critical Security Isolation:
- **`game_owner` Pool:** Exclusive read/write access to the `game` schema. Used only by backend internal services.
- **`investigator_ro` Pool:** Dedicated strictly to executing participant-submitted SQL.
  - Granted `USAGE` and `SELECT` **only** on the `investigation` schema.
  - Hard-revoked from `game` schema, system catalogs, and `public`.
  - Enforces `SET TRANSACTION READ ONLY`.
  - Backend AST/Token inspection blocks chained queries (`;`), DDL (`DROP`, `ALTER`, `CREATE`, `TRUNCATE`), and DML writes (`INSERT`, `UPDATE`, `DELETE`).

---

## 3. Technology Stack

- **Framework:** FastAPI (Python 3.10+)
- **ASGI Server:** Uvicorn
- **Database:** Local PostgreSQL 14+ (2 schemas: `game` and `investigation`)
- **Query Drivers:**
  - `SQLAlchemy 2.0 (asyncio)` for game logic and session state
  - `asyncpg` for high-throughput, sandboxed participant query execution
- **Query Parser:** `sqlparse`
- **Real-Time Push:** Native FastAPI WebSockets (`/ws/leaderboard`)

---

## 4. Repository Structure

```
murder-mystiql-backend/
├── app/
│   ├── main.py                     # FastAPI app, CORS, static SPA mount, lifespan
│   ├── api/                        # REST endpoint routers
│   │   ├── __init__.py
│   │   ├── session.py              # POST /api/session/start
│   │   ├── level.py                # GET /api/level/current
│   │   ├── query.py                # POST /api/query/execute
│   │   ├── answer.py               # POST /api/answer/submit
│   │   ├── hint.py                 # POST /api/hint/request
│   │   ├── leaderboard.py         # GET /api/leaderboard
│   │   └── proctor.py              # POST /api/proctor/violation
│   ├── core/
│   │   ├── config.py               # Pydantic settings and env management
│   │   └── security.py             # SQL AST validation and token generation
│   ├── db/
│   │   ├── connection.py           # Dual connection pool management
│   │   ├── models.py               # SQLAlchemy ORM definitions for game schema
│   │   └── session.py              # Dependency injectors (get_db, get_investigator_pool)
│   ├── schemas/                    # Pydantic request/response models
│   ├── services/                   # Authoritative game rules and business logic
│   └── websocket/
│       └── leaderboard.py          # WebSocket connection manager and broadcaster
├── database/
│   ├── roles.sql                   # Creates game_owner and investigator_ro roles
│   ├── game_schema.sql             # Creates game schema, tables, and leaderboard view
│   ├── investigation_schema.sql    # Template for story team's investigation data
│   ├── seed.sql                    # Initial seed for participants (DETECTIVE-01..30) & levels
│   └── setup_db.py                 # Automated Python setup script
├── docs/
│   └── API_CONTRACT.md             # Complete frontend API documentation for Adithya & Nithya
├── tests/                          # 15-scenario verification test suite
│   ├── conftest.py
│   ├── test_session.py             # Tests 1-3: Start, reject, resume
│   ├── test_gameplay.py            # Tests 4-8: Answers, penalties, locks, hints
│   ├── test_sql_sandbox.py         # Tests 9-13: SELECT, write-block, DDL-block, multi-statement
│   ├── test_leaderboard.py         # Test 14: Effective time calculation
│   └── test_proctor.py             # Test 15: Proctor violations logging
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 5. Local PostgreSQL Database Setup

### Step 1: Create Database
On the server laptop, open `psql` or pgAdmin as the `postgres` superuser:

```sql
CREATE DATABASE murdermystiql;
```

### Step 2: Initialize Roles, Schemas, and Seed Data
You can either run the automated Python setup script or execute the SQL files in order.

**Option A: Automated Python Setup**
```bash
python database/setup_db.py --admin-url postgresql://postgres:<POSTGRES_PASSWORD>@localhost:5432/murdermystiql
```

**Option B: Manual PSQL Execution**
```bash
psql -U postgres -d murdermystiql -f database/roles.sql
psql -U postgres -d murdermystiql -f database/game_schema.sql
psql -U postgres -d murdermystiql -f database/investigation_schema.sql
psql -U postgres -d murdermystiql -f database/seed.sql
```

---

## 6. Environment Configuration

Copy the example configuration:
```bash
copy .env.example .env
```

Ensure your `.env` matches your local PostgreSQL credentials:

```ini
APP_NAME="MurderMystiQL Backend"
APP_ENV="production"
DEBUG=false
HOST="0.0.0.0"
PORT=8000

# Pool 1: game_owner
GAME_DATABASE_URL="postgresql+asyncpg://game_owner:GameOwnerSecurePass123!@localhost:5432/murdermystiql"

# Pool 2: investigator_ro
INVESTIGATOR_DATABASE_URL="postgresql://investigator_ro:InvestigatorReadOnlyPass123!@localhost:5432/murdermystiql"

STATEMENT_TIMEOUT_MS=5000
MAX_QUERY_ROWS=500
WRONG_ANSWER_LOCK_SECONDS=60
WRONG_ANSWER_PENALTY_SECONDS=300

# Optional: Path to built React frontend dist folder
FRONTEND_DIST_DIR="../murder-mystiql-frontend/dist"
CORS_ORIGINS=["*"]
```

---

## 7. Running the Server

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Start Backend
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```
- Interactive API Documentation: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health`
- WebSocket Leaderboard: `ws://localhost:8000/ws/leaderboard`

---

## 8. Running the Test Suite

The test suite validates all 15 core game, security, and lifecycle constraints:

```bash
pytest -v tests/
```

Test scenarios covered:
1. `test_valid_participant_session_start`: Start session with pre-assigned username.
2. `test_unknown_username_rejected`: Reject unregistered username with 404.
3. `test_existing_session_resumes`: Resuming preserves state and token across page reloads.
4. `test_correct_answer_unlocks_next_level`: Correct answer advances to the next level.
5. `test_wrong_answer_applies_penalty_and_lock`: Wrong answer adds 300s penalty.
6. `test_wrong_answer_applies_penalty_and_lock`: Wrong answer triggers 60s lock.
7. `test_locked_participant_cannot_submit`: Submissions blocked with 409 while locked.
8. `test_hint_applies_configured_penalty`: Hint reveals clue and charges penalty idempotently.
9. `test_participant_sql_select_works`: SELECT query returns columns and rows.
10. `test_participant_sql_insert_update_delete_fails`: DML writes rejected.
11. `test_participant_sql_drop_fails`: DDL DROP commands rejected.
12. `test_participant_sql_multiple_statements_fail`: Statement chaining rejected.
13. `test_participant_cannot_access_game_schema`: Game schema access prohibited.
14. `test_leaderboard_effective_time_and_ranking`: Standings and effective time formula verified.
15. `test_proctor_violation_recorded`: Client tab switch/blur events logged.

---

## 9. Offline LAN Deployment Guide

1. **Server Machine Setup:**
   - Connect the server laptop to the event LAN router (Wi-Fi or Ethernet switch).
   - Find the server's local LAN IP:
     - Windows: `ipconfig` (e.g. `192.168.1.100`)
     - Linux/Mac: `ip a` or `ifconfig`
2. **Build and Mount the Frontend:**
   - Build the React frontend on the frontend repo: `npm run build`.
   - Copy the `dist` directory into `murder-mystiql-backend/static` or point `FRONTEND_DIST_DIR` in `.env` to the build folder.
3. **Launch Server:**
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
   ```
4. **Participant Access:**
   - Direct all participant laptops to: `http://192.168.1.100:8000`.
   - Each team enters their assigned ID (`DETECTIVE-01` through `DETECTIVE-30`).
   - The projector screen navigates to the leaderboard view on the frontend, which connects to `ws://192.168.1.100:8000/ws/leaderboard` for live updates.

---

## 10. Story Team Hand-off Notes

The investigation schema is derived from the official narrative case document. Once the story team finalizes clues, suspect tables, and answers:
1. Update `database/investigation_schema.sql` with the final tables.
2. Update the level questions and correct answers in `database/seed.sql`.
3. Re-run `python database/setup_db.py`.
