import numpy
import sys
import tripActivitySeparatorMongo
import modeChainSeparatorMongo
from pymongo import MongoClient
from sklearn import tree
from sklearn.externals.six import StringIO
import pydot


def determineFeatures(modeChain, gpsTraces, hcrThreshold, srThreshold, vcrTheshold, minSamplingRate):
    
    numPoints = modeChain[1] - modeChain[0]
    distance, time, hcr, sr, vcr, counter = 0, 0, 0, 0, 0, 0
    speed, acceleration = numpy.zeros(shape = (numPoints,1)), numpy.zeros(shape = (numPoints,1))    
    for i in range(modeChain[0], modeChain[1]):
        distance += modeChainSeparatorMongo.lengthPoint(gpsTraces, i)
        time += modeChainSeparatorMongo.timePoint(gpsTraces, i)
        hcr += int(modeChainSeparatorMongo.headingChangePoint(gpsTraces, i) > hcrThreshold)  
        speed[counter, 0] = modeChainSeparatorMongo.speedPoint(gpsTraces, i)
        sr += int(speed[counter, 0] < srThreshold)
        acceleration[counter, 0] = modeChainSeparatorMongo.accelerationPoint(gpsTraces, i)
        if gpsTraces[i+1]['epochTime'] - gpsTraces[i]['epochTime'] < minSamplingRate:
            vcr += int((abs(modeChainSeparatorMongo.speedPoint(gpsTraces, i + 1) - 
                    speed[counter, 0]) / speed[counter, 0]) > vcrTheshold)
        counter += 1
    hcr /= distance
    sr /= distance
    vcr /= distance
    averageSpeed = distance/time
    expectedSpeed = numpy.sum(speed, axis = 0) / numPoints
    varianceSpeed = numpy.var(speed, axis = 0)   
    speed, acceleration = numpy.sort(speed, axis = 0), numpy.sort(acceleration, axis = 0)
    features = [distance, hcr, sr, vcr, averageSpeed, expectedSpeed[0], varianceSpeed[0]]
    features.extend((speed[-1, 0], speed[-2, 0], speed[-3, 0]))
    features.extend((acceleration[-1, 0], acceleration[-2, 0], acceleration[-3, 0]))
    return features


# Procedure that takes as input a list of lists, where each element of the inner list is a numeric value,
# and return a 2-D numpy matrix containing the same elements

def convertListToArray(inputLists):
    outputArray, currentRow = numpy.zeros(shape = (len(inputLists), len(inputLists[0]))), 0
    for inputList in inputLists:
        currentColumn = 0
        for inputElement in inputList:
            outputArray[currentRow, currentColumn] = inputElement
            currentColumn += 1
        currentRow += 1
    return outputArray


# Procedure that takes as input the GPS data, and the inferred mode chain for trips, and calculates the 
# features for the mode chain and attaches the ground truth mode label

def determineModes(modeChains, modeData, gpsTraces, hcrThreshold, srThreshold, vcrTheshold, minSamplingRate):
    
    for modeChain in modeChains:
        
        try:
            if modeChain[1] - modeChain[0] >= 3:
                features = determineFeatures(modeChain, gpsTraces, hcrThreshold, srThreshold, vcrTheshold, minSamplingRate)
                
                walk, bike, car, transit, other = 0, 0, 0, 0, 0
                for i in range(modeChain[0], modeChain[1]):
                    if gpsTraces[i]['groundTruth']['label'] == 'Trip' and gpsTraces[i]['groundTruth']['mode'] == 'Walk':
                        walk += 1
                    elif gpsTraces[i]['groundTruth']['label'] == 'Trip' and gpsTraces[i]['groundTruth']['mode'] == 'Bike':
                        bike += 1
                    elif gpsTraces[i]['groundTruth']['label'] == 'Trip' and gpsTraces[i]['groundTruth']['mode'] == 'Car':
                        car += 1
                    elif gpsTraces[i]['groundTruth']['label'] == 'Trip' and gpsTraces[i]['groundTruth']['mode'] == 'Transit':
                        transit += 1
                    else:
                        other += 1
                        
                if max(walk, bike, car, transit, other) == walk:
                    features.append(1)
                    modeData.append(features)
                elif max(walk, bike, car, transit, other) == bike:
                    features.append(2)
                    modeData.append(features)
                elif max(walk, bike, car, transit, other) == car:
                    features.append(3)
                    modeData.append(features)
                elif max(walk, bike, car, transit, other) == transit:
                    features.append(4)
                    modeData.append(features)

        except:
            print "Unexpected error while calculating features:", sys.exc_info()[0]
            pass


# Procedure that takes as input a MongoDB collection of location data and a list of test phones,
# separates the GPS points into trip segments, and constructs a dictionary of segments, and their 
# features, corresponding to each of the four travel modes.

def constructDT(gpsPoints, testPhones):
    
    reload(tripActivitySeparatorMongo)
    reload(modeChainSeparatorMongo)

    minDuration, maxRadius, minSamplingRate, gpsAccuracyThreshold = 360000, 50, 300000, 200
    minSeparationDistance, minSeparationTime = 100, 360000
    maxWalkSpeed, maxWalkAcceleration, minSegmentDuration, minSegmentLength = 5, 1620, 90000, 200
    hcrThreshold, srThreshold, vcrTheshold = 19, 7.6, 0.26
    
    modeData = []

    for testPhone in testPhones:
        
        print 'Processing data for ' + str(testPhone)
        try:
            query = {'phNum': testPhone}
            projection = {'_id': 0, 'gpsReading': 1, 'epochTime': 1, 'groundTruth': 1, 'movesTime': 1}
            gpsTraces = list(gpsPoints.find(query, projection).sort('epochTime'))
    
            trips, activities, holes = tripActivitySeparatorMongo.inferTripActivity(gpsTraces, minDuration, 
                    maxRadius, minSeparationDistance, minSeparationTime, minSamplingRate, gpsAccuracyThreshold)
            
            for trip in trips:
                modeChains = modeChainSeparatorMongo.inferModeChain(gpsTraces, trip, maxWalkSpeed, maxWalkAcceleration, 
                        minSegmentDuration, minSegmentLength, gpsAccuracyThreshold)
                determineModes(modeChains, modeData, gpsTraces, hcrThreshold, srThreshold, vcrTheshold, minSamplingRate)
        except:
            print "Unexpected error during inference:", sys.exc_info()[0]
            pass

    return modeData
        

# Entry point to script

if __name__ == "__main__":
    
    # Mongo database details
    client = MongoClient()
    travelDiary = client.travelDiary
    gpsPoints = travelDiary.gpsPoints
    
    # Test phone numbers, change as appropriate    
    testPhones = [5107259365, 5107250774, 5107250619, 5107250786, 5107250740, 5107250744]
    
    # Call to function
    modeData = constructDT(gpsPoints, testPhones)    
    
    modeData = convertListToArray(modeData)
    modeDataEstimation = modeData[:int(0.9 * numpy.size(modeData, 0)), :]
    modeDataValidation = modeData[int(0.9 * numpy.size(modeData, 0)):, :]

    clf = tree.DecisionTreeClassifier(max_depth = 10, min_samples_leaf = 5)
    clf = clf.fit(modeDataEstimation[:, :-1], modeDataEstimation[:, -1])
    infAccuracy = (100.0 * sum(clf.predict(modeDataValidation[:, :-1]) == modeDataValidation[:, -1])) / numpy.size(modeDataValidation, 0)
    print 'Inference accuracy: %.2f%%' % infAccuracy
    
    dot_data = StringIO() 
    tree.export_graphviz(clf, out_file=dot_data) 
    graph = pydot.graph_from_dot_data(dot_data.getvalue()) 
    outputPath = '/Users/vij/Work/Current Research/Travel-Diary/Documentation/Mode Inference/' 
    graph.write_pdf(outputPath + "modeDecisionTree.pdf") 
