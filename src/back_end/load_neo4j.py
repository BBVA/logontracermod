#!/usr/bin/env python
# -*- coding: utf-8 -*-
import csv
from py2neo import Graph
import json
from datetime import datetime
from datetime import date, timedelta
import time
import pandas as pd
import collections
import numpy as np
import csv
from py2neo import Graph
import random
import json
from pykafka import KafkaClient
import pandas as pd
from py2neo import authenticate, Graph

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
ip_port = ""
usr = ""
pass = ""
authenticate(ip_port, usr, pass)
graph_connection = ""
graph = Graph(graph_connection)
i = 0
must_update = dict()
kafka_hosts = ""
client = KafkaClient(hosts=kafka_hosts)
zookeeper_hosts = ""
topic = client.topics['']
consumer = topic.get_balanced_consumer(
    auto_commit_enable = True,
    consumer_group="neo4j",
    zookeeper_connect=zookeeper_hosts
)

print("conectado a neo4j y a kafka")

first_time = 1
for message in consumer:
        if message is not None:
		try:

			event =  page["hits"]["hits"][0]["_source"]
			eventid = getField(event, "event_id")
			logintype =  getField(event, "logon_type")
			ipaddress =  getField(event, "ip_address")
			ipaddressraw =  getField(event, "ip_address")
			ts_raw = getField(event, "timestamp")
			username = getField(event, "target_user").upper()
			eventhost=getField(event, "event_host").upper()
			status = getField(event, "status_code")
			ts = getTime1("timestamp",event)			

        	        try:
	                        ipaddress = ipaddressraw.replace("::FFFF:","")
                	except:
                        	ipaddress = ipaddressraw
	                eventhost =  eventhost[:eventhost.find(".")]
	                ip_key = str(username) + "_" + str(ipaddress) + "_" + str(eventid) + "_" +  str(status) + "_" + str(logintype)
       	        	eventhost_key = str(username) + "_" + str(eventhost) + "_" + str(eventid) + "_" +  str(status) + "_" + str(logintype)
       	         	rights = ""
                	if "ADM_" in username or "ADMINISTRATOR" in username or "SYSTEM" in username or "ADMIN" in username:
                        	rights = "system"
                	else:
                        	rights = "user"

                        if first_time == 0:
                                try:
                                        date = graph.run("MATCH  (d:Date) RETURN d  ").data()
                                        init_date = date[0]["d"]
                                except:
                                        graph.run("CREATE (d:Date {date:'"+ str(ts)+"', start:'"+ str(ts)+"'})  ").dump()
                        graph.run("MERGE(u:Username {user:'"+ username+"'}) on create set u.rank = 0, u.last_hour_4625 = -1, u.last_hour_4624 = -1, u.last_hour_4672 = -1, u.last_hour_4688 = -1, u.detect = '' , u.sid = '" + sid + "' , u.rights = '"+rights+"'").dump()
                        graph.run("MERGE(ip:IPAddress {IP:'"+ ipaddress +"'}) on create set ip.rank = 0 ").dump()
                        graph.run("MERGE(ip:IPAddress {IP:'"+ d[eventhost] +"'}) on create set ip.rank = 0 ").dump()

                        try:
                                graph.run("match (d:Date) set d.end = '"+str(ts)+"'  ").dump()
                                eventhost_counter = str(hc[eventhost_key])
                                ip_counter = str(ipc[ip_key])
                                if logintype =="-":
                                        graph.run("MATCH (ip:IPAddress {eventhost:'"+ eventhost+"'}), (u:Username {user:'"+ username+"'}) with u, ip MERGE (ip)<-[e:Event { id: "+eventid+" , status: '"+ status+ "', logintype:'"+ logintype +"'}]-(u) ON CREATE SET e.id = "+  eventid + ", e.count= 1 , e.status = '"+ status+ "', e.logintype = '"+ logintype +"' ON MATCH SET e.count =  e.count +1 ").dump()

                                        graph.run("MATCH (ip:IPAddress {IP:'"+ ipaddress+"'}), (u:Username {user:'"+ username+"'}) with u, ip MERGE (u)<-[e:Event { id: "+eventid+" , status: '"+ status+ "', logintype:'"+ logintype +"'}]-(ip) ON CREATE SET e.id = "+  eventid + ", e.count=1 , e.status = '"+ status+ "', e.logintype = '"+ logintype +"' ON MATCH SET e.count =  e.count +1 ").dump()
                                else:
                                        graph.run("MATCH (ip:IPAddress {eventhost:'"+ eventhost+"'}), (u:Username {user:'"+ username+"'}) with u, ip MERGE (ip)<-[e:Event { id: "+eventid+" , status: '"+ status+ "', logintype:"+ logintype +"}]-(u) ON CREATE SET e.id = "+  eventid + ", e.count=1 , e.status = '"+ status+ "', e.logintype = "+ logintype +" ON MATCH SET e.count = e.count + 1").dump()
                                        graph.run("MATCH (ip:IPAddress {IP:'"+ ipaddress+"'}), (u:Username {user:'"+ username+"'}) with u, ip MERGE (u)<-[e:Event { id: "+eventid+" , status: '"+ status+ "', logintype:"+ logintype +"}]-(ip) ON CREATE SET e.id = "+  eventid + ", e.count=1 , e.status = '"+ status+ "', e.logintype = "+ logintype +" ON MATCH SET e.count = e.count +1  ").dump()

                        except:
                                print(eventid)
                                print(logintype)
                                print(status)
                                print(event)

                        first_time +=1

		except:
			print("error with page: " + str(page))


