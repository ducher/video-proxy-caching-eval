#coding=utf-8
import csv
import sys
import traceback
import sched, time
import os

from proxycachingevalfw import *
import simu

import cProfile
import re

import threading

# this will time how long it takes to start playing a video along with how many times
# the video stopped during playback.
@TwoMethodsTimerAndCounter('request_media', 'start_playback', '_video_stopped', 0, 'id_media')
class MetricClient(Client):
    pass

class Orchestrator:
    """ Orchestrating the simulation """
    DEF_PRIO = 1
    def __init__(self, speed=1, method=None, conf={}):
        self._speed = speed
        self._clients_req = dict()
        self._clients = dict()
        self._proxy = None
        self._servers = dict()
        self._scheduler = sched.scheduler(simu.timesched, simu.sleepsched)
        self._events_queue = queue.Queue()
        """ For the event_lock method, stores the trace"""
        self.skip_inactivity = True
        """ If true, the scheduler will accelerate time when the simu is inactive """
        self._req_event = threading.Event()
        """ For the event_lock method, so that we can wait"""
        self.method = method or conf['orchestration']['method']
        print("METHOD "+self.method)
        """can either be 'scheduler' or 'event_lock'"""
        self.conf = conf


    def load_trace(self, file_path='fake_trace.dat'):
        """ Creates the clients from the trace file """
        first_tmstp = None
        #id_clients = set()
        trace_file = open(file_path, 'r')
        trace_reader = csv.DictReader(filter(lambda row: row[0]!='#', trace_file))
        # needed to have a relative delay in case of the event_lock method
        last_delay = 0
        for row in trace_reader:
            # +1000 because clients begin at id 1000
            id_client = int(row['id_client'])+1000
            if id_client not in self._clients:
                self._clients[id_client] = MetricClient(id_client, 'Client '+str(id_client-1000))
                # to keep the state of the simulation
                if self.skip_inactivity:
                    self._clients[id_client].set_func_new_dl(simu.inc_nb_dl)
                    self._clients[id_client].set_func_end_dl(simu.dec_nb_dl)
            if first_tmstp is None:
                first_tmstp = float(row['req_timestamp'])
            #id_clients.add(id_client)
            #if row['id_client'] not in self._clients_req:
            #    self._clients_req.[row['id_client']] = []
            #self._clients_req.[row['id_client']].append()
            
            #print(row)
            
            delay = float(row['req_timestamp']) - first_tmstp

            if self.method == 'event_lock':
                """ if we use the event_lock method, we store the trace in a queue"""
                event = {'delay': delay - last_delay, 'id_client': id_client, 'id_video': row['id_video'], 'id_server': int(row['id_server'])}
                last_delay = delay
                self._events_queue.put(event)
                
            elif self.method == 'scheduler':
                """ if we use the scheduler method, we enter the requests as events 
                    in the scheduler
                """
                """ adds the events in the scheduler to trigger the requests at the right time """
                self._scheduler.enter(delay, 
                                      self.DEF_PRIO, 
                                      self._clients[id_client].request_media, 
                                      argument=(row['id_video'], int(row['id_server'])))
        trace_file.close()

        #self._create_clients(list(id_clients))

        pass

    def load_video_db(self, file_path='fake_video_db.dat'):
        """ Creates the video servers from the DBs dump """ 
        #id_servers = set()
        db_file = open(file_path, 'r')
        db_reader = csv.DictReader(filter(lambda row: row[0]!='#', db_file))
        for row in db_reader:
            #id_servers.add(row['id_server'])
            id_server = int(row['id_server'])
            if id_server not in self._servers:
                self._servers[id_server] = VideoServer(id_server, 'Server '+str(id_server))
            video = {'idVideo': row['id_video'], 
                     'duration': int(row['duration']), 
                     'size': int(row['size']), 
                     'bitrate': int(row['bitrate']), 
                     'title': row['title'], 
                     'description': row['description']}

            self._servers[id_server].add_video(video=video)
            #print(row)
        db_file.close()
        pass

    def set_up(self, trace_path=None, db_path=None):
        """ sets things up """
        #trace_path = 'trace_cut.dat'
        #trace_path = 'fake_trace_fast.dat'
        #db_path = 'db_passau2.dat'
        #db_path = 'fake_video_db.dat'

        trace_path = trace_path or self.conf['orchestration']['trace_file']
        db_path = db_path or self.conf['orchestration']['db_file']

        print(trace_path)

        self.load_trace(trace_path)
        self.load_video_db(db_path)

        self._proxy = FIFOProxy(0, "Proxy")
        self._proxy.set_cache_size(16000)

        self._connect_network()

    def signal_req_event(self):
        """ function to signal that we can execute the next request
        """
        #print("signal req event")
        self._req_event.set()

    def signal_sys_inact(self):
        """ function to signal that the system is currently inactive (no downloads)
        """
        if simu.no_active_download():
            # to be sure
            self.signal_req_event()
        
    def run_simulation(self):
        """ Runs the simulation, either with a scheduler or by waiting to trigger
            each event. 

            With the event_lock method, we wait of an event to happend with a 
            timeout set to the delay until the next event. The event should be 
            triggered when all current downloads are over, which means that nothing
            is happening any more in the simulation. This happens only when the 
            skip_inactivity is set to True.

            With the scheduler method, when not skiping inactivity, we just run 
            the already filled and configured scheduler object. The option to skip
            inactivity should not be used as it is using a lot of CPU for nothing. 
        """
        if self.method == 'event_lock':

            if self.skip_inactivity:
                simu.action_when_zero = self.signal_sys_inact

            while not self._events_queue.empty():
                event = self._events_queue.get()
                print("New event: "+str(event))
                self._req_event.clear()

                if not simu.no_active_download():
                    self._req_event.wait(event['delay'])

                self._clients[event['id_client']].request_media(event['id_video'], event['id_server'])

        elif self.method == 'scheduler':
            if self.skip_inactivity:
                while True:
                    """ Inefficient way to skip the inactivity """
                    next = self._scheduler.run(False)
                    # have a threshold to avoid testing the inavtivity all the time
                    if next != None:
                        if next/config.speed >= 1:
                            # if it takes more than 1 second in real time
                            if simu.no_active_download(self._clients.values()):
                                simu.add_time(next-1)
                                print("Skiping inactivity!")
                    elif self._scheduler.empty():
                        return
                    else:
                        simu.sleep(next/2)
            else:
                self._scheduler.run()
        else:
            print("run_simulation error: no method specified!")

    def wait_end(self):
        """ Waits for for all downloads to be over """
        print("The end.")

        while not simu.no_active_download(self._clients.values()):
            print("Waiting...")
            time.sleep(1)


    def run_simulation_from_trace(self, trace_path):
        """ Not used yet """
        trace_file = open(trace_path, 'r')
        trace_reader = csv.DictReader(filter(lambda row: row[0]!='#', trace_file))
        for row in trace_reader:
            id_client = row['id_client']
            if id_client not in self._clients:
                print("Unknown client in this trace! id: "+id_client)
            else:
                self._clients[id_client].request_media(int(row['id_video']), int(row['id_server']))
            self._clients_req[row['id_client']].append()
            
            #print(row)
        trace_file.close()

        self._create_clients(list(id_clients))
        pass

    def gather_statistics(self,out_dir='stats'):
        """ writes statistics from the metrics to the out_dir 
            For now two files: clients and proxy.
            Format of clients: CSV with a latency and the corresponding id client
            Format of proxy: precomputed values like hit ratio, also CSV but one line
        """
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

        print("Writing data to "+out_dir)

        client_file = open(out_dir+'/clients', 'w', newline='')
        client_keys= ['id_client','playout_latency']
        client_writer = csv.DictWriter(client_file,client_keys,quoting=csv.QUOTE_NONNUMERIC,delimiter=',')

        client_writer.writeheader()

        print("Writing clients data...")

        row_client = dict()
        row_client['id_client'] = None
        row_client['playout_latency'] = None

        for client in self._clients.values():
            id_client = client.get_id()
            if hasattr(client, 'latencies'):
                latencies = client.latencies
                for latency in latencies:
                    row_client['id_client'] = id_client
                    row_client['playout_latency'] = latency
                    client_writer.writerow(row_client)

        client_file.close()

        if hasattr(self._proxy, 'get_stats'):
            proxy_file = open(out_dir+'/proxy', 'w', newline='')
            proxy_keys= ['id_client','playout_latency']

            id_client = client.get_id()
            proxy_stats = self._proxy.get_stats()

            print("Writing proxy data...")

            proxy_writer = csv.DictWriter(proxy_file,proxy_stats.keys(),quoting=csv.QUOTE_NONNUMERIC,delimiter=',')
            proxy_writer.writeheader()

            proxy_writer.writerow(proxy_stats)

            proxy_file.close()

        
    """
    def _configure_client(self, client):
        client.set_buffer_size()
    """
    def _create_clients(self, id_clients):
        """ Not used yet, because we don't run the simulation from trace but
            we load it first.
        """
        print("Creating clients...")
        for id_ in id_clients:
            # +1000 because clients begin at id 1000
            real_id = 1000+id_
            self._clients[real_id] = MetricClient(real_id, 'Client '+id_)

    def _create_servers(self, id_servers):
        """ Not used yet """
        print("Creating servers...")
        for id_ in id_servers:
            self._clients[id_] = VideoServer(id_, 'Server '+id_)

    def _connect_network(self):
        """ Connects all clients to the proxy and all servers to 
            to the proxy with the config parameters.
        """
        self._connect_clients(self.conf['clients']['lag_down'],
                              self.conf['clients']['down'], 
                              self.conf['clients']['up'],
                              self.conf['clients']['max_chunk'])
        self._connect_servers(self.conf['servers']['lag_down'],
                              self.conf['servers']['down'], 
                              self.conf['servers']['up'],
                              self.conf['servers']['max_chunk'])

    def _connect_clients(self, lag=0.1, bandwidth_down=4000, bandwidth_up=600, max_chunk=16):
        print("Connecting the clients...")
        for client in self._clients.values():
            client.connect_to(self._proxy).set_lag(lag).set_bandwidth(bandwidth_up).set_max_chunk(max_chunk)
            self._proxy.connect_to(client).set_lag(lag).set_bandwidth(bandwidth_down).set_max_chunk(max_chunk)

    def _connect_servers(self, lag=0.1, bandwidth_down=100000, bandwidth_up=100000, max_chunk=16):
        print("Connecting the servers...")
        for server in self._servers.values():
            server.connect_to(self._proxy).set_lag(lag).set_bandwidth(bandwidth_up).set_max_chunk(max_chunk)
            self._proxy.connect_to(server).set_lag(lag).set_bandwidth(bandwidth_down).set_max_chunk(max_chunk)
