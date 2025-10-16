# 🚀 Airflow on Kubernetes - MLOps Demo Project

这是一个完整的**MLOps演示项目**，展示了如何在Kubernetes环境中使用Apache Airflow编排Kedro机器学习流水线，并通过MLflow进行实验追踪和模型管理。

## 📋 项目概述

### 🎯 演示目标
- **工作流编排**: 使用Airflow DAG调度和依赖管理
- **机器学习流水线**: 使用Kedro构建模块化的ML流程
- **实验追踪**: 使用MLflow记录实验指标和模型版本
- **容器化部署**: 在Kubernetes Pod中运行所有任务

### 🏗️ 技术架构
```
Airflow DAG → KubernetesPodOperator → Kedro Pipeline → MLflow Experiment
     ↓                                    ↓                   ↓
   模型注册 ← 选择最佳模型 ← 指标记录 ← 训练完成 ← 数据处理
```

## 🔧 核心组件

### 1. Airflow DAG (`dags/mlops_iris_dag.py`)
- **训练任务**: `train_iris_task` - 在K8s Pod中运行Kedro训练流水线
- **模型注册**: `register_model_task` - 从MLflow选择最佳模型并注册
- **配置管理**: 通过环境变量和Airflow Variables管理配置

### 2. Kedro ML项目 (`kedro_project/`)
- **数据加载**: 加载Iris数据集
- **数据分割**: 训练集/测试集分割
- **模型训练**: RandomForest分类器训练
- **实验记录**: 自动记录指标到MLflow

### 3. MLflow集成
- **实验追踪**: 记录训练参数、指标和模型
- **模型注册**: 自动选择最佳模型并创建版本
- **可视化**: 通过MLflow UI查看实验结果

## 📁 项目结构

```
airflow-on-k8s/
├── dags/
│   └── mlops_iris_dag.py          # Airflow DAG定义
├── scripts/
│   └── register_model.py          # 模型注册脚本
├── kedro_project/                 # Kedro ML项目
│   ├── conf/
│   │   ├── base/
│   │   │   ├── catalog.yml        # 数据目录配置
│   │   │   ├── mlflow.yml         # MLflow配置
│   │   │   └── logging.yml        # 日志配置
│   │   └── local/
│   │       └── credentials.yml    # 本地凭证
│   └── src/kedro_project/
│       ├── pipeline_registry.py   # 流水线注册
│       └── pipelines/training/
│           ├── pipeline.py        # 流水线定义
│           └── nodes.py           # 计算节点
├── requirements.txt               # Python依赖
├── CLAUDE.md                     # Claude开发指南
└── README.md                     # 项目说明
```

## 🚀 快速开始

### 前置条件
1. **Kubernetes集群** (v1.20+)
2. **kubectl** 配置就绪
3. **Helm 3** 安装
4. **MinIO** (S3兼容存储)
5. **Apache Airflow 2.0+** (支持新的DAG语法)

### 1. 部署基础服务

#### 部署MinIO (对象存储)
```bash
helm repo add minio https://helm.min.io/
helm repo update

helm install minio minio/minio \
  --namespace default \
  --set accessKey=admin \
  --set secretKey=password1234 \
  --set mode=distributed \
  --set service.type=ClusterIP
```

#### 部署MLflow (实验追踪)
```bash
# 创建MLflow命名空间
kubectl create namespace mlflow

# 创建MLflow部署文件
cat > mlflow-deployment.yaml << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mlflow
  namespace: mlflow
spec:
  replicas: 1
  selector:
    matchLabels:
      app: mlflow
  template:
    metadata:
      labels:
        app: mlflow
    spec:
      containers:
      - name: mlflow
        image: python:3.9-slim
        command: ["bash", "-c"]
        args:
        - |
          pip install mlflow boto3 && \
          mlflow server \
            --host 0.0.0.0 \
            --port 5000 \
            --backend-store-uri sqlite:///mlflow.db \
            --default-artifact-root s3://mlflow/artifacts
        env:
        - name: MLFLOW_S3_ENDPOINT_URL
          value: "http://minio.default.svc.cluster.local:9000"
        - name: AWS_ACCESS_KEY_ID
          value: "admin"
        - name: AWS_SECRET_ACCESS_KEY
          value: "password1234"
        ports:
        - containerPort: 5000
---
apiVersion: v1
kind: Service
metadata:
  name: mlflow
  namespace: mlflow
spec:
  selector:
    app: mlflow
  ports:
  - port: 5000
    targetPort: 5000
EOF

kubectl apply -f mlflow-deployment.yaml
```

#### 部署Airflow
```bash
# 创建Airflow命名空间
kubectl create namespace airflow

# 部署Airflow (使用Helm)
helm repo add apache-airflow https://airflow.apache.org
helm repo update

helm install airflow apache-airflow/airflow \
  --namespace airflow \
  --set config.airflow_core_executor=KubernetesExecutor \
  --set config.airflow_core_load_examples=False \
  --set config.airflow_core_dags_are_paused_at_creation=False
```

### 2. 配置Airflow Variables

在Airflow UI中设置以下Variables:
```
minio_access_key = admin
minio_secret_key = password1234
```

### 3. 创建ConfigMaps

```bash
# 创建DAG ConfigMap
kubectl create configmap airflow-dags \
  --from-file=dags/ \
  --from-file=scripts/ \
  --namespace=airflow

# 创建Kedro项目ConfigMap
kubectl create configmap kedro-project \
  --from-file=kedro_project/ \
  --namespace=airflow
```

### 4. 运行DAG

1. 访问Airflow UI: `http://<airflow-service>/`
2. 启用 `mlops_iris_dag`
3. 手动触发DAG执行
4. 监控任务执行状态
5. 在MLflow UI查看结果: `http://<mlflow-service>:5000`

## 🔍 监控和调试

### 查看Pod状态
```bash
kubectl get pods -n airflow
kubectl logs <pod-name> -n airflow
```

### 检查服务
```bash
kubectl get svc -n airflow
kubectl get svc -n mlflow
kubectl get svc -n default
```

### 端口转发 (本地测试)
```bash
# Airflow UI
kubectl port-forward svc/airflow-webserver 8080:8080 -n airflow

# MLflow UI
kubectl port-forward svc/mlflow 5000:5000 -n mlflow
```

## 📊 实验流程

### 1. 数据加载和预处理
- 加载Iris数据集 (150样本, 4特征, 3类别)
- 按80:20比例分割训练/测试集

### 2. 模型训练
- 使用RandomForest分类器 (100棵树)
- 记录训练指标到MLflow

### 3. 模型评估和注册
- 计算测试集准确率
- 自动选择最佳模型版本
- 注册到MLflow模型仓库

## 🔧 自定义配置

### 环境变量
```bash
# MLflow配置
export MLFLOW_TRACKING_URI="http://mlflow.mlflow.svc.cluster.local:5000"
export MLFLOW_S3_ENDPOINT_URL="http://minio.default.svc.cluster.local:9000"

# 存储凭证
export AWS_ACCESS_KEY_ID="admin"
export AWS_SECRET_ACCESS_KEY="password1234"
```

### 修改模型参数
编辑 `kedro_project/src/kedro_project/pipelines/training/nodes.py`:
```python
model = RandomForestClassifier(
    n_estimators=200,  # 增加树的数量
    max_depth=10,      # 设置最大深度
    random_state=42
)
```

## 🚨 故障排除

### 常见问题

1. **DAG解析错误**
   - 确保DAG文件没有导入MLflow等不存在的包
   - 检查Python语法是否正确
   - **TypeError: DAG.__init__() got an unexpected keyword argument 'schedule_interval'**: 使用 `schedule=None` 而不是 `schedule_interval=None` (Airflow 2.0+)
   - **AirflowException: Expected V1VolumeMount, got dict**: 使用正确的Kubernetes对象格式 `V1VolumeMount()` 和 `V1Volume()` 而不是字典格式

2. **Pod启动失败**
   - 检查镜像是否正确
   - 验证Volume挂载路径
   - 查看Pod日志: `kubectl logs <pod-name> -n airflow`

3. **MLflow连接失败**
   - 检查MLflow服务是否运行: `kubectl get pods -n mlflow`
   - 验证服务地址和端口
   - 检查网络策略

4. **模型注册失败**
   - 确保训练任务已成功完成
   - 检查MLflow实验是否存在
   - 验证S3/MinIO存储配置

### 日志位置
- **Airflow日志**: Airflow UI → Admin → Task Logs
- **Kedro日志**: Pod执行日志
- **MLflow日志**: MLflow UI 或 Pod日志

## 📚 扩展功能

### 添加新的数据集
1. 在 `nodes.py` 中添加新的数据加载函数
2. 更新 `pipeline.py` 中的流水线定义
3. 修改 `catalog.yml` 配置数据集

### 添加新的模型
1. 在 `nodes.py` 中实现新的训练函数
2. 更新流水线添加新的训练节点
3. 配置MLflow记录新的指标

### 添加超参数优化
1. 集成Optuna或Hyperopt
2. 创建参数搜索流水线
3. 配置MLflow记录参数和指标

## 🎓 学习资源

- [Kedro官方文档](https://kedro.readthedocs.io/)
- [Apache Airflow文档](https://airflow.apache.org/docs/)
- [MLflow指南](https://mlflow.org/docs/latest/index.html)
- [Kubernetes基础](https://kubernetes.io/docs/tutorials/)

## 📄 许可证

本项目仅用于教育和演示目的。

---

**🎉 现在您有了一个完整的MLOps演示项目！**

这个项目展示了现代机器学习运维的最佳实践，包括容器化、微服务架构、实验追踪和自动化工作流。
