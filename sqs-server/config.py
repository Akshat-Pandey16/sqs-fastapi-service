import os
from dotenv import load_dotenv

load_dotenv(override=True)


class Config:
    AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
    AWS_ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566")
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "qyrus-assignment")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "qyrus-assignment")
    SQS_QUEUE_NAME = os.getenv("SQS_QUEUE_NAME", "orders-queue")


config = Config()
