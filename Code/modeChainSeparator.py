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


# Function that takes as input a point and a list of points, where a point is itself a list containing 
# the elements in the row in the input file corresponding to that point. The function outputs the maximum 
# distance, in meters, from the 95% CI around that point to the 95% CI around any point in the list of points

def calDistanceToPoint(point, points):
    maxDistance = 0
    for i in range(0, len(points)):
        dist = calDistance(point[2:4], points[i][2:4]) - point[4] - points[i][4]
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
#
# GPS traces whose accuracy is above gpsAccuracyThreshold meters are ignored.

def inferTripActivity(gpsTraces, trips, activities, minDuration, maxRadius, minInterval, gpsAccuracyThreshold):
    
    # Infer activities
    i = 0
    while i < len(gpsTraces) - 1:
               
        # Skip over any black points at the beginning 
        while i < len(gpsTraces) - 1 and gpsTraces[i][4] >= gpsAccuracyThreshold:
            i += 1

        # Create a collection of successive points that lie within a circle of radius maxRadius meters
        j = i + 1
        points = [gpsTraces[i]]
        while (j < len(gpsTraces) and gpsTraces[j][4] < gpsAccuracyThreshold 
                and calDistanceToPoint(gpsTraces[j], points) < maxRadius):
            points.append(gpsTraces[j])
            j += 1

        # Check for black points
        k = j 
        while k < len(gpsTraces) and gpsTraces[k][4] >= gpsAccuracyThreshold:
            k += 1
        if k > j:
            if k < len(gpsTraces):
                if calDistanceToPoint(gpsTraces[k], points) < maxRadius:
                    j = k + 1

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

        if k == len(gpsTraces):
            break

    # Impute trips
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
        if activities[-1][-1] < len(gpsTraces) - 1:
            i = len(gpsTraces) - 1
            while i > activities[-1][-1] and gpsTraces[i][4] > gpsAccuracyThreshold:
                i -= 1
            if i != activities[-1][-1]:            
                trips.append([activities[-1][-1], i])
    else:
        trips.append([0, len(gpsTraces)-1])
        

# Functions that calculate the four features of a GPS point: distance to next point (in meters), 
# time interval (seconds), speed (mph) and acceleration (mph2)

def lengthPoint(gpsTraces, j):
   return calDistance(gpsTraces[j][2:4], gpsTraces[j+1][2:4])

def timePoint(gpsTraces, j):
   return (gpsTraces[j+1][1] - gpsTraces[j][1]) / 1000.0

def speedPoint(gpsTraces, j):
  return 2.23694 * (float(lengthPoint(gpsTraces, j)) / timePoint(gpsTraces, j))

def accelerationPoint(gpsTraces, j):
  return abs(speedPoint(gpsTraces, j + 1) - speedPoint(gpsTraces, j)) / (timePoint(gpsTraces,j) / 3600.0)


# Method that that takes as input the list containing GPS data, called gpsTraces, and a tuple containing the 
# indices of the start and end point of a trip, called trip.
#
# The trips are decomposed into their mode chains. 

def inferModeChain(gpsTraces, trip, maxWalkSpeed, maxWalkAcceleration, 
        minSegmentDuration, minSegmentLength, gpsAccuracyThreshold):

    # Step 1: Label GPS points as walk points or non-walk points    
    walkDummy = {}
    i = trip[0]
    while i < trip[1]:
        start, end = i, i
        while end < trip[1] and (gpsTraces[end][4] > gpsAccuracyThreshold 
                or gpsTraces[end + 1][4] > gpsAccuracyThreshold
                or gpsTraces[end + 2][4] > gpsAccuracyThreshold):
            end += 1
        if start == end:
            if speedPoint(gpsTraces, i) < maxWalkSpeed and accelerationPoint(gpsTraces, i) < maxWalkAcceleration:
                walkDummy[i] = 1
	    else:
	       walkDummy[i] = 0
	    i += 1            
	else:
	    distance = calDistance(gpsTraces[start][2:4], gpsTraces[end][2:4])
	    time = (gpsTraces[end][1] - gpsTraces[start][1]) / 1000.0
	    speed = 2.23694 * (float(distance) / time)
	    dummy = int(speed < maxWalkSpeed)
            while i < end:
                walkDummy[i] = dummy
                i += 1
    #print walkDummy 
    #print
    
    # Step 2: Identify walk and non-walk segments as consecutive walk or non-walk points 
    modeChains = []
    beginSegment = trip[0]
    currentPoint = trip[0] + 1
    while currentPoint < trip[1]:
        if walkDummy[currentPoint] != walkDummy[beginSegment]:
            modeChains.append([beginSegment, currentPoint, int(walkDummy[beginSegment] != 0)])
            beginSegment = currentPoint
        currentPoint += 1
    modeChains.append([beginSegment, currentPoint, int(walkDummy[beginSegment] != 0)])
    #print modeChains
    #print

    # Step 3: If the time span of a segment is greater than minSegmentDuration milliseconds, label it 
    # as certain. If it is less than minSegmentDuration milliseconds, and its backward segment is certain,
    # merge it with the backward segment. If no certain backward segment exists, label the segment as 
    # uncertain, and save it as an independent segment. 
    newModeChains = []
    for i in range(0, len(modeChains)):
        if gpsTraces[modeChains[i][1]][1] - gpsTraces[modeChains[i][0]][1] >= minSegmentDuration:
            modeChains[i].append(1)
            newModeChains.append(modeChains[i])
        elif newModeChains and newModeChains[-1][-1] == 1:
            newModeChains[-1][1] = modeChains[i][1]
        else:
            modeChains[i].append(0)
            newModeChains.append(modeChains[i])
    modeChains = newModeChains
    #print modeChains
    #print

    # Step 4: Merge consecutive uncertain segments into a single certain segment. Calculate average
    # speed over segment and compare it against maxWalkSpeed to determine whether walk or non-walk.
    # Check if this segment exceeds minSegmentDuration milliseconds. If it doesn't, and there exists 
    # a certain forward segment, merge the new segment with this forward segment. 
    newModeChains, i = [modeChains[0][0:-1]], 1
    while i < len(modeChains) and modeChains[i][-1] == 0:
        i += 1
    if i > 1:
        newModeChains[0][1] = modeChains[i-1][1]
        distance = calDistance(gpsTraces[newModeChains[0][0]][2:4], gpsTraces[newModeChains[0][1]][2:4])
        time = (gpsTraces[newModeChains[0][1]][1] - gpsTraces[newModeChains[0][0]][1]) / 1000.0
        speed = 2.23694 * (float(distance) / time)
        newModeChains[0][-1] = int(speed < maxWalkSpeed)
    if i < len(modeChains) and modeChains[0][-1] == 0:
        time = (gpsTraces[newModeChains[0][1]][1] - gpsTraces[newModeChains[0][0]][1])
        if time < minSegmentDuration:
            modeChains[i][0] = trip[0]
            newModeChains = []
    while i < len(modeChains):
        newModeChains.append(modeChains[i][:-1])
        i += 1
    modeChains = newModeChains
    #print modeChains
    #print
        
    # Step 5: Merge consecutive walk segments and consecutive non-walk segments
    newModeChains = [modeChains[0]]
    for i in range(1, len(modeChains)):
        if modeChains[i][2] == newModeChains[-1][2]:
            newModeChains[-1][1] = modeChains[i][1]
        else:
            newModeChains.append(modeChains[i])
    modeChains = newModeChains    

    return modeChains
    

# Method that takes as input the GPS data, and the inferred mode chains, and returns the total time elapsed 
# and distance covered over the dataset inferred as trips, and the time and distance correctly inferred
# as either a walk segment or non-walk segment

def calInfAccuray(modeChains, gpsTraces):
    
    timeTotal, timeInferred, distTotal, distInferred = 0, 0, 0, 0
    for modeChain in modeChains:
        for i in range(modeChain[0], modeChain[1]):
            timeTotal += ((gpsTraces[i+1][1] - gpsTraces[i][1])/1000.0)
            distTotal += (calDistance(gpsTraces[i][2:4], gpsTraces[i+1][2:4])/1609.34)            
            
            if ((modeChain[-1] == 1 and gpsTraces[i][10] == 'Trip' and gpsTraces[i][11] == 'Walk') or
                    (modeChain[-1] == 0 and gpsTraces[i][10] == 'Trip' and gpsTraces[i][11] != 'Walk')):
                timeInferred += ((gpsTraces[i+1][1] - gpsTraces[i][1])/1000.0)
                distInferred += (calDistance(gpsTraces[i][2:4], gpsTraces[i+1][2:4])/1609.34)
        
    return timeTotal, timeInferred, distTotal, distInferred 


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
dirPath = '/Users/biogeme/Desktop/Vij/Academics/Current Research/' 

# Shouldn't have to change anything below this for the code to run
dirPath += 'Travel-Diary/Data/Temp/'
dataFiles = [ f for f in listdir(dirPath) if isfile(join(dirPath,f)) ]

timeTotTrips, timeInfTrips, distTotTrips, distInfTrips = 0, 0, 0, 0

for dataFile in dataFiles:
    gpsTraces = []
    filePath = dirPath + dataFile
    try:
        print dataFile + '\n'
        parseCSV(filePath, gpsTraces)
        trips, activities = [], []
        minDuration, maxRadius, minInterval, gpsAccuracyThreshold = 180000, 50, 120000, 200
        inferTripActivity(gpsTraces, trips, activities, minDuration, maxRadius, minInterval, gpsAccuracyThreshold)
        print trips, activities
        print
        
        modeChains = []
        maxWalkSpeed, maxWalkAcceleration, minSegmentDuration, minSegmentLength = 5.60, 1620, 90000, 200
        for trip in trips:
            print trip
            print
            modeChains = inferModeChain(gpsTraces, trip, maxWalkSpeed, maxWalkAcceleration, 
                    minSegmentDuration, minSegmentLength, gpsAccuracyThreshold)
            print modeChains
            print
            timeTotal, timeInferred, distTotal, distInferred = calInfAccuray(modeChains, gpsTraces)            
            timeTotTrips += timeTotal
            timeInfTrips += timeInferred
            distTotTrips += distTotal
            distInfTrips += distInferred
    except:
        pass

print 'Accuracy in terms of time: ' + str(round((timeInfTrips*100)/timeTotTrips, 2)) + '%'
print 'Accuracy in terms of distance: ' + str(round((distInfTrips*100)/distTotTrips, 2)) + '%'
