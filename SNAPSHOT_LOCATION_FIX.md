# Snapshot Location Exists Columns Fix

## Problem
The `exists_local`, `exists_cloud`, and deletion-related columns in the `snapshots` table were not being populated correctly during sync operations in some databases.

The API returns location data as a JSON array of objects:
```json
[
  {"device_id": "d_...", "type": "local"},
  {"device_id": "d_...", "type": "cloud"}
]
```

Some databases had incorrect values (0) for `exists_cloud` and `exists_local` even when the `locations` JSON contained valid data.

## Solution

### 1. Database Version Tracking
Added a `schema_metadata` table to track database schema versions:
- Version 0: Pre-versioning (database may have incorrect snapshot location data)
- Version 1: Snapshot locations fixed and verified
- New databases automatically get version tracking on initialization
- Backfill script sets version to 1 after successful migration

**Files modified:**
- `/var/www/reports.slide.recipes/lib/database.py` - Added `schema_metadata` table and version methods

### 2. Parsing Logic (Already Correct)
The `/var/www/reports.slide.recipes/lib/sync.py` `_parse_snapshot_location_data()` method:
- Iterates through each location object in the array
- Checks the `type` field of each object
- Sets `exists_local = 1` if any location has `type == 'local'`
- Sets `exists_cloud = 1` if any location has `type == 'cloud'`
- This code was already correct and working properly

### 3. Backfill Script (Enhanced)
Updated `/var/www/reports.slide.recipes/backfill_snapshot_locations.py`:
- Parses the `locations` JSON field for all existing snapshots
- Updates the `exists_*` columns with correct values
- Can be run on a single database or all databases
- Supports `--dry-run` mode for testing
- Reports current schema version before processing
- Sets schema version to 1 after successful backfill
- Creates `schema_metadata` table if it doesn't exist

## Usage

### Backfill Existing Records
```bash
# For a specific API key
python3 backfill_snapshot_locations.py YOUR_API_KEY

# For all databases
python3 backfill_snapshot_locations.py

# Dry run to see what would be updated
python3 backfill_snapshot_locations.py YOUR_API_KEY --dry-run
```

### Future Syncs
All future sync operations will automatically populate these columns correctly. No additional action needed.

## Impact
Reports no longer need to parse the `locations` JSON field at runtime. They can directly use:
- `exists_local` - Boolean (1/0) indicating if snapshot exists in local storage
- `exists_cloud` - Boolean (1/0) indicating if snapshot exists in cloud storage
- `exists_deleted` - Boolean (1/0) indicating if snapshot has been deleted
- `exists_deleted_retention` - Boolean (1/0) for retention policy deletions
- `exists_deleted_manual` - Boolean (1/0) for manual deletions
- `exists_deleted_other` - Boolean (1/0) for other deletion types

This improves report generation performance by eliminating JSON parsing overhead.

## Checking Database Version

To check if a database has been migrated:

```bash
# Check a specific database
sqlite3 /var/www/reports.slide.recipes/data/YOUR_HASH.db \
  "SELECT value FROM schema_metadata WHERE key = 'schema_version'"
```

- Version 0 or no result: Database needs migration
- Version 1 or higher: Database has been migrated

## Test Results

**Initial State:**
Database `b3b0f4e34b64a07c.db` had 405 snapshots with incorrect `exists_cloud` and `exists_local` values (both set to 0 despite having valid location data in JSON).

**After Backfill:**
- Database version set to 1
- All 405 snapshots corrected
- Total snapshots: 6,273
- Snapshots with cloud storage: 340 (was 0)
- Snapshots with local storage: 342 (was 0)
- No mismatched records remaining

**All Databases Status:**
All 9 active databases successfully migrated to version 1 with correct snapshot location data.

## Files Modified
1. `/var/www/reports.slide.recipes/lib/database.py` - Added schema_metadata table and version tracking methods
2. `/var/www/reports.slide.recipes/lib/sync.py` - Verified parsing logic is correct
3. `/var/www/reports.slide.recipes/backfill_snapshot_locations.py` - Enhanced with version tracking and validation

## Migration Steps for Other Environments
1. Deploy updated files:
   - `lib/database.py` (with schema_metadata table)
   - `lib/sync.py` (verified correct)
   - `backfill_snapshot_locations.py` (enhanced version)
2. Run the backfill script: `python3 backfill_snapshot_locations.py`
3. Verify all databases are at version 1
4. Future syncs will automatically populate columns correctly

## Summary

This fix accomplishes three key objectives:

1. **Fixed Existing Data**: Ran backfill script on all databases, correcting 405 snapshots in database `b3b0f4e34b64a07c.db`
2. **Verified API Ingest Code**: Confirmed `lib/sync.py` has correct parsing logic that properly populates `exists_cloud` and `exists_local` from API JSON
3. **Added Version Tracking**: Implemented `schema_metadata` table with version tracking so we can identify which databases have been properly migrated (version 0 = pre-migration, version 1 = snapshot locations fixed)

All databases are now at version 1 with correct snapshot location data.

