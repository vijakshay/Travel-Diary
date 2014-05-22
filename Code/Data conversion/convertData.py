from os import listdir
from os.path import isfile, join
import sys
import csv
import datetime
import pytz
import re
from pymongo import MongoClient


# Procedure that takes as input a tab-delimited txt file, and stores the data as a list, 
# where each element of the list is a list itself that corresponds to a row in the file,
# and each element of that list corresponds to an entry in that row. 

def parseCSV(filePath, data):
    with open(filePath, 'rU') as csvfile:
        for row in csv.reader(csvfile, delimiter = '\t'):
            data.append(row)
    return data


# Procedure that takes as input the directory path containing the tab-delimited text files
# that need converting, and the collection in the MongoDB database to which this data needs
# to be transferred.

def convertJSON(dirPath, gpsPoints):
    
    dataFiles = [ f for f in listdir(dirPath) if isfile(join(dirPath,f)) ]    
    for dataFile in dataFiles:
        print 'Processing ', dataFile
        try:            
            gpsTraces = []
            filePath = dirPath + dataFile
            phoneNum, userName, date = dataFile.split('_')
            month, day, year = int(date[:2]), int(date[2:4]), int(date[4:8])
            gmtConversion = datetime.datetime(year, month, day, 0, 0, 0, 0, pytz.timezone('America/Los_Angeles')).strftime('%z')    
            data = parseCSV(filePath, gpsTraces)
            for row in data:
                
                googleInVeh, googleBike, googleWalk, googleStill, googleUnknown, googleTilting = 0, 0, 0, 0, 0, 0
                if 'in_vehicle' in row[8]:
                    googleInVeh = int(re.findall('\d+', re.findall('in_vehicle\d+', row[8])[0])[0])
                if 'on_bicycle' in row[8]:
                    googleBike = int(re.findall('\d+', re.findall('on_bicycle\d+', row[8])[0])[0])
                if 'on_foot' in row[8]:
                    googleWalk = int(re.findall('\d+', re.findall('on_foot\d+', row[8])[0])[0])
                if 'still' in row[8]:
                    googleStill = int(re.findall('\d+', re.findall('still\d+', row[8])[0])[0])
                if 'unknown' in row[8]:
                    googleUnknown = int(re.findall('\d+', re.findall('unknown\d+', row[8])[0])[0])
                if 'tilting' in row[8]:
                    googleTilting = int(re.findall('\d+', re.findall('tilting\d+', row[8])[0])[0])
                                                
                record = {'phNum': int(phoneNum),
                          'userName': userName,
                          'epochTime': float(row[1]),
                          'movesTime': ((datetime.datetime.fromtimestamp(int(float(row[1])/1000))).strftime('%Y%m%dT%H%M%S') 
                                + gmtConversion),                          
                          'gpsReading': {'location': {'type': 'Point',
                                                      'coordinates': [float(row[2]), float(row[3])]},
                                         'gpsAccuracy': float(row[4])},
                          'batteryLevel': int(float(row[5])),
                          'accelerometerReading': {'vector': float(row[7])},
                          'googleInference': {'inVehicle': googleInVeh,
                                              'bike': googleBike,
                                              'walk': googleWalk,
                                              'still': googleStill,
                                              'unknown': googleUnknown,
                                              'tilting': googleTilting},
                          'groundTruth': {'label': row[11]}}
                          
                if row[11] == 'Trip' and len(row) > 12:
                    record['groundTruth']['mode'] = row[12]
                    if row[12] == 'Transit' and len(row) > 13:
                        record['groundTruth']['transitAgency'] = row[13]
                        if row[13] == 'Other' and len(row) > 14:
                            record['groundTruth']['transitAgencyName'] = row[14]
                    elif row[12] == 'Other' and len(row) > 13:
                        record['groundTruth']['modeName'] = row[13]
                elif row[11] == 'Activity' and len(row) > 12:
                    record['groundTruth']['purpose'] = row[12]
                    if row[12] == 'Other' and len(row) > 13:
                        record['groundTruth']['purposeName'] = row[13]
                        if len(row) > 14:
                            record['groundTruth']['exactLocation'] = row[14]
                    elif len(row) > 13:
                        record['groundTruth']['exactLocation'] = row[13]
                
                if len(list(gpsPoints.find({'userName':userName, 'epochTime': float(row[1])}))) == 0:
                    gpsPoints.insert(record)
                    #print record
                
        except:
            print "Unexpected error:", sys.exc_info()[0]
            pass
    

# Entry point to script

if __name__ == "__main__":

    # Base directory where you clone the repository, change as appropriate
    dirPath = '/Users/vij/Work/Current Research/'
    
    # Folder within the repository containing the data files
    dirPath += 'Travel-Diary/Data/Temp/'
    
    # Mongo database details
    client = MongoClient()
    travelDiary = client.travelDiary
    gpsPoints = travelDiary.gpsPoints
       
    # Call to function
    convertJSON(dirPath, gpsPoints)
