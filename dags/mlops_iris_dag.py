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
            export http_proxy=http://192.168.2.1:4780 && \
            export https_proxy=http://192.168.2.1:4780 && \
            git clone --depth 1 --branch main https://github.com/maaoBit/airflow-on-k8s.git . && \
            echo "✅ 代码同步完成!"
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
        image="python:3.11-slim",
        cmds=["bash", "-c"],
        arguments=[
            """
            echo "📁 项目目录内容:"
            ls -la /repo/
            echo "📁 Kedro项目内容:"
            ls -la /repo/kedro_project/

            # 安装Poetry并使用它安装依赖
            echo "🔧 安装Poetry..."
            pip install poetry && \
            cd /repo && \
            echo "🔧 配置Poetry..."
            poetry config virtualenvs.create false && \
            echo "🔧 使用Poetry安装依赖..."
            poetry install && \
            cd kedro_project && \
            echo "🚀 开始Kedro训练流水线..." && \
            echo "📋 当前目录: $(pwd)" && \
            echo "📋 项目文件: $(ls -la pyproject.toml)" && \
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
        image="python:3.11-slim",
        cmds=["bash", "-c"],
        arguments=[
            """
            # 安装Poetry并安装项目依赖
            pip install poetry && \
            cd /repo && \
            poetry config virtualenvs.create false && \
            poetry install && \
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