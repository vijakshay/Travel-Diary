from pymongo import MongoClient
from dateutil import parser
import re
import glob

client = MongoClient()
db = client.travel_diary_db
obs = db.observations

for l in glob.glob('../../Data/Google Play API/*.csv'):
  print l
  with open(l,'rb') as f:
    for row in f:
      try:
        info = row.strip().split('\t')
        inferred = re.split(r'(\d+)',info[8])[:-1]
        obs.insert({'id':info[0],
                'epoc':int(float(info[1])),
                'location': {'type':'Point','coordinates':[float(info[3]),float(info[2])]}, 
                'gps_accuracy': float(info[4]),
                'battery_status': float(info[5]),
                'sampling_rate': int(info[6]),
                'accelerometer': float(info[7]),
                'Activity_inferred': dict([(inferred[i],int(inferred[i+1])) for i in xrange(0,len(inferred),2)]),
                'date-time': parser.parse(info[9]),
                'date': parser.parse(info[9]).date().isoformat(),
                'trip_type': info[10],
                'transit_type': info[11] if info[10].lower() == 'trip' else '',
                'transit_agency': info[12] if info[10].lower() == 'trip' and info[11].lower() == 'transit' else '',
                'custom_transit_agency': info[13] if info[10] == 'trip' and info[11].lower() == 'transit' and info[12].lower() == 'other' else '',
                
                'activity_type': info[11] if info[10].lower() == 'activity' else '',
                'activity_purpose': info[12] if info[10].lower() == 'activity' and info[11].lower() == 'other' else '',
                'activity_location': info[13] if info[10].lower() == 'activity' and info[11].lower() == 'other' else info[12] if info[10].lower() == 'activity' else '',
                })
      except Exception as e:
        print "Unexpected format: %s"%e
