import csv
import math
from os import listdir
from os.path import isfile, join


# Procedure that takes as input a tab-delimited txt file, and stores the data as a list, 
# where each element of the list is a list itself that corresponds to a row in the file,
# and each element of that list corresponds to an entry in that row. 

def parseCSV(filePath, data):
    with open(filePath, 'rU') as csvfile:
        for row in csv.reader(csvfile, delimiter = '\t'):
            tList = []
            for element in row:
                try:
                    tList.append(float(element))    
                except:
                    tList.append(element)    
            data.append(tList)


# Function that uses the haversine formula to calculate the 'great-circle' distance in meters
# between two points whose latitutde and longitude are known

def calDistance(point1, point2):

    earthRadius = 6371000 
    dLat = math.radians(point1[0]-point2[0])
    dLon = math.radians(point1[1]-point2[1])    
    lat1 = math.radians(point1[0])
    lat2 = math.radians(point2[0])
    
    a = (math.sin(dLat/2) ** 2) + ((math.sin(dLon/2) ** 2) * math.cos(lat1) * math.cos(lat2))
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    d = earthRadius * c 
    
    return d


# Function that takes as input the GPS location of a point and a list of points, where each element of the 
# list is a tuple containing the latitutde and longitude for that point. The function outputs the maximum 
# distance, in meters, from that point to any point in the list of points

def calDistanceToPoint(point, points):
    maxDistance = 0
    for i in range(0, len(points)):
        dist = calDistance(point, points[i])
        if dist > maxDistance:
            maxDistance = dist
    return maxDistance
    

# Procedure that takes as input the list containing GPS data, called gpsTraces, and two empty lists, 
# called trips and activities. 
#
# Each element of trips is a tuple and corresponds to a particular trip. The elements of the tuple are the 
# indices of the corresponding GPS data points in gpsTraces for where the trip began and ended, respectively.
# Similarly, each element of activities is a tuple and corresponds to a particular activity. The elements 
# of the tuple are the indices of the corresponding GPS data point in gpsTraces for where the activity began 
# and ended, respectively.
# 
# An activity is defined as a set of GPS points over a minimum duration of minDuration milliseconds that fall within 
# a circle of radius maxRadius meters. The minimum interval between successive activites must be at least 
# minInterval milliseconds, for them to be recorded as separate activities.

def inferTripActivity(gpsTraces, trips, activities, minDuration, maxRadius, minInterval):
    
    i = 0
    while i < len(gpsTraces) - 1:
        
        # Create a collection of successive points that lie within a circle of radius maxRadius meters
        j = i + 1
        points = [gpsTraces[i][2:4]]  
        while j < len(gpsTraces) and calDistanceToPoint(gpsTraces[j][2:4], points) < maxRadius:
            points.append(gpsTraces[j][2:4])
            j += 1
        
        # Check if the duration over which these points were collected exceeds minDuration milliseconds
        if gpsTraces[j-1][1] - gpsTraces[i][1] > minDuration:
            
            # Check if the activity is separated in time from previous activity by at least minInterval milliseconds
            if len(activities) > 0 and gpsTraces[i][1] - gpsTraces[activities[-1][-1]][1] < minInterval:
                activities[-1][-1] = j-1
            else:
                activities.append([i, j-1])
            i = j - 1
        else:
            i += 1

    numActivities = len(activities)
    if numActivities != 0:
        
        # Check if the GPS log begins with a trip
        if activities[0][0] != 0:
            trips.append([0, activities[0][0]])
        
        # Interpolate trips from activities
        if numActivities > 1:
            for i in range(0, numActivities - 1):            
                trips.append([activities[i][-1], activities[i+1][0]])
        
        # Check if the GPS log ends with a trip
        if activities[-1][-1] < len(gpsTraces)-1:
            trips.append([activities[-1][-1], len(gpsTraces)-1])
    else:
        trips.append([0, len(gpsTraces)-1])
        

# Functions that calculate the four features of a GPS point: distance to next point (in meters), 
# time interval (seconds), speed (mph) and acceleration (mph2)

def lengthPoint(gpsTraces, j):
   return calDistance(gpsTraces[j][2:4], gpsTraces[j+1][2:4])

def timePoint(gpsTraces, j):
   return (gpsTraces[j+1][1] - gpsTraces[j][1]) / 1000.0

def speedPoint(gpsTraces, j):
  return 2.23694 * (float(lengthPoint(gpsTraces,j))/timePoint(gpsTraces,j))

def accelerationPoint(gpsTraces, j):
  return (2.23694/60) * (float(lengthPoint(gpsTraces,j))/(timePoint(gpsTraces,j) ** 2))
  
  


def inferMode(gpsTraces, maxWalkSpeed, maxWalkAcceleration, minSegmentDuration):

    # Step 1: Separate walk points from non-walk points
    walkDummy = []
    for i in range(0, len(gpsTraces) - 1):
        if speedPoint(gpsTraces, i) < maxWalkSpeed and accelerationPoint(gpsTraces, i) < maxWalkAcceleration:
	    walkDummy.append(1); 
	else:
	    walkDummy.append(0)
    print walkDummy
    
    # Step 2: Combine points into walk and non-walk segments
    segments, numSegments, currentPoint = [], 0, 0
    while currentPoint < len(gpsTraces) - 1:
        segments.append([currentPoint])
        while currentPoint < len(gpsTraces) - 2 and walkDummy[currentPoint] == walkDummy[currentPoint + 1]:
            currentPoint += 1
        if currentPoint < len(gpsTraces) - 1:
            currentPoint += 1
        segments[numSegments].append(currentPoint)
        distance = round(calDistance(gpsTraces[segments[-1][0]][2:4], gpsTraces[segments[-1][1]][2:4]), 0)
        time = round((gpsTraces[segments[-1][1]][1] - gpsTraces[segments[-1][0]][1]) / 1000, 0)
        speed = round((2.23694 * distance)/time, 0)
        acceleration = round((2.23694 / 60) * (distance/(time ** 2)), 2)
        segments[numSegments].append(distance)
        segments[numSegments].append(time)
        segments[numSegments].append(speed)
        segments[numSegments].append(acceleration)
        numSegments += 1
    print segments
    print '\n'
    '''
    # Step 3: Check if segment length exceeds minSegmentDuration seconds
    tempSegments, numSegments = [], 0
    for i in range(0, len(segments) - 1):
        tempSegments.append(segments[i])
        if numSegments > 0 and gpsTraces[segment[1]][1] - gpsTraces[segment[0]][1]) < minSegmentDuration:
            tempSegments[numSegments][1] = segment[1]
    '''


# The input file is a csv containing the GPS data and ground truth. The file name should follow the generic
# format: '<test phone number>_<tester alias>_<date data recorded>.csv', where test phone number is a 
# 9-digit number with no brackets and hyphens, and date data recorded is in MMDDYYYY format.
# 
# The file should contain fourteen columns. The first nine columns denote the tester ID, timestamp (in epoch time, 
# recorded in milliseconds), latitude, longitude, GPS accuracy (in feet), battery status (in percentage), 
# sampling rate (in seconds), accelermoeter reading, activity as inferred by the Google API, and PST time, respectively. 
# The values for each of these fields will be generated by the tracking app installed on the test phone in 
# the appropriate units, and you shouldn't have to change anything.
#
# The next four columns reflect the ground truth that will be used to train our inference algorithms.
# The eleventh column can take on two string values: (1) Trip, if the individual at the time was making a trip; 
# or (2) Activity, if the individual at the time was engaging in an activity. Columns twelve to fourteen 
# are strings containing information regarding the trip or activity.
#
# Finally, the rows in the file should be ordered in terms of increasing time. 

# Base directory where you clone the repository, change as appropriate
filePath = '/Users/biogeme/Desktop/Vij/Academics/Post-Doc/' 

# Shouldn't have to change anything below this for the code to run
filePath += 'Travel-Diary/Data/Google Play API/5107250619_Vij_01032014.txt'
gpsTraces = []
parseCSV(filePath, gpsTraces)

trips, activities = [], []
minDuration, maxRadius, minInterval = 180000, 50, 120000
inferTripActivity(gpsTraces, trips, activities, minDuration, maxRadius, minInterval)
print trips, activities

'''
maxWalkSpeed, maxWalkAcceleration, minSegmentDuration = 4, 0.2237, 120
for trip in trips:
    print trip
    inferMode(gpsTraces[trip[0]:trip[1]], maxWalkSpeed, maxWalkAcceleration, minSegmentDuration)
'''