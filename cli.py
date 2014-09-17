#!/usr/bin/env python3
#coding=utf-8
# command line interface

import config
import orchestration
import time
import argparse
import sys

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("--verbosity", help="increase output verbosity", action="store_true")
    parser.add_argument("--config", metavar='/path/to/conf.ini', help="use this .ini file for the configuration")
    parser.add_argument("--skip", dest='skip_inactivity', help="override the ini conf to skip inactivity", action="store_true")
    parser.add_argument("--no-skip", dest='skip_inactivity', help="override the ini conf to skip inactivity", action="store_false")
    parser.set_defaults(skip_inactivity=None)
    parser.add_argument("--trace", metavar='/path/to/trace.dat', help="override the ini conf for the trace file")
    parser.add_argument("--db", metavar='/path/to/db.dat', help="override the ini conf for the database file")
    parser.add_argument("--consume", dest='consume_videos', help="override the ini conf to consume videos", action="store_true")
    parser.add_argument("--no-consume", dest='consume_videos', help="override the ini conf to consume videos", action="store_false")
    parser.set_defaults(consume_videos=None)
    parser.add_argument("--speed", type=int, metavar='6', help="override the ini conf for the speed of the simulation")
    args = parser.parse_args()

    if args.verbosity:
        print("verbosity turned on")

    if args.config:
        if not config.load_config_file(args.config):
            sys.exit()
    else:
        if not config.load_config_file():
            sys.exit()

    if args.skip_inactivity != None:
        config.set_skip_activity(args.skip_inactivity)

    if args.consume_videos != None:
        config.set_consume_videos(args.consume_videos)

    if args.trace:
        config.set_trace_file(args.trace)
    if args.db:
        config.set_db_file(args.db)
    if args.speed:
        config.set_speed(args.speed)


    conf = config.get_config_dict()
    conf_orch = config.get_orchestration_config_dict()

    print(str(conf))


    o = orchestration.Orchestrator(conf=conf_orch)
    #o.load_trace()
    #o.load_video_db()
    o.skip_inactivity = conf['orchestration']['skip_inactivity']
    o.method = conf['orchestration']['method']

    o.set_up()

    #cProfile.run('o.run_simulation()')
    # overriding the simulation speed
    #config.speed = 2
    o.run_simulation()
    o.wait_end()
    
    o.gather_statistics(conf['data']['data_out'])
