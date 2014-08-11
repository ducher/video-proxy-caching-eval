#!/usr/bin/env python
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
        self.connection = Connection(peer)
        return self.connection

    # size in mb
    # protected
    def _pack_data(self, data, size=None, type_='other', response_to=None, 
                   chunk_id=None, chunk_size=None):
        #TODO replace the plSize
        pl_size = size or len(data)/10
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

#unidirectional connection
class Connection:
    """

    Args:
            peer (:class:`Peer`): the Peer we want to send data to
            latency (int): the latency in seconds
            bandwidth (int): the speed of the connection, in kb/s
            max_chunk (int): the maximum size in which a packet will be devided
                if it is too large, in kb
    """
    def __init__(self, peer=None, latency=2, bandwidth=1024, max_chunk=512):
        self.latency = latency
        # waiting queue for the packets, append() and popleft() are threadafe
        #self.queue = deque()
        self.bandwidth = bandwidth
        self.peer = peer
        self.max_chunk = max_chunk
        self.q = queue.Queue()
        self.t = threading.Thread(target=self.worker)
        self.t.daemon = True
        self.t.start()

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

    def set_max_chunk(self, max_chunk=512):
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

            delay = self.latency+data['chunkSize']/self.bandwidth

            time.sleep(delay)
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

@TwoMethodsTimer("request_media", "start_playback")
class Client(Peer):
    """Represents a client, which downloads videos through the Proxy.
    """

    def __init__(self, *args, **kargs):
        Peer.__init__(self, *args, **kargs)
        self.buffer_size = 1024
        """bufferSize in Kb"""
        self.media_asked_for = {}

    def request_media(self, id_media, server_id=1):
        """
        A really useful function.

        Returns None
        """
        payload = {'idServer': server_id, 'idVideo': id_media}
        self.request(payload, None, 'videoRequest')
        self.media_asked_for[id_media] = {'received': 0, 'size': None}

    def set_buffer_size(self, buffer_size):
        self.buffer_size = buffer_size

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

            oldBuffer = self.media_asked_for[id_media]['received']
            # we update how much we received for this media
            self.media_asked_for[id_media]['received'] += data['chunkSize']
             #print("Downloaded "+str(self.media_asked_for[id_media]['received'])+" out of "+str(self.media_asked_for[id_media]['size'])+" for "+str(id_media))
            play_buffer = self.media_asked_for[id_media]['received']
            # if the download is complete
            if play_buffer >= self.media_asked_for[id_media]['size']:
                self.download_complete(id_media)

            # start playing the video if the buffer was previously not filled enough and is now ok
            if play_buffer >= self.buffer_size and oldBuffer < play_buffer:
                self.start_playback(id_media)
        else:
            Peer.received_callback(self, data)

    # to signal that we can start the playback
    def start_playback(self, id_media=None, data=None):
        """ To signal that we can start the playback

        Should only be called inernaly, is here so that a timer decorator
        can now when this is called and stop the timer.
        """
        if not id_media:
            id_media = data['payload']['videoId']
        print("Video "+str(id_media)+" is playing")

    # to signal that the download is complete
    def download_complete(self, id_media=None, data=None):
        if not id_media:
            id_media = data['payload']['videoId']
        print("Download of media "+str(id_media)+" completed.")

# bare bone proxy, doing almost nothing
class BaseProxy(Peer):
    """Mother of all Proxies

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

    # private
    def __pack_forward(self, data):
        forward_data = self._pack_data(data['payload'], 
                                       data['plSize'], 
                                       data['plType'], 
                                       chunk_id=data['chunkId'], 
                                       chunk_size=data['chunkSize'])
        self.active_requests[forward_data['packetId']] = {'origSender': data['sender'], 'origPackId': data['packetId']}
        return forward_data

    def _process_video_request(self, data):
        forward_data = self.__pack_forward(data)
        self.connection[data['payload']['idServer']].send(forward_data, 'forwardchunk')

    def _process_response_to(self, data):
        response_to = data['responseTo']
        req_info = self.active_requests[response_to]
        new_data = self._pack_data(data['payload'], 
                                   data['plSize'], 
                                   data['plType'], 
                                   req_info['origPackId'], 
                                   chunk_id=data['chunkId'], 
                                   chunk_size=data['chunkSize'])
        self.connection[req_info['origSender']].send(new_data, 'forwardchunk')
        if 'lastChunk' in data:
            del self.active_requests[response_to]

    def _process_other(self, data):
        real_data = self._pack_data("There you go: "+ data['payload'], response_to=data['packetId'])
        self.connection[data['sender']].send(real_data)

class FIFOProxy(AbstractProxy):

    def __init__(self, *args, **kargs):
        AbstractProxy.__init__(self, *args, **kargs)
        self.active_requests = dict()
        self.__cachedb = dict()
        self.__cache_size = 3072

class UnlimitedProxy(AbstractProxy):
    """ Proxy caching everything, without a size limit. 
    Once an object is accessed, it is stored in the cache 
    """

    def __init__(self, *args, **kargs):
        AbstractProxy.__init__(self, *args, **kargs)
        self.active_requests = dict()
        self.__cachedb = dict()

    # private
    def __pack_forward(self, data):
        forward_data = self._pack_data(data['payload'], 
                                       data['plSize'], 
                                       data['plType'], 
                                       chunk_id=data['chunkId'], 
                                       chunk_size=data['chunkSize'])
        self.active_requests[forward_data['packetId']] = {'origSender': data['sender'], 'origPackId': data['packetId']}
        return forward_data

    def _process_video_request(self, data):
        pld = data['payload']
        if pld['idVideo'] in self.__cachedb:
            video = self.__cachedb[pld['idVideo']]
            new_data = self._pack_data(video, video['size'], 
                                       'video', data['packetId'])
            self.connection[data['sender']].send(new_data)
        else:
            forward_data = self.__pack_forward(data)
            self.connection[data['payload']['idServer']].send(forward_data, 
                                                              'forwardchunk')

    def _process_response_to(self, data):
        response_to = data['responseTo']
        req_info = self.active_requests[response_to]

        pld = data['payload']
        # cache the video, unconditionally
        if pld['idVideo'] not in self.__cachedb:
            self.__cachedb[pld['idVideo']] = pld

        new_data = self._pack_data(pld, data['plSize'], data['plType'], 
                                   req_info['origPackId'], 
                                   chunk_id=data['chunkId'], 
                                   chunk_size=data['chunkSize'])
        self.connection[req_info['origSender']].send(new_data, 'forwardchunk')
        if 'lastChunk' in data:
            del self.active_requests[response_to]

    def _process_other(self, data):
        real_data = self._pack_data("There you go: "+ data['payload'], 2048, 
                                    response_to=data['packetId'])
        self.connection[data['sender']].send(real_data)

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
