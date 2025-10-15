# train/Dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY train_iris.py .

RUN pip install --no-cache-dir mlflow scikit-learn boto3

ENTRYPOINT ["python", "train_iris.py"]

