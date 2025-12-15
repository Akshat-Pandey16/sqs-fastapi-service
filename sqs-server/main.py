from multiprocessing import Process
from typing import Optional
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from schema import ProduceRequest
from consumer import consumer
from producer import producer
from logger import read_last_n_logs, clear_logs
from config import config
import uvicorn
from contextlib import asynccontextmanager

consumer_process: Optional[Process] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    clear_logs()
    global consumer_process
    consumer_process = Process(target=consumer.start)
    consumer_process.start()
    print("SQS Consumer process started")
    yield
    if consumer_process and consumer_process.is_alive():
        consumer_process.terminate()
        consumer_process.join()
        print("SQS Consumer process terminated")


app = FastAPI(title="SQS Order Management API", version="1.0.0", lifespan=lifespan)


@app.get("/api")
async def api_info():
    return JSONResponse(
        status_code=200,
        content={
            "status": 200,
            "message": "SQS Order Management API",
            "endpoints": {
                "produce": "POST /produce - Send random orders to queue",
                "consumer_logs": "GET /consumer_logs - Get latest 100 consumer logs",
            },
        },
    )


@app.post("/produce")
async def produce_orders(request: ProduceRequest):
    if request.count < 1 or request.count > 100:
        return JSONResponse(
            status_code=400,
            content={"status": 400, "error": "Count must be between 1 and 100"},
        )

    try:
        sent_orders = producer.send_orders_to_queue(request.count)
        return JSONResponse(
            status_code=200,
            content={
                "status": 200,
                "message": f"Successfully sent {request.count} orders to queue",
                "orders": sent_orders,
            },
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": 500, "error": str(e)},
        )


@app.get("/consumer_logs")
async def get_consumer_logs():
    logs = read_last_n_logs(100)
    return JSONResponse(
        status_code=200,
        content={
            "status": 200,
            "total_logs": len(logs),
            "logs": logs,
        },
    )


@app.get("/clear_redis_db")
async def clear_redis_db():
    try:
        consumer.get_redis_client().flushdb()
        return JSONResponse(
            status_code=200,
            content={"status": 200, "message": "Redis database cleared"},
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": 500, "error": str(e)},
        )


@app.get("/get_redis_db_stats")
async def get_redis_db_stats():
    try:
        redis_client = consumer.get_redis_client()
        users = redis_client.keys("user:*")
        users_stats = []
        for user in users:
            user_stats = redis_client.hgetall(user)
            user_id = user.decode("utf-8") if isinstance(user, bytes) else user
            order_count = user_stats.get(b"order_count") or user_stats.get(
                "order_count"
            )
            total_spend = user_stats.get(b"total_spend") or user_stats.get(
                "total_spend"
            )

            if isinstance(order_count, bytes):
                order_count = order_count.decode("utf-8")
            if isinstance(total_spend, bytes):
                total_spend = total_spend.decode("utf-8")

            users_stats.append(
                {
                    "user_id": user_id.replace("user:", ""),
                    "order_count": int(order_count) if order_count else 0,
                    "total_spend": float(total_spend) if total_spend else 0.0,
                }
            )

            global_stats = redis_client.hgetall("global:stats")
            total_orders = global_stats.get(b"total_orders") or global_stats.get(
                "total_orders"
            )
            total_revenue = global_stats.get(b"total_revenue") or global_stats.get(
                "total_revenue"
            )

            if isinstance(total_orders, bytes):
                total_orders = total_orders.decode("utf-8")
            if isinstance(total_revenue, bytes):
                total_revenue = total_revenue.decode("utf-8")

            global_stats = {
                "total_orders": int(total_orders) if total_orders else 0,
                "total_revenue": float(total_revenue) if total_revenue else 0.0,
            }

        return JSONResponse(
            status_code=200,
            content={"status": 200, "users": users_stats, "global": global_stats},
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": 500, "error": str(e)})


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
