# Proxy Caching Evaluation Framework

This framework will enable you to easily evaluate your new video proxy caching algorithm or compare existing algorithms. The framework is writtent in Python 3, an easy to read and write language for an easily extensible and comprehensible framework.

## Usage
There is a command line interface with cli.py. Running it with --help will show you the different option. Running it withou arguments will look for a config.ini file to load and run the simulation according to this file.

You can also use the the orchestrator.py module with your own files. Sample files are provided, named fake\_*. In these files you can see the expected input of the two files, the trace and the databases. The output will be written in the folder given as argument to "gather\_statistics", still in orchestration.py. For now this statistics are just all the playout latencies of all clients, unidentified.

The minimal code to have is something like this:

    o = orchestration.Orchestrator(conf=conf_orch) # create a new orchestrator
    o.set_up() # loads the trace and DB, creates the model
    o.skip_inactivity = False # to have a more realistic simulation
    o.run_simulation() # runs the simulation
    o.wait_end() # waits for the simulation to 
    o.gather_statistics("stats_fake") # writes the statistics to the folder "stats_fake"

To run the command line interface:

    ./cli.py [-h]

You can interrupt it by pressing ctrl+c (in a linux terminal), it will wait until the pending downloads are done and then write the statistics to the disk. If you don't want to wait and don't need the statistics, press ctrl+c again.

You can compare a Proxy to another by using the command line option --compare-to ProxyClassName. The graphics generated will compare the two proxies and the output files have the name of the proxy concerned.

## Extend the available proxies

To extend an existing proxy or to develop and new one, create a new file, for instance extend.py, and write your new proxy in it like this:

    #coding=utf-8
    """
    Custom module example to add a Proxy
    """

    import model

    class MyOwnProxy(model.ForwardProxy):
        pass

Of course, your proxy should do something more than "pass", but that is just an example. To have the metrics, you have to inherit from ProxyHitCounter and use the right methods at the right place. To have the cache size set correctly with the parameter specified in the .ini file, you need to inherit from CachingInterface and implement the set\_cache\_size method. 

**It is strongly advised to extend the CachingProxy** abstract class, as it is much easier. The metrics and CachingInterface are already integrated. Of course if you are too limited by this abstract class, extend directly another proxy, like the ForwardProxy. With this abstract class, you only have to implement four methods:
    
    _cache_admission(video): return true or false depending whether or not you 
                              you want to cache the video
    _id_to_evict(): return a video id to remove from the cache
    _new_video_inserted(video): is called when a new video is inserted in the 
                                cache. The video is passed as a parameter. Use 
                                it to update your data about the cache.
    _video_served(video): is called when a new video is served from the 
                          cache. The video is passed as a parameter. Use 
                          it to update your data about the cache.

An example with the FIFO Proxy algorithm, only ~14 lines of code:

    class FIFOProxy(CachingProxy):
        """ cache video in a limited size cache, 
            remove the oldest video(s) when full
        """
        def __init__(self, *args, **kargs):
            CachingProxy.__init__(self, *args, **kargs)
            """ Data structure to decide which video to evict """
            self.__cache_fifo = deque()
    
        def _cache_admission(self, video):
            """ We admit everything """
            return True
    
        def _id_to_evict(self):
            """ removes and returns the id of the video to evict """
            return self.__cache_fifo.popleft()
    
        def _new_video_inserted(self, video):
            self.__cache_fifo.append(video['idVideo'])
        
        def _video_served(self, video):
            pass

To use it your MyOwnProxy class in your extend.py file, in the config.ini file, have those lines:

    [proxy]
    proxy_type=MyOwnProxy
    module=extend

The Orchestrator will automatically load your proxy from your module file.

## Input

As you can see in the sample files, the input is *two csv files*. Values are separated by ',' and non numerical values must be enclosed in '"'. They can be described as the following:
The first one is the database file containing a description of the videos in each video server like this:

    "id_server","id_video","size","duration","bitrate","title","description"
The second one is the trace file contaning the requests from the clients for a given video on a given server at a given time like this:

    "id_client","req_timestamp","id_video","id_server"

## Output

The output is also CSV files, containing the values gathered by the different metrics. For now it is just the playout latencies of each client, the number of time the playout stopped for each client and the hit rate/ cache rate of the proxy server.

There are also two graphics in png format. One is the mean playout latencies of each client and the other the two hit ratios of the proxy.

## Warnings

This work is done for my masterarbeit and is not complete yet. Use it as your own "risk".

## Credits

By Pierre Ducher (pierre.ducher@gmail.com)