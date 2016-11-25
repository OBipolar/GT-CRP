from CRP import *
import argparse
import sys
import time
client = CRP()
parser = argparse.ArgumentParser()
parser.add_argument("A", help="the IP address of FTA-Server")
parser.add_argument("P", help="the UDP port number of FTA-Server", type=int)
parser.add_argument("d", help="debug mode", type=str)
args = parser.parse_args()
if args.d == 'd':
    client.debug == True
fileTerminator = "\0"
keepAlive = True

while keepAlive:
    print "Please enter a command ('help' for manual and 'exit' to quit):"
    command = raw_input()
    print '-----------------------------------------------------------------------\n'
    command = command.strip().lower()

    if command == 'help':
        print "--------------------------- Commands Manual ---------------------------"
        print "connect: \n\t connect to the FTA-server"
        print "disconnect: \n\t disconnect from the FTA-server"
        print "get F: \n\t downloads file F from the FTA-server"
        print "post F: \n\t uploads file F to the FTA-server"
        print "window W: \n\t W: the maximum receiver's window-size at the FTA-Client (in segments)"
        print '-----------------------------------------------------------------------\n'

    if command == 'exit':
        print "exit"
        keepAlive = False
        sys.exit(0)

    if command == 'connect':
        tclient = threading.Thread(target = client.connectTo, args=[10, args.A, args.P])
        tclient.start()

    if command == 'disconnect':
        client.close()

    if command.split(' ')[0] == 'get':
        filename = command.split(' ')[1]
        print "gonna get ", filename
        packetData = 'get ' + filename + fileTerminator
        packetHeader = dict()
        client._sendPacket(packetData, {'rst':1})
        isDone = False
        f = open("download-" + filename,'w')
        currentMessage = ""
        while not isDone:
            data = client.readData(fileTerminator)
            time.sleep(0.3)
            currentMessage += data
            if fileTerminator in data:
                currentMessage = currentMessage[0:currentMessage.index(fileTerminator)]+currentMessage[currentMessage.index(fileTerminator)+1:]
                currentMessage = currentMessage.strip()
                isDone = True
                print "write to file"
                if client.debug:
                    print currentMessage
                f.write(currentMessage)
                f.close()

    if command.split(' ')[0] == 'post':
        packetData = 'post ' + command.split(' ')[1] + fileTerminator
        client._sendPacket(packetData, {'rst':1})
    	filename = command.split(' ')[1]
        f = open(filename, 'r')
        client.push_file_to_sending_queue(f)

    if command.split(' ')[0] == 'window':
        client.set_window_size(int(command.split(' ')[1]))
