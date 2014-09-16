#coding=utf-8
# helper functions for simulation purpose

import time
import threading
import config


def sleep(delay, transfer=True):
    """ sleep function accelerated according to the speed of simulation """

    speed = config.speed
    if not transfer:
        speed = config.speed*config.wait_acc
    time.sleep(delay/speed)

def sleepsched(delay):
    sleep(delay, False)

def time_(transfer=True):
    """ returns the time according to the simulation.
            if transfer is true, it won't take the the additionnal acceleration
            for the waiting periods into account
    """
    speed = config.speed
    if not transfer:
        speed = config.speed*config.wait_acc

    return time.monotonic() * speed

base_time = 0
""" can be incremented to skip through time """

def timesched():
    global base_time
    return time_(False) + base_time

def add_time(amount):
    """ skip through time """
    global base_time
    base_time += amount

def real_time(time):
    """ converts simulation time to real time """
    return time * config.speed

# def no_active_download(clients):
#   """ returns true if no client from the list is currently downloading """
#   """ Inefficient way to check if there are still downloads pending """
#   for client in clients:
#       if client.media_downloading > 0:
#           #print("Guilty: "+client.name)
#           return False
#   return True


""" The following is used to determine when the system is not downloading antyhing """

def default_action_when_zero():
    print("System inactive!")
    pass

nb_dl = 0
""" number of curent downloads """
lock = threading.RLock()
""" To proect nb_dl """
action_when_zero = default_action_when_zero
""" Function to call when nb_dl == 0 """

def inc_nb_dl():
    """ Function to be called when a new download is pending """
    global nb_dl
    global lock
    with lock:
        nb_dl += 1
    #print("State nb_dl: "+str(nb_dl))


def dec_nb_dl():
    """ Function to be called when a download is over """
    global nb_dl
    global lock
    with lock:
        nb_dl -= 1
    if nb_dl < 1:
        action_when_zero()
    #print("State nb_dl: "+str(nb_dl))

def no_active_download(clients=None):
    """ Returns true if the number of downloads is zero.
        Parameter is for backward compatibility only.
    """
    global nb_dl
    return nb_dl == 0