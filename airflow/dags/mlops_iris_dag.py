from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
import os
import mlflow
import mlflow.sklearn
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier

# 从环境变量读取 MinIO / MLflow 配置
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow.mlflow.svc.cluster.local:5000")
MLFLOW_S3_ENDPOINT_URL = os.getenv("MLFLOW_S3_ENDPOINT_URL", "http://minio.default.svc.cluster.local:9000")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

def train_iris_model(**kwargs):
    # 设置 MLflow 环境
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    os.environ["MLFLOW_S3_ENDPOINT_URL"] = MLFLOW_S3_ENDPOINT_URL
    os.environ["AWS_ACCESS_KEY_ID"] = AWS_ACCESS_KEY_ID
    os.environ["AWS_SECRET_ACCESS_KEY"] = AWS_SECRET_ACCESS_KEY

    mlflow.set_experiment("iris-demo")

    # 加载数据
    iris = load_iris()
    X_train, X_test, y_train, y_test = train_test_split(
        iris.data, iris.target, test_size=0.2, random_state=42
    )

    with mlflow.start_run(run_name="iris_rf_run") as run:
        # 训练模型
        model = RandomForestClassifier(n_estimators=50)
        model.fit(X_train, y_train)

        # 打印准确率
        score = model.score(X_test, y_test)
        print(f"Accuracy: {score}")

        # 记录参数和指标
        mlflow.log_param("n_estimators", 50)
        mlflow.log_metric("accuracy", score)

        # 保存模型到 MLflow Artifact（MinIO）
        mlflow.sklearn.log_model(model, artifact_path="model")
        print(f"✅ MLflow run_id: {run.info.run_id}")

default_args = {
    "owner": "airflow",
    "start_date": datetime(2024, 1, 1),
    "retries": 0,
}

with DAG(
    dag_id="mlops_iris_dag",
    default_args=default_args,
    schedule_interval=None,
    catchup=False,
    tags=["mlops", "mlflow", "minio"]
) as dag:

    train_task = PythonOperator(
        task_id="train_iris_model",
        python_callable=train_iris_model,
    )

