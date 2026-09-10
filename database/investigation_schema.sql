-- ==============================================================================
-- MurderMystiQL: Investigation Schema (Pending Story Team Finalization)
-- ==============================================================================
-- IMPORTANT NOTE FROM SRS:
-- "The story team's document must exist before backend schema work begins —
-- the schema is derived from the case, not the other way around."
--
-- STATUS: PENDING FINAL STORY DATA
-- Once the story team completes the finalized narrative, suspect roster,
-- crime scene logs, and forensic clues, replace the sample tables below
-- with the actual case tables.
--
-- ALL tables in this schema are granted SELECT to 'investigator_ro'
-- so participants can query them via their SQL editor.
-- ==============================================================================

CREATE SCHEMA IF NOT EXISTS investigation;

-- Sample/Test Investigation Tables for System Validation & Test Suite
-- (These will be updated with the official story tables once provided)

CREATE TABLE IF NOT EXISTS investigation.suspects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    relationship VARCHAR(100),
    occupation VARCHAR(100),
    alibi TEXT
);

CREATE TABLE IF NOT EXISTS investigation.crime_scene_log (
    id SERIAL PRIMARY KEY,
    item VARCHAR(100) NOT NULL,
    location VARCHAR(100) NOT NULL,
    discovered_at TIMESTAMP WITH TIME ZONE NOT NULL,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS investigation.phone_records (
    id SERIAL PRIMARY KEY,
    caller VARCHAR(100) NOT NULL,
    receiver VARCHAR(100) NOT NULL,
    call_time TIMESTAMP WITH TIME ZONE NOT NULL,
    duration_seconds INT NOT NULL
);

-- Placeholder Seed Data for System Testing
INSERT INTO investigation.suspects (name, relationship, occupation, alibi) VALUES
('Arthur Vance', 'Business Partner', 'CFO', 'At the country club dining room until 10:30 PM'),
('Beatrice Ward', 'Personal Assistant', 'Secretary', 'Working late in the archives on the 2nd floor'),
('Charles Sterling', 'Estranged Brother', 'Investor', 'Driving back from out of town')
ON CONFLICT DO NOTHING;

INSERT INTO investigation.crime_scene_log (item, location, discovered_at, notes) VALUES
('Shattered Glass', 'Library French Doors', '2026-09-10 22:15:00+00', 'Impact from the outside'),
('Vintage Fountain Pen', 'Desk Corner', '2026-09-10 22:20:00+00', 'Engraved with initials A.V.'),
('Burned Note', 'Fireplace Hearth', '2026-09-10 22:30:00+00', 'Fragment contains the word "Blackmail"')
ON CONFLICT DO NOTHING;

INSERT INTO investigation.phone_records (caller, receiver, call_time, duration_seconds) VALUES
('Arthur Vance', 'Victim Office', '2026-09-10 21:45:00+00', 120),
('Beatrice Ward', 'Home', '2026-09-10 22:05:00+00', 45)
ON CONFLICT DO NOTHING;
