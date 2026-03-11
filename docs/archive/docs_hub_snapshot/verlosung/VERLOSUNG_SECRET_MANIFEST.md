# Verlosung Secrets Manifest

**Status:** QUARANTINED
**Date:** 2026-01-02
**Location:** `C:\Users\janne\.secrets\.cdb\verlosung\`

The following secret files were removed from the repository and moved to the external quarantine location.

## Files

### client.key
**SHA256:** `92F67B10C4C19CE6443298532B6576401D4FFB715A276EA203EB90C86AF440FF`

### postgres.key
**SHA256:** `210D5B6F0C6074B82220B9C594EE3B56DB1E22CB7DB8A88AB683C33921B9598E`

### postgres.crt
**SHA256:** `111819FDD91273E2141136991C94F919A0C13F4046B9487C417CF497C43F2F34`

### redis.key
**SHA256:** `D9712B762403938141E4C49C2AF81ACFA42E62601CE11FE863583CFBD803C30D`

### redis.crt
**SHA256:** `6BF2680027182F0A323BFDADAF9AD6E216F244F0AF9C26CA8F4353A468E945AA`

### redis.dh
**SHA256:** `95AAE62618925DD00AAF0545451172715C43C729F75EFF3B97F2F2F6A95BD162`

## Instructions
To restore these secrets for local development, copy them from the quarantine location to the appropriate configuration directory (gitignored).
**NEVER COMMIT THESE FILES.**

### ca.crt
Moved to quarantine during Slice E.

### client.crt
Moved to quarantine during Slice E.

## ca.key (2026-01-02)
- sha256: 5E352127701E98AFEB814E065A4DD2857D28F5DD21BD3197A96A14065027DB0C
- quarantined_to: C:\Users\janne\.secrets\.cdb\verlosung\ca.key
- rationale: removed private key material from repo; docs-only + no-secrets policy

