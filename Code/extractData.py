import urllib2
import csv
import os

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


# Returns the epoch Time in milliseconds for a given day and time in UTC. Input is a string in
# the format 'Thu Jan 23 18:18:00 UTC 2014'

def epochGroundTime(dateTime):

    year1 = 1970
    month1 = 1
    day1 = 1

    months = {'Jan': 1,
              'Feb': 2,
              'Mar': 3,
              'Apr': 4,
              'May': 5,
              'Jun': 6,
              'Jul': 7,
              'Aug': 8,
              'Sep': 9,
              'Oct': 10,
              'Nov': 11,
              'Dec': 12}

    dateTime = dateTime.split()
    year2 = int(dateTime[-1])
    month2 = int(months[dateTime[1]])
    day2 = int(dateTime[2])

    days = 0
    while dateIsAfter(year2, month2, day2, year1, month1, day1):
        days += 1
        (year1, month1, day1) = nextDay(year1, month1, day1)

    time = dateTime[3].split(':')
    hours = int(time[0])
    minutes = int(time[1])
    seconds = int(time[2])

    epochTime = ((((((days * 24) + hours) * 60) + minutes) * 60) + seconds) * 1000
    return epochTime


# Procedure that takes as input strings deonting the tester name, test phone number, date, difference between
# local time zone and UTC time, and the GPS file path name. Output is a list of lists containing GPS data
# for that tester, phone and day.

def getGPSData(testerName, phoneNum, date, gmtConversion, gpsFilePath):

    startTime, endTime = epochTime(date, gmtConversion)
    gpsData = []
    with open(gpsFilePath, 'rU') as csvfile:
        for row in csv.reader(csvfile, delimiter = '\t'):
            try:
                if int(row[1]) >= startTime and int(row[1]) <= endTime:
                    gpsData.append(row[:-1])
            except:
                pass
    gpsData = sorted(gpsData, key = lambda x: int(x[1]))
    return gpsData


# Procedure that takes as input strings deonting the tester name, test phone number, date, difference between
# local time zone and UTC time, and the file path name. Output is a list of lists containing ground truth data
# for that tester, phone and day.

def getGroundData(testerName, phoneNum, date, gmtConversion, groundFilePath):

    groundData = []
    with open(groundFilePath, 'rU') as csvfile:
        for row in csv.reader(csvfile, delimiter = ','):
            if row[1] == phoneNum and row[4] == testerName:
                if row[-2] == 'Yes':
                    time = epochGroundTime(row[0])
                else:
                    time = epochGroundTime(row[-1])
                row.append(time)
                groundData.append(row[:])

    startTime, endTime = epochTime(date, gmtConversion)
    groundData = sorted(groundData, key = lambda x: x[-1])
    startIndex, endIndex = 0, len(groundData)-1
    i = 0
    while i < len(groundData)-1:
        if groundData[i][-1] <= startTime and groundData[i+1][-1] > startTime:
            startIndex = i
        if groundData[i][-1] <= endTime and groundData[i+1][-1] > endTime:
            endIndex = i
        i += 1

    return groundData[startIndex:endIndex+1]

# Procedure that takes as input two lists, one containing GPS data and one containing ground truth, and combines them
# into a single list

def mergeRecord(gpsData, groundData):

    gpsData.append(groundData[5])
    if groundData[5] == 'Trip':
        gpsData.append(groundData[6])
        if groundData[6] == 'Transit':
            gpsData.append(groundData[7])
            if groundData[7] == 'Other':
                gpsData.append(groundData[8])
        elif groundData[6] == 'Other':
            gpsData.append(groundData[9])
    elif groundData[5] == 'Activity':
        gpsData.append(groundData[10])
        if 'Other' in groundData[10]:
            gpsData.append(groundData[11])
        gpsData.append(groundData[12])

    return gpsData


# Procedure that takes as input the list of lists containing GPS data and the ground truth, and combines them
# into a single list of lists.

def mergeData(gpsData, groundData):

    i, j = 0, 0
    while i < len(groundData) - 1 and j < len(gpsData):
        #print i, j
        if groundData[i][-1] > int(gpsData[j][1]):
            j += 1
        elif groundData[i][-1] <= int(gpsData[j][1]) and groundData[i+1][-1] > int(gpsData[j][1]):
            gpsData[j] = mergeRecord(gpsData[j], groundData[i])
            j += 1
        else:
            i += 1
    while j < len(gpsData):
        gpsData[j] = mergeRecord(gpsData[j], groundData[i])
        j += 1

    return gpsData


# A script that combines the GPS data with the ground truth in a tab-delimited text file that can
# subsequently be used to train inference algorithms. The GPS data file must be saved manually
# as a tab-delimited text file on the local hard drive. The ODK file containing ground truth must
# be exported manually as a csv and saved to the local hard drive as well.

# Personal details, change as appropriate
testerName = 'Andrew'       # Should be the same as that listed in the ODK form
phoneNum = '5107259365'  # 10-digit number with no brackets, hyphens or spaces
date = '02072014'        # MMDDYYYY format of day for which you wish to extract data
gmtConversion = -8       # Difference in hours between local time and UTC time, remember to change for daylight savings

# Base directory where you clone the repository, change as appropriate
filePath = '/Users/daddy30000/'

# Directory where you saved the file with GPS traces, change as appropriate
gpsFilePath = '/Users/daddy30000/Dropbox/Research/13_14_Project_Files/13_Tracking_Apps/logs/gaeandroid.txt'

# Directory where you've saved the ODK file with just the ground truth, change as appropriate
groundFilePath = '/Users/daddy30000/Dropbox/Research/13_14_Project_Files/13_Tracking_Apps/logs/14_02_07_10_odk_edit.csv'


# DON'T CHANGE ANYTHING BELOW THIS!

# Directory where the final data file will be saved, no need to change this
dataFilePath = filePath + 'Travel-Diary/Data/Google Play API/' + phoneNum + '_' + testerName + '_' + date + '.txt'

gpsData = getGPSData(testerName, phoneNum, date, gmtConversion, gpsFilePath)
groundData = getGroundData(testerName, phoneNum, date, gmtConversion, groundFilePath)
data = mergeData(gpsData, groundData)

with open(dataFilePath, 'wb') as csvfile:
    fileWriter = csv.writer(csvfile, delimiter = '\t')
    for row in data:
        fileWriter.writerow(row)
