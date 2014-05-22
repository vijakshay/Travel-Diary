from pymongo import MongoClient
import numpy as np
import tripActivitySeparatorMongo
import datetime, pytz
import dateutil.parser


def calCentroid(trackPoints):

    nTrackPoints = len(trackPoints)
    coordinates = np.zeros((nTrackPoints, 2))
    for i in range(0, nTrackPoints):
        coordinates[i, 0] = trackPoints[i]['location']['coordinates'][0]
        coordinates[i, 1] = trackPoints[i]['location']['coordinates'][1]
    centroid = np.median(coordinates, axis = 0)   
    return centroid     


# Procedure that takes as input a MongoDB collection of location data and a list of test phones,
# and separates the GPS points for each file into trips and activities. The activities are stored
# in the segments collection in the same MongoDB database. 

def addActivities(gpsPoints, segments, testPhones):

    reload(tripActivitySeparatorMongo)
    minDuration, maxRadius, minSamplingRate, gpsAccuracyThreshold = 360000, 50, 300000, 200
    minSeparationDistance, minSeparationTime = 100, 360000
    
    for testPhone in testPhones:
        
        print 'Processing data for ' + str(testPhone)
        query = {'phNum': testPhone}
        projection = {'_id': 1, 'gpsReading': 1, 'epochTime': 1, 'groundTruth': 1, 'movesTime': 1}
        gpsTraces = list(gpsPoints.find(query, projection).sort('epochTime'))
        
        purposes = list(gpsPoints.distinct('groundTruth.purpose'))    
        trips, activities, holes = tripActivitySeparatorMongo.inferTripActivity(gpsTraces, minDuration, maxRadius, 
                minSeparationDistance, minSeparationTime, minSamplingRate, gpsAccuracyThreshold)
        
        for activity in activities:

            trackPoints, wiFiNetwork, location = [], [], []
            purposeCount = {}
            for purpose in purposes:
                purposeCount[purpose] = 0

            for i in range(activity[0], activity[1]):
                trackPoint = {'location': gpsTraces[i]['gpsReading']['location'],
                              'time': gpsTraces[i]['movesTime'],
                              'id': gpsTraces[i]['_id']}
                trackPoints.append(trackPoint)
                if 'wiFiNetwork' in gpsTraces[i]:
                    if gpsTraces[i]['wiFiNetwork'] not in wiFiNetwork:
                        wiFiNetwork.append(gpsTraces[i]['wiFiNetwork'])
                if 'purpose' in gpsTraces[i]['groundTruth']:
                    for gtPurpose in gpsTraces[i]['groundTruth']['purpose']:
                        purposeCount[gtPurpose] += 1
                if 'exactLocation' in gpsTraces[i]['groundTruth']:
                    if gpsTraces[i]['groundTruth']['exactLocation'] not in location:
                        location.append(gpsTraces[i]['groundTruth']['exactLocation'])
            
            centroid = calCentroid(trackPoints)
            centroid = {'coordinates': [centroid[0], centroid[1]],
                        'type': 'Point'}

            maxCount, gtPurpose = purposeCount[max(purposeCount, key = purposeCount.get)], []
            if maxCount > (0.5 * (activity[1] - activity[0])):
                for purpose in purposes:
                    if purposeCount[purpose] == maxCount:
                        gtPurpose.append(purpose)
                                   
            startTime = gpsTraces[activity[0]]['movesTime']
            endTime = gpsTraces[activity[1]]['movesTime']
            duration = (dateutil.parser.parse(endTime) - dateutil.parser.parse(startTime)).total_seconds()
                                    
            record = {'type': 'Activity',
                      'phNum': testPhone,
                      'startTime': startTime,
                      'endTime': endTime,
                      'duration': duration,
                      'purpose': gtPurpose,
                      'location': location,
                      'wiFiNetwork': wiFiNetwork,
                      'centroid': centroid,
                      'trackPoints': trackPoints}

            if 'Sleep' in gtPurpose:
                record['mainPurpose'] = 'Sleep'
            elif 'Waiting' in gtPurpose:
                record['mainPurpose'] = 'Waiting'
            elif ('Work' in gtPurpose) or ('School' in gtPurpose):
                record['mainPurpose'] = 'Mandatory'
            elif ('Household_chores' in gtPurpose) or ('Meals' in gtPurpose) or ('Medical' in 
                    gtPurpose) or ('Personal_services' in gtPurpose) or ('Shopping' in gtPurpose):
                record['mainPurpose'] = 'Maintenance'
            elif ('Recreation' in gtPurpose) or ('Relaxing' in gtPurpose) or ('Social' in gtPurpose):
                record['mainPurpose'] = 'Discretionary'            
            
            if segments.find({'startTime': startTime, 'endTime': endTime, 'phNum': testPhone}).count() == 0:
                segments.insert(record)
                print testPhone, startTime, endTime, maxCount, gtPurpose
        

# Entry point to script

if __name__ == "__main__":

    # Mongo database details
    gpsPoints = MongoClient('localhost').travelDiary.gpsPoints
    segments = MongoClient('localhost').travelDiary.segments
    
    # Test phone numbers, change as appropriate    
    testPhones = [5107259365, 5107250774, 5107250619, 5107250786, 5107250740, 5107250744]
    
    # Call to function
    addActivities(gpsPoints, segments, testPhones)

