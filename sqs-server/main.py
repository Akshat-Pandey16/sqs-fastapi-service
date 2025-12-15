from multiprocessing import Process
from typing import Optional
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from schema import ProduceRequest
from consumer import consumer
from producer import producer
from logger import read_last_n_logs, clear_logs
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


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
