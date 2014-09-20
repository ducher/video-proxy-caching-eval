#!/usr/bin/env python3
#coding=utf-8
# command line interface

import config
import orchestration
import metrics
import time
import argparse
import sys
# to run multiple simulation at the same time
from multiprocessing import Pool
# for partial
import functools
import copy

#def compare(prox1, prox2):

def run_simu(conf_orch, data_out):
    o = orchestration.Orchestrator(conf=conf_orch)
    #o.load_trace()
    #o.load_video_db()
    o.skip_inactivity = conf_orch['orchestration']['skip_inactivity']
    o.method = conf_orch['orchestration']['method']

    o.set_up()

    #cProfile.run('o.run_simulation()')
    # overriding the simulation speed
    #config.speed = 2
    o.run_simulation()
    o.wait_end()

    return o.gather_statistics(data_out, graphs=False)

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
    parser.add_argument("--out", metavar='/path/to/stats', help="override the ini conf for the output folder")
    parser.add_argument("--proxy", metavar='FIFOProxy', help="override the ini conf for the proxy to use")
    parser.add_argument("--parallel", help="use true parallelism when comparing", action="store_true")
    parser.set_defaults(parallel=False)
    parser.add_argument("--compare-to", dest='proxy2', metavar='LRUProxy', help="compare the first proxy to this one")
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
    if args.out:
        config.set_data_out(args.out)
    if args.proxy:
        config.set_proxy_type(args.proxy)


    conf = config.get_config_dict()
    conf_orch = config.get_orchestration_config_dict()

    print(str(conf))
    
    if args.proxy2:
        conf_orch2 = copy.deepcopy(conf_orch)
        conf_orch2['proxy']['proxy_type'] = args.proxy2  

        
        
        run_simu_out = functools.partial(run_simu, data_out=conf['data']['data_out'])

        result = []

        if args.parallel:
            pool = Pool(processes=2)
            result = pool.map(run_simu_out, [conf_orch, conf_orch2])
        else:
            result.append(run_simu_out(conf_orch))
            result.append(run_simu_out(conf_orch2))
        lpc1 = None
        ps1 = None
        (lpc1, ps1) = result[0]

        lpc2 = None
        ps2 = None
        (lpc2, ps2) = result[1]
        
        plts = metrics.PlotStats()
        plts.plot_bar(conf['data']['data_out'], 
                      (conf['proxy']['proxy_type'], args.proxy2), 
                      lpc1, 
                      lpc2)

        plts.plot_cache_stats(conf['data']['data_out'], 
                              {
                                conf['proxy']['proxy_type']:ps1,
                                args.proxy2:ps2
                              }
                              )
    else:
        lpc1 = None
        ps1 = None
        
        plts = metrics.PlotStats()
        (lpc1, ps1) = run_simu(conf_orch, conf['data']['data_out'])
        plts.plot_bar(conf['data']['data_out'], 
                      (conf['proxy']['proxy_type'],), 
                      lpc1)
        plts.plot_cache_stats(conf['data']['data_out'], 
                              {
                                conf['proxy']['proxy_type']:ps1,
                              }
                              )

    #print(str(result))

    
