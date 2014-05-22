from pymongo import MongoClient
import numpy as np
import datetime
import dateutil.parser
import matplotlib.pyplot as plt


def idDestinations(activity):

    nTrackPoints = len(activity['trackPoints'])
    coordinates = np.zeros((nTrackPoints, 2))
    for i in range(0, nTrackPoints):
        coordinates[i, 0] = activity['trackPoints'][i]['location']['coordinates'][0]
        coordinates[i, 1] = activity['trackPoints'][i]['location']['coordinates'][1]
    centroid = np.median(coordinates, axis = 0)   
    return centroid     
    

# Entry point to script

if __name__ == "__main__":

    # Mongo database details
    gpsPoints = MongoClient('localhost').travelDiary.gpsPoints
    segments = MongoClient('localhost').travelDiary.segments
    
    # Test phone numbers, change as appropriate    
    testPhones = [5107250740]#5107259365, 5107250774, 5107250619, 5107250786, 5107250740, 5107250744]

    # Call to function
    for testPhone in testPhones:
        print 'Processing data for ' + str(testPhone)
        query = {'phNum': testPhone}
        projection = {'trackPoints': 0}
        activities = list(segments.find(query, projection).sort('duration'))
        destinations, totalDuration = [], 0
        for activity in activities:
            totalDuration += activity['duration']
            nearbyDuration, nearbyPurpose = 0, []
            centroid = activity['centroid']['coordinates']
            query = {'centroid': {'$nearSphere': {'$geometry': {'type': 'Point',
                                                                'coordinates': [centroid[0], centroid[1]]},
                                                  '$maxDistance': 100}},
                     'phNum': testPhone}
            nearbyActivities = segments.find(query, projection)
            for nearbyActivity in nearbyActivities:
                nearbyDuration += nearbyActivity['duration']
                for purpose in nearbyActivity['purpose']:
                    if purpose not in nearbyPurpose:
                        nearbyPurpose.append(purpose)
            destination = {'duration': nearbyDuration,
                           'purpose': nearbyPurpose}
            destinations.append(destination)
        for destination in destinations:
            destination['durationPercent'] = (100 * destination['duration']) / totalDuration
