# CyDust Bot

A Telegram bot that monitors and reports air quality data from Cyprus air quality stations.

## Features

- Hourly air quality updates for 11 monitoring stations across Cyprus
- On-demand data queries with the `/check` command
- Customizable notification filters based on air quality status
- Detailed air quality analysis with health recommendations
- Automatic duplicate detection and data validation

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Telegram Bot Token (from [@BotFather](https://t.me/botfather))

### Local Development

1. Clone the repository:
```bash
git clone <your-repo-url>
cd cydustbot
```

2. Set your Telegram token:
```bash
export TELEGRAM_TOKEN="your-token-here"
```

3. Run with Docker Compose:
```bash
docker-compose up --build
```

### Available Commands

- `/start` - Subscribe to air quality updates
- `/stop` - Unsubscribe from updates
- `/check` - View latest data for your selected station
- `/check <station>` - View data for a specific station
- `/filter` - Set notification filter preferences (all, yellow+, orange+, red only)
- `/status` - View your current settings
- `/test` - Test bot responsiveness

## Deployment with GitHub Actions

This project includes automated deployment to your VPS using GitHub Actions.

### Initial VPS Setup

1. SSH into your VPS and clone the repository:
```bash
cd ~
git clone <your-repo-url> cydust
cd cydust
```

2. Create a `.env` file with your Telegram token:
```bash
echo "TELEGRAM_TOKEN=your-token-here" > .env
```

3. Update `docker-compose.yml` to use the .env file:
```yaml
environment:
  - TELEGRAM_TOKEN=${TELEGRAM_TOKEN}
  - TZ=Asia/Nicosia
env_file:
  - .env
```

4. Start the bot:
```bash
docker-compose up -d
```

### GitHub Secrets Setup

Configure the following secrets in your GitHub repository (Settings → Secrets and variables → Actions):

| Secret | Description | Example |
|--------|-------------|---------|
| `VPS_HOST` | Your VPS IP address or hostname | `123.45.67.89` |
| `VPS_USER` | SSH username | `ubuntu` or `root` |
| `VPS_SSH_KEY` | Private SSH key for authentication | Contents of `~/.ssh/id_rsa` |
| `VPS_PORT` | SSH port (optional, defaults to 22) | `22` |
| `DEPLOY_PATH` | Path to project on VPS (optional) | `~/cydust` |

### How to Get Your SSH Key

On your local machine:
```bash
# Generate a new SSH key if you don't have one
ssh-keygen -t rsa -b 4096 -C "github-actions"

# Copy the public key to your VPS
ssh-copy-id -i ~/.ssh/id_rsa.pub user@your-vps-ip

# Display the private key to add to GitHub secrets
cat ~/.ssh/id_rsa
```

Copy the entire output (including `-----BEGIN RSA PRIVATE KEY-----` and `-----END RSA PRIVATE KEY-----`) and paste it into the `VPS_SSH_KEY` secret in GitHub.

### Deployment Process

Once configured, deployment is automatic:

1. Push code to the `main` or `master` branch
2. GitHub Actions automatically:
   - Connects to your VPS via SSH
   - Pulls the latest code
   - Rebuilds the Docker image
   - Restarts the containers
   - Shows deployment logs

You can also trigger deployment manually from the GitHub Actions tab.

### Monitoring Deployment

View deployment status and logs:
- GitHub: Actions tab in your repository
- VPS: `docker-compose logs -f cydust-bot`

## Architecture

### Components

- **cydust.py** - Telegram bot interface
- **scraper.py** - Data collection service
- **supervisord** - Process manager for running both services

### Timing

- Scraper runs at :20 past each hour (website updates between :15-:19)
- Bot sends notifications at :25 past each hour
- 5-minute delay ensures fresh data availability

### Database

Two SQLite databases:
- **subscribers.db** - User subscriptions and preferences
- **stations.db** - Air quality data for 11 stations

## Troubleshooting

### Check Container Status
```bash
docker-compose ps
docker-compose logs --tail=50 cydust-bot
```

### Rebuild After Code Changes
```bash
docker-compose build
docker-compose up -d
```

### Manual Database Check
```bash
docker exec -it cydust_cydust-bot_1 sqlite3 /app/stations.db "SELECT * FROM station03 ORDER BY id DESC LIMIT 5;"
```

## Development Notes

See [CLAUDE.md](CLAUDE.md) for detailed development documentation.

## License

This project is open source and available for personal use.
