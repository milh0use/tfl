import requests
from urllib.parse import urlencode
import json
import time
import config
from pymongo import MongoClient
#import pymongo

client = MongoClient()
db = client['bus']
coll_departures = db.departures

class TfLAPI:
    def __init__(self):
        self.app_id = "Test"
        self.app_key = config.app_key
        self.features = []
        self.request_count = 0
        self.api_token = {"app_id": self.app_id, "app_key": self.app_key}

    def get_query_strings(self, params):
        if params is None:
            params = {}
        if self.api_token is not None:
            params.update(self.api_token)
        return urlencode(params)

endpoint = "http://api.tfl.gov.uk/Line/"
# stop_ids_list = [
#     {
#         "name": "Julien Road",
#         "code": "490008591N",
#     }
# ]

stop_ids_list = [
    {
        "name": "Julien Road",
        "code": "490008591N",
    },
    {
        "name": "Northfields Station",
        "code": "490000159B",
    },
    {
        "name": "Graham Avenue",
        "code": "490007333N",
    },
    {
        "name": "Hessel Road",
        "code": "490008110N",
    },
    {
        "name": "Sherwood Close",
        "code": "490015589N",
    },
    {
        "name": "Dean Gardens / Mattock Lane",
        "code": "490013447G",
    }
]

def log_departure(bus_id,stop_id,time):
    # check if a departure has been logged at this stop for this bus in the last 30 minutes
    # otherwise log it now
    cur = coll_departures.find({'bus_id': bus_id,'stop_id': stop_id}).sort('time',-1)
    for doc in cur:
        # check if the time of any returned records = time - 30mins
        if doc['time'] > time-(30*60):
            print(bus_id + " has already been logged departing " + stop_id)
            break
    else:
        result = coll_departures.insert_one({'bus_id': bus_id, 'stop_id': stop_id, 'time': time})
        print(result)

buses = dict()
bus_stop = dict()
api = TfLAPI()
while True:
    for stop in stop_ids_list:
        stop_code = stop["code"]
        stop_name = stop["name"]
        current_time = int(time.time())
        if stop_code in bus_stop:
            #print("Bus stop last checked at "+str(bus_stop[stop_code]["last_check"]))
            #print("current_time = "+str(current_time))
            while bus_stop[stop_code]["last_check"] > current_time-30:
                time.sleep(1)
                current_time = int(time.time())
        #print("Making API request")
        print(stop_name+":")
        url = endpoint +"e2,e3,n11" +"/Arrivals/" + stop_code
        #print(url)
        pre_timestamp = time.time()
        r = requests.get(url,params=api.get_query_strings(None))
        api_execution_time = time.time() - pre_timestamp
        print("api execution time="+str(api_execution_time)+"s")
        if r.status_code == 200:
            # work out what to do here?
            # create a dictionary of individual buses and their departure times from each stop?
            arrivals = json.loads(r.text)
            buses_to_delete = list()
            if stop_code not in bus_stop:
                bus_stop[stop_code] = {"arrivals": dict(), "last_check": current_time}
            else:
                bus_stop[stop_code]["last_check"] = current_time
            for arrival in arrivals:
                bus_id = arrival['vehicleId']
                if arrival['timeToStation'] < 45:
                    print(bus_id+"\t"+arrival['lineName']+"\t"+str(arrival['timeToStation']))
                bus_stop[stop_code]["arrivals"][bus_id] = current_time
            for bus_id,timestamp in bus_stop[stop_code]["arrivals"].items():
                if timestamp != current_time:
                    buses[bus_id] = {stop_code: current_time}
                    departure_time = time.strftime("%H:%M",time.gmtime(current_time))
                    print("Bus "+bus_id+" left "+stop_name+" at "+departure_time)
                    log_departure(bus_id,stop_code,current_time)
                    buses_to_delete.append(bus_id)
            for bus_to_delete in buses_to_delete:
                del bus_stop[stop_code]["arrivals"][bus_to_delete]
        else:
            print("FAILED!")
    print("=====")


