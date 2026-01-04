# CIDS Server Reference

The CIDS server parses and serves files from CIDS archives.

## Overview

The CIDS server handles requests to serve content from CIDS archives:

1. Parses CIDS archive format (path-to-CID mappings)
2. Resolves CIDs to actual content
3. Serves content with appropriate MIME types
4. Provides directory navigation

## Server Parameters

### Direct Server Call

```
/servers/cids?archive={archive_content_or_CID}&path={filepath}
```

**Parameters:**
- `archive` - The CIDS archive content or its CID (required)
- `path` - File path to retrieve (optional, lists files if omitted)

## Archive Format

The server expects plain text archives where each line contains a path and CID separated by whitespace.

For more information about the CIDS format and server implementation, visit [256t.org on GitHub](https://github.com/curtcox/256t.org).

---

[← Back to Index](../index.md) | [Next: Gateway Integration →](gateway-server.md)
