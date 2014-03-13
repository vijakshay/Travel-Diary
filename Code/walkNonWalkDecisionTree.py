import csv
import math
import numpy
import sys
from os import listdir
from os.path import isfile, join
from sklearn import tree
from sklearn.externals.six import StringIO
import pydot



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
    

# Function that takes as input two lists of points, where a point is itself a list containing 
# the elements in the row in the input file corresponding to that point. The function outputs the 
# distance, in meters, between the median points in the two lists

def calDistanceBetweenPoints(points1, points2):
    latLon1, latLon2 = numpy.zeros(shape = (len(points1), 2)), numpy.zeros(shape = (len(points2), 2))
    for i in range(0, len(points1)):
        latLon1[i, 0] = points1[i][2]
        latLon1[i, 1] = points1[i][3]
    for i in range(0, len(points2)):
        latLon2[i, 0] = points2[i][2]
        latLon2[i, 1] = points2[i][3]
    point1 = [numpy.median(latLon1[:, 0]), numpy.median(latLon1[:, 1])]
    point2 = [numpy.median(latLon2[:, 0]), numpy.median(latLon2[:, 1])]    
    return calDistance(point1, point2)


# Procedure that takes as input the start and end points to an event, the list of events and holes,
# the list comprising the raw GPS data and the threshold for labelling a gap in the data a hole,
# and infers holes in the data and splits the event accordingly into multiple events

def inferHoles(eventStart, eventEnd, events, holes, gpsTraces, minSamplingRate):
    j = eventStart + 1
    while j <= eventEnd:
        while (j < eventEnd and 
                gpsTraces[j][1] - gpsTraces[j - 1][1] < minSamplingRate):
            j += 1
        if gpsTraces[j][1] - gpsTraces[j - 1][1] >= minSamplingRate:
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
        while i < len(gpsTraces) - 1 and gpsTraces[i][4] >= gpsAccuracyThreshold:
            i += 1

        # Create a collection of successive points that lie within a circle of radius maxRadius meters, such that no
        # two consecutive points in space are separated by more than minSamplingRate milliseconds
        j = i + 1
        points = [gpsTraces[i]]
        while (j < len(gpsTraces) and gpsTraces[j][4] < gpsAccuracyThreshold 
                and gpsTraces[j][1] - gpsTraces[j-1][1] < minSamplingRate
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
            
            # Check if the activity is separated in space from previous activity by at least minSeparationDistance meters
            # and separated in time by minSeparationTime milliseconds
            if (len(activities) > 0 and gpsTraces[j-1][1] - gpsTraces[activities[-1][1]][1] < minSeparationTime
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


# Functions that calculate the four features of a GPS point: distance to next point (in meters), 
# time interval (seconds), speed (mph), acceleration (mph2) and change in heading

def lengthPoint(gpsTraces, j):
   return calDistance(gpsTraces[j][2:4], gpsTraces[j+1][2:4])

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
    
    features = []
    features.append(speedPoint(gpsTraces, i))
    features.append(accelerationPoint(gpsTraces, i))
    features.append(headingChange(gpsTraces, i))
    return features
    

# Procedure that takes as input the GPS data, and the inferred trips, and calculates the 
# features for each data point and attaches the ground truth label

def labelData(gpsTraces, trip, labeledData):
    
    walk, nonWalk, activity = 0, 0, 0
    for i in range(trip[0], trip[1]):
        try:
            features = determineFeatures(gpsTraces, i)
            if gpsTraces[i][10] == 'Trip' and gpsTraces[i][11] == 'Walk':
                features.append(1)
                labeledData.append(features)
            elif gpsTraces[i][10] == 'Trip':
                features.append(0)
                labeledData.append(features)    
        except:
            print "Unexpected error:", sys.exc_info()[0]
            pass


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


# The input file is a csv containing the GPS data and ground truth. The file name should follow the generic
# format: '<test phone number>_<tester alias>_<date data recorded>.csv', where test phone number is a 
# 9-digit number with no brackets and hyphens, and date data recorded is in MMDDYYYY format.
# 
# The file should contain fourteen columns. The first ten columns denote the tester ID, timestamp (in epoch time, 
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
inputPath = dirPath + 'Travel-Diary/Data/Google Play API/'
outputPath = dirPath + 'Travel-Diary/Documentation/Change Point Segmentation/'

dataFiles = [ f for f in listdir(inputPath) if isfile(join(inputPath,f)) ]

minDuration, maxRadius, minSamplingRate, gpsAccuracyThreshold = 360000, 50, 300000, 200
minSeparationDistance, minSeparationTime = 100, 360000
labeledData = []

for dataFile in dataFiles:
    gpsTraces = []
    filePath = inputPath + dataFile
    try:
        parseCSV(filePath, gpsTraces)
        trips, activities, holes = inferTripActivity(gpsTraces, minDuration, maxRadius, minSeparationDistance, 
                minSeparationTime, minSamplingRate, gpsAccuracyThreshold)
        print dataFile, trips, activities, holes 

        for trip in trips:
            labelData(gpsTraces, trip, labeledData)

    except:
        print "Unexpected error:", sys.exc_info()[0]
        pass

labeledData = convertListToArray(labeledData)
clf = tree.DecisionTreeClassifier(max_depth = 3, min_samples_leaf = 5)
clf = clf.fit(labeledData[:, :-1], labeledData[:, -1])

dot_data = StringIO() 
tree.export_graphviz(clf, out_file=dot_data) 
graph = pydot.graph_from_dot_data(dot_data.getvalue()) 
graph.write_pdf(outputPath + "walkNonWalkDecisionTree.pdf") 