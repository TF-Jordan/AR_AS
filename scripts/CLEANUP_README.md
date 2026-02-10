# Vehicle Data Cleanup - Phase 0

## Overview

This directory contains scripts to completely remove the vehicle domain from the database and vector store. These scripts are part of **Phase 0** of the multi-tenant RaaS transformation.

## ⚠️ DANGER - NO BACKUP

**CRITICAL WARNING**: These scripts will **permanently delete** all vehicle data without creating backups. This action is **IRREVERSIBLE** and was confirmed by the user.

## Scripts

### 1. `cleanup_vehicle_data.sql`

**Purpose**: Remove all vehicle-related tables from PostgreSQL database.

**What it deletes**:
- Vehicle domain tables (vehicles, vehicle_review, vehicle_amenity, etc.)
- Reference tables (vehicle_make, vehicle_model, fuel_type, etc.)
- Party and ownership tables
- Legacy tables (personnes, comments)
- Associated triggers and indexes

**Usage**:

```bash
# Connect to PostgreSQL and run the script
psql -h localhost -U postgres -d ar_as_db -f cleanup_vehicle_data.sql

# Or using Docker Compose
docker compose exec postgres psql -U postgres -d ar_as_db -f /path/to/cleanup_vehicle_data.sql
```

**Interactive Confirmation**: The script will prompt for confirmation before proceeding.

### 2. `cleanup_qdrant_vehicles.py`

**Purpose**: Remove the 'vehicles' collection from Qdrant vector database.

**What it deletes**:
- The entire 'vehicles' collection
- All vectors stored in that collection
- Collection metadata

**Usage**:

```bash
# Ensure Qdrant is running
docker compose up -d qdrant

# Set environment variables (if not using defaults)
export QDRANT_HOST=localhost
export QDRANT_PORT=6333

# Run the cleanup script
python scripts/cleanup_qdrant_vehicles.py

# Or from the scripts directory
cd scripts
./cleanup_qdrant_vehicles.py
```

**Interactive Confirmation**: The script will require you to type 'DELETE' to confirm.

## Execution Order

For complete cleanup, execute in this order:

1. **First**: Clean Qdrant (optional to do first, but recommended)
   ```bash
   python scripts/cleanup_qdrant_vehicles.py
   ```

2. **Second**: Clean PostgreSQL
   ```bash
   psql -h localhost -U postgres -d ar_as_db -f scripts/cleanup_vehicle_data.sql
   ```

3. **Verify**: Check that everything is gone
   ```bash
   # Check PostgreSQL tables
   psql -h localhost -U postgres -d ar_as_db -c "\dt"

   # Check Qdrant collections
   curl http://localhost:6333/collections
   ```

## What Remains After Cleanup

After running these scripts, the database will contain:

- PostgreSQL extensions (uuid-ossp, etc.)
- The `update_updated_at_column()` function (can be reused)
- Keycloak schema (in separate schema 'keycloak')

**All vehicle data will be permanently removed.**

## Next Steps After Cleanup

Once cleanup is complete, proceed with Phase 1:

1. Create abstraction interfaces (`IProduct`, `IProductService`)
2. Create new multi-tenant PostgreSQL schema:
   - `tenants` table
   - `scoring_configs` table with dynamic JSON criteria
   - `products` table (generic, not vehicle-specific)
3. Set up Alembic migrations for new schema
4. Begin implementing multi-tenant architecture

## Rollback

**There is NO rollback mechanism.** If you need to restore data:

1. You must have created a manual backup before running these scripts
2. Restore from that backup using `pg_restore` or `psql`

Since no backup was requested, **data loss is permanent**.

## Confirmation Required

Both scripts include safety confirmation prompts:

- **SQL Script**: Prompts with "Continue? (yes/no)"
- **Python Script**: Requires typing "DELETE" to confirm

This prevents accidental execution.

## Verification

Both scripts include verification steps that:

- List remaining tables/collections
- Confirm successful deletion
- Provide summary of what was removed

## Troubleshooting

### PostgreSQL Connection Issues

```bash
# Check if PostgreSQL is running
docker compose ps postgres

# Check connection
psql -h localhost -U postgres -d ar_as_db -c "SELECT version();"
```

### Qdrant Connection Issues

```bash
# Check if Qdrant is running
docker compose ps qdrant

# Check health
curl http://localhost:6333/healthz

# List collections
curl http://localhost:6333/collections
```

### Permission Denied

```bash
# Make Python script executable
chmod +x scripts/cleanup_qdrant_vehicles.py

# Run with python directly if needed
python3 scripts/cleanup_qdrant_vehicles.py
```

## Script Safety Features

1. **Interactive Confirmation**: Both scripts require explicit confirmation
2. **Existence Checks**: Scripts check if data exists before attempting deletion
3. **Verification**: Post-cleanup verification to confirm success
4. **Clear Warnings**: Multiple warnings about irreversible operations
5. **Detailed Output**: Step-by-step progress reporting

## Related Documentation

- **Phase 0 Audit**: `PHASE0_AUDIT_VEHICLE_DEPENDENCIES.md`
- **Transformation Plan**: `TRANSFORMATION_MULTI_TENANT.md`
- **Workflow Details**: `WORKFLOW_RECOMMANDATION_MULTI_TENANT.md`

## Questions?

If you're unsure about running these scripts, review:

1. The transformation plan to understand the broader context
2. The audit document to see what will be affected
3. Confirm with stakeholders that data loss is acceptable

**Remember: Once executed, this cannot be undone without a backup.**
