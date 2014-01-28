import csv
import math


# Procedure that takes as input a tab-delimited txt file, and stores the NUMERICAL data as a list, 
# where each element of the list is a list itself that corresponds to a row in the file,
# and each element of that list corresponds to an entry in that row. Any non-numerical elements
# in any row in the txt file are skipped over.

def parseCSV(filePath, data):
    with open(filePath, 'rU') as csvfile:
        for row in csv.reader(csvfile, delimiter = '\t'):
            tList = []
            for element in row:
                try:
                    tList.append(float(element))    
                except:
                    pass
            data.append(tList)


# Function that uses the haversine formula to calculate the 'great-circle' distance in meters
# between two points whose latitutde and longitude are known

def calDistance(point1, point2):

    earthRadius = 6371000 
    dLat = math.radians(point1[0]-point2[0]);
    dLon = math.radians(point1[1]-point2[1]);  
    lat1 = math.radians(point1[0]);
    lat2 = math.radians(point2[0]);
    
    a = (math.sin(dLat/2) ** 2) + ((math.sin(dLon/2) ** 2) * math.cos(lat1) * math.cos(lat2));
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a));
    d = earthRadius * c ;
    
    return d


# Function that takes as input the GPS location of a point and a list of points, where each element of the 
# list is a tuple containing the latitutde and longitude for that point. The function outputs the maximum 
# distance, in meters, from that point to any point in the list of points

def calDistanceToPoint(point, points):
    maxDistance = 0
    for i in range(0, len(points)):
        dist = calDistance(point, points[i])
        if dist > maxDistance:
            maxDistance = dist
    return maxDistance

#Functions that calculate the four features of the GPS point :length and time between the next point,
#speed and acceleration

#meters
def lengthPoint(gpsTraces,j):
   return calDistance(gpsTraces[j][2:4], gpsTraces[j+1][2:4])

#milliseconds   
def timePoint(gpsTraces,j):
   return gpsTraces[j+1][1] - gpsTraces[j][1]

#meter/millisecond   
def speedPoint(gpsTraces,j):
  return float(lengthPoint(gpsTraces,j))/timePoint(gpsTraces,j)

#meter^2/millisecond  
def accelerationPoint(gpsTraces,j):
  return float(abs(speedPoint(gpsTraces, j+1)-speedPoint(gpsTraces, j)))/timePoint(gpsTraces, j)
  
  
#maxVelocity, maxAcceleration, meanVelocity, meanAcceleration, expVelocity and expAcceleration 
# are features of a segment, which will be use to infer the mode
	
def maxVelocity (gpsTraces, start, end):
    maxVelocity=0
    for i in range(start, end-1):
       vel=speedPoint(gpsTraces,i)
       if vel>maxVelocity:
          maxVelocity=vel;
    return maxVelocity

def maxAcceleration (gpsTraces, start, end):
    maxAcceleration=0
    for i in range(start, end-1):
       vel=accelerationPoint(gpsTraces,i)
       if vel>maxAcceleration:
          maxAcceleration=vel;
    return maxAcceleration

def meanVelocity (gpsTraces, start, end):
    if gpsTraces[end][1]-gpsTraces[start][1]>0:
       m=float(calDistance(gpsTraces[start][2:4], gpsTraces[end][2:4]))/(gpsTraces[end][1]-gpsTraces[start][1]);
    else:
       m=0;
    return m
    
def meanAcceleration (gpsTraces, start, end):
    if gpsTraces[end][1]-gpsTraces[start][1]>0:
        m=float(calDistance(gpsTraces[start][2:4], gpsTraces[end][2:4]))/((gpsTraces[end][1]-gpsTraces[start][1])*(gpsTraces[end][1]-gpsTraces[start][1]))
    else:
        m=0
    return m

def expVelocity (gpsTraces, start, end):
    m=0
    for i in range(start, end-1):
        m=m+speedPoint(gpsTraces,i)
    return float(m)/max((end-start-1),1)

def expAcceleration (gpsTraces, start, end):
    m=0
    for i in range(start, end-1):
        m=m+accelerationPoint(gpsTraces,i)
    return float(m)/max((end-start-1),1)

    

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

def inferTripActivity(gpsTraces, trips, activities, minDuration, maxRadius, minInterval):
    
    i = 0
    while i < len(gpsTraces) - 1:
        
        # Create a collection of successive points that lie within a circle of radius maxRadius meters
        j = i + 1
        points = [gpsTraces[i][2:4]]  
        while j < len(gpsTraces) and calDistanceToPoint(gpsTraces[j][2:4], points) < maxRadius:
            points.append(gpsTraces[j][2:4])
            j += 1
        
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
        if activities[-1][-1] < len(gpsTraces)-1:
            trips.append([activities[-1][-1], len(gpsTraces)-1])
    else:
        trips.append([0, len(gpsTraces)-1])
   
# tripFirstSegmentation takes as input a list containing GPS data, a specific trip covered by the data 
# as indices when the trip begins and when the trip ends, maxWalkSpeed and maxWalkAcceleration
# are the maximum values of speed and acceleration to consider a point as a "Walk Point". minConsecutivePoints
# is the minimum number of consecutive points to consider a segment as a walk segment or a non walk segment;
# otherwise, the segment is merged into its backward segment. minLength is the minimum length of 
# a segment to consider it as a certain segment. segment is an empty list  

def tripFirstSegmentation(gpsTraces, trip, maxWalkSpeed, maxWalkAcceleration, minConsecutivePoints, segment, tripDescription):
   beginTrip= trip[0];
   endTrip= trip[1];
   lenTrip= endTrip-beginTrip + 1;
   for i in range(0, lenTrip-1):
	  if speedPoint(gpsTraces,beginTrip+i)<maxWalkSpeed and accelerationPoint(gpsTraces,beginTrip+i)<maxWalkAcceleration :
		 tripDescription.append([beginTrip+i,1]); #walk point
	  else:
		 tripDescription.append([beginTrip+i,0]);
   i=1;
   beginSegment=0;
   while i<lenTrip-minConsecutivePoints+1:
	if tripDescription[i][1]!=tripDescription[i-1][1]:
		newsegment=1;
		for k in range (1, minConsecutivePoints):
			if i+k<lenTrip-1 and tripDescription[i][1]<>tripDescription[i+k][1]:
			   newsegment=0;
		if tripDescription[i][1]<>tripDescription[beginSegment][1] and newsegment==1:
			segment.append([beginTrip+beginSegment,beginTrip+i-1,tripDescription[beginSegment][1], calDistance(gpsTraces[beginSegment+beginTrip][2:4], gpsTraces[i-1+beginTrip][2:4]), maxVelocity(gpsTraces,beginSegment+beginTrip,i-1+beginTrip), maxAcceleration(gpsTraces,beginSegment+beginTrip,i-1+beginTrip), meanVelocity(gpsTraces,beginSegment+beginTrip,i+beginTrip-1), meanAcceleration(gpsTraces,beginSegment+beginTrip,i+beginTrip-1), expVelocity(gpsTraces,beginSegment+beginTrip,i+beginTrip-1), expAcceleration(gpsTraces,beginSegment+beginTrip,i+beginTrip-1)])
			beginSegment=i;
	i=i+1;
   if i>lenTrip-minConsecutivePoints:
	    segment.append([beginTrip+beginSegment,endTrip,tripDescription[beginSegment][1], calDistance(gpsTraces[beginSegment+beginTrip][2:4], gpsTraces[endTrip][2:4]), maxVelocity(gpsTraces,beginSegment+beginTrip, endTrip), maxAcceleration(gpsTraces,beginSegment+beginTrip,endTrip), meanVelocity(gpsTraces,beginSegment+beginTrip,endTrip),meanAcceleration(gpsTraces,beginSegment+beginTrip,endTrip),  expVelocity(gpsTraces,beginSegment+beginTrip,endTrip), expAcceleration(gpsTraces,beginSegment+beginTrip, endTrip)])
 
 
 
def firstSegmentation(gpsTraces, maxWalkSpeed, maxWalkAcceleration, minConsecutivePoints, segmentedTrip, minDuration, maxRadius, minInterval):  
    t, a = [], []
    inferTripActivity(gpsTraces, t, a, minDuration, maxRadius, minInterval)
    for i in range(0, len(t)):
        trip=t[i];
        seg, tDescription=[], []
        tripFirstSegmentation(gpsTraces, trip, maxWalkSpeed, maxWalkAcceleration, minConsecutivePoints, seg, tDescription)
        segmentedTrip.append(seg)
    



# The input file is a csv containing the GPS data and ground truth. The file name should follow the generic
# format: '<test phone number>_<tester alias>_<date data recorded>.csv', where test phone number is a 
# 9-digit number with no brackets and hyphens, and date data recorded is in MMDDYY format.
# 
# The file should contain eleven columns. The first nine columns denote the phone number of the test phone 
# (a 9-digit number with no brackets and hyphens), timestamp (in epoch time, recorded in milliseconds), latitude, 
# longitude, GPS accuracy (in feet), battry status (in percentage), sampling rate (in seconds), accelermoeter reading, 
# and the activity as inferred by the Google API, respectively. The values for each of these fields will be generated 
# by the tracking app installed on the test phone in the appropriate units, and you shouldn't have to change anything.
#
# The tenth and eleventh columns will have to be filled manually at the end of each day, and will reflect the 
# ground truth that will be used to train our inference algorithms.
# 
# The tenth column can take on two string values: (1) Trip, if the individual at the time was making a trip; 
# or (2) Activity, if the individual at the time was engaging in an activity.
#
# The eleventh column is a string as well. If the person was making a trip, then it denotes the mode, which can
# take the following values: Walk, Bike, Drive, Transit (Transit Agency). The variable Transit Agency can,
# for now, take the following values: AC Transit, MUNI, BART, Emery Go-Round, Dumbarton Express, Caltrain.
# As and when you encounter an agency not included in the list, be sure to add it to the protocol.
#
# If the person was engaging in an activity, then it denotes the location and/or purpose. For now, we're leaving
# it to the individual's discretion to fill this field however they deem appropriate. However, at some stage we'll 
# want to come up with a list of clearly defined activity purposes, if we wish to infer the same (which we do!).
#
# Finally, the rows in the file should be ordered in terms of increasing time. This will have to be done manually.

# Base directory where you clone the repository, change as appropriate
filePath = '/Users/biogeme/Desktop/Vij/Academics/Post-Doc/' 

# Shouldn't have to change anything below this for the code to run
filePath += 'Travel-Diary/Data/Google Play API/5107250619_Vij_010314.txt'
gpsTraces = []
parseCSV(filePath, gpsTraces)

#trips, activities, segment, tripDescription = [], [], [], []
segmentedTrip=[]
minDuration, maxRadius, minInterval = 180000, 50, 60000
#inferTripActivity(gpsTraces, trips, activities, minDuration, maxRadius, minInterval)
#trip=trips[1];
maxWalkSpeed, maxWalkAcceleration, minConsecutivePoints = 0.0025, 0.0000002, 3
#tripFirstSegmentation(gpsTraces, trip, maxWalkSpeed, maxWalkAcceleration, minConsecutivePoints, segment, tripDescription)
#print trips, activities
#print tripDescription, segment
firstSegmentation(gpsTraces, maxWalkSpeed, maxWalkAcceleration, minConsecutivePoints, segmentedTrip, minDuration, maxRadius, minInterval)
print segmentedTrip
