from multiprocessing import Process
from typing import Optional
from fastapi import FastAPI
from consumer import consumer
from logger import clear_logs
import uvicorn
from contextlib import asynccontextmanager
from api import api_router

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
app.include_router(api_router)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
