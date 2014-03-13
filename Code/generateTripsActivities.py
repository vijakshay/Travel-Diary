import urllib2 
import csv
import math
import numpy
import sys
from os import remove


# Check if a given year is a leap year or not

def isLeapYear(year):
    if year % 400 == 0:
        return True
    if year % 100 == 0:
        return False
    if year % 4 == 0:
        return True
    return False


# Calculate days in a month for a given year

def daysInMonth(year, month):
    if month in (1, 3, 5, 7, 8, 10, 12):
        return 31
    elif month == 2:
        if isLeapYear(year):
            return 29
        return 28
    return 30


# Calculate next day as per the Gregorian calendar

def nextDay(year, month, day):
    if day < daysInMonth(year, month):
        return year, month, day + 1
    else:
        if month == 12:
            return year + 1, 1, 1
        else:
            return year, month + 1, 1
        

# Returns True if year1-month1-day1 is after year2-month2-day2.  Otherwise, returns False.

def dateIsAfter(year1, month1, day1, year2, month2, day2):
    if year1 > year2:
        return True
    if year1 == year2:
        if month1 > month2:
            return True
        if month1 == month2:
            return day1 > day2
    return False        


# Returns the starting and ending epoch Time in milliseconds for a given day, as per PST. 
# Input must be a 8-character string containing a valid date in MMDDYYYY format.

def epochTime(date, gmtConversion):

    year1 = 1970
    month1 = 1
    day1 = 1

    year2 = int(date[4:8])
    month2 = int(date[0:2])
    day2 = int(date[2:4])
    
    days = 0
    while dateIsAfter(year2, month2, day2, year1, month1, day1):
        days += 1
        (year1, month1, day1) = nextDay(year1, month1, day1)
    
    startTime = ((days * 24) - gmtConversion) * 3600 * 1000
    endTime = startTime + (24 * 3600 * 1000)
    return startTime, endTime


# Procedure that takes as input strings deonting the tester name, test phone number, date, difference between 
# local time zone and UTC time, and the GPS file path name. Output is a list of lists containing GPS data 
# for that tester, phone and day.

def getNewGPSData(testerName, phoneNum, date, gmtConversion, gpsFilePath):

    url = 'http://' + phoneNum + 'gp.appspot.com/gaeandroid?query=1'
    data = urllib2.urlopen(url)
    
    localFile = open(gpsFilePath, 'w')
    localFile.write(data.read())
    localFile.close()

    startTime, endTime = epochTime(date, gmtConversion)

    gpsData = []
    with open(gpsFilePath, 'rU') as csvfile:
        for row in csv.reader(csvfile, delimiter = '\t'):
            try:
                if int(row[1]) >= startTime and int(row[1]) <= endTime:
                    tList = []
                    for element in row:
                        try:
                            tList.append(float(element))    
                        except:
                            tList.append(element)    
                    gpsData.append(tList)
            except:
                pass            
    gpsData = sorted(gpsData, key = lambda x: int(x[1]))
    remove(gpsFilePath)
    with open(gpsFilePath, "wb") as f:
        writer = csv.writer(f, delimiter = '\t')
        writer.writerows(gpsData)
    return gpsData


# Procedure that takes as input a tab-delimited txt file, and stores the data as a list, 
# where each element of the list is a list itself that corresponds to a row in the file,
# and each element of that list corresponds to an entry in that row. 

def getExistingGPSData(filePath):
    data = []
    with open(filePath, 'rU') as csvfile:
        for row in csv.reader(csvfile, delimiter = '\t'):
            tList = []
            for element in row:
                try:
                    tList.append(float(element))    
                except:
                    tList.append(element)    
            data.append(tList)
    return data


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
# time interval (seconds), speed (mph) and acceleration (mph2)

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
    

def writeFile(data, filePath):
    
    for tester in data:
        fileName = filePath + tester['ph'] + '_' + tester['tester'] + '_' + tester['date'] + '.csv'
        csvout = csv.writer(open(fileName, "wb"))
        csvout.writerow(("Start Time", "End Time", "Type", "Comments"))
        try:
            for event in tester['Day Schedule']:
                csvout.writerow((event['Start Time'], event['End Time'], event['Type']))
        except:
            pass
    

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

# Day for which you wish to extract trips and activities
date = '03122014'        # MMDDYYYY format of day for which you wish to extract data
gmtConversion = -7       # Difference in hours between local time and UTC time, remember to change for daylight savings
gmtConversion -= 3       # Adjusted to allow the day to begin at 3 AM

# Tester personal details, change as appropriate
testers = [{'name': 'Andrew', 'ph': '5107259365'},
           {'name': 'Caroline', 'ph': '5107250774'},
           {'name': 'Rory', 'ph': '5107250619'},
           {'name': 'Sreeta', 'ph': '5107250786'},
           {'name': 'Ziheng', 'ph': '5107250744'},
           {'name': 'Vij', 'ph': '5107250740'}]

# File path where the GitHub repository is located
filePath = '/Users/biogeme/Desktop/Vij/Academics/Current Research/'

# File path where you wish to store the ground truth
groundTruthPath = filePath + 'Travel-Diary/Data/Inferred Truth/' 

# File path where you wish to store the raw GPS data
rawDataPath = filePath + 'Travel-Diary/Data/Raw Data/' 

# Don't change anything below this
gpsTraces, data = [], []
for tester in testers:
    try:
        data.append({'tester': tester['name'],
                     'date': date,
                     'ph': tester['ph']})            
        rawDataFileName = tester['ph'] + '_' + tester['name'] + '_' + date + '.txt'
        gpsTraces = getNewGPSData(tester['name'], tester['ph'], date, gmtConversion, rawDataPath + rawDataFileName)
        #gpsTraces = getExistingGPSData(rawDataPath + rawDataFileName)
        daySchedule, event = [], {}
        minDuration, maxRadius, minSamplingRate, gpsAccuracyThreshold = 360000, 50, 300000, 200
        minSeparationDistance, minSeparationTime = 100, 360000
        maxWalkSpeed, maxWalkAcceleration, minSegmentDuration, minSegmentLength = 3.10, 1620, 90000, 200
        trips, activities, holes = inferTripActivity(gpsTraces, minDuration, maxRadius, minSeparationDistance, 
                minSeparationTime, minSamplingRate, gpsAccuracyThreshold)
        while trips or activities or holes:
            if ((trips and activities and holes and trips[0][0] < activities[0][0] and trips[0][0] < holes[0][0]) 
                    or (trips and not activities and holes and trips[0][0] < holes[0][0])
                    or (trips and activities and not holes and trips[0][0] < activities[0][0])
                    or (trips and not activities and not holes)):
                modeChain = inferModeChain(gpsTraces, trips[0], maxWalkSpeed, maxWalkAcceleration, 
                        minSegmentDuration, minSegmentLength, gpsAccuracyThreshold)
                for mode in modeChain:
                    event = {'Start Time': gpsTraces[mode[0]][9],
                             'End Time': gpsTraces[mode[1]][9]}
                    if mode[-1] == 0:
                        event['Type'] = 'Non-walk trip'
                    else:
                        event['Type'] = 'Walk trip'
                    daySchedule.append(event)
                    event = {}
                trips = trips[1:]
            elif ((activities and trips and holes and activities[0][0] < trips[0][0] and activities[0][0] < holes[0][0]) 
                    or (activities and not trips and holes and activities[0][0] < holes[0][0])
                    or (activities and trips and not holes and activities[0][0] < trips[0][0])
                    or (activities and not trips and not holes)):
                event = {'Start Time': gpsTraces[activities[0][0]][9],
                         'End Time': gpsTraces[activities[0][1]][9],
                         'Type': 'Activity'}
                activities = activities[1:]
                daySchedule.append(event)
                event = {}
            elif holes:
                event = {'Start Time': gpsTraces[holes[0][0]][9],
                         'End Time': gpsTraces[holes[0][1]][9],
                         'Type': 'Hole'}
                holes = holes[1:]
                daySchedule.append(event)
                event = {}
                
        #print daySchedule
        data[-1]['Day Schedule'] = daySchedule
    except:
        print "Unexpected error:", sys.exc_info()[0]
        pass
    
writeFile(data, groundTruthPath)