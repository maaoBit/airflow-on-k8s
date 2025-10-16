#!/usr/bin/env python3
"""
注册最新MLflow模型的脚本
用于在Kubernetes Pod中执行，避免在Airflow DAG处理器中导入MLflow
"""

import os
import sys
import mlflow


def register_latest_model():
    """
    从MLflow实验中找到最佳模型并注册
    """
    # 统一环境变量默认值，与DAG保持一致
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow.mlflow.svc.cluster.local:5000")
    mlflow.set_tracking_uri(tracking_uri)

    print(f"Connecting to MLflow at: {tracking_uri}")

    try:
        client = mlflow.tracking.MlflowClient()
        exp = client.get_experiment_by_name("iris-classification")

        if exp is None:
            raise ValueError("Experiment 'iris-classification' not found. Ensure training pipeline has run first.")

        print(f"Found experiment: {exp.name} (ID: {exp.experiment_id})")

        runs = client.search_runs(
            experiment_ids=[exp.experiment_id],
            max_results=1,
            order_by=["metrics.accuracy DESC"],
        )

        if not runs:
            raise ValueError("No MLflow runs found, ensure Kedro training logged runs.")

        best_run = runs[0]
        run_id = best_run.info.run_id
        accuracy = best_run.data.metrics.get("accuracy", 0.0)
        model_uri = f"runs:/{run_id}/model"
        model_name = "iris-classifier"

        print(f"Best run: {run_id} with accuracy: {accuracy:.4f}")

        mv = client.create_model_version(
            name=model_name,
            source=model_uri,
            run_id=run_id,
        )

        print(f"✅ Model registered successfully!")
        print(f"   Model: {model_name}")
        print(f"   Version: {mv.version}")
        print(f"   Run ID: {run_id}")
        print(f"   Accuracy: {accuracy:.4f}")

    except Exception as e:
        print(f"❌ Error registering model: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    register_latest_model()