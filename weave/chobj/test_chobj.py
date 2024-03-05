from typing import Any
import pytest
import chobj
import dataclasses


@pytest.fixture
def server():
    server = chobj.ObjectServer()
    server.drop_tables()
    server.create_tables()
    yield server


@pytest.fixture
def client():
    yield chobj.ObjectClient()


def test_table_create(server):
    table_ref = server.new_table([1, 2, 3])
    assert list(server.get_table(table_ref)) == [1, 2, 3]


def test_table_append(server):
    table_ref = server.new_table([1, 2, 3])
    new_table_ref, item_id = server.table_append(table_ref, 4)
    assert list(server.get_table(new_table_ref)) == [1, 2, 3, 4]


def test_table_remove(server):
    table_ref0 = server.new_table([1])
    table_ref1, item_id2 = server.table_append(table_ref0, 2)
    table_ref2, item_id3 = server.table_append(table_ref1, 3)
    table_ref3 = server.table_remove(table_ref2, item_id2)
    assert list(server.get_table(table_ref3)) == [1, 3]


def new_val_single(server):
    obj_id = server.new_val(42)
    assert server.get(obj_id) == 42


def test_new_val_with_list(server):
    ref = server.new_val({"a": [1, 2, 3]})
    server_val = server.get(ref)
    table_ref = server_val["a"]
    assert isinstance(table_ref, chobj.TableRef)
    table_val = server.get(table_ref)
    assert list(table_val) == [1, 2, 3]


# def test_nested_list_append(server):
#     ref = server.new_val({"a": [1, 2, 3]})
#     ref = ref.with_path("a")
#     ref = server.table_append(ref, [5, 6, 7])


def test_object(server):
    obj_ref = server.new_object({"a": 43}, "my-obj", "latest")
    val_ref = server.resolve_object("my-obj", "latest")
    assert obj_ref.val_id == val_ref.val_id
    assert server.resolve_object("my-obj", "latest2") is None


def test_save_load(client):
    ref = client.save({"a": [1, 2, 3]}, "my-obj")
    val = client.get(ref)
    assert val["a"][0] == 1
    assert val["a"][1] == 2
    assert val["a"][2] == 3


def test_dataset(client):
    @dataclasses.dataclass
    class Dataset:
        rows: list[Any]

    ref = client.save(Dataset([1, 2, 3]), "my-dataset")


# def test_publish_big_list(server):
#     import time

#     t = time.time()
#     big_list = list({"x": i, "y": i} for i in range(1000000))
#     print("create", time.time() - t)
#     t = time.time()
#     ref = server.new({"a": big_list})
#     print("insert", time.time() - t)
#     t = time.time()
#     res = server.get(ref)
#     print("get", time.time() - t)
#     assert res == {"a": big_list}