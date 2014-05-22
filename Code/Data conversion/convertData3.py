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
        print 'Processing ' + dataFile
        try:            
            gpsTraces = []
            filePath = dirPath + dataFile
            phoneNum, userName, date = dataFile.split('_')
            month, day, year = int(date[:2]), int(date[2:4]), int(date[4:8])
            gmtConversion = datetime.datetime(year, month, day, 0, 0, 0, 0, pytz.timezone('America/Los_Angeles')).strftime('%z')    
            data = parseCSV(filePath, gpsTraces)
            for row in data:
                record = {'phNum': int(phoneNum),
                          'userName': userName,
                          'epochTime': float(row[1]),
                          'movesTime': ((datetime.datetime.fromtimestamp(int(float(row[1])/1000))).strftime('%Y%m%dT%H%M%S') 
                                + gmtConversion),                          
                          'gpsReading': {'location': {'type': 'Point',
                                                      'coordinates': [float(row[2]), float(row[3])]},
                                         'gpsAccuracy': float(row[4])},
                          'batteryLevel': int(float(row[5])),
                          'accelerometerReading': {'xAxis': float(row[6]),
                                                   'yAxis': float(row[7]),
                                                   'zAxis': float(row[8])},
                          'googleInference': {'inVehicle': int(float(row[9])),
                                              'bike': int(float(row[10])),
                                              'walk': int(float(row[11])),
                                              'still': int(float(row[12])),
                                              'unknown': int(float(row[13])),
                                              'tilting': int(float(row[14]))},
                          'screenOn': int(float(row[15])),
                          'groundTruth': {'label': row[17]}}

                if row[16] != '':
                    record['wiFiNetwork'] = row[16]
                
                if row[17] == 'Trip' and len(row) > 18:
                    record['groundTruth']['mode'] = row[18]
                    if row[18] == 'Transit' and len(row) > 19:
                        record['groundTruth']['transitAgency'] = row[19]
                        if row[19] == 'Other' and len(row) > 20:
                            record['groundTruth']['transitAgencyName'] = row[20]
                    elif row[18] == 'Other' and len(row) > 19:
                        record['groundTruth']['modeName'] = row[19]
                elif row[17] == 'Activity' and len(row) > 18:
                    record['groundTruth']['purpose'] = row[18]
                    if row[18] == 'Other' and len(row) > 19:
                        record['groundTruth']['purposeName'] = row[19]
                        if len(row) > 20:
                            record['groundTruth']['exactLocation'] = row[20]
                    elif len(row) > 19:
                        record['groundTruth']['exactLocation'] = row[19]
                
                if gpsPoints.find({'userName':userName, 'epochTime': float(row[1])}).count() == 0:
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
