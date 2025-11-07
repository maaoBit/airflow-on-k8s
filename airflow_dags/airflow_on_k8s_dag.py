from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.providers.cncf.kubernetes.operators.pod import KubernetesPodOperator
from kubernetes.client import V1Volume, V1VolumeMount, V1PersistentVolumeClaimVolumeSource

# Kedro settings required to run your pipeline
env = "local"
pipeline_name = "__default__"
project_path = Path.cwd()
package_name = "airflow_on_k8s"
conf_source = "" or Path.cwd() / "conf"

# Kubernetes settings
NAMESPACE = "airflow"  # 修改为您的Kubernetes命名空间
DOCKER_IMAGE = "registry.paas/ai/airflow-on-k8s:latest"  # 修改为您的Docker镜像

# 共享存储配置
SHARED_VOLUME_NAME = "kedro-data-volume"
SHARED_STORAGE_PATH = "/home/kedro_docker/data"  # Kedro数据目录在容器内的路径
PVC_NAME = "kedro-shared-pvc"  # PVC名称，需要在Kubernetes中预先创建


# Using a DAG context manager, you don't have to specify the dag property of each task
with DAG(
    dag_id="airflow-on-k8s",
    start_date=datetime(2023,1,1),
    max_active_runs=3,
    # https://airflow.apache.org/docs/stable/scheduler.html#dag-runs
    schedule=None,
    catchup=False,
    # Default settings applied to all tasks
    default_args=dict(
        owner="airflow",
        depends_on_past=False,
        email_on_failure=False,
        email_on_retry=False,
        retries=1,
        retry_delay=timedelta(minutes=5)
    )
) as dag:
    # 共享存储配置 (用于除init_data外的其他任务)
    shared_volumes = {
        "volumes": [
            V1Volume(
                name=SHARED_VOLUME_NAME,
                persistent_volume_claim=V1PersistentVolumeClaimVolumeSource(claim_name=PVC_NAME)
            )
        ],
        "volume_mounts": [
            V1VolumeMount(
                name=SHARED_VOLUME_NAME,
                mount_path=SHARED_STORAGE_PATH,
                sub_path=None
            )
        ]
    }

    tasks = {
        "init_data": KubernetesPodOperator(
            task_id="init_data",
            name="init-data",
            namespace=NAMESPACE,
            image=DOCKER_IMAGE,
            cmds=["bash", "-c"],
            arguments=[
                """
                set -e  # 遇到错误立即退出

                echo "=== 开始初始化共享存储数据 ==="

                # 检查原始数据目录是否存在
                if [ ! -d "/home/kedro_docker/data" ]; then
                    echo "错误: 原始数据目录不存在 /home/kedro_docker/data"
                    exit 1
                fi

                # 检查共享存储挂载点
                if [ ! -d "/tmp/shared_storage" ]; then
                    echo "错误: 共享存储挂载点不存在 /tmp/shared_storage"
                    exit 1
                fi

                # 检查是否已初始化
                if [ -d "/tmp/shared_storage/01_raw" ]; then
                    echo "✓ 共享存储中已存在数据，跳过初始化"
                    echo "当前数据内容:"
                    ls -la /tmp/shared_storage/
                    exit 0
                fi

                # 执行数据复制
                echo "正在复制原始数据到共享存储..."
                echo "从: /home/kedro_docker/data"
                echo "到: /tmp/shared_storage"
                cp -rv /home/kedro_docker/data/* /tmp/shared_storage/

                # 验证复制结果
                echo "验证数据复制结果..."
                if [ -d "/tmp/shared_storage/01_raw" ]; then
                    echo "✓ 数据初始化成功！"
                    echo "共享存储内容:"
                    ls -la /tmp/shared_storage/
                else
                    echo "❌ 数据初始化失败"
                    exit 1
                fi
                """
            ],
            get_logs=True,
            is_delete_operator_pod=True,
            # init_data使用不同的挂载配置
            volumes=[
                V1Volume(
                    name=SHARED_VOLUME_NAME,
                    persistent_volume_claim=V1PersistentVolumeClaimVolumeSource(claim_name=PVC_NAME)
                )
            ],
            volume_mounts=[
                V1VolumeMount(
                    name=SHARED_VOLUME_NAME,
                    mount_path="/tmp/shared_storage"
                )
            ]
        ),
        "split": KubernetesPodOperator(
            task_id="split",
            name="split",
            namespace=NAMESPACE,
            image=DOCKER_IMAGE,
            cmds=["kedro"],
            arguments=["run", f"--nodes=split"],
            get_logs=True,
            is_delete_operator_pod=True,
            **shared_volumes
        ),
        "train": KubernetesPodOperator(
            task_id="train",
            name="train",
            namespace=NAMESPACE,
            image=DOCKER_IMAGE,
            cmds=["kedro"],
            arguments=["run", f"--nodes=train"],
            get_logs=True,
            is_delete_operator_pod=True,
            **shared_volumes
        ),
        "predict": KubernetesPodOperator(
            task_id="predict",
            name="predict",
            namespace=NAMESPACE,
            image=DOCKER_IMAGE,
            cmds=["kedro"],
            arguments=["run", f"--nodes=predict"],
            get_logs=True,
            is_delete_operator_pod=True,
            **shared_volumes
        ),
        "report": KubernetesPodOperator(
            task_id="report",
            name="report",
            namespace=NAMESPACE,
            image=DOCKER_IMAGE,
            cmds=["kedro"],
            arguments=["run", f"--nodes=report"],
            get_logs=True,
            is_delete_operator_pod=True,
            **shared_volumes
        )
    }
    # 设置任务依赖关系：首先初始化数据，然后执行原始流程
    tasks["init_data"] >> tasks["split"]
    tasks["split"] >> tasks["train"]
    tasks["split"] >> tasks["predict"]
    tasks["train"] >> tasks["predict"]
    tasks["split"] >> tasks["report"]
    tasks["predict"] >> tasks["report"]