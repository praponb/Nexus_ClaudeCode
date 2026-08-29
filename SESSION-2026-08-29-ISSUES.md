# Outstanding issues — opened 2026-08-29, worked 2026-08-30

Originally compiled by sweeping `DEPLOY-UBUNTU.md`,
`SESSION-2026-08-28-SECURITY.md`, `FAQ.md`, `UserManual.md`, `CLAUDE.md`,
`testcase/`, the code, and the running systems on both hosts.

**Updated 2026-08-30 (local; 2026-08-29 UTC).** Most of this list has now been
acted on rather than merely recorded. Resolved items are kept, marked, and dated
— deleting them would lose the reason each one existed, which is the part that
stops it happening again. What is still open is collected in
[§0](#0-what-is-still-open).

---

## 0. What is still open

Everything else on this page is done. These are not, and three of them cannot be
done from a terminal.

| # | Item | Why it is still open |
|---|---|---|
| [3.2](#3-operational-gaps) | Cloudflare rate-limiting rule + Bot Fight Mode | Dashboard-only. Steps in [§6](#6-cloudflare-edge-protection--the-steps). |
| [3.3](#3-operational-gaps) | `~/inventory-credentials-20260828.txt` still on the Mac | Human passwords belong in a password manager, and moving them there is your call, not an automated one. |
| [3.5](#3-operational-gaps) | `cloudflared` is not apt-managed on the server | Waiting on Cloudflare publishing a `resolute` suite. |
| [3.6](#3-operational-gaps) | Docker is not apt-managed on the server | Conversion is a maintenance window, not a code change. |
| [3.7](#3-operational-gaps) | Server reboot never tested | Needs someone watching the box come back up. |
| [3.8](#3-operational-gaps) | `.env` is gitignored, so production config is not in git | Inherent to the design. Verify the *running* config, not the repo. |
| [2.2](#22-the-audit-logs-tamper-evident-chain-explained-2026-08-30) | The audit chain still does not verify | Now **explained** and proven benign, but deliberately not resealed. See below. |

---

## 1. Restart safety — RESOLVED (verified 2026-08-30)

The MacBook is safe to reboot.

```
$ launchctl print-disabled system | grep cloudflare
        "com.cloudflare.cloudflared" => disabled
$ pgrep -fl cloudflared
(none running)
```

| Job | State |
|---|---|
| `com.nexus.inventory-autostart` | `disabled` (persists across reboot) ✅ |
| `com.praponb.inventory.backup` | `disabled` (persists across reboot) ✅ |
| `com.cloudflare.cloudflared` | `disabled` (persists across reboot) ✅ |

**Keep the reason, not just the result.** `launchctl unload` and
`launchctl bootout` last only until the next boot. The plist is still in
`/Library/LaunchDaemons/` with `RunAtLoad` true, so had it only been booted out,
a restart would have started **a second connector on the same Cloudflare
Tunnel**. Cloudflare would then load-balance visitors between the Ubuntu server
and a Mac whose database is frozen at the moment of cutover: stale data served at
random, and any writes landing on the Mac silently lost.

Renaming a plist does not disable it either — launchd keys off the `Label`
inside the file. Only `launchctl disable` persists. That mistake kept two
`disabled-`prefixed plists running for weeks.

---

## 2. Application defects

### 2.1 Attachment uploads (High) — FIXED AND DEPLOYED 2026-08-30

Attaching any file to an asset raised `PermissionError`, so no attachment had
ever been stored successfully and the media volume had always been empty.

**Cause.** `backend/Dockerfile` never created `/app/media`. Docker therefore
created the volume mount point itself, root-owned, *after* the image had already
run `chown -R appuser:appuser /app` — and the container runs as `appuser`
(uid 10001).

**Fix.** Create the directory in the image, in the same layer as the chown, so
every future volume inherits the right ownership without a manual step:

```dockerfile
RUN uv sync --frozen --no-dev && mkdir -p /app/media && chown -R appuser:appuser /app
```

The already-existing volume needed a one-off, which has been applied:

```bash
docker run --rm -v inventory_backend_media:/m alpine chown -R 10001:10001 /m
```

**Verified in production** by running the exact call that used to fail:

```
WROTE attachments/a5f4d63d-.../8837dd8dd963....txt
exists: True bytes: 19 uid: 10001
removed: True
```

`/app/media` is now `appuser:appuser`. The test file was removed afterwards.

**Why the test suite missed it.** The functional upload tests run against a
`tmp_path` `MEDIA_ROOT`, where ownership is never in question. The defect was
image-level, so the new regression guard
(`test_dockerfile_creates_media_dir_owned_by_appuser`) is image-level too: it
asserts the Dockerfile creates and chowns `/app/media` before dropping to
`appuser`.

### 2.2 The audit log's tamper-evident chain — EXPLAINED 2026-08-30

`verify_chain()` still returns `False`, and that is now a known, benign result
rather than an open question.

**Finding.** All seven failing records are explained by a single deleted user.

```
60 events (ids 366-425); 8 candidate actor UUIDs.
Chain links: INTACT

7 record(s) disagree with their own hash:
   403  auth.login       pending   -> actor=deleted-user<75c2cb8f-da6d-46f4-a3b8-7f735150098f>
   404  auth.mfa.enroll  success   -> actor=deleted-user<75c2cb8f-...>
   405  auth.login       success   -> actor=deleted-user<75c2cb8f-...>
   406  auth.logout      success   -> actor=deleted-user<75c2cb8f-...>
   407  auth.login       pending   -> actor=deleted-user<75c2cb8f-...>
   408  auth.mfa.verify  success   -> actor=deleted-user<75c2cb8f-...>
   409  auth.login       success   -> actor=deleted-user<75c2cb8f-...>

7 explained, 0 unexplained.
```

**Mechanism.** `AuditEvent.actor` is `on_delete=SET_NULL`, and
`_payload_for()` hashes `actor.uuid`. Deleting a user therefore silently rewrites
the payload of every event that user ever caused, while leaving `prev_hash`
untouched — so the links stay intact and only the individual rows disagree.
That is exactly the shape this looked like. It is bookkeeping, not tampering.

**The story the rows tell.** Events 403–409 are one account (uuid
`75c2cb8f-…`) enrolling TOTP, verifying, and signing in and out on 2026-08-28
21:08–21:10. Events 410+ are the same sequence repeated by user id 1
(`praponb`, uuid `55c9b23d-…`). The first account was deleted afterwards. §4's
description of "the rename to `praponb`" is therefore not quite right: it was a
new account plus a deletion, not a rename.

**The real gap this exposes.** There is no audit event recording that deletion.
A user vanished from the system and the audit log does not say who removed them
or when — which is a bigger weakness than the hash mismatch that led here.

**Still do not run `reseal_chain()`.** It would make the check pass by
recomputing hashes from whatever is currently stored, and the evidence above
would be gone. Two better options, neither applied yet because both change how
hashing works and need their own decision:

- snapshot the actor UUID into a column on the event, so a nulled FK can never
  invalidate a row again;
- record `user.delete` as an audit event in the first place.

**Diagnosing it again.** The forensics are a command, not a one-off script:

```bash
ssh prapon@192.168.1.49 'cd ~/inventory && docker compose exec -T backend \
  python manage.py audit_chain_report'
```

It is strictly read-only, separates a broken link from a row that disagrees with
its own hash, and recovers a deleted actor's UUID from `target_uuid` — the only
place it survives.

---

## 3. Operational gaps

| # | Item | Status |
|---|---|---|
| 3.1 | **Backups were on the same disk as the database.** | **FIXED 2026-08-30.** `scripts/pull-backups.sh` copies the server's dumps to this Mac and verifies the newest is a valid gzip stream. Ran today: 2 dumps + 2 media tarballs now in `~/inventory-backups`. Its LaunchAgent ships **uninstalled** — see the note below. |
| 3.2 | **Cloudflare edge protection not applied** — no rate-limiting rule on `/api/v1/auth/login/`, no Bot Fight Mode. The app's own 10/min throttle is the only brute-force defence, and it only acts after traffic reaches the server. | **OPEN.** Dashboard work, see [§6](#6-cloudflare-edge-protection--the-steps). |
| 3.3 | **`~/inventory-credentials-20260828.txt` still on the Mac** (mode 600, verified present again today). | **OPEN.** Move to a password manager, then delete. |
| 3.4 | **The server has no git history**, so an uncommitted change that got synced was untraceable afterwards. | **FIXED 2026-08-30.** `sync-to-server.sh` now refuses a dirty tree (`--allow-dirty` to override) and stamps `DEPLOYED_COMMIT` into the transfer. |
| 3.5 | **cloudflared is not apt-managed** on the server (installed from the release `.deb`, because Cloudflare publishes no `resolute` suite). Nothing will ever update it. | **OPEN.** Re-check for a `resolute` suite periodically. |
| 3.6 | **Docker is not apt-managed** either (`/usr/local/bin/docker`, from the convenience script), so `apt upgrade` will not update the container runtime. | **OPEN.** Convert to the apt packages when convenient. |
| 3.7 | **Server reboot never tested.** Boot resilience was verified structurally — `docker`, `containerd`, `cloudflared` all `enabled`, every container `unless-stopped` — but not proven by an actual restart. | **OPEN.** `sudo reboot` when you can watch it. |
| 3.8 | **`.env` is gitignored**, so production configuration is not backed up by `git push`. This is exactly what let the production settings silently revert once before. | **OPEN, inherent.** Verify the *running* config, not the repo. |

**On 3.1 and the uninstalled LaunchAgent.** `com.praponb.inventory.pull-backups.plist`
is deliberately *not* bootstrapped. This Mac is a cold standby; its whole value is
that nothing here starts on its own, and §1 is a two-paragraph illustration of
what an unnoticed launchd job costs. Loading it is a decision to make on purpose:

```bash
cp scripts/com.praponb.inventory.pull-backups.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) \
  ~/Library/LaunchAgents/com.praponb.inventory.pull-backups.plist
```

Until then, run `./scripts/pull-backups.sh` by hand after anything that matters.

**On 3.4, checking what is deployed:**

```bash
$ ssh prapon@192.168.1.49 'cat ~/inventory/DEPLOYED_COMMIT'
commit=4f4af78aba9c7071856df50fb0d554537c2ab317
branch=b_pbv_main
dirty=no
synced_at=2026-08-29T18:41:11Z
synced_from=Prapons-MacBook-Air by praponb
```

---

## 3b. Housekeeping on the standby Mac — DONE 2026-08-30

None of these affected production. They are kept because each was a small trap,
and because one of them turned out to matter.

| # | Item | Outcome |
|---|---|---|
| 3b.1 | **`com.praponb.jobs4dent.backup` was failing** — exit status 1. | **Root cause found, and it matters more than the exit code did.** Its log reads `ERROR: postgres service is not running; nothing backed up`, hourly since 2026-08-28 17:55 — that stack is stopped on this Mac. **A different project's production database has had no backup since then.** The agent is now `launchctl disable`d so it stops failing silently; restoring that project's backups is out of scope here but is worth doing. |
| 3b.2 | Two plists named `disabled-com.praponb.twin.*.plist`. | **Renamed** to `com.praponb.twin.app.plist` / `com.praponb.twin.tunnel.plist`. The prefix never disabled anything — launchd keys off the `Label` inside. Both remain genuinely disabled via `launchctl disable`, confirmed after the rename. |
| 3b.3 | Stale `~/.cloudflared/jobs4dent-config.yml` and `twin-chatbot-config.yml`. | **Moved to `~/.cloudflared/retired/`, not deleted.** Neither drives anything — `chatbot.praponb.com` is served from the server's own containers and the jobs4dent tunnel is disabled — but that tunnel is only disabled, not decommissioned, so deleting its config would quietly break bringing it back. |
| 3b.4 | Mac `cloudflared` is **2026.7.3**; the server runs **2026.8.2**. | **Note only.** Matters solely if the Mac is ever brought back for a rollback. |
| 3b.5 | `com.praponb.preventsleep` (a `caffeinate` LaunchAgent) still running. | **Booted out and disabled.** Its reason — keeping the Mac awake so the tunnel stayed up — is gone. To bring it back: `launchctl enable gui/$(id -u)/com.praponb.preventsleep && launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.praponb.preventsleep.plist`. |
| 3b.6 | `~/cf-staging/install-tunnel.sh` on the server. | **Deleted.** Its credentials were already shredded, and the procedure it encoded is documented in `DEPLOY-UBUNTU.md` §4 (Cutover), so nothing was lost. |

---

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
  move to the `praponb` account, a long password, per-account lockout, and
  mandatory TOTP. (See §2.2: this was a new account plus a deletion of the old
  one, not a rename — and the deletion was not audited.)
- **Email notification delivery is not implemented** (in-app notifications work;
  SMTP dispatch is backlog).
- **`chatbot.praponb.com` shares the server.** Containers `twin` and
  `twin-tunnel`, a separate compose project in `~/twin`. Never
  `docker system prune -a` or bulk-stop containers on that host. Verified still
  serving 200 after today's deploy.

---

## 5. Stale claims in existing docs

Each was checked against the live system and corrected. Treat the older
documents as history where they conflict with this list.

| Claim | Where | Reality |
|---|---|---|
| "Finish 2FA enrolment — blocking admin sign-in" | `SESSION-2026-08-28-SECURITY.md` §Outstanding 1 | **Done.** TOTP device for `praponb` confirmed 2026-08-28 22:09, 10 unused recovery codes. |
| "One High-severity npm audit finding open" | `FAQ.md` §What's not finished | **Clean.** `npm audit` reports 0 vulnerabilities, production and dev (re-verified 2026-08-30). |
| "62 unexecuted Playwright test cases" | memory / QA notes | **Executed.** 60 passed, 2 blocked, 15 evidence screenshots. |
| "The backup timer is not installed" | `DEPLOY-UBUNTU.md` §8 | **Installed.** Timer enabled; last run exited 0 and produced a valid dump + media tarball. |
| "Production runs on a Mac" | several docs | **Ubuntu server since 2026-08-29.** |
| "Attachments backed up by volume snapshot / bucket versioning" | `backend/docs/BACKUP_RESTORE.md` | **Corrected.** `backup.sh` produces a media tarball directly, with a matching timestamp. |
| Restore drill: "`verify_chain()` … must print `True`" | `backend/docs/BACKUP_RESTORE.md` | **Corrected — this one was dangerous.** It prints `False` for the reason in §2.2, so a faithful restore would have looked like a failure and a good backup might have been discarded. |
| Backup schedule documented as a macOS LaunchAgent | `backend/docs/BACKUP_RESTORE.md` | **Corrected.** Production is a systemd timer; the macOS section is marked development/standby only. |
| `testcase/` structure listing 3 files | `testcase/README.md` | **Corrected.** There are 12 entries including cycle-2/3 plans, `execution-status.json`, and `evidence/`. |
| "5 failed test cases" | `testcase/execution-status.json` | **Re-executed 2026-08-30. Zero failures remain.** Four pass (root `compose.yaml` exists, `uv.lock` exists, `npm audit` clean). `TC-DEF-002-01` is **WAIVED**, not passed — it asserts a root `.env.example` the project deliberately dropped for `scripts/templates/.env`, so calling it green would be a false pass. |

Current test status: 259 cases — 187 passed, 69 blocked, 2 manual, 1 waived,
**0 failed**. Most blocks are "browser unavailable" from the original automated
QA runs. The two blocked help-UI cases are genuine but minor: `TC-HELP-05`
(automated accessibility scan) and `TC-HELP-77` (forbidden-register response
renders a helpful alert).

---

## 6. Cloudflare edge protection — the steps

**Still open.** Dashboard-only, free plan. Cannot be verified from the command
line, because the application's own 10/min throttle triggers before a 20/min
edge rule would.

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

Verified 2026-08-30, after the deploy.

**Production — Ubuntu 26.04.1 LTS, `prapon@192.168.1.49`, `~/inventory`**
- Six containers up; backend/frontend bound to `127.0.0.1`, Postgres and Redis
  not published at all
- `cloudflared` systemd service active and enabled; `docker` and `containerd`
  enabled at boot; every container `unless-stopped`
- `DEBUG=False`, `config.settings.production`, Redis-backed throttle cache,
  `HTTP_CF_CONNECTING_IP` as the trusted client-IP header
- Data: 100,213 assets, 7 users (2 active: `demo`/viewer, `praponb`/system_admin),
  1 confirmed TOTP device, 10 unused recovery codes
- Attachment storage working, `/app/media` owned by `appuser`
- Running `DEPLOYED_COMMIT` `4f4af78`, branch `b_pbv_main`, `dirty=no`
- `https://inventory.praponb.com` → 200; `https://chatbot.praponb.com` → 200
- Also hosts `chatbot.praponb.com` — leave those containers alone

**Standby — this MacBook**
- All six containers stopped (`stop`, not `down -v`); volumes intact
- Data frozen at cutover; this is a rollback window of hours, not a replica
- Every relevant launchd job persistently `disabled`, tunnel daemon included (§1)
- Holds a second copy of the server's backups in `~/inventory-backups`

**Repository**
- Branch `b_pbv_main`
- Rollback procedure: `DEPLOY-UBUNTU.md` §7
