from spin.cli import reverse_toposort
from spin.util import SpinError
from pytest import raises

def test_valid():
    nodes = [1, 2, 3]
    graph = {1: [2], 2: [3]}
    assert reverse_toposort(nodes, graph) == [3, 2, 1]


def test_loop():
    nodes = [1, 2, 3]
    graph = {1: [2], 2: [3], 3: [1]}
    with raises(SpinError, match='.*cycle'):
        assert reverse_toposort(nodes, graph) == []
    
