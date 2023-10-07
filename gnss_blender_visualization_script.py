import bpy
import bmesh
import re
import math

file_path = ""  # Replace with your file path
# Initialize empty lists to store the extracted data
timestamps = []
latitudes = []
longitudes = []
headings = []

# Regular expressions for parsing the NMEA sentences
gga_pattern = re.compile(r"\$GNGGA,(\d+.\d+),(\d+.\d+),(N|S),(\d+.\d+),(E|W),.*")
hdt_pattern = re.compile(r"\$HEHDT,(\d+.\d+),T.*")

# see conversion formulas at
# http://en.wikipedia.org/wiki/Transverse_Mercator_projection
# and
# http://mathworld.wolfram.com/MercatorProjection.html
class TransverseMercator:
    radius = 6378137.

    def __init__(self, **kwargs):
        # setting default values
        self.lat = 0. # in degrees
        self.lon = 0. # in degrees
        self.k = 1. # scale factor
        
        for attr in kwargs:
            setattr(self, attr, kwargs[attr])
        self.latInRadians = math.radians(self.lat)

    def fromGeographic(self, lat, lon):
        lat = math.radians(lat)
        lon = math.radians(lon-self.lon)
        B = math.sin(lon) * math.cos(lat)
        x = 0.5 * self.k * self.radius * math.log((1.+B)/(1.-B))
        y = self.k * self.radius * ( math.atan(math.tan(lat)/math.cos(lon)) - self.latInRadians )
        return (x, y, 0.)

    def toGeographic(self, x, y):
        x = x/(self.k * self.radius)
        y = y/(self.k * self.radius)
        D = y + self.latInRadians
        lon = math.atan(math.sinh(x)/math.cos(D))
        lat = math.asin(math.sin(D)/math.cosh(x))

        lon = self.lon + math.degrees(lon)
        lat = math.degrees(lat)
        return (lat, lon)

scene = bpy.context.scene
projection = TransverseMercator(lat=scene["lat"], lon=scene["lon"])

# Read the file and extract the data
with open(file_path, 'r') as f:
    temp_time = None
    temp_lat = None
    temp_long = None
    temp_heading = None
    
    for line in f:
        # Match GGA sentence for time, latitude, and longitude
        gga_match = gga_pattern.match(line)
        if gga_match:
            temp_time = gga_match.group(1)
            temp_lat = float(gga_match.group(2))
            temp_long = float(gga_match.group(4))

        # Match HDT sentence for heading
        hdt_match = hdt_pattern.match(line)
        if hdt_match:
            temp_heading = float(hdt_match.group(1))

        # Only append data when both position and heading are available
        if temp_time and temp_lat and temp_long and temp_heading:
            timestamps.append(temp_time)
            latitudes.append(temp_lat)
            longitudes.append(temp_long)
            headings.append(temp_heading)

            # Reset temp variables
            temp_time = None
            temp_lat = None
            temp_long = None
            temp_heading = None


# Assume 'car' object exists in the scene
car_object = bpy.data.objects.get("car")
if not car_object:
    print("Car object not found in the scene.")
    exit()

# Clear animation data if exists
if car_object.animation_data:
    car_object.animation_data_clear()

# Set animation frame rate
bpy.context.scene.render.fps = 24

# Loop through each data point to set position and keyframe
for i in range(len(timestamps)):
    frame_number = i * 2  # You can adjust this to control speed
    
    (x,y,z) = projection.fromGeographic(latitudes[i]/100, longitudes[i]/100)
    
    # Set car position
    car_object.location = (x, y, z)
    
    # Set car rotation based on heading
    #car_object.rotation_euler.z = headings[i]  # Assuming heading is in radians
    
    # Insert keyframes
    car_object.keyframe_insert(data_path="location", frame=frame_number)
    car_object.keyframe_insert(data_path="rotation_euler", frame=frame_number)
