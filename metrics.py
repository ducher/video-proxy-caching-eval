#coding=utf-8
import time

import matplotlib.pyplot as plt
import numpy as np
import statistics as sts
import collections as collec

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
        hit_ratio = 0
        byte_hit_ratio = 0
        if self._nb_served != 0:
            hit_ratio = self._cache_hits/self._nb_served
        if self._byte_served != 0:
            byte_hit_ratio = self._byte_cache/self._byte_served
        return {'cache_hits':self._cache_hits,
                'nb_served':self._nb_served,
                'hit_ratio':hit_ratio,
                'byte_cache':self._byte_cache,
                'byte_served':self._byte_served,
                'byte_hit_ratio':byte_hit_ratio}


class PlotStats:



    def plot_latencies(self, latencies):
        print("plot")
        print(latencies)
        plt.plot(latencies, 'b-o')
        plt.show()

    def plot_cache_stats(self, path='graphs', proxy_stats=None):
        """ proxy_stats: dictionnary
            Example:
            {
                'FIFOProxy':
                    {
                        "byte_served":9733.5,
                        "byte_hit_ratio":0.4025273539836647,
                        "byte_cache"3918.0,
                        "hit_ratio":0.36363636363636365,
                        "cache_hits":4,
                        "nb_served":11
                    },
                'LRUProxy':
                    {
                     ...
                    }
            }
        """
        # Example data
        proxies = proxy_stats.keys()
        metrics = list(proxy_stats.values())[0].keys()

        N = 2 # only two ratios
        nb_proxies = len(proxies)
        width = 0.7/nb_proxies

        print("NB PROXIES: "+str(nb_proxies))

        labels = ('Byte Hit Ratio', 'Hit Ratio')


        ind = np.arange(N)
        fig, ax = plt.subplots()

        colors = ['c','m','y','b','g','r','k','w']
        rectss = []
        for stats, i, color in zip(proxy_stats.values(), range(nb_proxies), colors):
            ratios = []
            ratios.append(stats['byte_hit_ratio'])
            ratios.append(stats['hit_ratio'])

            print("RATIOS: "+str(ratios))

            rectsx = ax.bar(ind+i*width, ratios, width, color=color)
            rectss.append(rectsx)

        ax.set_ylabel('Ratios')
        ax.set_title('Hit and Byte Hit ratios')
        ax.set_xticks(ind+width)

        ax.set_xticklabels(labels)

        ax.legend( zip([rectsx[0] for rectsx in rectss]), proxies )

        def autolabel(rects):
            # attach some text labels
            for rect in rects:
                height = rect.get_height()
                ax.text(rect.get_x()+rect.get_width()/nb_proxies, 1.05*height, '%.2f'%float(height),
                        ha='center', va='bottom')

        for rectsx in rectss:
            autolabel(rectsx)

        #plt.show()
        plt.savefig(path+'/proxy_perfs.png')

    def plot_bar(self, path='graphs', legend=None, *latencies_per_client):
        """latencies_per_client: ordered dictionnary {1001:[0.9,1.1], 1002:[2.1,3.0,1.1]}
        """
        # all latencies should have the same length
        N = len(latencies_per_client[0])
        nb_proxies = len(latencies_per_client)
        width = 0.7/nb_proxies

        print("NB PROXIES: "+str(nb_proxies))

        cMeans = []
        cStd = []
        labels = []

        for lpc in latencies_per_client:
            means = []
            std = []
            for client, latencies in lpc.items():
                means.append(np.mean(latencies))
                if len(latencies)>1:
                    #cStd.append(sts.variance(latencies))
                    std.append(np.amax(latencies)-np.amin(latencies))
                else:
                    std.append(0)
            cMeans.append(means)
            cStd.append(std)

        for client, latencies in latencies_per_client[0].items():
            # all labels should be the same and in the same order
            labels.append(str(client))


        ind = np.arange(N)
        fig, ax = plt.subplots()

        colors = ['c','m','y','b','g','r','k','w']
        rectss = []
        for means, std, i, color in zip(cMeans, cStd, range(nb_proxies), colors):
            rectsx = ax.bar(ind+i*width, means, width, color=color, yerr=std)
            rectss.append(rectsx)
        #rects1 = ax.bar(ind, cMeans, width, color='r', yerr=cStd)

        ax.set_ylabel('Latencies')
        ax.set_title('Mean latency by client')
        ax.set_xticks(ind+width)

        ax.set_xticklabels(labels)

        if legend == None:
            legend = []
            for i in range(nb_proxies):
                legend.append('Proxy '+str(i))
        ax.legend( zip([rectsx[0] for rectsx in rectss]), legend )

        def autolabel(rects):
            # attach some text labels
            for rect in rects:
                height = rect.get_height()
                ax.text(rect.get_x()+rect.get_width()/nb_proxies, 1.05*height, '%.2f'%float(height),
                        ha='center', va='bottom')

        for rectsx in rectss:
            autolabel(rectsx)

        #plt.show()
        plt.savefig(path+'/mean_latencies.png')

    def hist_latencies(self, latencies):
        print("hist")
        print(latencies)
        plt.hist(latencies,bins=3)
        plt.show()