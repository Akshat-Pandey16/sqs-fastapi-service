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
        try:
            response = self.sqs.create_queue(QueueName=config.SQS_QUEUE_NAME)
            return response["QueueUrl"]
        except Exception as e:
            raise Exception(f"Failed to get queue URL: {e}")

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

    def handle_userwise_stats(self, order_data: dict):
        try:
            user_id = order_data.get("user_id")
            order_value = round(float(order_data.get("order_value", 0)), 2)
            redis_key = f"user:{user_id}"

            self.redis_client.hincrby(redis_key, "order_count", 1)
            self.redis_client.hincrbyfloat(redis_key, "total_spend", order_value)

            return True

        except Exception as e:
            write_log(f"[REDIS ERROR] Failed to update user stats: {e}")
            return False

    def handle_global_stats(self, order_data: dict):
        try:
            global_hash_key = "global:stats"
            order_value = round(float(order_data.get("order_value", 0)), 2)

            self.redis_client.hincrby(global_hash_key, "total_orders", 1)
            self.redis_client.hincrbyfloat(
                global_hash_key, "total_revenue", order_value
            )

            return True
        except Exception as e:
            write_log(f"[REDIS ERROR] Failed to update global stats: {e}")
            return False

    def handle_redis_db_insertion(self, order_data: dict):
        try:
            userwise_stats_result = self.handle_userwise_stats(order_data)
            if not userwise_stats_result:
                write_log(
                    f"[REDIS ERROR] Failed to update user stats for user {order_data.get('user_id')}"
                )
                return False

            global_stats_result = self.handle_global_stats(order_data)
            if not global_stats_result:
                write_log("[REDIS ERROR] Failed to update global stats")
                return False

            return True

        except Exception as e:
            write_log(f"[REDIS ERROR] Failed to update Redis DB: {e}")
            return False

    def handle_message(self, messages: list):
        for message in messages:
            try:
                order_data = json.loads(message["Body"])
                log_msg = f"[USER: {order_data.get('user_id')}] [ORDER: {order_data.get('order_id')}] Received"
                write_log(log_msg)

                validation_result = self.validate_order_data(order_data)
                if not validation_result:
                    write_log(
                        f"[USER: {order_data.get('user_id')}] [ORDER: {order_data.get('order_id')}] Validation failed, deleting invalid message"
                    )
                    self.sqs.delete_message(
                        QueueUrl=self.queue_url,
                        ReceiptHandle=message["ReceiptHandle"],
                    )
                    continue

                redis_result = self.handle_redis_db_insertion(order_data)
                if not redis_result:
                    write_log(
                        f"[USER: {order_data.get('user_id')}] [ORDER: {order_data.get('order_id')}] Redis insertion failed, will retry"
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
                self.sqs.delete_message(
                    QueueUrl=self.queue_url,
                    ReceiptHandle=message["ReceiptHandle"],
                )

    def start(self):
        if not self.sqs:
            self.sqs = self.get_sqs_client()
        if not self.queue_url:
            self.queue_url = self.get_queue_url()
        if not self.redis_client:
            self.redis_client = self.get_redis_client()

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
