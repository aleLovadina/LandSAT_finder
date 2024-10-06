from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import io
import urllib.request
import zipfile
import fiona
from shapely.geometry import shape, Point
from datetime import datetime, timedelta
import pytz
from timezonefinder import TimezoneFinder

app = Flask(__name__)
CORS(app)  # Enable CORS for cross-origin resource sharing

# Functions as provided earlier...
def download_wrs_shapefiles(url, extract_to):
    r = urllib.request.urlopen(url)
    zip_file = zipfile.ZipFile(io.BytesIO(r.read()))
    zip_file.extractall(extract_to)
    zip_file.close()

def check_point(feature, point, mode):
    polygon = shape(feature['geometry'])
    if point.within(polygon) and feature['properties']['MODE'] == mode:
        return True
    return False

def get_landsat_path_row(lat, lon, mode='D'):
    shapefile = 'landsat-path-row/WRS2_descending.shp'
    url = "https://d9-wret.s3.us-west-2.amazonaws.com/assets/palladium/production/s3fs-public/atoms/files/WRS2_descending_0.zip"
    download_wrs_shapefiles(url, "landsat-path-row")

    with fiona.open(shapefile) as shapefile_layer:
        point = Point(lon, lat)
        for feature in shapefile_layer:
            if check_point(feature, point, mode):
                path = feature['properties']['PATH']
                row = feature['properties']['ROW']
                return path, row
    return None, None

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

def get_cycle_day(path):
    # Check if cycle_day_paths is a dictionary
    if not isinstance(cycle_day_paths, dict):
        raise ValueError("cycle_day_paths should be a dictionary mapping days to paths")

    # Find the corresponding cycle day for the given path
    for day, paths in cycle_day_paths.items():
        if path in paths:
            return day

    # If no match is found, raise an error
    raise ValueError(f"Path {path} not found in any cycle day mapping")


def get_next_cycle_day(current_date, current_cycle_day):
    T = (current_date - datetime(2024, 10, 6)).days
    next_day_offset = ((current_cycle_day - 1) + 16 - (T % 16)) % 16
    if next_day_offset == 0:
        next_day_offset = 16
    next_date = current_date + timedelta(days=next_day_offset)
    return next_date

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

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/landsat')
def landsat():
    return render_template('landsat.html')

@app.route('/live')
def live():
    return render_template('live.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/get_time', methods=['POST'])
def get_time():
    data = request.json
    lat = data.get('latitude')
    lon = data.get('longitude')
    mode = 'D'  # Default to descending for now

    print(f"Received coordinates: Latitude = {lat}, Longitude = {lon}")

    # Calculate the next Landsat time for the given coordinates
    path, row = get_landsat_path_row(lat, lon, mode)
    print(f"Computed Path: {path}, Row: {row}")

    if path is not None and row is not None:
        cycle_day = get_cycle_day(path)

        current_date = datetime.now()
        next_cycle_date = get_next_cycle_day(current_date, cycle_day)
        time_at_location = calculate_time(path, row, next_cycle_date, lat, lon)

        response = {
            'path': path,
            'row': row,
            'cycle_day': cycle_day,
            'next_date': next_cycle_date.strftime('%Y-%m-%d'),
            'time_at_location': time_at_location.strftime('%Y-%m-%d %H:%M:%S %Z')
        }
    else:
        response = {
            'error': f'No matching path/row found for the given coordinates: Latitude = {lat}, Longitude = {lon}.'
        }

    return jsonify(response)

if __name__ == '__main__':
    app.run(debug=True)
