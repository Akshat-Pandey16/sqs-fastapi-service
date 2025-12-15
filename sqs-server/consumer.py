import json
import time
import boto3
from logger import write_log
from config import config
from redis import Redis


class Consumer:
    def __init__(self):
        self.sqs = None
        self.queue_url = None
        self.redis_client = None

    def get_sqs_client(self):
        self.sqs = boto3.client(
            "sqs",
            region_name=config.AWS_REGION,
            endpoint_url=config.AWS_ENDPOINT_URL,
            aws_access_key_id=config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
        )
        return self.sqs

    def get_queue_url(self):
        response = self.sqs.get_queue_url(QueueName=config.SQS_QUEUE_NAME)
        return response["QueueUrl"]

    def get_redis_client(self):
        self.redis_client = Redis(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            db=config.REDIS_DB,
        )
        return self.redis_client

    def validate_order_data(self, order_data: dict):
        order_id = order_data.get("order_id")
        user_id = order_data.get("user_id")
        order_value = order_data.get("order_value")

        if not order_id or not order_id.startswith("ORD"):
            write_log(f"[ERROR] Invalid/missing order ID: {order_id}, skipping order")
            return False
        if not user_id or not user_id.startswith("U"):
            write_log(f"[ERROR] Invalid/missing user ID: {user_id}, skipping order")
            return False
        if not order_value or order_value <= 0:
            write_log(
                f"[ERROR] Invalid/missing order value: {order_value}, skipping order"
            )
            return False

        calculated_order_value = 0
        for item in order_data.get("items", []):
            calculated_order_value += item.get("quantity") * item.get("price_per_unit")

        if round(calculated_order_value, 2) != round(order_value, 2):
            write_log(
                f"[ERROR] Order value mismatch: {round(calculated_order_value, 2)} != {round(order_value, 2)}, fixing with correct value"
            )

            order_data["order_value"] = calculated_order_value
        return True

    def handle_message(self, messages: list):
        for message in messages:
            try:
                order_data = json.loads(message["Body"])
                log_msg = f"[USER: {order_data.get('user_id')}] [ORDER: {order_data.get('order_id')}] Received"
                write_log(log_msg)

                result = self.validate_order_data(order_data)
                if not result:
                    write_log(
                        f"[USER: {order_data.get('user_id')}] [ORDER: {order_data.get('order_id')}] Validation failed, skipping order"
                    )
                    continue

                write_log(
                    f"[USER: {order_data.get('user_id')}] [ORDER: {order_data.get('order_id')}] Processed successfully"
                )

                self.sqs.delete_message(
                    QueueUrl=self.queue_url,
                    ReceiptHandle=message["ReceiptHandle"],
                )

            except (json.JSONDecodeError, KeyError) as e:
                write_log(f"[ERROR] Error processing message: {e}")

    def start(self):
        write_log("[INFO] Checking for SQS client connection...")
        if not self.sqs:
            self.sqs = self.get_sqs_client()
        write_log("[INFO] SQS client connection established")
        write_log("[INFO] Checking for queue URL...")
        if not self.queue_url:
            self.queue_url = self.get_queue_url()
        write_log(f"[INFO] Queue URL obtained: {self.queue_url}")
        write_log("[INFO] Checking for Redis client connection...")
        if not self.redis_client:
            self.redis_client = self.get_redis_client()
        write_log("[INFO] Redis client connection established")

        write_log("[INFO] Consumer started receiving messages...")

        while True:
            try:
                response = self.sqs.receive_message(
                    QueueUrl=self.queue_url,
                    MaxNumberOfMessages=config.SQS_MAX_NUMBER_OF_MESSAGES,
                    WaitTimeSeconds=config.SQS_WAIT_TIME_SECONDS,
                    VisibilityTimeout=config.SQS_VISIBILITY_TIMEOUT,
                )
                if "Messages" in response:
                    self.handle_message(response["Messages"])
                else:
                    time.sleep(float(config.SQS_MESSAGE_PROCESSING_DELAY))

            except Exception as e:
                write_log(f"[ERROR] Error receiving messages: {e}")
                time.sleep(float(config.SQS_MESSAGE_PROCESSING_DELAY))


consumer = Consumer()
