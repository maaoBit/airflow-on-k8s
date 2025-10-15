from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from datetime import datetime

default_args = {
    "owner": "airflow",
    "retries": 1,
}

with DAG(
    dag_id="mlops_iris_train",
    default_args=default_args,
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["mlops"],
) as dag:

    train_iris = KubernetesPodOperator(
        namespace="airflow",
        image="maao/mlops-train:latest",
        name="train-iris",
        task_id="train_iris_task",
        env_vars={
            "MLFLOW_TRACKING_URI": "http://mlflow.mlflow.svc.cluster.local:5000",
            "MLFLOW_S3_ENDPOINT_URL": "http://minio.default.svc.cluster.local:9000",
            "AWS_ACCESS_KEY_ID": "{{ var.value.minio_access_key }}",
            "AWS_SECRET_ACCESS_KEY": "{{ var.value.minio_secret_key }}",
        },
    )

    train_iris

