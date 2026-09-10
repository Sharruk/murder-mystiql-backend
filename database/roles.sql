-- ==============================================================================
-- MurderMystiQL: PostgreSQL Roles & Security Grants
-- ==============================================================================
-- Run as superuser (e.g. postgres) against database 'murdermystiql'.

-- 1. Create Roles if they do not exist
DO
$do$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'game_owner') THEN
      CREATE ROLE game_owner WITH LOGIN PASSWORD 'GameOwnerSecurePass123!';
   END IF;
   IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'investigator_ro') THEN
      CREATE ROLE investigator_ro WITH LOGIN PASSWORD 'InvestigatorReadOnlyPass123!';
   END IF;
END
$do$;

-- Ensure database exists and grant connect
GRANT CONNECT ON DATABASE murdermystiql TO game_owner;
GRANT CONNECT ON DATABASE murdermystiql TO investigator_ro;

-- 2. Schema: game
-- game_owner manages game state
CREATE SCHEMA IF NOT EXISTS game AUTHORIZATION game_owner;
GRANT ALL PRIVILEGES ON SCHEMA game TO game_owner;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA game TO game_owner;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA game TO game_owner;
GRANT ALL PRIVILEGES ON ALL ROUTINES IN SCHEMA game TO game_owner;

ALTER DEFAULT PRIVILEGES FOR ROLE game_owner IN SCHEMA game
    GRANT ALL ON TABLES TO game_owner;
ALTER DEFAULT PRIVILEGES FOR ROLE game_owner IN SCHEMA game
    GRANT ALL ON SEQUENCES TO game_owner;

-- 3. Schema: investigation
-- Both roles need schema access, but investigator_ro is strictly SELECT only
CREATE SCHEMA IF NOT EXISTS investigation AUTHORIZATION game_owner;
GRANT ALL PRIVILEGES ON SCHEMA investigation TO game_owner;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA investigation TO game_owner;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA investigation TO game_owner;

-- 4. CRITICAL SECURITY SANDBOX: investigator_ro Permissions
-- investigator_ro must ONLY have USAGE on investigation and SELECT on its tables.
GRANT USAGE ON SCHEMA investigation TO investigator_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA investigation TO investigator_ro;

-- Ensure future tables created in investigation are readable by investigator_ro
ALTER DEFAULT PRIVILEGES FOR ROLE game_owner IN SCHEMA investigation
    GRANT SELECT ON TABLES TO investigator_ro;

-- STRICT ISOLATION: investigator_ro must NEVER touch game schema or public
REVOKE ALL ON SCHEMA game FROM investigator_ro;
REVOKE ALL ON ALL TABLES IN SCHEMA game FROM investigator_ro;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA game FROM investigator_ro;
REVOKE ALL ON ALL ROUTINES IN SCHEMA game FROM investigator_ro;

ALTER DEFAULT PRIVILEGES FOR ROLE game_owner IN SCHEMA game
    REVOKE ALL ON TABLES FROM investigator_ro;
ALTER DEFAULT PRIVILEGES FOR ROLE game_owner IN SCHEMA game
    REVOKE ALL ON SEQUENCES FROM investigator_ro;

-- Revoke default public schema access from investigator_ro
REVOKE CREATE ON SCHEMA public FROM investigator_ro;
