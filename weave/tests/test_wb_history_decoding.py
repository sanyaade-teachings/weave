import datetime
import json
import time
import datetime

import pytest
import weave
from .. import context_state as _context
from PIL import Image
import numpy as np

from weave.wandb_client_api import wandb_gql_query
from weave.wandb_interface import wandb_stream_table


def image():
    imarray = np.random.rand(100, 100, 3) * 255
    return Image.fromarray(imarray.astype("uint8")).convert("RGBA")


_loading_builtins_token = _context.set_loading_built_ins()


@weave.type()
class TestType:
    a: int
    b: str


_context.clear_loading_built_ins(_loading_builtins_token)

base_types = {
    "number": 42,
    "string": "hello world",
    "boolean": True,
    "object": TestType(1, "hi"),
    "custom": image(),
}
base_types["list"] = list(base_types.values()) + [{**base_types}, None]
base_types["dict"] = {**base_types}

rows_tests = [
    # Here we have 1 test per type for easy debugging
    *[[{k: v}] for k, v in base_types.items()],
    # Here we have 1 test for all the types
    [base_types],
    # Here is a nasty test with really hard unions
    [
        {"a": 1, "b": "hi", "c": TestType(2, "bye"), "i": image()},
        {"a": True, "b": True, "c": True, "i": True},
        {
            "a": [
                1,
                "hi",
                True,
                TestType(2, "bye"),
                {"a": 1, "b": "hi", "c": TestType(2, "bye"), "i": image()},
            ]
        },
        {
            "randomly": {
                "nested": {
                    "objects": {
                        "a": 1,
                        "b": "hi",
                        "c": TestType(2, "bye"),
                        "i": image(),
                    }
                }
            }
        },
    ],
]


@pytest.mark.parametrize("rows", rows_tests)
def test_end_to_end_stream_table_history_path(user_by_api_key_in_env, rows):
    do_batch_test(user_by_api_key_in_env.username, rows)


def do_logging(username, rows, finish=False):
    table_name = "test_table_" + str(int(time.time()))
    st = wandb_stream_table.StreamTable(
        table_name=table_name,
        project_name="dev_test_weave_ci",
        entity_name=username,
        _disable_async_logging=True,
    )

    row_accumulator = []

    all_keys = set(["_step"])
    for row in rows:
        st.log(row)
        new_row = {
            # Extra fields automatically added from the Run
            "_step": len(row_accumulator),
            "_timestamp": datetime.datetime.now().timestamp(),
            # Extra fields automatically added from the StreamTable
            "_client_id": "dummy",
            "timestamp": datetime.datetime.utcnow(),
            # User fields
            **row,
        }
        row_accumulator.append(new_row)
        all_keys.update(list(row.keys()))

    if finish:
        st.finish()

    return row_accumulator, st, all_keys


# // I think data is screwed up on #6...
# TODO:
# I think we need to correct the nesting still...
# replace _type/_val with _val contents
#


def do_batch_test(username, rows):
    row_accumulator, st, all_keys = do_logging(username, rows)

    row_type = weave.types.TypeRegistry.type_of([{}, *row_accumulator])
    run_node = weave.ops.project(
        st._lite_run._entity_name, st._lite_run._project_name
    ).run(st._lite_run._run_name)

    def do_assertion():
        history_node = run_node.history_stream()
        row_object_type = make_optional_type(row_type.object_type)

        for key in all_keys:
            column_node = history_node[key]
            assert_type_assignment(
                row_object_type.property_types[key], column_node.type.object_type
            )
            column_value = weave.use(column_node).to_pylist_tagged()
            expected = []

            # NOTICE: This is super weird b/c right now gorilla does not
            # give back rows that are missing keys. Once this fix is deployed
            # will need to update this test
            for row in row_accumulator:
                if key in row and row[key] is not None:
                    expected.append(row[key])
            assert compare_objects(column_value, expected)

    def history_is_uploaded():
        history_node = run_node.history_stream()
        run_data = get_raw_gorilla_history(
            st._lite_run._entity_name,
            st._lite_run._project_name,
            st._lite_run._run_name,
        )
        history = run_data.get("parquetHistory", {})
        return (
            len(history.get("liveData", []))
            == len(row_accumulator)
            == (run_data.get("historyKeys", {}).get("lastStep", -999) + 1)
            and history.get("parquetUrls") == []
            and len(row_type.object_type.property_types)
            == len(history_node.type.object_type.property_types)
        )

    # First assertion is with liveset
    wait_for_x_times(history_is_uploaded)
    do_assertion()
    st.finish()

    # Second assertion is with parquet files
    wait_for_x_times(
        lambda: history_moved_to_parquet(
            st._lite_run._entity_name,
            st._lite_run._project_name,
            st._lite_run._run_name,
        )
    )
    do_assertion()


def history_moved_to_parquet(entity_name, project_name, run_name):
    history = get_raw_gorilla_history(entity_name, project_name, run_name)
    return (
        history.get("parquetHistory", {}).get("liveData") == []
        and len(history.get("parquetHistory", {}).get("parquetUrls", [])) > 0
    )


def compare_objects(a, b):
    if isinstance(a, Image.Image) and isinstance(b, Image.Image):
        return a.tobytes() == b.tobytes()
    elif isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(compare_objects(a_, b_) for a_, b_ in zip(a, b))
    elif isinstance(a, dict) and isinstance(b, dict):
        return len(a) == len(b) and all(
            k in b and compare_objects(a[k], b[k]) for k in a
        )
    return a == b


def make_optional_type(type_: weave.types.Type):
    if isinstance(type_, weave.types.List):
        type_ = weave.types.List(make_optional_type(type_.object_type))
    elif isinstance(type_, weave.types.TypedDict):
        type_ = weave.types.TypedDict(
            {k: make_optional_type(v) for k, v in type_.property_types.items()}
        )
    return weave.types.optional(type_)


def assert_type_assignment(a, b):
    if weave.types.optional(weave.types.TypedDict({})).assign_type(
        a
    ) and weave.types.optional(weave.types.TypedDict({})).assign_type(b):
        for k, ptype in a.property_types.items():
            assert k in b.property_types
            assert_type_assignment(ptype, b.property_types[k])
        return
    assert a.assign_type(b)


def wait_for_x_times(for_fn, times=10, wait=1):
    done = False
    while times > 0 and not done:
        times -= 1
        done = for_fn()
        time.sleep(wait)
    assert times > 0


def get_raw_gorilla_history(entity_name, project_name, run_name):
    query = """query WeavePythonCG($entityName: String!, $projectName: String!, $runName: String! ) {
            project(name: $projectName, entityName: $entityName) {
                run(name: $runName) {
                    historyKeys
                    parquetHistory(liveKeys: ["_timestamp"]) {
                        liveData
                        parquetUrls
                    }
                }
            }
    }"""
    variables = {
        "entityName": entity_name,
        "projectName": project_name,
        "runName": run_name,
    }
    res = wandb_gql_query(query, variables)
    return res.get("project", {}).get("run", {})


@pytest.mark.parametrize(
    "n_rows, n_cols",
    [
        # (100, 100),
        (1500, 1500),
        (10_000, 1_000),
        (1_000_000, 1_000),
        (1_000_000, 10_000),
        (10_000_000, 10_000),
    ],
)
def test_stream_table_perf(user_by_api_key_in_env, n_rows, n_cols):
    print(f"Conducting StreamTable perf test using {n_rows} rows and {n_cols} cols")
    table_name = "test_table_" + str(int(time.time()))
    st = wandb_stream_table.StreamTable(
        table_name=table_name,
        project_name="dev_test_weave_ci",
        entity_name=user_by_api_key_in_env.username,
        _disable_async_logging=True,
    )
    timings = {
        "log": 0,
        "history2_refine": 0,
        "history2_fetch_100_cols": 0,
        "history_stream_refine": 0,
        "history_stream_fetch_100_cols": 0,
    }
    print_interval = int(n_rows / 10)
    timings["log"] = 0
    for i in range(n_rows):
        row = {}
        for j in range(n_cols):
            row[f"col_{j}"] = (i * j) + (i + j)
        timings["log"] -= time.time()
        st.log(row)
        timings["log"] += time.time()
        if i % print_interval == 0:
            print(f"Logged {i} rows")
        if i % 100 == 0:
            time.sleep(0.5)

    print("Finishing Run")
    timings["log"] -= time.time()
    st.finish()
    timings["log"] += time.time()
    print(f"Log Time: {timings['log']}")

    run_node = weave.ops.project(
        st._lite_run._entity_name, st._lite_run._project_name
    ).run(st._lite_run._run_name)

    timings["history2_refine"] -= time.time()
    history2_node = run_node.history2()
    timings["history2_refine"] += time.time()
    print(f"History2 Refine Time: {timings['history2_refine']}")

    fetch_nodes = [history2_node[f"col_{i}"] for i in range(100)]
    timings["history2_fetch_100_cols"] -= time.time()
    res = weave.use(fetch_nodes)
    timings["history2_fetch_100_cols"] += time.time()
    print(f"History2 Fetch 100 Cols Time: {timings['history2_fetch_100_cols']}")

    timings["history_stream_refine"] -= time.time()
    history_stream_node = run_node.history_stream()
    timings["history_stream_refine"] += time.time()
    print(f"History Stream Refine Time: {timings['history_stream_refine']}")

    fetch_nodes = [history_stream_node[f"col_{i}"] for i in range(100)]
    timings["history_stream_fetch_100_cols"] -= time.time()
    res = weave.use(fetch_nodes)
    timings["history_stream_fetch_100_cols"] += time.time()
    print(
        f"History Stream Fetch 100 Cols Time: {timings['history_stream_fetch_100_cols']}"
    )

    print(f"Perf for {n_rows} rows and {n_cols} cols:")
    print(json.dumps(timings, indent=2))
    assert timings == None