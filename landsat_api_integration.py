import json
import schedule
import time
from landsatxplore.api import API
from datetime import datetime, timedelta
from LandsatCalc import get_landsat_path_row
import matplotlib.pyplot as plt
import pandas as pd

# Function to convert various object types to string
def custom_json_serial(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()  # Convert datetime to ISO 8601 string
    elif hasattr(obj, 'wkt'):  # Check if the object has a 'wkt' attribute (common in geometric objects)
        return obj.wkt  # Return Well-Known Text representation of the Polygon
    raise TypeError(f"Type {obj.__class__.__name__} not serializable")

# Function to search for Landsat scenes and fetch metadata
def search_landsat_scenes(lat, lon, start_date, end_date):
    api = API('samahosam', 'Sasosaso@2022')

    # Get the path and row for the given coordinates
    path, row = get_landsat_path_row(lat, lon)
    
    if path is None or row is None:
        print("No matching path/row found for the given coordinates.")
        return []
    
    print(f"Path: {path}, Row: {row}")
    
    # Search for Landsat scenes using the path and row
    scenes = api.search(
        dataset='landsat_ot_c2_l2',
        latitude=lat,
        longitude=lon,
        start_date=start_date,
        end_date=end_date,
        max_cloud_cover=10
    )
    
    print(f"{len(scenes)} scenes found.")
   
    scene_data = []
    for scene in scenes:
        #print(json.dumps(scene, default=custom_json_serial, indent=2))
        #Use the custom serialization function to serialize scenes
        print(scene['entity_id'])
        scene_data.append({
            "scene_id": scene['entity_id'],
            "acquisition_date": scene['publish_date'],
            "cloud_cover": scene['cloud_cover'],
        })
    
    api.logout()
    return scene_data  # Return the list of dictionaries containing scene data

# Function to send a notification
def send_notification(date):
    print(f"Reminder: Landsat satellite will overpass on {date}.")

# Function to schedule notifications
def schedule_notification(lat, lon, target_date):
    # Schedule the notification for a day before the target date
    notification_date = target_date - timedelta(days=1)
    schedule.every().day.at("09:00").do(send_notification, notification_date)

    while True:
        schedule.run_pending()
        time.sleep(60)  # Wait a minute before checking again

if __name__ == "__main__":
    latitude = 50.85
    longitude = -4.35
    start_date = '2024-01-01'
    end_date = '2024-10-01'
    
    scenes_data = search_landsat_scenes(latitude, longitude, start_date, end_date)

    if scenes_data:
        # Assuming the next overpass date is known or calculated
        # Replace this with actual date calculation logic
        next_overpass_date = datetime.now() + timedelta(days=15)  # Example date
        schedule_notification(latitude, longitude, next_overpass_date)

        # Convert to DataFrame
        df = pd.DataFrame(scenes_data)

        # Convert the acquisition_date to a datetime object
        df['acquisition_date'] = pd.to_datetime(df['acquisition_date'])
        
        # Display the DataFrame as a table
        print("Landsat Scene Data:")
        print(df)

        # Plot cloud cover over time
        plt.figure(figsize=(12, 6))
        plt.plot(df['acquisition_date'], df['cloud_cover'], marker='o', linestyle='-')
        plt.title('Cloud Coverage Over Time for Landsat Scenes')
        plt.xlabel('Acquisition Date')
        plt.ylabel('Cloud Coverage (%)')
        plt.xticks(rotation=45)
        plt.grid()
        plt.tight_layout()
        plt.show()
