# What are CIDs?

CID stands for **Content-addressed ID** - a unique identifier derived from the content itself.

## Content Addressing

Unlike traditional file systems that use names and locations, content addressing identifies data by its actual content:

- **Same content = Same CID**: If two files have identical content, they have the same CID
- **Different content = Different CID**: Even tiny changes produce a completely different CID
- **Verifiable**: You can verify content hasn't been tampered with by recalculating its CID

## How CIDs Work

1. **Content** → Hash function → **CID**
2. The CID is deterministic - the same input always produces the same CID
3. CIDs are typically base64-encoded for safe use in URLs and file systems

Example CID:
```
AAAAABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789AB
```

## Benefits

### Deduplication
Store content once, reference it many times:
- Multiple archives can reference the same content
- Reduces storage requirements
- No need to bundle large files repeatedly

### Integrity
Built-in verification:
- CIDs prove content hasn't changed
- No silent corruption
- Cryptographically secure

### Efficiency
Smart storage:
- Content automatically deduplicated
- Bandwidth savings
- Cache-friendly

## CIDs vs Traditional Files

| Traditional Files | Content-addressed (CIDs) |
|------------------|--------------------------|
| Name-based (`file.txt`) | Content-based (`AAAA...xyz`) |
| Location matters | Content is location-independent |
| Can be modified in place | Immutable - changes create new CID |
| Duplicates waste space | Automatically deduplicated |
| No built-in verification | Content integrity guaranteed |

## Learn More

For more information about CIDs and content-addressing:
- Visit [256t.org on GitHub](https://github.com/curtcox/256t.org)
- See [CIDS Format](cids-format.md) for archive structure
- Read [Content Deduplication](deduplication.md) for benefits

---

[← Back to Index](../index.md) | [Next: CIDS Format →](cids-format.md)
