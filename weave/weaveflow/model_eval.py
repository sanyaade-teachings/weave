import typing
import weave

from .dataset import Dataset
from .model import Model
from .evaluate import Evaluate
from ..parallelism import do_in_parallel


@weave.op()
def evaluate(eval: Evaluate, dataset: Dataset, model: Model) -> typing.Any:
    outputs = []
    ds_rows = list(dataset.rows)

    def do_one(row: typing.Any) -> typing.Any:
        print("evaluating row", row)
        return model.predict(row)

    # do one row serially to publish everything
    outputs = [do_one(ds_rows[0])]

    outputs.extend(list(do_in_parallel(do_one, ds_rows[1:])))

    eval_result = eval.compute(dataset, outputs)
    summary = eval_result["summary"]
    eval_table_columns: dict[str, weave.WeaveList] = {
        "dataset_id": weave.WeaveList([r["id"] for r in ds_rows]),
        "output": weave.WeaveList(outputs),
        **eval_result["columns"],
    }
    return {
        "summary": summary,
        "eval_table": weave.WeaveList(eval_table_columns),
    }
