from CRP import *
import argparse
import sys
import threading
def listen_cmd():
    live = True
    while live:
        print "Please enter a command ('help' for manual and 'exit' to quit):"
        command = raw_input()
        command = command.strip().lower()
        if command == 'help':
            print "--------------------------- Commands Manual ---------------------------"
            print "terminate: \n\t disconnect from the FTA-server"
            print "window W: \n\t W: the maximum receiver's window-size at the FTA-Client (in segments)"
            print '-----------------------------------------------------------------------\n'

        if command == 'exit':
            live = False
            sys.exit(0)

        if command.split(' ')[0] == 'window':
            server.set_window_size(int(command.split(' ')[1]))

        if command =='terminate':
            live =False
            server.close()

server = CRP()
parser = argparse.ArgumentParser()
parser.add_argument("X", help="the UDP port number of FTA-Server", type=int)
args = parser.parse_args()
port = args.X
if port < 0  or port > 65535:
    print "invalid port number"
    sys.exit(1)

tserver = threading.Thread(target = server.setupServer ,args=[port,0])
tlistener = threading.Thread(target = listen_cmd)
tlistener.start()
tserver.start()






