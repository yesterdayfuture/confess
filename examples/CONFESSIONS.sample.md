# CONFESSIONS.md (sample)

This file is what a team repo might accumulate after several AI-assisted pushes.
Copy is illustrative only — real hooks append to `CONFESSIONS.md` at the repo root.

---

## 2026-10-18T09:12:44+00:00 — `7f3a91c2b4e0`

**Files**: src/auth/session.py, src/auth/tokens.py

### What does this code do? (your own words, not a paste of comments)
Issues short-lived JWTs after password login and stores the refresh token hash in Redis.

### If this breaks in production tomorrow, what is the most likely cause?
Clock skew between app and Redis TTL, or the refresh cookie path not matching the API prefix.

### How would you verify it's correct in under 5 minutes?
Hit `/login` then `/refresh` with curl; confirm Redis key appears and expires near the configured TTL.

---

## 2026-10-19T14:03:11+00:00 — `c0ffee12ab34`

**SKIPPED**: hotfix — payment webhook timeout during incident

---

## 2026-10-20T16:00:00+00:00 — `a1b2c3d4e5f6` (MCP-recorded)

### What does this code do?
Adds a healthcheck endpoint that pings the DB pool.

### If this breaks in production tomorrow, what is the most likely cause?
Pool exhausted under load so `/health` returns 500 and the LB drains the instance.

### How would you verify it's correct in under 5 minutes?
`curl localhost:8000/health` before and after stopping Postgres; expect 200 then 503.
