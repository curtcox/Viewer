# Creating CIDS Archives

A step-by-step guide to creating your own CIDS archives.

## Quick Start

### 1. Create Content Files

Create the content files you want to include in your archive.

### 2. Store Content and Get CIDs

Store each file to get its CID.

### 3. Create CIDS Archive

Create a text file mapping paths to CIDs:

```
readme.md CID_README.md
docs/api.md CID_API.md
style.css CID_STYLE.css
```

### 4. Access via Gateway

```
/gateway/cids/{archive_cid}/readme.md
```

For more information about creating and managing CIDS archives, visit [256t.org on GitHub](https://github.com/curtcox/256t.org).

---

[← Back to Index](../index.md) | [Next: Linking Guide →](links.md)
