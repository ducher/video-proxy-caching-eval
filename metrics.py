
import time

# To time how long it takes to receive a response to a request
# keeps track of the packetId, so that mangled calls can be distinguished
def PacketTimer(func1, func2):                        # On @ decorator
    def ClassBuilder(aClass):
        class Wrapper:
            def __init__(self, *args, **kargs):           # On instance creation
                # stores the begining timestamps when timing
                self.startTime = dict()
                # to start all the latencies, for statistics purpose
                self.latencies = []
                self.wrapped = aClass(*args, **kargs)     # Use enclosing scope name

                self.oldFunc1 = self.wrapped.__getattribute__(func1)
                self.oldFunc2 = self.wrapped.__getattribute__(func2)

                self.wrapped.__setattr__(func1, self.newFunc1)
                self.wrapped.__setattr__(func2, self.newFunc2)


            def startTimer(self):
                # keeping track of the request with the _num_packet, which will be used to send the request
                self.startTime[self.wrapped._num_packet] = time.time()

            def stopTimer(self, packetid):
                if len(self.startTime) > 0:
                    #packetid = self.wrapped.receivedData['responseTo']
                    totalTime = time.time() - self.startTime[packetid]
                    #self.startTime.remove(packetid)
                    del self.startTime[packetid]
                    self.latencies.append(totalTime)
                    print("Took "+str(totalTime)+" seconds for "+ str(self.wrapped.get_id()) + " Average: "+str(sum(self.latencies)/float(len(self.latencies))))
                    
            def newFunc1(self, *args, **kargs):
                self.startTimer()
                return self.oldFunc1( *args, **kargs)

            def newFunc2(self, *args, **kargs):
                # the function needs the packetId it is answering to stop the right timer
                self.stopTimer(args[0]['responseTo'])
                return self.oldFunc2( *args, **kargs)

            def __getattr__(self, attrname):
                # to keep the original methods working
                return getattr(self.wrapped, attrname)    # Delegate to wrapped obj
        return Wrapper
    return ClassBuilder

# Time how long between the last call of func1 and first call of func2.
# Once func2 has been called, can time another interval.
def TwoMethodsTimer(func1, func2):                        # On @ decorator
    def ClassBuilder(aClass):
        class Wrapper:
            def __init__(self, *args, **kargs):           # On instance creation
                # stores the begining timestamp when timing
                self.startTime = 0  
                # to start all the latencies, for statistics purpose
                self.latencies = []
                self.wrapped = aClass(*args, **kargs)     # Use enclosing scope name

                self.oldFunc1 = self.wrapped.__getattribute__(func1)
                self.oldFunc2 = self.wrapped.__getattribute__(func2)

                self.wrapped.__setattr__(func1, self.newFunc1)
                self.wrapped.__setattr__(func2, self.newFunc2)


            def startTimer(self):
                print("Start")
                self.startTime = time.time()

            def stopTimer(self):
                if self.startTime != 0:
                    totalTime = time.time() - self.startTime
                    self.latencies.append(totalTime)
                    print("Took "+str(totalTime)+" seconds for "+ str(self.wrapped.get_id()) + " Average: "+str(sum(self.latencies)/float(len(self.latencies))))
                    self.startTime = 0

            def newFunc1(self, *args, **kargs):
                self.startTimer()
                return self.oldFunc1( *args, **kargs)

            def newFunc2(self, *args, **kargs):
                self.stopTimer()
                return self.oldFunc2( *args, **kargs)

            def __getattr__(self, attrname):
                # to keep the original methods working
                return getattr(self.wrapped, attrname)    # Delegate to wrapped obj
        return Wrapper
    return ClassBuilder