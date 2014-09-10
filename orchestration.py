#!/usr/bin/env python
#coding=utf-8
import csv
import sys
import sched, time
import os

from proxycachingevalfw import *
import simu

import cProfile
import re

@TwoMethodsTimerAndCounter('request_media', 'start_playback', '_video_stopped', 0, 'id_media')
class MetricClient(Client):
    pass


class Orchestrator:
    """ Orchestrating the simulation """
    DEF_PRIO = 1
    def __init__(self, speed=1):
        self._speed = speed
        self._clients_req = dict()
        self._clients = dict()
        self._proxy = None
        self._servers = dict()
        self._scheduler = sched.scheduler(simu.timesched, simu.sleepsched)
        self.skip_inactivity = True
        """ If true, the scheduler will accelerate time when the simu is inactive """


    def load_trace(self, file_path='fake_trace.dat'):
        """ Creates the clients from the trace file """
        first_tmstp = None
        #id_clients = set()
        trace_file = open(file_path, 'r')
        trace_reader = csv.DictReader(filter(lambda row: row[0]!='#', trace_file))
        for row in trace_reader:
            # +1000 because clients begin at id 1000
            id_client = int(row['id_client'])+1000
            if id_client not in self._clients:
                self._clients[id_client] = MetricClient(id_client, 'Client '+str(id_client-1000))
            if first_tmstp is None:
                first_tmstp = float(row['req_timestamp'])
            #id_clients.add(id_client)
            #if row['id_client'] not in self._clients_req:
            #    self._clients_req.[row['id_client']] = []
            #self._clients_req.[row['id_client']].append()
            
            #print(row)
            """ adds the events in the scheduler to trigger the requests at the right time """
            delay = float(row['req_timestamp']) - first_tmstp
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

    def set_up(self):
        #trace_path = 'trace_cut.dat'
        trace_path = 'fake_trace_fast.dat'
        #db_path = 'db_passau2.dat'
        db_path = 'fake_video_db.dat'
        self.load_trace(trace_path)
        self.load_video_db(db_path)

        self._proxy = FIFOProxy(0, "Proxy")

        self._connect_network()

        
    def run_simulation(self):
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

    def wait_end(self):
        print("The end.")
        while not simu.no_active_download(self._clients.values()):
            print("Waiting...")
            time.sleep(1)


    def run_simulation_from_trace(self, trace_path):
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
        """ writes statistics from the metrics to the out_dir """
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
        client_file = open(out_dir+'/clients', 'wb')

        encoding = 'UTF-8'

        for client in self._clients.values():
            latencies = client.latencies
            for latency in latencies:
                client_file.write(bytes(str(latency)+'\n', encoding))

        client_file.close()
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
            to the proxy with the default parameters.
        """
        self._connect_clients()
        self._connect_servers()

    def _connect_clients(self, lag=0.1, bandwidth_down=4000, bandwidth_up=600, max_chunk=32):
        print("Connecting the clients...")
        for client in self._clients.values():
            client.connect_to(self._proxy).set_lag(lag).set_bandwidth(bandwidth_up).set_max_chunk(max_chunk)
            self._proxy.connect_to(client).set_lag(lag).set_bandwidth(bandwidth_down).set_max_chunk(max_chunk)

    def _connect_servers(self, lag=0.1, bandwidth_down=100000, bandwidth_up=100000):
        print("Connecting the servers...")
        for server in self._servers.values():
            server.connect_to(self._proxy).set_lag(lag).set_bandwidth(bandwidth_up)
            self._proxy.connect_to(server).set_lag(lag).set_bandwidth(bandwidth_down)



o = Orchestrator()
#o.load_trace()
#o.load_video_db()

o.set_up()
o.skip_inactivity = False
#cProfile.run('o.run_simulation()')
o.run_simulation()
o.wait_end()
o.gather_statistics("stats_fake")