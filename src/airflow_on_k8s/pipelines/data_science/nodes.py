"""Example code for the nodes in the example pipeline. This code is meant
just for illustrating basic Kedro features.

Delete this when you start working on your own Kedro project.
"""
import logging
from typing import Any

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score


def train_model(
    train_x: pd.DataFrame, train_y: pd.DataFrame, parameters: dict[str, Any]
) -> Any:
    """Node for training a scikit-learn logistic regression model that will be
    automatically registered to MLflow Model Registry through catalog configuration.
    """
    num_iter = parameters["example_num_train_iter"]
    lr = parameters["example_learning_rate"]

    # Convert one-hot encoded labels to single column
    y_labels = np.argmax(train_y.to_numpy(), axis=1)

    # Create and train logistic regression model
    model = LogisticRegression(
        max_iter=num_iter,
        C=1.0/lr if lr > 0 else 1.0,
        multi_class='multinomial',
        solver='lbfgs',
        random_state=42
    )

    model.fit(train_x, y_labels)

    # Log metrics to MLflow (will be automatically tracked)
    train_score = model.score(train_x, y_labels)
    logging.getLogger(__name__).info(f"Training accuracy: {train_score:.4f}")

    return model


def predict(model: Any, test_x: pd.DataFrame) -> np.ndarray:
    """Node for making predictions given a pre-trained sklearn model and a test set."""
    predictions = model.predict(test_x)
    return predictions


def report_accuracy(predictions: np.ndarray, test_y: pd.DataFrame) -> None:
    """Node for reporting the accuracy of the predictions performed by the
    previous node. Notice that this function has no outputs, except logging.
    """
    # Get true class index
    target = np.argmax(test_y.to_numpy(), axis=1)
    # Calculate accuracy of predictions
    accuracy = accuracy_score(target, predictions)
    # Log the accuracy of the model
    log = logging.getLogger(__name__)
    log.info("Model accuracy on test set: %0.2f%%", accuracy * 100)


def _sigmoid(z):
    """A helper sigmoid function used by the training and the scoring nodes."""
    return 1 / (1 + np.exp(-z))
