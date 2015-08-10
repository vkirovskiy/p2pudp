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

myid = '0b38ddb4627776f7ddf210cd90f1bec1'
SERVER = '192.168.66.82'
SRVPORT = 8001
SRCIP = '192.168.2.2'
SRCPORT = 6789

clients = {} 
registered = False

def create_socket(srvip=SERVER, srvport=SRVPORT, srcip=SRCIP, srcport=SRCPORT):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setblocking(0)
    sock.bind((srcip, srcport))
    
    return sock

def send_udp(socket, addr, port, data):
    socket.sendto(data, (addr, port))

def recv_udp(socket):
    data, addr = socket.recvfrom(128)
    
    return data, addr

def register(socket, srvip=SERVER, srvport=SRVPORT, mid=""):

    send_udp(socket, srvip, srvport, "set " + mid)

def net_worker(socket, data):
    response = data[0]
    addrport = data[1]

    if addrport[0] == SERVER and addrport[1] == SRVPORT:
        sys.stderr.write("Server: " + str(response))
        catch_server_cmd(socket, addrport, response)

    else:
        sys.stderr.write("Client: " + "from " + str(addrport) + " " + str(response))
        catch_client_cmd(socket, addrport, response)

def send_ka_to_clients(socket, clients):
    for i in clients:
        claddr, clport = i.split(":")
        send_udp(socket, claddr, int(clport), "KA")
        sys.stderr.write("Daemon: Send KA to " + claddr + clport + "\n")

def catch_server_cmd(socket, addrport, response):
    global registered
    global clients
    r = str(response).strip(">").rstrip().split(" ")

    if r[0] == myid and r[1] == 'registered':
        if not registered:
            print "Registered on server"
            registered = True

        # somebody wants to connect
        if len(r) > 2:
            sys.stderr.write("Daemon: Query to connect from " + r[2] + "\n")
            claddr, clport = r[2].split(":")
            if r[2] not in clients:
                clients[str(r[2])] = 'unknown'

    elif r[0] == 'client':
        clients[str(r[2])] = r[1]
        sys.stderr.write("Daemon: added client " + r[2] + "as" + r[1] + "\n")

def catch_client_cmd(socket, addrport, response):
    r = str(response).rstrip().split(" ")
    print "Msg from " + str(addrport) + str(r)


def user_worker(socket, data):
    global clients
    r = str(data).strip().rstrip().split(" ")

    if r[0] == 'listclients':
        for k in clients:
            print k, clients[k] 
    elif r[0] == 'connect':
        remoteid = r[1]
        print "Connecting to " + remoteid
        send_udp(socket, SERVER, SRVPORT, "get " + remoteid)
        send_udp(socket, SERVER, SRVPORT, "conn " + remoteid)


socket = create_socket()
register(socket, mid=myid)
t1 = time()

while True:
    r, w, e = select.select([socket, sys.stdin],[],[],10)
    for s in r:
        if s == socket:
            net_worker(s, recv_udp(s))
        elif s == sys.stdin:
            user_worker(socket, s.readline()) 
        else:
            print "Unknown socket"

    t2 = time()
    if t2-t1>10: 
        register(socket, mid=myid)
        send_ka_to_clients(socket, clients)
        t1=t2

