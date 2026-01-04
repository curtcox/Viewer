# CIDS Archive Guide

Welcome to the CIDS (Content-addressed ID Storage) documentation! This CIDS archive serves as both a template and a live example of what you can do with CIDS files.

## What is this?

This file is a CIDS archive that contains multiple pages of documentation. Unlike HRX which bundles content inline, CIDS references content by Content-addressed IDs (CIDs). You can:

- **Browse it** via the CIDS gateway at `/gateway/cids/{CID}/`
- **Use it as a template** when uploading new CIDS archives
- **Learn from it** about CIDs, content addressing, and deduplication

## Navigation

### Core Concepts

Understanding CIDS and content-addressing:

- [What are CIDs?](concepts/what-are-cids.md) - Content-addressed IDs explained
- [CIDS Format](concepts/cids-format.md) - Archive file structure
- [Content Deduplication](concepts/deduplication.md) - Benefits of CID-based storage

### Reference Guides

Deep dives into the CIDS implementation:

- [CIDS Server](reference/cids-server.md) - How this archive is served
- [Gateway Integration](reference/gateway-server.md) - How gateway routing works
- [256t.org Project](reference/256t-project.md) - More about CID implementation

### Examples

- [Creating Archives](examples/creating-archives.md) - How to build CIDS files
- [Linking Guide](examples/links.md) - How to link between app sections

---

> **Tip:** Click any link above to navigate within this archive. The CIDS gateway automatically rewrites relative links to work correctly.
