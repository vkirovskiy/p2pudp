#!/usr/bin/env python
# UDP hole punching
# client-1 (192.168.1.1 srcport 1234) -> (register, conn cmd to client-2) -> server (192.168.2.1 dstport 8001)
# server store real ip and srcport client-1 (192.168.1.1:1234)
# client-2 (192.168.3.1 srcport 4567) -> (register cmd ) -> server (192.168.2.1 dstport 8001)
# server response -> (client-1 is 192.168.1.1:1234) -> client-2

import select
import sys
from time import time
import argparse
from p2pserver import pServerWorker
import signal


parser = argparse.ArgumentParser()
parser.add_argument("--myid", help="id to find you")
parser.add_argument("-p", type=int, help="server port")
parser.add_argument("server", help="helper server ip")
parser.add_argument("-l", help="log file with packet trace")

args = parser.parse_args()
if args.myid:
    myid = args.myid

if args.server:
    SERVER=args.server
    if args.p:
        SRVPORT=args.p
    else:
        SRVPORT=8001

pworker = pServerWorker(SERVER, SRVPORT, myid)
if args.l: pworker.packetlog = args.l

signal.signal(signal.SIGINT, pworker.sig_exit_handler)

pworker.register()
t1 = time()

while True:
    r, w, e = select.select([pworker.socket, sys.stdin],[],[],10)
    for s in r:
        if s == pworker.socket:
            pworker.recv_data()
        elif s == sys.stdin:
            line = s.readline()
            pworker.user_console(line) 
        else:
            print "Unknown socket"

    t2 = time()
    if t2-t1>10: 
        pworker.register()
        pworker.send_ka_to_clients()
        t1=t2

