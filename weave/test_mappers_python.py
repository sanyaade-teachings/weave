import math

from . import mappers_python
from . import weave_types as types


def test_map_typed_dict():
    d = {"a": 5, "b": "x"}
    d_type = types.TypeRegistry.type_of(d)
    m = mappers_python.map_to_python(d_type, None)
    d2_type = m.result_type()
    # TODO: This fails because we start with ConstString and end up with String
    # assert d_type == d2_type
    d2 = m.apply(d)
    assert d == d2
    m2 = mappers_python.map_from_python(d2_type, None)
    d3_type = m2.result_type()
    d3 = m2.apply(d2)
    assert d2 == d3
    assert d2_type == d3_type


def test_map_dict():
    d = {"a": 5, "b": 9}
    d_type = types.Dict(types.String(), types.Int())
    m = mappers_python.map_to_python(d_type, None)
    d2_type = m.result_type()
    d2 = m.apply(d)
    assert d == d2
    m2 = mappers_python.map_from_python(d2_type, None)
    d3_type = m2.result_type()
    d3 = m2.apply(d2)
    assert d2 == d3
    assert d2_type == d3_type


def test_map_type():
    t = types.TypedDict({"a": types.Int(), "b": types.String()})
    t_type = types.TypeRegistry.type_of(t)
    m = mappers_python.map_to_python(t_type, None)
    t2 = m.apply(t)
    t2_type = m.result_type()
    assert t2_type == types.Type()
    m2 = mappers_python.map_from_python(t2_type, None)
    t3_type = m2.result_type()
    assert t3_type == types.Type()
    t3 = m2.apply(t2)
    assert t == t3


def test_map_typed_dict_with_nan():
    d = {"a": 5, "b": float("nan")}
    d_type = types.TypeRegistry.type_of(d)
    m = mappers_python.map_to_python(d_type, None)
    d2_type = m.result_type()
    d2 = m.apply(d)
    m2 = mappers_python.map_from_python(d2_type, None)
    d3_type = m2.result_type()
    d3 = m2.apply(d2)
    assert d["a"] == d3["a"]
    assert math.isnan(d3["b"])
    assert d2_type == d3_type
