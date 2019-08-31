import pytest
from race_data import data

from res_mod import Race, Start, Result

@pytest.fixture
def race():
    start = Start('','', 2, 5, '3:12:52.933')
    return Race(start)
 
def test_result_or_ab():
    items = data
    assert Race.is_result(items[0]) == False
    for i in range(1, len(items)):
        assert Race.is_result(items[i]) == True

def test_res_from_data(race):
    data = '| 1| 2| 1|  2|       6.054|'
    res = race.res_from_data(data)
    assert (res.bib, res.pulse, res.res, res.ab) == (2, 1, '6.054', 'A')
    data = '| 1| 2| 8|  2|   |      41.955|'
    res = race.res_from_data(data)
    assert (res.bib, res.pulse, res.res, res.ab) == (2, 8, '41.955', 'A')
    
def test_start_from_data(race):
    data = '| 1| 2|  2|202| 3:12:52.933'
    s = race.start_from_data(data)
    assert (s.bib_a, s.bib_b, s.time) == (2, 202, '3:12:52.933')
    assert (s.key_a, s.key_b) == ('3:12:52.933-2', '3:12:52.933-202')
    
