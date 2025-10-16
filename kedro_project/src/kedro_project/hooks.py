from kedro.framework.hooks import hook_impl
from kedro_mlflow.framework.hooks import MlflowHook

# 使用 kedro-mlflow 进行自动 MLflow 集成
mlflow_hook = MlflowHook()

class ProjectHooks:
    @hook_impl
    def after_context_created(self, context):
        print("Kedro context initialized with MLflow.")
