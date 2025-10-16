# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个Apache Airflow在Kubernetes上的机器学习运维(MLOps)项目，主要功能是使用Airflow编排Kubernetes Pod中的Kedro机器学习流水线，并结合MLflow进行实验追踪。

## 项目架构

### 核心组件
- **Airflow DAGs** (`dags/`): 工作流编排层，使用KubernetesPodOperator在K8s中执行ML任务
- **Kedro项目** (`kedro_project/`): 机器学习流水线实现，包含数据加载、训练、评估等节点
- **配置管理** (`kedro_project/conf/`): 分层配置（base/和local/），支持MLflow、存储和凭证配置

### 技术栈
- Apache Airflow (工作流编排)
- Kubernetes (容器编排)
- Kedro (ML流水线框架)
- MLflow (实验追踪)
- MinIO/S3 (对象存储)
- scikit-learn (机器学习)

## 常用开发命令

### Airflow相关
```bash
# 启动Airflow服务
airflow webserver
airflow scheduler

# 安装Python依赖
pip install -r requirements.txt

# 验证DAG语法
python dags/mlops_iris_dag.py
```

### Kedro流水线相关
```bash
# 在kedro_project目录下运行
kedro run --pipeline=training    # 运行训练流水线
kedro build                      # 构建项目
kedro catalog list              # 查看数据目录配置
kedro info                       # 显示流水线信息
```

### Docker和Kubernetes相关
```bash
# 构建Docker镜像（如需要）
docker build -t kedro-ml-pipeline .

# Kubernetes操作
kubectl get pods -n airflow
kubectl logs <pod-name> -n airflow
```

## 核心配置说明

### 环境变量
- `MLFLOW_TRACKING_URI`: MLflow追踪服务地址
- `MLFLOW_S3_ENDPOINT_URL`: MinIO/S3端点地址
- `AWS_ACCESS_KEY_ID`: AWS或MinIO访问密钥
- `AWS_SECRET_ACCESS_KEY`: AWS或MinIO秘密密钥

### Kubernetes服务发现
- MLflow服务: `mlflow.mlflow.svc.cluster.local:5000`
- MinIO服务: `minio.default.svc.cluster.local:9000`

## 项目结构要点

### DAG文件结构 (`dags/mlops_iris_dag.py`)
- 使用`KubernetesPodOperator`定义所有任务，避免DAG处理器导入问题
- 主要任务：`train_iris_task`（训练）和`register_model_task`（模型注册）
- 通过Airflow Variables管理敏感配置
- **重要**: 所有ML相关的函数都移到单独的脚本文件中，避免DAG解析错误

### Kedro流水线 (`kedro_project/src/kedro_project/pipelines/training/`)
- `pipeline.py`: 流水线定义和节点连接
- `nodes.py`: 具体计算节点实现（load_data, split_data, train_model）

### 配置文件 (`kedro_project/conf/`)
- `base/catalog.yml`: 数据集存储配置
- `base/mlflow.yml`: MLflow实验配置
- `local/credentials.yml`: 本地开发凭证（不应提交到版本控制）

### 脚本文件 (`scripts/`)
- `register_model.py`: MLflow模型注册脚本，从DAG中提取以避免导入问题

## 开发工作流

1. **本地开发**: 在`kedro_project/`目录下使用`kedro run`测试流水线
2. **Kubernetes测试**: 通过Airflow UI触发DAG执行
3. **实验追踪**: 在MLflow UI中查看实验结果和模型指标
4. **配置管理**: 修改`conf/base/`中的配置文件，避免直接修改代码

## 注意事项

- 凭证文件 `kedro_project/conf/local/credentials.yml` 包含敏感信息，不应提交到版本控制
- Kubernetes集群中需要预先部署MLflow和MinIO服务
- Airflow需要配置Kubernetes连接权限
- 修改DAG后需要在Airflow UI中刷新才能看到更新
- **DAG解析兼容性**: 所有ML相关代码必须移到单独脚本中，因为Airflow DAG处理器容器不包含ML包
- **Volume挂载**: DAG中的Pod任务需要正确挂载ConfigMap以访问脚本文件
- **Airflow版本兼容性**: 使用 `schedule=None` 而不是 `schedule_interval=None` (Airflow 2.0+)