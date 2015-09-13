#!/usr/bin/env python
# UDP hole punching
# client-1 (192.168.1.1 srcport 1234) -> (register, conn cmd to client-2) -> server (192.168.2.1 dstport 8001)
# server store real ip and srcport client-1 (192.168.1.1:1234)
# client-2 (192.168.3.1 srcport 4567) -> (register cmd ) -> server (192.168.2.1 dstport 8001)
# server response -> (client-1 is 192.168.1.1:1234) -> client-2

import select
import socket
import sys
from time import time
import argparse
from p2pserver import pServerWorker
import signal
from p2pusercmd import user_console

parser = argparse.ArgumentParser()
parser.add_argument("--myid", help="id to find you")
parser.add_argument("-p", type=int, help="server port")
parser.add_argument("server", help="helper server ip")
parser.add_argument("-l", help="log file with packet trace")
parser.add_argument("--connect", help="auto connect to")
parser.add_argument("--wait", help="wait client and exit")

args = parser.parse_args()
if args.myid:
    myid = args.myid

if args.server:
    SERVER=args.server
    if args.p:
        SRVPORT=args.p
    else:
        SRVPORT=8001

pworker = pServerWorker(SERVER, SRVPORT, myid, args.connect)
pworker_slave = pServerWorker(SERVER, SRVPORT, myid + "-slave", '')

def sig_exit(sig, f):
    pworker.sig_exit_handler()
    pworker_slave.sig_exit_handler()
    sys.exit(0)

if args.l: pworker.packetlog = args.l
if args.wait: pworker_slave.wait_client = args.wait

signal.signal(signal.SIGINT, sig_exit)

pworker.register()
pworker_slave.register()
t1 = time()

print type(pworker.socket)
print type(sys.stdin)

socks = [pworker.socket, pworker_slave.socket, sys.stdin]

while True:
    r, w, e = select.select(socks,[],[],10)

    for s in r:
        if s == pworker.socket:
            pworker.recv_data()
        elif s == pworker_slave.socket:
            pworker_slave.recv_data()
        elif s == sys.stdin:
            line = s.readline()
            user_console(pworker, line) 
        else:
            print "Unknown socket"

    if not pworker_slave:
        print "Slave died. Restarting"
        pworker_slave = pServerWorker(SERVER, SRVPORT, myid + "-slave", '')

    t2 = time()
    if t2-t1>5: 
        pworker.register()
        pworker_slave.register()
        pworker.send_ka_to_clients()
        #pworker_slave.send_ka_to_clients()
        t1=t2

