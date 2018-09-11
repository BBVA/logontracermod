#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# LICENSE
# Please refer to the LICENSE.txt in the https://github.com/JPCERTCC/aa-tools/
#

import os
import sys
import argparse
import itertools
import datetime
import subprocess
import requests
from influxdb import InfluxDBClient
from flask import jsonify



try:
    from py2neo import Graph
    has_py2neo = True
except ImportError:
    has_py2neo = False

try:
    import numpy as np
    has_numpy = True
except ImportError:
    has_numpy = False

try:
    from flask import Flask, render_template, request
    has_flask = True
except ImportError:
    has_flask = False

# neo4j password
NEO4J_PASSWORD = os.environ['neo4j_password']
# neo4j user name
NEO4J_USER = os.environ['neo4j_user']
# neo4j server
NEO4J_SERVER = os.environ['neo4j_server']
print(NEO4J_SERVER)
# neo4j listen port
NEO4J_PORT = os.environ['neo4j_port']
print(NEO4J_PORT)
# Web application port
WEB_PORT = 8080

# Check Event Id
EVENT_ID = [4624, 4625, 4768, 4769, 4776]

# EVTX Header
EVTX_HEADER = b"\x45\x6C\x66\x46\x69\x6C\x65\x00"

# Flask instance
if not has_flask:
    sys.exit("[!] Flask must be installed for this script.")
else:
    app = Flask(__name__)
    app.debug = True
parser = argparse.ArgumentParser(description="Visualizing and analyzing active directory Windows logon event logs.")
parser.add_argument("-r", "--run", action="store_true", default=False,
                    help="Start web application.")
parser.add_argument("-o", "--port", dest="port", action="store", type=int, metavar="PORT",
                    help="Port number to be started web application. (default: 8080).")
parser.add_argument("-s", "--server", dest="server", action="store", type=str, metavar="SERVER",
                    help="Neo4j server. (default: localhost)")
parser.add_argument("-u", "--user", dest="user", action="store", type=str, metavar="USERNAME",
                    help="Neo4j account name. (default: neo4j)")
parser.add_argument("-p", "--password", dest="password", action="store", type=str, metavar="PASSWORD",
                    help="Neo4j password. (default: password).")
parser.add_argument("-z", "--timezone", dest="timezone", action="store", type=int, metavar="UTC",
                    help="Event log time zone. (for example: +9) (default: GMT)")
parser.add_argument("-f", "--from", dest="fromdate", action="store", type=str, metavar="DATE",
                    help="Parse Security Event log from this time. (for example: 20170101000000)")
parser.add_argument("-t", "--to", dest="todate", action="store", type=str, metavar="DATE",
                    help="Parse Security Event log to this time. (for example: 20170228235959)")
parser.add_argument("--delete", action="store_true", default=False,
                    help="Delete all nodes and relationships from this Neo4j database. (default: False)")
args = parser.parse_args()

statement_user = """
  MERGE (user:Username{ user:{user} }) set user.rights={rights}, user.sid={sid}, user.rank={rank}, user.counts={counts}, user.counts4624={counts4624}, user.counts4625={counts4625}, user.counts4768={counts4768}, user.counts4769={counts4769}, user.counts4776={counts4776}, user.detect={detect}
  RETURN user
  """

statement_ip = """
  MERGE (ip:IPAddress{ IP:{IP} }) set ip.rank={rank}
  RETURN ip
  """

statement_r = """
  MATCH (user:Username{ user:{user} })
  MATCH (ip:IPAddress{ IP:{IP} })
  CREATE (ip)-[event:Event]->(user) set event.id={id}, event.logintype={logintype}, event.status={status}, event.count={count}

  RETURN user, ip
  """

statement_date = """
  MERGE (date:Date{ date:{Daterange} }) set date.start={start}, date.end={end}
  RETURN date
  """

if args.user:
    NEO4J_USER = args.user

if args.password:
    NEO4J_PASSWORD = args.password

if args.server:
    NEO4J_SERVER = args.server

if args.port:
    WEB_PORT = args.port

# Web application index.html
@app.route('/')
def index():
    return render_template("index.html", server_ip=NEO4J_SERVER, neo4j_password=NEO4J_PASSWORD, neo4j_user=NEO4J_USER)


# Timeline view
@app.route('/timeline')
def timeline():
    return render_template("timeline.html", server_ip=NEO4J_SERVER, neo4j_password=NEO4J_PASSWORD, neo4j_user=NEO4J_USER)


# Web application logs
@app.route('/log')
def logs():
    lf = open("static/logontracer.log", "r")
    logdata = lf.read()
    lf.close()
    return logdata


# Web application influxdb
@app.route('/getTimeline', methods=["POST"])
def getTimelineInfluxdb():
    host = os.environ['influx_host']
    port = os.environ['influx_port']
    user = os.environ['influx_user']
    password = os.environ['influx_pass']
    dbname = os.environ['influx_db']
    data = request.form.to_dict()


    client = InfluxDBClient(host, port, user, password, dbname)

    query = (data['query'])
    result = client.query(query)
    return jsonify(result.raw)

def main():
    if not has_py2neo:
        sys.exit("[!] py2neo must be installed for this script.")


    try:
        graph_http = "http://" + NEO4J_USER + ":" + NEO4J_PASSWORD +"@" + NEO4J_SERVER + ":" + NEO4J_PORT + "/db/data/"
        GRAPH = Graph(graph_http)
    except:
        sys.exit("[!] Can't connect Neo4j Database.")

    print("[*] Script start. %s" % datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"))

    if args.run:
        try:
            app.run(threaded=True, host="0.0.0.0", port=WEB_PORT, debug=True)
        except:
            sys.exit("[!] Can't runnning web application.")

    # Delete database data
    if args.delete:
        GRAPH.delete_all()
        print("[*] Delete all nodes and relationships from this Neo4j database.")


    print("[*] Script end. %s" % datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"))

if __name__ == "__main__":
    main()
