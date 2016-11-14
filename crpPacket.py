# Author: Shaohui Xu

# CRP Packet Serializer and Deserializer
# Together with Util functions

BYTE_SIZE = 8
FLETCHER_CONFIG = (16, 32, 64)

# TODO: documentation

def str2Bits(s):
    bits = ''
    bitMask = '00000000'
    for c in s:
        charBits = bin(ord(c))[2:]
        charBits = bitMask[len(bits):] + charBits
        bits = bits + charBits
    return bits

def bits2Str(bits, byteLength):
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

# Serialize packet in dict form to a string
def packetSerialize(packet):

# Deserialize a packet in string form into dict
def packetDeserialize(packetString):

# Fletcher checksum
# More details can be found on http://www.drdobbs.com/database/fletchers-checksum/184408761
def fletcherCheckSum(packetString, k):
    if k not in FLETCHER_CONFIG:
        raise ValueError("Valid choices of k are 16, 32 and 64")
