#!/usr/bin/python

import datetime
import httplib
import os
import socket
import urlparse
import re
import socket
import time
import BeautifulSoup
import urlparse
from optparse import OptionParser

timeout = 30
user_agent = 'htprobe 0.1'

debug_log = []

def log(msg):
    if msg.startswith(' '):
        debug_log.append('                ' + msg.lstrip())
    else:
        debug_log.append(datetime.datetime.now().strftime('%H:%M:%S.%f') + ' ' + msg) 

class PageProbe(object):
    def __init__(self, url):
        self.url = url
        self.probes = []
        self.id = time.strftime('%Y%m%d%H%M%S-') + url2path(self.url)

class ProbeResult(object):
    def __init__(self, url, original_url=None):
        self.url = url
        self.original_url = original_url
        self.html = False
        self.time_dns = 0
        self.time_connect = 0
        self.time_request = 0
        self.time_response = 0
        self.time_total = 0
        self.status_code = 0
        self.response_body = ''

def url2path(url):
    pat = re.compile('[^a-z0-9._-]+')
    return pat.sub('_', url.lower())[:100]

def rewrite_urls(content, probes):
    pat = re.compile('<base[^>]*>')
    content = pat.sub('', content)
    for r in probes:
        if r.original_url:
            content = content.replace(r.original_url, url2path(r.url))
    return content

def dump_probe(probe, path):
    path = os.path.join(path, probe.id)
    os.mkdir(path)
    #tar = tarfile.open(mode='w:gz', fileobj=fd)
    with open(os.path.join(path, 'perfdata.tsv'), 'wb') as fd:
        for r in probe.probes:
            fd.write('\t'.join(map(str, (r.url, r.status_code,
                r.time_dns, r.time_connect, r.time_request, r.time_response, r.time_total,
                len(r.response_body)))))
            fd.write('\n')
    with open(os.path.join(path, 'debug.log'), 'wb') as fd:
        for line in debug_log:
            fd.write(line)
            fd.write('\n')
    assets = os.path.join(path, 'assets')
    os.mkdir(assets)
    for r in probe.probes:
        with open(os.path.join(assets, url2path(r.url)), 'wb') as fd:
            fd.write(r.response_body)
        if r.html:
            try: 
                rewritten_body = rewrite_urls(r.response_body.decode('utf-8'), probe.probes)
                with open(os.path.join(assets, url2path(r.url) + '.rewritten.html'), 'wb') as fd:
                    fd.write(rewritten_body.encode('utf-8'))
            except UnicodeDecodeError, e:
                log('HTML response of {0} not UTF-8 encoded: {1}'.format(r.url, e))
    

def probe(url):
    r = ProbeResult(url)
    scheme, unused, host_port, path = url.split('/', 3)
    host, unused, port = host_port.partition(':')
    try:
        port = int(port)
    except ValueError:
        if scheme == 'https':
            port = 443
        else:
            port = 80
    path = '/' + path

    start = time.time()
    log('Resolving {0}'.format(host))
    try:
        r.addr = socket.gethostbyname(host)
    except socket.gaierror, e:
        log('Failed to resolve DNS for {0}'.format(host))
        log('  socket.gaierror: {0}'.format(e))
        r.status_code = 903
        r.time_dns = time.time() - start
        last = r.time_dns
        for a in ('time_connect', 'time_request', 'time_response'):
            v = getattr(r, a)
            if not v:
                setattr(r, a, last)
            last = v
        r.time_total = time.time() - start    
        return r

    r.time_dns = time.time() - start

    log('Connecting to {0}|{1}|{2}'.format(host, r.addr, port))
    conn = httplib.HTTPConnection(r.addr, port=port, timeout=timeout)
    try:
        conn.connect()
        r.time_connect = time.time() - start
        log('GET {0}'.format(path))
        conn.request('GET', path, None, {'Host': host, 'User-Agent': user_agent})
        r.time_request = time.time() - start
        resp = conn.getresponse()
        log('  {0} {1}'.format(resp.status, resp.reason))
        for key, val in sorted(resp.getheaders()):
            log('  {0}: {1}'.format(key.capitalize(), val))
        r.status_code = resp.status
        r.time_response = time.time() - start
        r.response_body = resp.read()
        r.time_total = time.time() - start
        conn.close()
        log('Downloaded {0} Bytes'.format(len(r.response_body)))
    except socket.timeout, e:
        log('  socket.timeout: {0}'.format(e))
        r.status_code = 901
        last = r.time_dns
        for a in ('time_connect', 'time_request', 'time_response'):
            v = getattr(r, a)
            if not v:
                setattr(r, a, last)
            last = v
        r.time_total = time.time() - start    
    except socket.error, e:
        log('  socket.error: {0}'.format(e))
        r.status_code = 902
        last = r.time_dns
        for a in ('time_connect', 'time_request', 'time_response'):
            v = getattr(r, a)
            if not v:
                setattr(r, a, last)
            last = v
        r.time_total = time.time() - start    
    return r


def probe_page(url):
    p = PageProbe(url)

    r = probe(url)
    p.probes.append(r)

    soup = BeautifulSoup.BeautifulSoup(r.response_body)
    if soup.html:
        r.html = True
    base = r.url
    if soup.base:
        base = soup.base['href']

    def mkabs(url, base=base):
        url = urlparse.urljoin(base, url)
        return url

    css_assets = set()
    for style in soup.findAll('link', {'rel':'stylesheet'}):
        css_url = mkabs(style['href'])
        r = probe(css_url)
        r.original_url = style['href']
        p.probes.append(r)
        for url in re.findall('url\(([^)]*)\)', r.response_body):
            css_assets.add(mkabs(url.strip('\'"'), base=css_url))

    for script in soup.findAll('script', {'src':True}):
        r = probe(mkabs(script['src']))
        r.original_url = script['src']
        p.probes.append(r)

    img_urls = set()
    for img in soup.findAll('img', {'src': True}):
        if img['src'] not in img_urls:
            img_urls.add(mkabs(img['src']))
            r = probe(mkabs(img['src']))
            r.original_url = img['src']
            p.probes.append(r)

    for asset_url in sorted(css_assets):
        r = probe(asset_url)
        p.probes.append(r)

    for iframe in soup.findAll('iframe', {'src': True}):
        r = probe(mkabs(iframe['src']))
        p.probes.append(r)

    for icon in soup.findAll('link', {'rel':'icon'}):
        icon_url = mkabs(icon['href'])
        r = probe(icon_url)
        r.original_url = icon['href']
        p.probes.append(r)

    p.links = []
    for a in soup.findAll('a', {'href': True}):
        url = mkabs(a['href'])
        p.links.append(url)
        #print url
    return p

parser = OptionParser(usage='usage: %prog [options] <URL> <RESULT_PATH>')
parser.add_option('-q', '--quiet', action='store_true', dest='quiet', help='silent mode: do not print informational messages')
parser.add_option('-u', '--user-agent', dest='user_agent', default=user_agent, help='use custom user agent HTTP header')
parser.add_option('-t', '--timeout', dest='timeout', default=timeout, help='socket timeout in seconds')
parser.add_option('-v', '--verbose', action='store_true', dest='verbose', help='verbose mode: output debug messages')
(options, args) = parser.parse_args()

if len(args) != 2:
    parser.error('incorrect number of arguments')

timeout = float(options.timeout)
user_agent = options.user_agent

p = probe_page(args[0])
path = args[1]

dump_probe(p, path)

if not options.quiet:
    print 'Probed {0} urls in {1:.2} seconds with {2} Bytes total size'.format(len(p.probes),
        sum([ r.time_total for r in p.probes ]),
        sum([ len(r.response_body) for r in p.probes ]))
    if options.verbose:
        print '\n'.join(debug_log)


