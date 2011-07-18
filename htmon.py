#!/usr/bin/python

import collections
import os
import sys
import time
import urlparse

path = sys.argv[1]

nodes = sorted(os.listdir(path))

ProbePerfData = collections.namedtuple('ProbePerfData', 'ts url status_code time_dns time_connect time_request time_response time_total response_body_length')



for node in nodes:
    node_dir = os.path.join(path, node)
    probes = sorted(os.listdir(node_dir))
    for probe in probes:
        ts = time.strptime(probe[:14], '%Y%m%d%H%M%S')
        perffile = os.path.join(node_dir, probe, 'perfdata.tsv')
        with open(perffile) as fd:
            for line in fd:
                cols = line.rstrip().split('\t')
                cols = [ts, cols[0], int(cols[1])] + map(float, cols[2:-1]) + [int(cols[-1])]
                row = ProbePerfData._make(cols)
                o = urlparse.urlparse(row.url)
                print o.netloc
                print row
            

