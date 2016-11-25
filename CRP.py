import socket
from crpPacket import *
import threading
import sys
import time
import netaddr
import os

class CRP:

    def __init__(self):
    	self.sendingQueue = Queue()
    	self.notAckedQueue = Queue() # [packetString, timeStamp]
    	self.receiveBUffer = Queue()
        self.expectedSeqNum = 1 # expected sequence number in buffer
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
        self.receiverSeqNum = 0
        self.receivedSeqNum = set()
        self.readSeqNum = 0
        self.lock = threading.Lock()
        self.normalClose = None
        self.emptyZeros = bits2Str(str(bin(1024))[2:], 4)

    def setupServer(self,port,IPV6):
        """
            Server setup with listener and sender running in threads

            Args:
                port: port used by server
                IPV6: flag to determine whether a IPv6 address is used
        """
        if IPV6:
            self.dataSocket = socket.socket(socket.AF_INET6,socket.SOCK_DGRAM)
        else:
    	    self.dataSocket = socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
        self.dataSocket.settimeout(100) #timeout for whole connection
        listen_addr = ("", port)
        self.dataSocket.bind(listen_addr)
        print "server listening on port " , port
        data, addr = self.dataSocket.recvfrom(self.packetSize)
        synPacketDictFromClient = packetDeserialize(data)

        # Three way handshake start----------------------------------------
        if (synPacketDictFromClient['checksum'] == int(fletcherCheckSum(data[20:], 16)) and synPacketDictFromClient['syn'] == 1):
            # create new
            self.portNum = port #port listening
            self.destination = addr #send packet to destination
            self.timeout = 2 #init timeout for packet resend is 2 seconds

            # send ack back to client
            self._sendPacket("", {"ack": 1, "syn":1})

            # # wait for ack from client
            ackData = self._receive_packet()
            ackFromClientDict = packetDeserialize(ackData)
            if (ackFromClientDict['checksum'] == int(fletcherCheckSum(ackData[20:], 16)) and ackFromClientDict['ack'] == 1):
                print "BOOM! Shakalaka: " + str(addr[1])
                # ------------FINISH THREE WAY HANDSHAKE--------------#
                tSender = threading.Thread(target=self.sender)
                tListener = threading.Thread(target=self.receiver)
                tcheck_timeout = threading.Thread(target=self.check_timeout_resend)
                tListener.start()
                tSender.start()
                tcheck_timeout.start()

    def sender(self):
        """
            Sender thread

            Always running to check sending queue and send packets if necessary
        """
    	while 1:
            time.sleep(1)
            if not self.sendingQueue.isEmpty(): # TODO: check if notackqueue has space using windowsize 
                packet = self.sendingQueue.pop()
                packet["checksum"] = fletcherCheckSum(packet["data"],16)
                print "Sender now sending:"
                print packet
                packetString = packetSerialize(packet)
                packetString = updateChecksum(packetString, 16)
                print packetDeserialize(packetString)
                # ------------DEBUG INFO--------------
                print("SENT: seq=" + str(packet["seqNum"]) + " ackNum=" + str(packet["ackNum"]) + " ack=" + str(packet["ack"]) + " fin=" + str(packet["fin"]))
                print("TO: addr=" + str(self.destination[0]) + " port=" + str(self.destination[1]))  
                # ------------END DEBUG INFO--------------
                self.dataSocket.sendto(packetString, self.destination)
                if packet["seqNum"] != 0:
                    self.notAckedQueue.push([packet, time.time()]) # TODO: resend if packet in notAckedQueue exceed timeout 


    def receiver(self):
        """
            Receiver thread

            Always running to check incoming packets and respond
        """
    	while 1:
            try:
                time.sleep(0.5)
            except socket.timeout:
                print "connection timeout"#a connection cannot exeet the timeout limit
                self.close()
            print 'waiting for response'
            dataString, addr = self.dataSocket.recvfrom(self.packetSize)
            data = packetDeserialize(dataString)
            print data
            print "Receive with SequenceNum: ", data["seqNum"]," ackNum: ",data["ackNum"], " ack_bit: ",data["ack"], " fin: ", data['fin']
            #check sum
            if data["checksum"] ==  int(fletcherCheckSum(data["data"],16)):

                #the other side send ackNum = desired SequenceNum
                #when ack is 1, whcih means CRP previously sent something

                #case 1: NACK--------------------------------------------
                if data["ack"] == 1 and data["rst"] == 1 and data['fin'] == 0:
                    print "case 1: NACK"
                    for index, notAckPacket in enumerate(self.notAckedQueue.list):
                        if notAckPacket[0]["seqNum"] == data["ackNum"]:
                            mypacket = self.notAckedQueue.remove(index)
                            mypacket[1] = time.time()
                            self.sendingQueue.push_front(mypacket)
                            break

                #case 2: empty ACK packet--------------------------------
                elif data['ack'] == 1 and len(data['data'].strip()) == 0 and data['fin'] == 0 and data['rst'] == 0:
                    print "case 2: empty data with ack"
                    if str(data['ackNum']) in self.ackedNum:
                        self.ackedNum[str(data['ackNum'])] += 1
                    else:
                        self.ackedNum[str(data['ackNum'])] = 1
                    #remove the acked packet from the notAckedQueue
                    if self.ackedNum[str(data['ackNum'])] == 1:
                        for index, packet in enumerate(self.notAckedQueue.list):
                            if packet[0]['seqNum'] == data["ackNum"] - 1:
                                self.notAckedQueue.remove(index)
                                print "remove packet with seqNum ", packet[0]['seqNum']
                                break
                    self._check_nackQueue_retransmit()

                #case 3 Data and ACK-------------------------------------
                elif data['ack'] == 1 and len(data['data'].strip()) > 0 and data['fin'] == 0 and data['rst'] == 0:
                    print "case 3 data and ack"
                    if str(data['ackNum']) in self.ackedNum:
                        self.ackedNum[str(data['ackNum'])] += 1
                    else:
                        self.ackedNum[str(data['ackNum'])] = 1
                    #remove the acked packet from the notAckedQueue
                    if self.ackedNum[str(data['ackNum'])] == 1:
                        for index, packet in enumerate(self.notAckedQueue.list):
                            if packet[0]['seqNum'] == data["ackNum"] - 1:
                                self.notAckedQueue.remove(index)
                                print "remove packet with seqNum ", packet[0]['seqNum']
                                break
                    self._check_nackQueue_retransmit()
                    if data['seqNum'] not in  self.receivedSeqNum:
                        self._push_to_Buffer(data)
                        #self._send_ack(data['seqNum']+1)
                        self._check_buffer_send_Ack(data)

                #case 4 only data, no ACK--------------------------------
                elif data['ack'] == 0 and len(data['data'].strip()) > 0 and data['fin'] == 0 and data['rst'] == 0:
                    print "case 4, only data, no ACK"
                    if data['seqNum'] not in  self.receivedSeqNum:
                        self._push_to_Buffer(data)
                        #self._send_ack(data['seqNum']+1)
                        self._check_buffer_send_Ack(data)

                #case 5 finish connection-------------------------------
                elif data['fin'] == 1:
                    print "go into fin"
                    if self.ready_for_close:
                        self._sendPacket("", {'ack':1})
                        print("CLOSED")
                        sys.exit(0)
                    else:
                        self._sendPacket("", {'ack':1})
                        self.ready_for_close = True
                        self.receiver_close()
                        print "go out of fin"

                #case 6 data transfer-----------------------------------
                elif data['rst'] == 1:
                    print "transfer file"
                    operation, filename = data['data'].split(' ')
                    operation = operation.strip().lower()
                    filename = filename.strip()
                    if operation == 'push':
                        #TODO readdata
                        pass
                    elif operation == 'get':
                        files = [f for f in os.listdir('.') if os.path.isfile(f)]
                        filename = filename.strip('\x00')
                        if filename not in files:
                            print "can't find ",filename,  " in current directory"
                            self.close()
                        myfile = open(filename, 'r')
                        self.push_file_to_sending_queue(myfile)
                else:
                    print "wrong packet sent"
            else:
                print "checksum fails"
                if len(data['data'].strip()) > 0:
                    self.receiver_seqNum += 1
                    self._send_NACK(data["seqNum"]) #ack and rst means NACK


    def push_file_to_sending_queue(self, file):
        """
            push_file_to_sending_queue

            Read file and break into packet in sending queue

            Args:
                file: file to be sent
        """
        while True:
            fileString = file.read(1004)
            if fileString == "":
                break
            packet = dict()
            self.sender_seqNum += 1
            packet["seqNum"] = self.sender_seqNum
            packet["sourcePort"] = self.portNum
            packet["destPort"] = self.destination[1]
            packet["data"] = fileString
            self.sendingQueue.push(packet)

        endingPacket = dict()
        self.sender_seqNum += 1
        endingPacket["seqNum"] = self.sender_seqNum
        endingPacket["sourcePort"] = self.portNum
        endingPacket["destPort"] = self.destination[1]
        endingPacket["data"] = '\0'
        self.sendingQueue.push(endingPacket)


    def _send_NACK(self,seqNum):
        """
            _send_NACK

            Send nack for data retransmission, here we use ack bit plus rst bit as the signal of data retransmist

            Args:
                seqNum: seq num of packet to be retransmit
        """
        self.receiverSeqNum += 1
        self._sendPacket("", {"ack": 1, "rst":1, "ackNum": seqNum})

    def _check_buffer_send_Ack(self,data):
        seqNuminBuff = [x['seqNum'] for x in self.receiveBUffer.getList()]
        # if self.expectedSeqNum in seqNuminBuff:
        #     if not self.receiveBUffer.isEmpty():
        #         if len(seqNuminBuff) == 1:
        #             self._send_ack(self.receiveBUffer.list[0]['seqNum']-1)
        #         else:
        #             pos = 0
        #             for i in range(len(seqNuminBuff)-1,0,-1):
        #                 if(self.receiveBUffer.list[i]["seqNum"] - self.receiveBUffer.list[i-1]["seqNum"]) != -1:
        #                     pos = i
        #             self.expectedSeqNum = self.receiveBUffer.list[pos]['seqNum'] - 1
        #             self._send_ack(self.expectedSeqNum)
        #     else:
        #         self._send_ack(self.expectedSeqNum)
        # else:
        #     self._send_ack(self.expectedSeqNum)

        if data['seqNum'] == self.expectedSeqNum:
            dataIndex = seqNuminBuff.index(data['seqNum'])
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
        else:
            self._send_ack(self.expectedSeqNum)
        print "Send ack!!\n\n"


    def _piggy_backing_send_ack(self,Mypacket):
        """
            _piggy_backing_send_ack

            Patch ack bit to data packet and send the ack packet

            Args:
                Mypacket: packet to be sent ack with
        """
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
        self.receiverSeqNum += 1
        self._sendPacket("",{"ackNum":seqNum, "seqNum":self.receiverSeqNum, "ack": 1})

    def _push_to_Buffer(self,data):
        if self.receiveBUffer.length() >= self.receiver_windowSize:
            return False
        if data["seqNum"] < self.expectedSeqNum or data["seqNum"] >= self.expectedSeqNum+self.receiver_windowSize:
            return False
        self.receiveBUffer.insert_inorder(data)#may should be inverse
        return True

    def _check_nackQueue_retransmit(self):
        for key, value in self.ackedNum.iteritems():
            if value >= 3:
                for index, notAckPacket in enumerate(self.notAckedQueue.list):
                    if notAckPacket["seqNum"] <= key:
                        mypacket = self.notAckedQueue.remove(index)
                        self.sendingQueue.push_front(mypacket[0])
                        self.ackedNum[key] = 0

    def _sendPacket(self, data, header):
        """
            Called by sender to send a individual packet to receiver

            Args:
                data: value of packet's data field
                header: collection of packet's header
        """
    	packet = dict()
    	packet["sourcePort"] = self.portNum
    	packet["destPort"] = self.destination[1]
    	packet["data"] = data
    	packet["checksum"] = fletcherCheckSum(data,16)

    	for key in header:
    		packet[key] = header[key]
        print "sent: " ,packet
    	sendString = packetSerialize(packet)
        sendString = updateChecksum(sendString, 16)

    	self.dataSocket.sendto(sendString,self.destination)


    def _receive_packet(self):
    	return self.dataSocket.recvfrom(self.packetSize)[0]

    def readData(self, terminator):
        """
            Called by receiver to read data in the buffer

            Args:
                terminator: special character used to check whether reached the end of file
        """
        data = ""
        if not self.receiveBUffer.isEmpty():
            seqNuminBuff = [x['seqNum'] for x in self.receiveBUffer.getList()]
            if len(seqNuminBuff) == 1:
                tempString = self.receiveBUffer.pop()['data']
                print "in read data: " ,tempString
                data += tempString
            else:
                pos = 0
                for i in range(len(seqNuminBuff)-1,0,-1):
                    if(self.receiveBUffer.list[i]["seqNum"] - self.receiveBUffer.list[i-1]["seqNum"]) != -1:
                        pos = i
                        break
                for j in range(pos,len(seqNuminBuff)):
                    tempString = self.receiveBUffer.pop()['data']
                    print tempString
                    data += tempString
        return data

    def connectTo(self, selfPort, serverIP, serverPort, initialPacketSizeInByte=1024):
        """
            Called by client to create connection with server

            Args:
                selfPort: client's port
                serverIP: server's IP address
                serverPort: server's port
                initialPacketSizeInByte: packet size for window
        """
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
        self._sendPacket(bits2Str(str(bin(initialPacketSizeInByte))[2:], 4), {"syn":1})
        print "send inital syn packet"
        ackPacketString = self._receive_packet()
        ackPacket = packetDeserialize(ackPacketString)
        print "recevie inital ack packet"
        print ackPacket
        if (ackPacket['checksum'] == int(fletcherCheckSum(ackPacketString[20:],16)) and ackPacket['syn'] == 1 and ackPacket['ack'] == 1):
            self._sendPacket("", {"ack": 1})
            # ------------FINISH THREE WAY HANDSHAKE--------------
            tSender = threading.Thread(target=self.sender)
            tListener = threading.Thread(target=self.receiver)
            tcheck_timeout = threading.Thread(target=self.check_timeout_resend)
            tListener.start()
            tSender.start()
            tcheck_timeout.start()



    def receiver_close(self):
        """
            Called by server to close the connection
        """
        print "go in to receiver close"
        self.receiverSeqNum += 1
        time.sleep(1)
        self._sendPacket("", {"fin": 1, "seqNum":self.receiverSeqNum})
        print "receiver send packet with fin set to 1" 
        packet,addr = self.dataSocket.recvfrom(self.packetSize)
        packet = packetDeserialize(packet)
        print_received_packet(packet)
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
                "seqNum": self.sender_seqNum,
                "fin": 1
                }
            self._sendPacket("", finPacket)
            self.ready_for_close = True
        sys.exit(0)

    def check_timeout_resend(self):
        while(True):
            if self.ready_for_close:
                break
            time.sleep(2)
            if self.notAckedQueue.isEmpty():
                continue
            for index, packet in enumerate(self.notAckedQueue.list):
                if time.time() - packet[1] > self.timeout:
                    print "packet timeout"
                    packet = self.notAckedQueue.remove(index)
                    self.sendingQueue.push_front(packet[0])

    def set_window_size(self,size):
        if size > 0:
            self.windowsize = size

