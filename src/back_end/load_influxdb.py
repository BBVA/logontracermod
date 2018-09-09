#!/usr/bin/env python
# -*- coding: utf-8 -*-
import collections
import numpy as np
import pandas as pd 
import csv
import random
import json
from datetime import datetime
from datetime import date, timedelta
import time
from influxdb import InfluxDBClient
from pykafka import KafkaClient
import pandas as pd

def getField(field, event):
	try:
		result = event[field]
	except:
		result = "-"
	return result[0].encode("utf-8")

def getTime(field, event):
        try:
                r = event[field][0]
                ind = r.find(".")
                result1 = str(r[:ind])
                result2 = datetime.strptime(result1, '%Y-%m-%dT%H:%M:%S')
		result = result2.day
        except:
                result = "-"
        return result
i = 0
must_update = dict()
kafka_hosts = ""
client = KafkaClient(hosts=kafka_hosts)
 topic = client.topics['']
consumer = topic.get_balanced_consumer(
    auto_commit_enable = True,
    consumer_group="influxdb",
    zookeeper_connect=" "
)
ip = ""
usr = ""
pass = ""
db = ""
influx_client = InfluxDBClient(ip, port, usr, pass, db)
for message in consumer:
        if message is not None:
            event = json.loads(message.value)
		    eventid = getField("event_id", event)
    		eventhost=getField("eventhost",event).upper()
    		ipaddress=getField("ip_address",event).upper()
    		username = getField("target_user", event).upper()
    		sid = getField("target_usersid", event)
    		logintype = getField("logon_type", event)
    		status = getField("status_code", event).upper()
    		ts = getTime("timestamp",event)
    		ts_raw = getField("timestamp", event)
    		json_body = [
    	    			{
    				        "measurement": "events_count",
    			        	"tags": {
    				       	   "username": username,
      			       		   "eventid":eventid,
    	  			       	   "logintype":logintype,
      				       	   "ipaddress":ipaddress,
      				       	   "status":status,
      				       	   "eventhost":eventhost
    				        },
    				        "time": ts_raw,
    				        "fields": {
    				            "value": 1
    				        }
    				    }
    				]
    	

		    influx_client.write_points(json_body)
	
