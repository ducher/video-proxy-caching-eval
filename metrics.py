#coding=utf-8
""" 
Presentation
============

This module contains everything related to the metrics. The Decartors are the
metrics for the Client class, the ProxyHitCounter is to be inherited from by 
proxies.

Using a decorator
=================

To use a decorator to monitor a class:

.. code-block:: python

    # this will time how long it takes to start playing a video along with how many times
    # the video stopped during playback.
    @TwoMethodsTimerAndCounter('request_media', 'start_playback', '_video_stopped', 0, 'id_media')
    class MetricClient(Client):
        pass

A more simple example with TwoMethodsTimer applied to a standard class:

.. code-block:: python

    class Foo:

        def bar(self):
            print("bar")

        def foobar(self):
            print("foobar")

    @TwoMethodsTimer('bar', 'foobar')
    class TimedFoo(Foo):
        pass

Then to use it:

>>> f = TimedFoo()
>>> f.bar()
bar
>>> time.sleep(1) # we wait
>>> f.foobar()
foobar
>>> print(f.latencies)
[1.02]


Code documentation
==================
"""
import time

import matplotlib.pyplot as plt
import numpy as np
import statistics as sts
import collections as collec

import simu

# To time how long it takes to receive a response to a request
# keeps track of the packetId, so that mangled calls can be distinguished
def PacketTimer(func1, func2):                        # On @ decorator
    """ Decorator to time how long it takes to receive a response to a request
        keeps track of the packetId, so that mangled calls can be distinguished

        Args:
            func1 (function): first function to start the timer. Calling 
            it will start the timer.
            func2 (function): second function to stop the timer. Calling 
            it will stop the timer and store the time in the datastructure.

    """
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
    """ Time how long between the last call of func1 and first call of func2.
        Once func2 has been called, can time another interval.
        Counts how many times func3 has been called.
        To differentiate the func2 call that corresponds to a certain func1 call,
        it will use the parameter in func1 and func2 specified by param_pos and
        param_name to keep track of the calls.

        Args:
            func1 (function): first function to start the timer. Calling 
                              it will start the timer.
            func2 (function): second function to stop the timer. Calling 
                              it will stop the timer and store the time in the 
                              datastructure.
            func3 (function): function for which we want to count the number of 
                              calls
            param_pos (int): the position of the parameter to keep track of the 
                             calls between func1 and func2.
            param_name (str): the name of the parameter to keep track of the 
                              calls between func1 and func2.
    """
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
    """ Time how long between the last call of func1 and first call of func2.
        Once func2 has been called, can time another interval.

        Args:
            func1 (function): first function to start the timer. Calling 
                              it will start the timer.
            func2 (function): second function to stop the timer. Calling 
                              it will stop the timer and store the time in the 
                              datastructure.
    """
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
    """ Class to inherit from for proxies to have hit stats.

        The inherited class must call _from_cache() and _from_server() when
        serving a video from the cache or not. Then, get_stats() can be used.
    """
    
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
        """ 
            Returns:
                A dictionnary containing the stats, fields:

                - cache_hits (int): number of time the data was served from the 
                                    cache
                - nb_served (int): total number of objects served
                - hit_ratio (float): cache_hits/nb_served
                - byte_cache (int): number of bytes served from the cache
                - byte_served (int): total number of bytes served
                - byte_hit_ratio (float): byte_cache/byte_served
        """
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
    """ Class to plot the statistics/metrics of the clients and proxy and save 
        it in PNG pictures.
    """

    def plot_latencies(self, latencies):
        print("plot")
        print(latencies)
        plt.plot(latencies, 'b-o')
        plt.show()

    def plot_cache_stats(self, path='graphs', proxy_stats=None):
        """ Bar graph with the hit ratio and byte hit ratio of one or more 
            proxies.

            Args:
                path (str): where to save the file
                proxy_stats (dict): dictionnary
            Example of proxy_stats:

            >>> {
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
        """ Writes a bar graph on disk with the mean latency of each client.
            Looks very messy when there are too many clients.

            Args:
                path (str): where to save the png file
                legend (list): name of the proxies, in same order as the other 
                               parameter
                latencies_per_client (dict): ordered dictionnary containging the 
                                      latencies associated with the id of 
                                      each client: 
                                      {1001:[0.9,1.1], 1002:[2.1,3.0,1.1]}
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

    def hist_latencies(self, latencies, path='graphs', nb_bins=3):
        """ Draws an histogram of the latencies, with 3 bins by default.

            Args:
                path (str): where to save the png file
                latencies (list): all latencies, not ordered
                nb_bins (int): desired number of bins
        """
        print("hist")
        print(latencies)
        plt.hist(latencies,bins=nb_bins)
        #plt.show()
        plt.savefig(path+'/hist_latencies.png')