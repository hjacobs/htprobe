htprobe
=======

Requirements
------------

* python 2.6+
* BeautifulSoup (tolerant HTML parsing)
* cherrypy (simple HTTP server)
* jinja2 (template engine)

Getting Started
---------------

A step by step tutorial for Debian/Ubuntu users.

First install python and all necessary dependencies (please note: for probing (htprobe.py) you need only python and BeautifulSoup)

    sudo apt-get install python python-setuptools
    sudo easy_install BeautifulSoup cherrypy jinja2

Create the log and results directory:

    mkdir -p logs results/local01

Do a first sample probe (this will create a new subfolder below results/local01):

    ./htprobe.py http://www.srcco.de/ results/local01

Wait a few seconds (or minutes) and do another sample probe:

    ./htprobe.py http://www.srcco.de/ results/local01

Now you will have two probes sitting below results/local01.
To see the results we copy our sample config file and start up our HTTP monitor server:

    cp config.py.sample config.py
    ./htmon.py results

Now direct your browser to http://localhost:8081/ and you should see a nice first status overview.
You can add another probe anytime by calling htprobe.py as described above -- htmon.py will poll the results directory for new probes every 5 seconds.
