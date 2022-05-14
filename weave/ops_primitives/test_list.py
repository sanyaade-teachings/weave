from .. import api as weave
from .. import weave_types as types
from . import list_


def test_unnest():
    data = [{"a": [1, 2], "b": "x", "c": [5, 6]}, {"a": [3, 4], "b": "j", "c": [9, 10]}]
    unnested = weave.use(list_.unnest(data))
    # convert to list so pytest prints nice diffs if there is a mismatch
    assert list(unnested) == [
        {"a": 1, "b": "x", "c": 5},
        {"a": 2, "b": "x", "c": 6},
        {"a": 3, "b": "j", "c": 9},
        {"a": 4, "b": "j", "c": 10},
    ]


def test_op_list():
    node = list_.make_list(a=1, b=2, c=3)
    assert node.type == types.List(types.Int())
