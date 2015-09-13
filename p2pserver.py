import socket
from collections import deque
from os import popen
from struct import *
from time import time, sleep
from p2pcmdhandler import pStdCmdHandler as cmdHandler
import sys
import types
import threading
import string
import random
import pickle

ENDC = '\033[0m'
OKGREEN = '\033[92m'
OKRED = '\033[91m'

class pServerWorker:

    ka_timeout = 120

    clientstruct = {
        'id': '',
        'address': '',
        'port': 0,
        'last_ka': 0,
    }

    def __init__(s, server, port, myid, autoconn):
        s.clients = []
        s.registered = False


        s.server = server
        s.srvport = port
        s.myid = myid
        s.autoconnect = autoconn
        s.wait_client = ''
        
        s.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.socket.connect((server,port))

        s.srcip = s.socket.getsockname()[0]
        s.srcport = s.socket.getsockname()[1]
        s.socket.close()

        s.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.socket.setblocking(0)
        s.socket.bind((s.srcip, s.srcport))
        print s.myid + " listening on " + s.srcip + ":" + str(s.srcport)
        s.bufflen = 65535 

        s.log = deque('', 128)
        s.cmdq = deque()

        s.packetlog = ''
        s.packetlogfd = ''

        s.oreadsize = 16384 
        s.ostream = {
            'name': '',
            'type': '',
            'uid': '',
            'size': '',
            'seek': 0,
            'blksize': 32768,
            'data': []
        }

        s.clcmdhandler = cmdHandler(s)

        s.th_run = 1
        s.th = threading.Thread(target=s.clcmdhandler.run)
        s.th.start()

    def sig_exit_handler(s):
        s.th_run = 0
        s.th.join()

        print "\n" + __name__ + " Bye\n"

    def logger(s, data):
        s.log.append(data)

        if s.packetlog:
            if type(s.packetlogfd) == 'file':
                if s.packetlogfd.closed:
                    s.packetlogfd = open(s.packetlog, 'a')
            else:
                s.packetlogfd = open(s.packetlog, 'a')

            s.packetlogfd.write(data)

    def printlog(s):
        for i in s.log:
            sys.stdout.write(i)
        
    def send_data(s, addr='', port=0, data=''):
        if not addr:
            addr=s.server

        if not port:
            port=s.srvport

        while True:
            try:
                s.socket.sendto(data, (addr, port))
                #print OKRED + "[" + s.myid + "]" + data + ENDC
                s.logger("UDP: sent  " + str(len(data)) + " bytes \n")
                break
            except IOError, e:
                if e.errno == 11: 
                    s.logger("UDP socket busy")
                    sleep(0.01)

    def send_packet_data(s, addr, port, cmdid, data):
        uniqstr = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(4))
        pdata = pack("H4sI%ds" % (len(data)), cmdid, uniqstr, len(data), data)
        s.send_data(addr, port, pdata)

    def recv_data(s):
        response, addrport = s.socket.recvfrom(s.bufflen)

        s.logger("UDP: received  " + str(len(response)) + " bytes \n")
       # print OKGREEN + "[" + s.myid + "] " + response + ENDC
        
        if addrport[0] == s.server and addrport[1] == s.srvport:
            s.pCmdHandler(response)
            
        else:
            (cmdid, uniqstr, psize) = unpack("H4sI", response[:12])
            pdata = response[12:12+psize]
            #print "cmdid:", cmdid, "psize:", psize, pdata
            s.catch_client_cmd(addrport, cmdid, psize, pdata)

    def register(s):
        s.send_data(data = "set " + s.myid)
        
    def connect_to(s, uid):
        s.send_data(data = "get " + uid)
        
    def add_client(s, addr='', port=0, mid=''):
        found = 0

        for cl in s.clients:
            print "Finding clients: ", cl['address'], " = ", addr, cl['port'], " = ", port
            if cl['address'] == addr and cl['port'] == port:
               found = 1 
               print "found"

        if not found:
            newcl = s.clientstruct
            newcl['address'] = addr
            newcl['port'] = port
            newcl['id'] = mid
            newcl['last_ka'] = time()
            print "Append " + str(newcl)
            s.clients.append(newcl)

    def pCmdHandler(s, data):
        r = str(data).strip(">").rstrip().split(" ")

        if r[0] == s.myid and r[1] == 'registered':
            if not s.registered:
                s.logger("Registered on server\n")
                s.registered = True
                if isinstance(s.autoconnect, str) and len(s.autoconnect) > 0:
                    s.connect_to(s.autoconnect)
                    s.autoconnect = ''

            if len(r) > 2:
                s.logger("Daemon: Query to connect from " + r[2] + "\n")
                claddr, clport = r[2].split(":")

                s.add_client(claddr, int(clport), '')

        elif r[0] == 'client':
            claddr, clport = r[2].split(":")
            s.add_client(claddr, int(clport), r[1])

            s.logger("Daemon: added client " + r[2] + "as" + r[1] + "\n")

    def send_ka_to_clients(s):
        tn = time()
        for i in s.clients:
            s.send_packet_data(i['address'], int(i['port']), 0, data=s.myid)
            if i['id']:
                s.logger("[" + s.myid + "] Daemon: Send KA to " + i['id'] + "\n")
            else:
                s.logger("[" + s.myid + "] Daemon: Send KA to " + i['address'] + " " + str(i['port']) + "\n")

            if s.wait_client == i['id'] and s.wait_client > '':
                print "I'm exit because " + s.wait_client + " is appeared"
                s.socket.close()
                s.th_run = 0
                s.th.join()
                del s
                break

    def catch_client_cmd(s, addrport, cmdid, size, response):
        r = str(response)

        for cl in s.clients:
            if cl['address'] == addrport[0] and cl['port'] == addrport[1]:
                if s.th_run:
                    if not s.th.isAlive():
                        print "Starting thread"
                        s.th = threading.Thread(target=s.clcmdhandler.run)
                        s.th.start()

                    s.cmdq.append((cl, cmdid, response))


    def id2ip(s, mid):
        for i in s.clients:
            if i['id'] == mid:
                return i['address'], i['port']

        return False


import socket
