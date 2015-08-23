#!/usr/bin/env python

from os import popen
import sys

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


