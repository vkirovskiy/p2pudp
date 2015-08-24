import socket
from collections import deque
from os import popen
from struct import *
from time import time
from p2pcmdhandler import pCmdHandler
import sys

class pServerWorker:

    clients = [] 
    registered = False
    ka_timeout = 120

    clientstruct = {
        'id': '',
        'address': '',
        'port': 0,
        'last_ka': 0,
        'connection': 'CLOSED'
    }

    usercommands = ['help', 'write', '>', 'exec', 'connect', 'log', 'clients']

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
            sys.stdout.write(i)
        
    def send_data(s, addr='', port=0, data=''):
        if not addr:
            addr=s.server

        if not port:
            port=s.srvport
        s.socket.sendto(data, (addr, port))

    def send_packet_data(s, addr, port, cmdid, data):
        #print "Len of data", str(len(data))
        pdata = pack("HH%ds" % (len(data)), cmdid, len(data), data)
        s.send_data(addr, port, pdata)

    def recv_data(s):
        response, addrport = s.socket.recvfrom(s.bufflen)
        
        if addrport[0] == s.server and addrport[1] == s.srvport:
            s.logger("Server: " + str(response))
            s.pCmdHandler(response)
            
        else:
            s.logger("Client: " + "from " + str(addrport) + " " + str(response) + "\n")
            (cmdid, psize) = unpack("BH", response[:4])
            pdata = response[4:4+psize]
            #print "cmdid:", cmdid, "psize:", psize, pdata
            s.catch_client_cmd(addrport, cmdid, psize, pdata)

    def register(s):
        s.send_data(data = "set " + s.myid)

    def add_client(s, addr='', port=0, mid=''):
        for cl in s.clients:
            if cl['address'] == addr and cl['port'] == port:
                break
        else:
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
                s.logger("Registered on server")
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
            if tn - i['last_ka'] < s.ka_timeout:
                claddr, clport = i['address'], i['port']
                s.send_packet_data(claddr, int(clport), 0, data="KA")
                s.logger("Daemon: Send KA to " + claddr + str(clport) + "\n")

    def catch_client_cmd(s, addrport, cmdid, size, response):
        r = str(response)

        s.logger("Received:" + str(cmdid) + str(size) + r + "\n")

        if cmdid == 0:
            for cl in s.clients:
                if cl['id'] == '':
                    s.send_packet_data(addrport[0], addrport[1], 1, '')

                if cl['address'] == addrport[0] and cl['port'] == addrport[1]:
                    cl['last_ka'] = time()
                    break
            else:
                s.logger("KA from unknown client received: " + str(addrport))
                s.send_packet_data(addrport[0], addrport[1], 1, '')

        elif cmdid == 1:
            for cl in s.clients:
                if cl['address'] == addrport[0] and cl['port'] == addrport[1]:
                    if len(r) == 0:
                        s.send_packet_data(addrport[0], addrport[1], 1, s.myid)
                    else:
                        cl['id'] = r
        else:
            cmdh = pCmdHandler(cmdid, r)
            for i in cmdh.run():
                s.send_packet_data(addrport[0], addrport[1], 2, i)

    def id2ip(s, mid):
        for i in s.clients:
            if i['id'] == mid:
                return i['address'], i['port']

        return False
    
    def user_console(s, data):
        r = str(data).strip().rstrip().split(" ")
        claddr, clport = s.id2ip(r[1])

        """
        usercmd = userCmdClass(

        """

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

            elif r[0] == '>' or r[0] == 'write':
                claddr, clport = s.id2ip(r[1])
                cmdlen = len(r[0])+len(r[1])+1
                s.send_packet_data(claddr, clport, 2, data[cmdlen:])

            elif r[0] == 'exec':
                claddr, clport = s.id2ip(r[1])
                cmdlen = len(r[0])+len(r[1])+1
                s.send_packet_data(claddr, clport, 3, data[cmdlen:])

            elif r[0] == 'log':
                s.printlog()

            elif r[0] == 'clients':
                print "Name\t\tAddress\tPort\tLast response"
                for i in s.clients:
                    print i['id'] + "\t" + i['address'] + "\t" + str(i['port']) + "\t" + str(i['last_ka'])
            else:
                ret = cmdparser(data)

        else:
            print "Invalid command"

