# Horus VPS Deploy (Paper Live-Linked)

## 1) System packages
```bash
sudo apt update
sudo apt install -y python3.11 python3.11-venv git build-essential postgresql postgresql-contrib tmux curl
```

## 2) Postgres
```bash
sudo -u postgres psql << 'SQL'
CREATE USER horus WITH PASSWORD 'CHANGE_ME_STRONG';
CREATE DATABASE horus OWNER horus;
GRANT ALL PRIVILEGES ON DATABASE horus TO horus;
SQL
```

## 3) Repo + venv
```bash
cd ~
git clone <YOUR_REPO_URL> horus
cd horus
python3.11 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
cp .env.example .env
```

## 4) Init schema
```bash
source .venv/bin/activate
python -m horus.db.init_schema
```

## 5) Install systemd user units
```bash
mkdir -p ~/.config/systemd/user
cp deploy/systemd/horus-paper.service ~/.config/systemd/user/
cp deploy/systemd/horus-nightly.service ~/.config/systemd/user/
cp deploy/systemd/horus-nightly.timer ~/.config/systemd/user/

systemctl --user daemon-reload
systemctl --user enable --now horus-paper.service
systemctl --user enable --now horus-nightly.timer
sudo loginctl enable-linger $USER
```

## 6) Verify linked runtime
```bash
systemctl --user status horus-paper.service
journalctl --user -u horus-paper.service -f
```

## 7) Verify nightly outputs
```bash
systemctl --user list-timers | grep horus
ls -lah ~/horus/horus/data/reports/
```

## Runtime modules used
- `python -m horus.runtime.run_paper`
- `python -m horus.ops.run_nightly`
