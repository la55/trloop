from race_data import data

import res_mod
 
def test_result_or_ab():
    items = data
    assert res_mod.is_result(items[0]) == False
    for i in range(1, len(items)):
        assert res_mod.is_result(items[i]) == True

def test_res_from_data():
    data = '| 1| 2| 1|  2|       6.054|'
    res = res_mod.res_from_data(data)
    assert (res.bib, res.pulse, res.time, res.ab) == (2, 1, '6.054', 'A')
    data = '| 1| 2| 8|  2|   |      41.955|'
    res = res_mod.res_from_data(data)
    assert (res.bib, res.pulse, res.time, res.ab) == (2, 8, '41.955', 'A')
    
def test_start_from_data():
    data = '| 1| 2|  2|202| 3:12:52.933'
    s = res_mod.start_from_data(data)
    assert (s.bib_a, s.bib_b, s.time) == (2, 202, '3:12:52.933')
    assert (s.key_a, s.key_b) == ('3:12:52.933-2', '3:12:52.933-202')
    
