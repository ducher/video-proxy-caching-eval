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

    if raw_conf.read(file):

        speed = raw_conf.getfloat('simulation', 'speed')
        wait_acc = raw_conf.getfloat('simulation', 'wait_acc')

        return True

    print("Config File "+file+" not found")
    return False




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

def set_skip_activity(value):
    global raw_conf
    raw_conf.set('orchestration', 'skip_inactivity', str(value))

def set_consume_videos(value):
    global raw_conf
    raw_conf.set('clients', 'consume_videos', str(value))

def set_trace_file(value):
    global raw_conf
    raw_conf.set('orchestration', 'trace_file', value)

def set_db_file(value):
    global raw_conf
    raw_conf.set('orchestration', 'db_file', value)

def set_speed(value):
    global raw_conf
    global speed
    raw_conf.set('simulation', 'speed', str(value))
    speed = value
