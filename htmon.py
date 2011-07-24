#!/usr/bin/python

import cherrypy
import collections
import itertools
import logging
import logging.config
import os
import sys
import time
import urlparse
import lib.jinjatool
import config

logging.basicConfig()
logging.config.fileConfig('logging.conf')

expose = cherrypy.expose
jinja = cherrypy.tools.jinja


class Page(object):
    def __init__(self, url):
        self.url = url
        self.probes = collections.deque(maxlen=100)
    def add_probe(self, probe):
        self.probes.append(probe)
    def http_errors(self):
        return [ (l.ts, l.url, l.status_code) for l in itertools.chain(*self.probes) if l.status_code not in (200, 301, 302) ]
    def max_time_total(self):
        return max([ p[0].time_total for p in self.probes])
    def min_time_total(self):
        return min([ p[0].time_total for p in self.probes])
    def avg_time_total(self):
        return sum([ p[0].time_total for p in self.probes]) / len(self.probes)
    def get_probes(self, minutes):
        cutoff = time.time() - minutes*60
        for p in self.probes:
            if p[0].ts > cutoff:
                yield p

class Root(object):
    _cp_config = {
        'tools.staticdir.root': os.path.dirname(os.path.abspath(__file__)),
        'tools.staticfile.root': os.path.dirname(os.path.abspath(__file__))
    }

    @expose
    @jinja(tpl='index.html')
    def index(self):
        return {'checks': config.checks, 'pages': pages, 'validation_results': validation_results}

    @expose
    @jinja(tpl='probes.html')
    def probes(self, check_id=None):
        selected_probes = set()
        if check_id:
            selected_probes.update(config.checks[int(check_id)-1].get_matching_probes(pages.values()))
        return {'pages': pages, 'validation_results': validation_results, 'selected_probes': selected_probes}


class BackgroundPollerPlugin(cherrypy.process.plugins.Monitor):
    def __init__(self, bus, frequency=5):
        cherrypy.process.plugins.Monitor.__init__(self, bus, self.run, frequency)
        self.probes_by_node = {}
        nodes = sorted(os.listdir(path))
        for node in nodes:
            node_dir = os.path.join(path, node)
            probes = set(os.listdir(node_dir))
            self.probes_by_node[node] = probes
        

    def _run(self):
        # self.bus.log('Polling')
        nodes = sorted(os.listdir(path))
        for node in nodes:
            node_dir = os.path.join(path, node)
            old_probes = self.probes_by_node.get(node, set())
            probes = set(os.listdir(node_dir))
            new_probes = probes - old_probes
            if not new_probes:
                continue
            self.bus.log('Found new probes from node {0}: {1}'.format(node, ', '.join(sorted(new_probes))))
            for probe in sorted(new_probes):
                perfdata = read_perfdata(node_dir, probe)
                page = pages.get(perfdata[0].url)
                if not page:
                    page = Page(perfdata[0].url)
                    pages[page.url] = page
                page.add_probe(perfdata)
            self.probes_by_node[node] = probes

    def run(self):
        try:
            self._run()
        except:
            self.bus.log('Exception while polling for new probes', traceback=True)

ProbePerfData = collections.namedtuple('ProbePerfData', 'node ts url status_code time_dns time_connect time_request time_response time_total response_body_length')

path = sys.argv[1]

nodes = sorted(os.listdir(path))
pages = {}
validation_results = {}

def validate_probe(probe):
    for validator in config.validators:
        res, errors = validator(probe) 
        if res != 'OK':
            return (res, errors)
    return ('OK', None)

def read_perfdata(node_dir, probe):
    ts = time.mktime(time.strptime(probe[:14], '%Y%m%d%H%M%S'))
    perfdata = []
    perffile = os.path.join(node_dir, probe, 'perfdata.tsv')
    node = os.path.basename(node_dir)
    tsum = 0
    with open(perffile) as fd:
        for line in fd:
            cols = line.rstrip().split('\t')
            cols = [node, ts + tsum, cols[0], int(cols[1])] + map(float, cols[2:-1]) + [int(cols[-1])]
            p = ProbePerfData._make(cols)
            tsum += p.time_total
            validation_results[p] = validate_probe(p)
            perfdata.append(p)
    return perfdata

for node in nodes:
    node_dir = os.path.join(path, node)
    probes = sorted(os.listdir(node_dir))
    for probe in probes:
        perfdata = read_perfdata(node_dir, probe)
        page = pages.get(perfdata[0].url)
        if not page:
            page = Page(perfdata[0].url)
            pages[page.url] = page
        page.add_probe(perfdata)
        
conf = os.path.dirname(os.path.abspath(__file__)) + '/site.conf'
cherrypy.config.update(conf)

app = cherrypy.tree.mount(Root(), '', conf) 
poller_plugin = BackgroundPollerPlugin(cherrypy.engine, frequency=app.config['poller']['frequency'])
poller_plugin.subscribe()
cherrypy.engine.start()
cherrypy.engine.block()


