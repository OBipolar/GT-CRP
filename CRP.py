import socket
from crpPacket import *
import threading
import sys
import time
import netaddr

class CRP:

    def __init__(self):
    	self.sendingQueue = Queue()
    	self.notAckedQueue = Queue() # [packetString, timeStamp]
    	self.receiveBUffer = Queue()
    	self.packetSize = 1024
    	self.buffsize = 4096
    	self.portNum = None
    	self.IP = socket.gethostbyname(socket.gethostname())
    	self.destination = None #[addr, port]
    	self.dataSocket.settimeout(30) #timeout for whole connection
    	self.sender_seqNum = 0
    	self.receiver_seqNum
    	self.close = False
    	self.ackedNum = set()

    """
        Establish socket for incoming connection
    """
    def setupServer(self,port):
    	self.dataSocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
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
                self.timeout = 2 #init timeout for packet resend is 2 seconds

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
    	while 1:
            time.sleep(0.5)
            if not self.sendingQueue.isEmpty:
                packetString = self.sendingQueue.pop()
                packet = packetDeserialize(packetString)
                # ------------DEBUG INFO--------------    
                pprint("SENT: seq=" + str(packet["seqNum"]) + " ackNum=" + str(packet["ackNum"]) + " ack=" + str(packet["ack"]) + " fin=" + str(packet["fin"]))
                pprint("TO: addr=" + str(self.destination[0]) + " port=" + str(self.destination[1]))  
                # ------------END DEBUG INFO--------------
                self.dataSocket.sendto(packetString, self.destination[0])
                if packet["seqNum"] != 0:
                    self.notAckedQueue.push((packetString, time.time()))

    def receiver(self):
    	pass

    #this is used for send individual packet, used for receiver
    def _sendPacket(self, data, header):
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

    """
        Establish connection from client to server
        Supports both IPv4 and IPv6
    """
    def connectTo(self, selfPort, serverIP, serverPort, initialPacketSizeInByte = 1024):
        if netaddr.valid_ipv4(serverIP):
            self.dataSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        elif netaddr.valid_ipv6(serverIP):
            self.dataSocket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)            
        else:
            print ("IP Address not valid")
            break
        listen_addr = ("", selfPort)
        self.dataSocket.bind(listen_addr)
        # Init data socket
        self.portNum = selfPort
        self.destination = (serverIP, serverPort)
        self.timeout = 2 #init timeout for packet resend is 2 seconds
        self._sendPacket(packetDeserialize(str(bin(initialPacketSizeInByte))[2:], 4), {"syn":1})
        ackPacketString = self._receive_packet()
        ackPacket = packetDeserialize(ackPacketString)
        if (ackPacket['checksum'] == fletcherCheckSum(ackPacketString,16) and ackPacket['syn'] == 1 and ackPacket['ack'] == 1):
            self._sendPacket("", {"ack": 1})
            # ------------FINISH THREE WAY HANDSHAKE--------------
            tSender = threading.Thread(target=self.sender)
            tSender.daemon = True
            tSender.start()
            tListener = threading.Thread(target=self.receiver)
            tListener.daemon = True
            tListener.start()

    def close(self):
    	pass

