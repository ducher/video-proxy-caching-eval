#!/usr/bin/env python
#coding=utf-8

from threading import Timer
from pprint import pprint
import sys
import getopt
import time


def TwoMethodsTimer(func1, func2):                        # On @ decorator
    def ClassBuilder(aClass):
        class Wrapper:
            def __init__(self, *args, **kargs):           # On instance creation
                self.startTime = 0
                self.wrapped = aClass(*args, **kargs)     # Use enclosing scope name

            def startTimer(self):
                self.startTime = time.time()

            def stopTimer(self):
                totalTime = time.time() - self.startTime
                print("Took "+str(totalTime)+" seconds for "+ str(self.wrapped.getID()))

            def __getattr__(self, attrname):
                if attrname is func1:
                    self.startTimer()
                if attrname is func2:
                    self.stopTimer()
                return getattr(self.wrapped, attrname)    # Delegate to wrapped obj
        return Wrapper
    return classBuilder

class Peer:
    id = 0
    name = ""
    connection = None

    def __init__(self, id, name=None):
        self.name = name or ""
        self.id = id

    def connectTo(self, peer):
        self.connection = Connection(peer)
        return self.connection

    def packData(self, data):
        realData = {'sender':self.id, 'data':data}
        return realData

    def request(self, data):
        realData = self.packData(data)
        self.connection.send(realData)

    def receivedCallback(self, data):
        print(self.name+" received data: "+data['data']+" from: "+str(data['sender']))

    def getID(self):
        return self.id

#unidirectional connection
class Connection:
    def __init__(self, peer=None, latency=2):
        self.latency = latency
        self.peer = peer

    def connect(self, peer):
        if not self.peer:
            self.peer = peer
        else:
            #error
            print("error, already one peer")

    def setLag(self, latency=2):
        self.latency = latency

    def send(self, data):
        if self.peer:
            t = Timer(self.latency, self.peer.receivedCallback, args=[data])
            t.start()
        else:
            #error, no peer
            print("error, no peer connected")

@TwoMethodsTimer("request", "receivedCallback")
class Client(Peer):
    id = 0

    def requestMedia(mediaID):
        self.request("getmedia:"+mediaID)




class Proxy(Peer):
    connection = dict()

    '''def __init__(self, id, name=None):
        Peer.__init__(self, id, name)
        connection = dict()'''

    def connectTo(self, peer):
        id = peer.getID()
        self.connection[id] = Connection(peer)
        return self.connection[id]

    def receivedCallback(self, data):
        realData = self.packData("There you go: "+ data['data'])
        self.connection[data['sender']].send(realData)



c1 = Client(1, "c1")
c2 = Client(2, "c2")
c3 = Client(3, "c3")

p = Proxy(0, "Proxy")

c1.connectTo(p)
p.connectTo(c1)

c3.connectTo(p).setLag(0.5)
p.connectTo(c3).setLag(0.5)
'''
c1 = Client(1, "c1")
c2 = Client(2, "c2")
c3 = Client(3, "c3")

c1.connectTo(c2)
c2.connectTo(c1)

c3.connectTo(c2).setLag(0.5)
c2.connectTo(c3).setLag(0.5)
'''

c1.request('lol')
c3.request('pouet')
c3.request('truc')