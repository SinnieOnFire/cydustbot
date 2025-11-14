# CyDust Bot

A Telegram bot that monitors and reports air quality data from Cyprus air quality stations.

## Features

- Hourly air quality updates for 11 monitoring stations across Cyprus
- On-demand data queries with the `/check` command
- Customizable notification filters based on air quality status
- Detailed air quality analysis with health recommendations
- Automatic duplicate detection and data validation
- **Automated deployment** - Push code to GitHub, deploys to VPS in ~24 seconds

## Bot Commands

- `/start` - Subscribe to air quality updates
- `/stop` - Unsubscribe from updates
- `/check` - View latest data for your selected station
- `/check <station>` - View data for a specific station
- `/filter` - Set notification filter preferences (all, yellow+, orange+, red only)
- `/status` - View your current settings
- `/test` - Test bot responsiveness

## Quick Start

### Local Development

```bash
# Clone and run locally
git clone https://github.com/SinnieOnFire/cydustbot.git
cd cydustbot
export TELEGRAM_TOKEN="your-token-here"
docker-compose up --build
```

### Production Deployment

**Prerequisites**: Docker, Docker Compose, VPS with SSH access

#### 1. VPS Setup

```bash
# SSH to your VPS
ssh user@your-vps-ip

# Clone repository
git clone https://github.com/SinnieOnFire/cydustbot.git /home/user/cydust
cd /home/user/cydust

# Create environment file
echo "TELEGRAM_TOKEN=your-actual-token" > .env

# Start bot
docker-compose up -d
docker-compose logs -f cydust-bot
```

#### 2. GitHub Actions Setup

Enable automated deployment by configuring GitHub Secrets.

**Add these secrets**:

| Secret | Value |
|--------|-------|
| `VPS_HOST` | Your VPS IP (e.g., `123.45.67.89`) |
| `VPS_USER` | SSH username (e.g., `root`) |
| `VPS_SSH_KEY` | Private SSH key (see below) |
| `DEPLOY_PATH` | Absolute path (e.g., `/home/user/cydust`) |

**SSH Key Setup**:

```bash
# On local machine: Generate key
ssh-keygen -t ed25519 -C "github-actions" -f ~/.ssh/cydustbot_deploy

# Copy public key to VPS
cat ~/.ssh/cydustbot_deploy.pub
# Paste into VPS: ~/.ssh/authorized_keys

# Copy private key to GitHub Secret
cat ~/.ssh/cydustbot_deploy
# Paste entire output into VPS_SSH_KEY secret
```

#### 3. Deploy

```bash
# Make changes locally
git add .
git commit -m "Your changes"
git push  # Automatically deploys in ~24 seconds
```

## Architecture

**Components**:
- `cydust.py` - Telegram bot (notifications at :25 past hour)
- `scraper.py` - Data collector (runs at :20 past hour)
- `supervisord` - Process manager for both services
- `stations.db` - Air quality data (11 stations)
- `subscribers.db` - User subscriptions and preferences

**Deployment**:
- Code lives on GitHub
- GitHub Actions auto-deploys on push to `main`
- VPS runs Docker container with both services
- Databases and `.env` persist outside container

## Troubleshooting

```bash
# Check bot status
docker-compose ps
docker-compose logs --tail=50 cydust-bot

# Restart after manual changes
docker-compose build
docker-compose up -d

# Check database
docker exec -it cydust_cydust-bot_1 sqlite3 /app/stations.db \
  "SELECT * FROM station03 ORDER BY id DESC LIMIT 5;"
```
