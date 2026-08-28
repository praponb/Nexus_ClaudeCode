# Asset Inventory — security session, 2026-08-28

What happened, why, and how to operate what came out of it.

The session started with "I lost my admin password" and ended with
`inventory.praponb.com` publicly reachable and hardened. The password turned out
not to be lost; looking for it surfaced everything else.

**Start here:** [Outstanding actions](#outstanding-actions) — 2FA enrolment is
unfinished, which currently blocks admin sign-in.

---

## Part 1 — What happened

Four commits, in order.

### `91bb4ae` — restore production settings, make rate limiting real

The password was never lost. the recorded `admin` password still verified against
the database; the screenshot showed 8 characters typed against an 11-character
password. (That password has since been rotated and is deliberately not
reproduced here — retired credentials get reused elsewhere, and git history is
permanent.) There is no account lockout in this app, so a wrong password never
locks anyone out permanently.

Checking for a lockout is what surfaced the rest:

**The live stack was running `config.settings.local`** — `DEBUG=True`,
non-Secure session and CSRF cookies, no SSL redirect. The 2026-08-03 hardening
had been undone because root `.env` was reverted to local dev values. `.env` is
gitignored, so **that revert left no trace in git**. Cloudflare Access was the
only thing limiting exposure at the time.

`compose.yaml` also hardcoded `APP_ENV: local` and `target: dev` on the three
Django services, so they could never follow `.env` at all. Both are now
interpolated, making prod/dev a single `.env` toggle.

Three separate rate-limiting failures, each of which alone made the limit
useless:

| Problem | Why it mattered |
|---|---|
| `login: 1000/minute` in `base.py` | A dev ceiling copied into the shared base — which also made `local.py`/`test.py` overriding it to the *same* value look like a no-op. Now `10/minute`. |
| No `CACHES` setting at all | DRF throttle counters sat in per-process `LocMemCache`. Under `gunicorn --workers 3` that silently **tripled** every rate and reset it on each deploy. Now Redis db 3. |
| `X-Forwarded-For` trusted for identity | DRF's `get_ident` returns the *whole* XFF header when `NUM_PROXIES` is unset, and that header is caller-supplied — **rotating it gave a fresh bucket per request**, defeating the limit outright. |

That last one had a second edge: the same unvalidated value was written to
`AuditEvent.ip_address`, a PostgreSQL `inet` column, so
`X-Forwarded-For: <junk>` on a failed login raised a `DataError` — an
**unauthenticated 500**. [`apps/core/client_ip.py`](backend/apps/core/client_ip.py)
now resolves one explicitly trusted header (`CF-Connecting-IP`, which Cloudflare
overwrites), then `REMOTE_ADDR`, validates the result, and never trusts XFF.

Verified live: 13 logins each with a different XFF still cut off at exactly 10.

### `1847311` — repair the quality gates

Three things meant the gates couldn't be trusted:

- **The dev image never contained ruff/mypy/pytest.** `dev` is a
  `[project.optional-dependencies]` *extra*, and a bare `uv sync` skips extras,
  so `scripts/check.sh` in its default mode always failed with "ruff: not found".
- **`check.sh` couldn't run against a production-target stack** — it only
  `exec`'d into the running backend. It now detects missing tools and falls back
  to a one-off dev-stage container. It mounts at `/w`, **not** `/app`: the image
  keeps its virtualenv at `/app/.venv`, and mounting over it would hide the very
  tools being run.
- **Four `agentic_builder` tests failed on any machine exporting
  `MODEL_PROVIDER`.** `Settings(_env_file=None)` disables the dotenv file but
  **not** `os.environ`, so pydantic-settings still read the shell — and
  CLAUDE.md's own documented `MODEL_PROVIDER=fake pytest` was exactly what broke
  them. An autouse `isolate_settings_env` fixture now clears the relevant vars.

### `eff6876` — prepare to be publicly reachable

Removing Cloudflare Access makes the Django login the only gate, so this landed
first.

**A new `viewer` role**, because no existing role fit a public demo:

| Role | Why it didn't fit |
|---|---|
| `auditor` | Grants `audit.read`, and audit rows store client IPs |
| `asset_manager` | Grants write — visitors could vandalise the 100k demo rows |
| `employee` | Not a global reader, so with no department scopes it sees nothing |

`viewer` is read-only *by omission*: `ASSET_WRITE_ROLES` and `FINANCE_ROLES`
already exclude it, so no new permission checks were needed.

**The audit log was purged** — 365 rows holding 7 distinct IPs, including real
public addresses (`171.99.154.126` ×35 and two others). Deleting is chain-safe
because `verify_chain()` walks from an empty `prev_hash`, so an empty table
verifies; **editing rows in place would have broken the chain**.

Also: `/api/v1/schema/` moved from `AllowAny` to authenticated (an anonymous
OpenAPI dump hands out a map of every endpoint); app ports bound to `127.0.0.1`;
Postgres and Redis no longer published at all; passwords rotated to unique
24-character values; and the first backups ever taken, with a restore rehearsed
into a scratch database (100,213 assets, zero errors).

Django admin needed no action — the tunnel only routes `^/api/.*` to the
backend, so `/django-admin/` lands on the Nuxt frontend and 404s.

### `744c5c0` — per-account lockout and TOTP

With Access gone, `LoginThrottle` was the only defence — and it keys on **client
IP**, so an attacker spread across N addresses got N × the per-IP budget against
one account, entirely unbounded per-account.

**Per-account lockout** ([`apps/core/login_guard.py`](backend/apps/core/login_guard.py)):
failed sign-ins counted per username in Redis, refused past a threshold
regardless of source address. Failures only, cleared on success. Attempts on
*unknown* usernames are counted too, so the lockout can't be used to discover
which accounts exist.

**TOTP for privileged roles** ([`apps/accounts/mfa.py`](backend/apps/accounts/mfa.py)):
the flow never calls `django.contrib.auth.login` until the second factor is
satisfied — between steps the caller holds only an unauthenticated session with
a pending user id and a 5-minute deadline, so a correct password alone grants
nothing.

Built on **pyotp**, not django-axes/django-otp: pyotp is pure Python with no
framework coupling. django-axes 8.3.1 declares support only through **Django
6.0**, and this project runs **6.1**.

Replay protection records the time-step that *actually matched*, not "now" — a
TOTP code stays valid for a whole step plus drift, so keying on "now" would have
wrongly rejected a legitimate newer code in the same window while still needing
to refuse a replayed one.

---

## Two incidents

Recorded because they are the ones worth not repeating.

### A ~3-minute outage I caused

Binding Postgres to `127.0.0.1:5432` **collided with Homebrew PostgreSQL**,
which already held that port. The old `0.0.0.0:5432` publish had silently
coexisted with it; an explicit loopback bind does not.

It went unnoticed for minutes because the autostart watchdog
(`com.nexus.inventory-autostart.plist`, `StartInterval 300`) runs
`docker compose up -d` **every 5 minutes**. It picked up the half-finished
compose edit, failed to bind, and left three containers in `Created`.

> **Lesson:** editing `compose.yaml` triggers an unattended recreate within 5
> minutes. Check `~/Library/Logs/inventory-stack-autostart.log` after any edit.

The fix — not publishing Postgres at all — is also the more secure outcome.
Nothing on the host needs it: the app reaches Postgres over the compose network
and `backup.sh` goes through `docker compose exec`.

### A 520 I misjudged

Right after the Access app was deleted, `/` returned a **520**. I called it a
one-off. **That call was wrong** — it recurred on the next burst. Only after
~130 further requests (including 20 parallel GETs and a 30-POST burst) with zero
errors, and with no matching entries in either the origin or `cloudflared` logs,
was "Cloudflare edge propagation settling" actually supported.

> If 520s recur **outside** a config change, that conclusion needs revisiting.
> `/Library/Logs/com.cloudflare.cloudflared.err.log` is sparse and may log
> nothing for an edge-side 520.

---

## Part 2 — Operations runbook

### Current state

- **Public:** <https://inventory.praponb.com> — open to anyone, no Cloudflare Access.
- **Ports:** backend and frontend bound to `127.0.0.1`; Postgres and Redis not
  published. Nothing on the LAN can bypass Cloudflare.
- **Settings:** `config.settings.production` — DEBUG off, HSTS, Secure cookies,
  `X-Frame-Options: DENY`.
- **Backups:** daily via `com.praponb.inventory.backup` LaunchAgent, 14 kept.

### Accounts

| Username | Role | Active | Notes |
|---|---|:--:|---|
| `demo` | `viewer` | yes | Public. Read-only across all 100,213 assets |
| `praponb` | `system_admin` | yes | Renamed from `admin`. **Requires TOTP** |
| `manager`, `deptmgr`, `operator`, `employee`, `auditor` | various | no | Deactivated — unused attack surface |

`viewer` can read assets, search, dashboard and export. It **cannot** write,
see finance fields, read the audit log, or reach user admin.

### Credentials

- **Publishable:** `demo` / `PublicDemo2026!`
- **Private:** in `~/inventory-credentials-20260828.txt` (mode `600`).
  Deliberately **not** recorded here — anything committed persists in git
  history forever. Move it into a password manager and delete the file.

### Common operations

```bash
# Unlock an account locked by failed attempts
docker compose exec backend python -c "import django; django.setup(); \
  from apps.core.login_guard import reset; reset('praponb')"

# Back up now (also runs daily via LaunchAgent)
./scripts/backup.sh

# Quality gates — falls back to a dev-stage container automatically,
# because the deployed image is production and has no ruff/mypy/pytest
./scripts/check.sh

# Reactivate a deactivated account
docker compose exec backend python -c "import django; django.setup(); \
  from django.contrib.auth import get_user_model; U=get_user_model(); \
  u=U.objects.get(username='manager'); u.is_active=True; u.save()"

# Ad-hoc database access (Postgres is not published to the host)
docker compose exec postgres psql -U asset_inventory -d asset_inventory
```

**If the site is unreachable**, in order:

1. `curl https://inventory.praponb.com/api/v1/health/ready/` — bypasses nothing
   now, but a non-200 means the stack is down.
2. `docker info` — if this fails, Docker Desktop is dead. This is the single
   most likely cause of a 502. `open -a Docker`, then `docker compose up -d`.
3. `tail ~/Library/Logs/inventory-stack-autostart.log` — watchdog history.
4. `pgrep -fl cloudflared` — only if the origin is confirmed healthy.

A 502 with Cloudflare "Working" / Host "Error" always means the origin.

### Security posture

| Control | Enforced in | Tuning knob |
|---|---|---|
| Per-IP login rate | `LoginThrottle` | `DEFAULT_THROTTLE_RATES["login"]` (10/min) |
| Per-account lockout | `apps/core/login_guard.py` | `LOGIN_LOCKOUT_THRESHOLD` (10), `LOGIN_LOCKOUT_WINDOW_SECONDS` (900), `LOGIN_LOCKOUT_EXEMPT_USERNAMES` (`demo`) |
| TOTP second factor | `apps/accounts/mfa.py` | `MFA_REQUIRED_ROLES` (`system_admin`), `MFA_ISSUER` |
| Second-factor rate | `MfaThrottle` | `DEFAULT_THROTTLE_RATES["mfa"]` (10/min) |
| Search / import-export rate | `SearchThrottle`, `ImportExportThrottle` | `"search"` (120/min), `"import_export"` (60/hr) |
| Trusted client IP | `apps/core/client_ip.py` | `TRUSTED_CLIENT_IP_HEADER` (`HTTP_CF_CONNECTING_IP`) |

Throttle counters live in Redis db 3 (dbs 1 and 2 are the Celery
broker/results), so they are shared across gunicorn workers.

---

## Outstanding actions

### 1. Finish 2FA enrolment — blocking admin sign-in

`praponb` has an unconfirmed TOTP device, so the password step currently ends at
a setup screen. The stale pending record is harmless: opening setup issues a
fresh secret and discards it.

1. <https://inventory.praponb.com/login>, sign in as **`praponb`**
2. Scan the QR with an authenticator app
3. Enter the 6-digit code, then **save the 10 recovery codes** — shown once only

### 2. Cloudflare edge protection

Dashboard-only work, free plan, not yet applied.

- **Rate limiting rule** — `praponb.com` → Security → WAF → Rate limiting rules.
  Expression `URI Path equals /api/v1/auth/login/` and
  `Hostname equals inventory.praponb.com`; characteristic **IP**; **20 requests
  / 1 minute**; action **Block**, 10 minutes. The free plan allows one rule, and
  this is the one worth spending it on — it stops attack traffic before it
  reaches the Mac.
- **Bot Fight Mode** — Security → Bots → toggle on.

### 3. Move credentials to a password manager

Then delete `~/inventory-credentials-20260828.txt`.

### Known gaps, left open by choice

- **No edge WAF** beyond the rate-limiting rule above.
- **The lockout is DoS-able**: anyone who learns a username can keep that
  account locked in 15-minute windows. This is inherent — counting unknown
  usernames is what stops the lockout leaking which accounts exist. The unlock
  command above is the mitigation.
- **`admin` password auth from the open internet.** Mitigated by the rename,
  a 24-character password, lockout, and TOTP — but it remains the front door.
- **`.env` is gitignored**, so production configuration is not backed up by
  `git push`. This is exactly what let the settings silently revert before.
