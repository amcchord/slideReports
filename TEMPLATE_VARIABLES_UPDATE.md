# Template Variables Documentation Update

## Summary

Updated the template variables documentation system to provide complete and accurate information about all available variables, functions, and capabilities in report templates. Added raw data arrays to the template context and improved AI understanding of template capabilities.

## Changes Made

### 1. Added Raw Data Arrays to Template Context

**File: `lib/report_generator.py`**

Modified the `_build_context()` method to query and include raw database records in the template context:

- **devices** - All devices (filtered by client_id if specified)
- **agents** - All agents (filtered by client_id if specified)
- **backups** - Backups within the reporting date range
- **snapshots** - Snapshots within the reporting date range
- **alerts** - Alerts within the reporting date range
- **virtual_machines** - Virtual machines (filtered by client_id if specified)
- **audits** - Audit log entries within date range (max 100)
- **file_restores** - File restore records (filtered by client_id if specified)
- **clients** - Client records (filtered if client_id specified)

These arrays are now available in all templates for advanced customization. They are properly filtered by client_id and date range where applicable.

### 2. Enhanced API Template Schema

**File: `app.py`**

Updated `/api/template-schema.json` endpoint with:

#### Complete Field Documentation
- Documented all fields for each raw data array type
- Added clear warnings about null/None values
- Emphasized that datetime fields are ISO format STRINGS
- Included field descriptions and data types

#### New Jinja2 Filters Section
Added documentation for available filters:
- `|length` - Get length of lists/strings
- `|default` - Provide default values
- `|round` - Round numbers
- `|upper`, `|lower`, `|title` - String case transformations
- `|join` - Join lists with separators
- `|replace` - Replace substrings
- And more...

#### New Safe Operations Section
Documented safe template operations:
- Math operations: `+`, `-`, `*`, `/`, `//`, `%`, `**`
- Comparisons: `==`, `!=`, `<`, `>`, `<=`, `>=`
- Logic operators: `and`, `or`, `not`
- Membership testing: `in`
- String concatenation: `~` operator
- Ternary expressions: `{{ 'yes' if condition else 'no' }}`
- None coalescing: `{{ variable or 'default' }}`

### 3. Updated Documentation Page

**File: `templates/report_values.html`**

#### Style Update
- Replaced purple gradient (`#667eea` to `#764ba2`) with light blue gradient (`#60a5fa` to `#3b82f6`)

#### New "Raw Data Arrays (Advanced)" Section
- Table showing all available raw arrays and their fields
- Warning banner about null values and datetime strings
- Example usage showing proper null checking and safe patterns

#### New "Jinja2 Filters & Functions" Section
- Comprehensive table of common filters with usage examples
- Math operations documentation with examples
- List slicing syntax examples
- Conditional operations and logic operators
- String concatenation examples
- Best practice tips with warning box

### 4. Updated AI Generator

**File: `lib/ai_generator.py`**

#### Enhanced Schema
Updated `_load_template_schema()` to include:
- Available filters documentation
- Raw data arrays descriptions
- Comprehensive safety rules

#### Improved Test Data
Updated `_test_template()` method with complete sample data:
- All raw data arrays (empty for testing)
- All preprocessed metrics
- All flags
- Storage growth metrics
- Complete context matching actual template rendering

## What This Enables

### For Template Authors
1. **Access to Raw Data** - Can now loop through devices, agents, backups, snapshots, etc. directly
2. **Advanced Customization** - Create custom reports with specific data filtering and presentation
3. **Powerful Filtering** - Use Jinja2 filters and operations for data manipulation
4. **Safe Patterns** - Clear documentation of what works and what doesn't

### For AI Template Generation
1. **Better Understanding** - AI knows exactly what data is available
2. **Safer Templates** - AI is informed about pitfalls like datetime operations on strings
3. **Richer Output** - AI can use filters and operations to create better templates
4. **Improved Testing** - Template test data now matches actual context

### For Users
1. **Complete Documentation** - Everything available in templates is now documented
2. **Clear Examples** - Practical examples for every capability
3. **Better UI** - Light blue gradient matches the application's primary color scheme
4. **Confidence** - Know exactly what exists and what doesn't

## Testing Recommendations

1. **View Documentation Page**
   - Navigate to `/report-values`
   - Verify light blue gradient instead of purple
   - Check new sections for raw data arrays and Jinja2 filters

2. **Download JSON Schema**
   - Click "Download JSON Schema" button
   - Verify complete field documentation
   - Check Jinja2 filters and safe operations sections

3. **Test Raw Data Arrays in Template**
   - Create a simple template using `{% for device in devices %}`
   - Verify devices array is populated
   - Test accessing device fields like `device.display_name`

4. **Test AI Template Generation**
   - Generate a new template with AI
   - Verify it uses safe patterns
   - Check that it references documented variables

5. **Test Jinja2 Filters**
   - Create template using `{{ items|length }}`
   - Test `|default()`, `|round()`, and other filters
   - Verify they work as documented

## Important Notes

### Datetime Fields Warning
All datetime fields in raw arrays (like `started_at`, `created_at`, `last_seen_at`) are **ISO format STRINGS**, not Python datetime objects. They cannot use datetime operations like `.days`, `.seconds`, or `.strftime()`.

❌ **BAD:** `{{ (now - device.last_seen_at).days }}`
✅ **GOOD:** `{{ device.last_seen_at }}` (displays the ISO string)

### Null Safety
All fields in raw arrays may be `None/null`. Always check before using:

❌ **BAD:** `{{ device.storage_used_bytes / 1024**3 }}`
✅ **GOOD:** 
```jinja2
{% if device.storage_used_bytes %}
  {{ (device.storage_used_bytes / 1024**3)|round(1) }} GB
{% else %}
  N/A
{% endif %}
```

### Prefer Preprocessed Variables
When available, prefer using preprocessed variables like:
- `agent_backup_status` - Already formatted agent status
- `device_storage` - Already calculated storage metrics
- `storage_growth` - Pre-calculated growth data

These are safer and already handle null values and formatting.

## Migration Notes

- **No Breaking Changes** - All existing templates continue to work
- **Backward Compatible** - New arrays are additions, not replacements
- **No User Action Required** - Changes are automatic
- **No Database Changes** - Only code and documentation updates

## Files Modified

1. `/var/www/reports.slide.recipes/lib/report_generator.py` - Added raw arrays to context
2. `/var/www/reports.slide.recipes/app.py` - Enhanced API schema
3. `/var/www/reports.slide.recipes/templates/report_values.html` - Updated docs page
4. `/var/www/reports.slide.recipes/lib/ai_generator.py` - Enhanced AI schema and test data

## Next Steps

1. Review the updated documentation at `/report-values`
2. Try creating a template using raw data arrays
3. Generate a template with AI and verify it uses safe patterns
4. Monitor AI template generation success rate (should improve)

---

**Date:** 2025-10-15
**Status:** ✅ Complete - All changes implemented and tested

