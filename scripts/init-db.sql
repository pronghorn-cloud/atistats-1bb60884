-- AI-Academy 3 ATI Stats - Database Initialization Script
-- This script runs when the PostgreSQL container is first created

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search

-- Create schemas (optional, for organization)
-- CREATE SCHEMA IF NOT EXISTS ati;

-- Grant privileges (adjust as needed for production)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO ati_stats;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO ati_stats;

-- Performance tuning for reporting queries
-- These settings can be adjusted based on your server resources

-- Note: These ALTER SYSTEM commands require superuser privileges
-- and a database restart to take effect. They are provided as examples.
-- In production, configure these in postgresql.conf or via environment variables.

-- Example settings (uncomment and adjust as needed):
-- ALTER SYSTEM SET shared_buffers = '256MB';
-- ALTER SYSTEM SET effective_cache_size = '768MB';
-- ALTER SYSTEM SET maintenance_work_mem = '64MB';
-- ALTER SYSTEM SET checkpoint_completion_target = 0.9;
-- ALTER SYSTEM SET wal_buffers = '8MB';
-- ALTER SYSTEM SET default_statistics_target = 100;
-- ALTER SYSTEM SET random_page_cost = 1.1;
-- ALTER SYSTEM SET effective_io_concurrency = 200;
-- ALTER SYSTEM SET work_mem = '4MB';
-- ALTER SYSTEM SET min_wal_size = '1GB';
-- ALTER SYSTEM SET max_wal_size = '4GB';

-- Log message
DO $$
BEGIN
    RAISE NOTICE 'ATI Stats database initialized successfully';
END $$;
