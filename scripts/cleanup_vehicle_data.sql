-- ==========================================================
-- CLEANUP SCRIPT: Remove All Vehicle Domain Data
-- Phase 0 - Multi-Tenant RaaS Transformation
-- ==========================================================
-- This script completely removes the vehicle domain model and data
-- from the database. NO BACKUP is created as per user confirmation.
--
-- DANGER: This operation is IRREVERSIBLE!
-- ==========================================================

\echo '============================================================'
\echo 'WARNING: This will permanently delete all vehicle data!'
\echo 'NO BACKUP will be created.'
\echo 'Press Ctrl+C to abort, or Enter to continue...'
\prompt 'Continue? (yes/no): ' confirmation

\if :{?confirmation}
  \if :confirmation = 'yes'
    \echo 'Proceeding with cleanup...'
  \else
    \echo 'Aborted by user.'
    \quit
  \endif
\else
  \echo 'Aborted by user.'
  \quit
\endif

\echo ''
\echo '============================================================'
\echo 'Step 1: Dropping Vehicle Domain Tables'
\echo '============================================================'

-- Drop all vehicle-related tables in correct order (respecting FK constraints)
DROP TABLE IF EXISTS vehicle_review CASCADE;
DROP TABLE IF EXISTS vehicle_illustration_image CASCADE;
DROP TABLE IF EXISTS vehicle_can_transport CASCADE;
DROP TABLE IF EXISTS vehicle_keyword CASCADE;
DROP TABLE IF EXISTS vehicle_amenity CASCADE;
DROP TABLE IF EXISTS vehicle_ownership CASCADE;
DROP TABLE IF EXISTS vehicles CASCADE;
DROP TABLE IF EXISTS party CASCADE;

-- Drop vehicle reference/lookup tables
DROP TABLE IF EXISTS vehicle_make CASCADE;
DROP TABLE IF EXISTS vehicle_model CASCADE;
DROP TABLE IF EXISTS transmission_type CASCADE;
DROP TABLE IF EXISTS fuel_type CASCADE;
DROP TABLE IF EXISTS vehicle_type CASCADE;
DROP TABLE IF EXISTS vehicle_size CASCADE;
DROP TABLE IF EXISTS manufacturer CASCADE;

\echo '✓ Vehicle tables dropped successfully'

\echo ''
\echo '============================================================'
\echo 'Step 2: Dropping Legacy Tables'
\echo '============================================================'

-- Drop legacy tables from older schema versions
DROP TABLE IF EXISTS personnes CASCADE;
DROP TABLE IF EXISTS comments CASCADE;

\echo '✓ Legacy tables dropped successfully'

\echo ''
\echo '============================================================'
\echo 'Step 3: Cleaning Up Triggers and Functions'
\echo '============================================================'

-- Drop triggers related to vehicle tables
DROP TRIGGER IF EXISTS update_vehicles_updated_at ON vehicles;
DROP TRIGGER IF EXISTS update_personnes_updated_at ON personnes;
DROP TRIGGER IF EXISTS tr_update_vehicles ON vehicles;
DROP TRIGGER IF EXISTS tr_update_party ON party;

\echo '✓ Triggers cleaned up successfully'

\echo ''
\echo '============================================================'
\echo 'Step 4: Verifying Cleanup'
\echo '============================================================'

-- Verify all vehicle tables are gone
DO $$
DECLARE
    table_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO table_count
    FROM information_schema.tables
    WHERE table_schema = 'public'
    AND table_name IN (
        'vehicles', 'vehicle_review', 'vehicle_illustration_image',
        'vehicle_can_transport', 'vehicle_keyword', 'vehicle_amenity',
        'vehicle_ownership', 'party', 'vehicle_make', 'vehicle_model',
        'transmission_type', 'fuel_type', 'vehicle_type', 'vehicle_size',
        'manufacturer', 'personnes', 'comments'
    );

    IF table_count = 0 THEN
        RAISE NOTICE '✓ All vehicle tables successfully removed (0 remaining)';
    ELSE
        RAISE WARNING '⚠ Warning: % vehicle table(s) still exist!', table_count;
    END IF;
END $$;

\echo ''
\echo '============================================================'
\echo 'Step 5: Listing Remaining Tables'
\echo '============================================================'

-- Show remaining tables in the database
SELECT schemaname, tablename
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY tablename;

\echo ''
\echo '============================================================'
\echo 'Cleanup Summary'
\echo '============================================================'
\echo 'Vehicle domain tables: DELETED'
\echo 'Legacy tables: DELETED'
\echo 'Associated triggers: REMOVED'
\echo 'Data backup: NONE (as requested)'
\echo ''
\echo '✓ Database cleanup completed successfully!'
\echo ''
\echo 'Next Steps:'
\echo '1. Clean Qdrant vector collections: DELETE collection "vehicles"'
\echo '2. Begin Phase 1: Create abstraction interfaces (IProduct, IProductService)'
\echo '3. Create new multi-tenant PostgreSQL schema (Tenant, ScoringConfig, etc.)'
\echo '============================================================'
