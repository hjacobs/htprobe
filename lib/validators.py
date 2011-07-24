import re

class ValidateStatusCode(object):
    def __init__(self, allowed_status_codes=(200, 301, 302)):
        self.allowed_status_codes = allowed_status_codes
    def __call__(self, probe):
        if probe.status_code in self.allowed_status_codes:
            return ('OK', None)
        else:
            return ('CRITICAL', 'invalid status code')

class ValidateTimeTotal(object):
    def __init__(self, url_pattern, warning, critical):
        self.url_pattern = re.compile(url_pattern)
        self.warning = warning
        self.critical = critical
    def __call__(self, probe):
        if self.url_pattern.search(probe.url):
            if probe.time_total >= self.critical:
                return ('CRITICAL', 'time_total >= %.2f' % (self.critical,))
            if probe.time_total >= self.warning:
                return ('WARNING', 'time_total >= %.2f' % (self.warning,))
        return ('OK', None)

