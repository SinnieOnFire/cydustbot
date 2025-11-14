import requests
from bs4 import BeautifulSoup
import sqlite3
import os
import schedule
import time
from datetime import datetime

# Function to map group status to emojis
def status_to_emoji(status):
    if status == "station-status-green":
        return "🟢"
    elif status == "station-status-yellow":
        return "🟡"
    elif status == "station-status-orange":
        return "🟠"
    elif status == "station-status-red":
        return "🔴"
    elif status == "station-status-white":
        return "⚪"
    else:
        return "❓"

# Mapping of station names to table names
station_table_mapping = {
    "Nicosia - Traffic Station": "station01",
    "Nicosia - Residential Station": "station02",
    "Limassol - Traffic Station": "station03",
    "Larnaca - Traffic Station": "station04",
    "Paphos - Traffic Station": "station05",
    "Ayia Marina Xyliatou - Background Station": "station06",
    "Zygi - Industrial Station": "station07",
    "Mari - Industrial Station": "station08",
    "Paralimni - Traffic Station": "station09",
    "Kalavasos Industrial Station": "station10",
    "Ormidia Industrial Station": "station11"
}

def scrape_and_save_data():
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[{current_time}] Starting data scrape...")
    
    # URL of the webpage to scrape
    url = "https://www.airquality.dli.mlsi.gov.cy/"

    # Send a GET request to the URL
    response = requests.get(url)

    # Parse the HTML content
    soup = BeautifulSoup(response.content, "html.parser")

    # Find the main container div
    main_container = soup.find("div", id="views-bootstrap-frontpage-stations-overview-block-1")

    # Check if the main container exists
    if main_container:
        # Create or connect to the SQLite database
        db_path = "stations.db"
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        stations_processed = 0
        new_data_inserted = 0

        # Iterate over each station div
        for index, div in enumerate(main_container.find_all("div", class_=lambda x: x and x.startswith("col")), 1):

            # Check if the station is under maintenance
            if div.find("span", class_="under-maintenance-label"):
                print(f"Station {index}: Under maintenance, skipping.")
                continue

            # Define table name
            station_name = div.find("h4", class_="stations-overview-title").text.strip()
            table_name = station_table_mapping.get(station_name)
            if not table_name:
                print(f"No table mapping found for station: {station_name}")
                continue

            # Create a table for the current station if it doesn't exist
            cur.execute(f'''CREATE TABLE IF NOT EXISTS {table_name} (
                            id INTEGER PRIMARY KEY,
                            status TEXT,
                            pm_10 TEXT,
                            pm_2_5 TEXT,
                            o3 TEXT,
                            no TEXT,
                            no2 TEXT,
                            nox TEXT,
                            so2 TEXT,
                            co TEXT,
                            c6h6 TEXT,
                            update_time TEXT
                        )''')

            # Find group status
            status_element = div.find("span", class_="group-status-helper-wrapper")
            status_class = status_element.find("span")["class"] if status_element else ""
            status_emoji = status_to_emoji(status_class[0]) if status_class else ""

            # Find pollutant data
            pollutant_data = {}
            for label_span, value_span in zip(
                div.find_all("span", class_="pollutant-label"),
                div.find_all("span", class_="pollutant-value")
            ):
                pollutant_label = label_span.text.strip().replace(":", "")
                pollutant_value = value_span.text.strip()
                pollutant_data[pollutant_label] = pollutant_value

            # Find station update time
            update_time_raw = div.find("div", class_="views-field-field-station-update-time").text.strip()
            
            # Extract just the timestamp part (e.g., "24/05/2025 17:00")
            # The format is usually "Updated on: DD/MM/YYYY HH:MM"
            if "Updated on:" in update_time_raw:
                update_time = update_time_raw.replace("Updated on:", "").strip()
            else:
                update_time = update_time_raw
            
            # Log what timestamp we found on the website
            if index == 1:  # Only log once, not for every station
                print(f"Website shows timestamp: '{update_time}'")
            
            # Check if this timestamp already exists in the database
            cur.execute(f"SELECT COUNT(*) FROM {table_name} WHERE update_time = ?", (update_time,))
            count = cur.fetchone()[0]
            
            if count > 0:
                print(f"{station_name}: Data for '{update_time}' already exists, skipping.")
                # Also check what the latest timestamp in DB is
                cur.execute(f"SELECT update_time FROM {table_name} ORDER BY id DESC LIMIT 1")
                latest = cur.fetchone()
                if latest:
                    print(f"  Latest in DB: '{latest[0]}'")
            else:
                # Insert data into the table for the current station
                cur.execute(f'''INSERT INTO {table_name} (status, pm_10, pm_2_5, o3, no, no2, nox, so2, co, c6h6, update_time)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                            (status_emoji, pollutant_data.get("PM₁₀"), pollutant_data.get("PM₂.₅"), pollutant_data.get("O₃"),
                             pollutant_data.get("NO"), pollutant_data.get("NO₂"), pollutant_data.get("NOx"), pollutant_data.get("SO₂"),
                             pollutant_data.get("CO"), pollutant_data.get("C₆H₆"), update_time))
                print(f"{station_name}: New data inserted for '{update_time}'")
                new_data_inserted += 1
            
            stations_processed += 1

        # Commit the changes and close the connection
        conn.commit()
        conn.close()

        print(f"\n[{current_time}] Scraping complete:")
        print(f"  - Stations processed: {stations_processed}")
        print(f"  - New data entries: {new_data_inserted}")
    else:
        print(f"[{current_time}] ERROR: Data not found on the webpage.")

# Schedule the scraping function to run once per hour
# Run at :20 since website has updated by :19 based on user observation
schedule.every().hour.at(":20").do(scrape_and_save_data)

# Run the scraping function initially
scrape_and_save_data()

# Keep the script running to allow scheduling
while True:
    schedule.run_pending()
    time.sleep(1)