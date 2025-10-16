import mlflow
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
import pandas as pd

def load_data():
    iris = load_iris(as_frame=True)
    df = iris.frame
    return df

def split_data(df: pd.DataFrame):
    X = df.drop(columns=["target"])
    y = df["target"]
    return train_test_split(X, y, test_size=0.2, random_state=42)

def train_model(X_train, X_test, y_train, y_test):
    with mlflow.start_run(run_name="iris-train"):
        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        acc = accuracy_score(y_test, y_pred)

        mlflow.log_metric("accuracy", acc)
        mlflow.sklearn.log_model(model, artifact_path="model")

        print(f"Model trained with accuracy: {acc:.4f}")
    return model
