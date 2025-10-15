import mlflow
import os
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
import pandas as pd

def load_data():
    print("🔄 Loading Iris dataset...")
    iris = load_iris(as_frame=True)
    df = iris.frame
    print(f"✅ Loaded dataset with shape: {df.shape}")
    print(f"   Features: {list(df.columns[:-1])}")
    print(f"   Target classes: {df['target'].unique()}")
    return df

def split_data(df: pd.DataFrame):
    print("🔄 Splitting data into train/test sets...")
    X = df.drop(columns=["target"])
    y = df["target"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    print(f"✅ Data split completed:")
    print(f"   Training set: {X_train.shape[0]} samples")
    print(f"   Test set: {X_test.shape[0]} samples")
    return X_train, X_test, y_train, y_test

def train_model(X_train, X_test, y_train, y_test):
    print("🚀 Starting model training...")

    # 获取MLflow配置
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow.mlflow.svc.cluster.local:5000")
    mlflow.set_tracking_uri(tracking_uri)
    print(f"   MLflow tracking URI: {tracking_uri}")

    with mlflow.start_run(run_name="iris-train") as run:
        print(f"   MLflow run ID: {run.info.run_id}")

        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)

        y_pred = model.predict(X_test)
        acc = accuracy_score(y_test, y_pred)

        # 记录参数和指标
        mlflow.log_param("n_estimators", 100)
        mlflow.log_param("test_size", 0.2)
        mlflow.log_metric("accuracy", acc)
        mlflow.log_metric("train_samples", len(X_train))
        mlflow.log_metric("test_samples", len(X_test))

        # 记录模型
        mlflow.sklearn.log_model(model, artifact_path="model")

        print(f"✅ Model training completed!")
        print(f"   Accuracy: {acc:.4f}")
        print(f"   Model logged to MLflow: {run.info.run_id}")

    return model
