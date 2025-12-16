from consumer import consumer
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from logger import read_last_n_logs
from producer import producer
from schema import LeaderStats, ProduceRequest

api_router = APIRouter(tags=["API"])


@api_router.get("/api")
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


@api_router.post("/produce")
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


@api_router.get("/consumer_logs")
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


@api_router.get("/clear_redis_db")
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


@api_router.get("/user/{user_id}")
async def get_user_stats(user_id: str):
    try:
        redis_client = consumer.get_redis_client()
        user_stats = redis_client.hgetall(f"user:{user_id}")

        if not user_stats:
            return JSONResponse(
                status_code=404,
                content={"status": 404, "error": f"User {user_id} not found"},
            )

        order_count = user_stats.get(b"order_count") or user_stats.get("order_count")
        total_spend = user_stats.get(b"total_spend") or user_stats.get("total_spend")

        if isinstance(order_count, bytes):
            order_count = order_count.decode("utf-8")
        if isinstance(total_spend, bytes):
            total_spend = total_spend.decode("utf-8")

        return JSONResponse(
            status_code=200,
            content={
                "status": 200,
                "user_id": user_id,
                "order_count": int(order_count) if order_count else 0,
                "total_spend": float(total_spend) if total_spend else 0.0,
            },
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": 500, "error": str(e)})


@api_router.get("/global_stats")
async def get_global_stats():
    try:
        redis_client = consumer.get_redis_client()
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

        return JSONResponse(
            status_code=200,
            content={
                "status": 200,
                "total_orders": int(total_orders) if total_orders else 0,
                "total_revenue": float(total_revenue) if total_revenue else 0.0,
            },
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": 500, "error": str(e)})


@api_router.post("/user_rankings")
async def get_user_ranking(leader_stats: LeaderStats):
    try:
        redis_client = consumer.get_redis_client()
        limit = leader_stats.limit

        spend_results = redis_client.zrevrange(
            "user_leader:total_spend", 0, limit - 1, withscores=True
        )
        orders_results = redis_client.zrevrange(
            "user_leader:total_order_count", 0, limit - 1, withscores=True
        )

        by_spend = []
        for idx, (user_id, score) in enumerate(spend_results):
            user_id = user_id.decode("utf-8")
            by_spend.append(
                {"position": idx, "user_id": user_id, "total_spend": round(score, 2)}
            )

        by_orders = []
        for idx, (user_id, score) in enumerate(orders_results):
            user_id = user_id.decode("utf-8")
            by_orders.append(
                {"position": idx, "user_id": user_id, "total_order_count": int(score)}
            )

        return JSONResponse(
            status_code=200,
            content={
                "status": 200,
                "by_total_spend": by_spend,
                "by_total_order_count": by_orders,
            },
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": 500, "error": str(e)})
