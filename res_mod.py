from collections import namedtuple

Result = namedtuple('Result', ['key', 'ab', 'bib', 'pulse', 'time'])
Start = namedtuple('Start', ['key_a', 'key_b', 'bib_a', 'bib_b', 'time'])

#class Race()
    #start
    #a
    #b
    #results

def is_result(data_str):
    last = data_str.strip()[-1]
    if last == '|':
        return True
    return False

def start_from_data(data_str):
    _, _, _, bib_a, bib_b, time = (i.strip() for i in data_str.split('|'))
    bib_a, bib_b = map(int, (bib_a, bib_b))
    key_a = '{}-{}'.format(time, bib_a)
    key_b = '{}-{}'.format(time, bib_b)
    start = Start(key_a, key_b, bib_a, bib_b, time)
    return start

def res_from_data(data_str):
    _, _, _,  pulse, bib, time, *xx = (i.strip() for i in data_str.split('|'))
    if time.strip() == '':
        time = xx[0]
    bib, pulse = map(int, (bib, pulse))
    ab = 'A' if bib < 100 else 'B'
    key = get_key(bib)
    res = Result(key, ab, bib, pulse, time)
    return res

def get_key(bib):
    key = '{}-{}'.format('3:12:52.933', bib)
    return key
