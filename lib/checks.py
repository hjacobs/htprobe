import itertools
import operator
import re

def average_by_time(data, window_secs=30):
    data_grouped = []
    for key, group in itertools.groupby(data, lambda x: int(x[0]/window_secs)):
        sumts = 0
        sumtup = [0, 0, 0, 0, 0]
        l = 0 
        for ts, tup in group:
            sumts += ts
            for i, v in enumerate(tup):
                sumtup[i] += v
            l += 1
        data_grouped.append((sumts/l, tuple(map(lambda x: x/l, sumtup))))
    return data_grouped

class AbstractCheck(object):
    def get_matching_probes(self, pages, minutes=60):
        data = []
        for p in pages:
            for l in p.get_probes(minutes):
                for u in l:
                    if self.matches(p, u):
                        data.append(u)
        return data
    def get_max_value(self, pages):
        return max([0] + [ u.time_total for u in self.get_matching_probes(pages) ])
    def get_min_value(self, pages):
        probes = self.get_matching_probes(pages)
        if not probes:
            return 0
        return min([ u.time_total for u in probes ])
    def get_avg_value(self, pages):
        probes = self.get_matching_probes(pages)
        if not probes:
            return 0
        return sum([ u.time_total for u in self.get_matching_probes(pages) ]) / len(self.get_matching_probes(pages))
    def get_graph_data(self, pages):
        data = [ (u[1], u[4:9]) for u in self.get_matching_probes(pages, minutes=500) ]
        return average_by_time(sorted(data))
    def get_validation_errors(self, pages, validation_results):
        probes = self.get_matching_probes(pages)
        errors = []
        for probe in probes:
            res, msg = validation_results[probe]
            if res != 'OK':
                errors.append((probe, res, msg))
        return errors
    def evaluate(self, pages, validation_results):
        status = 'OK'
        probes = self.get_matching_probes(pages)
        if not probes:
            return 'UNKNOWN'
        for probe in probes:
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
    def __init__(self, name, url_pattern, negate=False):
        self.name = name
        self.url_pattern = re.compile(url_pattern)
        if negate:
            self.func = operator.not_
        else:
            self.func = bool
    def matches(self, page, probe):
        return self.func(self.url_pattern.search(probe.url))

if __name__ == '__main__':

    data = [
        (1, (1, 2, 3, 4, 5)),
        (10, (1, 2, 3, 8, 5)),
        (61, (9, 10, 11, 12, 13)),
        (123, (3, 3, 3, 3, 3))
    ]
    print average_by_time(data, window_secs=60)

