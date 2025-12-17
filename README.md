# SQS FastAPI Service

A microservice application that simulates an order processing system using AWS SQS (via LocalStack), Redis for analytics storage, and FastAPI for REST API endpoints. The system processes orders from an SQS queue, validates them, and stores aggregated statistics in Redis.

## Features

- **Order Production**: Generate and send random orders to SQS queue
- **Order Consumption**: Background consumer process that polls SQS and processes orders
- **Data Validation**: Validates order data including order ID, user ID, and order value calculations
- **Analytics Storage**: Stores user-wise, global, and monthly statistics in Redis
- **REST API**: FastAPI endpoints for querying statistics and managing the system
- **Logging**: Consumer logs stored in JSONL format for monitoring

## Prerequisites

- Docker and Docker Compose installed
- Git (for cloning the repository)

## Getting Started

### 1. Clone the Repository

```bash
git clone <repository-url>
cd sqs-fastapi-service
```

### 2. Docker Setup (Make sure the following ports are free)

The project uses Docker Compose to orchestrate three services:
- **LocalStack**: Simulates AWS SQS locally
- **Redis**: In-memory data store for analytics
- **SQS Server**: FastAPI application with producer and consumer

#### Start the Services

```bash
docker-compose up -d --build
```

This command will:
- Start LocalStack on port `4566`
- Start Redis on port `6379`
- Build and start the SQS server on port `9000`

#### Check Service Status

```bash
docker-compose ps
```

#### View Logs

```bash
docker-compose logs -f sqs-server
```

#### Stop the Services

```bash
docker-compose down
```


## System Architecture & Flow

### Components

1. **Producer** (`producer.py`)
   - Generates random order data
   - Sends orders to SQS queue via boto3
   - 20% of generated orders are intentionally invalid for testing

2. **Consumer** (`consumer.py`)
   - Runs as a background process
   - Continuously polls SQS queue for messages
   - Validates order data
   - Stores analytics in Redis
   - Handles failed orders

3. **FastAPI Server** (`main.py`, `api.py`)
   - REST API endpoints for system interaction
   - Manages consumer process lifecycle
   - Provides statistics and analytics queries

4. **Redis Storage**
   - User-wise statistics (order count, total spend, failed orders)
   - Global statistics (total orders, revenue, failed orders)
   - Monthly aggregations per user
   - User rankings (by spend and order count)

### System Flow

```
┌─────────────┐
│   FastAPI   │
│    Server   │
└──────┬──────┘
       │
       │ POST /produce
       ▼
┌─────────────┐
│  Producer   │──────┐
└─────────────┘      │
                     │ Send Messages
                     ▼
              ┌─────────────┐
              │   SQS Queue │
              │ (LocalStack) │
              └──────┬───────┘
                     │
                     │ Poll Messages
                     ▼
              ┌─────────────┐
              │  Consumer   │
              │  (Process)  │
              └──────┬───────┘
                     │
                     │ Store Analytics
                     ▼
              ┌─────────────┐
              │    Redis    │
              └──────┬───────┘
                     │
                     │ Query Data
                     ▼
              ┌─────────────┐
              │   FastAPI   │
              │  Endpoints  │
              └─────────────┘
```

### Detailed Flow

1. **Order Production**
   - Client sends POST request to `/produce` with order count
   - Producer generates random orders (valid and invalid)
   - Orders are sent to SQS queue via LocalStack

2. **Order Consumption**
   - Consumer process continuously polls SQS queue
   - Receives messages in batches (configurable)
   - Validates each order:
     - Order ID must start with "ORD"
     - User ID must start with "U"
     - Order value must be > 0
     - Calculated order value must match provided value
   - If validation fails, order is marked as failed

3. **Data Storage**
   - Valid orders update:
     - User statistics (order count, total spend)
     - Global statistics (total orders, revenue)
     - Monthly aggregations (per user per month)
     - User rankings (sorted sets for spend and order count)
   - Failed orders are tracked separately

4. **Data Retrieval**
   - FastAPI endpoints query Redis for:
     - User rankings
     - Individual user stats
     - Global statistics
     - Monthly statistics

## API Endpoints

### Base URL
```
http://localhost:9000
```

### Endpoints

#### `GET /api`
Get API information and available endpoints.

#### `POST /produce`
Send random orders to the SQS queue.

**Request Body:**
```json
{
  "count": 10
}
```

**Response:**
```json
{
  "message": "Successfully sent 10 orders to queue",
  "orders": [...]
}
```

#### `GET /consumer_logs`
Get the latest 100 consumer logs.

**Response:**
```json
{
  "total_logs": 100,
  "logs": [...]
}
```

#### `DELETE /clear_redis_db`
Clear all data from Redis database.

**Response:**
```json
{
  "message": "Redis database cleared"
}
```

#### `GET /users?limit=10`
Get user rankings by total spend and order count.

**Query Parameters:**
- `limit` (optional): Number of top users to return (default: 10)

**Response:**
```json
{
  "total_spend_ranking": [...],
  "total_order_count_ranking": [...]
}
```

#### `GET /users/{user_id}/stats`
Get statistics for a specific user.

**Response:**
```json
{
  "user_id": "U1001",
  "order_count": 25,
  "total_spend": 1250.50,
  "failed_order_count": 2
}
```

#### `GET /stats/global`
Get global statistics across all orders.

**Response:**
```json
{
  "total_orders": 150,
  "total_revenue": 75000.00,
  "failed_orders": 5
}
```

#### `GET /stats/monthly/{month}`
Get monthly statistics for a specific month.

**Path Parameter:**
- `month`: Format `YYYY-MM` (e.g., `2025-12`)

**Response:**
```json
{
  "month": "2025-12",
  "total_orders": 50,
  "total_revenue": 25000.00,
  "failed_orders": 2,
  "user_stats": [...]
}
```

## Configuration

Configuration is managed through environment variables in `docker-compose.yml`:

- **AWS Settings**: Region, endpoint URL, credentials
- **SQS Settings**: Queue name, message batch size, wait time, visibility timeout
- **Redis Settings**: Host, port, database number
- **FastAPI Settings**: Server port

## Project Structure

```
sqs-fastapi-service/
├── docker-compose.yml          # Docker Compose configuration
├── requirements.txt            # Python dependencies
├── README.md                   # This file
└── sqs-server/
    ├── Dockerfile              # Docker image definition
    ├── main.py                 # FastAPI application entry point
    ├── api.py                  # API route handlers
    ├── producer.py             # SQS message producer
    ├── consumer.py             # SQS message consumer
    ├── config.py               # Configuration management
    ├── schema.py               # Pydantic models
    ├── logger.py               # Logging utilities
    └── consumer_logs.jsonl     # Consumer log file
```

## Development

### Running Locally (Without Docker)

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Start LocalStack and Redis using Docker Compose:
```bash
docker-compose up -d localstack redis
```

3. Set environment variables or create a `.env` file

4. Run the FastAPI server:
```bash
cd sqs-server
python main.py
```

## Testing the System

1. Start the services:
```bash
docker-compose up -d
```

2. Wait for services to be ready (about 10-15 seconds)

3. Send some orders:
```bash
curl -X POST http://localhost:9000/produce \
  -H "Content-Type: application/json" \
  -d '{"count": 20}'
```

4. Check consumer logs:
```bash
curl http://localhost:9000/consumer_logs
```

5. View user rankings:
```bash
curl http://localhost:9000/users?limit=5
```

6. Check global stats:
```bash
curl http://localhost:9000/stats/global
```

7. Check userwise stats:
```bash
curl http://localhost:9000/users/<user_id>/stats
```

8. Check monthly stats:
```bash
curl http://localhost:9000/stats/monthly/<month>
```
