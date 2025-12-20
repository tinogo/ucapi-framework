# Testing Mode - To Be Removed Before Final Release

## Overview
Testing mode has been added to the migration system to allow comprehensive testing without making actual PATCH calls to the Remote. This is a **temporary feature** that should be removed before the final release.

## Files Modified

### 1. `ucapi_framework/migration.py`
- **Line ~57**: Added `testing_mode: bool = False` parameter to `migrate_entities_on_remote()`
- **Line ~76**: Added docstring entry for testing_mode parameter
- **Line ~153**: Added warning log when testing_mode is enabled
- **Line ~246**: Pass testing_mode to `_update_activity_on_remote()`
- **Line ~483**: Added `testing_mode: bool = False` parameter to `_update_activity_on_remote()`
- **Line ~498**: Added docstring entry for testing_mode parameter
- **Lines ~519-527**: Conditional PATCH for main activity (skip if testing_mode)
- **Lines ~555-573**: Conditional PATCH for button mappings (skip if testing_mode)
- **Lines ~588-606**: Conditional PATCH for UI pages (skip if testing_mode)

### 2. `ucapi_framework/setup.py`
- **Line ~73**: Added `migration_testing_mode: bool = False` parameter to `__init__()`
- **Line ~88-90**: Added docstring entry for migration_testing_mode parameter
- **Line ~97**: Store `self.migration_testing_mode`
- **Line ~1195**: Pass `testing_mode=self.migration_testing_mode` to `migrate_entities_on_remote()`

## Removal Checklist

When ready to remove testing mode:

1. **In `ucapi_framework/migration.py`**:
   - [ ] Remove `testing_mode` parameter from `migrate_entities_on_remote()` signature
   - [ ] Remove testing_mode docstring entry
   - [ ] Remove warning log for testing_mode
   - [ ] Remove `testing_mode` argument from `_update_activity_on_remote()` call
   - [ ] Remove `testing_mode` parameter from `_update_activity_on_remote()` signature
   - [ ] Remove testing_mode docstring entry from `_update_activity_on_remote()`
   - [ ] Remove all `if testing_mode:` conditionals and their else blocks
   - [ ] Keep only the actual PATCH call code (remove the testing log branches)

2. **In `ucapi_framework/setup.py`**:
   - [ ] Remove `migration_testing_mode` parameter from `__init__()`
   - [ ] Remove migration_testing_mode docstring entry
   - [ ] Remove `self.migration_testing_mode` attribute assignment
   - [ ] Remove `testing_mode=self.migration_testing_mode` argument from `migrate_entities_on_remote()` call

3. **Testing**:
   - [ ] Run all migration tests to ensure they still pass (they should use mocking instead of testing_mode)
   - [ ] Verify no references to "testing_mode" or "migration_testing_mode" remain in the codebase

4. **Documentation**:
   - [ ] Delete this file (`TESTING_MODE_REMOVAL.md`)

## Usage During Development

To enable testing mode in integration code:

```python
# In your integration's driver main() function
setup_flow = MySetupFlow.create_handler(
    driver,
    discovery=discovery,
    migration_testing_mode=True  # Enable testing mode
)
```

This will execute all migration logic (fetching activities, replacing entity IDs, building payloads) but skip the actual PATCH calls to the Remote.

## Rationale

Testing mode allows developers to:
- Test the complete migration flow without modifying Remote state
- Verify entity ID replacement logic works correctly
- Inspect generated payloads in logs
- Test migration checks and data generation
- Debug issues without affecting production activities

The scope is intentionally narrow - only the PATCH calls are skipped. All other logic executes normally, providing maximum test coverage while preventing side effects.
