#libraries
import time
import uuid
import asyncio
from typing import Optional

#FastAPI framework & Prometheus
from fastapi import FastAPI,HTTPException,Response
from pydantic import BaseModel
from prometheus_client import Gauge,Histogram,Counter,generate_latest,CONTENT_TYPE_LATEST


# === PROMETHEUS METRICS ===
# Track what's happening in service
# Metric 1: Count all HTTP requests
http_requests_total=Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method','endpoint','status']
)
# Metric 2:Latency aka Request Duration
http_request_duration_seconds=Histogram(
    'http_request_duration_seconds',
    'HTTP requests latency in seconds',
    ['method','endpoint']
)
# Metric 3: Service Health
service_up=Gauge(
    'service_up',
    'Service health status (1=up, 0=down)',
    []
)


# === FASTAPI APP ===
# Create the web server
app = FastAPI(
    title="AutoSRE API Service",
    description="Self-healing microservice demo",
    version="1.0.0"
)


# === STARTUP LOGIC ===
# When the service starts, mark it as healthy
@app.on_event("startup")
async def startup_event():
    service_up.set(1)
    print("Service Started, Running Healthy")

# === DATA MODELS ===
# define what requests and responses look like
class OrderRequest(BaseModel):
    """
    Data model for creating an order.
    FASTapi will auto validate
    """
    item: str
    quantity: int

    class Config:
        json_schema_extra = {
            "example":{
                "item":"laptop",
                "quantity": 1
            }
        }

class OrderResponse(BaseModel):
    """
    Data model for order response
    """
    order_id:str
    status:str
    item:str
    quantity:int

# === ENDPOINTS ===
@app.get("/health")
async def health_check():
    """
    Liveness probe: Is the process running?
    Returns 200 if the service is alive.
    """
    return{
        "status": "Healthy",
        "service": "autosre-api"
    }

# Metrics endpoint - for Prometheus to scrape
@app.get("/metrics")
async def metrics():
    """
    Prometheus will scrape this every 15s
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

# POST /orders - Create an order
@app.post("/orders", response_model=OrderResponse)
async def create_order(Order:OrderRequest):
    """
     Create a new order with full instrumentation
    """
    start_time = time.time()
    try:
        order_id = f"order_{uuid.uuid4().hex[:8]}"

        await asyncio.sleep(0.05)

        http_requests_total.labels(
            method="POST",
            endpoint="/orders",
            status="201"
        ).inc()


        #Latency
        duration = time.time() - start_time
        http_request_duration_seconds.labels(
            method="POST",
            endpoint="/orders"
        ).observe(duration)

        #Return response (successful)
        return OrderResponse(
            order_id=order_id,
            status="created",
            item=Order.item,
            quantity=Order.quantity
        )
    
    except Exception as e:
        #Failed Requests
        http_requests_total.labels(
            method="POST",
            endpoint="/orders",
            status="500"
        ).inc()

        #Record Latency for errors
        duration = time.time() - start_time
        http_request_duration_seconds.labels(
            method="POST",
            endpoint="/orders",
        ).observe(duration)

        #Return error to client
        raise HTTPException(status_code=500, detail=str(e))

# === RUN THE SERVER ===
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
