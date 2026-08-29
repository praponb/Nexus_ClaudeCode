# Outstanding issues — 2026-08-29

Compiled by sweeping `DEPLOY-UBUNTU.md`, `SESSION-2026-08-28-SECURITY.md`,
`FAQ.md`, `UserManual.md`, `CLAUDE.md`, `testcase/`, the code, and the running
systems on both hosts.

Every item below was **verified against the live systems today**, not copied
forward from the older documents — several of those turned out to be stale, and
those are listed in [§5](#5-stale-claims-in-existing-docs) so they stop causing
confusion.

---

## 1. Before you restart the MacBook — one blocking action

> ### ⛔ Run this first, or the restart will break production
>
> ```bash
> sudo launchctl disable system/com.cloudflare.cloudflared
> ```
>
> Confirm with:
> ```bash
> sudo launchctl print-disabled system | grep cloudflare      # expect "=> disabled"
> ```

**Why it matters.** `launchctl unload` and `launchctl bootout` last only until
the next boot. The plist is still in `/Library/LaunchDaemons/`, so a restart
reloads it (`RunAtLoad` is true) and the Mac starts **a second connector on the
same Cloudflare Tunnel**. Cloudflare then load-balances visitors between the
Ubuntu server and the Mac — and the Mac's database is frozen at the moment of
cutover. Visitors would get served stale data at random, and any writes landing
on the Mac would be silently lost.

This is not theoretical: it is the same class of mistake that made two
`disabled-`prefixed plists keep running for weeks (renaming a plist does not
disable it either — only `launchctl disable` persists).

**Already handled** — no action needed:

| Job | State |
|---|---|
| `com.nexus.inventory-autostart` | `disabled` (persists across reboot) ✅ |
| `com.praponb.inventory.backup` | `disabled` (persists across reboot) ✅ |
| `com.cloudflare.cloudflared` | **booted out, but NOT disabled** ⛔ needs the command above |

Once that command has run, the Mac is safe to reboot as often as you like. The
Ubuntu server is entirely independent of it.

---

## 2. Open defects in the application

Both are **pre-existing**, both reproduce on the standby Mac, and neither was
caused by the server migration — it is simply what surfaced them. Both are
user-visible.

### 2.1 Attachment uploads fail (High)

Attaching any file to an asset raises `PermissionError`. Verified by running the
real code path:

```
>>> store_upload(uuid4(), b'hello', 'txt')
PermissionError: [Errno 13] Permission denied: '/app/media/attachments'
```

The `backend_media` volume is owned by `root`, while the backend container runs
as `appuser` (uid 10001). This is why the media volume has always been empty —
no attachment has ever been stored successfully.

**Fix:** `chown` the media directory in `backend/Dockerfile` before
`USER appuser`, so newly created volumes inherit the right ownership, plus a
one-off for the volume that already exists:

```bash
docker run --rm -v inventory_backend_media:/m alpine chown -R 10001:10001 /m
```

Not applied — it is an application change and was outside the migration's scope.

### 2.2 The audit log's tamper-evident chain does not verify (Medium)

`verify_chain()` returns `False` on both hosts. Seven events (ids 403–409, all
`auth.*`: login, logout, `mfa.enroll`, `mfa.verify`) carry a `record_hash` that
does not recompute from their stored payload.

The chain **links** are intact — every `prev_hash` matches its predecessor — so
this is not a truncated or spliced log. It is seven individual records
disagreeing with their own hash. They are the newest events, written during the
2FA work, which points at how those particular events are recorded rather than
at tampering.

**Do not run `reseal_chain()` yet.** It would make the check pass by recomputing
hashes from whatever is currently stored — hiding the discrepancy and destroying
the evidence needed to explain it.

---

## 3. Operational gaps

| # | Item | Risk | Owner |
|---|---|---|---|
| 3.1 | **Backups are on the same disk as the database.** Covers bad migrations and accidental deletion, not drive failure. | Medium | copy dumps to another machine |
| 3.2 | **Cloudflare edge protection not applied** — no rate-limiting rule on `/api/v1/auth/login/`, no Bot Fight Mode. The app's own 10/min throttle is the only brute-force defence, and it only acts after traffic reaches the server. | Medium | dashboard work, see §6 |
| 3.3 | **`~/inventory-credentials-20260828.txt` still on the Mac** (mode 600, verified present today). Human account passwords belong in a password manager. | Medium | move, then delete |
| 3.4 | **The server has no git history.** Code arrives by rsync, so *this Mac's working tree is the only record of what is deployed*. An uncommitted change that gets synced is untraceable afterwards. | Medium | commit before every sync; a read-only deploy key would fix it properly |
| 3.5 | **cloudflared is not apt-managed** on the server (installed from the release `.deb`, because Cloudflare publishes no `resolute` suite). Nothing will ever update it. | Low | re-check for a `resolute` suite periodically |
| 3.6 | **Docker is not apt-managed** either (`/usr/local/bin/docker`, from the convenience script), so `apt upgrade` will not update the container runtime. | Low | convert to the apt packages when convenient |
| 3.7 | **Server reboot never tested.** Boot resilience was verified structurally — `docker`, `containerd`, `cloudflared` all `enabled`, every container `unless-stopped` — but not proven by an actual restart. | Low | `sudo reboot` when you can watch it |
| 3.8 | **`.env` is gitignored**, so production configuration is not backed up by `git push`. This is exactly what let the production settings silently revert once before. | Low | inherent; verify the *running* config, not the repo |

---

## 3b. Housekeeping on the standby Mac

None of these affect production. They are recorded because they are invisible
otherwise and each is a small trap for a future session.

| # | Item | Note |
|---|---|---|
| 3b.1 | **`com.praponb.jobs4dent.backup` is failing** — last exit status **1**, verified today. | A *different* project's production database backup. Left running deliberately during the tunnel cleanup, but it has not been succeeding. Worth a look if that project matters. |
| 3b.2 | Two plists named `disabled-com.praponb.twin.*.plist` remain in `~/Library/LaunchAgents/`. | The prefix is misleading — it never disabled anything; launchd keys off the `Label` inside. They *are* now genuinely disabled via `launchctl disable`. Renaming them back would make the directory honest. |
| 3b.3 | Stale `~/.cloudflared/jobs4dent-config.yml` and `twin-chatbot-config.yml`. | Neither drives anything: `chatbot.praponb.com` is served from the Ubuntu server's own containers, and the jobs4dent tunnel is disabled. Clutter that previously caused a wrong conclusion. |
| 3b.4 | Mac `cloudflared` is **2026.7.3**; the server runs **2026.8.2**. | Only matters if the Mac is ever brought back for a rollback. |
| 3b.5 | `com.praponb.preventsleep` (a `caffeinate` LaunchAgent) is still running. | It existed to stop the Mac sleeping and dropping the tunnel. That reason is gone; keep it only if something else needs the Mac awake. |
| 3b.6 | `~/cf-staging/install-tunnel.sh` remains on the server. | Harmless — the credentials it staged were shredded once systemd had its own copy at mode 600. Delete when convenient. |

## 4. Known gaps accepted by choice

Recorded so they are not rediscovered as surprises.

- **The per-account lockout is DoS-able.** Anyone who learns a username can keep
  it locked in 15-minute windows. This is inherent to the design: counting
  unknown usernames is what stops the lockout from leaking which accounts exist.
  Operator unlock:
  ```bash
  ssh prapon@192.168.1.49 'cd ~/inventory && docker compose exec -T backend python -c "
  import django; django.setup()
  from apps.core.login_guard import reset; reset(\"praponb\")"'
  ```
- **Admin password auth is reachable from the open internet.** Mitigated by the
  rename to `praponb`, a long password, per-account lockout, and mandatory TOTP.
- **Email notification delivery is not implemented** (in-app notifications work;
  SMTP dispatch is backlog).
- **`chatbot.praponb.com` shares the server.** Containers `twin` and
  `twin-tunnel`, a separate compose project in `~/twin`. Never
  `docker system prune -a` or bulk-stop containers on that host.

---

## 5. Stale claims in existing docs

Found while compiling this. Each was checked against the live system today and
is **already resolved** — treat the older documents as history where they
conflict with this list.

| Claim | Where | Reality (verified 2026-08-29) |
|---|---|---|
| "Finish 2FA enrolment — blocking admin sign-in" | `SESSION-2026-08-28-SECURITY.md` §Outstanding 1 | **Done.** TOTP device for `praponb` confirmed 2026-08-28 22:09, 10 unused recovery codes. |
| "One High-severity npm audit finding open" | `FAQ.md` §What's not finished | **Clean.** `npm audit` reports 0 vulnerabilities, production and dev. |
| "62 unexecuted Playwright test cases" | memory / QA notes | **Executed.** 60 passed, 2 blocked, 15 evidence screenshots. |
| "The backup timer is not installed" | `DEPLOY-UBUNTU.md` §8 | **Installed.** Timer enabled, next run 03:19; last run exited 0 and produced a valid dump + media tarball. |
| "Production runs on a Mac" | several docs | **Ubuntu server since 2026-08-29.** |

| "Attachments backed up by volume snapshot / bucket versioning" | `backend/docs/BACKUP_RESTORE.md` | **Corrected.** `backup.sh` now produces a media tarball directly, with a matching timestamp. |
| Restore drill: "`verify_chain()` … must print `True`" | `backend/docs/BACKUP_RESTORE.md` | **Corrected — this one was dangerous.** It prints `False` for the known reason in §2.2, so a faithful restore would have looked like a failure and a good backup might have been discarded. |
| Backup schedule documented as a macOS LaunchAgent | `backend/docs/BACKUP_RESTORE.md` | **Corrected.** Production is a systemd timer; the macOS section is now marked development/standby only. |
| `testcase/` structure listing 3 files | `testcase/README.md` | **Corrected.** There are 12 entries including cycle-2/3 plans, `execution-status.json`, and `evidence/`. |

The two blocked help-UI cases are genuine, though minor: `TC-HELP-05`
(automated accessibility scan) and `TC-HELP-77` (forbidden-register response
renders a helpful alert).

Broader test coverage: of 259 recorded cases, 183 passed, 69 blocked, 5 failed,
2 manual. Most blocks are "browser unavailable" from the original automated QA
runs. Several of the 5 failures are themselves stale — e.g. one asserts the root
`compose.yaml` is absent (it exists), and another expects a `.env.example` that
was removed deliberately.

---

## 6. Cloudflare edge protection — the steps

Dashboard-only, free plan. Cannot be verified from the command line, because the
application's own 10/min throttle triggers before a 20/min edge rule would.

1. **Rate limiting rule** — `praponb.com` → Security → WAF → Rate limiting rules
   - Expression: `URI Path equals /api/v1/auth/login/` **and**
     `Hostname equals inventory.praponb.com`
   - Characteristic: **IP**
   - Threshold: **20 requests / 1 minute**
   - Action: **Block**, 10 minutes

   The free plan allows one rule, and this is the one worth spending it on: it
   stops attack traffic at the edge, before it ever reaches the server.

2. **Bot Fight Mode** — Security → Bots → toggle on.

---

## 7. Current state, for reference

Verified 2026-08-29.

**Production — Ubuntu 26.04.1 LTS, `prapon@192.168.1.49`, `~/inventory`**
- Six containers up; backend/frontend bound to `127.0.0.1`, Postgres and Redis
  not published at all
- `cloudflared` systemd service active and enabled; `docker` and `containerd`
  enabled at boot; every container `unless-stopped`
- `DEBUG=False`, `config.settings.production`, Redis-backed throttle cache,
  `HTTP_CF_CONNECTING_IP` as the trusted client-IP header
- Data: 100,213 assets, 7 users (2 active: `demo`/viewer, `praponb`/system_admin),
  1 confirmed TOTP device, 10 unused recovery codes
- Login throttle verified live: cuts off at exactly 10 under a rotating
  `X-Forwarded-For`
- Also hosts `chatbot.praponb.com` — leave those containers alone

**Standby — this MacBook**
- All six containers stopped (`stop`, not `down -v`); volumes intact
- Data frozen at cutover; this is a rollback window of hours, not a replica
- Both LaunchAgents persistently disabled; tunnel daemon booted out but
  **not yet disabled** (§1)

**Repository**
- Branch `b_pbv_main`, clean, nothing unpushed
- Rollback procedure: `DEPLOY-UBUNTU.md` §7
