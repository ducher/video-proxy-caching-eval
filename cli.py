#!/usr/bin/env python3
#coding=utf-8
# command line interface

import config
import orchestration
import time


if __name__ == "__main__":
    config.load_config_file()

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
    # waiting for everything to be really done
    time.sleep(5)
    o.gather_statistics(conf['data']['data_out'])
