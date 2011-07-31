import datetime

def parse_date(d):
    if not d:
        return None
    d = d.strip().lower()
    if d == 'now':
        return datetime.datetime.now()
    elif len(d) == 10 and '-' in d:
        return datetime.datetime.strptime(d, '%Y-%m-%d')
    elif len(d) == 16:
        return datetime.datetime.strptime(d, '%Y-%m-%d %H:%M')
    elif len(d) == 19:
        return datetime.datetime.strptime(d, '%Y-%m-%d %H:%M:%S')
    elif len(d) == 10 and d.startswith('1'):
        # looks like unix timestamp: 1311631200
        return datetime.datetime.fromtimestamp(int(d))

    days = h = m = 0
    if d.endswith('d'):
        try:
            days = int(d.rstrip('d'))
        except ValueError:
            pass
    elif d.endswith('h'):
        try:
            h = int(d.rstrip('h'))
        except ValueError:
            pass
    elif d.endswith('m'):
        try:
            m = int(d.rstrip('m'))
        except ValueError:
            pass
    else:
        try:
            h = int(d)
        except ValueError:
            pass
    return datetime.datetime.now() + datetime.timedelta(days=days, hours=h, minutes=m)

