# Author: Shaohui Xu, Xinnan Du

BYTE_SIZE = 8
FLETCHER_CONFIG = (16, 32, 64)
PACKET_HEADER = ("sourcePort", "destPort", "seqNum", "ackNum", "headerLen", "ack", "rst", "syn", "fin", "recvWindowSize", "checksum")

def str2Bits(s):
    """
        Convert string to bits (represented using binary string)
    """
    bits = ''
    bitMask = '00000000'
    for c in s:
        charBits = bin(ord(c))[2:]
        charBits = bitMask[len(charBits):] + charBits
        bits = bits + charBits
    return bits

def bits2Str(bits, byteLength):
    """
        Convert bits represetned using bianry string to normal string
        Args:
            bits: binary string
            byteLength: length of expected output string
    """
    charList = []
    if len(bits) <= byteLength * BYTE_SIZE:
        bits = str('0' * (byteLength * BYTE_SIZE - len(bits))) + bits 
    elif len(bits) > byteLength * BYTE_SIZE and byteLength != 0:
        bits = bits[-byteLength * BYTE_SIZE]

    for idx in range(len(bits) / BYTE_SIZE):
        byte = bits[idx * BYTE_SIZE: (idx+1) * BYTE_SIZE]
        charList.append(chr(int(''.join([str(bit) for bit in byte]), 2)))
    s = ''.join(charList)

    return s

def normalPacketSerialize(packet):
    """
        Serialize packet with all the fields filled (normalized packet)
    """
    packetString = ""
    packetString += bits2Str(str(bin(int(packet["sourcePort"])))[2:],2)
    packetString += bits2Str(str(bin(int(packet["destPort"])))[2:],2)
    packetString += bits2Str(str(bin(int(packet["seqNum"])))[2:],4)
    packetString += bits2Str(str(bin(int(packet["ackNum"])))[2:],4)
    packetString += bits2Str(str(bin(int(packet["headerLen"])))[2:] + str(bin(int(packet["ack"])))[2:] + str(bin(int(packet["rst"])))[2:] + str(bin(int(packet["syn"])))[2:] + str(bin(int(packet["fin"])))[2:], 1)
    packetString += bits2Str(str(bin(int(packet["recvWindowSize"])))[2:], 3)
    packetString += bits2Str(str(bin(int(packet["checksum"])))[2:],4)
    if int(packet["headerLen"]) != 0:
        packetString += bits2Str(str(bin(int(packet["option"])))[2:], int(packet["headerLen"]) * 4)
    if "data" in packet:
        packetString += packet["data"]
    return packetString

def packetSerialize(packet):
    """
        Serialize any packet, it will first do the normalization then serialization
        Args:
            packet: packet in the form of dictionary
        Returns:
            packetString: packet in the from of binary string
    """
    packetString = ""
    try:
        # normalize header with empty fields
        for field in PACKET_HEADER:
            if field not in packet:
                packet[field] = 0
        packetString = normalPacketSerialize(packet)
    except:
        print "Unexpected error in crp packet serialization"
        raise
    return packetString

def packetDeserialize(packetString):
    """
        Deserialize any packet string
        Args:
            packetString: packet in the form of string
        Returns:
            packet: packet in the from of dictionary
    """
    packet = {}
    try:
        packetBitString = str2Bits(packetString)
        packet["sourcePort"] = int(packetBitString[0:16], 2)
        packet["destPort"] = int(packetBitString[16:32], 2)
        packet["seqNum"] = int(packetBitString[32:64], 2)
        packet["ackNum"] = int(packetBitString[64:96], 2)
        packet["headerLen"] = int(packetBitString[96:100], 2)
        packet["ack"] = int(packetBitString[100:101], 2)
        packet["rst"] = int(packetBitString[101:102], 2)
        packet["syn"] = int(packetBitString[102:103], 2)
        packet["fin"] = int(packetBitString[103:104], 2)
        packet["recvWindowSize"] = int(packetBitString[104:128], 2)
        packet["checksum"] = int(packetBitString[128:160], 2)
        if packet["headerLen"] != 0:
            packet["option"] = int(packetBitString[160: (160 + packet["headerLen"]*4*BYTE_SIZE)], 2)
        else:
            packet["option"] = 0;
        packet["data"] = packetString[20 + packet["headerLen"] * 4:]
    except:
        print "Unexpected error in crp packet string deserialization"
        raise
    return packet

def updateChecksum(packetString, k):
    """
        Fletcher CheckSum Update
        Update packet string after performing checksum
        Args:
            packetString: packet in the form of binary string
            k: flecher constant
    """
    checksum = bits2Str(str(bin(int(fletcherCheckSum(packetString, k))))[2:], 4)
    return packetString[:16] + checksum + packetString[20:]

def fletcherCheckSum(packetString, k):
    """
        Fletcher CheckSum
        More details can be found on http://www.drdobbs.com/database/fletchers-checksum/184408761
        Args:
            packetString: packet in the form of binary string
            k: flecher constant
    """
    packetString = packetString[:16] + packetString[20:]
    if k not in FLETCHER_CONFIG:
        raise ValueError("Valid choices of k should be 16, 32 and 64")
    sum1 = 0
    sum2 = 0
    count = len(packetString)/k
    for index in range(count):
        tempSum = 0
        for char in packetString[index*k:(index+1)*k]:
            tempSum += ord(char)
        sum1 = (sum1 + tempSum)%255
        sum2 = (sum2+sum1)%255

    return (sum2 << 24) | (sum1 << 8)

def make8bit(string):
    zeros = ''
    if len(string) != 8:
        compensate = 8 - len(string)
        for x in range(0,compensate):
            zeros += "0"
    return zeros+string

class Queue():
    """
        Self defined queue class
    """
    def __init__(self):
        self.list = []

    def push(self,item):
        # Enqueue the 'item' into the queue
        self.list.insert(0,item)

    def pop(self):
        # Dequeue the earliest enqueued item still in the queue. This operation removes the item from the queue.
        return self.list.pop()

    def push_front(self,item):
        self.list.append(item)

    def isEmpty(self):
        # Returns true if the queue is empty"
        return len(self.list) == 0

    def insert_inorder(self,item):
        self.list.append(item)
        self.list.sort(key=lambda x: x['seqNum'],reverse=True) 

    def remove(self, pos):
        return self.list.pop(pos)

    def length(self):
        return len(self.list)

    def getList(self):
        # List getter for iteration
        return self.list

def get_zeros():
    result = ''
    for i in range(0,1004):
        result += " "
    return result

def print_received_packet(packet):
    print "Receive with SequenceNum: ", packet["seqNum"]," ackNum: ",packet["ackNum"], " ack_bit: ",packet["ack"], " fin: ", packet['fin']

if __name__ == "__main__":
    packet = dict()
    packet["sourcePort"] = 1000
    packet["destPort"] = 1200
    packet["seqNum"] = 1
    packet["data"] = ""
    sendString = packetSerialize(packet)
    getString = packetDeserialize(sendString)
    checksum = fletcherCheckSum("sendStringdhcsbchdsgcbdshgcdsuhuhuhuhbchdsgcbdsyuyvtfvtcdc",16)
    # checksum = fletcherCheckSum("hahaha",16)
    print checksum
