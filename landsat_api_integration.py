import json
import schedule
import time
from landsatxplore.api import API
from datetime import datetime, timedelta
from LandsatCalc import get_landsat_path_row
from shapely.wkt import loads
import matplotlib.pyplot as plt

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
        # Load the polygon using Shapely
        print()
        #wkt_string = "POLYGON ((-6.43793 49.64714, -3.88869 49.19698, -3.11761 50.89143, -5.75664 51.34855, -6.43793 49.64714))"
        wkt_string = str(scene['spatial_coverage'])
        polygon = loads(wkt_string)

        # Get properties
        centroid = polygon.centroid
        area = polygon.area
        perimeter = polygon.length

        # Print properties
        print(f"Centroid: {centroid}")
        print(f"Area: {area}")
        print(f"Perimeter: {perimeter}")

        # Plot the polygon using Matplotlib
        x, y = polygon.exterior.xy
        plt.plot(x, y)
        plt.scatter(centroid.x, centroid.y, color='red')  # Plot centroid
        plt.title("Polygon Visualization with Centroid")
        plt.show()

    api.logout()
    return scenes # Return the list of dictionaries containing scene data

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
    
    # Search for Landsat scenes
    scenes_data = search_landsat_scenes(latitude, longitude, start_date, end_date)
    
    if scenes_data:
        # Save the scene data to a JSON-formatted text file
        with open("landsat_scenes_data.txt", "w") as outfile:
            json.dump(scenes_data, outfile, indent=4, default=custom_json_serial)
        print("Landsat scene data saved to 'landsat_scenes_data.txt'.")

        # Example print statement to confirm the file contents
        print("Sample data:", scenes_data[0])
