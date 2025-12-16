from consumer import consumer
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from logger import read_last_n_logs
from producer import producer
from schema import ProduceRequest

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
                "delete_redis_db": "DELETE /delete_redis_db - Delete Redis database",
                "users": "GET /users - Get user ranking",
                "users/{user_id}/stats": "GET /users/{user_id}/stats - Get user stats",
                "stats/global": "GET /stats/global - Get global stats",
                "stats/monthly/{month}": "GET /stats/monthly/{month} - Get monthly stats (format: YYYY-MM)",
            },
        },
    )


@api_router.post("/produce")
async def produce_orders(request: ProduceRequest):
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


@api_router.delete("/clear_redis_db")
async def delete_redis_db():
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


@api_router.get("/users")
async def get_user_ranking(limit: int = 10):
    try:
        redis_client = consumer.get_redis_client()

        spend_results = redis_client.zrevrange(
            "user_ranking:total_spend", 0, limit - 1, withscores=True
        )
        orders_results = redis_client.zrevrange(
            "user_ranking:total_order_count", 0, limit - 1, withscores=True
        )

        by_spend = []
        for idx, (user_id, score) in enumerate(spend_results, start=1):
            user_id = user_id.decode("utf-8")
            by_spend.append(
                {"position": idx, "user_id": user_id, "total_spend": round(score, 2)}
            )

        by_orders = []
        for idx, (user_id, score) in enumerate(orders_results, start=1):
            user_id = user_id.decode("utf-8")
            by_orders.append(
                {"position": idx, "user_id": user_id, "total_order_count": int(score)}
            )

        return JSONResponse(
            status_code=200,
            content={
                "status": 200,
                "total_spend_ranking": by_spend,
                "total_order_count_ranking": by_orders,
            },
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": 500, "error": str(e)})


@api_router.get("/users/{user_id}/stats")
async def get_user_stats(user_id: str):
    try:
        redis_client = consumer.get_redis_client()
        user_stats = redis_client.hgetall(f"user:{user_id}")

        if not user_stats:
            return JSONResponse(
                status_code=404,
                content={"status": 404, "error": f"User {user_id} not found"},
            )

        order_count = user_stats.get(b"order_count")
        total_spend = user_stats.get(b"total_spend")
        failed_order_count = user_stats.get(b"failed_order_count")

        return JSONResponse(
            status_code=200,
            content={
                "user_id": user_id,
                "order_count": int(order_count) if order_count else 0,
                "total_spend": float(total_spend) if total_spend else 0.0,
                "failed_order_count": int(failed_order_count)
                if failed_order_count
                else 0,
            },
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": 500, "error": str(e)})


@api_router.get("/stats/global")
async def get_global_stats():
    try:
        redis_client = consumer.get_redis_client()
        global_stats = redis_client.hgetall("global:stats")

        total_orders = global_stats.get(b"total_orders")
        total_revenue = global_stats.get(b"total_revenue")
        failed_orders = global_stats.get(b"failed_orders")

        return JSONResponse(
            status_code=200,
            content={
                "status": 200,
                "total_orders": int(total_orders) if total_orders else 0,
                "total_revenue": float(total_revenue) if total_revenue else 0.0,
                "failed_orders": int(failed_orders) if failed_orders else 0,
            },
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": 500, "error": str(e)})


@api_router.get("/stats/monthly/{month}")
async def get_monthly_stats(month: str):
    try:
        redis_client = consumer.get_redis_client()

        if not redis_client.sismember("months:list", month):
            return JSONResponse(
                status_code=404,
                content={"status": 404, "error": f"No data found for month {month}"},
            )

        pattern = f"monthly:{month}:user:*"
        user_keys = redis_client.keys(pattern)

        user_stats = []
        total_orders = 0
        total_revenue = 0.0
        total_failed_orders = 0

        for key in user_keys:
            user_data = redis_client.hgetall(key)
            user_id = key.decode("utf-8").split(":")[-1]

            order_count = int(user_data.get(b"order_count", 0))
            total_spend = float(user_data.get(b"total_spend", 0.0))
            failed_order_count = int(user_data.get(b"failed_order_count", 0))

            total_orders += order_count
            total_revenue += total_spend
            total_failed_orders += failed_order_count

            user_stats.append(
                {
                    "user_id": user_id,
                    "order_count": order_count,
                    "total_spend": round(total_spend, 2),
                    "failed_order_count": failed_order_count,
                }
            )

        user_stats.sort(key=lambda x: x["total_spend"], reverse=True)

        return JSONResponse(
            status_code=200,
            content={
                "status": 200,
                "month": month,
                "total_orders": total_orders,
                "total_revenue": round(total_revenue, 2),
                "failed_orders": total_failed_orders,
                "user_stats": user_stats,
            },
        )
    except Exception as e:
        return JSONResponse(status_code=500, content={"status": 500, "error": str(e)})
