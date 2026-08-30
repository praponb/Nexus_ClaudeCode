# Deploying Asset Inventory on an Ubuntu host

Runbook for moving `inventory.praponb.com` off the MacBook and onto an
always-on **Ubuntu 26.04 LTS** machine on the LAN, keeping the same tunnel and
hostname.

Target host: `prapon@192.168.1.49`, deployment at `~/inventory`.

> ### ✅ Executed 2026-08-29
>
> The cutover is **done**. `inventory.praponb.com` is served from the Ubuntu
> server; the MacBook is a cold standby with its containers stopped, volumes
> intact, and both LaunchAgents unloaded. Verified after cutover: all public
> endpoints 200, HSTS and the full security-header set present on Django-served
> paths, data identical (100,213 assets / 7 users / 1 TOTP device / 10 recovery
> codes), and the login throttle still cutting off at 10 despite rotating
> `X-Forwarded-For`. This document is now the operations runbook and the
> rollback procedure rather than a plan.

### Verified state of the target host (2026-08-29)

| | |
|---|---|
| OS / arch | Ubuntu **26.04.1 LTS** (`resolute`), **amd64**, kernel 7.0.0-30 |
| Hardware | 8 vCPU, 13 GiB RAM, 417 GB free of 468 GB |
| Docker | **already installed** — 29.7.2, Compose v5.4.0, at `/usr/local/bin/docker` (**not** apt-managed) |
| cloudflared | **not installed** |
| coreutils | **uutils 0.8.0** — the Rust reimplementation, not GNU |
| `~/inventory` | exists, empty |
| Ports 3000 / 8000 / 5432 / 6379 | all free |
| sudo | **requires a password** — see below |

Three consequences worth knowing before you start:

- **Docker is not apt-managed.** It sits in `/usr/local/bin` and no `.deb` owns
  it, so it was installed by the convenience script rather than the repo.
  `provision-ubuntu.sh` detects a working `docker` + `docker compose` and skips
  its own install, so this is fine — but `apt upgrade` will never update Docker
  on this host. Worth converting to the apt packages later.
- **uutils coreutils is confirmed present**, so the smoke test in section 2 is
  not hypothetical. Run it.
- **This box is not idle.** It already serves `chatbot.praponb.com` from two
  containers (`twin`, and `twin-tunnel` running `cloudflare/cloudflared:latest`),
  up 10 days with `restart: unless-stopped`. The inventory stack coexists —
  different tunnel, no port overlap — but **do not `docker system prune -a` or
  stop containers indiscriminately on this host**; you would take that site down.

> **Correcting an earlier finding.** When the Mac's `twin-chatbot` LaunchAgent
> was disabled, `chatbot.praponb.com` stayed up and I concluded "something else
> in the Cloudflare account routes it." The real answer is here: a containerised
> cloudflared on *this* server has been serving it for 10 days. The Mac's
> `~/.cloudflared/twin-chatbot-config.yml` was simply a stale leftover, which is
> why stopping it changed nothing.

Companion documents:
[SESSION-2026-08-28-SECURITY.md](SESSION-2026-08-28-SECURITY.md) (how the app
got to its current security posture), [CLAUDE.md](CLAUDE.md) (invariants that
must not be weakened), [scripts/ScriptUserGuide.md](scripts/ScriptUserGuide.md).

---

## 0. Why this move

The app currently runs on a laptop. That makes uptime a function of the lid
being open and Docker Desktop behaving — the reason
`com.nexus.inventory-autostart` exists at all is that Docker Desktop was found
to leave containers `Exited` after a restart despite `restart: unless-stopped`.
On Linux that whole class of problem disappears: Docker is a system service and
the restart policy simply works.

## 1. What moves, and what must not

| Item | Source | Notes |
|---|---|---|
| Code | this Mac's working tree | `scripts/sync-to-server.sh` (rsync) — no GitHub credentials on the server |
| Stack definition | `compose.yaml` | unchanged; same file works on Linux |
| App config + secrets | root `.env` | **app subset only** — use `scripts/export-app-env.sh` |
| Database | `nexus_claudecode_postgres_data` | via `pg_dump`, not a volume copy |
| Attachments | `nexus_claudecode_backend_media` | `backup.sh` now tars this too |
| Tunnel credentials | `~/.cloudflared/<TUNNEL_ID>.json` | secret; mode 600, root-owned |
| Tunnel ingress | `~/.cloudflared/config.yml` | template: `scripts/templates/cloudflared-config.yml` |
| Backup schedule | LaunchAgent plist | replaced by `scripts/inventory-backup.{service,timer}` |

**Does not move:**

- `MODEL_*`, `AGENTIC_BUILDER_*`, `GEMINI_API_KEY`, `POSTGRES_URL` — these belong
  to the `agentic_builder` orchestrator, not the web app. `export-app-env.sh`
  is an allowlist precisely so these cannot ride along by accident.
- `~/inventory-credentials-20260828.txt` — human account passwords. These belong
  in a password manager, not on a server.
- `com.nexus.inventory-autostart` — a Docker Desktop workaround. Porting it to
  Linux would be cargo-culting a fix for a problem that does not exist there.

**Two facts that make this migration cheaper than it looks:**

- **TOTP secrets and recovery codes live in the database**
  (`accounts_totpdevice`, `accounts_mfarecoverycode`). They travel with the
  dump, so authenticator apps keep working — nobody re-enrols.
- **The audit hash-chain is plain sha256, not keyed by `DJANGO_SECRET_KEY`**
  ([backend/apps/audit/services.py:23](backend/apps/audit/services.py#L23)), so
  `verify_chain()` stays valid across the move and across a later key rotation.

**Architecture note:** the Mac is arm64 and the Ubuntu box is most likely amd64.
Do **not** copy Docker images. The stack is rebuilt from source on the server
using the same Dockerfiles and the same `postgres:18-alpine`, so there is no
version skew to manage.

---

## 2. Provision the server (once)

**Target: Ubuntu 26.04 LTS "Resolute"**. Realistic minimum: 2 vCPU, 4 GB RAM,
40 GB disk.

> **Order of operations.** The provisioning script lives in the repo, and the
> repo reaches the server by rsync rather than `git clone` — so run the sync in
> [section 3](#3-stand-the-stack-up-no-traffic-yet) *first*, then come back here.
> One command from the Mac: `./scripts/sync-to-server.sh`.

Ubuntu's release metadata marks `resolute` **`Supported: 1`** — a normal LTS with
security updates into 2031, so `unattended-upgrades` does real work here and the
host patches itself:

```bash
curl -s https://changelogs.ubuntu.com/meta-release | grep -A4 'Dist: resolute'
```

Everything in this section is encoded in
[`scripts/provision-ubuntu.sh`](scripts/provision-ubuntu.sh), including the
cloudflared workaround, the Docker-source repair, and the tooling smoke test. It
is idempotent, so re-running it is safe:

```bash
# --- on the server, after scripts/sync-to-server.sh has run (section 3) ---
cd ~/inventory && ./scripts/provision-ubuntu.sh --lan 192.168.1.0/24
```

It refuses to run without `--lan`: enabling ufw's default-deny policy with no
SSH allow rule locks you out of a remote machine permanently, and that is the
one mistake here that needs physical access to undo.

The manual equivalent, step by step:

```bash
# --- on the server ---
sudo apt update && sudo apt upgrade -y
sudo apt install -y ca-certificates curl gnupg ufw unattended-upgrades

# Confirm the release before adding any third-party repo keyed to its codename.
. /etc/os-release && echo "$VERSION_ID $VERSION_CODENAME"   # expect: 26.04 resolute

# Docker Engine + Compose plugin from Docker's own repo. The distro's
# docker.io package lags and ships no `docker compose` subcommand.
# Verified 2026-08-29: Docker DOES publish a `resolute` suite, amd64 + arm64.
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"   # log out and back in for this to take effect
```

If Docker ever drops `resolute`, pin that one line to the most recent published
codename (`noble`) instead of the host's own — the packages are built against
glibc and run fine:

```bash
# fallback only, if `apt update` 404s on the docker suite
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu noble stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list
```

### Shell tooling — verify before trusting the scripts

Ubuntu now ships **Rust reimplementations as defaults**: `uutils` in place of GNU
coreutils, and `sudo-rs` in place of sudo (introduced in 25.10, carried into
26.04). They are close to drop-in but not
identical, and `scripts/backup.sh` leans on `date`, `du`, `ls -1t`, and
`tail -n +N`. Confirm they behave before the backup timer is the thing that
discovers otherwise:

```bash
date -u +%Y%m%d-%H%M%SZ                 # expect e.g. 20260829-031500Z
du -h /etc/hostname | cut -f1           # expect a size, not an error
ls -1t /etc | tail -n +3 | head -2      # expect two filenames
tar --version | head -1                 # tar and gzip are NOT coreutils
```

If any of these misbehave, install GNU coreutils alongside
(`sudo apt install -y coreutils`) rather than rewriting the scripts — the Mac
runs the same `backup.sh` and the two must not drift.

Firewall — nothing needs to be open inbound. Cloudflare Tunnel dials **out**,
and compose binds the app to `127.0.0.1` only:

```bash
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow from 192.168.0.0/16 to any port 22 proto tcp   # adjust to your LAN
sudo ufw enable
```

> **Docker and UFW:** Docker writes its own iptables rules that bypass UFW for
> published ports. That is not a hole here *only because* `compose.yaml`
> publishes to `127.0.0.1:8000` and `127.0.0.1:3000` rather than `0.0.0.0`.
> Keep it that way — changing those bindings would expose the app to the whole
> LAN regardless of what UFW says.

SSH hardening: `ssh-copy-id` from the Mac, verify key login works, *then* set
`PasswordAuthentication no` and `PermitRootLogin no` in
`/etc/ssh/sshd_config.d/99-hardening.conf` and `sudo systemctl reload ssh`.

The deployment runs as the server's `prapon` account out of `~/inventory`, so
there is no service account to create — `provision-ubuntu.sh` adds `prapon` to
the `docker` group, which is all that is needed.

> Note the spelling: the server account is **`prapon`**, while this Mac's account
> and the Django admin user are both **`praponb`**. They are easy to confuse and
> an `ssh` to the wrong one just fails with a permission error.

---

## 3. Stand the stack up (no traffic yet)

Production stays on the Mac throughout this section. Nothing here is
user-visible.

```bash
# --- on the Mac ---
./scripts/sync-to-server.sh                 # -> prapon@192.168.1.49:~/inventory/
./scripts/sync-to-server.sh --dry-run       # preview first, if you prefer
```

The script refuses to run with uncommitted changes (`--allow-dirty` overrides),
and writes `DEPLOYED_COMMIT` into the transfer so the server itself records the
SHA it is running — otherwise that fact exists only in this Mac's working tree.

The repo is private, and rsync keeps GitHub credentials off the deployment host
entirely — no deploy key, no token, nothing to leak from a public-facing machine.

It ships ~14 MB. The excluded `node_modules` (359 MB) and the two `.venv`s
(768 MB) are **compiled arm64 binaries from this Mac**; copying them onto an
amd64 server would put broken native modules exactly where the Docker build
expects to create working ones. Both are regenerated inside the images.

`.env` and `backups/` are excluded for correctness, not size — the server keeps
its own. rsync does not delete excluded paths on the receiver, so `--delete`
prunes stale files without ever touching them.

> **The trade-off:** the server has no git history and no `git pull`. **This Mac
> is the source of truth for what is deployed.** Commit before syncing, or you
> will not be able to tell later what is actually running out there.

```bash
# --- on the Mac ---
./scripts/export-app-env.sh app.env
scp app.env prapon@192.168.1.49:~/inventory/.env
rm app.env      # do not leave a second copy of the secrets lying around
```

The exported file is already correct for the server — `APP_ENV=production`,
`DJANGO_SETTINGS_MODULE=config.settings.production`,
`BACKEND_BUILD_TARGET=production`, `TRUSTED_CLIENT_IP_HEADER=HTTP_CF_CONNECTING_IP`
— because the Mac is already running the production configuration. No edits
needed. Confirm anyway:

```bash
# --- on the server ---
chmod 600 ~/inventory/.env
grep -E '^(APP_ENV|DJANGO_SETTINGS_MODULE|BACKEND_BUILD_TARGET|DJANGO_DEBUG)=' ~/inventory/.env
cd ~/inventory && docker compose build && docker compose up -d
```

The first build is slow (Nuxt build plus `uv sync`). Then rehearse the restore
with any existing dump, to prove the pipeline before it matters:

```bash
scp backups/asset-inventory-<stamp>.sql.gz prapon@192.168.1.49:~/inventory/backups/
# --- on the server ---
APP_ENV=local ./scripts/restore.sh backups/asset-inventory-<stamp>.sql.gz
./scripts/migrate.sh
```

`restore.sh` refuses to run with `APP_ENV=production` — that guard is correct
and deliberate. Override it on the command line for this one rehearsal rather
than editing the script.

Verify without the tunnel. The app only answers to its real hostname, so send
an explicit `Host` header:

```bash
# BOTH headers are required. Host, because the app only answers to its real
# name; X-Forwarded-Proto, because production sets SECURE_SSL_REDIRECT and 301s
# every plain-HTTP request otherwise. cloudflared sets both in normal operation,
# so this reproduces what the app actually sees.
curl -sS -H 'Host: inventory.praponb.com' -H 'X-Forwarded-Proto: https' \
  http://127.0.0.1:8000/api/v1/health/ready/          # -> {"status":"ready"}
curl -sS -o /dev/null -w '%{http_code}\n' -H 'Host: inventory.praponb.com' \
  http://127.0.0.1:3000/login

# DEBUG must be False in the RUNNING container, not just in the repo.
docker compose exec -T backend python -c \
  "import django,os;os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings.production');django.setup();from django.conf import settings;print('DEBUG:',settings.DEBUG)"
```

---

## 4. Cutover

> **One tunnel, one host.** Running the same tunnel from two machines makes
> Cloudflare load-balance across both connections — with a database on each,
> users get served from whichever host their request happened to land on. Every
> step below is strictly serialized for that reason.

Expected downtime: about five minutes, dominated by dumping and restoring 50 MB.

```bash
# --- 1. Freeze the Mac. The watchdog FIRST, or it resurrects the stack in <5 min.
launchctl unload ~/Library/LaunchAgents/com.nexus.inventory-autostart.plist
launchctl unload ~/Library/LaunchAgents/com.praponb.inventory.backup.plist

# --- 2. Stop the inventory tunnel on the Mac. The site goes down here.
#        It is a ROOT LaunchDaemon with KeepAlive, so `kill` will not do it —
#        launchd restarts it 5s later. Bootout is the only thing that sticks.
sudo launchctl bootout system/com.cloudflare.cloudflared
ps aux | grep '[c]loudflared'   # confirm ONLY the inventory one went away

# --- 3. Final backup. pg_dump takes an MVCC snapshot, so it is consistent.
cd ~/GitHub/Nexus_ClaudeCode && ./scripts/backup.sh

# --- 4. Stop the Mac stack. `stop`, NEVER `down -v` — the volumes are the standby.
docker compose stop

# --- 5. Ship the data.
scp backups/asset-inventory-<stamp>.sql.gz \
    backups/asset-inventory-media-<stamp>.tar.gz \
    prapon@192.168.1.49:~/inventory/backups/
```

```bash
# --- 6. Restore on the server.
cd ~/inventory
APP_ENV=local ./scripts/restore.sh backups/asset-inventory-<stamp>.sql.gz
./scripts/migrate.sh
# -u root is required: backend_media is root-owned while the container runs as
# appuser. See the attachment-permissions note in section 8.
docker compose exec -T -u root backend sh -c 'tar -xzf - -C /app/media' \
  < backups/asset-inventory-media-<stamp>.tar.gz

# --- 7a. Install cloudflared. NOT from Cloudflare's apt repo — see below.
ARCH=$(dpkg --print-architecture)          # amd64 or arm64
curl -fsSL -o /tmp/cloudflared.deb \
  "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${ARCH}.deb"
sudo dpkg -i /tmp/cloudflared.deb && rm -f /tmp/cloudflared.deb
cloudflared --version

# --- 7b. Move the tunnel.
sudo mkdir -p /etc/cloudflared
sudo cp <TUNNEL_ID>.json /etc/cloudflared/        # scp'd from ~/.cloudflared on the Mac
sudo chown root:root /etc/cloudflared/<TUNNEL_ID>.json
sudo chmod 600 /etc/cloudflared/<TUNNEL_ID>.json
sudo cp ~/inventory/scripts/templates/cloudflared-config.yml /etc/cloudflared/config.yml
sudo sed -i "s/<TUNNEL_ID>/<the actual uuid>/g" /etc/cloudflared/config.yml
sudo cloudflared service install
sudo systemctl enable --now cloudflared
sudo systemctl status cloudflared
```

> ### Cloudflare's apt repo has no 26.04 suite
>
> Being an LTS does not help here — Cloudflare simply has not published for
> 26.04. Verified 2026-08-29:
>
> | Suite | `pkg.cloudflare.com/cloudflared` |
> |---|---|
> | `resolute` (26.04 LTS) | **404** |
> | `questing` (25.10) | 404 |
> | `noble` (24.04 LTS) | 200 |
> | `jammy` (22.04 LTS) | 200 |
>
> So the documented `apt install cloudflared` path does not work here. Two ways
> round it:
>
> 1. **The direct `.deb` above** (what this runbook does). cloudflared is a
>    static Go binary with no distro coupling; both `amd64` and `arm64` assets
>    return 200. Cost: no `apt upgrade` — you update it by re-running that
>    `curl | dpkg -i`. Put a reminder somewhere, because a stale tunnel client
>    is exactly what you do not want holding up a public site. (The Mac's copy
>    is already behind: 2026.7.3 against 2026.8.2 available.)
> 2. **Pin the repo to `noble`** (the newest suite Cloudflare publishes) and let
>    apt manage upgrades:
>    ```bash
>    echo "deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] \
>    https://pkg.cloudflare.com/cloudflared noble main" \
>      | sudo tee /etc/apt/sources.list.d/cloudflared.list
>    ```
>    Works in practice, but you are telling apt the host is something it is not.
>
> Re-check periodically: once Cloudflare publishes a `resolute` suite, the plain
> `apt install cloudflared` path becomes available and both workarounds retire.

`cert.pem` is needed only for tunnel *management* (`tunnel create` / `route`),
not for `tunnel run` — copy it only if you want to manage tunnels from the
server.

The tunnel UUID is not a secret (it is the public DNS CNAME target,
`<TUNNEL_ID>.cfargotunnel.com`). The `.json` next to it **is** — it is the
tunnel's credential.

### How the tunnel runs on the Mac today

Verified on 2026-08-29:

| Tunnel | Config | Runs as | Started by | State |
|---|---|---|---|---|
| **inventory** (the one that moves) | `~/.cloudflared/config.yml` | **root** | `/Library/LaunchDaemons/com.cloudflare.cloudflared.plist` | running |
| jobs4dent | `~/.cloudflared/jobs4dent-config.yml` | praponb | `com.praponb.jobs4dent.tunnel` | **disabled 2026-08-29** |
| twin-chatbot | `~/.cloudflared/twin-chatbot-config.yml` | praponb | `com.praponb.twin.tunnel` | **disabled 2026-08-29** |

The inventory tunnel is now the only cloudflared process on this Mac, which
makes cutover simpler: stopping cloudflared here stops exactly one thing.

`brew services` reports cloudflared as `none` — the Homebrew service manages
none of these. Do not try to stop them that way.

> **Renaming a plist does not disable it.** Two of these were prefixed
> `disabled-` in `~/Library/LaunchAgents/`, and both were still loaded and
> running: launchd keys off the `Label` inside the file, not the filename, and
> an already-loaded job survives a rename regardless. The state that actually
> persists is `launchctl disable`, recorded in launchd's override database and
> visible via `launchctl print-disabled gui/$UID`. To re-enable:
> `launchctl enable gui/$UID/<label>` then
> `launchctl bootstrap gui/$UID ~/Library/LaunchAgents/<file>.plist`.

The daemon sets `KeepAlive { SuccessfulExit: false }` with a 5-second
`ThrottleInterval`, so killing the process just makes launchd start it again.
Use `bootout`. To restore it during a rollback:
`sudo launchctl bootstrap system /Library/LaunchDaemons/com.cloudflare.cloudflared.plist`.

---

## 5. Verification

Work through all of these before calling the migration done.

| # | Check | Expected |
|---|---|---|
| 0 | `. /etc/os-release && echo $VERSION_ID` | `26.04` — confirm the host is what the runbook assumes |
| 1 | `docker compose ps` | six services up; postgres/redis healthy; only `127.0.0.1:8000` and `127.0.0.1:3000` published |
| 2 | `curl -I https://inventory.praponb.com/` | 200, HSTS header present |
| 3 | Row counts vs. the Mac | 100,213 assets, 7 users, 49 audit events |
| 4 | `verify_chain()` on the audit log | **`False` on both hosts** — expected, and explained in section 8 (a deleted actor, not tampering). Match the Mac's result, don't expect `True`; `python manage.py audit_chain_report` says why |
| 5 | Sign in as `demo` in a browser | works; read-only (no create/edit, no audit view) |
| 6 | Sign in as `praponb` with the **existing** authenticator | accepted — proves the TOTP secret survived |
| 7 | 11 failed logins with rotating `X-Forwarded-For` | still cuts off at 10 |
| 8 | `settings.DEBUG` in the running container | `False` |
| 9 | `sudo reboot`, wait | stack returns on its own; site stays up |
| 10 | `sudo systemctl start inventory-backup.service` | a dump and a media tarball land in `backups/` |
| 11 | `cloudflared --version` | a current release — it is not apt-managed here, so nothing will update it for you |

Check 7 is the important one: it proves both that throttle counters are in a
*shared* Redis (not per-worker `LocMemCache`) and that `client_ip.py` is still
ignoring the caller-supplied `X-Forwarded-For` on the new host. Both were real
bugs here once; see [CLAUDE.md](CLAUDE.md) security invariants.

---

## 6. Operations on the new host

**Auto-start.** Nothing to build. `restart: unless-stopped` in `compose.yaml`
plus an enabled `docker.service` covers reboots. Do not port the macOS watchdog.

**Backups.** `scripts/backup.sh` runs unchanged and now captures the attachment
volume alongside the database:

```bash
sudo cp ~/inventory/scripts/inventory-backup.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now inventory-backup.timer
systemctl list-timers inventory-backup.timer
```

Retention is `BACKUP_KEEP=14` (set in the unit file) and prunes both the `.sql.gz`
dumps and the `.tar.gz` media tarballs.

> A backup on the same disk as the database is not a backup. Add an off-host
> copy — `rsync` to another machine or an object store — once the migration has
> settled.

**Patching.** `unattended-upgrades` was installed during provisioning and does
real work on an LTS: 26.04 receives security updates into 2031. Confirm it is
actually enabled rather than merely installed:

```bash
systemctl status unattended-upgrades --no-pager
sudo unattended-upgrade --dry-run --debug 2>&1 | tail -20
```

The containers are patched separately — `python:3.12-slim`, `node:22-slim`,
`postgres:18-alpine` and `redis:7-alpine` are rebuilt from upstream, so a
`docker compose build --pull` picks up base-image fixes independently of the
host's own updates. Do that periodically; host patching alone does not update
what actually serves traffic.

**Updating cloudflared.** It is not apt-managed here (section 4), so it will
never update itself:

```bash
ARCH=$(dpkg --print-architecture)
curl -fsSL -o /tmp/cloudflared.deb \
  "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${ARCH}.deb"
sudo dpkg -i /tmp/cloudflared.deb && rm -f /tmp/cloudflared.deb
sudo systemctl restart cloudflared
```

**Updating the app.**

```bash
# --- on the Mac: commit, then push the tree across
git commit -am "..." && ./scripts/sync-to-server.sh

# --- on the server
cd ~/inventory
./scripts/backup.sh            # always, before anything else
docker compose build && docker compose up -d
./scripts/migrate.sh
```

There is no `git pull` here — the server has no remote. Updates always originate
from this Mac.

---

## 7. The Mac as cold standby

> ### ⚠️ Unloading a LaunchAgent does not survive a reboot
>
> This is the single most dangerous thing about the standby Mac, and it was
> nearly discovered the hard way on 2026-08-29 when a restart was proposed.
>
> `launchctl unload` and `launchctl bootout` affect only the **current boot**.
> The plists are still on disk, so on the next restart launchd loads all three
> again:
>
> - `com.nexus.inventory-autostart` → `docker compose up -d` → the Mac's stale
>   stack comes back
> - `com.cloudflare.cloudflared` (root, `RunAtLoad`) → **a second connector on
>   the same tunnel**
>
> Cloudflare then load-balances between the two connectors, so visitors are
> served at random from either the real server or the Mac's frozen copy of the
> database. Writes land in whichever they happened to reach.
>
> The state that *does* persist is `launchctl disable`, recorded in launchd's
> override database:
>
> ```bash
> launchctl disable gui/$UID/com.nexus.inventory-autostart
> launchctl disable gui/$UID/com.praponb.inventory.backup
> sudo launchctl disable system/com.cloudflare.cloudflared     # needs root
> ```
>
> Verify with `launchctl print-disabled gui/$UID` and
> `sudo launchctl print-disabled system`. All three were disabled on
> 2026-08-29, and **all three overrides were read back and confirmed still
> present on 2026-08-31** — the two agents in the `gui` domain and
> `com.cloudflare.cloudflared` in `system`. That check is the one that matters:
> until it has been run, "the tunnel is stopped" only means stopped *now*. Re-enabling them is part of the rollback below — and note that
> `launchctl enable` is required before `bootstrap` will do anything.



After cutover the Mac keeps its stopped containers, its volumes, and its
`backups/`. Both LaunchAgents stay unloaded so nothing restarts behind your back.

**Its data freezes at the moment of cutover.** This is a rollback window measured
in hours, not an ongoing replica — do not mistake it for one.

To roll back, in this order:

```bash
# --- on the server: release the tunnel before anything else claims it
sudo systemctl stop cloudflared

# --- on the Mac. `enable` first: these are persistently disabled, and
#     bootstrap/load silently does nothing against a disabled job.
cd ~/GitHub/Nexus_ClaudeCode && docker compose start
launchctl enable gui/$UID/com.nexus.inventory-autostart
launchctl enable gui/$UID/com.praponb.inventory.backup
launchctl load ~/Library/LaunchAgents/com.nexus.inventory-autostart.plist
launchctl load ~/Library/LaunchAgents/com.praponb.inventory.backup.plist
sudo launchctl enable system/com.cloudflare.cloudflared
sudo launchctl bootstrap system /Library/LaunchDaemons/com.cloudflare.cloudflared.plist
```

If the site has taken real traffic on Ubuntu, dump that database before rolling
back or you will lose it.

---

## 8. What actually happened, and what is still open

### Things that differed from the plan

Worth reading before the next deployment — every one of these cost time.

| Expectation | Reality |
|---|---|
| `apt install cloudflared` works on an LTS | Cloudflare publishes **no `resolute` suite** — 404. Installed from the release `.deb`, which means apt will never update it. |
| Docker would need installing | Already present (29.7.2) but **not apt-managed** (`/usr/local/bin/docker`, convenience script), so `apt upgrade` will never update it either. |
| coreutils is GNU | It is **uutils 0.8.0**, the Rust reimplementation. The smoke test in section 2 is not hypothetical — run it. |
| The server was idle | It already served `chatbot.praponb.com` from two containers, up 10 days. Never `docker system prune -a` there. |
| `sudo` would be available to automation | It requires a password. The entire app deployment turned out to need **no root at all** — only cloudflared, ufw, systemd units and `/etc/cloudflared` did. |
| The health check returns 200 | It returns **301** without `X-Forwarded-Proto: https`, because production sets `SECURE_SSL_REDIRECT`. |
| `docker compose exec` can restore media | Fails without `-u root`; the volume is root-owned. |
| macOS `rsync` accepts modern flags | It is **openrsync**, which rejects `--info=`. A sync appeared to succeed while transferring nothing. |

### Two pre-existing defects

Neither was caused by the move — both reproduced identically on the standby Mac,
which was live production until 2026-08-29. They are recorded here because the
migration is what surfaced them. **Both were resolved on 2026-08-30**; the
resolutions are noted inline below, and the full account is in
[`SESSION-2026-08-29-ISSUES.md`](SESSION-2026-08-29-ISSUES.md) §2.

**1. Attachment uploads are broken (production).** The `backend_media` volume is
`root:root`, while the backend container runs as `appuser` (uid 10001). The real
code path fails:

```
>>> store_upload(uuid4(), b'hello', 'txt')
PermissionError: [Errno 13] Permission denied: '/app/media/attachments'
```

This is why the media volume is empty — nothing was ever successfully written.
Any user who has tried to attach a file to an asset got an error. The fix is a
`chown` of the media directory in `backend/Dockerfile` before `USER appuser`, so
freshly created volumes inherit `appuser` ownership, plus a one-off
`docker run --rm -v inventory_backend_media:/m alpine chown -R 10001:10001 /m`
for volumes that already exist.

> **FIXED 2026-08-30.** The Dockerfile now runs
> `mkdir -p /app/media` in the same layer as the chown — creating the directory
> *in the image* is what makes Docker give a new volume the right ownership. The
> existing volume was chowned, the stack rebuilt, and a real `store_upload` call
> verified in production: file written, owned by uid 10001, then removed.

**2. `verify_chain()` returns `False`.** Seven audit events (ids 403–409, all
`auth.*`: login, logout, `mfa.enroll`, `mfa.verify`) have `record_hash` values
that do not recompute from their stored payload. The chain *links* are intact —
every `prev_hash` matches — so this is not a broken or truncated chain; it is
seven individual records whose self-hash disagrees with their content. They are
the newest events, written during the 2FA work.

`reseal_chain()` in `apps/audit/services.py` would make the check pass, but it
recomputes hashes from whatever is stored — it papers over the discrepancy
rather than explaining it, and destroys the evidence needed to diagnose it.

> **EXPLAINED 2026-08-30, and still not resealed.** All seven rows are accounted
> for by a single deleted user (`75c2cb8f-…`) — a second `system_admin` created
> and deleted during the 2FA work, **not** the old `admin` account, which was
> renamed to `praponb` and kept its UUID. `AuditEvent.actor` is
> `on_delete=SET_NULL` and `_payload_for()` hashes `actor.uuid`, so deleting a
> user rewrites the payload of every event they caused while leaving `prev_hash`
> untouched — links intact, individual rows disagreeing. Bookkeeping, not
> tampering. Reproduce with `python manage.py audit_chain_report`, which is
> read-only. The genuine finding underneath: **the deletion itself was never
> audited.**

### Still outstanding

A consolidated, verified list lives in
[`SESSION-2026-08-29-ISSUES.md`](SESSION-2026-08-29-ISSUES.md) — prefer it over
this section, which is scoped to the migration.

- **cloudflared updates are manual** on this host — see section 6. Re-check
  whether Cloudflare has published a `resolute` suite; once they do, switch to
  the apt-managed path and this item retires.
- **The server has no git history.** Deployment provenance depends on this Mac's
  working tree being committed before each sync. A deploy key and `git clone`
  would fix that later without disturbing anything else.
- **The `inventory-backup` systemd timer is not installed yet** — production
  currently has no scheduled backup. Section 6 has the commands; it needs root.
- Off-host backup copies (see section 6). The dumps sit on the same disk as the
  database they protect, which covers bad migrations but not drive failure.
- **A reboot of the server has not been tested.** Boot resilience was verified
  structurally (`docker`, `containerd`, `cloudflared` all `enabled`; every
  container `unless-stopped`) but not proven by an actual restart.
- The Cloudflare edge rate-limiting rule and Bot Fight Mode are still not
  configured; they are independent of this migration.
- Move `~/inventory-credentials-20260828.txt` into a password manager and
  delete it — it holds the human account passwords and predates this migration.
- Consider rotating `DJANGO_SECRET_KEY` and `POSTGRES_PASSWORD` once settled — a
  host change is a natural rotation point. Rotating the secret key only logs
  everyone out; it does not affect the audit chain.
