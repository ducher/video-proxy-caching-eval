
import time

# To time how long it takes to receive a response to a request
# keeps track of the packetId, so that mangled calls can be distinguished
def PacketTimer(func1, func2):                        # On @ decorator
    def ClassBuilder(aClass):
        class Wrapper:
            def __init__(self, *args, **kargs):           # On instance creation
                # stores the begining timestamps when timing
                self.__startTime = dict()
                # to start all the latencies, for statistics purpose
                self.__latencies = []
                self.__wrapped = aClass(*args, **kargs)     # Use enclosing scope name

                self.__oldFunc1 = self.__wrapped.__getattribute__(func1)
                self.__oldFunc2 = self.__wrapped.__getattribute__(func2)

                self.__wrapped.__setattr__(func1, self.__newFunc1)
                self.__wrapped.__setattr__(func2, self.__newFunc2)


            def __startTimer(self):
                # keeping track of the request with the _num_packet, which will be used to send the request
                self.__startTime[self.__wrapped._num_packet] = time.time()

            def __stopTimer(self, packetid):
                if len(self.__startTime) > 0:
                    #packetid = self.__wrapped.receivedData['responseTo']
                    totalTime = time.time() - self.__startTime[packetid]
                    #self.__startTime.remove(packetid)
                    del self.__startTime[packetid]
                    self.__latencies.append(totalTime)
                    print("Took "+str(totalTime)+" seconds for "+ str(self.__wrapped.get_id()) + " Average: "+str(sum(self.__latencies)/float(len(self.__latencies))))
                    
            def __newFunc1(self, *args, **kargs):
                self.__startTimer()
                return self.__oldFunc1( *args, **kargs)

            def __newFunc2(self, *args, **kargs):
                # the function needs the packetId it is answering to stop the right timer
                self.__stopTimer(args[0]['responseTo'])
                return self.__oldFunc2( *args, **kargs)

            def __getattr__(self, attrname):
                if(attrname is 'latencies'):
                    return self.__latencies
                # to keep the original methods working
                return getattr(self.__wrapped, attrname)    # Delegate to wrapped obj
        return Wrapper
    return ClassBuilder

# Time how long between the last call of func1 and first call of func2.
# Once func2 has been called, can time another interval.
def TwoMethodsTimer(func1, func2):                        # On @ decorator
    def ClassBuilder(aClass):
        class Wrapper:
            def __init__(self, *args, **kargs):           # On instance creation
                # stores the begining timestamp when timing
                self.__startTime = 0  
                # to start all the latencies, for statistics purpose
                self.__latencies = []
                self.__wrapped = aClass(*args, **kargs)     # Use enclosing scope name

                self.__oldFunc1 = self.__wrapped.__getattribute__(func1)
                self.__oldFunc2 = self.__wrapped.__getattribute__(func2)

                self.__wrapped.__setattr__(func1, self.__newFunc1)
                self.__wrapped.__setattr__(func2, self.__newFunc2)


            def __startTimer(self):
                print("Start")
                self.__startTime = time.time()

            def __stopTimer(self):
                if self.__startTime != 0:
                    totalTime = time.time() - self.__startTime
                    self.__latencies.append(totalTime)
                    print("Took "+str(totalTime)+" seconds for "+ str(self.__wrapped.get_id()) + " Average: "+str(sum(self.__latencies)/float(len(self.__latencies))))
                    self.__startTime = 0

            def __newFunc1(self, *args, **kargs):
                self.__startTimer()
                return self.__oldFunc1( *args, **kargs)

            def __newFunc2(self, *args, **kargs):
                self.__stopTimer()
                return self.__oldFunc2( *args, **kargs)

            def __getattr__(self, attrname):
                if(attrname is 'latencies'):
                    return self.__latencies
                # to keep the original methods working
                return getattr(self.__wrapped, attrname)    # Delegate to wrapped obj
        return Wrapper
    return ClassBuilder