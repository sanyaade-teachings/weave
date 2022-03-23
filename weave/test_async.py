from . import api
from . import storage
from . import ops
from .ecosystem import async_demo
import pytest
from . import weave_objects
from . import run_obj


def test_run():
    import shutil

    try:
        shutil.rmtree("local-artifacts")
    except FileNotFoundError:
        pass

    run_id = "TESTRUN"
    run = run_obj.Run(_id=run_id, _op_name="test-run")
    run_name = "run-%s" % run_id
    storage.save(run, name=run_name)

    run_node = ops.get("%s/latest" % run_name)
    # run = api.use(run_node)
    assert api.use(run_node.state()) == "pending"
    api.use(run_node.set_state("running"))
    assert api.use(run_node.state()) == "running"
    api.use(run_node.print_("Hello"))
    api.use(run_node.print_("Hello again"))
    api.use(run_node.log({"x": 49.0}))
    api.use(run_node.set_output("some-output"))

    saved_prints = api.use(run_node.prints())
    assert saved_prints == ["Hello", "Hello again"]
    saved_logs = api.use(run_node.history())
    assert saved_logs == [{"x": 49.0}]
    saved_output = api.use(run_node.output())
    assert saved_output == "some-output"


@pytest.mark.timeout(3)
def test_automatic_await():
    import shutil

    try:
        shutil.rmtree("local-artifacts")
    except FileNotFoundError:
        pass

    twelve = async_demo.slowmult(3, 4, 0.01)
    twenty_four = async_demo.slowmult(2, twelve, 0.01)
    assert api.use(twenty_four.await_final_output()) == 24


@pytest.mark.timeout(3)
def test_stable_when_fetching_input():
    import shutil

    try:
        shutil.rmtree("local-artifacts")
    except FileNotFoundError:
        pass

    dataset = weave_objects.List([{"prompt": "a", "completion": "5"}])
    ref = storage.save(dataset)
    get_dataset = ops.get(str(ref))
    # We're going to fetch a new in memory dataset object for both of these.
    # But we should get the same run ID back because the datasets are the same
    # (which we know by checking that they come from the same ref in the code)
    run_id1 = api.use(async_demo.train(get_dataset).id())
    run_id2 = api.use(async_demo.train(get_dataset).id())
    assert run_id1 == run_id2


@pytest.mark.timeout(3)
def test_run_ops():
    twelve = async_demo.slowmult(3, 4, 0.01)

    # We can call any ops that are available on the run's output type.
    # So this should not fail!
    api.use(twelve + 9) == 21


@pytest.mark.timeout(3)
def test_async_op_expr():
    import shutil

    try:
        shutil.rmtree("local-artifacts")
    except FileNotFoundError:
        pass

    dataset = weave_objects.List([{"prompt": "a", "completion": "5"}])

    train_result = async_demo.train(dataset)
    model = train_result.model()
    saved_model = api.save(model, "model")
    version0 = api.versions(saved_model)[0]
    assert (
        str(api.expr(version0))
        == 'get("list-dataset/1214862bae4cb3c78b12af10412b29eb").train().trainresult-model().save("model")'
    )
