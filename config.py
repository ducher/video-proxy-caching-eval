#coding=utf-8
# module config

import configparser

# acceleration factor of the simulation during network com
# should not be greater than ~8 for good precision
speed = 6
# acceleration factor of the simulation to wait in between
wait_acc = 1
# recomended to be 1 if you want good results, but will be slower.

raw_conf = configparser.ConfigParser()

def load_config_file(file = 'config.ini'):
    global speed
    global wait_acc
    global raw_conf

    raw_conf.read(file)

    speed = raw_conf.getfloat('simulation', 'speed')
    wait_acc = raw_conf.getfloat('simulation', 'wait_acc')

    pass




def get_sub_config_dict(file=None, sublist=None):
    global raw_conf

    if file == None:
        conf = {}
        for section in raw_conf.sections():
                if sublist == None or section in sublist:
                    conf[section] = {}
                    for option in raw_conf.options(section):
                        if option in ['skip_inactivity', 'consume_videos']:
                            conf[section][option] = raw_conf.getboolean(section, option)
                        elif option in ['speed', 'wait_acc', 'cache_size', 'up', 'down', 'lag_up', 'lag_down', 'max_chunk']:
                            conf[section][option] = raw_conf.getfloat(section, option)
                        else:
                            conf[section][option] = raw_conf.get(section, option)
        return conf

def get_config_dict(file=None):
    return get_sub_config_dict(file)

def get_orchestration_config_dict(file=None):
    return get_sub_config_dict(file, ['orchestration', 'proxy', 'clients', 'servers'])