#!/usr/bin/env bash
# Provision an Ubuntu 26.04 LTS host to run the Asset Inventory stack.
# Companion to DEPLOY-UBUNTU.md section 2. Run ON THE SERVER, not the Mac.
#
# Usage:
#   ./scripts/provision-ubuntu.sh --lan 192.168.1.0/24
#   ./scripts/provision-ubuntu.sh --lan 192.168.1.0/24 --skip-firewall
#
# Idempotent: safe to re-run. Installs nothing that is already present.
#
# TARGET: Ubuntu 26.04 LTS "resolute" (Supported: 1, patched into 2031).
# Two things still need handling on 26.04:
#   1. Cloudflare's apt repo publishes only `noble` and `jammy` -- there is NO
#      `resolute` suite (verified 2026-08-29), so the documented
#      `apt install cloudflared` does not work. It is installed from its
#      release .deb instead, which means apt will not update it afterwards.
#   2. Ubuntu now defaults to Rust reimplementations (uutils coreutils,
#      sudo-rs). backup.sh depends on date/du/ls/tail, so they are smoke-tested
#      here rather than assumed.
set -euo pipefail

LAN_CIDR=""
SKIP_FIREWALL=0

while [ $# -gt 0 ]; do
  case "$1" in
    --lan) LAN_CIDR="${2:-}"; shift 2 ;;
    --skip-firewall) SKIP_FIREWALL=1; shift ;;
    -h|--help) sed -n '2,10p' "$0"; exit 0 ;;
    *) echo "ERROR: unknown argument '$1'" >&2; exit 2 ;;
  esac
done

say() { echo; echo "==> $*"; }
warn() { echo "WARNING: $*" >&2; }

# -- Preflight ----------------------------------------------------------------

if [ ! -f /etc/os-release ]; then
  echo "ERROR: no /etc/os-release -- this is not the Ubuntu server." >&2
  exit 1
fi
. /etc/os-release

say "Host: ${PRETTY_NAME:-unknown} ($(dpkg --print-architecture))"

if [ "${VERSION_ID:-}" != "26.04" ]; then
  warn "expected Ubuntu 26.04 LTS, found '${VERSION_ID:-unknown}'."
  warn "The codename-specific repo handling below is tuned for 'resolute'."
  read -r -p "Continue anyway? [y/N] " reply
  [ "${reply:-}" = "y" ] || exit 1
fi

# Refuse to enable a firewall without being told what may reach SSH. Enabling
# ufw with a default-deny policy and no allow rule locks you out of a remote
# box permanently -- the one mistake here that needs physical access to undo.
if [ "$SKIP_FIREWALL" -eq 0 ] && [ -z "$LAN_CIDR" ]; then
  echo "ERROR: --lan <cidr> is required (e.g. --lan 192.168.1.0/24)." >&2
  echo "       It is the SSH allow rule. Without it, enabling ufw would lock" >&2
  echo "       you out of this machine. Pass --skip-firewall to leave ufw alone." >&2
  exit 2
fi

# -- Repair conflicting Docker apt sources ------------------------------------
#
# apt 3.x refuses to read the ENTIRE source list -- not just the offending file
# -- when two entries describe the same repo with different Signed-By values:
#
#   Error: Conflicting values set for option Signed-By regarding source
#          https://download.docker.com/linux/ubuntu/ resolute
#   E: The list of sources could not be read.
#
# This happens after following Docker's docs (which use docker.asc) and then a
# guide that uses docker.gpg, leaving two entries behind. Nothing installs until
# it is cleared, so check before the first `apt-get update` rather than dying on
# it. We keep the .list this script manages and move any others aside.

say "Checking for conflicting Docker apt sources"
DOCKER_SRC_FILES=()
while IFS= read -r f; do
  [ -n "$f" ] && DOCKER_SRC_FILES+=("$f")
done < <(grep -rl "download\.docker\.com" /etc/apt/sources.list /etc/apt/sources.list.d/ 2>/dev/null || true)

if [ "${#DOCKER_SRC_FILES[@]}" -gt 1 ]; then
  warn "Found ${#DOCKER_SRC_FILES[@]} files declaring the Docker repo:"
  printf '      %s\n' "${DOCKER_SRC_FILES[@]}"
  warn "apt cannot read its source list while these disagree. Keeping"
  warn "/etc/apt/sources.list.d/docker.list and disabling the rest."
  for f in "${DOCKER_SRC_FILES[@]}"; do
    if [ "$f" != "/etc/apt/sources.list.d/docker.list" ]; then
      sudo mv -f "$f" "${f}.disabled-by-provision"
      echo "      moved aside: ${f} -> ${f}.disabled-by-provision"
    fi
  done
elif [ "${#DOCKER_SRC_FILES[@]}" -eq 1 ]; then
  echo "    one Docker source file, no conflict: ${DOCKER_SRC_FILES[0]}"
else
  echo "    none yet (added below)"
fi

# -- Base packages ------------------------------------------------------------

say "Updating apt and installing base packages"
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg ufw unattended-upgrades

# -- Docker -------------------------------------------------------------------

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  say "Docker already present: $(docker --version)"
else
  say "Installing Docker Engine + Compose plugin from Docker's own apt repo"
  sudo install -m 0755 -d /etc/apt/keyrings
  if [ ! -f /etc/apt/keyrings/docker.gpg ]; then
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
      | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  fi

  # Docker publishes a `resolute` suite (verified 2026-08-29), but check rather
  # than assume -- if it is ever dropped, fall back to the newest LTS codename.
  # The packages are built against glibc and run fine on a later release.
  DOCKER_SUITE="${VERSION_CODENAME:-noble}"
  if ! curl -fsS -o /dev/null "https://download.docker.com/linux/ubuntu/dists/${DOCKER_SUITE}/Release"; then
    warn "Docker publishes no '${DOCKER_SUITE}' suite; falling back to 'noble'."
    DOCKER_SUITE=noble
  fi

  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu ${DOCKER_SUITE} stable" \
    | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
  sudo apt-get update
  sudo apt-get install -y docker-ce docker-ce-cli containerd.io \
    docker-buildx-plugin docker-compose-plugin
  sudo systemctl enable --now docker
  sudo usermod -aG docker "$USER"
  warn "Added $USER to the 'docker' group -- log out and back in for it to apply."
fi

# -- cloudflared --------------------------------------------------------------

if command -v cloudflared >/dev/null 2>&1; then
  say "cloudflared already present: $(cloudflared --version 2>&1 | head -1)"
else
  # Cloudflare's apt repo carries only `noble` and `jammy`; `resolute` and
  # `questing` both 404 (verified 2026-08-29). Being an LTS does not help --
  # 26.04 simply is not published yet. cloudflared is a static Go binary, so
  # the release .deb is a clean substitute, at the cost of no apt updates.
  say "Installing cloudflared from its release .deb (no apt suite for 26.04)"
  ARCH="$(dpkg --print-architecture)"
  curl -fsSL -o /tmp/cloudflared.deb \
    "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-${ARCH}.deb"
  sudo dpkg -i /tmp/cloudflared.deb
  rm -f /tmp/cloudflared.deb
  warn "cloudflared is NOT apt-managed. Update it by re-running this install."
fi

# -- Firewall -----------------------------------------------------------------

if [ "$SKIP_FIREWALL" -eq 1 ]; then
  say "Skipping firewall configuration (--skip-firewall)"
else
  say "Configuring ufw: deny inbound, allow SSH from ${LAN_CIDR}"
  # Order matters: the allow rule must exist before the policy is enforced.
  sudo ufw allow from "${LAN_CIDR}" to any port 22 proto tcp
  sudo ufw default deny incoming
  sudo ufw default allow outgoing
  sudo ufw --force enable
  sudo ufw status verbose
  warn "Docker bypasses ufw for PUBLISHED ports. This host is only safe because"
  warn "compose.yaml binds to 127.0.0.1 -- never change those to 0.0.0.0."
fi

# -- Shell tooling smoke test (uutils coreutils) -------------------------------------------

say "Smoke-testing shell tooling that scripts/backup.sh depends on"
FAILED=0
check() {
  local label="$1"; shift
  if out="$("$@" 2>&1)"; then
    printf '    ok   %-28s %s\n' "$label" "$(echo "$out" | head -1)"
  else
    printf '    FAIL %-28s %s\n' "$label" "$(echo "$out" | head -1)"
    FAILED=$((FAILED + 1))
  fi
}
check "date -u +stamp"  date -u +%Y%m%d-%H%M%SZ
check "du -h"           du -h /etc/hostname
check "tar --version"   tar --version
check "gzip --version"  gzip --version
if ! ls -1t /etc | tail -n +3 | head -2 | grep -q .; then
  printf '    FAIL %-28s\n' "ls -1t | tail -n +N"
  FAILED=$((FAILED + 1))
else
  printf '    ok   %-28s\n' "ls -1t | tail -n +N"
fi

if [ "$FAILED" -gt 0 ]; then
  warn "${FAILED} tool check(s) failed. Ubuntu ships uutils in place of GNU"
  warn "coreutils; install GNU coreutils rather than editing backup.sh, which"
  warn "is shared with the Mac and must not drift:  sudo apt install -y coreutils"
fi

say "Provisioning complete."
cat <<'EOF'
    Next (DEPLOY-UBUNTU.md section 3):
      1. Log out and back in, so docker group membership applies.
      2. On the Mac:  ./scripts/export-app-env.sh app.env
                      scp app.env prapon@<host>:~/inventory/.env
      3. docker compose build && docker compose up -d
EOF
