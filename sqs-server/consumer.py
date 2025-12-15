import json
import time
import boto3
from logger import write_log
from config import config


class Consumer:
    def __init__(self):
        self.sqs = None
        self.queue_url = None

    def start(self):
        self.sqs = boto3.client(
            "sqs",
            region_name=config.AWS_REGION,
            endpoint_url=config.AWS_ENDPOINT_URL,
            aws_access_key_id=config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
        )

        try:
            response = self.sqs.get_queue_url(QueueName=config.SQS_QUEUE_NAME)
            self.queue_url = response["QueueUrl"]
            write_log(f"Consumer connected to queue: {self.queue_url}")
        except Exception as e:
            write_log(f"Error getting queue URL: {e}")
            return

        write_log("Consumer started receiving messages...")

        while True:
            try:
                response = self.sqs.receive_message(
                    QueueUrl=self.queue_url,
                    MaxNumberOfMessages=10,
                    WaitTimeSeconds=5,
                    VisibilityTimeout=30,
                )

                if "Messages" in response:
                    for message in response["Messages"]:
                        try:
                            order_data = json.loads(message["Body"])
                            log_msg = f"Received Order: {json.dumps(order_data)}"
                            write_log(log_msg)

                            self.sqs.delete_message(
                                QueueUrl=self.queue_url,
                                ReceiptHandle=message["ReceiptHandle"],
                            )
                            write_log(
                                f"Order {order_data['order_id']} processed successfully"
                            )

                        except (json.JSONDecodeError, KeyError) as e:
                            write_log(f"Error processing message: {e}")

            except Exception as e:
                write_log(f"Error receiving messages: {e}")
                time.sleep(5)


consumer = Consumer()
