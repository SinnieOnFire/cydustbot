import logging
import subprocess
import sqlite3
import os
from datetime import datetime, timedelta

from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, MessageHandler, Job, filters, CallbackQueryHandler

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.INFO)

logger = logging.getLogger(__name__)

# Mapping of station names to SQLite table names
station_table_mapping = {
    "Nicosia: Traffic Station": "station01",
    "Nicosia: Residential Station": "station02",
    "Limassol: Traffic Station": "station03",
    "Larnaca: Traffic Station": "station04",
    "Paphos: Traffic Station": "station05",
    "Ayia Marina Xyliatou: Background Station": "station06",
    "Zygi: Industrial Station": "station07",
    "Mari: Industrial Station": "station08",
    "Paralimni: Traffic Station": "station09",
    "Kalavasos Industrial Station": "station10",
    "Ormidia Industrial Station": "station11"
}

# Mapping of pollutant labels for bot message
key_mapping = {
    "status": "Status",
    "pm_10": "PM₁₀",
    "pm_2_5": "PM₂.₅",
    "o3": "O₃",
    "no": "NO",
    "no2": "NO₂",
    "nox": "NOx",
    "so2": "SO₂",
    "co": "CO",
    "c6h6": "C₆H₆",
    "update_time": "Timestamp"
}

# Pollutant thresholds based on EU/Cyprus standards (μg/m³)
pollutant_thresholds = {
    "pm_10": {"low": 50, "moderate": 100, "high": 200},
    "pm_2_5": {"low": 25, "moderate": 50, "high": 100},
    "o3": {"low": 100, "moderate": 140, "high": 180},
    "no2": {"low": 100, "moderate": 200, "high": 400},
    "so2": {"low": 125, "moderate": 350, "high": 500},
    "co": {"low": 10000, "moderate": 20000, "high": 30000}
}

def analyze_air_quality(data_dict):
    """Analyze air quality data and generate descriptive message."""
    status = data_dict.get('status', '')
    messages = []
    
    # Parse numeric values from strings (handles values with units like "69.6 μg/m³")
    def parse_value(val):
        if val and val != 'None':
            try:
                # Remove units by taking only the numeric part before any space
                # Also handle comma as decimal separator
                numeric_part = val.split()[0] if ' ' in val else val
                return float(numeric_part.replace(',', '.'))
            except:
                return None
        return None
    
    pm10 = parse_value(data_dict.get('pm_10'))
    pm25 = parse_value(data_dict.get('pm_2_5'))
    o3 = parse_value(data_dict.get('o3'))
    no2 = parse_value(data_dict.get('no2'))
    so2 = parse_value(data_dict.get('so2'))
    co = parse_value(data_dict.get('co'))
    
    # Pollutant health impact descriptions (based on WHO/EPA 2025 guidelines)
    health_impacts = {
        'pm_10': ('PM₁₀ (coarse particles)', 'Irritates airways, worsens asthma, aggravates heart/lung disease'),
        'pm_2_5': ('PM₂.₅ (fine particles)', 'Penetrates lungs/bloodstream causing cardiovascular disease, stroke, lung cancer'),
        'o3': ('Ozone (O₃)', 'Inflames airways, triggers asthma, reduces lung function, causes chronic bronchitis'),
        'no2': ('Nitrogen dioxide (NO₂)', 'Aggravates asthma, reduces lung function, increases respiratory infections'),
        'so2': ('Sulfur dioxide (SO₂)', 'Causes wheezing, chest tightness, shortness of breath, worsens heart disease'),
        'co': ('Carbon monoxide (CO)', 'Reduces oxygen to organs (heart/brain), causes headaches, dizziness, fatigue')
    }

    # Pollutant sources for Cyprus (based on Cyprus Air Quality data and research)
    pollutant_sources = {
        'pm_10': 'Saharan/Middle Eastern dust storms (~50 days/year), local traffic, construction',
        'pm_2_5': 'Vehicle exhaust, power generation, industrial facilities, regional transport',
        'o3': 'Forms from traffic NOx + heat/sunlight (Eastern Mediterranean climate factor)',
        'no2': 'Urban traffic (2-4x higher in cities), diesel vehicles, ships, aviation',
        'so2': 'Power generation, cement production, industrial facilities, ship emissions',
        'co': 'Vehicle exhaust, incomplete combustion from traffic congestion'
    }

    # Analyze each pollutant
    high_pollutants = []
    moderate_pollutants = []

    if pm10:
        if pm10 > pollutant_thresholds['pm_10']['high']:
            high_pollutants.append(('pm_10', pm10, 'very high'))
        elif pm10 > pollutant_thresholds['pm_10']['moderate']:
            high_pollutants.append(('pm_10', pm10, 'high'))
        elif pm10 > pollutant_thresholds['pm_10']['low']:
            moderate_pollutants.append(('pm_10', pm10, 'moderate'))

    if pm25:
        if pm25 > pollutant_thresholds['pm_2_5']['high']:
            high_pollutants.append(('pm_2_5', pm25, 'very high'))
        elif pm25 > pollutant_thresholds['pm_2_5']['moderate']:
            high_pollutants.append(('pm_2_5', pm25, 'high'))
        elif pm25 > pollutant_thresholds['pm_2_5']['low']:
            moderate_pollutants.append(('pm_2_5', pm25, 'moderate'))

    if o3:
        if o3 > pollutant_thresholds['o3']['high']:
            high_pollutants.append(('o3', o3, 'very high'))
        elif o3 > pollutant_thresholds['o3']['moderate']:
            high_pollutants.append(('o3', o3, 'high'))
        elif o3 > pollutant_thresholds['o3']['low']:
            moderate_pollutants.append(('o3', o3, 'moderate'))

    if no2:
        if no2 > pollutant_thresholds['no2']['high']:
            high_pollutants.append(('no2', no2, 'very high'))
        elif no2 > pollutant_thresholds['no2']['moderate']:
            high_pollutants.append(('no2', no2, 'high'))
        elif no2 > pollutant_thresholds['no2']['low']:
            moderate_pollutants.append(('no2', no2, 'moderate'))

    if so2:
        if so2 > pollutant_thresholds['so2']['high']:
            high_pollutants.append(('so2', so2, 'very high'))
        elif so2 > pollutant_thresholds['so2']['moderate']:
            high_pollutants.append(('so2', so2, 'high'))
        elif so2 > pollutant_thresholds['so2']['low']:
            moderate_pollutants.append(('so2', so2, 'moderate'))

    if co:
        if co > pollutant_thresholds['co']['high']:
            high_pollutants.append(('co', co, 'very high'))
        elif co > pollutant_thresholds['co']['moderate']:
            high_pollutants.append(('co', co, 'high'))
        elif co > pollutant_thresholds['co']['low']:
            moderate_pollutants.append(('co', co, 'moderate'))
    
    # Generate descriptive message based on status and pollutants
    if status == '🔴':
        if high_pollutants:
            pollutant_names = [health_impacts[p[0]][0] for p in high_pollutants[:2]]  # Top 2 pollutants
            messages.append(f"❗ Warning! Severe air pollution: very high levels of {' and '.join(pollutant_names)}.")
            messages.append("Avoid outdoor activities. Keep windows closed.")
        else:
            messages.append("❗ Warning! Poor air quality detected!")
            messages.append("Avoid going outdoors, especially if you're sensitive.")

    elif status == '🟠':
        if high_pollutants:
            pollutant_names = [health_impacts[p[0]][0] for p in high_pollutants[:2]]
            messages.append(f"❗ Warning! High levels of {' and '.join(pollutant_names)}!")
            messages.append("Sensitive groups should reduce outdoor activity.")
        elif moderate_pollutants:
            messages.append(f"❗ Warning! Elevated {health_impacts[moderate_pollutants[0][0]][0]} levels.")
            messages.append("Consider limiting extended time outdoors.")
        else:
            messages.append("❗ Warning! Moderate to high air pollution.")
            messages.append("Some individuals may feel effects during outdoor activity.")

    elif status == '🟡':
        if moderate_pollutants:
            pollutant_names = [health_impacts[p[0]][0] for p in moderate_pollutants[:2]]
            messages.append(f"Attention: moderate levels of {' and '.join(pollutant_names)}.")
            messages.append("Air quality acceptable for most people.")
        else:
            messages.append("Moderate air quality.")
            messages.append("Sensitive individuals may want to limit outdoor time.")

    elif status == '🟢':
        messages.append("Good air quality!")
        messages.append("Safe for all outdoor activities.")

    # List elevated pollutants with health impacts
    if high_pollutants or moderate_pollutants:
        messages.append("")  # Blank line separator

        # Combine and sort by severity
        all_concerning = high_pollutants + moderate_pollutants
        if all_concerning:
            messages.append("⚠️ Elevated pollutants:")
            for pollutant_key, value, level in all_concerning[:3]:  # Show top 3
                name, health_impact = health_impacts[pollutant_key]
                messages.append(f"• {name}: {value:.1f} μg/m³ ({level})")
                messages.append(f"  {health_impact}")

        # Add source information for the most elevated pollutant
        messages.append("")  # Blank line
        dominant_pollutants = high_pollutants if high_pollutants else moderate_pollutants
        top_pollutant = dominant_pollutants[0][0]  # Get the key of the most concerning pollutant

        # Add appropriate emoji and source info
        if top_pollutant in ['pm_10', 'pm_2_5']:
            messages.append(f"💨 Common sources: {pollutant_sources[top_pollutant]}")
            # Add specific dust storm context for Cyprus when PM10 is high
            if top_pollutant == 'pm_10' and pm10 and pm10 > 100:
                messages.append("🌍 Note: Cyprus experiences African/Middle Eastern dust ~50 days/year")
        elif top_pollutant == 'o3':
            messages.append(f"☀️ Formation: {pollutant_sources[top_pollutant]}")
        elif top_pollutant == 'no2':
            messages.append(f"🚗 Common sources: {pollutant_sources[top_pollutant]}")
        elif top_pollutant == 'so2':
            messages.append(f"🏭 Common sources: {pollutant_sources[top_pollutant]}")
        elif top_pollutant == 'co':
            messages.append(f"🚗 Common sources: {pollutant_sources[top_pollutant]}")

    return '\n'.join(messages) if messages else None

# Connect to the SQLite database
conn = sqlite3.connect("subscribers.db")
cur = conn.cursor()
# Create the subscribers table if it doesn't exist
cur.execute('''CREATE TABLE IF NOT EXISTS subscribers (
                user_id INTEGER PRIMARY KEY,
                selected_station TEXT,
                status_filter TEXT DEFAULT 'all'
            )''')
conn.commit()

# Add status_filter column if it doesn't exist (for existing databases)
try:
    cur.execute("ALTER TABLE subscribers ADD COLUMN status_filter TEXT DEFAULT 'all'")
    conn.commit()
except sqlite3.OperationalError:
    # Column already exists
    pass

# Load the initial list of subscribers from the database
cur.execute("SELECT user_id FROM subscribers")
initial_subscribers = cur.fetchall()
subscribed_users = set(user_id for user_id, in initial_subscribers)

# Define commands
async def start(update: Update, context: CallbackContext) -> str:
    # Create keyboard from station_table_mapping keys - one station per row
    keyboard = [
        ["Nicosia: Traffic Station"],
        ["Nicosia: Residential Station"],
        ["Limassol: Traffic Station"],
        ["Larnaca: Traffic Station"],
        ["Paphos: Traffic Station"],
        ["Ayia Marina Xyliatou: Background Station"],
        ["Zygi: Industrial Station"],
        ["Mari: Industrial Station"],
        ["Paralimni: Traffic Station"],
        ["Kalavasos Industrial Station"],
        ["Ormidia Industrial Station"]
    ]
    
    await update.message.reply_text(
        "Please select a station:",
        reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True),
    )

    return "SELECTED_STATION"

# Send a help message when the command /help is issued
async def help_command(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        "/start to start the bot and choose desired station.\n"
        "/subscribe to get hourly notifications.\n"
        "/unsubscribe to stop receiving hourly notifications.\n"
        "/filter to set notification filter by status color.\n"
        "/status to check your current settings.\n"
        "/restart to start from the beginning.\n"
        "/help for help.\n\n"
        "Data source: https://www.airquality.dli.mlsi.gov.cy\n\n"
        "Donations:\n"
        "https://streamlabs.com/sinnieonfire/\n"
        "https://revolut.me/sinnie\n"
        "https://paypal.me/sinnieonfire"
    )


async def select_station(update: Update, context: CallbackContext) -> None:
    try:
        # Retrieve the selected station from the user's message
        selected_station = update.message.text
        
        # TEMPORARY DEBUG
        if selected_station == "/test":
            await update.message.reply_text("DEBUG: /test command received in select_station")
            return
        if selected_station == "/check":
            await update.message.reply_text("DEBUG: /check command received in select_station")
            return
        
        # Skip if this is a command
        if selected_station.startswith('/'):
            return
            
        # Check if the selected station is in the station mapping
        if selected_station in station_table_mapping:
            logger.info(f"Valid station selected: {selected_station}")
            # Store the selected station in the context for later use
            context.user_data["SELECTED_STATION"] = selected_station
            # Get the corresponding table name from the mapping
            table_name = station_table_mapping.get(selected_station)
            if not table_name:
                await update.message.reply_text("Please enter the correct name or use the command keyboard.")
                return

            # Connect to the SQLite database
            conn = sqlite3.connect("stations.db")
            cur = conn.cursor()
            # Fetch the latest row from the table for the selected station
            cur.execute(f"SELECT * FROM {table_name} ORDER BY id DESC LIMIT 1")
            data = cur.fetchone()
            # Close the database connection
            conn.close()
            if data:
                # Create data dictionary for analysis
                data_dict = dict(zip(['status', 'pm_10', 'pm_2_5', 'o3', 'no', 'no2', 'nox', 'so2', 'co', 'c6h6', 'update_time'], data[1:]))
                
                # Generate descriptive message
                descriptive_msg = analyze_air_quality(data_dict)
                
                # Combine status, descriptive message, and data
                # Start with status emoji
                status_line = f"Status: {data_dict.get('status', '')}"
                
                # Build the message: status first, then description, then parameters
                message_parts = [status_line]
                
                if descriptive_msg:
                    message_parts.append(descriptive_msg)
                
                # Add pollutant data (excluding status and timestamp)
                pollutant_data = []
                for key, value in data_dict.items():
                    if key not in ['status', 'update_time']:
                        pollutant_data.append(f"{key_mapping.get(key, key)}: {value}")
                
                if pollutant_data:
                    message_parts.append('\n'.join(pollutant_data))
                
                # Add timestamp at the end
                message_parts.append(f"Timestamp: {data_dict.get('update_time', '')}")
                
                full_message = '\n\n'.join(message_parts)
                
                # Send the data as a response to the user
                await update.message.reply_text(f"{full_message}\n\nUse /subscribe for hourly updates, or /filter for alerts only.")
            else:
                await update.message.reply_text("No data found for this station.")
        else:
            # If the selected station is not in the predefined list, ignore the message
            logger.warning(f"Invalid station selected: '{selected_station}'")
            await update.message.reply_text("Station not found. Please enter the correct name or use the command keyboard.")
    except Exception as e:
        logger.error(f"An error occurred when selecting a station: {e}")

# Define the /subscribe command handler
async def subscribe(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    selected_station = context.user_data.get("SELECTED_STATION")
    if selected_station:
        try:
            cur.execute("INSERT OR IGNORE INTO subscribers (user_id, selected_station) VALUES (?, ?)", (user_id, selected_station))
            conn.commit()
            subscribed_users.add(user_id)
            await update.message.reply_text('You are now subscribed to hourly updates.')
        except Exception as e:
            logger.error(f"An error occurred while subscribing user {user_id}: {e}")
    else:
        await update.message.reply_text('Please select a station first using the /start command.')

# Define the /unsubscribe command handler
async def unsubscribe(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    if user_id in subscribed_users:
        subscribed_users.remove(user_id)
        await update.message.reply_text('You have unsubscribed from hourly updates.')
        # Update the subscribers table in the database
        cur.execute("DELETE FROM subscribers WHERE user_id = ?", (user_id,))
        conn.commit()
    else:
        await update.message.reply_text('You are not subscribed.')

# Test command
async def test_command(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Test command works!")

# Debug command to check database timestamps
async def check_data(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    
    # Check if station was provided as argument
    if context.args:
        # Join all arguments to handle station names with spaces
        station_name = ' '.join(context.args)
        selected_station = None
        
        # Find matching station (case insensitive partial match)
        for station in station_table_mapping.keys():
            if station_name.lower() in station.lower():
                selected_station = station
                break
        
        if not selected_station:
            # Show available stations
            stations_list = '\n'.join(station_table_mapping.keys())
            await update.message.reply_text(f'Station "{station_name}" not found.\n\nAvailable stations:\n{stations_list}')
            return
    else:
        # Check if user has selected a station
        cur.execute("SELECT selected_station FROM subscribers WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        
        if not row:
            await update.message.reply_text('Please select a station first using /start or provide station name: /check Limassol')
            return
        
        selected_station = row[0]
    
    table_name = station_table_mapping.get(selected_station)
    
    if not table_name:
        await update.message.reply_text('Invalid station')
        return
    
    # Get last 5 entries from the database
    station_conn = sqlite3.connect("stations.db")
    station_cur = station_conn.cursor()
    
    station_cur.execute(f"SELECT id, update_time FROM {table_name} ORDER BY id DESC LIMIT 5")
    rows = station_cur.fetchall()
    
    station_conn.close()
    
    if rows:
        message = f"Last 5 entries for {selected_station}:\n\n"
        for row in rows:
            message += f"ID: {row[0]} - Time: {row[1]}\n"
        message += f"\nCurrent time: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    else:
        message = "No data found in database"
    
    await update.message.reply_text(message)

# Filter command to set notification preferences
async def filter_command(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    
    # Check if user is subscribed
    cur.execute("SELECT selected_station FROM subscribers WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    
    if not row:
        await update.message.reply_text('Please subscribe first using /start and /subscribe commands.')
        return
    
    # Create inline keyboard for filter options
    keyboard = [
        [InlineKeyboardButton("All statuses", callback_data='filter_all')],
        [InlineKeyboardButton("🟡 Yellow and above", callback_data='filter_yellow_up')],
        [InlineKeyboardButton("🟠 Orange and above", callback_data='filter_orange_up')],
        [InlineKeyboardButton("🔴 Red only", callback_data='filter_red_only')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        'Select which air quality statuses you want to be notified about:',
        reply_markup=reply_markup
    )

# Callback handler for filter buttons
async def filter_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    filter_type = query.data.replace('filter_', '')
    
    # Update the filter in database
    try:
        cur.execute("UPDATE subscribers SET status_filter = ? WHERE user_id = ?", (filter_type, user_id))
        conn.commit()
        
        # Send confirmation message
        filter_descriptions = {
            'all': 'You will receive notifications for all statuses.',
            'yellow_up': 'You will receive notifications for 🟡 Yellow, 🟠 Orange, and 🔴 Red statuses only.',
            'orange_up': 'You will receive notifications for 🟠 Orange and 🔴 Red statuses only.',
            'red_only': 'You will receive notifications for 🔴 Red status only.'
        }
        
        await query.edit_message_text(f"Filter updated! {filter_descriptions.get(filter_type, '')}")
        
    except Exception as e:
        logger.error(f"Error updating filter for user {user_id}: {e}")
        await query.edit_message_text("An error occurred. Please try again.")

# Status command to show current settings
async def status_command(update: Update, context: CallbackContext) -> None:
    user_id = update.effective_user.id
    
    # Get user settings from database
    cur.execute("SELECT selected_station, status_filter FROM subscribers WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    
    if not row:
        await update.message.reply_text('You are not subscribed yet. Use /start to begin.')
        return
    
    selected_station, status_filter = row
    
    filter_descriptions = {
        'all': 'All statuses',
        'yellow_up': '🟡 Yellow and above',
        'orange_up': '🟠 Orange and above', 
        'red_only': '🔴 Red only'
    }
    
    status_message = f"Your current settings:\n\n"
    status_message += f"📍 Station: {selected_station}\n"
    status_message += f"🔔 Notification filter: {filter_descriptions.get(status_filter, 'All statuses')}\n\n"
    status_message += "Use /filter to change notification preferences."
    
    await update.message.reply_text(status_message)

# Define the function to send hourly messages with data from the database to subscribed users
async def send_hourly_message(context: CallbackContext) -> None:
    start_time = datetime.now()
    logger.info(f"Starting hourly notifications at {start_time}")
    
    # First, fetch all station data at once
    station_data = {}
    
    try:
        station_conn = sqlite3.connect("stations.db")
        station_cur = station_conn.cursor()
        
        # Fetch latest data for all stations
        for station_name, table_name in station_table_mapping.items():
            station_cur.execute(f"SELECT * FROM {table_name} ORDER BY id DESC LIMIT 1")
            data = station_cur.fetchone()
            if data:
                # Create data dictionary for analysis
                data_dict = dict(zip(['status', 'pm_10', 'pm_2_5', 'o3', 'no', 'no2', 'nox', 'so2', 'co', 'c6h6', 'update_time'], data[1:]))
                
                # Generate descriptive message
                descriptive_msg = analyze_air_quality(data_dict)
                
                # Combine status, descriptive message, and data
                # Start with status emoji
                status_line = f"Status: {data_dict.get('status', '')}"
                
                # Build the message: status first, then description, then parameters
                message_parts = [status_line]
                
                if descriptive_msg:
                    message_parts.append(descriptive_msg)
                
                # Add pollutant data (excluding status and timestamp)
                pollutant_data = []
                for key, value in data_dict.items():
                    if key not in ['status', 'update_time']:
                        pollutant_data.append(f"{key_mapping.get(key, key)}: {value}")
                
                if pollutant_data:
                    message_parts.append('\n'.join(pollutant_data))
                
                # Add timestamp at the end
                message_parts.append(f"Timestamp: {data_dict.get('update_time', '')}")
                
                full_message = '\n\n'.join(message_parts)
                
                station_data[station_name] = {
                    'message': full_message,
                    'status': data_dict.get('status', '')
                }
        
        station_conn.close()
        
    except Exception as e:
        logger.error(f"Error fetching station data: {e}")
        return
    
    # Now send messages to users
    users_sent = 0
    
    for user_id in subscribed_users:
        try:
            # Fetch the selected station for the current user from the database
            cur.execute("SELECT selected_station FROM subscribers WHERE user_id = ?", (user_id,))
            row = cur.fetchone()
            if not row:
                logger.error(f"No selected station found for user {user_id}")
                continue
            
            selected_station = row[0]
            
            # Get pre-formatted data
            if selected_station in station_data:
                # Check status filter
                cur.execute("SELECT status_filter FROM subscribers WHERE user_id = ?", (user_id,))
                filter_result = cur.fetchone()
                status_filter = filter_result[0] if filter_result else 'all'
                
                # Get status from the station data
                status_emoji = station_data[selected_station]['status']
                
                # Check if we should send based on filter
                should_send = False
                if status_filter == 'all':
                    should_send = True
                elif status_filter == 'yellow_up' and status_emoji in ['🟡', '🟠', '🔴']:
                    should_send = True
                elif status_filter == 'orange_up' and status_emoji in ['🟠', '🔴']:
                    should_send = True
                elif status_filter == 'red_only' and status_emoji == '🔴':
                    should_send = True
                
                if should_send:
                    await context.bot.send_message(user_id, station_data[selected_station]['message'])
                    users_sent += 1
                else:
                    logger.info(f"Skipping notification for user {user_id} - status {status_emoji} doesn't match filter {status_filter}")
            else:
                logger.error(f"No data available for station: {selected_station}")
                
        except Exception as e:
            logger.error(f"Error sending hourly message to user {user_id}: {e}")
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    logger.info(f"Hourly notifications complete: {users_sent} users in {duration:.2f} seconds")

# Function to schedule the hourly job at specific minutes after the hour
def schedule_hourly_job(context: CallbackContext) -> None:
    now = datetime.now()
    # Set notifications to run at :25 past each hour (5 minutes after scraper runs at :20)
    target_minute = 25
    
    # Calculate the next run time at :25 past the hour
    if now.minute >= target_minute:
        next_run = now.replace(hour=now.hour+1, minute=target_minute, second=0, microsecond=0)
    else:
        next_run = now.replace(minute=target_minute, second=0, microsecond=0)
    
    # Calculate delay until first run
    delay = (next_run - now).total_seconds()
    
    # Schedule the repeating job
    context.job_queue.run_repeating(send_hourly_message, interval=3600, first=delay)
    logger.info(f"Scheduled hourly updates to start at {next_run.strftime('%H:%M')} and repeat hourly")

def main() -> None:
    # Get token from environment variable
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        logger.error("TELEGRAM_TOKEN environment variable not set")
        return

    # Pass token
    application = Application.builder().token(token).build()
    
    # Handle commands
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("restart", start))
    application.add_handler(CommandHandler("subscribe", subscribe))
    application.add_handler(CommandHandler("unsubscribe", unsubscribe))
    application.add_handler(CommandHandler("test", test_command))
    application.add_handler(CommandHandler("check", check_data))
    application.add_handler(CommandHandler("filter", filter_command))
    application.add_handler(CommandHandler("status", status_command))

    # Handle callback queries for inline keyboards
    application.add_handler(CallbackQueryHandler(filter_callback, pattern='^filter_'))

    # Handle messages from ReplyKeyboardMarkup
    application.add_handler(MessageHandler(filters.TEXT, select_station))

    # Schedule the hourly job with specific timing instead of immediate start
    application.job_queue.run_once(schedule_hourly_job, 0)

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)

    # Close the database connection when the bot stops
    conn.close()

if __name__ == "__main__":
    main()