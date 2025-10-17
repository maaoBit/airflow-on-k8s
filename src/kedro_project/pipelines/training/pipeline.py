from kedro.pipeline import Pipeline, node
from .nodes import load_data, split_data, train_model

def create_pipeline(**kwargs):
    return Pipeline([
        node(load_data, None, "raw_data"),
        node(split_data, "raw_data", ["X_train", "X_test", "y_train", "y_test"]),
        node(train_model, ["X_train", "X_test", "y_train", "y_test"], "model"),
    ])
