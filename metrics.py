
import time
import matplotlib.pyplot as plt

import simu

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
                    totalTime = simu.real_time(totalTime)
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
                # necessary to get the latencies
                if(attrname is 'latencies'):
                    return self.__latencies
                # to keep the original methods working
                return getattr(self.__wrapped, attrname)    # Delegate to wrapped obj
        return Wrapper
    return ClassBuilder

# Time how long between the last call of func1 and first call of func2.
# Once func2 has been called, can time another interval.
# Counts how many times func3 has been called
# param: parameter to track in func1 and func2 when having multiple requests at the same time
def TwoMethodsTimerAndCounter(func1, func2, func3, param_pos=None, param_name=None):           # On @ decorator
    def ClassBuilder(aClass):
        class Wrapper:
            def __init__(self, *args, **kargs):           # On instance creation
                # stores the begining timestamps when timing
                self.__startTime = dict()
                # to start all the latencies, for statistics purpose
                self.__latencies = []
                self.__counter = 0
                self.__wrapped = aClass(*args, **kargs)     # Use enclosing scope name

                self.__oldFunc1 = self.__wrapped.__getattribute__(func1)
                self.__oldFunc2 = self.__wrapped.__getattribute__(func2)
                self.__oldFunc3 = self.__wrapped.__getattribute__(func3)

                self.__wrapped.__setattr__(func1, self.__newFunc1)
                self.__wrapped.__setattr__(func2, self.__newFunc2)
                self.__wrapped.__setattr__(func3, self.__newFunc3)

            def __startTimer(self, id_=0):
                print("Start")
                self.__startTime[id_] = time.time()

            def __stopTimer(self, id_=0):
                if id_ in self.__startTime:
                    totalTime = time.time() - self.__startTime[id_]
                    totalTime = simu.real_time(totalTime)
                    self.__latencies.append(totalTime)
                    print("Took "+str(totalTime)+" seconds for client "+ str(self.__wrapped.get_id()) + " Video: "+str(id_)+" Average: "+str(sum(self.__latencies)/float(len(self.__latencies))))
                    del self.__startTime[id_]
                    
            def __newFunc1(self, *args, **kargs):
                #print("__newFunc1")
                id_ = 0
                if param_pos != None and len(args) > param_pos:
                    id_ = args[param_pos]
                    print(str(id_))
                elif param_name and param_name in kargs:
                    id_ = kargs[param_name]
                
                self.__startTimer(id_)
                return self.__oldFunc1( *args, **kargs)

            def __newFunc2(self, *args, **kargs):
                #print("__newFunc2")
                id_ = 0
                if param_pos != None and len(args) > param_pos:
                    id_ = args[param_pos]
                elif param_name and param_name in kargs:
                    id_ = kargs[param_name]
                self.__stopTimer(id_)
                return self.__oldFunc2( *args, **kargs)

            def __newFunc3(self, *args, **kargs):
                #print("__newFunc1")
                self.__counter += 1
                return self.__oldFunc3( *args, **kargs)

            def __getattr__(self, attrname):
                if(attrname is 'counter'):
                    return self.__counter
                # necessary to get the latencies
                elif(attrname is 'latencies'):
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
                    totalTime = simu.real_time(totalTime)
                    self.__latencies.append(totalTime)
                    print("Took "+str(totalTime)+" seconds for "+ str(self.__wrapped.get_id()) + " Average: "+str(sum(self.__latencies)/float(len(self.__latencies))))
                    self.__startTime = 0

            def __newFunc1(self, *args, **kargs):
                #print("__newFunc1")
                self.__startTimer()
                return self.__oldFunc1( *args, **kargs)

            def __newFunc2(self, *args, **kargs):
                #print("__newFunc2")
                self.__stopTimer()
                return self.__oldFunc2( *args, **kargs)

            def __getattr__(self, attrname):
                if(attrname is 'latencies'):
                    return self.__latencies
                # to keep the original methods working
                return getattr(self.__wrapped, attrname)    # Delegate to wrapped obj
        return Wrapper
    return ClassBuilder

class ProxyHitCounter:
    
    def __init__(self):
        self._cache_hits = 0
        self._nb_served = 0
        self._byte_served = 0
        self._byte_cache = 0

    def _from_cache(self, size_kB=None, size_kb=None):
        """ kilo bytes - bits """
        size = 0
        if size_kB:
            size = size_kB
        elif size_kb:
            size = size_kb/8
        self._byte_cache += size
        self._byte_served += size

        self._cache_hits += 1
        self._nb_served += 1

    def _from_server(self, size_kB=None, size_kb=None):
        size = 0
        if size_kB:
            size = size_kB
        elif size_kb:
            size = size_kb/8
        self._byte_served += size
        self._nb_served += 1

    def get_stats(self):
        return self.get_hit_stats()

    def get_hit_stats(self):
        return {'cache_hits':self._cache_hits,
                'nb_served':self._nb_served,
                'hit_ratio':self._cache_hits/self._nb_served,
                'byte_cache':self._byte_cache,
                'byte_served':self._byte_served,
                'byte_hit_ratio':self._byte_cache/self._byte_served}


class PlotStats:

    def plot_latencies(self, latencies):
        print("plot")
        print(latencies)
        plt.plot(latencies, 'b-o')
        plt.show()

    def hist_latencies(self, latencies):
        print("hist")
        print(latencies)
        plt.hist(latencies,bins=3)
        plt.show()