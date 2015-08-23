import socket
from collections import deque
from os import popen
from struct import *

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

    def send_packet_data(s, addr, port, cmdid, data):
        print "Len of data", str(len(data))
        pdata = pack("HH%ds" % (len(data)), cmdid, len(data), data)
        s.send_data(addr, port, pdata)

    def recv_data(s):
        response, addrport = s.socket.recvfrom(s.bufflen)
        
        if addrport[0] == s.server and addrport[1] == s.srvport:
            s.logger("Server: " + str(response))
            s.pCmdHandler(response)
            
        else:
            s.logger("Client: " + "from " + str(addrport) + " " + str(response))
            (cmdid, psize) = unpack("BH", response[:4])
            pdata = response[4:4+psize]
            print "cmdid:", cmdid, "psize:", psize, pdata
            s.catch_client_cmd(addrport, cmdid, psize, pdata)

    def register(s):
        s.send_data(data = "set " + s.myid)

    def pCmdHandler(s, data):
        r = str(data).strip(">").rstrip().split(" ")

        if r[0] == s.myid and r[1] == 'registered':
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
            s.send_packet_data(claddr, int(clport), 1, data="KA")
            s.logger("Daemon: Send KA to " + claddr + clport + "\n")
        

    def catch_client_cmd(s, addrport, cmdid, size, response):
        r = str(response)

        print "REceived:", str(cmdid), str(size), r

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
