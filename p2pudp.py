#!/usr/bin/env python
# UDP hole punching
# client-1 (192.168.1.1 srcport 1234) -> (register, conn cmd to client-2) -> server (192.168.2.1 dstport 8001)
# server store real ip and srcport client-1 (192.168.1.1:1234)
# client-2 (192.168.3.1 srcport 4567) -> (register cmd ) -> server (192.168.2.1 dstport 8001)
# server response -> (client-1 is 192.168.1.1:1234) -> client-2

import socket
import select
import sys
from time import time
from os import popen 
from collections import deque
import argparse


class pServerWorker:

    clients = {} 
    registered = False

    def __init__(s, server, port, myid):
        s.server = server
        s.srvport = port
        s.myid = myid
        
        s.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.socket.connect((server,port))

        s.srcip = s.socket.getsockname()[0]
        s.srcport = s.socket.getsockname()[1]
        s.socket.close()

        s.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.socket.setblocking(0)
        s.socket.bind((s.srcip, s.srcport))
        s.bufflen = 1024

        s.log = deque('', 128)

    def logger(s, data):
        s.log.append(data)

    def printlog(s):
        for i in s.log:
            print i
        
    def send_data(s, addr='', port=0, data=''):
        if not addr:
            addr=s.server

        if not port:
            port=s.srvport
        s.socket.sendto(data, (addr, port))

    def recv_data(s):
        response, addrport = s.socket.recvfrom(s.bufflen)
        
        if addrport[0] == s.server and addrport[1] == s.srvport:
            s.logger("Server: " + str(response))
            s.pCmdHandler(response)
            
        else:
            s.logger("Client: " + "from " + str(addrport) + " " + str(response))
            s.catch_client_cmd(addrport, response)

    def register(s):
        s.send_data(data = "set " + s.myid)

    def pCmdHandler(s, data):
        r = str(data).strip(">").rstrip().split(" ")

        if r[0] == myid and r[1] == 'registered':
            if not s.registered:
                s.logger("Registered on server")
                s.registered = True

            if len(r) > 2:
                s.logger("Daemon: Query to connect from " + r[2] + "\n")
                claddr, clport = r[2].split(":")
                if r[2] not in s.clients:
                    s.clients[str(r[2])] = 'unknown'

        elif r[0] == 'client':
            s.clients[str(r[2])] = r[1]
            s.logger("Daemon: added client " + r[2] + "as" + r[1] + "\n")

    def send_ka_to_clients(s):
        for i in s.clients:
            claddr, clport = i.split(":")
            s.send_data(addr=claddr, port=int(clport), data="KA")
            s.logger("Daemon: Send KA to " + claddr + clport + "\n")
        

    def catch_client_cmd(s, addrport, response):
        r = str(response).rstrip().split(" ")

        if r[0] == 'exec':
            print "Executing command ", r[1]
            for i in popen(r[1]).readlines():
                s.send_data(addr=addrport[0], port=addrport[1], data="> " + i)
        elif [0] == '>':
            print str(r)

    def id2ip(s, id):
        for i in s.clients:
            if s.clients[i] == id:
                return i

        return False


def user_worker(worker, data):

    r = str(data).strip().rstrip().split(" ")

    if r[0] == 'listclients':
        for k in worker.clients:
            print k, worker.clients[k] 
    elif r[0] == 'connect':
        remoteid = r[1]
        print "Connecting to " + remoteid
        worker.send_data(data="get " + remoteid)
        worker.send_data(data="conn " + remoteid)
    elif r[0] == "exec":
        remoteid = r[1]
        raddrport = worker.id2ip(remoteid)
        if raddrport:
            claddr, clport = raddrport.split(":")
            worker.send_data(addr=claddr, port=int(clport), data="exec "+ r[2])
    elif r[0] == 'log':
        worker.printlog()


# Parse cmdline

parser = argparse.ArgumentParser()
parser.add_argument("--myid", help="id to find you")
parser.add_argument("-p", type=int, help="server port")
parser.add_argument("server", help="helper server ip")

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
pworker.register()
t1 = time()

while True:
    r, w, e = select.select([pworker.socket, sys.stdin],[],[],10)
    for s in r:
        if s == pworker.socket:
            pworker.recv_data()
        elif s == sys.stdin:
            user_worker(pworker, s.readline()) 
        else:
            print "Unknown socket"

    t2 = time()
    if t2-t1>10: 
        pworker.register()
        pworker.send_ka_to_clients()
        t1=t2

