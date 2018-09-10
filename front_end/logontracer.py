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
    from lxml import etree
    has_lxml = True
except ImportError:
    has_lxml = False

try:
    from Evtx.Evtx import Evtx
    from Evtx.Views import evtx_file_xml_view
    has_evtx = True
except ImportError:
    has_evtx = False

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
    import changefinder
    has_changefinder = True
except ImportError:
    has_changefinder = False

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
parser.add_argument("-e", "--evtx", dest="evtx", nargs="*", action="store", type=str, metavar="EVTX",
                    help="Import to the AD EVTX file. (multiple files OK)")
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


# Web application upload
@app.route("/upload", methods=["POST"])
def do_upload():
    filelist= ""
    try:
        timezone = request.form["timezone"]
        for  i in range(0, len(request.files)):
            loadfile = "file" + str(i)
            file = request.files[loadfile]
            if file and file.filename:
                filename = file.filename
                file.save(filename)
                filelist += filename + " "
        parse_command = "nohup python3 logontracer.py --delete -z " + timezone + " -e " + filelist + " -u " + NEO4J_USER + " -p " + NEO4J_PASSWORD + " > static/logontracer.log 2>&1 &";
        subprocess.call("rm -f static/logontracer.log > /dev/null", shell=True)
        subprocess.call(parse_command, shell=True)
        #parse_evtx(filename)
        return "SUCCESS"
    except:
        return "FAIL"


# Calculate ChangeFinder
def adetection(counts, users,  ranks, starttime, tohours):
    count_array = np.zeros((5, len(users), tohours + 1))
    count_all_array = []
    result_array = []
    for event, count in counts:
        column = int((datetime.datetime.strptime(event[0], "%Y-%m-%d  %H:%M:%S") - starttime).total_seconds() / 3600)
        row = users.index(event[2])
        #count_array[row, column, 0] = count_array[row, column, 0] + count
        if event[1] == 4624:
            count_array[0, row, column] = count
        elif event[1] == 4625:
            count_array[1, row, column] = count
        elif event[1] == 4768:
            count_array[2, row, column] = count
        elif event[1] == 4769:
            count_array[3, row, column] = count
        elif event[1] == 4776:
            count_array[4, row, column] = count

    #count_average = count_array.mean(axis=0)
    count_sum = np.sum(count_array, axis=0)
    count_average = count_sum.mean(axis=0)
    num = 0
    for udata in count_sum:
        cf = changefinder.ChangeFinder(r=0.04, order=1, smooth=5)
        ret = []
        u = ranks[users[num]]
        for i in count_average:
            cf.update(i * u)

        for i in udata:
            score = cf.update(i * u)
            ret.append(round(score, 2))
        result_array.append(ret)

        count_all_array.append(udata.tolist())
        for var in range(0, 5):
            con = []
            for i in range(0, tohours + 1):
                con.append(count_array[var, num, i])
            count_all_array.append(con)
        num += 1

    return count_all_array, result_array


# Calculate PageRank
def pagerank(event_set_uniq):
    graph = {}
    nodes = []
    for events, count in event_set_uniq:
        nodes.append(events[1])
        nodes.append(events[2])

    for node in list(set(nodes)):
        links = []
        for events, count in event_set_uniq:
            if node in events[1]:
                links.append(events[2])
            if node in events[2]:
                links.append(events[1])
        graph[node] = links

    d = 0.8
    numloops = 10
    ranks = {}
    npages = len(graph)
    for page in graph:
        ranks[page] = 1.0 / npages

    for i in range(0, numloops):
        newranks = {}
        for page in graph:
            newrank = (1 - d) / npages
            for node in graph:
                if page in graph[node]:
                    newrank = newrank + d * ranks[node]/len(graph[node])
            newranks[page] = newrank
        ranks = newranks

    return ranks


def to_lxml(record_xml):
    record_xml = record_xml.encode("utf-8")
    return etree.fromstring(record_xml)


def xml_records(filename):
    with Evtx(filename) as evtx:
        for xml, record in evtx_file_xml_view(evtx.get_file_header()):
            try:
                yield to_lxml(xml), None
            except etree.XMLSyntaxError as e:
                yield xml, e, fh


def get_child(node, tag, ns="{http://schemas.microsoft.com/win/2004/08/events/event}"):
    return node.find("%s%s" % (ns, tag))


# Parse the EVTX file
def parse_evtx(evtx_list, GRAPH):
    event_set = []
    count_set = []
    ipaddress_set = []
    username_set = []
    admins = []
    sids = {}
    count = 0
    record_sum = 0
    starttime = None
    endtime = None

    if args.timezone:
        try:
            datetime.timezone(datetime.timedelta(hours=args.timezone))
            tzone = args.timezone
            print("[*] Time zone is %s." % args.timezone)
        except:
            sys.exit("[!] Can't load time zone '%s'." % args.timezone)
    else:
        tzone = 0

    if args.fromdate:
        try:
            fdatetime = datetime.datetime.strptime(args.fromdate, "%Y%m%d%H%M%S")
            print("[*] Parse the EVTX from %s." % fdatetime.strftime("%Y-%m-%d %H:%M:%S"))
        except:
            sys.exit("[!] From date does not match format '%Y%m%d%H%M%S'.")

    if args.todate:
        try:
            tdatetime =  datetime.datetime.strptime(args.todate, "%Y%m%d%H%M%S")
            print("[*] Parse the EVTX from %s." % tdatetime.strftime("%Y-%m-%d %H:%M:%S"))
        except:
            sys.exit("[!] To date does not match format '%Y%m%d%H%M%S'.")

    for evtx_file in evtx_list:
        fb = open(evtx_file, "rb")
        fb_data = fb.read()[0:8]
        if fb_data != EVTX_HEADER:
            sys.exit("[!] This file is not EVTX format {0}.".format(evtx_file))
        fb.close()

        chunk = -2
        with Evtx(evtx_file) as evtx:
            fh = evtx.get_file_header()
            while True:
                last_chunk = list(evtx.chunks())[chunk]
                last_record = last_chunk.file_last_record_number()
                chunk -= 1
                if last_record > 0:
                    record_sum = record_sum + last_record
                    break

    print("[*] Last recode number is %i." % record_sum)

    # Parse Event log
    print("[*] Start parsing the EVTX file.")

    for evtx_file in evtx_list:
        print("[*] Parse the EVTX file %s." % evtx_file)

        for node, err in xml_records(evtx_file):
            count += 1
            if not count % 100:
                sys.stdout.write("\r[*] Now loading %i records." % count)
                sys.stdout.flush()

            if err is not None:
                continue

            sysev = get_child(node, "System")
            if int(get_child(sysev, "EventID").text) in EVENT_ID:
                logtime = get_child(sysev, "TimeCreated").get("SystemTime")
                etime = datetime.datetime.strptime(logtime.split(".")[0], "%Y-%m-%d %H:%M:%S") + datetime.timedelta(hours=tzone)
                if args.fromdate or args.todate:
                    if args.fromdate and fdatetime > etime:
                        continue
                    if args.todate and tdatetime < etime:
                        endtime = datetime.datetime(*etime.timetuple()[:4])
                        break

                if starttime is None:
                    starttime = datetime.datetime(*etime.timetuple()[:4])
                elif starttime > etime:
                    starttime = datetime.datetime(*etime.timetuple()[:4])

                if endtime is None:
                    endtime = datetime.datetime(*etime.timetuple()[:4])
                elif endtime < etime:
                    endtime = datetime.datetime(*etime.timetuple()[:4])

                event_data = get_child(node, "EventData")
                logintype = "-"
                username = "-"
                ipaddress = "-"
                status = "-"
                sid = "-"
                for data in event_data:
                    if data.get("Name") in ["IpAddress", "Workstation"] and data.text != None:
                        ipaddress = data.text.split("@")[0]
                        ipaddress = ipaddress.lower().replace("::ffff:", "")
                        ipaddress = ipaddress.replace("\\", "")

                    if data.get("Name") in "TargetUserName" and data.text != None:
                        username = data.text.split("@")[0]
                        if username[-1:] not in "$":
                            username = username.lower()
                        else:
                            username = "-"

                    if data.get("Name") in ["TargetUserSid", "TargetSid"] and data.text != None and data.text[0:2] in "S-1":
                        sid = data.text

                    if data.get("Name") in "LogonType":
                        logintype = int(data.text)

                    if data.get("Name") in "Status":
                        status = data.text

                if username != "-" and ipaddress != "-" and ipaddress != "::1" and ipaddress != "127.0.0.1":
                    event_set.append([int(get_child(sysev, "EventID").text), ipaddress, username, logintype, status])
                    # print("%s,%i,%s,%s,%s,%s" % (int(get_child(sysev, "EventID").text), ipaddress, username, comment, logintype))
                    count_set.append([datetime.datetime(*etime.timetuple()[:4]).strftime("%Y-%m-%d %H:%M:%S"), int(get_child(sysev, "EventID").text), username])
                    # print("%s,%s" % (datetime.datetime(*etime.timetuple()[:4]).strftime("%Y-%m-%d %H:%M:%S"), username))

                    if ipaddress not in ipaddress_set:
                        ipaddress_set.append(ipaddress)

                    if username not in username_set:
                        username_set.append(username)

                    if sid not in "-":
                        sids[username] = sid

            if int(get_child(sysev, "EventID").text) == 4672:
                logtime = get_child(sysev, "TimeCreated").get("SystemTime")
                if args.fromdate or args.todate:
                    etime = datetime.datetime.strptime(logtime.split(".")[0], "%Y-%m-%d %H:%M:%S") + datetime.timedelta(hours=tzone)
                    if args.fromdate and fdatetime > etime:
                        continue
                    if args.todate and tdatetime < etime:
                        break

                event_data = get_child(node, "EventData")
                username = "-"
                for data in event_data:
                    if data.get("Name") in "SubjectUserName" and data.text != None:
                        username = data.text.split("@")[0]
                        if username[-1:] not in "$":
                            username = username.lower()
                        else:
                            username = "-"

                if username not in admins and username != "-":
                    admins.append(username)

    tohours = int((endtime - starttime).total_seconds() / 3600)

    print("\n[*] Load finished.")
    print("[*] Total Event log is %i." % count)
    event_set.sort()
    event_set_uniq = [(g[0], len(list(g[1]))) for g in itertools.groupby(event_set)]
    count_set.sort()
    count_set_uniq = [(g[0], len(list(g[1]))) for g in itertools.groupby(count_set)]

    # Calculate PageRank
    print("[*] Calculate PageRank.")
    ranks = pagerank(event_set_uniq)

    # Calculate ChangeFinder
    print("[*] Calculate ChangeFinder.")
    timelines, detects = adetection(count_set_uniq, username_set, ranks, starttime, tohours)

    # Create node
    print("[*] Creating a graph data.")
    tx = GRAPH.begin()
    for ipaddress in ipaddress_set:
        tx.append(statement_ip, {"IP": ipaddress, "rank": ranks[ipaddress]})

    i = 0
    for username in username_set:
        if username in sids:
            sid = sids[username]
        else:
            sid = "-"
        if username in admins:
            rights = "system"
        else:
            rights = "user"
        tx.append(statement_user, {"user": username, "rank": ranks[username],"rights": rights,"sid": sid,
                                                    "counts": ",".join(map(str, timelines[i*6])), "counts4624": ",".join(map(str, timelines[i*6+1])),
                                                    "counts4625": ",".join(map(str, timelines[i*6+2])), "counts4768": ",".join(map(str, timelines[i*6+3])),
                                                    "counts4769": ",".join(map(str, timelines[i*6+4])), "counts4776": ",".join(map(str, timelines[i*6+5])),
                                                    "detect": ",".join(map(str, detects[i]))})
        i += 1

    for events, count in event_set_uniq:
        tx.append(statement_r, {"user": events[2], "IP": events[1], "id": events[0], "logintype": events[3],
                                               "status": events[4], "count": count})

    tx.append(statement_date, {"Daterange": "Daterange", "start": datetime.datetime(*starttime.timetuple()[:4]).strftime("%Y-%m-%d %H:%M:%S"),
                                                 "end": datetime.datetime(*endtime.timetuple()[:4]).strftime("%Y-%m-%d %H:%M:%S")})

    tx.process()
    tx.commit()
    print("[*] Creation of a graph data finished.")


def main():
    if not has_py2neo:
        sys.exit("[!] py2neo must be installed for this script.")

    if not has_evtx:
        sys.exit("[!] python-evtx must be installed for this script.")

    if not has_lxml:
        sys.exit("[!] lxml must be installed for this script.")

    if not has_lxml:
        sys.exit("[!] numpy must be installed for this script.")

    if not has_changefinder:
        sys.exit("[!] changefinder must be installed for this script.")

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

    if args.evtx:
        for evtx_file in args.evtx:
            if not os.path.isfile(evtx_file):
                sys.exit("[!] Can't open file {0}.".format(evtx_file))
        parse_evtx(args.evtx, GRAPH)

    print("[*] Script end. %s" % datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"))

if __name__ == "__main__":
    main()
