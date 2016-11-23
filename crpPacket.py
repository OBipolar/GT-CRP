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
    s = ''
    charList = []

    if len(bits) <= byteLength * BYTE_SIZE:
        bits = str('0' * (byteLength * BYTE_SIZE - len(bits))) + bits 
    elif len(bits) > byteLength * BYTE_SIZE and byteLength != 0:
        bits = bits[-byteLength * BYTE_SIZE]

    for idx in range(len(bits) / BYTE_SIZE):
        byte = bits[idx * BYTE_SIZE: (idx+1) * BYTE_SIZE]
        charList.append(chr(int(''.join([str(bit) for bit in byte]), 2)))
    s = s.join(charList)

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

def fletcherCheckSum(packetString, k):
    """
        Fletcher CheckSum
        More details can be found on http://www.drdobbs.com/database/fletchers-checksum/184408761
        Args:
            packetString: packet in the form of binary string
            k: flecher constant
    """
    if k not in FLETCHER_CONFIG:
        raise ValueError("Valid choices of k should be 16, 32 and 64")
    sum1 = 0
    sum2 = 0
    count = len(packetString)/k
    for index in range(count):
        sum1 = (sum1 + packetString[count*k:(count+1)*k])%255
        sum2 = (sum2+sum1)%255
    sum1 = bin(sum1)[2:]
    sum2 = bin(sum2<<8)[2:]
    zero16 = "0000000000000000"
    return sum2+sum1+zero16

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
        self.list.sort(key=lambda x: x['seqNum']) 

    def remove(self, pos):
        return self.list.pop(pos)

    def length(self):
        return len(self.list)
