from pymongo import MongoClient
import dateutil.parser
import numpy as np
import datetime
from sklearn import tree
from sklearn.externals.six import StringIO
import pydot


def getTimeofDay(segment):
    
    frequency = np.zeros((8))    
    startTime = dateutil.parser.parse(segment['startTime'])
    endTime = dateutil.parser.parse(segment['endTime'])
    while startTime < endTime:
        frequency[startTime.hour/3] += 1
        startTime = startTime + datetime.timedelta(0, 0, 0, 0, 0, 3, 0)    
    return frequency


def getDayOfWeek(segment):

    frequency = np.zeros((3))    
    weekDays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'] 
    weekEnds = ['Saturday', 'Sunday']    
    startTime = dateutil.parser.parse(segment['startTime'])
    endTime = dateutil.parser.parse(segment['endTime'])
    while startTime < endTime:
        currentDay = startTime.strftime('%A')
        if currentDay in weekDays:
            frequency[0] += 1
        elif currentDay in weekEnds:
            frequency[1] += 1
        if currentDay == 'Friday':
            frequency[2] += 1
        startTime = startTime + datetime.timedelta(1)
    return frequency
        

def getDurationInNeighborhood(activity):
    
    nearbyDuration = 0
    centroid = activity['centroid']['coordinates']
    query = {'centroid': {'$nearSphere': {'$geometry': {'type': 'Point',
                                                        'coordinates': [centroid[0], centroid[1]]},
                                          '$maxDistance': 100}},
             'phNum': activity['phNum']}
    nearbyActivities = segments.find(query)
    for nearbyActivity in nearbyActivities:
        nearbyDuration += nearbyActivity['duration']    
    return nearbyDuration


def getTotalDuration(activities):
    
    duration = 0
    for activity in activities:
        duration += activity['duration']
    return duration        


def calFeatures(segments, phNums):
    
    numActivities = segments.find({'type': 'Activity', 'mainPurpose': {'$exists': True}}).count()
    features = np.zeros((numActivities, 14))
    count = 0
    purposes = segments.distinct('mainPurpose')

    for phNum in phNums:
        query = {'type': 'Activity', 'phNum': phNum, 'mainPurpose': {'$exists': True}}
        projection = {'_id': 0, 'trackPoints': 0}
        activities = list(segments.find(query, projection))
        totalDuration = getTotalDuration(activities)
        for activity in activities:            
             
            timeOfDay = getTimeofDay(activity)
            dayOfWeek = getDayOfWeek(activity)
            durationActivity = activity['duration']
            durationInNeighborhood = (100 * getDurationInNeighborhood(activity)) / totalDuration

            features[count, :timeOfDay.shape[0]] = timeOfDay
            features[count, timeOfDay.shape[0]:timeOfDay.shape[0] + dayOfWeek.shape[0]] = dayOfWeek
            features[count, -3] = durationActivity
            features[count, -2] = durationInNeighborhood             
            features[count, -1] = purposes.index(activity['mainPurpose']) + 1
            count += 1
    
    return features


# Entry point to script

if __name__ == "__main__":

    # Mongo database details
    segments = MongoClient('localhost').travelDiary.segments
    
    # Test phone numbers, change as appropriate    
    testPhones = [5107259365, 5107250774, 5107250619, 5107250786, 5107250740, 5107250744]
    
    # Call to function
    features = calFeatures(segments, testPhones)
    featuresEstimation = features[:int(0.9 * np.size(features, 0)), :]
    featuresValidation = features[int(0.9 * np.size(features, 0)):, :]

    clf = tree.DecisionTreeClassifier(max_depth = 10, min_samples_leaf = 5)
    clf = clf.fit(featuresEstimation[:, :-1], featuresEstimation[:, -1])
    infAccuracy = (100.0 * sum(clf.predict(featuresValidation[:, :-1]) == featuresValidation[:, -1])) / np.size(featuresValidation, 0)
    print 'Inference accuracy: %.2f%%' % infAccuracy
    
    dot_data = StringIO() 
    tree.export_graphviz(clf, out_file=dot_data) 
    graph = pydot.graph_from_dot_data(dot_data.getvalue()) 
    outputPath = '/Users/vij/Work/Current Research/Travel-Diary/Documentation/Activity Inference/' 
    graph.write_pdf(outputPath + "purposeDecisionTree01.pdf") 
    
