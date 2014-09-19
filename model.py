#coding=utf-8
"""A framework to easily test new proxy caching algorithms.

.. moduleauthor:: Pierre Ducher

units:

- data in kb
- time in seconds
- bandwidth in kb/s
"""
# units:
# data in kb
# time in bandwidth
# seconds in kb/s

#from pprint import pprint
import sys
import getopt
import time
import queue
import threading
from collections import deque
# for abstract classes
import abc
from abc import ABCMeta

from metrics import *
import config
import simu


class Peer:
    """Common base for classes that are communicating

    The Peer class gives a base for communication, all communicating classes
    should inherit from it.

    IDs conventions:

    - 0 for the proxy
    - from 1 to 1000 for VideoServers
    - from 1001 to infinity for the clients

    Args:
        id (int): an ID identifying the Peer on the 'network', should be unique
        name (str): a easy to read name, optional
    """
    # IDs conventions:
    # 0 for the proxy
    # from 1 to 1000 for VideoServers
    # from 1001 to infinity for the clients

    def __init__(self, id_, name=None):
        self.name = name or ""
        self._id = id_
        self.connection = None
        self._num_packet = 0
        self._received_data = None

    def connect_to(self, peer):
        """ connect a peer to another peer """
        self.connection = Connection(peer)
        return self.connection

    def _pack_data(self, data, size=None, type_='other', response_to=None, 
                   chunk_id=None, chunk_size=None):
        #TODO replace the plSize
        pl_size = size or len(data)*8/1024
        real_data = {'sender':self._id, 'payload':data, 'plSize': pl_size, 
                     'plType': type_, 'packetId': self._num_packet}
        self._num_packet += 1
        if response_to != None:
            real_data['responseTo'] = response_to
        if chunk_id != None:
            real_data['chunkId'] = chunk_id
            real_data['chunkSize'] = chunk_size
        return real_data

    def request(self, data, size=None, type_='other'):
        """ low level method to request something from the other peer """
        real_data = self._pack_data(data, size, type_)
        self.connection.send(real_data)

    def received_callback(self, data):
        """Meant to be called to give data to the Peer

        The :class:`Connection` uses it when data is available for a Peer.

        Args:
            data (dict): The data to give to the peer.
        Returns:
            Nothing
        """
        self._received_data = data
        print(self.name+" received data: "+str(data['payload'])+
              " from: "+str(data['sender']))

    def get_id(self):
        return self._id

    @property
    def received_data(self):
        return self._received_data

class Connection:
    """Unidirectional connection

    Args:
            peer (:class:`Peer`): the Peer we want to send data to
            latency (int): the latency in seconds
            bandwidth (int): the speed of the connection, in kb/s
            max_chunk (int): the maximum size in which a packet will be devided
                if it is too large, in kb
    """
    def __init__(self, peer=None, latency=2, bandwidth=1024, max_chunk=8):
        self.latency = latency
        # waiting queue for the packets, append() and popleft() are threadafe
        #self.queue = deque()
        self.bandwidth = bandwidth
        self.peer = peer
        self.max_chunk = max_chunk
        self.q = queue.Queue()
        self.thread = threading.Thread(target=self.worker)
        self.thread.daemon = True
        self.thread.start()

    def connect(self, peer):
        """ Connect to antoher :class:`Peer`
        This is a one-way communication,
        so this Connection will only be able to send data to this Peer

        Args:
            peer (:class:`Peer`): Who we want to send data to
        """
        if not self.peer:
            self.peer = peer
        else:
            #error
            print("error, already one peer")

    def set_lag(self, latency=2):
        self.latency = latency
        return self

    def set_bandwidth(self, bandwidth=1024):
        self.bandwidth = bandwidth
        return self

    def set_max_chunk(self, max_chunk=8):
        self.max_chunk = max_chunk
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
                if item['size'] > self.max_chunk:
                    data['chunkSize'] = self.max_chunk
                    item['chunkId'] += 1
                    item['size'] -= self.max_chunk
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

            delay = data['chunkSize']/self.bandwidth

            if data['chunkId'] is 0:
                """ only add the latency on the first chunk as the latency
                    is only noticable one time, then all chunks are sent
                    consecutively  """
                delay += self.latency

            #print("Delay: "+str(delay)+", ChunkSize: "+str(data['chunkSize']))

            simu.sleep(delay)
            self.peer.received_callback(data)
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

#@TwoMethodsTimer("request_media", "start_playback")
class Client(Peer):
    """Represents a client, which downloads videos through the Proxy.
       Can be monitored wit the metrics in metrics.python.
       Can consume videos (play them) to measure how many times the video stops.
       For the latter feature, call start_video_consumer.

    """

    def __init__(self, *args, **kargs):
        Peer.__init__(self, *args, **kargs)
        self.buffer_size = 1024
        """bufferSize in Kb"""
        self.media_asked_for = {}
        self.media_downloading = 0
        self.play_thread = threading.Thread(target=self._play_videos)
        self.play_thread.daemon = True
        
        # settings for the player thread
        self.play_auto = True
        self.play_wait_buffer = True

        # to avoid asking the same video two times in a row
        self.two_in_a_row_protection = True
        self.last_media = None

        # function to signal a new download pending
        self.signal_new_download = self.print_new_dl

        # function to signal a download being done
        self.signal_end_download = self.print_end_dl

    def _play_videos(self):
        """ Automatically consumes videos when the buffer has been filled initially
            Supposed to be run only in an independant thread.
            Runs once every simulated second.
        """
        while True:
            # Infinite loop, not really efficient
            for id_media in self.media_asked_for:
                # if the state of the video is "buffering"
                if self.play_wait_buffer and self.media_asked_for[id_media]['state'] is 'buffer':
                    # if the buffer is filled enough, we update the state to "playing"
                    if self.media_asked_for[id_media]['buffer'] > self.buffer_size:
                        self.media_asked_for[id_media]['state'] = 'play'
                # if the state of the video is "playing"
                if self.media_asked_for[id_media]['state'] is 'play':
                    if self.media_asked_for[id_media]['buffer'] >= self.media_asked_for[id_media]['bitrate']:
                        self.media_asked_for[id_media]['buffer'] -= self.media_asked_for[id_media]['bitrate']
                    else:
                        self.media_asked_for[id_media]['buffer'] = 0
                    if self.media_asked_for[id_media]['buffer'] is 0:
                        # change the state if we want to wait for the buffer to be filled
                        if self.play_wait_buffer:
                            # only when we want to wait for a buffer refill each time it stops
                            self.media_asked_for[id_media]['state'] = 'buffer'
                        #print("Buffer empty for video "+str(id_media))
                        self._video_stopped(id_media)
                    percentage = self.media_asked_for[id_media]['buffer']/self.buffer_size*100
                    #print("Buffer for media "+str(id_media)+" filled at "+str(percentage)+"%")
            simu.sleep(1)


    def start_video_consumer(self):
        """ starts the thread to consume videos"""
        self.play_thread.start()

    def _video_stopped(self, id_video=None):
        """ Hook to count how many times videos are stopping
            (because of a bad network inducing an empty buffer)
        """
        # if id_video != None:
        #     print("Video "+str(id_video)+" stopped playing on client "+self.name)
        # else:
        #     print("A video stopped playing on client "+self.name)
        pass


    def request_media(self, id_media, server_id=1):
        """
        A really useful function.

        Returns None
        """
        print(self.name+" requesting: "+str(id_media)+", last media: "+str(self.last_media))
        if self.two_in_a_row_protection and id_media == self.last_media:
            print("Not requesting "+str(id_media))
            return
        self.last_media = id_media
        payload = {'idServer': server_id, 'idVideo': id_media}
        self.request(payload, None, 'videoRequest')
        self.media_asked_for[id_media] = {'received': 0, 'size': None, 'bitrate': 0, 'buffer': 0, 'state': 'stop'}
        #self.media_downloading += 1
        self.signal_new_download()

    def set_buffer_size(self, buffer_size):
        self.buffer_size = buffer_size

    def set_play_wait_buffer(self, play_wait_buffer):
        self.play_wait_buffer = play_wait_buffer

    def set_two_in_a_row_protection(self, two_in_a_row_protection):
        self.two_in_a_row_protection = two_in_a_row_protection

    def received_callback(self, data):
        self._received_data = data
        if data['plType'] is 'video':

            id_media = data['payload']['idVideo']

            # wow, we never asked for that media!
            if id_media not in self.media_asked_for:
                print("These are not the droids you're looking for")
                return

            # if this is the first chunk we receive
            if not self.media_asked_for[id_media]['size']:
                self.media_asked_for[id_media]['size'] = data['plSize']
                self.media_asked_for[id_media]['bitrate'] = data['payload']['bitrate']

            oldReceived = self.media_asked_for[id_media]['received']
            # we update how much we received for this media
            self.media_asked_for[id_media]['received'] += data['chunkSize']
            self.media_asked_for[id_media]['buffer'] += data['chunkSize']
            #print("Downloaded "+str(self.media_asked_for[id_media]['received'])+" out of "+str(self.media_asked_for[id_media]['size'])+" for "+str(id_media))
            received = self.media_asked_for[id_media]['received']
            # if the download is complete
            if received >= self.media_asked_for[id_media]['size']:
                print("Downloaded "+str(self.media_asked_for[id_media]['received'])+" out of "+str(self.media_asked_for[id_media]['size'])+" for "+str(id_media))
                self.download_complete(id_media)

            # start playing the video if the buffer was previously not filled enough and is now ok
            if received >= self.buffer_size and oldReceived < received \
            and self.media_asked_for[id_media]['state'] is 'stop':
                self.media_asked_for[id_media]['state'] = 'play'
                self.start_playback(id_media=id_media)
        else:
            Peer.received_callback(self, data)

    def start_playback(self, id_media=None, data=None):
        """ To signal that we can start the playback

        Should only be called inernaly, is here so that a timer decorator
        can now when this is called and stop the timer.
        """
        if not id_media:
            id_media = data['payload']['videoId']
        print("Video "+str(id_media)+" is playing")

    def download_complete(self, id_media=None, data=None):
        if not id_media:
            id_media = data['payload']['videoId']
        #self.media_downloading -= 1
        self.signal_end_download()
        print("Download of media "+str(id_media)+" for client "+self.name+" completed.")

    def print_new_dl(self):
        """ "Placeholder" for the signal_new_download function """
        print("New dl")

    def print_end_dl(self):
        """ "Placeholder" for the signal_end_download function """
        print("End dl")

    def set_func_new_dl(self, func):
        """ Change the function to call when starting a new download """
        self.signal_new_download = func

    def set_func_end_dl(self, func):
        """ Change the function to call when starting a download is done """
        self.signal_end_download = func

class BaseProxy(Peer):
    """Bare bone proxy, doing almost nothing

    The base only includes a way to be connected to multiple peers at the same time.
    No disconnection yet, though.
    """
    def __init__(self, *args, **kargs):
        Peer.__init__(self, *args, **kargs)
        self.connection = dict()

    def connect_to(self, peer):
        id_ = peer.get_id()
        self.connection[id_] = Connection(peer)
        return self.connection[id_]

class AbstractProxy(BaseProxy, metaclass=ABCMeta):
    """ base for more sophisticated proxy working with the requests defined in the specs 

    Splits the received_callback into 3 different possibilities: 

    - processVideoRequest for a video request from a client and maybe forward it to a Video Server
    - processResponseTo for the responses the Proxy receives, usually the video he asked
    - processOther for anything else
    """

    @abc.abstractmethod
    def _process_video_request(self, data):
        """ process a video request, usually look into the cache to get it or get it from the video server """
        pass

    @abc.abstractmethod
    def _process_response_to(self, data):
        """ process a response to a previous request, usually a request for a video """
        pass

    @abc.abstractmethod
    def _process_other(self, data):
        """ process the unknown, can be anything else """
        pass

    def received_callback(self, data):
        """
        This will filter through the different type of packets
        and cal the appropriate function.
        """
        if 'responseTo' in data:
            self._process_response_to(data)
        elif data['plType'] is 'videoRequest':
            self._process_video_request(data)
        elif data['plType'] is 'other':
            self._process_other(data)

class ForwardProxy(AbstractProxy):
    """ A proxy forwarding everything and caching nothing """

    def __init__(self, *args, **kargs):
        AbstractProxy.__init__(self, *args, **kargs)
        self.active_requests = dict()

    def _pack_forward_request(self, data):
        forward_data = self._pack_data(data['payload'], 
                                       data['plSize'], 
                                       data['plType'])
        forward_data['chunkId'] = data['chunkId']
        forward_data['chunkSize'] = data['chunkSize']
        # store the forwarded packetId in the active request to keep track of it
        self.active_requests[forward_data['packetId']] = \
                {'origSender': data['sender'], 'origPackId': data['packetId']}

        return forward_data

    def _pack_forward_response(self, data):
        response_to = data['responseTo']
        req_info = self.active_requests[response_to]
        forward_data = self._pack_data(data['payload'], 
                                   data['plSize'], 
                                   data['plType'], 
                                   req_info['origPackId'])
        forward_data['chunkId'] = data['chunkId']
        forward_data['chunkSize'] = data['chunkSize']
        if 'lastChunk' in data:
            del self.active_requests[response_to]

        return forward_data

    def _process_video_request(self, data):
        #print("DATA "+str(data))
        forward_data = self._pack_forward_request(data)
        self.connection[data['payload']['idServer']].send(forward_data, 'forwardchunk')

    def _process_response_to(self, data):
        response_to = data['responseTo']
        req_info = self.active_requests[response_to]
        new_data = self._pack_forward_response(data)
        self.connection[req_info['origSender']].send(new_data, 'forwardchunk')

    def _process_other(self, data):
        real_data = self._pack_data("There you go: "+ data['payload'], 
                                    response_to=data['packetId'])
        self.connection[data['sender']].send(real_data)

    def _get_req_info(self, id_req):
        return self.active_requests[id_req]

class CachingInterface(metaclass=ABCMeta):
    """ Common interface for proxies that are actually caching objects """

    def __init__(self, *args, **kargs):
        pass

    @abc.abstractmethod
    def set_cache_size(self, size):
        pass

class CachingProxy(ForwardProxy, CachingInterface, ProxyHitCounter, metaclass=ABCMeta):
    """ Common abstract class for proxies that are actually caching objects 

        To implement your own Proxy, extend this Class.
        You have to implement the abstract methods:
            _cache_admission: return true or false depending whether or not you 
                              you want to cache the video
            _id_to_evict: return a video id to remove from the cache
            _new_video_inserted: is called when a new video is inserted in the 
                                 cache. The video is passed as a parameter. Use 
                                 it to update your data about the cache.

        A fairly simple example is the FIFOProxy. The FIFOProxyOld shows the same
        proxy but without the help of this abstract class.
    """

    def __init__(self, *args, **kargs):
        ForwardProxy.__init__(self, *args, **kargs)
        ProxyHitCounter.__init__(self)
        self.__cachedb = dict()
        self.__cache_size = 0
        self.__cache_max_size = 4096

    def set_cache_size(self, size):
        """ Change the maximum size of the cache
            Args:
                size (int): the new size
        """
        self.__cache_max_size = size

    @abc.abstractmethod
    def _cache_admission(self, video):
        """ Should return true to admit the video in the cache
        """
        pass

    @abc.abstractmethod
    def _id_to_evict(self):
        """ should return the id of the video we can remove
            used in case the proxy is full
            This is the cache eviction part of the proxy
        """
        pass

    @abc.abstractmethod
    def _new_video_inserted(self, video):
        """ To signal that a new video has been inserted.
            Use this to update your data/statistics to make
            later decisions on what video to evict.
        """
        pass

    def _cache_full(self, newSize=0):
        """ check if the cache is full, or will be if we add the new size """
        return (self.__cache_size+newSize) >= self.__cache_max_size

    def _make_space_for_new_video(self, video=None, size=None):
        """ Removes videos until we have enough space """
        vsize = size
        if video != None:
            vsize = video['size']

        while self._cache_full(vsize):
            id_evict = self._id_to_evict()
            self.__cache_size -= self.__cachedb[id_evict]['size']
            del self.__cachedb[id_evict]

    def _insert_new_video(self, video):
        """ inserts a new video, updates the cache size"""
        self.__cachedb[video['idVideo']] = video
        self.__cache_size += video['size']
        self._new_video_inserted(video)

    def _process_video_request(self, data):
        pld = data['payload']
        if pld['idVideo'] in self.__cachedb:
            video = self.__cachedb[pld['idVideo']]
            # for the metric, ProxyHitCounter
            self._from_cache(size_kb=video['size'])

            new_data = self._pack_data(video, video['size'], 
                                       'video', data['packetId'])
            self.connection[data['sender']].send(new_data)
        else:
            forward_data = self._pack_forward_request(data)
            self.connection[data['payload']['idServer']].send(forward_data, 
                                                              'forwardchunk')

    def _process_response_to(self, data):
        response_to = data['responseTo']
        req_info = self._get_req_info(response_to)

        pld = data['payload']
        
        if pld['idVideo'] not in self.__cachedb and\
           self._cache_admission(pld) and\
           pld['size'] < self.__cache_max_size:
            """ cache the video, if it's not already in the cache
                and we decide to cache it
                and it's smaller than the cache size
            """
            # for the metric
            self._from_server(size_kb=pld['size'])

            self._make_space_for_new_video(pld)
            self._insert_new_video(pld)

        new_data = self._pack_forward_response(data)

        self.connection[req_info['origSender']].send(new_data, 'forwardchunk')

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


class FIFOProxyOld(ForwardProxy, ProxyHitCounter, CachingInterface):
    """ Old implentation of a FIFOProxy, to show how to do a proxy without the 
        help of the CachingProxy abstract class.

        cache video in a limited size cache, 
        remove the oldest video(s) when full
    """
    def __init__(self, *args, **kargs):
        ForwardProxy.__init__(self, *args, **kargs)
        self.__cachedb = dict()
        self.__cache_fifo = deque()
        self.__cache_size = 0
        self.__cache_max_size = 3072
        ProxyHitCounter.__init__(self)

    def set_cache_size(self, size):
        """ Change the maximum size of the cache
            Args:
                size (int): the new size
        """
        self.__cache_max_size = size

    

    def _process_video_request(self, data):
        pld = data['payload']
        if pld['idVideo'] in self.__cachedb:
            video = self.__cachedb[pld['idVideo']]
            # for the metric
            self._from_cache(size_kb=video['size'])

            new_data = self._pack_data(video, video['size'], 
                                       'video', data['packetId'])
            self.connection[data['sender']].send(new_data)
        else:
            forward_data = self._pack_forward_request(data)
            self.connection[data['payload']['idServer']].send(forward_data, 
                                                              'forwardchunk')

    def _process_response_to(self, data):
        response_to = data['responseTo']
        req_info = self._get_req_info(response_to)

        pld = data['payload']
        # cache the video, if it's smaller than the cache size
        if pld['idVideo'] not in self.__cachedb and\
           pld['size'] < self.__cache_max_size:
            # for the metric
            self._from_server(size_kb=pld['size'])

            self._make_space_for_new_video(pld)
            self._insert_new_video(pld)

        new_data = self._pack_forward_response(data)

        self.connection[req_info['origSender']].send(new_data, 'forwardchunk')

    def _make_space_for_new_video(self, video):
        """ Removes videos until we have enough space """
        while self._cache_full(video['size']):
            id_evict = self._id_to_evict()
            self.__cache_size -= self.__cachedb[id_evict]['size']
            del self.__cachedb[id_evict]

    def _cache_full(self, newSize=0):
        """ check if the cache is full, or will be if we add the new size """
        return (self.__cache_size+newSize) >= self.__cache_max_size

    def _id_to_evict(self):
        """ removes and returns the id of the video to evict """
        return self.__cache_fifo.popleft()

    def _insert_new_video(self, video):
        """ inserts a new video, updates the cache size and fifo queue """
        self.__cachedb[video['idVideo']] = video
        self.__cache_size += video['size']
        self.__cache_fifo.append(video['idVideo'])

class UnlimitedProxy(ForwardProxy):
    """ Proxy caching everything, without a size limit. 
    Once an object is accessed, it is stored in the cache 
    """

    def __init__(self, *args, **kargs):
        AbstractProxy.__init__(self, *args, **kargs)
        self.active_requests = dict()
        self.__cachedb = dict()

    def _process_video_request(self, data):
        pld = data['payload']
        if pld['idVideo'] in self.__cachedb:
            video = self.__cachedb[pld['idVideo']]
            new_data = self._pack_data(video, video['size'], 
                                       'video', data['packetId'])
            self.connection[data['sender']].send(new_data)
        else:
            forward_data = self._pack_forward_request(data)
            self.connection[data['payload']['idServer']].send(forward_data, 
                                                              'forwardchunk')

    def _process_response_to(self, data):
        response_to = data['responseTo']
        req_info = self.active_requests[response_to]

        pld = data['payload']
        # cache the video, unconditionally
        if pld['idVideo'] not in self.__cachedb:
            self.__cachedb[pld['idVideo']] = pld

        new_data = self._pack_forward_response(data)

        self.connection[req_info['origSender']].send(new_data, 'forwardchunk')

class VideoServer(Peer):
    """ Simulation of the video server, can store 'videos' 
    and give them through the connection 
    """

    def __init__(self, *args, **kargs):
        Peer.__init__(self, *args, **kargs)
        self.__db = dict()
        self.__cur_id = 0

    def received_callback(self, data):
        if data['plType'] is 'videoRequest':
            req = data['payload']
            #response = {'idVideo': req['idVideo'], 'duration': 60, 'size': 2048, 'bitrate': 2048/60}
            #resp_data = {'sender': self.id, 'payload': response, 'plSize': response['size'], 'plType': 'video'}
            response = self.__db[req['idVideo']]
            resp_data = self._pack_data(response, response['size'], 
                                        'video', data['packetId'])
            self.connection.send(resp_data)
        req = data['payload']

    def add_video(self, duration=0, size=0, bitrate=0, title='', 
                  description='', id_=None, video=None):
        """ Add a video to the video server.

        Args:
            duration (int): The duration of the video in seconds
            size (int): Size of the video in kilobits
            bitrate (int): Bitrate of the video in kb/s
            title (str): Title of the video
            description (str): Description of the video
            id (int): optional, if not specified, the id will be the previous+1
            video (dict): if specified, ignores everything else.
            Dictionnary entry like this:
                {'idVideo': 1, 'duration': 13, 'size': 1245, 'bitrate': 96, 
                 'title': "Video", 'description': "Best video"}
        Returns:
            Nothing
        """
        if video:
            self.__db[video['idVideo']] = video
        else:
            if id_:
                new_id = id_
            else:
                new_id = self.__cur_id
                self.__cur_id += 1

            self.__db[new_id] = {'idVideo': new_id, 
                                 'duration': duration, 
                                 'size': size, 
                                 'bitrate': bitrate, 
                                 'title': title, 
                                 'description': description}
