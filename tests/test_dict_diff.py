import pytest
import copy


class Compare(object):
    def __init__(self):
        self._diff = {}
    
    def diff(self, d1, d2):
        self._recursive_compare(d1, d2)
        return self._diff

    def _recursive_compare(self, d1, d2, level='root'):
        if isinstance(d1, dict) and isinstance(d2, dict):
            if d1.keys() != d2.keys():
                s1 = set(d1.keys())
                s2 = set(d2.keys())
                print('{:<20} + {} - {}'.format(level, s1-s2, s2-s1))
                common_keys = s1 & s2
            else:
                common_keys = set(d1.keys())
            for k in common_keys:
                self._recursive_compare(d1[k], d2[k], level='{}.{}'.format(level, k))
        elif isinstance(d1, list) and isinstance(d2, list):
            if len(d1) != len(d2):
                print('{:<20} len1={}; len2={}'.format(level, len(d1), len(d2)))
            common_len = min(len(d1), len(d2))
            for i in range(common_len):
                self._recursive_compare(d1[i], d2[i], level='{}[{}]'.format(level, i))
        else:
            if d1 != d2:
                diff = '{:<20} {} != {}'.format(level, d1, d2)
                self._nested_set(level.split('.')[1:], d2)

    def _nested_set(self, keys, value):
        d = self._diff
        for key in keys[:-1]:
            if key in d:
                d = d[key]
            else:
                d = d.setdefault(key, {})
        d[keys[-1]] = value

def test_recursive_compare():
    first = {
        'a': 1,
        'b': 'one',
        'c': {
            'd': 2,
            'e': 'two'
        }
    }
    second = copy.deepcopy(first)
    second['b'] = 'three'
    second['c']['d'] = 3

    diff = Compare().diff(first, second)
    assert(len(diff.keys()) == 2)
    assert(len(diff['c'].keys()) == 1)
    assert(diff['b'] == 'three')
    assert(diff['c']['d'] == 3)

def test_obj_compare():
    a = lambda: None
    a.name = 'asdf'
    b = lambda: None
    b.name = 'asdf'
    a.c = lambda: None
    b.c = lambda: None
    a.c.name ='asdf'
    b.c.name = 'ddd'
    diff = Compare().diff(a, b)
    assert(len(diff.keys))
    

if __name__ == '__main__':
    pytest.main(['-s', __file__])
