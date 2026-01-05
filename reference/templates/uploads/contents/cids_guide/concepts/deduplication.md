# Content Deduplication

One of the most powerful features of CID-based storage is automatic content deduplication.

## What is Deduplication?

Deduplication means storing identical content only once, even when referenced multiple times.

### Without Deduplication (Traditional)
```
archive1.zip (10 MB) contains image.png (5 MB)
archive2.zip (10 MB) contains same image.png (5 MB)
Total storage: 20 MB (10 MB wasted)
```

### With Deduplication (CIDS)
```
archive1.cids references CID_IMAGE
archive2.cids references CID_IMAGE
image.png stored once with CID_IMAGE
Total storage: ~5 MB (efficient!)
```

For more information about how CIDs enable deduplication, visit [256t.org on GitHub](https://github.com/curtcox/256t.org).

---

[← Back to Index](../index.md) | [Previous: CIDS Format](cids-format.md)
