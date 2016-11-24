from CRP import *
import argparse
import sys
client = CRP()
parser = argparse.ArgumentParser()
parser.add_argument("A", help="the IP address of FTA-Server")
parser.add_argument("P", help="the UDP port number of FTA-Server", type=int)
args = parser.parse_args()
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
        client.connectTo(10, args.A, args.P)

    if command == 'disconnect':
        client.close()
        keepAlive = False
        sys.exit(0)

    if command.split(' ')[0] == 'get':
	filename = command.split(' ')[1]
        print command
        packetData = 'get ' + filename + fileTerminator
        packetHeader = dict()
        client._sendPacket(packetData, packetHeader)
        isDone = False
        currentMessage = ""
        while not isDone:
            data = client.readData(fileTerminator)
            currentMessage += data
            if fileTerminator in data:
                currentMessage = currentMessage[0:currentMessage.index(fileTerminator)]+currentMessage[currentMessage.index(fileTerminator)+1:]
                currentMessage = currentMessage.strip()
                f = open(filename,'w')
                f.write(currentMessage)
                f.close()
                isDone = True

    if command.split(' ')[0] == 'post':
    	filename = command.split(' ')[1]
        f = open(filename, 'r')
        file = filename + '\n' + f.read() + fileTerminator
        client.push_file_to_sending_queue(file)

    # TODO: add windows size setup after merging
	if command.split(' ')[0] == 'window':
		w = int(command.split(' ')[1])
        server.set_window_size(w)
