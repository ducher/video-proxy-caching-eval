#!/usr/bin/env python
#coding=utf-8
import csv
import sys
import sched, time

from proxycachingevalfw import *

class Orchestrator:
    """ Orchestrating the simulation """
    DEF_PRIO = 1
    def __init__(self, speed=1):
        self._speed = speed
        self._clients_req = dict()
        self._clients = dict()
        self._proxy = None
        self._servers = dict()
        self._scheduler = sched.scheduler(time.time, time.sleep)


    def load_trace(self, file_path='fake_trace.dat'):
        """ Creates the clients from the trace file """
        first_tmstp = None
        #id_clients = set()
        trace_file = open(file_path, 'r')
        trace_reader = csv.DictReader(filter(lambda row: row[0]!='#', trace_file))
        for row in trace_reader:
            id_client = int(row['id_client'])
            if id_client not in self._clients:
                self._clients[id_client] = Client(id_client, 'Client '+str(id_client))
            if first_tmstp is None:
                first_tmstp = int(row['req_timestamp'])
            #id_clients.add(id_client)
            #if row['id_client'] not in self._clients_req:
            #    self._clients_req.[row['id_client']] = []
            #self._clients_req.[row['id_client']].append()
            
            #print(row)
            delay = int(row['req_timestamp']) - first_tmstp
            self._scheduler.enter(delay, 
                                  self.DEF_PRIO, 
                                  self._clients[id_client].request_media, 
                                  argument=(int(row['id_video']), int(row['id_server'])))
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
            video = {'idVideo': int(row['id_video']), 
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
        trace_path = 'fake_trace_fast.dat'
        self.load_trace(trace_path)
        self.load_video_db()

        self._proxy = UnlimitedProxy(0, "Proxy")

        self._connect_network()

        
    def run_simulation(self):
        self._scheduler.run()


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

    def _create_clients(self, id_clients):
        print("Creating clients...")
        for id_ in id_clients:
            self._clients[id_] = Client(id_, 'Client '+id_)

    def _create_servers(self, id_servers):
        print("Creating servers...")
        for id_ in id_servers:
            self._clients[id_] = VideoServer(id_, 'Server '+id_)

    def _connect_network(self):
        self._connect_clients()
        self._connect_servers()

    def _connect_clients(self, lag=0.1, bandwidth_down=4000, bandwidth_up=600):
        print("Connecting the clients...")
        for client in self._clients.values():
            print(client)
            client.connect_to(self._proxy).set_lag(lag).set_bandwidth(bandwidth_up)
            self._proxy.connect_to(client).set_lag(lag).set_bandwidth(bandwidth_down)

    def _connect_servers(self, lag=0.1, bandwidth_down=100000, bandwidth_up=100000):
        print("Connecting the servers...")
        for server in self._servers.values():
            print(server)
            server.connect_to(self._proxy).set_lag(lag).set_bandwidth(bandwidth_up)
            self._proxy.connect_to(server).set_lag(lag).set_bandwidth(bandwidth_down)



o = Orchestrator()
#o.load_trace()
#o.load_video_db()

o.set_up()
o.run_simulation()