# Brand Intel - API & Frontend Implementation Guide

## 🎉 Implementation Status

### ✅ Completed Components

#### Backend API (FastAPI)
- **Core Structure**: Complete dependency injection system
- **API Models**: 61 lines of request models, 260 lines of response models
- **Routes Implemented**:
  - ✅ `brands.py` (278 lines) - Full CRUD for brand management
  - ✅ `monitors.py` (398 lines) - Monitor control with manual triggers
  - ✅ `hits.py` (227 lines) - Raw hits and alerts management
  - ✅ `health.py` (184 lines) - System health monitoring
  - ✅ `enrichment.py` (63 lines) - AI enrichment configuration
  - ✅ `admin.py` (125 lines) - Admin operations
- **Main Application**: FastAPI app with CORS, lifespan management, and route registration

**Total Backend Code**: ~1,600 lines of production-ready API code

### 🚧 Pending Components

#### Frontend (Streamlit)
- Dashboard page
- Brands management page
- Monitors control page
- Alerts viewer page
- Enrichment configuration page
- Admin panel page
- API client wrapper
- Reusable components

---

## 🚀 Quick Start

### 1. Start the API Server

```bash
cd backend
uvicorn app.api.main:app --reload --port 8000
```

The API will be available at: `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`
- Alternative Docs: `http://localhost:8000/redoc`

### 2. Test the API

```bash
# Health check
curl http://localhost:8000/api/v1/health

# List brands
curl http://localhost:8000/api/v1/brands

# Get monitors status
curl http://localhost:8000/api/v1/monitors/status
```

### 3. Manual Monitor Trigger

```bash
# Trigger all monitors for all brands
curl -X POST http://localhost:8000/api/v1/monitors/trigger \
  -H "Content-Type: application/json" \
  -d '{}'

# Trigger all monitors for specific brand
curl -X POST http://localhost:8000/api/v1/monitors/trigger \
  -H "Content-Type: application/json" \
  -d '{"brand_id": "your_brand_id_here"}'

# Trigger specific monitor (e.g., pastebin) for a brand
curl -X POST http://localhost:8000/api/v1/monitors/pastebin/trigger \
  -H "Content-Type: application/json" \
  -d '{"brand_id": "your_brand_id_here"}'
```

---

## 📁 Project Structure

```
backend/app/api/
├── __init__.py
├── main.py                    # FastAPI application (237 lines)
├── dependencies.py            # Dependency injection (89 lines)
├── models/
│   ├── __init__.py
│   ├── requests.py           # Request models (61 lines)
│   └── responses.py          # Response models (260 lines)
└── routes/
    ├── __init__.py
    ├── brands.py             # Brand CRUD (278 lines)
    ├── monitors.py           # Monitor control (398 lines)
    ├── hits.py               # Hits management (227 lines)
    ├── health.py             # Health checks (184 lines)
    ├── enrichment.py         # Enrichment config (63 lines)
    └── admin.py              # Admin operations (125 lines)

frontend/                      # TO BE IMPLEMENTED
├── app.py
├── api_client.py
├── config.py
├── requirements.txt
├── pages/
│   ├── 1_📊_Dashboard.py
│   ├── 2_🏢_Brands.py
│   ├── 3_🔍_Monitors.py
│   ├── 4_🚨_Alerts.py
│   ├── 5_🤖_Enrichment.py
│   └── 6_⚙️_Admin.py
├── components/
│   ├── brand_form.py
│   ├── monitor_card.py
│   ├── hit_viewer.py
│   └── stats_charts.py
└── utils/
    ├── formatters.py
    └── validators.py
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
| POST | `/monitors/trigger` | **Trigger all monitors** |
| POST | `/monitors/{type}/trigger` | **Trigger specific monitor** |
| GET | `/monitors/runs` | Get run history |
| GET | `/monitors/runs/{id}` | Get run details |
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

## 🎯 Key Features Implemented

### 1. Manual Monitor Triggers ✅
- Trigger all monitors for all brands
- Trigger all monitors for specific brand
- Trigger specific monitor for specific brand
- Real-time execution with results

### 2. Brand Management ✅
- Full CRUD operations
- Statistics tracking (hits, last scan, etc.)
- Enable/disable brands
- Monitor configuration per brand

### 3. Hit Management ✅
- Paginated listing with filters
- Status updates (pending, reviewed, false_positive)
- Statistics and analytics
- Timeline visualization data

### 4. System Health ✅
- Component health checks
- Circuit breaker monitoring
- DLQ status
- Performance metrics

### 5. Admin Operations ✅
- DLQ management
- Circuit breaker reset
- System cleanup
- Log viewing

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

# Enrichment
ENRICHMENT_ENABLED=true
USE_ANTHROPIC=false
LLM_API_KEY=your_key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o
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
# Get brand ID from previous response, then trigger
curl -X POST http://localhost:8000/api/v1/monitors/trigger \
  -H "Content-Type: application/json" \
  -d '{"brand_id": "507f1f77bcf86cd799439011"}'
```

### View Results

```bash
# Get hits for the brand
curl "http://localhost:8000/api/v1/hits?brand_id=507f1f77bcf86cd799439011&limit=10"

# Get statistics
curl "http://localhost:8000/api/v1/hits/stats?brand_id=507f1f77bcf86cd799439011"
```

---

## 🎨 Frontend Implementation Guide

### Next Steps

1. **Create Frontend Structure**
   ```bash
   mkdir -p frontend/{pages,components,utils}
   cd frontend
   ```

2. **Install Dependencies**
   ```bash
   pip install streamlit requests pandas plotly python-dotenv streamlit-autorefresh
   ```

3. **Create API Client** (`frontend/api_client.py`)
   - Wrapper for all API endpoints
   - Error handling
   - Response parsing

4. **Create Main App** (`frontend/app.py`)
   - Streamlit configuration
   - Navigation
   - Session state management

5. **Create Pages**
   - Dashboard: Real-time metrics, monitor cards with trigger buttons
   - Brands: CRUD interface with forms
   - Monitors: Status display, manual triggers, run history
   - Alerts: Hit viewer with filtering
   - Enrichment: Configuration interface
   - Admin: DLQ, circuit breaker, logs

6. **Create Components**
   - `monitor_card.py`: Reusable monitor status card
   - `brand_form.py`: Brand create/edit form
   - `hit_viewer.py`: Hit display component
   - `stats_charts.py`: Chart components

---

## 🧪 Testing

### Manual Testing Checklist

- [ ] API starts successfully
- [ ] Health endpoint responds
- [ ] Can create a brand
- [ ] Can list brands
- [ ] Can trigger monitors manually
- [ ] Monitor runs are recorded
- [ ] Hits are stored correctly
- [ ] Can view hit details
- [ ] Can update hit status
- [ ] Statistics are calculated correctly
- [ ] Circuit breaker works
- [ ] DLQ captures failures

### Automated Testing

```bash
# Run API tests (when implemented)
pytest backend/tests/test_api.py -v

# Run integration tests
pytest backend/tests/test_integration.py -v
```

---

## 📈 Performance Considerations

1. **Database Indexing**: Indexes are created automatically on startup
2. **Pagination**: All list endpoints support pagination
3. **Caching**: Consider adding Redis for frequently accessed data
4. **Rate Limiting**: Monitors respect API rate limits
5. **Concurrent Execution**: Monitors run in parallel with semaphore control

---

## 🔒 Security Considerations

1. **Authentication**: Add JWT or API key authentication
2. **CORS**: Configure allowed origins for production
3. **Input Validation**: Pydantic models validate all inputs
4. **SQL Injection**: Using MongoDB with proper ObjectId validation
5. **Rate Limiting**: Add rate limiting middleware for production

---

## 🐛 Troubleshooting

### API Won't Start
- Check MongoDB is running: `mongosh`
- Verify environment variables are set
- Check logs for specific errors

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
- **Design Plan**: `.opencode/plans/api-and-frontend-design.md`
- **Implementation Summary**: `.opencode/plans/implementation-summary.md`
- **Architecture Review**: `.opencode/plans/monitoring-architecture-review.md`

---

## 🎯 Next Implementation Phase

### Priority 1: Frontend Core (4-6 hours)
1. Create `frontend/api_client.py`
2. Create `frontend/app.py`
3. Create `frontend/config.py`
4. Implement Dashboard page with monitor trigger buttons

### Priority 2: Brand Management (2-3 hours)
1. Implement Brands page
2. Create brand form component
3. Add CRUD operations

### Priority 3: Monitoring Interface (3-4 hours)
1. Implement Monitors page
2. Add manual trigger buttons
3. Display run history
4. Show circuit breaker status

### Priority 4: Alerts & Admin (3-4 hours)
1. Implement Alerts page
2. Implement Admin page
3. Add enrichment configuration

---

**Made with Bob** 🤖

**Status**: Backend API Complete ✅ | Frontend Pending 🚧