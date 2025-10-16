from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import KubernetesPodOperator
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
import os
import mlflow

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "retries": 0,
}

with DAG(
    dag_id="mlops_iris_dag",
    default_args=default_args,
    start_date=days_ago(1),
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
            pip install kedro mlflow boto3 scikit-learn pandas numpy && \
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
    )

    def register_latest_model():
        tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow.mlflow.svc.cluster.local:5000")
        mlflow.set_tracking_uri(tracking_uri)

        client = mlflow.tracking.MlflowClient()
        exp = client.get_experiment_by_name("iris-classification")
        runs = client.search_runs(
            experiment_ids=[exp.experiment_id],
            max_results=1,
            order_by=["metrics.accuracy DESC"],
        )

        if not runs:
            raise ValueError("No MLflow runs found, ensure Kedro training logged runs.")

        best_run = runs[0]
        run_id = best_run.info.run_id
        model_uri = f"runs:/{run_id}/model"
        model_name = "iris-classifier"

        mv = client.create_model_version(
            name=model_name,
            source=model_uri,
            run_id=run_id,
        )

        print(f"Model registered: {model_name} (version {mv.version}) from run {run_id}")

    register_model_task = PythonOperator(
        task_id="register_model_task",
        python_callable=register_latest_model,
    )

    train_iris_task >> register_model_task