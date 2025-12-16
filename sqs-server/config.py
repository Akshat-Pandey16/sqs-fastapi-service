import os

from dotenv import load_dotenv

load_dotenv(override=True)


class Config:
    AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
    AWS_ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL", "http://localhost:4566")
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "qyrus-assignment")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "qyrus-assignment")
    SQS_QUEUE_NAME = os.getenv("SQS_QUEUE_NAME", "orders-queue")
    SQS_MAX_NUMBER_OF_MESSAGES = int(os.getenv("SQS_MAX_NUMBER_OF_MESSAGES", 10))
    SQS_WAIT_TIME_SECONDS = int(os.getenv("SQS_WAIT_TIME_SECONDS", 5))
    SQS_VISIBILITY_TIMEOUT = int(os.getenv("SQS_VISIBILITY_TIMEOUT", 30))
    SQS_MESSAGE_PROCESSING_DELAY = float(os.getenv("SQS_MESSAGE_PROCESSING_DELAY", 1))
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    REDIS_DB = int(os.getenv("REDIS_DB", 0))


config = Config()
