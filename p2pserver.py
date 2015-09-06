import socket
from collections import deque
from os import popen
from struct import *
from time import time
from p2pcmdhandler import pStdCmdHandler as cmdHandler
import sys
import types
import threading
import string
import random
import pickle

class pServerWorker:

    clients = [] 
    registered = False
    ka_timeout = 120

    clientstruct = {
        'id': '',
        'address': '',
        'port': 0,
        'last_ka': 0,
    }

    usercommands = ['help', 'write', '>', 'exec', 'connect', 'log', 'clients', 'testbuff', 'getfile']

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
        s.bufflen = 65535 

        s.log = deque('', 128)
        s.cmdq = deque('', 1024)

        s.oreadsize = 8192
        s.ostream = {
            'name': '',
            'type': '',
            'uid': '',
            'size': '',
            'seek': 0,
            'data': []
        }

        s.clcmdhandler = cmdHandler(s)

        s.th_run = 1
        s.th = threading.Thread(target=s.clcmdhandler.run)
        s.th.start()

    def sig_exit_handler(s, sig, f):
        s.th_run = 0
        s.th.join()

        print "\nBye\n"
        sys.exit(0)

    def logger(s, data):
        s.log.append(data)

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
                s.logger("UDP: sent  " + str(len(data)) + " bytes \n")
                break
            except IOError, e:
                if e.errno == 11: pass

    def send_packet_data(s, addr, port, cmdid, data):
        uniqstr = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(4))
        pdata = pack("H4sI%ds" % (len(data)), cmdid, uniqstr, len(data), data)
        s.send_data(addr, port, pdata)

    def recv_data(s):
        response, addrport = s.socket.recvfrom(s.bufflen)

        s.logger("UDP: received  " + str(len(response)) + " bytes \n")
        
        if addrport[0] == s.server and addrport[1] == s.srvport:
            s.pCmdHandler(response)
            
        else:
            (cmdid, uniqstr, psize) = unpack("H4sI", response[:12])
            pdata = response[12:12+psize]
            #print "cmdid:", cmdid, "psize:", psize, pdata
            s.catch_client_cmd(addrport, cmdid, psize, pdata)

    def register(s):
        s.send_data(data = "set " + s.myid)

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
            s.clients.append(newcl)

    def pCmdHandler(s, data):
        r = str(data).strip(">").rstrip().split(" ")

        if r[0] == s.myid and r[1] == 'registered':
            if not s.registered:
                s.logger("Registered on server\n")
                s.registered = True

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
            #if tn - i['last_ka'] < s.ka_timeout:
            s.send_packet_data(i['address'], int(i['port']), 0, data=s.myid)
            s.logger("Daemon: Send KA to " + i['address'] + str(i['port']) + "\n")

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
    
    def user_console(s, data):
        r = str(data).strip().rstrip().split(" ")

        if r[0] in s.usercommands:
            if r[0] == 'help':
                print "Available commands:"
                for i in s.usercommands:
                    print i 
            elif r[0] == 'connect':
                remoteid = r[1]
                print "Connecting to " + remoteid
                s.send_data(data="get " + remoteid)
                s.send_data(data="conn " + remoteid)

           #elif r[0] == '>' or r[0] == 'write':
           #    claddr, clport = s.id2ip(r[1])
           #    cmdlen = len(r[0])+len(r[1])+1
           #    s.send_packet_data(claddr, clport, 2, data[cmdlen:])

            elif r[0] == 'exec':
                claddr, clport = s.id2ip(r[1])
                cmdlen = len(r[0])+len(r[1])+1
                s.send_packet_data(claddr, clport, 2, data[cmdlen:])

            elif r[0] == 'log':
                s.printlog()

            elif r[0] == 'clients':
                print "Name\t\tAddress\tPort\tLast response"
                for i in s.clients:
                    print i['id'] + "\t" + i['address'] + "\t" + str(i['port']) + "\t" + str(i['last_ka'])
            elif r[0] == 'testbuff':
                claddr, clport = s.id2ip(r[1])
                bufflen = int(r[2]) 
                sbuff = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in xrange(bufflen))
                s.send_packet_data(claddr, clport, 128+2, sbuff)
            elif r[0] == 'getfile':
                claddr, clport = s.id2ip(r[1])
                fname = r[2]
                fobj = s.ostream
                fobj['name'] = fname
                fobj['type'] = 'file'
                fobj['uid'] = ''
                fobj['size'] = 0
                s.send_packet_data(claddr, clport, 3, pickle.dumps(fobj))
            else:
                ret = cmdparser(data)

        else:
            print "Invalid command"

