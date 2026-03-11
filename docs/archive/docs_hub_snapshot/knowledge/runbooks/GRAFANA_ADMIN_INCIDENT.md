# Runbook: Grafana Admin Password Incident

**Severity:** HIGH
**Expected Duration:** 5-10 minutes
**Prerequisites:** Access to Grafana UI + Password Manager

---

## When to Use This Runbook

Execute this runbook when **any** of the following occur:

1. **Grafana admin password suspected leaked**
   - Found in logs, screenshots, or shared documents
   - Accidentally committed to git (even if removed)
   - Exposed via screen share or recording

2. **Grafana admin account compromise suspected**
   - Unauthorized dashboards created/modified
   - Unexpected Grafana users added
   - Suspicious API token activity

3. **Grafana admin login from unknown location**
   - IP address not recognized
   - Login at unusual time
   - Multiple failed login attempts

4. **Periodic security rotation** (if mandated by policy)
   - Currently: Manual only
   - Future: May be scheduled (quarterly/annually)

---

## Why This is Manual (Not Auto-Rotated)

Grafana admin password is stored in:
- **Browser saved passwords** (auto-fill on login)
- **Password manager** (1Password, Bitwarden, etc.)

**Problem:** Tool cannot reliably update these external stores.

**Solution:** Manual rotation via UI + password manager update.

---

## Incident Response Steps

### Step 1: Change Password in Grafana UI (2 minutes)

1. **Log in to Grafana:**
   ```
   http://localhost:3000
   User: admin
   Password: <current password from password manager>
   ```

2. **Navigate to Admin Settings:**
   - Click profile icon (bottom left)
   - Select "Profile" or "Preferences"
   - Go to "Change Password" section

3. **Generate New Password:**
   - **Option A (Recommended):** Use password manager to generate strong password (20+ chars)
   - **Option B:** Use `openssl rand -base64 24` and copy output

4. **Change Password:**
   - Enter current password
   - Enter new password (twice)
   - Click "Change Password"
   - **Confirm:** You are logged out immediately

5. **Verify New Password:**
   - Log in again with new password
   - **Confirm:** Old password rejected

---

### Step 2: Update Password Manager Entry (1 minute)

**If using password manager (1Password, Bitwarden, etc.):**
1. Open password manager
2. Find entry: "Grafana Admin (CDB)"
3. Update password field with new password
4. Save entry
5. **Verify:** Auto-fill works on next login

**If using browser saved passwords:**
1. Navigate to `chrome://settings/passwords` (or equivalent)
2. Search for `localhost:3000` or `grafana`
3. Update password
4. Save

---

### Step 3: Update Secrets File (Optional - For Consistency)

**Why:** `GRAFANA_ADMIN_PASSWORD` file in `$SECRETS_PATH` should match actual password.

**How:**
```powershell
# Navigate to secrets directory
cd C:\Users\janne\Documents\.secrets\.cdb

# Update file (NO newline at end)
$newPassword = Read-Host -AsSecureString "Enter new Grafana admin password"
$plain = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($newPassword)
)
[System.IO.File]::WriteAllText(".\GRAFANA_ADMIN_PASSWORD", $plain)

# Verify
Get-Content .\GRAFANA_ADMIN_PASSWORD -Raw
```

**Note:** This file is **reference only** - not loaded by stack_up.ps1 for Grafana admin.

---

### Step 4: Restart Grafana (If Required)

**Usually NOT required** (password change takes effect immediately).

**If needed:**
```powershell
cd D:\Dev\Workspaces\Repos\Claire_de_Binare
docker compose -f infrastructure\compose\base.yml restart cdb_grafana
```

---

### Step 5: Verify and Audit (2 minutes)

#### Test Login
```powershell
# Test new password works
curl -u admin:<new-password> http://localhost:3000/api/health
# Expected: {"database":"ok","version":"..."}

# Test old password rejected
curl -u admin:<old-password> http://localhost:3000/api/health
# Expected: 401 Unauthorized
```

#### Audit Grafana
1. **Check Users:**
   - Navigate to Configuration → Users
   - Verify no unauthorized users
   - Disable/delete suspicious accounts

2. **Check API Tokens:**
   - Navigate to Configuration → API Keys
   - Verify no unexpected tokens
   - Revoke suspicious tokens

3. **Check Dashboards:**
   - Review recent dashboard changes (Audit log)
   - Verify no unauthorized modifications

---

## Post-Incident Actions

### Immediate (Within 1 hour)
- [ ] Document incident in `knowledge/incidents/YYYY-MM-DD-grafana-admin.md`
- [ ] Notify team (if applicable)
- [ ] Review Grafana access logs for unauthorized activity

### Short-Term (Within 1 week)
- [ ] Review other admin credentials (if pattern suspected)
- [ ] Consider enabling 2FA for Grafana (future enhancement)
- [ ] Update SECRETS_POLICY.md if new risks identified

### Long-Term (Within 1 month)
- [ ] Review secret storage architecture (consider Vault/SSO)
- [ ] Audit all manual secrets (API keys, etc.)

---

## Break-Glass Admin (Future Enhancement)

**Status:** Not yet implemented

**Proposal:** Create second Grafana admin account:
- Username: `break_glass_admin`
- Stored in sealed envelope / encrypted file
- Only used when primary admin locked out
- Rotation: Manual, same as primary admin

**Implementation:** Issue #TBD

---

## References

- **Secret Rotation Policy:** `knowledge/governance/SECRET_ROTATION_POLICY.md`
- **General Secrets Policy:** `governance/SECRETS_POLICY.md`
- **Grafana Official Docs:** https://grafana.com/docs/grafana/latest/administration/user-management/

---

## Troubleshooting

### "Cannot log in with new password"
- **Cause:** Browser cached old password
- **Fix:** Clear browser cache for `localhost:3000`, try incognito mode

### "Old password still works"
- **Cause:** Grafana session not invalidated
- **Fix:** Restart Grafana: `docker compose restart cdb_grafana`

### "Password file doesn't match actual password"
- **Cause:** File is reference only, not used by Grafana
- **Fix:** Update file (Step 3) or ignore (file not critical)

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)
