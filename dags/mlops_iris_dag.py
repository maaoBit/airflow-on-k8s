from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from kubernetes.client.models import V1Volume, V1VolumeMount, V1Container
from datetime import datetime

import os

# Git配置 - 可通过环境变量覆盖
GIT_REPO = os.getenv("GIT_REPO", "https://github.com/maaoBit/airflow-on-k8s.git")
GIT_BRANCH = os.getenv("GIT_BRANCH", "main")

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "retries": 0,
}

# 简单的git-sync sidecar容器
def create_git_sync_container():
    """创建简单的git-sync sidecar容器"""
    return V1Container(
        name="git-sync",
        image="alpine/git",
        command=["sh", "-c"],
        args=[
            """
            echo "🔄 同步代码仓库..."
            cd /repo && \
            git clone --depth 1 --branch main https://github.com/maaoBit/airflow-on-k8s.git . && \
            echo "✅ 代码同步完成!" && \
            sleep infinity  # 保持容器运行
            """
        ],
        volume_mounts=[
            V1VolumeMount(name="git-repo-volume", mount_path="/repo")
        ]
    )

with DAG(
    dag_id="mlops_iris_dag",
    default_args=default_args,
    start_date=datetime(2025, 10, 16),
    schedule=None,
    catchup=False,
    tags=["mlops", "kedro", "iris", "git-sync"],
) as dag:

    # 训练任务 - 使用git-sync自动同步代码
    train_iris_task = KubernetesPodOperator(
        task_id="train_iris_task",
        name="train-iris",
        namespace="airflow",
        image="python:3.9-slim",
        cmds=["bash", "-c"],
        arguments=[
            """
            # 等待git-sync完成代码同步
            echo "⏳ 等待代码同步..."
            while [ ! -f "/repo/kedro_project/conf/base/catalog.yml" ]; do
                echo "等待中..."; sleep 2
            done
            echo "✅ 代码同步完成!"

            # 安装依赖并运行训练
            pip install kedro mlflow kedro-mlflow boto3 scikit-learn pandas numpy && \
            cd /repo && \
            echo "🚀 开始Kedro训练流水线..." && \
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
            V1VolumeMount(name="git-repo-volume", mount_path="/repo", read_only=False),
        ],
        volumes=[
            V1Volume(
                name="git-repo-volume",
                empty_dir={}
            ),
        ],
        # 添加git-sync sidecar
        init_containers=[create_git_sync_container()],
    )

    # 模型注册任务 - 使用git-sync同步脚本
    register_model_task = KubernetesPodOperator(
        task_id="register_model_task",
        name="register-model",
        namespace="airflow",
        image="python:3.9-slim",
        cmds=["bash", "-c"],
        arguments=[
            """
            # 等待git-sync完成脚本同步
            echo "⏳ 等待脚本同步..."
            while [ ! -f "/repo/scripts/register_model.py" ]; do
                echo "等待中..."; sleep 2
            done
            echo "✅ 脚本同步完成!"

            # 安装依赖并运行模型注册
            pip install mlflow boto3 && \
            python /repo/scripts/register_model.py
            """
        ],
        env_vars={
            "MLFLOW_TRACKING_URI": os.getenv("MLFLOW_TRACKING_URI", "http://mlflow.mlflow.svc.cluster.local:5000"),
            "MLFLOW_S3_ENDPOINT_URL": os.getenv("MLFLOW_S3_ENDPOINT_URL", "http://minio.default.svc.cluster.local:9000"),
            "AWS_ACCESS_KEY_ID": "{{ var.value.minio_access_key }}",
            "AWS_SECRET_ACCESS_KEY": "{{ var.value.minio_secret_key }}",
        },
        volume_mounts=[
            V1VolumeMount(name="git-repo-volume", mount_path="/repo", read_only=False),
        ],
        volumes=[
            V1Volume(
                name="git-repo-volume",
                empty_dir={}
            ),
        ],
        # 添加git-sync sidecar
        init_containers=[create_git_sync_container()],
    )

    train_iris_task >> register_model_task