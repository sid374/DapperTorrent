import bencode
import requests
import hashlib
import struct
import socket
from urlparse import urlparse
import random
import logging
import pdb

PEER_ID = "SB374374374374374374"

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    metadata = Metadata('mazerunner.torrent')
    metadata.connectToTrackers()

    print("HELOEOJFOJSFAOSJFOASJFOAJS")

def connectionIdRequestMessage():
        connection_id = struct.pack('>Q', 0x41727101980)
        action = struct.pack('>I', 0)
        trans_id = struct.pack('>I', random.randint(0, 100000))
        return connection_id+action+trans_id, action, trans_id

def announceRequestMessage(connection_id, info_hash):
        action = struct.pack('>I', 1)
        trans_id = struct.pack('>I', random.randint(0, 100000))
        downloaded = struct.pack('>Q', 0)
        left = struct.pack('>Q', 0)
        uploaded = struct.pack('>Q', 0)
        event = struct.pack('>I', 0)
        ip = struct.pack('>I', 0)
        key = struct.pack('>I', 0)
        num_want = struct.pack('>i', -1)
        port = struct.pack('>h', 8000)

        return connection_id+action+trans_id+info_hash.digest()+PEER_ID+downloaded+left+uploaded+event+ip+key+num_want+port, action, trans_id

def getPeersFromAnnounce(response, metadata):
    ipResponse = response[20:]
    numIPs = len(ipResponse)/6
    #f = open("Peers.txt", 'a+')
    for i in range(numIPs):
        chunk = ipResponse[i*6:i*6+6]
        ip = []
        for j in range(4):
            #pdb.set_trace()
            ip.append(str(ord(chunk[j])))
        port = ord(chunk[4])*256+ord(chunk[5])
        ipString = '.'.join(ip)
        peer = Peer(ipString, port)
        metadata.addPeer(peer)
        #f.write(ipString+" ")
        #f.write(str(port)+"\n")
        logging.debug("IP = %s, Port = %d", ipString, port)

def sendUdpMessage(sock, conn, msg, action, trans_id, numTries, size):
    """
    Sends the udp message and then immediately waits for the response.
    If the response times out or is incorrect we only retry 2 times
    Returns the response
    """
    sock.sendto(msg, conn)
    try:
        response = sock.recvfrom(2048)
    except socket.timeout as err:
        logging.debug(err)
        logging.debug('Connecting again')
        if numTries >= 2: return False
        numTries += 1
        return sendUdpMessage(sock, conn, msg, action, trans_id, numTries, size)
    if len(response[0]) < 16:
        logging.debug("Short Response, Retrying")
        if numTries >= 2: return False
        numTries += 1
        return sendUdpMessage(sock, conn, msg, action, trans_id, numTries, size)
    if action != response[0][0:4] or trans_id != response[0][4:8]:
        logging.debug("Action/trans_id not matching")
        if numTries >= 2: return False
        numTries += 1
        return sendUdpMessage(sock, conn, msg, action, trans_id, numTries, size)
    return response[0]


def initUdpTracker(trackerUrl, info_hash, metadata):
    """
    Sends the connect request and the announce request to the tracker
    """
    parsed =  urlparse(trackerUrl)
    try:
        ip = socket.gethostbyname(parsed.hostname) #TODO: Try except for socket.gaierror: [Errno 8] nodename nor servname provided, or not known
    except:
        logging.debug("Error occured while connecting to host. Invalid hostname")
        return
    conn = (ip, parsed.port)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(1)
    msg, action, trans_id = connectionIdRequestMessage()
    response = sendUdpMessage(sock, conn, msg, action, trans_id, 0, 16)
    if response:
        logging.debug("Connection succesfull. Connection id= %s",response)
        connection_id = response[8:16]
        msg, action, trans_id = announceRequestMessage(connection_id, info_hash)
        response = sendUdpMessage(sock, conn, msg, action, trans_id, 0, 20)
        if response:
            logging.debug("Announce Sucessfull")
            getPeersFromAnnounce(response, metadata)




class Metadata:
    def __init__(self, torrentFileName):
        self.metadata = bencode.bdecode(open('mazerunner.torrent', 'rb').read())
        self.bencodedInfo = bencode.bencode(self.metadata['info'])
        self.info_hash = hashlib.sha1(self.bencodedInfo)
        self.peers = []

    def addPeer(self, peer):
        self.peers.append(peer)


    def connectToTrackers(self):
        for tracker in self.metadata['announce-list']:
            tracker = tracker[0]
            if tracker.startswith('udp'):
                initUdpTracker(tracker, self.info_hash, self)


class Peer:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port

if __name__ == "__main__": main()





