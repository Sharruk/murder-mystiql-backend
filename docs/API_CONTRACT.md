# MurderMystiQL — Official Frontend/Backend API Contract

**Target Audience:** Adithya & Nithya (Frontend Engineering Team)  
**Protocol:** REST (JSON over HTTP) + Native WebSocket for live leaderboard  
**Base URL:** `http://<SERVER-IP>:8000/api`  
**WebSocket URL:** `ws://<SERVER-IP>:8000/ws/leaderboard`  
**Environment:** 100% Offline Local LAN (College Event Server)

---

## Authentication & Session Lifecycle

- **No conventional login/password system.**
- Participants are assigned usernames beforehand (e.g. `DETECTIVE-01`, `DETECTIVE-02` ... `DETECTIVE-30`).
- Calling `POST /api/session/start` with an assigned username creates or resumes a session.
- The server returns an **opaque session token** (a 64-character hexadecimal string).
- **All subsequent authenticated requests** must include this token in **either** of these headers:
  ```http
  Authorization: Bearer <TOKEN>
  ```
  *OR*
  ```http
  X-Session-Token: <TOKEN>
  ```
- Browser refresh **never** resets progress. Storing the token in `localStorage` or `sessionStorage` and calling `POST /api/session/start` or `GET /api/level/current` restores state completely.

---

## Global Error Response Format

All error responses from the backend adhere to standard HTTP status codes with a JSON error payload:

```json
{
  "detail": "Descriptive error message explaining the issue."
}
```

Common status codes:
- `400 Bad Request`: Invalid input or forbidden SQL syntax / keywords.
- `401 Unauthorized`: Missing, expired, or invalid session token.
- `403 Forbidden`: Insufficient privileges or attempted access to protected schemas.
- `404 Not Found`: Detective username or level does not exist.
- `409 Conflict`: Action temporarily locked (e.g. 1-minute wrong answer lock active).
- `500 Internal Server Error`: Safe unexpected server error.

---

## REST Endpoints

### 1. Start or Resume Session
Authenticate a detective and obtain a session token.

- **Method:** `POST`
- **URL:** `/api/session/start`
- **Authentication:** None (Public entrypoint)
- **Headers:** `Content-Type: application/json`

#### Request Body:
```json
{
  "username": "DETECTIVE-01",
  "pin": null
}
```
*(Note: `pin` is optional; pass `null` or omit unless event organizers enable team PINs).*

#### Success Response (`200 OK`):
```json
{
  "token": "4f92a188fbb1724d9c020584b455b81a82e98cbe6bb6e4b4dd42512ea2c99db1",
  "participant": {
    "id": 1,
    "username": "DETECTIVE-01",
    "display_name": "Sherlock Holmes",
    "seat_no": "Lab-01"
  },
  "current_level_order": 1,
  "is_locked": false,
  "remaining_lock_seconds": 0,
  "effective_time_seconds": 12,
  "is_completed": false
}
```

#### Error Responses:
- `404 Not Found`:
  ```json
  { "detail": "Participant username 'DETECTIVE-99' not found. Please verify your assigned detective ID." }
  ```
- `401 Unauthorized`:
  ```json
  { "detail": "Invalid PIN for this detective account." }
  ```

---

### 2. Get Current Level
Retrieve the active level's narrative context, question, and unlocked investigation tables.

- **Method:** `GET`
- **URL:** `/api/level/current`
- **Authentication:** Required (`Authorization: Bearer <TOKEN>` or `X-Session-Token: <TOKEN>`)

#### Success Response (`200 OK`):
```json
{
  "id": 1,
  "order_no": 1,
  "title": "The Crime Scene Inspection",
  "story_context": "At 10:15 PM, Lord Harrington was discovered deceased in his study. The police log documents several items found around the estate.",
  "question_text": "Which item found at the crime scene had initials engraved on it? State the initials.",
  "unlocks_tables": [
    "crime_scene_log"
  ],
  "attempts": 2,
  "is_hint_used": false,
  "hint_text": null,
  "hint_penalty_seconds": 120,
  "is_locked": false,
  "remaining_lock_seconds": 0
}
```

*(Note: If the hint was previously unlocked by this session, `is_hint_used` will be `true` and `hint_text` will contain the revealed hint string).*

#### Error Responses:
- `401 Unauthorized`: Token missing or invalid.
- `404 Not Found`: Session not associated with a current level.

---

### 3. Execute Participant SQL Query
Run an arbitrary read-only SQL query against the `investigation` schema via the sandboxed `investigator_ro` connection pool.

- **Method:** `POST`
- **URL:** `/api/query/execute`
- **Authentication:** Required (`Authorization: Bearer <TOKEN>` or `X-Session-Token: <TOKEN>`)
- **Headers:** `Content-Type: application/json`

#### Request Body:
```json
{
  "query": "SELECT item, location, notes FROM crime_scene_log WHERE notes ILIKE '%engraved%';"
}
```

#### Success Response (`200 OK`):
```json
{
  "columns": [
    "item",
    "location",
    "notes"
  ],
  "rows": [
    [
      "Vintage Fountain Pen",
      "Desk Corner",
      "Engraved with initials A.V."
    ]
  ],
  "row_count": 1,
  "execution_time_ms": 3.42
}
```

#### Query Restrictions & Error Responses:
The query engine enforces strict security:
- Single statement only (no multiple semicolons `;`).
- Read-only `SELECT` only.
- No `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`, `TRUNCATE`, `GRANT`, `REVOKE`, `COPY`, `EXECUTE`, etc.
- No references to the internal `game` schema or system tables.
- 5-second statement timeout.
- Maximum 500 rows returned.

- `400 Bad Request`:
  ```json
  { "detail": "Query Validation Error: Multiple SQL statements are strictly forbidden. Submit only one query." }
  ```
  ```json
  { "detail": "Query Validation Error: Forbidden SQL keyword detected: DROP" }
  ```
  ```json
  { "detail": "SQL Syntax Error: syntax error at or near \"SELCT\"" }
  ```
- `403 Forbidden`:
  ```json
  { "detail": "Access Denied: You do not have permission to access that schema or table." }
  ```

---

### 4. Submit Answer
Submit an answer for the current level. The backend evaluates it authoritatively.

- **Method:** `POST`
- **URL:** `/api/answer/submit`
- **Authentication:** Required (`Authorization: Bearer <TOKEN>` or `X-Session-Token: <TOKEN>`)
- **Headers:** `Content-Type: application/json`

#### Request Body:
```json
{
  "answer": "A.V."
}
```

#### Success Response — Correct Answer (`200 OK`):
```json
{
  "is_correct": true,
  "message": "Brilliant detective work! Level 1 solved.",
  "completed": false,
  "next_level_order": 2,
  "is_locked": false,
  "remaining_lock_seconds": 0,
  "penalty_applied_seconds": 0
}
```

#### Response — Final Case Level Solved (`200 OK`):
```json
{
  "is_correct": true,
  "message": "Case Closed! You have solved all levels and unmasked the culprit.",
  "completed": true,
  "next_level_order": null,
  "is_locked": false,
  "remaining_lock_seconds": 0,
  "penalty_applied_seconds": 0
}
```

#### Response — Incorrect Answer (`200 OK`):
```json
{
  "is_correct": false,
  "message": "Incorrect answer. A 1-minute submission lock and 5-minute time penalty have been applied.",
  "completed": false,
  "next_level_order": null,
  "is_locked": true,
  "remaining_lock_seconds": 60,
  "penalty_applied_seconds": 300
}
```

#### Error Response — Attempting to Submit While Locked (`409 Conflict`):
```json
{
  "detail": "Submissions are locked for another 42 seconds due to a previous incorrect attempt."
}
```

---

### 5. Request Level Hint
Reveal the hint for the current level and incur the level's configured time penalty.

- **Method:** `POST`
- **URL:** `/api/hint/request`
- **Authentication:** Required (`Authorization: Bearer <TOKEN>` or `X-Session-Token: <TOKEN>`)
- **Headers:** `Content-Type: application/json`

#### Request Body:
Empty JSON object `{}`.

#### Success Response — First Time Requested (`200 OK`):
```json
{
  "level_order": 1,
  "hint_text": "Check the notes column in the crime_scene_log table for mentions of engravings.",
  "penalty_applied_seconds": 120,
  "is_already_revealed": false
}
```

#### Success Response — Already Requested for this Level (`200 OK`):
```json
{
  "level_order": 1,
  "hint_text": "Check the notes column in the crime_scene_log table for mentions of engravings.",
  "penalty_applied_seconds": 0,
  "is_already_revealed": true
}
```
*(Guaranteed idempotent: Repeated requests for the same level will NEVER charge additional penalties).*

---

### 6. Get Leaderboard
Retrieve the ranked standings of all participants.

- **Method:** `GET`
- **URL:** `/api/leaderboard`
- **Authentication:** None (Can be called by projector displays or participant dashboards)

#### Success Response (`200 OK`):
```json
{
  "entries": [
    {
      "rank": 1,
      "username": "DETECTIVE-01",
      "display_name": "Sherlock Holmes",
      "seat_no": "Lab-01",
      "current_level_order": 3,
      "levels_solved": 2,
      "total_penalty_seconds": 0,
      "wrong_answers_count": 0,
      "hints_used_count": 0,
      "effective_time_seconds": 340,
      "is_completed": false
    },
    {
      "rank": 2,
      "username": "DETECTIVE-03",
      "display_name": "Hercule Poirot",
      "seat_no": "Lab-03",
      "current_level_order": 2,
      "levels_solved": 1,
      "total_penalty_seconds": 300,
      "wrong_answers_count": 1,
      "hints_used_count": 0,
      "effective_time_seconds": 580,
      "is_completed": false
    }
  ],
  "total_participants": 2,
  "generated_at": "2026-09-10T00:30:00Z"
}
```

---

### 7. Record Proctor Violation
Record browser-level proctoring events detected by the frontend (tab switch, window blur, exiting fullscreen).

- **Method:** `POST`
- **URL:** `/api/proctor/violation`
- **Authentication:** Required (`Authorization: Bearer <TOKEN>` or `X-Session-Token: <TOKEN>`)
- **Headers:** `Content-Type: application/json`

#### Request Body:
```json
{
  "type": "TAB_SWITCH",
  "detail": "User switched tabs or minimized window for 4 seconds."
}
```
*Supported violation types:* `TAB_SWITCH`, `FULLSCREEN_EXIT`, `FOCUS_LOSS`, `DEVTOOLS_OPEN`.

#### Success Response (`200 OK`):
```json
{
  "status": "recorded",
  "violation_id": 14,
  "recorded_at": "2026-09-10T00:31:12Z"
}
```

---

## Native WebSocket — Live Leaderboard

Connect to receive real-time leaderboard broadcasts whenever any participant submits an answer or requests a hint.

- **WebSocket URL:** `ws://<SERVER-IP>:8000/ws/leaderboard`
- **Connection Handshake:** Direct WebSocket connection (no initial query params required).

### Incoming Server Messages:
Upon connection, the server immediately pushes a snapshot:
```json
{
  "event": "LEADERBOARD_SNAPSHOT",
  "data": {
    "entries": [ ... ],
    "total_participants": 2,
    "generated_at": "2026-09-10T00:30:00Z"
  }
}
```

Whenever game state changes (a level is solved, incorrect answer penalty applied, or hint taken):
```json
{
  "event": "LEADERBOARD_UPDATE",
  "data": {
    "entries": [ ... ],
    "total_participants": 2,
    "generated_at": "2026-09-10T00:32:15Z"
  }
}
```

### Client Heartbeat:
Clients can send `"ping"` string over the WebSocket; the server replies with `"pong"`.
