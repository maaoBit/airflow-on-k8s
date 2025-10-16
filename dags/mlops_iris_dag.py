from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from datetime import datetime

import os

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "retries": 0,
}

with DAG(
    dag_id="mlops_iris_dag",
    default_args=default_args,
    start_date=datetime(2025, 10, 16),
    schedule_interval=None,
    catchup=False,
    tags=["mlops", "kedro", "iris"],
) as dag:

    train_iris_task = KubernetesPodOperator(
        task_id="train_iris_task",
        name="train-iris",
        namespace="airflow",
        image="python:3.9-slim",
        cmds=["bash", "-c"],
        arguments=[
            """
            pip install kedro mlflow kedro-mlflow boto3 scikit-learn pandas numpy && \
            cd /project && \
            echo "Running Kedro training pipeline..." && \
            kedro run --pipeline=training
            """
        ],
        env_vars={
            "MLFLOW_TRACKING_URI": os.getenv("MLFLOW_TRACKING_URI", "http://mlflow.mlflow.svc.cluster.local:5000"),
            "MLFLOW_S3_ENDPOINT_URL": os.getenv("MLFLOW_S3_ENDPOINT_URL", "http://minio.default.svc.cluster.local:9000"),
            "AWS_ACCESS_KEY_ID": "{{ var.value.minio_access_key }}",
            "AWS_SECRET_ACCESS_KEY": "{{ var.value.minio_secret_key }}",
        },
        volume_mounts=[
            {
                "name": "dags-volume",
                "mount_path": "/opt/airflow/dags",
                "read_only": True,
            },
            {
                "name": "kedro-project-volume",
                "mount_path": "/project",
                "read_only": True,
            }
        ],
        volumes=[
            {
                "name": "dags-volume",
                "config_map": {
                    "name": "airflow-dags"
                }
            },
            {
                "name": "kedro-project-volume",
                "config_map": {
                    "name": "kedro-project"
                }
            }
        ],
    )

    register_model_task = KubernetesPodOperator(
        task_id="register_model_task",
        name="register-model",
        namespace="airflow",
        image="python:3.9-slim",
        cmds=["bash", "-c"],
        arguments=[
            """
            pip install mlflow boto3 && \
            python /opt/airflow/dags/scripts/register_model.py
            """
        ],
        env_vars={
            "MLFLOW_TRACKING_URI": os.getenv("MLFLOW_TRACKING_URI", "http://mlflow.mlflow.svc.cluster.local:5000"),
            "MLFLOW_S3_ENDPOINT_URL": os.getenv("MLFLOW_S3_ENDPOINT_URL", "http://minio.default.svc.cluster.local:9000"),
            "AWS_ACCESS_KEY_ID": "{{ var.value.minio_access_key }}",
            "AWS_SECRET_ACCESS_KEY": "{{ var.value.minio_secret_key }}",
        },
        volume_mounts=[
            {
                "name": "dags-volume",
                "mount_path": "/opt/airflow/dags",
                "read_only": True,
            }
        ],
        volumes=[
            {
                "name": "dags-volume",
                "config_map": {
                    "name": "airflow-dags"
                }
            }
        ],
    )

    train_iris_task >> register_model_task