#!/usr/bin/env python
#coding=utf-8

# units:
# data in kb
# time in seconds
# bandwidth in kb/s

from pprint import pprint
import sys
import getopt
import time
import queue
import threading
# for abstract classes
import abc
from abc import ABCMeta
from metrics import *

class Peer:
    # IDs conventions:
    # 0 for the proxy
    # from 1 to 1000 for VideoServers
    # from 1001 to infinity for the clients
    id = 0
    name = ""
    connection = None
    numPacket = 0

    receivedData = None

    def __init__(self, id, name=None):
        self.name = name or ""
        self.id = id

    def connectTo(self, peer):
        self.connection = Connection(peer)
        return self.connection

    # size in mb
    # protected
    def _packData(self, data, size = None, type = 'other', responseTo = None, chunkId = None, chunkSize = None):
        #TODO replace the plSize
        plSize = size or len(data)/10
        realData = {'sender':self.id, 'payload':data, 'plSize': plSize, 'plType': type, 'packetId': self.numPacket}
        self.numPacket += 1
        if responseTo != None:
            realData['responseTo'] = responseTo
        if chunkId != None:
            realData['chunkId'] = chunkId
            realData['chunkSize'] = chunkSize
        return realData

    def request(self, data, size = None, type = 'other'):
        realData = self._packData(data, size, type)
        self.connection.send(realData)

    def receivedCallback(self, data):
        self.receivedData = data
        print(self.name+" received data: "+str(data['payload'])+" from: "+str(data['sender']))

    def getID(self):
        return self.id

#unidirectional connection
class Connection:
    # bandwidth in kb/s
    # latency in seconds
    def __init__(self, peer=None, latency=2, bandwidth=1024, maxChunk=512):
        self.latency = latency
        # waiting queue for the packets, append() and popleft() are threadafe
        #self.queue = deque()
        self.bandwidth = bandwidth
        self.peer = peer
        self.maxChunk = maxChunk
        self.q = queue.Queue()
        self.t = threading.Thread(target=self.worker)
        self.t.daemon = True
        self.t.start()

    def connect(self, peer):
        if not self.peer:
            self.peer = peer
        else:
            #error
            print("error, already one peer")

    def setLag(self, latency=2):
        self.latency = latency
        return self

    def setBandwidth(self, bandwidth=1024):
        self.bandwidth = bandwidth
        return self

    def setMaxChunk(self, maxChunk=512):
        self.maxChunk = maxChunk
        return self

    # infinite loop running in a thread to simulate the time needed to send the data.
    # the thread gets the data to send from the Queue q, where the items have two fields:
    # - delay, how long the task is supposed to take
    # - data, the data to send, after the delay
    # private
    def worker(self):
        while True:
            item = self.q.get()
            data = item['data']
            mode = item['mode']
            if mode is 'normal':
                # we set the chunkId before it is updated in the item (in the if)
                data['chunkId'] = item['chunkId']

                # if the packet is too big, we split it
                if item['size'] > self.maxChunk:
                    data['chunkSize'] = self.maxChunk
                    item['chunkId'] += 1
                    item['size'] -= self.maxChunk
                    # and put the rest on the top of the queue, to have a round robin
                    self.q.put(item)
                # if not, we set the chunkSize to remaining size and don't split it
                else:
                    data['chunkSize'] = item['size']
                    data['lastChunk'] = True

            elif mode is 'forwardchunk':
                if 'chunkSize' not in data:
                    print("We got a problem with this chunk forwarding!")
                    data['chunkSize'] = item['size']

            elif mode is 'donotchunk':
                data['chunkId'] = 0
                data['chunkSize'] = item['size']
                data['lastChunk'] = True

            delay = self.latency+data['chunkSize']/self.bandwidth

            time.sleep(delay)
            self.peer.receivedCallback(data)
            self.q.task_done()

    def send(self, data, mode='normal'):
        if self.peer:
            # calculating the time the packet would need to be transmitted over this connection
            delay = self.latency+data['plSize']/self.bandwidth
            #DEBUG
            #print("Delay: "+str(delay)+" for data: "+str(data))
            # inserting the data to send in the Queue with the time it's supposed to take
             #self.q.put({'delay': delay, 'data':data})
            # modes: normal, donotchunk, forwardchunk
            self.q.put({'size': data['plSize'], 'chunkId': 0, 'data': data, 'mode': mode})
        else:
            #error, no peer
            print("error, no peer connected")

@TwoMethodsTimer("requestMedia", "startPlayback")
class Client(Peer):
    # bufferSize in Kb
    bufferSize = 1024
    mediaAskedFor = {}

    def requestMedia(self, idMedia, serverId = 1):
        payload = {'idServer': serverId, 'idVideo': idMedia}
        self.request(payload, None, 'videoRequest')
        self.mediaAskedFor[idMedia] = {'received': 0, 'size': None}

    def setBufferSize(self, bufferSize):
        self.bufferSize = bufferSize

    def receivedCallback(self, data):
        self.receivedData = data
        if data['plType'] is 'video':

            idMedia = data['payload']['idVideo']

            # wow, we never asked for that media!
            if idMedia not in self.mediaAskedFor:
                print("These are not the droids you're looking for")
                return

            # if this is the first chunk we receive
            if not self.mediaAskedFor[idMedia]['size']:
                self.mediaAskedFor[idMedia]['size'] = data['plSize']

            oldBuffer = self.mediaAskedFor[idMedia]['received']
            # we update how much we received for this media
            self.mediaAskedFor[idMedia]['received'] += data['chunkSize']
             #print("Downloaded "+str(self.mediaAskedFor[idMedia]['received'])+" out of "+str(self.mediaAskedFor[idMedia]['size'])+" for "+str(idMedia))
            playBuffer = self.mediaAskedFor[idMedia]['received']
            # if the download is complete
            if playBuffer >= self.mediaAskedFor[idMedia]['size']:
                self.downloadComplete(idMedia)

            # start playing the video if the buffer was previously not filled enough and is now ok
            if playBuffer >= self.bufferSize and oldBuffer < playBuffer:
                self.startPlayback(idMedia)
        else:
            Peer.receivedCallback(self, data)

    # to signal that we can start the playback
    def startPlayback(self, idMedia=None, data=None):
        if not idMedia:
            idMedia = data['payload']['videoId']
        print("Video "+str(idMedia)+" is playing")

    # to signal that the download is complete
    def downloadComplete(self, idMedia=None, data=None):
        if not idMedia:
            idMedia = data['payload']['videoId']
        print("Download of media "+str(idMedia)+" completed.")

# bare bone proxy, doing almost nothing
class BaseProxy(Peer):
    connection = dict()
    '''def __init__(self, id, name=None):
        Peer.__init__(self, id, name)
        connection = dict()'''

    def connectTo(self, peer):
        id = peer.getID()
        self.connection[id] = Connection(peer)
        return self.connection[id]

# base for more sophisticated proxy working with the requests defined in the specs
class AbstractProxy(BaseProxy, metaclass=ABCMeta):

    @abc.abstractmethod
    def _processVideoRequest(self, data):
        """ process a video request, usually look into the cache to get it or get it from the video server """
        return

    @abc.abstractmethod
    def _processResponseTo(self, data):
        """ process a response to a previous request, usually a request for a video """
        return

    @abc.abstractmethod
    def _processOther(self, data):
        """ process the unknown, can be anything else """
        return

    def receivedCallback(self, data):
        if 'responseTo' in data:
            self._processResponseTo(data)
        elif data['plType'] is 'videoRequest':
            self._processVideoRequest(data)
        elif data['plType'] is 'other':
            self._processOther(data)

class ForwardProxy(AbstractProxy):
    activeRequests = dict()

    # private
    def __packForward(self, data):
        forwardData = self._packData(data['payload'], data['plSize'], data['plType'], chunkId=data['chunkId'], chunkSize=data['chunkSize'])
        self.activeRequests[forwardData['packetId']] = {'origSender': data['sender'], 'origPackId': data['packetId']}
        return forwardData;

    def _processVideoRequest(self, data):
        forwardData = self.__packForward(data)
        self.connection[data['payload']['idServer']].send(forwardData, 'forwardchunk')

    def _processResponseTo(self, data):
        responseTo = data['responseTo']
        reqInfo = self.activeRequests[responseTo]
        newData = self._packData(data['payload'], data['plSize'], data['plType'], reqInfo['origPackId'], chunkId=data['chunkId'], chunkSize=data['chunkSize'])
        self.connection[reqInfo['origSender']].send(newData, 'forwardchunk')
        if 'lastChunk' in data:
            del self.activeRequests[responseTo]

    def _processOther(self, data):
        realData = self._packData("There you go: "+ data['payload'], responseTo=data['packetId'])
        self.connection[data['sender']].send(realData)

class FIFOProxy(AbstractProxy):
    __cachedb = dict()
    __cacheSize = 3072

class UnlimitedProxy(AbstractProxy):
    __cachedb = dict()
    activeRequests = dict()

    # private
    def __packForward(self, data):
        forwardData = self._packData(data['payload'], data['plSize'], data['plType'], chunkId=data['chunkId'], chunkSize=data['chunkSize'])
        self.activeRequests[forwardData['packetId']] = {'origSender': data['sender'], 'origPackId': data['packetId']}
        return forwardData;

    def _processVideoRequest(self, data):
        pl = data['payload']
        if pl['idVideo'] in self.__cachedb:
            video = self.__cachedb[pl['idVideo']]
            newData = self._packData(video, video['size'], 'video', data['packetId'])
            self.connection[data['sender']].send(newData)
        else:
            forwardData = self.__packForward(data)
            self.connection[data['payload']['idServer']].send(forwardData, 'forwardchunk')

    def _processResponseTo(self, data):
        responseTo = data['responseTo']
        reqInfo = self.activeRequests[responseTo]

        pl = data['payload']
        # cache the video, unconditionally
        if pl['idVideo'] not in self.__cachedb:
            self.__cachedb[pl['idVideo']]=pl

        newData = self._packData(pl, data['plSize'], data['plType'], reqInfo['origPackId'], chunkId=data['chunkId'], chunkSize=data['chunkSize'])
        self.connection[reqInfo['origSender']].send(newData, 'forwardchunk')
        if 'lastChunk' in data:
            del self.activeRequests[responseTo]

    def _processOther(self, data):
        realData = self._packData("There you go: "+ data['payload'], 2048, responseTo=data['packetId'])
        self.connection[data['sender']].send(realData)

class VideoServer(Peer):

    # private
    __db = dict()
    __curId = 0

    def receivedCallback(self, data):
        if data['plType'] is 'videoRequest':
            req = data['payload']
            #response = {'idVideo': req['idVideo'], 'duration': 60, 'size': 2048, 'bitrate': 2048/60}
            #respData = {'sender': self.id, 'payload': response, 'plSize': response['size'], 'plType': 'video'}
            response = self.__db[req['idVideo']]
            respData = self._packData(response, response['size'], 'video', data['packetId'])
            self.connection.send(respData)
        req = data['payload']

    def addVideo(self, duration=0, size=0, bitrate=0, title='', description='', id=None, video=None):
        if video:
            self.__db[video['idVideo']] = video
        else:
            if id:
                newId = id
            else:
                newId = __curId
                __curId += 1

            self.__db[newId] = {'idVideo': newId, 'duration': duration, 'size': size, 'bitrate': bitrate, 'title': title, 'description': description}
