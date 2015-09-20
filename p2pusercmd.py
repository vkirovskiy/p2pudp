#!/usr/bin/env python

usercommands = ['help', 'write', '>', 'exec', 'connect', 'log', 'clients', 'testbuff', 'getfile', 'myid']

def user_console(s, data):
    r = str(data).strip().rstrip().split(" ")

    if r[0] in usercommands:
        if r[0] == 'help':
            print "Available commands:"
            for i in usercommands:
                print i 
        elif r[0] == 'connect':
            remoteid = r[1]
            print "Connecting to " + remoteid
            s.send_data(data="get " + remoteid)
            s.send_data(data="conn " + remoteid)

        elif r[0] == 'myid':
            print "ID: " + s.myid

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
