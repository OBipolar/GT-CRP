import socket
from crpPacket import *
import threading
import sys
import time
class CRP:

    def __init__(self):
    	self.sendingQueue = Queue()
    	self.notAckedQueue = Queue()
    	self.receiveBUffer = Queue()
    	self.packetSize = 1024
    	self.buffsize = 4096
    	self.portNum = None
    	self.IP = socket.gethostbyname(socket.gethostname())
    	self destination = None
    	self.sender_seqNum = 0
    	self.receiver_seqNum
    	self.close = False
    	self.ackedNum = set()

    def setupServer(self,port):
    	self.dataSocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM) #init data socket
        self.dataSocket.settimeout(30) #timeout for whole connection
        listen_addr = (self.IP, port)
        self.dataSocket.bind(listen_addr)
    	while True:
    	    data, addr = self.dataSocket.recvfrom(24)
            synPacketDictFromClient = packetDeserialize(data)
            # print "get initail syn!"
            if (synPacketDictFromClient['checksum'] == fletcherCheckSum(data,16) and synPacketDictFromClient['syn'] == 1):
                # create new
                self.portNum = port
                self.destination = addr
                self.timeout = 2 #init timeout for packet resend is 2 seco`nds

                # send ack back to client
                self._sendPacket("", {"ack": 1})
                # # wait for ack from client
                ackFromClient = self._receivePacket()
                ackFromClientDict = packetDeserialize(ackFromClient)
                if (ackFromClientDict['checksum'] == fletcherCheckSum(data,16) and ackFromClientDict['ack'] == 1):
                    print "BOOM! Shakalaka: " + str(addr[1])
                    # ------------FINISH THREE WAY HANDSHAKE--------------
                    tSender = threading.Thread(target=self.sender)
                    tSender.daemon = True
                    tSender.start()
                    tListener = threading.Thread(target=self.receiver)
                    tListener.daemon = True
                    tListener.start()
                    tSender.join()
                    tListener.join()
    def sender(self):
    	pass

    def receiver(self):
    	pass
    #this is used for send individual packet, used for receiver
    def _sendPacket(self, data,header):
    	packet = dict()
    	packet["sourcePort"] = self.portNum
    	packet["destPort"] = self.destination[1]
    	packet["data"] = data
    	packet["checksum"] = fletcherCheckSum(data,16)

    	for key in header:
    		packet[key] = header[key]
    	sendString = normalPacketSerialize(packet)

    	self.dataSocket.sendto(sendString,self.destination)

    	

    def _receive_packet(self):
    	return self.dataSocket.recvfrom(self.packetSize)[0]

    def readData(self):
    	pass

    def connectTo(self, selfPort, serverIP, serverPort):
    	pass

    def close(self):
    	pass

