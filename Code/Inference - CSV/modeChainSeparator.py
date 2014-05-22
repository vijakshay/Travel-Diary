import math
from os import listdir
from os.path import isfile, join
import sys
import tripActivitySeparator 


# Function that calculates the initial bearing in degrees from point 1 to point 2, given the 
# latitude and longitude of both points

def calBearing(point1, point2):

    dLon = math.radians(point2[1]-point1[1])    
    lat1 = math.radians(point1[0])
    lat2 = math.radians(point2[0])
    
    y = math.sin(dLon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dLon)
    b = math.atan2(y, x)

    return math.degrees(b)


# Functions that calculate the four features of a GPS point: distance to next point (in meters), 
# time interval (seconds), speed (mph) and acceleration (mph2)

def lengthPoint(gpsTraces, j):
   return tripActivitySeparator.calDistance(gpsTraces[j][2:4], gpsTraces[j+1][2:4])

def timePoint(gpsTraces, j):
   return (gpsTraces[j+1][1] - gpsTraces[j][1]) / 1000.0

def speedPoint(gpsTraces, j):
  return 2.23694 * (float(lengthPoint(gpsTraces, j)) / timePoint(gpsTraces, j))

def accelerationPoint(gpsTraces, j):
  return abs(speedPoint(gpsTraces, j + 1) - speedPoint(gpsTraces, j)) / (timePoint(gpsTraces,j) / 3600.0)

def headingChange(gpsTraces, j):
    return math.fabs(calBearing(gpsTraces[j][2:4], gpsTraces[j + 1][2:4]) 
            - calBearing(gpsTraces[j + 1][2:4], gpsTraces[j + 2][2:4]))    
    
    
# Methods that takes an input the GPS data and the index of a particular point in the data, and returns
# a list contanining the features of that point

def determineFeatures(gpsTraces, i):
    
    features = {}
    features['Speed'] = speedPoint(gpsTraces, i)
    features['Acceleration'] = accelerationPoint(gpsTraces, i)
    features['Heading Change'] = headingChange(gpsTraces, i)
    return features
    

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
            features = determineFeatures(gpsTraces, i)            
            if features['Acceleration'] <= 945:
                if features['Heading Change'] <= 0.0000:
                    walkDummy[i] = 0
                elif features['Speed'] <= 8.0205:
                    walkDummy[i] = 1
                else:
                    walkDummy[i] = 0
            else:
                walkDummy[i] = 0
	    i += 1            
	else:
	    distance = tripActivitySeparator.calDistance(gpsTraces[start][2:4], gpsTraces[end][2:4])
	    time = (gpsTraces[end][1] - gpsTraces[start][1]) / 1000.0
	    speed = 2.23694 * (float(distance) / time)
	    dummy = int(speed < maxWalkSpeed)
            while i < end:
                walkDummy[i] = dummy
                i += 1
    print walkDummy 
    print
    
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
    print modeChains
    print

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
    print modeChains
    print

    # Step 4: Merge consecutive uncertain segments into a single certain segment. Calculate average
    # speed over segment and compare it against maxWalkSpeed to determine whether walk or non-walk.
    # Check if this segment exceeds minSegmentDuration milliseconds. If it doesn't, and there exists 
    # a certain forward segment, merge the new segment with this forward segment. 
    newModeChains, i = [modeChains[0][0:-1]], 1
    while i < len(modeChains) and modeChains[i][-1] == 0:
        i += 1
    if i > 1:
        newModeChains[0][1] = modeChains[i-1][1]
        distance = tripActivitySeparator.calDistance(gpsTraces[newModeChains[0][0]][2:4], gpsTraces[newModeChains[0][1]][2:4])
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
    print modeChains
    print
        
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
    segTotal, segInferred, segWalkInfNonWalk, segNonWalkInfWalk = 0, 0, 0, 0
    for modeChain in modeChains:
        segTotal += 1
        walk, nonWalk, activity = 0, 0, 0
        for i in range(modeChain[0], modeChain[1]):
            timeTotal += ((gpsTraces[i+1][1] - gpsTraces[i][1])/1000.0)
            distTotal += (tripActivitySeparator.calDistance(gpsTraces[i][2:4], gpsTraces[i+1][2:4])/1609.34)            

            if gpsTraces[i][10] == 'Trip' and gpsTraces[i][11] == 'Walk':
                walk += 1
            elif gpsTraces[i][10] == 'Trip':
                nonWalk += 1
            else:
                activity += 1
                        
            if ((modeChain[-1] == 1 and gpsTraces[i][10] == 'Trip' and gpsTraces[i][11] == 'Walk') or
                    (modeChain[-1] == 0 and gpsTraces[i][10] == 'Trip' and gpsTraces[i][11] != 'Walk')):
                timeInferred += ((gpsTraces[i+1][1] - gpsTraces[i][1])/1000.0)
                distInferred += (tripActivitySeparator.calDistance(gpsTraces[i][2:4], gpsTraces[i+1][2:4])/1609.34)

        if ((max(walk, nonWalk, activity) == walk and modeChain[-1] == 1) 
                or (max(walk, nonWalk, activity) == nonWalk and modeChain[-1] == 0)):
            segInferred += 1
        elif (max(walk, nonWalk, activity) == walk and modeChain[-1] == 0):
            segWalkInfNonWalk += 1
        elif (max(walk, nonWalk, activity) == nonWalk and modeChain[-1] == 1):
            segNonWalkInfWalk += 1
                        
    return (timeTotal, timeInferred, distTotal, distInferred, 
            segTotal, segInferred, segWalkInfNonWalk, segNonWalkInfWalk)  


# Procedure that takes as input a string containing the path to the dircetory containing the GPS data files,
# and calculates for each file the travel mode chain for each trip. Output is the accuracy of the inference
# when matched against the ground truth, also contained in the GPS data files.
#
# The GPS data file is a tab-delimited text file containing the GPS data and ground truth. The file name should 
# follow the generic format: '<test phone number>_<tester alias>_<date data recorded>.txt', where test phone number is a 
# 9-digit number with no brackets and hyphens, and date data recorded is in MMDDYYYY format.
# 
# The file should contain fourteen columns. The first ten columns denote the tester ID, timestamp (in epoch time, 
# recorded in milliseconds), latitude, longitude, GPS accuracy (in feet), battery status (in percentage), 
# sampling rate (in milliseconds), accelermoeter reading, activity as inferred by the Google API, and PST time, 
# respectively. The values for each of these fields will be generated by the tracking app installed on the test phone in 
# the appropriate units, and you shouldn't have to change anything.
#
# The next four columns reflect the ground truth that will be used to train our inference algorithms.
# The eleventh column can take on two string values: (1) Trip, if the individual at the time was making a trip; 
# or (2) Activity, if the individual at the time was engaging in an activity. Columns twelve to fourteen 
# are strings containing information regarding the trip or activity.
#
# Finally, the rows in the file should be ordered in terms of increasing time. 

def modeChainSeparator(dirPath):
    dataFiles = [ f for f in listdir(dirPath) if isfile(join(dirPath,f)) ]
    
    timeTotTrips, timeInfTrips, distTotTrips, distInfTrips = 0, 0, 0, 0
    segTotTrips, segInfTrips, segWalkInfNonWalkTrips, segNonWalkInfWalkTrips = 0, 0, 0, 0
    for dataFile in dataFiles:
        gpsTraces = []
        filePath = dirPath + dataFile
        try:
            print dataFile + '\n'
            tripActivitySeparator.parseCSV(filePath, gpsTraces)
            minDuration, maxRadius, minSamplingRate, gpsAccuracyThreshold = 360000, 50, 300000, 200
            minSeparationDistance, minSeparationTime = 100, 360000
            trips, activities, holes = tripActivitySeparator.inferTripActivity(gpsTraces, minDuration, maxRadius, 
                    minSeparationDistance, minSeparationTime, minSamplingRate, gpsAccuracyThreshold)
            print trips, activities, holes
            print
            
            maxWalkSpeed, maxWalkAcceleration, minSegmentDuration, minSegmentLength = 5, 1620, 90000, 200
            for trip in trips:
                print trip
                print
                modeChains = inferModeChain(gpsTraces, trip, maxWalkSpeed, maxWalkAcceleration, 
                        minSegmentDuration, minSegmentLength, gpsAccuracyThreshold)
                print modeChains
                print
                (timeTotal, timeInferred, distTotal, distInferred, segTotal, segInferred, 
                        segWalkInfNonWalk, segNonWalkInfWalk) = calInfAccuray(modeChains, gpsTraces)           
                timeTotTrips += timeTotal
                timeInfTrips += timeInferred
                distTotTrips += distTotal
                distInfTrips += distInferred
                segTotTrips += segTotal
                segInfTrips += segInferred
                segWalkInfNonWalkTrips += segWalkInfNonWalk
                segNonWalkInfWalkTrips += segNonWalkInfWalk
        except:
            print "Unexpected error:", sys.exc_info()[0]
            pass
    
    print 'Accuracy in terms of time: ' + str(round((timeInfTrips*100)/timeTotTrips, 2)) + '%'
    print 'Accuracy in terms of distance: ' + str(round((distInfTrips*100)/distTotTrips, 2)) + '%'
    print 'Accuracy in terms of number of segments: ' + str(round((segInfTrips*100)/segTotTrips, 2)) + '%'
    print ('Percentage of total segments that are walk but inferred as non-walk: ' 
            + str(round((segWalkInfNonWalkTrips*100)/segTotTrips, 2)) + '%')
    print ('Percentage of total segments that are non-walk but inferred as walk: ' 
            + str(round((segNonWalkInfWalkTrips*100)/segTotTrips, 2)) + '%')
            

# Entry point to script

if __name__ == "__main__":
    
    reload(tripActivitySeparator)

    # Base directory where you clone the repository, change as appropriate
    dirPath = '/Users/vij/Work/Current Research/'
    
    # Folder within the repository containing the data files
    dirPath += 'Travel-Diary/Data/Temp/'
    
    # Call to function
    modeChainSeparator(dirPath)