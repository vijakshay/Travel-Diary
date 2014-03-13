import csv


# Procedure that takes as input a string deonting the date, difference between local time zone and UTC time, 
# and the GPS file path name. Output is a list of lists containing GPS data for that day.

def getGPSData(gpsFilePath):

    gpsData = []
    with open(gpsFilePath, 'rb') as csvfile:
        for row in csv.reader(csvfile, delimiter = '\t'):
            tList = []
            for element in row:
                if element != '':
                    tList.append(element)                
            gpsData.append(tList)
    return gpsData


# Procedure that takes as input strings deonting the tester name, test phone number, date, difference between
# local time zone and UTC time, and the file path name. Output is a list of lists containing ground truth data
# for that tester, phone and day.

def getGroundData(groundFilePath):

    groundData = []
    with open(groundFilePath, 'rU') as csvfile:
        for row in csv.reader(csvfile, dialect=csv.excel_tab, delimiter = ','):
            if row[0] != 'Start Time':
                tList = []
                for element in row:
                    if element != '':
                        tList.append(element)                
                groundData.append(tList)
    return groundData

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

    i, lastEvent = 0, groundData[-1][3:]
    while groundData:
        while gpsData[i][9] != groundData[0][1]:
            for element in groundData[0][3:]:
                gpsData[i].append(element)
            i += 1
        groundData = groundData[1:]
    for element in lastEvent:
        gpsData[i].append(element)
    return gpsData


# A script that combines the GPS data with the ground truth in a tab-delimited text file that can
# subsequently be used to train inference algorithms. The GPS data file must be saved manually
# as a tab-delimited text file on the local hard drive. The ODK file containing ground truth must
# be exported manually as a csv and saved to the local hard drive as well.

# Personal details, change as appropriate

testers = [{'name': 'Andrew', 'ph': '5107259365'}, 
           {'name': 'Caroline', 'ph': '5107250774'},
           {'name': 'Rory', 'ph': '5107250619'},
           {'name': 'Sreeta', 'ph': '5107250786'},
           {'name': 'Vij', 'ph': '5107250740'},
           {'name': 'Ziheng', 'ph': '5107250744'}]

# Details of data to be merged

testerName = 'Vij'        # Should be the same as that listed in the ODK form
date = '03122014'            # MMDDYYYY format of day for which you wish to extract data

# Base directory where you clone the repository, change as appropriate
filePath = '/Users/biogeme/Desktop/Vij/Academics/Current Research/'

# Directory where you saved the file with GPS traces, change as appropriate
gpsFilePath = filePath + 'Travel-Diary/Data/Raw Data/' 

# Directory where you've saved the corrected ground truth, change as appropriate
groundFilePath = filePath + 'Travel-Diary/Data/Corrected Truth/' 

# DON'T CHANGE ANYTHING BELOW THIS!

for tester in testers:
    if tester['name'] == testerName:
        fileName = tester['ph'] + '_' + testerName + '_' + date

gpsFile = gpsFilePath + fileName + '.txt'
groundFile = groundFilePath + fileName + '.csv'

# Directory where the final data file will be saved, no need to change this
mergedFile = filePath + 'Travel-Diary/Data/Google Play API/' + fileName + '.txt'

gpsData = getGPSData(gpsFile)
groundData = getGroundData(groundFile)
data = mergeData(gpsData, groundData)

with open(mergedFile, 'wb') as csvfile:
    fileWriter = csv.writer(csvfile, delimiter = '\t')
    for row in data:
        fileWriter.writerow(row)
