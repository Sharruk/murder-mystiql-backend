-- ==============================================================================
-- MurderMystiQL: Initial Database Seed
-- ==============================================================================
-- Pre-seeds 30 participant slots and initial level specifications.

-- 1. Seed Participants (DETECTIVE-01 to DETECTIVE-30)
INSERT INTO game.participants (username, display_name, seat_no) VALUES
('DETECTIVE-01', 'Sherlock Holmes', 'Lab-01'),
('DETECTIVE-02', 'John Watson', 'Lab-02'),
('DETECTIVE-03', 'Hercule Poirot', 'Lab-03'),
('DETECTIVE-04', 'Miss Marple', 'Lab-04'),
('DETECTIVE-05', 'Benoit Blanc', 'Lab-05'),
('DETECTIVE-06', 'Columbo', 'Lab-06'),
('DETECTIVE-07', 'Adrian Monk', 'Lab-07'),
('DETECTIVE-08', 'Veronica Mars', 'Lab-08'),
('DETECTIVE-09', 'Philip Marlowe', 'Lab-09'),
('DETECTIVE-10', 'Sam Spade', 'Lab-10'),
('DETECTIVE-11', 'Nancy Drew', 'Lab-11'),
('DETECTIVE-12', 'Perry Mason', 'Lab-12'),
('DETECTIVE-13', 'C. Auguste Dupin', 'Lab-13'),
('DETECTIVE-14', 'Jessica Fletcher', 'Lab-14'),
('DETECTIVE-15', 'Nero Wolfe', 'Lab-15'),
('DETECTIVE-16', 'K Detective 16', 'Lab-16'),
('DETECTIVE-17', 'K Detective 17', 'Lab-17'),
('DETECTIVE-18', 'K Detective 18', 'Lab-18'),
('DETECTIVE-19', 'K Detective 19', 'Lab-19'),
('DETECTIVE-20', 'K Detective 20', 'Lab-20'),
('DETECTIVE-21', 'K Detective 21', 'Lab-21'),
('DETECTIVE-22', 'K Detective 22', 'Lab-22'),
('DETECTIVE-23', 'K Detective 23', 'Lab-23'),
('DETECTIVE-24', 'K Detective 24', 'Lab-24'),
('DETECTIVE-25', 'K Detective 25', 'Lab-25'),
('DETECTIVE-26', 'K Detective 26', 'Lab-26'),
('DETECTIVE-27', 'K Detective 27', 'Lab-27'),
('DETECTIVE-28', 'K Detective 28', 'Lab-28'),
('DETECTIVE-29', 'K Detective 29', 'Lab-29'),
('DETECTIVE-30', 'K Detective 30', 'Lab-30')
ON CONFLICT (username) DO NOTHING;

-- 2. Seed Levels (Generic Level Architecture - Story details to be updated by story team)
INSERT INTO game.levels (order_no, title, story_context, question_text, correct_answer, hint_text, hint_penalty_seconds, unlocks_tables) VALUES
(
    1,
    'The Crime Scene Inspection',
    'At 10:15 PM, Lord Harrington was discovered deceased in his study. The police log documents several items found around the estate.',
    'Which item found at the crime scene had initials engraved on it? State the initials.',
    'A.V.',
    'Check the notes column in the crime_scene_log table for mentions of engravings.',
    120,
    '["crime_scene_log"]'::jsonb
),
(
    2,
    'Unmasking the Initials',
    'The initials point toward someone intimately connected with Harrington Industries.',
    'What is the full name of the suspect whose initials match the engraved item found on the desk?',
    'Arthur Vance',
    'Query the suspects table and compare their names to the initials from Level 1.',
    180,
    '["crime_scene_log", "suspects"]'::jsonb
),
(
    3,
    'The Disputed Alibi',
    'Vance claimed he was at the country club dining room until 10:30 PM, but phone logs suggest otherwise.',
    'At what time did Arthur Vance place a call to the victim''s office? (Format: HH:MM)',
    '21:45',
    'Query the phone_records table where the caller is Arthur Vance and check the call_time.',
    180,
    '["crime_scene_log", "suspects", "phone_records"]'::jsonb
),
(
    4,
    'The Fireplace Evidence',
    'A partially burned piece of paper was pulled from the fireplace hearth before it turned completely to ash.',
    'What single word was found on the burned note recovered from the fireplace?',
    'Blackmail',
    'Inspect the notes column in crime_scene_log for items discovered at the fireplace hearth.',
    240,
    '["crime_scene_log", "suspects", "phone_records"]'::jsonb
),
(
    5,
    'Final Accusation',
    'Reviewing the timeline, phone records, and motive, identify the primary suspect who had both means and opportunity.',
    'Who is the primary suspect responsible for the crime?',
    'Arthur Vance',
    'Synthesize the evidence from Levels 1 through 4.',
    300,
    '["crime_scene_log", "suspects", "phone_records"]'::jsonb
)
ON CONFLICT (order_no) DO NOTHING;
