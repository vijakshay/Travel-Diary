import math
import sys
import tripActivitySeparatorMongo
from pymongo import MongoClient


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


# Functions that calculate the five features of a GPS point: distance to next point (in meters), 
# time interval (seconds), speed (mph), acceleration (mph2) and change in heading (in degrees)

def lengthPoint(gpsTraces, j):
    return tripActivitySeparatorMongo.calDistance(gpsTraces[j]['gpsReading']['location']['coordinates'], 
            gpsTraces[j+1]['gpsReading']['location']['coordinates'])

def timePoint(gpsTraces, j):
    return (gpsTraces[j+1]['epochTime'] - gpsTraces[j]['epochTime']) / 1000.0

def speedPoint(gpsTraces, j):
    return 2.23694 * (float(lengthPoint(gpsTraces, j)) / timePoint(gpsTraces, j))

def accelerationPoint(gpsTraces, j):
    return abs(speedPoint(gpsTraces, j + 1) - speedPoint(gpsTraces, j)) / (timePoint(gpsTraces,j) / 3600.0)

def headingChangePoint(gpsTraces, j):
    return math.fabs(calBearing(gpsTraces[j]['gpsReading']['location']['coordinates'], 
            gpsTraces[j + 1]['gpsReading']['location']['coordinates']) 
            - calBearing(gpsTraces[j + 1]['gpsReading']['location']['coordinates'], 
            gpsTraces[j + 2]['gpsReading']['location']['coordinates']))    
    
    
# Method that takes as input the GPS data and the index of a particular point in the data, and returns
# a list contanining the features of that point

def determineFeatures(gpsTraces, i):
    
    features = {}
    features['Speed'] = speedPoint(gpsTraces, i)
    features['Acceleration'] = accelerationPoint(gpsTraces, i)
    features['Heading Change'] = headingChangePoint(gpsTraces, i)
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
        while end < trip[1] and (gpsTraces[end]['gpsReading']['gpsAccuracy'] > gpsAccuracyThreshold 
                or gpsTraces[end + 1]['gpsReading']['gpsAccuracy'] > gpsAccuracyThreshold
                or gpsTraces[end + 2]['gpsReading']['gpsAccuracy'] > gpsAccuracyThreshold):
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
	    distance = tripActivitySeparatorMongo.calDistance(gpsTraces[start]['gpsReading']['location']['coordinates'], 
	           gpsTraces[end]['gpsReading']['location']['coordinates'])
	    time = (gpsTraces[end]['epochTime'] - gpsTraces[start]['epochTime']) / 1000.0
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
        if gpsTraces[modeChains[i][1]]['epochTime'] - gpsTraces[modeChains[i][0]]['epochTime'] >= minSegmentDuration:
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
        distance = tripActivitySeparatorMongo.calDistance(gpsTraces[newModeChains[0][0]]['gpsReading']['location']['coordinates'], 
                gpsTraces[newModeChains[0][1]]['gpsReading']['location']['coordinates'])
        time = (gpsTraces[newModeChains[0][1]]['epochTime'] - gpsTraces[newModeChains[0][0]]['epochTime']) / 1000.0
        speed = 2.23694 * (float(distance) / time)
        newModeChains[0][-1] = int(speed < maxWalkSpeed)
    if i < len(modeChains) and modeChains[0][-1] == 0:
        time = (gpsTraces[newModeChains[0][1]]['epochTime'] - gpsTraces[newModeChains[0][0]]['epochTime'])
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
    segTotal, segInferred, segWalkInfNonWalk, segNonWalkInfWalk = 0, 0, 0, 0
    for modeChain in modeChains:
        segTotal += 1
        walk, nonWalk, activity = 0, 0, 0
        for i in range(modeChain[0], modeChain[1]):
            try:
                timeTotal += ((gpsTraces[i+1]['epochTime'] - gpsTraces[i]['epochTime'])/1000.0)
                distTotal += (tripActivitySeparatorMongo.calDistance(gpsTraces[i]['gpsReading']['location']['coordinates'], 
                        gpsTraces[i+1]['gpsReading']['location']['coordinates'])/1609.34)            
    
                if gpsTraces[i]['groundTruth']['label'] == 'Trip' and gpsTraces[i]['groundTruth']['mode'] == 'Walk':
                    walk += 1
                elif gpsTraces[i]['groundTruth']['label'] == 'Trip':
                    nonWalk += 1
                else:
                    activity += 1
                            
                if ((modeChain[-1] == 1 and gpsTraces[i]['groundTruth']['label'] == 'Trip' and 
                        gpsTraces[i]['groundTruth']['mode'] == 'Walk') or (modeChain[-1] == 0 and 
                        gpsTraces[i]['groundTruth']['label'] == 'Trip' and gpsTraces[i]['groundTruth']['mode'] != 'Walk')):
                    timeInferred += ((gpsTraces[i+1]['epochTime'] - gpsTraces[i]['epochTime'])/1000.0)
                    distInferred += (tripActivitySeparatorMongo.calDistance(gpsTraces[i]['gpsReading']['location']['coordinates'], 
                            gpsTraces[i+1]['gpsReading']['location']['coordinates'])/1609.34)
            except:
                print "Unexpected error while calculating inference accuracy:", sys.exc_info()[0]
                pass

        if ((max(walk, nonWalk, activity) == walk and modeChain[-1] == 1) 
                or (max(walk, nonWalk, activity) == nonWalk and modeChain[-1] == 0)):
            segInferred += 1
        elif (max(walk, nonWalk, activity) == walk and modeChain[-1] == 0):
            segWalkInfNonWalk += 1
        elif (max(walk, nonWalk, activity) == nonWalk and modeChain[-1] == 1):
            segNonWalkInfWalk += 1
                        
    return (timeTotal, timeInferred, distTotal, distInferred, 
            segTotal, segInferred, segWalkInfNonWalk, segNonWalkInfWalk)  


# Procedure that takes as input a MongoDB collection of location data and a list of test phones,
# and separates the GPS points for each file into walk and non-walk trip segments. Output is the accuracy 
# of the inference when matched against the ground truth, also contained in the MongoDB collection.

def modeChainSeparator(gpsPoints, testPhones):

    print
    reload(tripActivitySeparatorMongo)

    minDuration, maxRadius, minSamplingRate, gpsAccuracyThreshold = 360000, 50, 300000, 200
    minSeparationDistance, minSeparationTime = 100, 360000
    maxWalkSpeed, maxWalkAcceleration, minSegmentDuration, minSegmentLength = 5, 1620, 90000, 200

    timeTotTrips, timeInfTrips, distTotTrips, distInfTrips = 0, 0, 0, 0
    segTotTrips, segInfTrips, segWalkInfNonWalkTrips, segNonWalkInfWalkTrips = 0, 0, 0, 0
    
    for testPhone in testPhones:
        
        print 'Processing data for ' + str(testPhone)
        try:
            query = {'phNum': testPhone}
            projection = {'_id': 0, 'gpsReading': 1, 'epochTime': 1, 'groundTruth': 1, 'movesTime': 1}
            gpsTraces = list(gpsPoints.find(query, projection).sort('epochTime'))
    
            trips, activities, holes = tripActivitySeparatorMongo.inferTripActivity(gpsTraces, minDuration, 
                    maxRadius, minSeparationDistance, minSeparationTime, minSamplingRate, gpsAccuracyThreshold)
            
            for trip in trips:
                modeChains = inferModeChain(gpsTraces, trip, maxWalkSpeed, maxWalkAcceleration, 
                        minSegmentDuration, minSegmentLength, gpsAccuracyThreshold)
    
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
            print "Unexpected error during inference:", sys.exc_info()[0]
            pass

    print
    print 'Accuracy in terms of time: %.0f%% of %.0f hours' %((timeInfTrips*100.0)/timeTotTrips, timeTotTrips)
    print 'Accuracy in terms of distance: %.0f%% of %.0f miles' %((distInfTrips*100.0)/distTotTrips, distTotTrips) 
    print 'Accuracy in terms of number of segments: %.0f%% of %.0f segments' %((segInfTrips*100.0)/segTotTrips, segTotTrips) 
    print ('Percentage of total segments that are walk but inferred as non-walk: %.0f%% of %.0f segments' 
            %((segWalkInfNonWalkTrips*100.0)/segTotTrips, segTotTrips))
    print ('Percentage of total segments that are non-walk but inferred as walk: %.0f%% of %.0f segments' 
            %((segNonWalkInfWalkTrips*100.0)/segTotTrips, segTotTrips))

# Entry point to script

if __name__ == "__main__":
    
    # Mongo database details
    client = MongoClient()
    travelDiary = client.travelDiary
    gpsPoints = travelDiary.gpsPoints
    
    # Test phone numbers, change as appropriate    
    testPhones = [5107259365, 5107250774, 5107250619, 5107250786, 5107250740, 5107250744]
    
    # Call to function
    modeChainSeparator(gpsPoints, testPhones)