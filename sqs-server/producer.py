import json
from datetime import datetime
from random import choice, randint, uniform

import boto3
from config import config


class Producer:
    def __init__(self):
        self.sqs = boto3.client(
            "sqs",
            region_name=config.AWS_REGION,
            endpoint_url=config.AWS_ENDPOINT_URL,
            aws_access_key_id=config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
        )
        self.queue_url = self.get_queue_url()

    def get_queue_url(self):
        try:
            response = self.sqs.create_queue(QueueName=config.SQS_QUEUE_NAME)
            return response["QueueUrl"]
        except Exception as e:
            raise Exception(f"Failed to get queue URL: {e}")

    def generate_random_order(self):
        should_generate_invalid = randint(1, 100) <= 20

        order_id = f"ORD{randint(1000, 9999)}"
        user_id = f"U{randint(1000, 1005)}"

        if should_generate_invalid:
            invalid_type = randint(1, 4)
            if invalid_type == 1:
                order_id = f"INVALID{randint(1000, 9999)}"
            elif invalid_type == 2:
                user_id = f"INVALID{randint(1000, 1005)}"

        products = [
            {"id": "P001", "name": "Laptop", "price": (500, 1500)},
            {"id": "P002", "name": "Mouse", "price": (10, 50)},
            {"id": "P003", "name": "Keyboard", "price": (30, 150)},
            {"id": "P004", "name": "Monitor", "price": (200, 800)},
            {"id": "P005", "name": "Headphones", "price": (50, 300)},
            {"id": "P006", "name": "Webcam", "price": (40, 200)},
        ]

        num_items = randint(1, 100)
        items = []
        total_value = 0

        for _ in range(num_items):
            product = choice(products)
            quantity = randint(1, 100)
            price = round(uniform(*product["price"]), 2)
            items.append(
                {
                    "product_id": product["id"],
                    "quantity": quantity,
                    "price_per_unit": price,
                }
            )
            total_value += quantity * price

        addresses = [
            "123, Test Apartment, Test City, Test State",
            "456, Test Apartment No. 2, Test City No. 2",
            "789, Test Apartment No. 3, Test City No. 3",
            "321, Test Apartment No. 4, Test City No. 4",
            "654, Test Apartment No. 5, Test City No. 5",
        ]

        payment_methods = ["CreditCard", "DebitCard", "PayPal", "BankTransfer", "UPI"]

        final_order_value = round(total_value, 2)

        if should_generate_invalid:
            invalid_type = randint(1, 4)
            if invalid_type == 3:
                final_order_value = 0
            elif invalid_type == 4:
                final_order_value = round(total_value * uniform(0.5, 1.5), 2)

        return {
            "order_id": order_id,
            "user_id": user_id,
            "order_timestamp": datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "order_value": final_order_value,
            "items": items,
            "shipping_address": choice(addresses),
            "payment_method": choice(payment_methods),
        }

    def send_orders_to_queue(self, count: int):
        sent_orders = []
        for _ in range(count):
            order = self.generate_random_order()
            response = self.sqs.send_message(
                QueueUrl=self.queue_url, MessageBody=json.dumps(order)
            )
            sent_orders.append(
                {
                    "order_id": order["order_id"],
                    "user_id": order["user_id"],
                    "order_value": order["order_value"],
                    "message_id": response["MessageId"],
                }
            )

        return sent_orders


producer = Producer()
