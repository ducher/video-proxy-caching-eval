# Proxy Caching Evaluation Framework

This framework will enable you to easily evaluate your new video proxy caching algorithm or compare existing algorithms. The framework is writtent in Python 3, an easy to read and write language for an easily extensible and comprehensible framework.

## Usage
There is a command line interface with cli.py. Running it with --help will show you the different option. Running it withou arguments will look for a config.ini file to load and run the simulation according to this file.

You can also use the the orchestrator.py module with your own files. Sample files are provided, named fake\_*. In these files you can see the expected input of the two files, the trace and the databases. The output will be written in the folder given as argument to "gather\_statistics", still in orchestration.py. For now this statistics are just all the playout latencies of all clients, unidentified.

The minimal code to have is something like this:

    o = orchestration.Orchestrator(conf=conf_orch) # create a new orchestrator
    o.set_up() # loads the trace and DB, creates the model
    o.skip_inactivity = False # to have a more realistic simulation
    o.run_simulation() # runs the simulation
    o.wait_end() # waits for the simulation to 
    o.gather_statistics("stats_fake") # writes the statistics to the folder "stats_fake"

Run the program:

    ./cli.py

You can interrupt it by pressing ctrl+c in a linux terminal, it will wait until the pending downloads are done and then write the statistics to the disk. If you don't want to wait and don't need the statistics, press ctrl+c again.

## Input

As you can see in the sample files, the input is *two csv files*. Values are separated by ',' and non numerical values must be enclosed in '"'. They can be described as the following:
The first one is the database file containing a description of the videos in each video server like this:

    "id\_server","id\_video","size","duration","bitrate","title","description"
The second one is the trace file contaning the requests from the clients for a given video on a given server at a given time like this:

    "id_client","req_timestamp","id_video","id_server"

## Output

The output is also CSV files, containing the values gathered by the different metrics. For now it is just the playout latencies of each client, the number of time the playout stopped for each client and the hit rate/ cache rate of the proxy server.

## Warnings

This work is done for my masterarbeit and is not complete yet. Use it as your own "risk".

## Credits

By Pierre Ducher (pierre.ducher@gmail.com)