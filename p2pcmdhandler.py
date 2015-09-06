#!/usr/bin/env python

from os import popen
from os.path import getsize
import sys
from time import time, sleep
import types
import pickle
import string
import random
from struct import *

class pStdCmdHandler:
    cmds = {}

    def __init__(s, srv):
        s.server = srv
        s.cmds[0] = s.send_ka
        s.cmds[1] = s.send_id
        s.cmds[2] = s.run_command
        s.cmds[3] = s.send_stream

        s.cmds[128+0] = s.receive_ka
        s.cmds[128+1] = s.receive_id
        s.cmds[128+2] = s.print_command_output
        s.cmds[128+3] = s.recv_stream
    
    def send_ka(s, client, data):
        return s.server.myid

    def send_id(s, client, data):
        return s.server.myid

    def run_command(s, client, data):
        for i in popen(data).readlines():
            yield i

    def send_stream(s, client, data):
        # see format of ostream
        ddict = pickle.loads(data)

        # send only uid and wait response (uid != '')
        if ddict['uid'] == '':
            uid = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in xrange(10))
            s.server.ostream['name'] = ddict['name']
            s.server.ostream['uid'] = uid
            s.server.ostream['data'] = []
            s.server.ostream['size'] = 0

            if ddict['type'] == 'file' and len(ddict['name']) > 1:
                fsize = getsize(ddict['name'])  
                s.server.ostream['size'] = fsize
                s.server.ostream['type'] = 'file'
                s.server.ostream['seek'] = 0

                yield pickle.dumps(s.server.ostream)

        elif ddict['uid'] == s.server.ostream['uid']:
            if ddict['type'] == 'file' and ddict['name'] == s.server.ostream['name']:
                f = open(ddict['name'], 'r')
                oseek = f.tell()

                while True:
                    fdata = f.read(s.server.oreadsize)
                    if not fdata:
                        f.close()
                        break
                    else:
                        s.server.ostream['type'] = 'file'
                        s.server.ostream['seek'] = oseek 
                        s.server.ostream['data'] = bytearray(fdata) 
                        oseek = f.tell()
                        yield pickle.dumps(s.server.ostream)

    def receive_ka(s, client, data):
        client['last_ka'] = time()
        if client['id'] == '':
            client['id'] = data.strip().rstrip()

        return ''

    def receive_id(s, client, data):
        cid = data.strip().rstrip()
        client['id'] == cid
        return ''

    def print_command_output(s, client, data):
        sys.stdout.write("[" + client['id'] + "] => " + str(data))
        return ''

    def recv_stream(s, client, data):
        ddict = pickle.loads(data)
        
        if ddict['type'] == 'file' and len(ddict['data']) == 0:
            #print "Stream: ", ddict['type'], ddict['name'], ddict['uid'], ddict['seek'], ddict['size']
            print str(time()) + " Start transsfer stream " + ddict['uid'] + " " + str(ddict['size']) + "\n"
            s.server.ostream['type'] = 'file'
            s.server.ostream['uid'] = ddict['uid']
            s.server.ostream['name'] = ddict['name']
            s.server.ostream['size'] = ddict['size']
            s.server.ostream['data'] = []

            fname = "/tmp/tmp." + ddict['uid']
            f = open(fname, 'w')
            f.seek(ddict['size'])
            f.write("\0")
            f.close()

            s.server.send_packet_data(client['address'], client['port'], 3, pickle.dumps(s.server.ostream))

        elif ddict['type'] == 'file' and len(ddict['data']) > 0:
            #print "Stream: ", ddict['type'], ddict['name'], ddict['uid'], ddict['seek'], ddict['size']
            fname = "/tmp/tmp." + ddict['uid']

            f = open(fname, 'w')
            f.seek(ddict['seek'])
            f.write(ddict['data'])
            f.close()

            if ddict['seek'] + len(ddict['data']) == s.server.ostream['size']:
                print "File received: " + fname
                print str(time()) + " End transsfer stream " + ddict['uid'] + " " + str(ddict['size']) + "\n" 


        return ''

    def run(s):
        
        s.server.logger("Thread worker is running\n")

        while s.server.th_run:
            try: 
                (client, cmdid, data) = s.server.cmdq.popleft()
                s.server.logger("Thread: recerved cmd " + str(cmdid) + "\n")

                cmd = s.cmds[cmdid]
                rcmdid = 128+cmdid if cmdid < 128 else cmdid

                ret = cmd(client, data)

                if isinstance(ret, types.GeneratorType):
                    for l in ret:
                        s.server.logger("Cmd id returned: " + str(rcmdid) +" " + str(len(l)) + " \n")
                        if isinstance(l, list):
                            for m in l:
                                if m > '': s.server.send_packet_data(client['address'], client['port'], rcmdid, m)
                        elif isinstance(l, str):
                            if l > '': s.server.send_packet_data(client['address'], client['port'], rcmdid, l)
                elif isinstance(ret, str) and ret > '':
                    s.server.send_packet_data(client['address'], client['port'], rcmdid, ret)
                elif isinstance(ret, list) and len(list)>0:
                    for l in ret:
                        s.server.send_packet_data(client['address'], client['port'], rcmdid, l)

            except IndexError:
                pass
            sleep(0.01)
