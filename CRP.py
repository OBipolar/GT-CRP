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
        self.expectedSeqNum = 0 # expected sequence number in buffer
    	self.packetSize = 1024
        self.receiver_windowSize = 20
        self.send_windowSize = 20
    	self.portNum = None
    	self.IP = socket.gethostbyname(socket.gethostname())#get self IP address
    	self.destination = None #[addr, port]
    	self.sender_seqNum = 0 #sequence number associated with sending queue
    	self.receiver_seqNum = 0 #ACK sequence number
    	self.ready_for_close = False
    	self.ackedNum = dict()
        self.receivedSeqNum = []
        self.readSeqNum = 0
        self.lock = threading.Lock()
        self.normalClose = None

    def setupServer(self,port,IPV6):
        #three way handshake of receiver
        if IPV6:
            self.dataSocket = socket.socket(socket.AF_INET6,socket.SOCK_DGRAM)
        else:
    	    self.dataSocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.dataSocket.settimeout(100) #timeout for whole connection
        listen_addr = ("", port)
        self.dataSocket.bind(listen_addr)
        print "server listening on port " , port
    	while True:
            time.sleep(1)
    	    data, addr = self.dataSocket.recvfrom(self.packetSize)
            synPacketDictFromClient = packetDeserialize(data)
            # Three way handshake start---------------------------------------- 
            if (synPacketDictFromClient['checksum'] == fletcherCheckSum(data["data"],16) and synPacketDictFromClient['syn'] == 1):
                # create new
                self.portNum = port #port listening
                self.destination = addr #send packet to destination
                self.timeout = 2 #init timeout for packet resend is 2 seconds

                # send ack back to client
                self._sendPacket("", {"ack": 1, "syn":1})

                # # wait for ack from client
                ackFromClient = self._receivePacket()
                ackFromClientDict = packetDeserialize(ackFromClient)
                if (ackFromClientDict['checksum'] == fletcherCheckSum(data,16) and ackFromClientDict['ack'] == 1):
                    print "BOOM! Shakalaka: " + str(addr[1])
                    # ------------FINISH THREE WAY HANDSHAKE--------------#
                    tSender = threading.Thread(target=self.sender)
                    tSender.daemon = True
                    tSender.start()
                    tListener = threading.Thread(target=self.receiver)
                    tListener.daemon = True
                    tListener.start()
                    tcheck_timeout = threading.Thread(target=self.check_timeout_resend)
                    tcheck_timeout.daemon = True
                    tcheck_timeout.start()
                    tSender.join()
                    tListener.join()
                    tcheck_timeout.join()

    def sender(self):
    	while 1:
            time.sleep(0.5)
            if not self.sendingQueue.isEmpty(): # TODO: check if notackqueue has space using windowsize 
                packet = self.sendingQueue.pop()
                # ------------DEBUG INFO--------------    
                pprint("SENT: seq=" + str(packet["seqNum"]) + " ackNum=" + str(packet["ackNum"]) + " ack=" + str(packet["ack"]) + " fin=" + str(packet["fin"]))
                pprint("TO: addr=" + str(self.destination[0]) + " port=" + str(self.destination[1]))  
                # ------------END DEBUG INFO--------------
                self.dataSocket.sendto(packetString, self.destination[0])
                if packet["seqNum"] != 0:
                    self.notAckedQueue.push([packetString, time.time()]) # TODO: resend if packet in notAckedQueue exceed timeout 


    def receiver(self):
    	while 1:
            try:
                time.sleep(0.5)
            except socket.timeout:
                print "connection timeout"#a connection cannot exeet the timeout limit
                self.receiver_close()
            print 'waiting for response'
            dataString, addr = self.dataSocket.recvfrom(self.packetSize)
            data = packetDeserialize(dataString)
            print "Receive with SequenceNum: ", data["seqNum"]," ackNum: ",data["ackNum"], " ack_bit: ",data["ack"], " fin: ", data[fin]

            #check sum
            if data["checksum"] ==  fletcherCheckSum(data["data"],16):
                #the other side send ackNum = desired SequenceNum
                #when ack is 1, whcih means CRP previously sent something
                #case 1: NACK-------------------------------------------- 
                if data["ack"] == 1 and data["rst"] == 1:
                    for index, notAckPacket in enumerate(self.notAckedQueue.list):
                        if notAckPacket[0]["seqNum"] == data["ackNum"]:
                            mypacket = self.notAckedQueue.remove(index)
                            mypacket[1] = time.time()
                            self.sendingQueue.push_front(mypacket)
                            break
                #case 2: empty ACK packet--------------------------------
                if data['ack'] == 1 and len(data['data'].strip()) == 0:
                    if str(data['ackNum']) in self.ackedNum:
                        self.ackedNum[str(data['ackNum'])] += 1
                    else:
                        self.ackedNum[str(data['ackNum'])] = 1
                    #remove the acked packet from the notAckedQueue
                    if self.ackedNum[str(data['ackNum'])] == 1:
                        for index, packet in enumerate(self.notAckedQueue.list):
                            if packet['seqNum'] == data["ackedNum"] - 1:
                                self.notAckedQueue.remove(index)
                                break
                    self._check_nackQueue_retransmit()
                #case 3 Data and ACK-------------------------------------
                elif data['ack'] == 1 and len(data['data'].strip()) > 0:
                    if str(data['ackNum']) in self.ackedNum:
                        self.ackedNum[str(data['ackNum'])] += 1
                    else:
                        self.ackedNum[str(data['ackNum'])] = 1
                    #remove the acked packet from the notAckedQueue
                    if self.ackedNum[str(data['ackNum'])] == 1:
                        for index, packet in enumerate(self.notAckedQueue.list):
                            if packet[0]['seqNum'] == data["ackedNum"] - 1:
                                self.notAckedQueue.remove(index)
                                break
                    self._check_nackQueue_retransmit()
                    self._push_to_Buffer(data)
                    self._check_buffer_send_Ack(data)
                #case 4 only data, no ACK--------------------------------
                elif data['ack'] == 0 and len(data['data'].strip()) > 0:
                    self._push_to_Buffer(data)
                    self._check_buffer_send_Ack(data)
                #case 5 finish connection-------------------------------
                elif data['fin'] == 1:
                    self._send_ack(data)
                    self.ready_for_close = True
                    self.receiver_close()
                else:
                    print "wrong packet sent"
            else:
                if len(data['data'].strip()) > 0:
                    self.receiver_seqNum += 1
                    self._send_NACK(data["seqNum"]) #ack and rst means NACK
                    
                
    
    def _send_NACK(self,seqNum):
        self.receivedSeqNum += 1
        self._sendPacket("", {"ack": 1, "rst":1, "ackNum": seqNum})

    def _check_buffer_send_Ack(self,data):
        seqNuminBuff = [x['seqNum'] for x in self.receiveBUffer]

        if data['seqNum'] == self.expectedSeqNum:
            self.lock.require()
            dataIndex = self.receiveBUffer.index(data['seqNum'])
            if len(self.receiveBUffer.list)==1:
                self.expectedSeqNum+=1
            elif self.receiveBUffer.list[dataIndex + 1]['seqNum']  -self.expectedSeqNum >1:
                self.expectedSeqNum+=1
            else:
                findBreak = False
                for i in range(0,len(seqNuminBuff)-1):
                    if seqNuminBuff[i] + 1 != seqNuminBuff[i+1]:
                        self.expectedSeqNum = seqNuminBuff[i] + 1
                        findBreak = True
                        break
                if not findBreak:
                    self.expectedSeqNum = max(seqNuminBuff)+1
            self._send_ack(self.expectedSeqNum)
            self.lock.release()
        else:
            self._send_ack(self.expectedSeqNum)

        

    def _piggy_backing_send_ack(self,Mypacket):
        '''
        piggy backing send ack, attach ack to a packet we are going to send
        '''
        findOne = False
        for index, packet in enumerate(self.sendingQueue.list):
            if packet["ack"] == 0:
                packet["ack"] = 1
                packet["ackNum"] = Mypacket["seqNum"] + 1
                findOne = True
                break
        if not findOne:
            self._send_ack(Mypacket["seqNum"]+1)

    def _send_ack(self, seqNum):
        self.receivedSeqNum += 1
        rtpPacketDict["sourcePort"] = self.port
        rtpPacketDict["destPort"] = self.destAddr[1]
        self._sendPacket("",{"ackNum":seqNum, "seqNum":self.receivedSeqNum})


    def _push_to_Buffer(self,data):
        if self.receiveBUffer.length() >= self.receiver_windowSize:
            return False
        if data["seqNum"] < expectedSeqNum or data["seqNum"] >= self.expectedSeqNum+self.receiver_windowSize:
            return False
        self.receiveBUffer.insert_inorder(data)#may should be inverse
        return True

    def _check_nackQueue_retransmit(self):
        for key, value in self.ackedNum.iteritems():
            if value >= 3:
                for index, notAckPacket in enumerate(self.notAckedQueue.list):
                    if notAckPacket["seqNum"] == key:
                        mypacket = self.notAckedQueue.remove(index)
                        mypacket[1] = time.time()
                        self.sendingQueue.push_front(mypacket)
                        self.ackedNum[key] = 0
            
    #this is used for send individual packet, used for receiver
    def _sendPacket(self, data,header):
    	packet = dict()
    	packet["sourcePort"] = self.portNum
    	packet["destPort"] = self.destination[1]
    	packet["data"] = data
    	packet["checksum"] = fletcherCheckSum(data,16)
        
    	for key in header:
    		packet[key] = header[key]
    	sendString = packetSerialize(packet)

    	self.dataSocket.sendto(sendString,self.destination)

    	

    def _receive_packet(self):
    	return self.dataSocket.recvfrom(self.packetSize)[0]

    def readData(self, terminator):
        data = ""
    	if not self.receiveBUffer.empty():
            topPacket = self.receiveBUffer.get()
            if topPacket["seqNum"] == self.readSeqNum:
                done = False
                nextSeqNum = self.readSeqNum + self.packetSize
                data += topPacket["data"]
                while not done:
                    nextPacket = self.receiveBUffer.get()
                    if nextPacket["seqNum"] == nextSeqNum:
                        data += nextPacket["data"]
                        if terminator in data:
                            done = True
                        nextSeqNum = nextSeqNum + self.packetSize
                    else:
                        done = True
                        self.receiveBUffer.put(nextPacket)
                self.readSeqNum = nextSeqNum
                return data
        return data

    def connectTo(self, selfPort, serverIP, serverPort):
    	if netaddr.valid_ipv4(serverIP):
            self.dataSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        elif netaddr.valid_ipv6(serverIP):
            self.dataSocket = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        else:
            print ("IP Address not valid")
            raise
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
            tcheck_timeout = threading.Thread(target=self.check_timeout_resend)
            tcheck_timeout.daemon = True
            tcheck_timeout.start()
            tSender.join()
            tListener.join()
            tcheck_timeout.join()



    def receiver_close(self):
        """
            Called by server to close the connection
        """
        self.receivedSeqNum += 1
        self._sendPacket(data, {"fin": 1, "seqNum":self.receivedSeqNum})
        packet = self.dataSocket.recvfrom(self.packetSize)
        packet = packetDeserialize(packet)
        if(packet["ack"] == 1):
            print "close connection"
            sys.exit(0)

    def close(self):
        """
            Called by client to close the connection 
        """
        # Create finish packet 
        if not self.ready_for_close:
            finPacket = {
                "sourcePort": self.portNum,
                "destPort": self.destination[1],
                "seqNum": 0,
                "fin": 1
                }
            self._sendPacket("", finPacket)
            packet1,addr = self.dataSocket.recvfrom(self.packetSize)
            time.sleep(1)
            packet2, addr = self.dataSocket.recvfrom(self.packetSize)
            packet1 = packetDeserialize(packet1)
            packet2 = packetDeserialize(packet2)
            if(packet1['ack'] == 1 and packet2['fin'] == 1):
                self._send_ack(packet2['seqNum']+1)
            print("CLOSED")
            sys.exit(0)

    def check_timeout_resend(self):
        while(True):
            if self.ready_for_close:
                break
            time.sleep(0.1)
            if self.notAckedQueue.isEmpty():
                continue
            for index, packet in enumerate(self.notAckedQueue.list):
                if time.time() - packet[1] > self.timeout:
                    packet = self.notAckedQueue.remove(index)
                    packet[1] = time.time()
                    self.sendingQueue.push_front(packet)
                
    def set_window_size(self,size):
        if size > 0:
            self.windowsize = size
        
        
                
