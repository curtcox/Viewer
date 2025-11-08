# Boot CID Import Feature

## Overview

The Viewer application now supports importing a CID (Content Identifier) on startup. This feature allows you to automatically import configuration data (aliases, servers, variables, secrets, etc.) when the application starts.

## Usage

To import a CID on startup, use the `--boot-cid` parameter when running the application:

```bash
python main.py --boot-cid <CID>
```

### Example

```bash
python main.py --boot-cid bafkreigwmhxwpimunvw5lp7fffhkbhytwdw77zqpibxsrq3xnvqdx4smwu
```

## Requirements

Before using the boot CID import feature, ensure:

1. **All CID files are in the `cids` directory**: The boot CID and all CIDs it references must exist as files in the `cids` directory.

2. **CID filenames match their content hash**: Each file in the `cids` directory must be named exactly as the CID of its content.

3. **All dependencies are present**: The boot CID may reference other CIDs in its payload. All referenced CIDs must be available in the database before the import can proceed.

## How It Works

When you provide a `--boot-cid` parameter:

1. **CID Directory Loading**: The application first loads all CID files from the `cids` directory into the database (this happens automatically on every startup).

2. **Dependency Verification**: The application checks that all CIDs referenced by the boot CID are present in the database.

3. **Import or Exit**:
   - If any referenced CIDs are missing, the application lists them and exits with an error.
   - If all dependencies are present, the application imports the boot CID using the same mechanism as the web-based `/import` page.

4. **Application Start**: After successful import, the application starts normally.

## Error Messages

The feature provides helpful error messages for common issues:

### Missing Boot CID

```
Boot CID import failed:
Boot CID not found in database: <CID>
Make sure the CID file exists in the cids directory.
```

**Solution**: Add the CID file to the `cids` directory.

### Missing Dependencies

```
Boot CID import failed: The following referenced CIDs are missing from the database:
  /<CID1>
  /<CID2>

Please ensure all required CID files are present in the cids directory before starting.
```

**Solution**: Add all missing CID files to the `cids` directory.

### Invalid CID Format

```
Boot CID import failed:
Invalid CID format: <invalid-cid>
```

**Solution**: Provide a valid CID string.

### Invalid JSON Content

```
Boot CID import failed:
Boot CID content is not valid JSON: <CID>
Error: <JSON parse error>
```

**Solution**: Ensure the CID file contains valid JSON content.

## Testing

To test the boot CID import functionality, you can run the manual test script:

```bash
python test_boot_cid_manual.py
```

Or run the full test suite:

```bash
pytest tests/test_boot_cid_importer.py -v
```

## Implementation Details

The boot CID import feature consists of:

- `boot_cid_importer.py`: Core import logic and dependency verification
- `main.py`: Command-line argument handling
- `tests/test_boot_cid_importer.py`: Comprehensive test suite

The import uses the same underlying mechanism as the web-based `/import` page, ensuring consistency between manual and automated imports.
