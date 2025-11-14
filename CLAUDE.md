# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

CyDust Bot is a Telegram bot that monitors and reports air quality data from Cyprus air quality stations. It consists of two main components:
1. A web scraper that collects data from the official Cyprus air quality website
2. A Telegram bot that provides hourly notifications and on-demand data to users

## Key Commands

### Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run the scraper manually
python scraper.py

# Run the bot (requires TELEGRAM_TOKEN environment variable)
export TELEGRAM_TOKEN="your-token-here"
python cydust.py
```

### Deployment
```bash
# Build and run with Docker Compose
docker-compose up --build -d

# View logs
docker-compose logs -f

# Stop the service
docker-compose down
```

## Architecture

### Core Components

1. **cydust.py** - Telegram bot interface
   - Handles user subscriptions and notifications
   - Sends hourly updates at :25 past each hour
   - Uses SQLite database for subscriber management
   - Supports status-based notification filtering

2. **scraper.py** - Data collection service
   - Runs every hour at :15 past
   - Scrapes https://www.airquality.dli.mlsi.gov.cy/
   - Stores data in SQLite database with station-specific tables

3. **Process Management**
   - Both services run in a single Docker container
   - Supervised by supervisord for automatic restarts
   - Logs available in ./logs directory

### Database Schema

**subscribers.db**
- `user_id` (INTEGER PRIMARY KEY)
- `selected_station` (TEXT)
- `status_filter` (TEXT DEFAULT 'all') - Filter for notification status levels

**stations.db**
- Tables: `station01` through `station11`
- Columns: `id`, `status`, `pm_10`, `pm_2_5`, `o3`, `no`, `no2`, `nox`, `so2`, `co`, `c6h6`, `update_time`

### Important Timing
- Scraper runs at :20 past each hour (website updates between :15-:19)
- Bot notifications sent at :25 past each hour
- 5-minute delay ensures fresh data availability
- Scraper checks for duplicate timestamps before inserting data
- This timing ensures users receive current hour data (e.g., 19:00 data at 19:25)

### Key Features
- Duplicate checking prevents inserting the same timestamp multiple times
- Enhanced logging shows website timestamps and insertion status
- Batch data fetching optimizes notification sending
- `/check` command shows last 5 database entries for debugging
- Status-based notification filtering (all, yellow+, orange+, red only)
- `/filter` command to set notification preferences
- `/status` command to view current settings
- **Air Quality Analysis**: Descriptive messages explain what each status means
  - Analyzes pollutant levels (PM10, PM2.5, O3, NO2, SO2, CO)
  - Provides health recommendations based on air quality status
  - Identifies likely pollution sources (dust storms, vehicle emissions, ozone on hot days)
  - Messages are user-friendly and actionable

### Deployment & Troubleshooting

#### Docker Deployment
- **IMPORTANT**: The bot runs inside Docker container `cydust_cydust-bot_1`
- To update code: rebuild Docker image with `docker-compose build` then `docker-compose up -d`
- Simply updating files on host without rebuilding will have no effect
- Container mounts: databases and logs are persisted, but code is baked into image

#### Common Issues & Solutions
1. **Commands not working**: 
   - In python-telegram-bot v20.6, MessageHandler with `filters.TEXT` catches commands too
   - Solution: Add command skip in select_station or use handler groups
   - Commands must be defined at module level, not inside main()

2. **Bot not updating after code changes**:
   - Check if running in Docker: `docker ps | grep cydust`
   - If in Docker, must rebuild: `docker-compose build && docker-compose up -d`
   - If using supervisor directly, check which Python: `/cydust/bin/python`

3. **Duplicate timestamps in database**:
   - Caused by format change: "Updated on: DD/MM/YYYY HH:MM" → "DD/MM/YYYY HH:MM"
   - Scraper now strips "Updated on:" prefix and checks for duplicates

#### Debug Commands
```bash
# Check container status
docker ps | grep cydust
docker-compose logs --tail=50 cydust-bot

# Test bot commands
/test - Verify bot is responsive
/check - Show last 5 timestamps for your selected station
/check Limassol - Show data for specific station (partial match works)
/filter - Set notification filter preferences
/status - Show current station and filter settings

# Manual database check
docker exec -it cydust_cydust-bot_1 sqlite3 /app/stations.db "SELECT * FROM station03 ORDER BY id DESC LIMIT 5;"
```

### Lessons Learned
- Always check if service runs in Docker before debugging
- Handler registration order matters in python-telegram-bot
- Supervisor paths must be container-relative, not host-relative
- Website update timing can vary; scraper at :20 gives sufficient buffer

### Environment Variables
- `TELEGRAM_TOKEN` - Required for bot authentication
- `TZ=Asia/Nicosia` - Cyprus timezone for correct scheduling

### Setting Up & Updating the Bot

#### Updating Bot Code
When you modify any Python files (cydust.py, scraper.py) or configuration files:

```bash
# 1. Copy updated files to server

# 2. SSH into server

# 3. Navigate to bot directory
cd /home/user/cydust

# 4. Rebuild Docker image (REQUIRED - files are baked into image)
docker-compose build

# 5. Restart container with new image
docker-compose up -d

# 6. Check logs to ensure bot started correctly
docker-compose logs -f cydust-bot
```

**Important**: Simply copying files is NOT enough - you MUST rebuild the Docker image for changes to take effect!