from os import listdir
from os.path import isfile, join
import sys
import csv
import datetime
import pytz
import time
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
                
                record = {'_id': Unique identifier used by MongoDB by default (format: ObjectId),
                          'phNum': User phone number (format: int),
                          'userName': User name (format: str),
                          'epochTime': Epoch time in milliseconds (format: float),
                          'movesTime': ISO 8601 local date and time with time zone information (format: str),
                          'gpsReading': {'location': {'type': 'Point' (format: str),
                                                      'coordinates': [Latitude (format: float), Longitude (format: float)]},
                                         'gpsAccuracy': GPS accuracy in meters (format: float)},
                          'batteryLevel': Battery level (format: int),
                          'accelerometerReading': {'xAxis': Accelerometer reading along X-axis (format: float),
                                                   'yAxis': Accelerometer reading along Y-axis (format: float),
                                                   'zAxis': Accelerometer reading along Z-axis (format: float),
                                                   'vector': Accelerometer reading vector value (format: float)},
                          'googleInference': {'inVehicle': Probability in-vehicle (format: int),
                                              'bike': Probability on bike (format: int),
                                              'walk': Probability walking (format: int),
                                              'still': Probability still (format: int),
                                              'unknown': Probability unknown (format: int),
                                              'tilting': Probability tilting (format: int)},
                          'screenOn': Binary variable equal to one if screen is on (format: int),
                          'wiFiNetwork': Name of wifi network (format: str),
                          'receivedTime': Epoch time in milliseconds when record data received by server (format: float),
                          'groundTruth': {'label': Label denoting 'Trip', 'Activity' or 'Hole' in data (format: str),
                                          'mode': Travel mode denoting 'Walk', 'Bike', 'Car', 'Transit', if 'label' is 'Trip' (format: str),
                                          'transitAgency': Transit agency name denoting 'AC_Transit', 'BART', 'Bear_Transit', 'MUNI', if mode is transit (format:str),
                                          'purpose': Activity purpose(s), if 'label' is 'Activity' (format: str),
                                          'exactLocation': Specific name of place, e.g. McLaughlin Hall (format: str)}}
                
                timeReceived = time.strptime(row[17][:row[17].find('PDT')-1], '%a %b %d %H:%M:%S')
                epochReceived = float(datetime.datetime(2014, timeReceived.tm_mon, timeReceived.tm_mday,
                        timeReceived.tm_hour, timeReceived.tm_min, timeReceived.tm_sec).strftime('%s')) * 1000
                record['receivedTime'] = epochReceived

                
                if row[18] == 'Trip' and len(row) > 19:
                    record['groundTruth']['mode'] = row[19]
                    if row[19] == 'Transit' and len(row) > 20:
                        record['groundTruth']['transitAgency'] = row[20]
                        if row[20] == 'Other' and len(row) > 21:
                            record['groundTruth']['transitAgencyName'] = row[21]
                    elif row[19] == 'Other' and len(row) > 20:
                        record['groundTruth']['modeName'] = row[20]
                elif row[18] == 'Activity' and len(row) > 19:
                    record['groundTruth']['purpose'] = row[19]
                    if row[19] == 'Other' and len(row) > 20:
                        record['groundTruth']['purposeName'] = row[20]
                        if len(row) > 21:
                            record['groundTruth']['exactLocation'] = row[21]
                    elif len(row) > 20:
                        record['groundTruth']['exactLocation'] = row[20]
                
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
