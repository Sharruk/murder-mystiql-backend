-- ==============================================================================
-- MurderMystiQL: Game Schema & Tables
-- ==============================================================================
-- This schema houses all authoritative game state, participants, sessions,
-- progress tracking, submissions, penalties, and leaderboard views.
-- Only 'game_owner' role has access to this schema.

CREATE SCHEMA IF NOT EXISTS game;

-- 1. Participants
CREATE TABLE IF NOT EXISTS game.participants (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(64) UNIQUE NOT NULL,
    display_name VARCHAR(128) NOT NULL,
    pin VARCHAR(32),
    seat_no VARCHAR(32),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_participants_username ON game.participants(username);

-- 2. Levels
CREATE TABLE IF NOT EXISTS game.levels (
    id BIGSERIAL PRIMARY KEY,
    order_no INT UNIQUE NOT NULL,
    title VARCHAR(255) NOT NULL,
    story_context TEXT NOT NULL,
    question_text TEXT NOT NULL,
    correct_answer TEXT NOT NULL,
    hint_text TEXT NOT NULL,
    hint_penalty_seconds INT DEFAULT 180 NOT NULL,
    unlocks_tables JSONB DEFAULT '[]'::jsonb NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_levels_order_no ON game.levels(order_no);

-- 3. Sessions
CREATE TABLE IF NOT EXISTS game.sessions (
    id BIGSERIAL PRIMARY KEY,
    participant_id BIGINT UNIQUE NOT NULL REFERENCES game.participants(id) ON DELETE CASCADE,
    token VARCHAR(128) UNIQUE NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    current_level_id BIGINT REFERENCES game.levels(id),
    locked_until TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_sessions_token ON game.sessions(token);
CREATE INDEX IF NOT EXISTS idx_sessions_participant ON game.sessions(participant_id);

-- 4. Level Progress (Tracks unlocked/solved timestamp & attempts per level)
CREATE TABLE IF NOT EXISTS game.level_progress (
    session_id BIGINT NOT NULL REFERENCES game.sessions(id) ON DELETE CASCADE,
    level_id BIGINT NOT NULL REFERENCES game.levels(id) ON DELETE CASCADE,
    unlocked_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    solved_at TIMESTAMP WITH TIME ZONE,
    attempts INT DEFAULT 0 NOT NULL,
    PRIMARY KEY (session_id, level_id)
);

CREATE INDEX IF NOT EXISTS idx_level_progress_session ON game.level_progress(session_id);

-- 5. Submissions (Audit log of all participant answer submissions)
CREATE TABLE IF NOT EXISTS game.submissions (
    id BIGSERIAL PRIMARY KEY,
    session_id BIGINT NOT NULL REFERENCES game.sessions(id) ON DELETE CASCADE,
    level_id BIGINT NOT NULL REFERENCES game.levels(id) ON DELETE CASCADE,
    submitted_answer TEXT NOT NULL,
    is_correct BOOLEAN NOT NULL,
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_submissions_session ON game.submissions(session_id);

-- 6. Hints Used
CREATE TABLE IF NOT EXISTS game.hints_used (
    id BIGSERIAL PRIMARY KEY,
    session_id BIGINT NOT NULL REFERENCES game.sessions(id) ON DELETE CASCADE,
    level_id BIGINT NOT NULL REFERENCES game.levels(id) ON DELETE CASCADE,
    used_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
    penalty_applied_seconds INT NOT NULL,
    CONSTRAINT uq_session_level_hint UNIQUE (session_id, level_id)
);

CREATE INDEX IF NOT EXISTS idx_hints_used_session ON game.hints_used(session_id);

-- 7. Penalties (Wrong answers, hint penalties, manual proctor penalties)
CREATE TABLE IF NOT EXISTS game.penalties (
    id BIGSERIAL PRIMARY KEY,
    session_id BIGINT NOT NULL REFERENCES game.sessions(id) ON DELETE CASCADE,
    reason VARCHAR(64) NOT NULL,
    seconds INT NOT NULL,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_penalties_session ON game.penalties(session_id);

-- 8. Proctor Violations (Client tab switch, blur, fullscreen exit)
CREATE TABLE IF NOT EXISTS game.proctor_violations (
    id BIGSERIAL PRIMARY KEY,
    session_id BIGINT NOT NULL REFERENCES game.sessions(id) ON DELETE CASCADE,
    type VARCHAR(64) NOT NULL,
    detail TEXT,
    occurred_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_proctor_violations_session ON game.proctor_violations(session_id);

-- 9. Leaderboard View
-- Calculates ranks based on:
-- 1. Levels solved DESC
-- 2. Effective time ASC (Elapsed time + sum of penalties)
CREATE OR REPLACE VIEW game.v_leaderboard AS
WITH penalty_summary AS (
    SELECT
        session_id,
        COALESCE(SUM(seconds), 0)::INT AS total_penalty_seconds,
        COUNT(CASE WHEN reason = 'WRONG_ANSWER' THEN 1 END)::INT AS wrong_answers_count,
        COUNT(CASE WHEN reason = 'HINT' THEN 1 END)::INT AS hints_used_count
    FROM game.penalties
    GROUP BY session_id
),
progress_summary AS (
    SELECT
        session_id,
        COUNT(CASE WHEN solved_at IS NOT NULL THEN 1 END)::INT AS levels_solved
    FROM game.level_progress
    GROUP BY session_id
)
SELECT
    p.id AS participant_id,
    p.username,
    p.display_name,
    p.seat_no,
    s.id AS session_id,
    s.started_at,
    s.completed_at,
    (s.completed_at IS NOT NULL) AS is_completed,
    COALESCE(lvl.order_no, 1) AS current_level_order,
    COALESCE(prog.levels_solved, 0) AS levels_solved,
    COALESCE(pen.total_penalty_seconds, 0) AS total_penalty_seconds,
    COALESCE(pen.wrong_answers_count, 0) AS wrong_answers_count,
    COALESCE(pen.hints_used_count, 0) AS hints_used_count,
    -- Raw elapsed seconds: completed_at - started_at if completed, else NOW() - started_at
    EXTRACT(EPOCH FROM (COALESCE(s.completed_at, CURRENT_TIMESTAMP) - s.started_at))::INT AS raw_elapsed_seconds,
    -- Effective Time = Raw elapsed seconds + total penalty seconds
    (
        EXTRACT(EPOCH FROM (COALESCE(s.completed_at, CURRENT_TIMESTAMP) - s.started_at))::INT
        + COALESCE(pen.total_penalty_seconds, 0)
    ) AS effective_time_seconds,
    DENSE_RANK() OVER (
        ORDER BY
            (s.completed_at IS NOT NULL) DESC,
            COALESCE(prog.levels_solved, 0) DESC,
            (
                EXTRACT(EPOCH FROM (COALESCE(s.completed_at, CURRENT_TIMESTAMP) - s.started_at))::INT
                + COALESCE(pen.total_penalty_seconds, 0)
            ) ASC
    ) AS rank
FROM game.sessions s
JOIN game.participants p ON s.participant_id = p.id
LEFT JOIN game.levels lvl ON s.current_level_id = lvl.id
LEFT JOIN progress_summary prog ON s.id = prog.session_id
LEFT JOIN penalty_summary pen ON s.id = pen.session_id;
