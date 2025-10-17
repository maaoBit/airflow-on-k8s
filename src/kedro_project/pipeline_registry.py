from kedro.pipeline import Pipeline
from kedro_project.pipelines.training import pipeline as training_pipeline

def register_pipelines() -> dict[str, Pipeline]:
    return {
        "training": training_pipeline.create_pipeline(),
        "__default__": training_pipeline.create_pipeline(),
    }
