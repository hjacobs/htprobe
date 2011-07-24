import re

class AbstractCheck(object):
    def _get_matching_probes(self, pages):
        data = []
        for p in pages:
            for l in p.probes:
                for u in l:
                    if self.matches(p, u):
                        data.append(u)
        return data
    def get_max_value(self, pages):
        return max([0] + [ u.time_total for u in self._get_matching_probes(pages) ])
    def get_min_value(self, pages):
        probes = self._get_matching_probes(pages)
        if not probes:
            return 0
        return min([ u.time_total for u in probes ])
    def get_avg_value(self, pages):
        probes = self._get_matching_probes(pages)
        if not probes:
            return 0
        return sum([ u.time_total for u in self._get_matching_probes(pages) ]) / len(self._get_matching_probes(pages))
    def get_graph_data(self, pages):
        data = [ (u[1], u[4:9]) for u in self._get_matching_probes(pages) ]
        return data
    def evaluate(self, pages, validation_results):
        status = 'OK'
        for probe in self._get_matching_probes(pages):
            res, msg = validation_results[probe]
            if res == 'CRITICAL':
                return res
            elif res != 'OK':
                status = res
        return status

class PageCheck(AbstractCheck):
    def __init__(self, name, url_pattern):
        self.name = name
        self.url_pattern = re.compile(url_pattern)
    def matches(self, page, probe):
        return probe.url == page.url and self.url_pattern.search(page.url)
    
class UrlCheck(AbstractCheck):
    def __init__(self, name, url_pattern):
        self.name = name
        self.url_pattern = re.compile(url_pattern)
    def matches(self, page, probe):
        return self.url_pattern.search(probe.url)
