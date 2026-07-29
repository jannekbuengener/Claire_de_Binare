# CDB Issue Comment Patterns

Use short issue-ready comments after the gate verdict is stable.

## PASS WITH EXPLICIT LIMITS
```md
Decision surface: <surface>
Claim under review: <claim>
Verdict: PASS WITH EXPLICIT LIMITS

Why:
- Direct evidence: <artifact>
- Limits: <explicit residual>
- Not upgraded: <surface that remains unchanged>

Next move:
- <one concrete action>
```

## NON-BLOCKING GAP
```md
Decision surface: <surface>
Claim under review: <claim>
Verdict: NON-BLOCKING GAP

Why:
- The core claim is supportable for this surface.
- Residual gap: <explicit gap>
- This does not block: <named surface>

Next move:
- <one concrete action>
```

## BLOCKED
```md
Decision surface: <surface>
Claim under review: <claim>
Verdict: BLOCKED

Why:
- Missing or ambiguous proof: <artifact or contract gap>
- Blocking system: <surface>
- No fake PASS issued.

Next move:
- <one concrete action>
```
