# Outstanding issues — opened 2026-08-29

Originally compiled by sweeping `DEPLOY-UBUNTU.md`,
`SESSION-2026-08-28-SECURITY.md`, `FAQ.md`, `UserManual.md`, `CLAUDE.md`,
`testcase/`, the code, and the running systems on both hosts.

**Trimmed 2026-08-30.** Everything that was fixed has been removed from this
page, so what remains is only what still needs doing. The removed items are not
lost: each one's cause and fix is recorded where the code lives — attachment
uploads and the audit chain in [`DEPLOY-UBUNTU.md`](DEPLOY-UBUNTU.md) §8, the
deploy and backup changes in [`scripts/ScriptUserGuide.md`](scripts/ScriptUserGuide.md),
and all of it in the git history for 2026-08-30.

Section numbers are unchanged from the original list, and the gaps in them are
deliberate — other documents link to `§2.2` and `§0` by number.

---

## 0. What is still open

Four of these cannot be done from a terminal at all.

| # | Item | Why it is still open |
|---|---|---|
| [2.2](#22-the-audit-logs-tamper-evident-chain) | The audit chain does not verify | **Explained and proven benign**, but deliberately not resealed, and the two real fixes are unapplied. |
| [3.2](#3-operational-gaps) | Cloudflare rate-limiting rule + Bot Fight Mode | Dashboard-only. Steps in [§6](#6-cloudflare-edge-protection--the-steps). |
| [3.3](#3-operational-gaps) | `~/inventory-credentials-20260828.txt` still on the Mac | Human passwords belong in a password manager, and moving them there is your call, not an automated one. |
| [3.5](#3-operational-gaps) | `cloudflared` is not apt-managed on the server | Waiting on Cloudflare publishing a `resolute` suite. |
| [3.6](#3-operational-gaps) | Docker is not apt-managed on the server | Conversion is a maintenance window, not a code change. |
| [3.8](#3-operational-gaps) | `.env` is gitignored, so production config is not in git | Inherent to the design. Verify the *running* config, not the repo. |
| [3.11](#3-operational-gaps) | **The server lost power on 2026-08-31 and nobody knows why** | Needs hands on the hardware and its BIOS event log. See [§9](#9-the-2026-08-31-outage). |
| [3.12](#3-operational-gaps) | HSTS is missing from the Nuxt-served pages | A real deviation from `DEPLOY-UBUNTU.md` §5 check 2, found 2026-08-31. |
| [3b.1](#3b-neighbouring-systems) | **Jobs4Dent has had no database backup since 2026-08-28** | Different repo. Found here, needs fixing there. |
| [3.10](#3-operational-gaps) | Whether to keep `SESSION-2026-08-28-SECURITY.md` | Deleting it drops content that exists nowhere else. Decision, not a task. |

---

## 2. Application defects

### 2.2 The audit log's tamper-evident chain

`verify_chain()` returns `False`. That result is now **explained and benign**,
but the underlying design weakness is still there, so this stays open.

**What is happening.** `AuditEvent.actor` is `on_delete=SET_NULL` and
`_payload_for()` hashes `actor.uuid`, so deleting a user silently rewrites the
payload of every event that user ever caused while leaving `prev_hash` untouched.
The links stay intact; only the individual rows disagree with their own hash.
All seven failing records (ids 403–409) are accounted for by one deleted
account, `75c2cb8f-…` — a second `system_admin` created and deleted during the
2FA work (it completed `mfa.enroll` and `mfa.verify`, and MFA is required only
for that role). It is bookkeeping, not tampering. It is **not** the old `admin`
account: `praponb` is user id 1 and carried the same UUID before, during and
after that work, which is what a rename looks like.

**The real gap.** There is no audit event recording that deletion. A user
vanished from the system and the audit log does not say who removed them, or
when, or even what the account was called — a bigger weakness than the hash
mismatch that led here.

**Two fixes, neither applied.** Both change how hashing works and need their own
decision:

- snapshot the actor UUID into a column on the event, so a nulled FK can never
  invalidate a row again;
- record `user.delete` as an audit event in the first place.

**Do not run `reseal_chain()`.** It would make the check pass by recomputing
hashes from whatever is currently stored, hiding the discrepancy and destroying
the evidence. Nothing above would be recoverable afterwards.

**Re-diagnosing.** The forensics are a command, not a one-off script:

```bash
ssh prapon@192.168.1.49 'cd ~/inventory && docker compose exec -T backend \
  python manage.py audit_chain_report'
```

It is strictly read-only, separates a broken link from a row that disagrees with
its own hash, and recovers a deleted actor's UUID from `target_uuid` — the only
place it survives.

---

## 3. Operational gaps

| # | Item | Owner / next step |
|---|---|---|
| 3.2 | **Cloudflare edge protection not applied** — no rate-limiting rule on `/api/v1/auth/login/`, no Bot Fight Mode. The app's own 10/min throttle is the only brute-force defence, and it only acts after traffic reaches the server. | Dashboard work, see [§6](#6-cloudflare-edge-protection--the-steps). |
| 3.3 | **`~/inventory-credentials-20260828.txt` still on the Mac** (mode 600, verified present 2026-08-30). | Move to a password manager, then delete. |
| 3.5 | **cloudflared is not apt-managed** on the server (installed from the release `.deb`, because Cloudflare publishes no `resolute` suite). Nothing will ever update it. | Re-check for a `resolute` suite periodically. |
| 3.6 | **Docker is not apt-managed** either (`/usr/local/bin/docker`, from the convenience script), so `apt upgrade` will not update the container runtime. | Convert to the apt packages when convenient. |
| 3.7 | ~~Server reboot never tested.~~ **Resolved 2026-08-31 by doing it.** A graceful `sudo reboot` was watched all the way back up: all six inventory containers plus `twin` and `twin-tunnel` returned on their own, postgres and redis healthy, `cloudflared` active, and both public hostnames back to 200 — no manual step anywhere. `restart: unless-stopped` plus the enabled units do cover a restart, as [`DEPLOY-UBUNTU.md`](DEPLOY-UBUNTU.md) §6 claimed. | Nothing to do. |
| 3.8 | **`.env` is gitignored**, so production configuration is not backed up by `git push`. This is exactly what let the production settings silently revert once before. | Inherent. Verify the *running* config, not the repo. |
| 3.9 | ~~The Mac's tunnel LaunchDaemon may still be armed for boot.~~ **Resolved 2026-08-31 by observation.** `sudo launchctl print-disabled system` returns `"com.cloudflare.cloudflared" => disabled`, so the system-domain override from 2026-08-29 did stick and the daemon stays down across a restart. Kept here because the plist is still installed with `RunAtLoad` + `KeepAlive` — the override is the only thing holding it, and `launchctl enable` (part of the rollback) re-arms it. | Nothing to do. Re-check with [§8](#8-before-and-after-rebooting-this-mac) after any rollback. |
| 3.10 | **`SESSION-2026-08-28-SECURITY.md` — keep or relocate?** It has no pending items (its own banner says so), which raised the question of deleting it. But four things live only there: the accounts table with active/deactivated/TOTP status, the reactivate-account command (`is_active=True`), the consolidated security-posture table (`ImportExportThrottle` appears in no other doc), and the *rationale* behind the security invariants `CLAUDE.md` says must not be weakened without discussion. Three documents link to it: `CLAUDE.md`, `DEPLOY-UBUNTU.md`, `FAQ.md`. | Either leave it (recommended), or move Part 3 into `DEPLOY-UBUNTU.md` §6 and retarget the three links *before* deleting. |
| 3.11 | **The server lost power on 2026-08-31 and the cause is unknown.** The journal for that boot ends mid-line at 12:40:04 +07 with no shutdown sequence at all — the signature of a power cut or a hard hang, not a crash the OS survived long enough to log. Roughly five hours down. The clean reboot afterwards proves the hardware is not persistently faulted, so this is **intermittent and can recur**. Full account in [§9](#9-the-2026-08-31-outage). | Check the physical power path, then the BIOS event log (`sudo dmidecode -t 32`, or F10 at boot). A UPS would rule power out entirely. |
| 3.12 | **HSTS is missing from the pages Nuxt serves.** Django's own routes return the full set — `strict-transport-security: max-age=31536000; includeSubDomains; preload`, `x-content-type-options: nosniff`, `x-frame-options: DENY` — but `/`, `/login/` and `/admin/` come back from Nuxt carrying none of them. So a first-time visitor landing on the homepage gets no HSTS policy at all; only someone whose browser has already hit an API path has one cached for the host. [`DEPLOY-UBUNTU.md`](DEPLOY-UBUNTU.md) §5 check 2 expects HSTS on `/`, so the documented verification does not currently pass. Pre-existing, not a regression from the reboot. | Decide where the headers belong for Nuxt-served responses — the tunnel ingress, or Nuxt itself. |

---

## 3b. Neighbouring systems

| # | Item | Detail |
|---|---|---|
| 3b.1 | **Jobs4Dent has had no database backup since 2026-08-28.** | Found while clearing this Mac's failing launchd jobs. `com.praponb.jobs4dent.backup` was exiting 1 every hour with `ERROR: postgres service is not running; nothing backed up` — that stack is stopped on this Mac. The agent has been `launchctl disable`d so it stops failing silently, which fixes the noise and not the problem. **That project's production database is currently unprotected.** Lives in a different repo, so fixing it is out of scope here, but it is the most consequential thing on this page. |

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
  rename to `praponb`, a 24-character password, per-account lockout, and
  mandatory TOTP — but it remains the front door.
- **Backup pulls are manual.** `scripts/pull-backups.sh` copies the server's
  dumps to this Mac, but `com.praponb.inventory.pull-backups.plist` is
  deliberately *not* bootstrapped: this Mac is a cold standby and its value is
  that nothing here starts on its own. Run the script by hand after anything
  that matters, or load the agent on purpose:
  ```bash
  cp scripts/com.praponb.inventory.pull-backups.plist ~/Library/LaunchAgents/
  launchctl bootstrap gui/$(id -u) \
    ~/Library/LaunchAgents/com.praponb.inventory.pull-backups.plist
  ```
- **Email notification delivery is not implemented** (in-app notifications work;
  SMTP dispatch is backlog).
- **`chatbot.praponb.com` shares the server.** Containers `twin` and
  `twin-tunnel`, a separate compose project in `~/twin`. Never
  `docker system prune -a` or bulk-stop containers on that host.

---

## 6. Cloudflare edge protection — the steps

For §3.2. Dashboard-only, free plan. Cannot be verified from the command line,
because the application's own 10/min throttle triggers before a 20/min edge rule
would.

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

Verified 2026-08-31.

**Production — Ubuntu 26.04.1 LTS, `prapon@192.168.1.49`, `~/inventory`**
- Six containers up (28-37h uptime); backend/frontend bound to `127.0.0.1`,
  Postgres and Redis not published at all
- `cloudflared` systemd service active and enabled; `docker` and `containerd`
  enabled at boot; every container `unless-stopped`
- `DEBUG=False`, `config.settings.production`, Redis-backed throttle cache,
  `HTTP_CF_CONNECTING_IP` as the trusted client-IP header
- Data: 100,213 assets, 7 users (2 active: `demo`/viewer, `praponb`/system_admin),
  1 confirmed TOTP device, 10 unused recovery codes
- Attachment storage working, `/app/media` owned by `appuser`
- Deployed SHA matched local `HEAD` when last checked (2026-08-31). Pinning the
  hash here just goes stale — read it instead:
  `ssh prapon@192.168.1.49 'cat ~/inventory/DEPLOYED_COMMIT'`
- `https://inventory.praponb.com` → 200; `https://chatbot.praponb.com` → 200
- Also hosts `chatbot.praponb.com` — leave those containers alone

**Standby — this MacBook**
- All six containers stopped (`stop`, not `down -v`); volumes intact
- Data frozen at cutover; this is a rollback window of hours, not a replica
- Both LaunchAgents re-verified persistently `disabled` on 2026-08-31 via
  `launchctl print-disabled gui/$UID`; no cloudflared process running here
- Tunnel LaunchDaemon confirmed `disabled` in the `system` domain on 2026-08-31
  (`sudo launchctl print-disabled system`), so **this Mac is safe to reboot**.
  The plist is still installed and `RunAtLoad`, so the override is the only
  thing holding it down — re-check with [§8](#8-before-and-after-rebooting-this-mac)
  after any rollback, or if the daemon is ever `enable`d
- `cloudflared` here is **2026.7.3**; the server runs **2026.8.2**. Only matters
  if the Mac is brought back for a rollback
- Holds a second copy of the server's backups in `~/inventory-backups`

**Testing**
- 259 recorded cases: 187 passed, 69 blocked, 2 manual, 1 waived, **0 failed**.
  Most blocks are "browser unavailable" from the original automated QA runs
- Two genuine but minor blocked help-UI cases: `TC-HELP-05` (automated
  accessibility scan) and `TC-HELP-77` (forbidden-register response renders a
  helpful alert)

**Repository**
- Branch `b_pbv_main`
- Rollback procedure: `DEPLOY-UBUNTU.md` §7

---

## 8. Before and after rebooting this Mac

A reboot is the one action that can undo the cutover by accident. `bootout` and
`unload` last only for the current boot; the plists are all still on disk. The
state that survives is the `launchctl disable` override, and only the two
LaunchAgents have been confirmed today — `com.cloudflare.cloudflared` is a root
LaunchDaemon with `RunAtLoad` and `KeepAlive`, so if its override is missing it
comes straight back at boot and Cloudflare load-balances the live hostname
across the server and this Mac's frozen database.

**Last checked 2026-08-31: all three overrides present, this Mac is safe to
reboot.** Re-run the check anyway after a rollback, or after anything that runs
`launchctl enable`.

**Before rebooting** — this is the whole check:

```bash
sudo launchctl print-disabled system | grep cloudflare
```

- `"com.cloudflare.cloudflared" => disabled` → nothing else to do; reboot.
- Absent, or `=> enabled` → run this first, then reboot:
  ```bash
  sudo launchctl disable system/com.cloudflare.cloudflared
  ```

Do **not** delete or rename the plist instead. launchd keys off the `Label`, not
the filename, and the plist is needed as-is for the rollback in
[`DEPLOY-UBUNTU.md`](DEPLOY-UBUNTU.md) §7.

**After rebooting**, confirm the Mac came back inert and production is untouched:

```bash
pgrep -fl cloudflared                 # expect no output
docker ps -q | wc -l                  # expect 0 (Docker Desktop may not even start)
curl -sS -o /dev/null -w '%{http_code}\n' https://inventory.praponb.com/   # 200
curl -sS -o /dev/null -w '%{http_code}\n' https://chatbot.praponb.com/     # 200
```

Nothing on this Mac needs starting afterwards. It is a cold standby by design,
and `scripts/pull-backups.sh` is deliberately manual ([§4](#4-known-gaps-accepted-by-choice)).

---

## 9. The 2026-08-31 outage

The first unplanned outage since the migration. Both public sites were down for
about five hours and returned **Cloudflare error 1033** — the tunnel had no
origin to reach, because the machine holding it was off.

### What happened

| Time (+07) | Event |
|---|---|
| 12:40:04 | Journal stops **mid-line**, during a routine `sysstat-collect` run. No shutdown sequence. |
| 12:40 – 17:46 | Dark. Both hostnames serve 1033. Not reachable by ping, SSH, or even ARP. |
| 17:32 | Outage noticed (`Ray ID a33b5f5cfb8c5d52`, 10:32 UTC). |
| 17:46:42 | Powered back on. Everything returned unattended. |
| 17:59:15 | Deliberate clean `sudo reboot`, to confirm recovery. |

The absence of a shutdown sequence is the whole diagnosis. A kernel panic, an
OOM kill, a thermal trip, `systemd` stopping — all of them write *something*
first. A log that simply ends means the CPU stopped executing between one line
and the next: a power cut, or a hard hang. **Cause still unknown — [3.11](#3-operational-gaps).**

Ruled out along the way: it was not the network (the LAN gateway answered in
~3.7 ms throughout, and a sweep of all 254 addresses found no host with SSH
open, so the box had not merely taken a new DHCP lease); not Cloudflare; and not
disk pressure (7% used).

### What it cost

Nothing, as far as anything can tell:

- Postgres logged `database system was not properly shut down; automatic
  recovery in progress`, ran its end-of-recovery checkpoint, and came up. No
  `PANIC`, no invalid-page or checksum errors.
- **100,213 assets and 7 users** — exactly the counts
  [`DEPLOY-UBUNTU.md`](DEPLOY-UBUNTU.md) §5 check 3 records as correct. 60 audit
  events, up from 49 at migration, which is ordinary growth.
- `DEPLOYED_COMMIT` still `30e0eec`, clean.

### What it proved

- **Unattended recovery works.** The 17:46 boot brought back all six inventory
  containers, `twin`, `twin-tunnel`, and `cloudflared` with nobody touching
  anything — which is exactly what [3.7](#3-operational-gaps) had been waiting
  for someone to witness, and it closed that item.
- **The standby stayed inert, correctly.** Through the whole outage the Mac ran
  no `cloudflared` and zero containers, so there was never a moment when two
  hosts could have claimed the tunnel.

### The rollback that was started and abandoned

With the server apparently dead, the [`DEPLOY-UBUNTU.md`](DEPLOY-UBUNTU.md) §7
rollback to the Mac was begun: Docker Desktop was started and the six stopped
containers confirmed intact. It got no further before the server returned on its
own, and **nothing that claims the tunnel was ever run** — no `docker compose
start`, no `launchctl enable`. Docker Desktop was quit again afterwards, so the
Mac is back to a cold standby rather than merely an idle one.

[§8](#8-before-and-after-rebooting-this-mac) still reads true, and this was
**checked rather than assumed** once the incident closed:
`sudo launchctl print-disabled system | grep cloudflare` returns
`"com.cloudflare.cloudflared" => disabled`. Worth doing even though no
`launchctl enable` ran — §8 asks for the check after any rollback, and "we
never got that far" is reasoning, not observation. That distinction is the
whole point of the check, because the failure it guards against is silent:
nothing warns you at boot.

Origin was confirmed the same way, by evidence rather than inference. Requesting
a unique random path on each public hostname put that path in the **server's**
own container logs for `inventory.praponb.com`; `chatbot.praponb.com` does not
log request paths, but its `twin-tunnel` container is visibly serving
`dest=https://chatbot.praponb.com/…` to `originService=http://twin:7860`. Both
hostnames demonstrably terminate on the server.

Three things surfaced while reading that procedure under time pressure, worth
knowing *before* the next outage rather than during it:

- **§7's first step is `sudo systemctl stop cloudflared` on the server**, to
  release the tunnel. When the server is unreachable that step cannot be run —
  but its *purpose* is already satisfied, because a machine that is off is not
  holding the tunnel. What genuinely matters is the inverse: **once the Mac is
  serving, the server must not be powered on with `cloudflared` still
  `enabled`**, or it rejoins the tunnel and Cloudflare load-balances the
  hostname across two diverging databases. Bring it up with the network
  disconnected and `systemctl disable --now cloudflared` first.
- **The Mac's data is frozen at the cutover**, so rolling back silently reverts
  the database to that moment, and §7's instruction to dump the server's
  database first is impossible in the one situation that most demands a
  rollback — the server being unreachable. A rollback under those conditions
  means accepting stale data *and* a manual reconciliation afterwards. That is
  a judgement call, not a checklist step.
- **`chatbot.praponb.com` has no standby at all.** It exists only on the server,
  so a rollback restores half the outage.

### Worth doing before the next one

A UPS is the direct answer if the cause turns out to be power. Independently:
nothing watches these hostnames, so this outage was found by a person opening
the site roughly five hours in. An uptime check on both hostnames would have
caught it in minutes, and is the cheapest improvement on this page.
