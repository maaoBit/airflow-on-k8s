from kedro.framework.hooks import hook_impl

class ProjectHooks:
    @hook_impl
    def after_context_created(self, context):
        print("Kedro context initialized with MLflow.")