# AutoSRE Platform

🌐 **Live Demo:** [autosre.vercel.app](https://auto-sre.vercel.app/)

A production-like Site Reliability Engineering platform built to demonstrate observability, failure handling, and automated recovery in distributed systems.

## 🎯 What is AutoSRE?

AutoSRE simulates real-world production challenges that SRE teams face daily. It's a working demonstration of how to design, monitor, break, and heal microservices at scale.

**Built to showcase:**
- Instrumentation and observability (Prometheus metrics)
- Self-healing patterns (circuit breakers, retries)
- Chaos engineering (controlled failure injection)
- Incident response (automated recovery + postmortems)

## ✅ Current Features (Phase 1 Complete)

- **Instrumented API Service** - FastAPI with RED metrics (Rate, Errors, Duration)
- **Prometheus Integration** - Counter, Histogram, and Gauge metrics with proper labeling
- **Health Checks** - Liveness probes for container orchestration
- **Docker Containerization** - Reproducible deployments across environments
- **Auto-generated API Docs** - Interactive documentation at `/docs`

## 🚧 Roadmap

**Phase 2: Observability Stack** *(In Progress)*
- Prometheus auto-scraping with 15s intervals
- Grafana dashboards with SLO tracking
- Alert definitions based on SLI violations

**Phase 3: Multi-Service Architecture**
- Worker service (async job processing)
- Auth service (with circuit breaker pattern)
- PostgreSQL + Redis integration

**Phase 4: Chaos Engineering**
- Failure injection endpoints
- Latency injection
- Database connection failures
- Self-healing validation

**Phase 5: Production Readiness**
- Incident postmortems (3 documented scenarios)
- Runbook automation
- Load testing results
- Performance benchmarks

## 🚀 Quick Start

### Prerequisites
- Docker Desktop installed
- Git

### Run Locally
```bash
# Clone the repository
git clone https://github.com/Raynzler/Auto-SRE.git
cd Auto-SRE

# Start all services
docker-compose up --build
```

### Access Services
- **API Service:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs
- **Metrics Endpoint:** http://localhost:8000/metrics
- **Prometheus:** http://localhost:9090 *(Phase 2)*
- **Grafana:** http://localhost:3000 *(Phase 2)*

### Test the API
```bash
# Health check
curl http://localhost:8000/health

# Create an order
curl -X POST http://localhost:8000/orders \
  -H "Content-Type: application/json" \
  -d '{"item": "laptop", "quantity": 1}'

# View metrics
curl http://localhost:8000/metrics
```

## 🛠 Technology Stack

**Backend:** Python, FastAPI, Pydantic  
**Observability:** Prometheus, Grafana  
**Infrastructure:** Docker, Docker Compose  
**Database:** PostgreSQL *(Phase 3)*  
**Cache:** Redis *(Phase 3)*  
**Proxy:** Nginx *(Phase 3)*  
**Deployment:** Vercel (landing page), Docker (services)

## 📊 Key Metrics Tracked

- **Request Rate:** Requests per second by endpoint and method
- **Error Rate:** Percentage of failed requests (4xx, 5xx)
- **Latency:** p50, p95, p99 response times
- **Service Health:** Binary indicator (up/down)
- **Saturation:** Resource usage (CPU, memory) *(Phase 3)*

## 🎓 Learning Outcomes

This project demonstrates:
- ✅ SRE fundamentals (SLIs, SLOs, error budgets)
- ✅ Instrumentation best practices (RED metrics)
- ✅ Container orchestration
- ✅ Failure mode analysis
- ✅ Automated recovery patterns
- ✅ Incident documentation

## 📝 Documentation

- [Architecture Decisions](docs/architecture.md) *(coming soon)*
- [Incident Postmortems](docs/postmortems/) *(Phase 5)*
- [Runbook](docs/runbook.md) *(Phase 5)*

## 🤝 Contributing

This is a personal learning project, but feedback is welcome! Open an issue or PR if you spot improvements.

## 📧 Contact

**Built by:** Hamza Shaikh
**GitHub:** [@Raynzler](https://github.com/Raynzler)  
**Project Status:** 🟢 Active Development

---

*This project is designed for portfolio demonstration and SRE role interviews. It mirrors production patterns used at companies like Google, Netflix, and Stripe.*