#libraries
import time
import uuid
import asyncio
from typing import Optional

#FastAPI framework & Prometheus
from fastapi import FastAPI, HTTPException, Response, Request
from pydantic import BaseModel
from prometheus_client import Gauge, Histogram, Counter, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware

# === PROMETHEUS METRICS ===
# Track what's happening in service
# Metric 1: Count all HTTP requests
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)
# Metric 2: Latency aka Request Duration
http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP requests latency in seconds',
    ['method', 'endpoint']
)
# Metric 3: Service Health
service_up = Gauge(
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

# === SRE MIDDLEWARE ===
# Intercept HTTP requests for global metric tracking
class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        endpoint = request.url.path 

        if endpoint == "/metrics":
            return await call_next(request)

        try:
            response = await call_next(request)
            status_code = str(response.status_code)
        except Exception as e:
            status_code = "500"
            raise e
        finally:
            duration = time.time() - start_time
            
            http_requests_total.labels(
                method=request.method,
                endpoint=endpoint,
                status=status_code
            ).inc()

            http_request_duration_seconds.labels(
                method=request.method,
                endpoint=endpoint
            ).observe(duration)
            
        return response

app.add_middleware(PrometheusMiddleware)

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
    order_id: str
    status: str
    item: str
    quantity: int

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

@app.get("/metrics")
async def metrics():
    """
    Prometheus will scrape this every 15s
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )

@app.post("/orders", response_model=OrderResponse)
async def create_order(Order: OrderRequest):
    """
    Create a new order with full instrumentation
    """
    order_id = f"order_{uuid.uuid4().hex[:8]}"
    
    await asyncio.sleep(0.05)

    return OrderResponse(
        order_id=order_id,
        status="created",
        item=Order.item,
        quantity=Order.quantity
    )

# === RUN THE SERVER ===
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )