import io
import urllib.request
import zipfile
import fiona
from shapely.geometry import shape, Point
from datetime import datetime, timedelta
import pytz
from timezonefinder import TimezoneFinder

# Function to download and extract WRS-2 shapefiles
def download_wrs_shapefiles(url, extract_to):
    r = urllib.request.urlopen(url)
    zip_file = zipfile.ZipFile(io.BytesIO(r.read()))
    zip_file.extractall(extract_to)
    zip_file.close()

# Function to check if a point is within a specific path/row feature
def check_point(feature, point, mode):
    # Use shapely to create a polygon shape from feature geometry
    polygon = shape(feature['geometry'])
    if point.within(polygon) and feature['properties']['MODE'] == mode:
        return True
    return False

# Main function to get path and row for given coordinates
def get_landsat_path_row(lat, lon, mode='D'):
    # Download WRS-2 shapefiles if not already done
    shapefile = 'landsat-path-row/WRS2_descending.shp'
    url = "https://d9-wret.s3.us-west-2.amazonaws.com/assets/palladium/production/s3fs-public/atoms/files/WRS2_descending_0.zip"

    # Download and extract shapefiles
    download_wrs_shapefiles(url, "landsat-path-row")

    # Open the shapefile using Fiona
    with fiona.open(shapefile) as shapefile_layer:
        # Define point with given latitude and longitude
        point = Point(lon, lat)

        # Loop through features to find a matching one
        for feature in shapefile_layer:
            if check_point(feature, point, mode):
                # Get path and row values from the matched feature
                path = feature['properties']['PATH']
                row = feature['properties']['ROW']
                return path, row

    # If no match is found, return None
    return None, None

# Cycle day paths dictionary
cycle_day_paths = {
    1: [13, 29, 45, 61, 77, 93, 102, 118, 134, 150, 166, 182, 198, 214, 230],
    2: [4, 20, 36, 52, 68, 84, 93, 109, 125, 141, 157, 173, 189, 205, 221],
    3: [11, 27, 43, 59, 75, 91, 100, 116, 132, 148, 164, 180, 196, 212, 228],
    4: [2, 18, 34, 50, 66, 82, 91, 107, 123, 139, 155, 171, 187, 203, 219],
    5: [9, 25, 41, 57, 73, 89, 98, 114, 130, 146, 162, 178, 194, 210, 226],
    6: [16, 32, 48, 64, 80, 96, 105, 121, 137, 153, 169, 185, 201, 217, 233],
    7: [7, 23, 39, 55, 71, 87, 96, 112, 128, 144, 160, 176, 192, 208, 224],
    8: [14, 30, 46, 62, 78, 94, 103, 119, 135, 151, 167, 183, 199, 215, 231],
    9: [5, 21, 37, 53, 69, 85, 94, 110, 126, 142, 158, 174, 190, 206, 222],
    10: [12, 28, 44, 60, 76, 92, 101, 117, 133, 149, 165, 181, 197, 213, 229],
    11: [3, 19, 35, 51, 67, 83, 92, 108, 124, 140, 156, 172, 188, 204, 220],
    12: [10, 26, 42, 58, 74, 90, 99, 115, 131, 147, 163, 179, 195, 211, 227],
    13: [1, 17, 33, 49, 65, 81, 90, 106, 122, 138, 154, 170, 186, 202, 218],
    14: [8, 24, 40, 56, 72, 88, 97, 113, 129, 145, 161, 177, 193, 209, 225],
    15: [15, 31, 47, 63, 79, 95, 104, 120, 136, 152, 168, 184, 200, 216, 232],
    16: [6, 22, 38, 54, 70, 86, 95, 111, 127, 143, 159, 175, 191, 207, 223],
}

# Function to get the cycle day based on the path
def get_cycle_day(path):
    for day, paths in cycle_day_paths.items():
        if path in paths:
            return day
    return "Path not found in any cycle day"

# Function to calculate the next occurrence of the given cycle day
def get_next_cycle_day(current_date, current_cycle_day):
    T = (current_date - datetime(2024, 10, 6)).days
    next_day_offset = ((current_cycle_day - 1) + 16 - (T % 16)) % 16
    if next_day_offset == 0:
        next_day_offset = 16  # Cycle days are 1 to 16, not 0 to 15

    # Calculate the date of the next occurrence of the current cycle day
    next_date = current_date + timedelta(days=next_day_offset)
    return next_date

# Function to calculate time based on path and row
def calculate_time(path, row, current_date, lat, lon):
    # Each path takes 98.8 minutes (approximately 1 hour 38.8 minutes), each row takes ~0.39 minutes
    time_per_path = 98.8  # in minutes
    time_per_row = 0.39  # in minutes

    # Get the cycle day for the path
    cycle_day = get_cycle_day(path)

    # Get the time spent on previous paths in the day
    path_index_in_day = cycle_day_paths[cycle_day].index(path)
    total_time_on_paths = path_index_in_day * time_per_path

    # Add time spent on rows in the current path
    time_on_rows = row * time_per_row

    # Total time into the day
    total_minutes = total_time_on_paths + time_on_rows

    # Convert total minutes to time
    start_of_day = datetime.combine(current_date, datetime.min.time())
    time_at_location = start_of_day + timedelta(minutes=total_minutes)

    # Get the timezone based on the latitude and longitude
    tf = TimezoneFinder()
    timezone_str = tf.timezone_at(lat=lat, lng=lon)
    local_timezone = pytz.timezone(timezone_str)

    # Convert UTC time to local time
    time_at_location = time_at_location.astimezone(local_timezone)
    
    return time_at_location
# Example usage
if __name__ == "__main__":
    latitude = 50.85
    longitude = -4.35
    mode = 'D'  # 'D' for descending, 'A' for ascending

    path, row = get_landsat_path_row(latitude, longitude, mode)
    if path is not None and row is not None:
        print(f"Path: {path}, Row: {row}")
        
        # Get the cycle day for the retrieved path
        cycle_day = get_cycle_day(path)
        print(f"The path {path} is in Day {cycle_day}.")
        
        # Get the current date
        current_date = datetime.now()
        
        # Calculate the next cycle day occurrence
        next_cycle_date = get_next_cycle_day(current_date, cycle_day)
        print(f"The next occurrence of Cycle Day {cycle_day} is on: {next_cycle_date.date()}.")
        
        # Calculate the time for this path and row
        time_at_location = calculate_time(path, row, next_cycle_date, latitude, longitude)
        print(f"The machine will be at Path {path}, Row {row} at: {time_at_location.strftime('%Y-%m-%d %H:%M:%S')} {time_at_location.tzinfo}.")
    else:
        print("No matching path/row found for the given coordinates.")
