import csv
import math
import numpy
from os import listdir
from os.path import isfile, join
import sys
from pymongo import MongoClient


# Function that uses the haversine formula to calculate the 'great-circle' distance in meters
# between two points whose longitude and latitude are known

def calDistance(point1, point2):

    earthRadius = 6371000 
    dLon = math.radians(point1[0]-point2[0])    
    dLat = math.radians(point1[1]-point2[1])
    lat1 = math.radians(point1[1])
    lat2 = math.radians(point2[1])
    
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
        dist = (calDistance(point['gpsReading']['location']['coordinates'], 
                points[i]['gpsReading']['location']['coordinates']) - 
                point['gpsReading']['gpsAccuracy'] - points[i]['gpsReading']['gpsAccuracy'])
        if dist > maxDistance:
            maxDistance = dist
    return maxDistance
    

# Function that takes as input two lists of points, where a point is itself a list containing 
# the elements in the row in the input file corresponding to that point. The function outputs the 
# distance, in meters, between the median points in the two lists

def calDistanceBetweenPoints(points1, points2):
        
    if len(points1) % 2 == 0:
        points1 = sorted(points1, key = lambda point: point['gpsReading']['location']['coordinates'][0])
        medLon1 = (points1[(len(points1)/2) - 1]['gpsReading']['location']['coordinates'][0] + 
                points1[len(points1)/2]['gpsReading']['location']['coordinates'][0]) / 2
        points1 = sorted(points1, key = lambda point: point['gpsReading']['location']['coordinates'][1])
        medLat1 = (points1[(len(points1)/2) - 1]['gpsReading']['location']['coordinates'][1] + 
                points1[len(points1)/2]['gpsReading']['location']['coordinates'][1]) / 2    
    else:
        points1 = sorted(points1, key = lambda point: point['gpsReading']['location']['coordinates'][0])
        medLon1 = points1[(len(points1)/2)]['gpsReading']['location']['coordinates'][0]
        points1 = sorted(points1, key = lambda point: point['gpsReading']['location']['coordinates'][1])
        medLat1 = points1[(len(points1)/2)]['gpsReading']['location']['coordinates'][1]

    if len(points2) % 2 == 0:
        points2 = sorted(points2, key = lambda point: point['gpsReading']['location']['coordinates'][0])
        medLon2 = (points2[(len(points2)/2) - 1]['gpsReading']['location']['coordinates'][0] + 
                points2[len(points2)/2]['gpsReading']['location']['coordinates'][0]) / 2
        points2 = sorted(points2, key = lambda point: point['gpsReading']['location']['coordinates'][1])
        medLat2 = (points2[(len(points2)/2) - 1]['gpsReading']['location']['coordinates'][1] + 
                points2[len(points2)/2]['gpsReading']['location']['coordinates'][1]) / 2    
    else:
        points2 = sorted(points2, key = lambda point: point['gpsReading']['location']['coordinates'][0])
        medLon2 = points2[(len(points2)/2)]['gpsReading']['location']['coordinates'][0]
        points2 = sorted(points2, key = lambda point: point['gpsReading']['location']['coordinates'][1])
        medLat2 = points2[(len(points2)/2)]['gpsReading']['location']['coordinates'][1]
        
    point1 = [medLon1, medLat1]
    point2 = [medLon2, medLat2]    
    return calDistance(point1, point2)


# Procedure that takes as input the start and end points to an event, the list of events and holes,
# the list comprising the raw GPS data and the threshold for labelling a gap in the data a hole,
# and infers holes in the data and splits the event accordingly into multiple events

def inferHoles(eventStart, eventEnd, events, holes, gpsTraces, minSamplingRate):
    j = eventStart + 1
    while j <= eventEnd:
        while (j < eventEnd and 
                gpsTraces[j]['epochTime'] - gpsTraces[j - 1]['epochTime'] < minSamplingRate):
            j += 1
        if gpsTraces[j]['epochTime'] - gpsTraces[j - 1]['epochTime'] >= minSamplingRate:
            holes.append([j - 1, j])
            if j - 1 > eventStart:
                events.append([eventStart, j - 1])
        else:
            events.append([eventStart, j])
        eventStart, j = j, j + 1
    
    
# Method that takes as input the list containing GPS data, called gpsTraces, and two empty lists, 
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

def inferTripActivity(gpsTraces, minDuration, maxRadius, minSeparationDistance, 
        minSeparationTime, minSamplingRate, gpsAccuracyThreshold):
    
    trips, activities, holes = [], [], []
    
    # Infer activities
    i = 0
    while i < len(gpsTraces) - 1:
               
        # Skip over any black points at the beginning 
        while i < len(gpsTraces) - 1 and gpsTraces[i]['gpsReading']['gpsAccuracy'] >= gpsAccuracyThreshold:
            i += 1

        # Create a collection of successive points that lie within a circle of radius maxRadius meters, such that no
        # two consecutive points in space are separated by more than minSamplingRate milliseconds
        j = i + 1
        points = [gpsTraces[i]]
        while (j < len(gpsTraces) and gpsTraces[j]['gpsReading']['gpsAccuracy'] < gpsAccuracyThreshold 
                and gpsTraces[j]['epochTime'] - gpsTraces[j-1]['epochTime'] < minSamplingRate
                and calDistanceToPoint(gpsTraces[j], points) < maxRadius):
            points.append(gpsTraces[j])
            j += 1

        # Check for black points
        k = j 
        while k < len(gpsTraces) and gpsTraces[k]['gpsReading']['gpsAccuracy'] >= gpsAccuracyThreshold:
            k += 1
        if k > j:
            if k < len(gpsTraces):
                if calDistanceToPoint(gpsTraces[k], points) < maxRadius:
                    j = k + 1

        # Check if the duration over which these points were collected exceeds minDuration milliseconds
        if gpsTraces[j-1]['epochTime'] - gpsTraces[i]['epochTime'] > minDuration:
            
            # Check if the activity is separated in space from previous activity by at least minSeparationDistance meters
            # and separated in time by minSeparationTime milliseconds
            if (len(activities) > 0 and gpsTraces[j-1]['epochTime'] - gpsTraces[activities[-1][1]]['epochTime'] < minSeparationTime
                    and calDistanceBetweenPoints(gpsTraces[activities[-1][0]:activities[-1][1]], 
                    gpsTraces[i:j-1]) < minSeparationDistance):                
                activities[-1][-1] = j-1
            else:
                activities.append([i, j-1])
            i = j - 1
        else:
            i += 1
        
        if k == len(gpsTraces):
            break
        
    # Impute trips and identify holes in data
    numActivities, newActivities = len(activities), []
    if numActivities != 0:
        
        # Check if the GPS log begins with a trip
        if activities[0][0] != 0:
            inferHoles(0, activities[0][0], trips, holes, gpsTraces, minSamplingRate)
        
        # Interpolate trips from activities and identify holes in activities
        if numActivities > 1:
            for i in range(0, numActivities - 1):            
                inferHoles(activities[i][0], activities[i][1], newActivities, holes, gpsTraces, minSamplingRate)
                inferHoles(activities[i][1], activities[i + 1][0], trips, holes, gpsTraces, minSamplingRate)
        
        # Identify holes in the last activity
        inferHoles(activities[-1][0], activities[-1][1], newActivities, holes, gpsTraces, minSamplingRate)

        # Check if the GPS log ends with a trip
        if activities[-1][-1] < len(gpsTraces) - 2:
            inferHoles(activities[-1][1], len(gpsTraces) - 2, trips, holes, gpsTraces, minSamplingRate)
    
    # If the data comprises a single trip
    else:
        trips.append([0, len(gpsTraces)-1])
    
    return trips, newActivities, holes


# Method that takes as input the GPS data, and the inferred trips and activities, and returns the 
# total time elapsed and distance covered over the dataset, and the time and distance correctly inferred
# as either a trip or an activity

def calInfAccuray(trips, activities, gpsTraces, minSamplingRate):
    
    tripsInferred, numTripsInferred = [], 0
    for trip in trips:
        tripInferred = range(trip[0], trip[1])
        tripsInferred += tripInferred
        numTrips, numActivities = 0, 0
        for i in tripInferred:
            if gpsTraces[i]['groundTruth']['label'] == 'Trip':
                numTrips += 1
            elif gpsTraces[i]['groundTruth']['label'] == 'Activity':
                numActivities += 1
        if numTrips > (len(tripInferred)/2):
            numTripsInferred += 1
        '''
        else:            
            print '\nTrip'            
            print 'Moves time:', gpsTraces[trip[0]]['movesTime'], gpsTraces[trip[1]]['movesTime']
            print 'Epoch time: %.0f %.0f' % (gpsTraces[trip[0]]['epochTime'], gpsTraces[trip[1]]['epochTime']) 
            print 'Coordinates:'
            print (str(gpsTraces[trip[0]-1]['gpsReading']['location']['coordinates'][0]) + ', ' + 
                    str(gpsTraces[trip[0]-1]['gpsReading']['location']['coordinates'][1]))
            print (str(gpsTraces[trip[1]]['gpsReading']['location']['coordinates'][0]) + ', ' + 
                    str(gpsTraces[trip[1]]['gpsReading']['location']['coordinates'][1]))
            raw_input('Press Enter to continue: ')
        '''
    activitiesInferred, numActivitiesInferred = [], 0
    for activity in activities:
        activityInferred = range(activity[0], activity[1])
        activitiesInferred += activityInferred
        numTrips, numActivities = 0, 0
        for i in activityInferred:
            if gpsTraces[i]['groundTruth']['label'] == 'Trip':
                numTrips += 1
            elif gpsTraces[i]['groundTruth']['label'] == 'Activity':
                numActivities += 1
        if numActivities > (len(activityInferred)/2):
            numActivitiesInferred += 1
        '''
        else:
            print '\nActivity'
            print 'Moves time:', gpsTraces[activity[0]]['movesTime'], gpsTraces[activity[1]]['movesTime']
            print 'Epoch time: %.0f %.0f' % (gpsTraces[activity[0]]['epochTime'], gpsTraces[activity[1]]['epochTime']) 
            print 'Coordinates:'
            print (str(gpsTraces[activity[0]-1]['gpsReading']['location']['coordinates'][0]) + ', ' + 
                    str(gpsTraces[activity[0]-1]['gpsReading']['location']['coordinates'][1]))
            print (str(gpsTraces[activity[1]]['gpsReading']['location']['coordinates'][0]) + ', ' + 
                    str(gpsTraces[activity[1]]['gpsReading']['location']['coordinates'][1]))
            raw_input('Press Enter to continue: ')
        '''
    timeTotal, timeInferred, distTotal, distInferred = 0, 0, 0, 0
    for i in range(0, len(gpsTraces) - 1):
        if (gpsTraces[i+1]['epochTime'] - gpsTraces[i]['epochTime']) < minSamplingRate:
            
            timeTotal += ((gpsTraces[i+1]['epochTime'] - gpsTraces[i]['epochTime'])/1000.0)
            distTotal += (calDistance(gpsTraces[i]['gpsReading']['location']['coordinates'], 
                    gpsTraces[i+1]['gpsReading']['location']['coordinates'])/1609.34)            

            if gpsTraces[i]['groundTruth']['label'] == 'Trip' and i in tripsInferred:
                timeInferred += ((gpsTraces[i+1]['epochTime'] - gpsTraces[i]['epochTime'])/1000.0)
                distInferred += (calDistance(gpsTraces[i]['gpsReading']['location']['coordinates'], 
                        gpsTraces[i+1]['gpsReading']['location']['coordinates'])/1609.34)
    
            if gpsTraces[i]['groundTruth']['label'] == 'Activity' and i in activitiesInferred:
                timeInferred += ((gpsTraces[i+1]['epochTime'] - gpsTraces[i]['epochTime'])/1000.0)
                distInferred += (calDistance(gpsTraces[i]['gpsReading']['location']['coordinates'], 
                        gpsTraces[i+1]['gpsReading']['location']['coordinates'])/1609.34)
        
    return timeTotal, timeInferred, distTotal, distInferred, numTripsInferred, numActivitiesInferred 


# Procedure that takes as input a MongoDB collection of location data and a list of test phones,
# and separates the GPS points for each file into trips and activities. Output is the accuracy 
# of the inference when matched against the ground truth, also contained in the MongoDB collection.

def tripActivitySeparator(gpsPoints, testPhones):

    minDuration, maxRadius, minSamplingRate, gpsAccuracyThreshold = 360000, 50, 300000, 200
    minSeparationDistance, minSeparationTime = 100, 360000
    timeTot, timeInf, distTot, distInf = 0, 0, 0, 0
    numTotTrips, numInfTrips, numTotActivities, numInfActivities = 0, 0, 0, 0
    
    for testPhone in testPhones:
        
        print 'Processing data for ' + str(testPhone)
        try:
            query = {'phNum': testPhone}
            projection = {'_id': 0, 'gpsReading': 1, 'epochTime': 1, 'groundTruth': 1, 'movesTime': 1}
            gpsTraces = list(gpsPoints.find(query, projection).sort('epochTime'))
    
            trips, activities, holes = inferTripActivity(gpsTraces, minDuration, maxRadius, minSeparationDistance, 
                    minSeparationTime, minSamplingRate, gpsAccuracyThreshold)
            
            timeTotal, timeInferred, distTotal, distInferred, numTripsInferred, numActivitiesInferred = calInfAccuray(trips, 
                    activities, gpsTraces, minSamplingRate)
            timeTot += timeTotal
            timeInf += timeInferred
            distTot += distTotal
            distInf += distInferred
            numTotTrips += len(trips)
            numInfTrips += numTripsInferred
            numTotActivities += len(activities)
            numInfActivities += numActivitiesInferred
        
        except:
            print "Unexpected error:", sys.exc_info()[0]
            pass

    print
    print 'Accuracy in terms of time: %.0f%% of %.0f hours' %((timeInf*100.0)/timeTot, timeTot/3600.0)
    print 'Accuracy in terms of distance: %.0f%% of %.0f miles' %((distInf*100.0)/distTot, distTot) 
    print ('Accuracy in terms of number of activities: %.0f%% of %.0f activities'  
            %((numInfActivities*100)/numTotActivities, numTotActivities))
    print 'Accuracy in terms of number of trips: %.0f%% of %.0f trips' %((numInfTrips*100)/numTotTrips, numTotTrips) 


# Entry point to script

if __name__ == "__main__":

    # Mongo database details
    client = MongoClient()
    travelDiary = client.travelDiary
    gpsPoints = travelDiary.gpsPoints
    
    # Test phone numbers, change as appropriate    
    testPhones = [5107259365, 5107250774, 5107250619, 5107250786, 5107250740, 5107250744]
    
    # Call to function
    tripActivitySeparator(gpsPoints, testPhones)

