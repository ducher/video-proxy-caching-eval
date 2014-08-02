#!/usr/bin/env python
#coding=utf-8

from pprint import pprint
import sys
import getopt
import time
import queue
import threading

def TwoMethodsTimer(func1, func2):                        # On @ decorator
    def ClassBuilder(aClass):
        class Wrapper:
            def __init__(self, *args, **kargs):           # On instance creation
                # stores the begining timestamp when timing
                self.startTime = 0  
                # to start all the latencies, for statistics purpose
                self.latencies = [] 
                self.wrapped = aClass(*args, **kargs)     # Use enclosing scope name

            def startTimer(self):
                self.startTime = time.time()

            def stopTimer(self):
                totalTime = time.time() - self.startTime
                self.latencies.append(totalTime)
                print("Took "+str(totalTime)+" seconds for "+ str(self.wrapped.getID()) + " Average: "+str(sum(self.latencies)/float(len(self.latencies))))

            def __getattr__(self, attrname):
                if attrname is func1:
                    self.startTimer()
                if attrname is func2:
                    self.stopTimer()
                return getattr(self.wrapped, attrname)    # Delegate to wrapped obj
        return Wrapper
    return ClassBuilder

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

    # size in mb
    def packData(self, data, size = None):
        #TODO replace the plSize
        plSize = size or len(data)/10
        realData = {'sender':self.id, 'payload':data, 'plSize': plSize}
        return realData

    def request(self, data):
        realData = self.packData(data)
        self.connection.send(realData)

    def receivedCallback(self, data):
        print(self.name+" received data: "+data['payload']+" from: "+str(data['sender']))

    def getID(self):
        return self.id

#unidirectional connection
class Connection:
    # bandwidth in mb/s
    # latency in seconds
    def __init__(self, peer=None, latency=2, bandwidth=1024):
        self.latency = latency
        # waiting queue for the packets, append() and popleft() are threadafe
        #self.queue = deque()
        self.bandwidth = bandwidth
        self.peer = peer
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

    # infinite loop running in a thread to simulate the time needed to send the data.
    # the thread gets the data to send from the Queue q, where the items have two fields:
    # - delay, how long the task is supposed to take
    # - data, the data to send, after the delay
    # private
    def worker(self):
        while True:
            item = self.q.get()
            data = item['data']
            time.sleep(item['delay'])
            self.peer.receivedCallback(data)
            self.q.task_done()

    def send(self, data):
        if self.peer:
            # calculating the time the packet would need to be transmitted over this connection
            delay = self.latency+data['plSize']/self.bandwidth
            #DEBUG
            #print("Delay: "+str(delay)+" for data: "+str(data))
            # inserting the data to send in the Queue with the time it's supposed to take
            self.q.put({'delay': delay, 'data':data})
        else:
            #error, no peer
            print("error, no peer connected")

@TwoMethodsTimer("request", "receivedCallback")
class Client(Peer):
    bufferSize = 0

    def requestMedia(self, mediaID):
        self.request("getmedia:"+mediaID)

    def setBufferSize(self, bufferSize):
        self.bufferSize = bufferSize




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
        realData = self.packData("There you go: "+ data['payload'], 2048)
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
c3.request('truc 2')
time.sleep(4)
c3.request('truc 3')

time.sleep(10)