# Brand Intel - API & Frontend

## ✅ Implemented Components

### Backend API (FastAPI)
- **Core Structure**: Complete dependency injection system
- **API Models**: Request and response models
- **Routes Implemented**:
  - ✅ `brands.py` - Full CRUD for brand management
  - ✅ `monitors.py` - Monitor control with manual triggers
  - ✅ `hits.py` - Raw hits and alerts management
  - ✅ `health.py` - System health monitoring
  - ✅ `enrichment.py` - AI enrichment configuration
  - ✅ `admin.py` - Admin operations

### Frontend (React + TypeScript + Vite)
- ✅ Dashboard page with real-time metrics
- ✅ Brands management page with CRUD
- ✅ Monitors control page with manual triggers
- ✅ Alerts viewer page with filtering
- ✅ Enrichment configuration page
- ✅ Admin panel page

---

## 🚀 Quick Start

### 1. Start All Services

```bash
./start.sh
```

This starts:
- **API**: http://localhost:8000
- **Frontend**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs

### 2. Start Services Individually

```bash
# Backend only
./start-api.sh

# Frontend only
./start-frontend.sh

# Monitoring daemon
./start-daemon.sh
```

### 3. Test the API

```bash
# Health check
curl http://localhost:8000/api/v1/health

# List brands
curl http://localhost:8000/api/v1/brands

# Get monitors status
curl http://localhost:8000/api/v1/monitors/status
```

---

## 📁 Project Structure

```
brand-intel/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── main.py
│   │   │   ├── dependencies.py
│   │   │   ├── models/
│   │   │   └── routes/
│   │   │       ├── brands.py
│   │   │       ├── monitors.py
│   │   │       ├── hits.py
│   │   │       ├── health.py
│   │   │       ├── enrichment.py
│   │   │       └── admin.py
│   │   ├── enrichment/
│   │   │   ├── llm/
│   │   │   └── service.py
│   │   ├── monitors/
│   │   ├── daemon/
│   │   └── models/
│   ├── daemon.py
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── types/
│   │   └── utils/
│   ├── package.json
│   └── vite.config.ts
├── start.sh
├── start-api.sh
├── start-frontend.sh
└── start-daemon.sh
```

---

## 🔌 API Endpoints

### Brands (`/api/v1/brands`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/brands` | List all brands with stats |
| GET | `/brands/{id}` | Get brand details |
| POST | `/brands` | Create new brand |
| PUT | `/brands/{id}` | Update brand |
| DELETE | `/brands/{id}` | Delete brand |
| PATCH | `/brands/{id}/toggle` | Toggle active status |

### Monitors (`/api/v1/monitors`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/monitors/status` | Get all monitors status |
| POST | `/monitors/trigger` | Trigger all monitors |
| POST | `/monitors/{type}/trigger` | Trigger specific monitor |
| GET | `/monitors/runs` | Get run history |
| GET | `/monitors/{type}/health` | Get monitor health |

### Hits (`/api/v1/hits`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/hits` | List hits (paginated, filtered) |
| GET | `/hits/{id}` | Get hit details |
| PATCH | `/hits/{id}/status` | Update hit status |
| GET | `/hits/stats` | Get statistics |

### Health (`/api/v1/health`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Basic health check |
| GET | `/health/detailed` | Detailed system health |
| GET | `/health/metrics` | System metrics |
| GET | `/health/circuit-breaker` | Circuit breaker status |

### Enrichment (`/api/v1/enrichment`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/enrichment/config` | Get configuration |
| PUT | `/enrichment/config` | Update configuration |
| GET | `/enrichment/stats` | Get statistics |
| POST | `/enrichment/process/{id}` | Manual enrichment |

### Admin (`/api/v1/admin`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/admin/dlq` | Get DLQ items |
| POST | `/admin/dlq/{id}/retry` | Retry DLQ item |
| DELETE | `/admin/dlq/{id}` | Delete DLQ item |
| POST | `/admin/circuit-breaker/reset` | Reset circuit breaker |
| GET | `/admin/logs` | Get system logs |
| POST | `/admin/cleanup` | Trigger cleanup |

---

## 🔧 Configuration

### Environment Variables

```bash
# MongoDB
MONGODB_URI=mongodb://localhost:27017

# API Keys
PASTEBIN_API_KEY=your_key
GITHUB_TOKEN=your_token
REDDIT_CLIENT_ID=your_id
REDDIT_CLIENT_SECRET=your_secret
HIBP_API_KEY=your_key

# LLM (for enrichment)
USE_ANTHROPIC=false
LLM_API_KEY=your_key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o

# Monitoring
SCAN_INTERVAL_MINUTES=15
MAX_CONCURRENT_BRANDS=10

# Circuit Breaker
CIRCUIT_BREAKER_ENABLED=true
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_TIMEOUT_SECONDS=300

# DLQ
DLQ_ENABLED=true
DLQ_MAX_RETRIES=3
```

---

## 📊 Example API Usage

### Create a Brand

```bash
curl -X POST http://localhost:8000/api/v1/brands \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Acme Corp",
    "domain": "acme.com",
    "keywords": ["acme", "acme corp", "acmecorp"],
    "email_patterns": ["@acme.com"],
    "monitor_config": {
      "pastebin_enabled": true,
      "github_enabled": true,
      "hibp_enabled": true,
      "reddit_enabled": true,
      "scan_frequency_minutes": 15
    }
  }'
```

### Trigger Monitoring

```bash
curl -X POST http://localhost:8000/api/v1/monitors/trigger \
  -H "Content-Type: application/json" \
  -d '{"brand_id": "507f1f77bcf86cd799439011"}'
```

### View Results

```bash
curl "http://localhost:8000/api/v1/hits?brand_id=507f1f77bcf86cd799439011&limit=10"
curl "http://localhost:8000/api/v1/hits/stats?brand_id=507f1f77bcf86cd799439011"
```

---

## 🧪 Testing

```bash
# Run backend tests
pytest backend/tests/test_monitors.py -v
```

---

## 📈 Performance Considerations

1. **Database Indexing**: Indexes are created automatically on startup
2. **Pagination**: All list endpoints support pagination
3. **Rate Limiting**: Monitors respect API rate limits
4. **Concurrent Execution**: Monitors run in parallel with semaphore control

---

## 🔒 Security Considerations

1. **Authentication**: Add JWT or API key authentication for production
2. **CORS**: Configure allowed origins for production
3. **Input Validation**: Pydantic models validate all inputs
4. **Rate Limiting**: Add rate limiting middleware for production

---

## 🐛 Troubleshooting

### API Won't Start
- Check MongoDB is running: `mongosh`
- Verify environment variables are set
- Check logs for specific errors

### Frontend Won't Start
- Ensure Node.js is installed
- Run `npm install` in the `frontend` directory
- Check that the backend API is running

### Monitors Not Triggering
- Verify API keys are configured
- Check circuit breaker status
- Review monitor run history for errors

### No Hits Found
- Verify brand keywords are correct
- Check monitor availability
- Review brand configuration

---

## 📚 Additional Resources

- **API Documentation**: http://localhost:8000/docs
- **Backend README**: `backend/README.md`
- **Enrichment README**: `backend/app/enrichment/README.md`
