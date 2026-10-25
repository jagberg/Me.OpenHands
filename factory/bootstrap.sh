#!/usr/bin/env bash
# Set up the factory on a Mac. Safe to re-run: every step checks before it acts. No sudo, no system settings.
#   factory/bootstrap.sh                          trial repo (jagberg/ai-agent-trial-sandbox)
#   factory/bootstrap.sh --repo org/name          your repo: writes ~/.config/factory/target.json + overlay to edit
#   factory/bootstrap.sh --langfuse               also start local Langfuse (traces), see observability/langfuse
# Then: cd factory && caffeinate -dimsu .venv/bin/python app.py   (keep the Mac on mains power)
set -euo pipefail
cd "$(dirname "$0")"
ROOT=$(cd .. && pwd); CFG="$HOME/.config/factory"; REPO=""; LANGFUSE=0
while [ $# -gt 0 ]; do case $1 in --repo) REPO=$2; shift 2;; --langfuse) LANGFUSE=1; shift;; *) echo "unknown $1"; exit 2;; esac; done
ok() { printf '  ok  %s\n' "$*"; }; step() { printf '\n== %s\n' "$*"; }; die() { printf '  !!  %s\n' "$*"; exit 1; }

step "Tools"
missing=""
for t in git gh docker ollama uv python3; do command -v $t >/dev/null || missing="$missing $t"; done
[ -z "$missing" ] || die "missing:$missing  -> install: brew install git gh uv ollama; Docker Desktop from docker.com"
ok "git gh docker ollama uv python3"
mem=$(( $(sysctl -n hw.memsize) / 1073741824 ))
[ "$mem" -ge 32 ] && ok "${mem} GB RAM" || echo "  ..  ${mem} GB RAM: qwen3.8:27b needs about 20 GB free; expect swapping"

step "GitHub"
gh auth status >/dev/null 2>&1 || die "run: gh auth login"
ok "gh logged in"
if [ -n "$REPO" ]; then gh repo view "$REPO" --json name >/dev/null || die "gh cannot see $REPO"; ok "can see $REPO"; fi

step "Docker agent image"
docker info >/dev/null 2>&1 || die "start Docker Desktop"
IMAGE=$(sed -n 's/^SERVER_IMAGE = os.environ.get("AGENT_SERVER_IMAGE", "\([^"]*\)").*/\1/p' shell.py)
docker image inspect "$IMAGE" >/dev/null 2>&1 || docker pull "$IMAGE"
ok "$IMAGE"

step "Local model"
curl -s -o /dev/null http://127.0.0.1:11434 || die "start Ollama (open the app or: ollama serve)"
if ! ollama show qwen3.8-27b-32k >/dev/null 2>&1; then
  ollama pull qwen3.8:27b && ollama create qwen3.8-27b-32k -f "$ROOT/bakeoff/harness/Modelfile.qwen38-32k"
fi
ok "qwen3.8-27b-32k (32k context)"

step "Python venv"
[ -x .venv/bin/python ] || uv venv -q .venv --python 3.12
uv pip install -q --python .venv/bin/python -r requirements.txt
.venv/bin/python test_metrics.py >/dev/null && ok "venv + self-check"

step "ignite plugin"
ls -d "$HOME"/.claude/plugins/cache/compareclub-ignite/ignite/*/skills >/dev/null 2>&1 \
  && ok "found (copied into each run, never committed)" || die "install the CompareClub ignite plugin in Claude Code"

step "Config ($CFG)"
mkdir -p "$CFG"; chmod 700 "$CFG"
if [ -n "$REPO" ]; then
  [ -d "$CFG/overlay" ] || { cp -R overlay-template "$CFG/overlay"; ok "overlay copied: EDIT $CFG/overlay/knowledge/project.md"; }
  if [ ! -f "$CFG/target.json" ]; then
    printf '{\n  "repo": "%s",\n  "test_cmd": "EDIT: host command that runs the repo tests, e.g. npm test",\n  "protected": [],\n  "overlay_dir": "%s"\n}\n' \
      "$REPO" "$CFG/overlay" > "$CFG/target.json"
    ok "target.json written: EDIT test_cmd and protected"
  else ok "target.json exists (left as is)"; fi
else ok "no --repo: runs use the trial repo"; fi

if [ $LANGFUSE = 1 ]; then
  step "Langfuse (local, 127.0.0.1)"
  if [ ! -f "$CFG/langfuse-server.env" ]; then
    (umask 077
     PK="pk-lf-$(uuidgen | tr A-Z a-z)"; SK="sk-lf-$(uuidgen | tr A-Z a-z)"
     printf '%s\n' "NEXTAUTH_SECRET=$(openssl rand -base64 32)" "SALT=$(openssl rand -base64 32)" \
       "ENCRYPTION_KEY=$(openssl rand -hex 32)" LANGFUSE_INIT_ORG_ID=factory LANGFUSE_INIT_ORG_NAME=Factory \
       LANGFUSE_INIT_PROJECT_ID=factory LANGFUSE_INIT_PROJECT_NAME=factory "LANGFUSE_INIT_PROJECT_PUBLIC_KEY=$PK" \
       "LANGFUSE_INIT_PROJECT_SECRET_KEY=$SK" LANGFUSE_INIT_USER_EMAIL=admin@factory.local \
       "LANGFUSE_INIT_USER_NAME=Factory admin" "LANGFUSE_INIT_USER_PASSWORD=$(openssl rand -base64 18 | tr -d '/+=')" \
       > "$CFG/langfuse-server.env"
     printf 'LANGFUSE_PUBLIC_KEY=%s\nLANGFUSE_SECRET_KEY=%s\n' "$PK" "$SK" > "$CFG/langfuse.env")
    ok "secrets generated (mode 600; login password: grep PASSWORD $CFG/langfuse-server.env)"
  fi
  (cd "$ROOT/observability/langfuse" && docker compose -p langfuse --env-file "$CFG/langfuse-server.env" up -d --quiet-pull)
  for _ in $(seq 60); do curl -sf -o /dev/null http://127.0.0.1:3000/api/public/health && break; sleep 3; done
  curl -sf -o /dev/null http://127.0.0.1:3000/api/public/health && ok "http://127.0.0.1:3000 (admin@factory.local)" || die "Langfuse not healthy: docker compose -p langfuse logs"
fi

step "Next"
echo "  1. Telegram (optional): see factory/README.md"
[ -n "$REPO" ] && echo "  2. Edit $CFG/target.json and $CFG/overlay/knowledge/project.md"
echo "  3. cd factory && caffeinate -dimsu .venv/bin/python app.py   -> http://127.0.0.1:8766  (on mains power)"
