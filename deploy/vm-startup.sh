#!/bin/bash
# Startup script ของ VM (ตั้งผ่าน metadata startup-script โดย scripts/bootstrap-gcp.sh)
# รันในนาม root ทุกครั้งที่ VM boot ต้องรันซ้ำได้
#
# metadata ที่ใช้:
#   repo-url       ที่อยู่ repo แบบ SSH เช่น git@github.com:owner/Hai-Nida.git
#   repo-branch    branch ที่ VM ติดตาม (default: release)
#   poll-interval  ความถี่ที่ VM เช็กโค้ดใหม่ ในรูปแบบ systemd เช่น 5min (default: 5min)
#
# secret ที่ใช้ (Secret Manager): hai-nida-repo-deploy-key และที่ scripts/render-env.sh อ่าน
set -euo pipefail

APP_DIR=/opt/hai-nida
APP_USER=deploy
STATE_DIR=/var/lib/hai-nida
METADATA="http://metadata.google.internal/computeMetadata/v1"

log() {
  echo "hai-nida: $*"
}

metadata() {
  curl -fsS -H "Metadata-Flavor: Google" "$METADATA/$1"
}

attribute() {
  metadata "instance/attributes/$1" 2>/dev/null || true
}

# พิมพ์ค่า secret ออก stdout คืนค่า 1 ถ้าไม่มี secret หรืออ่านไม่ได้
secret() {
  local token project body
  token=$(metadata instance/service-accounts/default/token | jq -r '.access_token')
  project=$(metadata project/project-id)
  body=$(printf 'header = "Authorization: Bearer %s"\n' "$token" |
    curl -fsS -K - "https://secretmanager.googleapis.com/v1/projects/$project/secrets/$1/versions/latest:access" 2>/dev/null) ||
    return 1
  jq -r '.payload.data' <<<"$body" | base64 -d
}

install_packages() {
  if ! command -v jq >/dev/null || ! command -v git >/dev/null; then
    log "ติดตั้ง git, curl, jq"
    apt-get update -q
    DEBIAN_FRONTEND=noninteractive apt-get install -y -q git curl jq ca-certificates
  fi

  if ! command -v docker >/dev/null || ! docker compose version >/dev/null 2>&1; then
    log "ติดตั้ง Docker Engine"
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    chmod a+r /etc/apt/keyrings/docker.asc
    # shellcheck disable=SC1091
    . /etc/os-release
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
      >/etc/apt/sources.list.d/docker.list
    apt-get update -q
    DEBIAN_FRONTEND=noninteractive apt-get install -y -q \
      docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    systemctl enable --now docker
  fi
}

setup_user() {
  if ! id "$APP_USER" >/dev/null 2>&1; then
    log "สร้าง user $APP_USER"
    useradd --create-home --shell /bin/bash "$APP_USER"
  fi
  usermod -aG docker "$APP_USER"
  install -d -o "$APP_USER" -g "$APP_USER" -m 0755 "$STATE_DIR"
}

# เขียน deploy key ใหม่ทุกครั้งที่ boot เพื่อให้การเปลี่ยน key ใน Secret Manager มีผล
setup_deploy_key() {
  local ssh_dir key
  ssh_dir="$(getent passwd "$APP_USER" | cut -d: -f6)/.ssh"
  install -d -o "$APP_USER" -g "$APP_USER" -m 0700 "$ssh_dir"

  if key=$(secret hai-nida-repo-deploy-key); then
    install -o "$APP_USER" -g "$APP_USER" -m 0600 /dev/null "$ssh_dir/id_ed25519"
    printf '%s\n' "$key" >"$ssh_dir/id_ed25519"
  else
    log "ไม่พบ secret hai-nida-repo-deploy-key จะ clone โดยไม่ใช้ deploy key"
  fi

  # host key ของ GitHub จาก API ที่ยืนยันตัวตนด้วย HTTPS แทนการเชื่อ ssh-keyscan
  local known_hosts
  if known_hosts=$(curl -fsS https://api.github.com/meta | jq -r '.ssh_keys[] | "github.com " + .'); then
    printf '%s\n' "$known_hosts" >"$ssh_dir/known_hosts"
    chown "$APP_USER:$APP_USER" "$ssh_dir/known_hosts"
    chmod 0644 "$ssh_dir/known_hosts"
  fi
}

as_app_user() {
  sudo -u "$APP_USER" -H "$@"
}

setup_source() {
  local repo_url="$1" branch="$2"
  if [ ! -d "$APP_DIR/.git" ]; then
    [ -n "$repo_url" ] || { log "ERROR: ไม่ได้ตั้ง metadata repo-url"; exit 1; }
    log "clone $repo_url ($branch)"
    install -d -o "$APP_USER" -g "$APP_USER" -m 0755 "$APP_DIR"
    as_app_user git clone --branch "$branch" "$repo_url" "$APP_DIR"
  elif [ -n "$repo_url" ]; then
    as_app_user git -C "$APP_DIR" remote set-url origin "$repo_url"
  fi
}

install_update_timer() {
  local interval="$1"
  cat >/etc/systemd/system/hai-nida-update.service <<EOF
[Unit]
Description=Hai-Nida: pull and deploy new commits
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=$APP_USER
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/scripts/vm-update.sh
EOF

  cat >/etc/systemd/system/hai-nida-update.timer <<EOF
[Unit]
Description=Hai-Nida: check for new commits every $interval

[Timer]
OnBootSec=$interval
OnUnitActiveSec=$interval

[Install]
WantedBy=timers.target
EOF

  systemctl daemon-reload
  systemctl enable hai-nida-update.timer
  systemctl restart hai-nida-update.timer
}

install_backup_cron() {
  if ! as_app_user crontab -l 2>/dev/null | grep -q "hai-nida-chromadb-backup"; then
    # VM ใช้เวลา UTC: 20:00 UTC = 03:00 เวลาไทย
    log "ติดตั้ง cron backup ChromaDB"
    as_app_user bash "$APP_DIR/setup-backup-cron.sh" "0 20 * * *" >/dev/null
  fi
}

main() {
  local repo_url branch interval
  repo_url=$(attribute repo-url)
  branch=$(attribute repo-branch)
  branch="${branch:-release}"
  interval=$(attribute poll-interval)
  [[ "$interval" =~ ^[0-9]+(s|min|h)$ ]] || interval=5min

  install_packages
  setup_user
  setup_deploy_key
  setup_source "$repo_url" "$branch"
  install_update_timer "$interval"

  log "ขึ้นระบบจาก branch $branch"
  if as_app_user "$APP_DIR/scripts/vm-update.sh" --force; then
    log "ready"
  else
    log "failed (ดู log ด้วย journalctl -u google-startup-scripts)"
  fi

  install_backup_cron
}

main "$@"
