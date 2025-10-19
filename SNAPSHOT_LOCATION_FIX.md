# Snapshot Location Exists Columns Fix

## Problem
The `exists_local`, `exists_cloud`, and deletion-related columns in the `snapshots` table were not being populated correctly during sync operations. 

The API returns location data as a JSON array of objects:
```json
[
  {"device_id": "d_...", "type": "local"},
  {"device_id": "d_...", "type": "cloud"}
]
```

However, the sync code was incorrectly checking `if 'local' in locations` (checking if a string is in the list), when it should have been iterating through the list and checking each object's `type` field.

## Solution

### 1. Fixed Parsing Logic
Updated `/var/www/reports.slide.recipes/lib/sync.py` - the `_parse_snapshot_location_data()` method now:
- Iterates through each location object in the array
- Checks the `type` field of each object
- Sets `exists_local = 1` if any location has `type == 'local'`
- Sets `exists_cloud = 1` if any location has `type == 'cloud'`

### 2. Backfill Script
Created `/var/www/reports.slide.recipes/backfill_snapshot_locations.py` to update existing records:
- Parses the `locations` JSON field for all existing snapshots
- Updates the `exists_*` columns with correct values
- Can be run on a single database or all databases
- Supports `--dry-run` mode for testing

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

## Test Results
Tested on database `99f2d88118f4f279.db` (API key: `tk_4xgc378i7hfe_...`):
- Total snapshots: 6,349
- Records updated: 352
- Snapshots with local storage: 289
- Snapshots with cloud storage: 288
- Deleted snapshots: 5,997

All parsing tests passed for various scenarios:
- ✅ Both local and cloud locations
- ✅ Local only
- ✅ Cloud only
- ✅ Deleted by retention policy
- ✅ Manually deleted

## Files Modified
1. `/var/www/reports.slide.recipes/lib/sync.py` - Fixed parsing logic
2. `/var/www/reports.slide.recipes/backfill_snapshot_locations.py` - New backfill script

## Migration Steps for Other Environments
1. Deploy the updated `lib/sync.py` file
2. Run the backfill script: `python3 backfill_snapshot_locations.py`
3. Future syncs will automatically populate columns correctly

