# Brand Intel Monitoring Daemon

Background service for continuous brand monitoring across multiple data sources.

## Overview

The monitoring daemon is a standalone Python process that:
- Periodically scans all active brands (default: every 15 minutes)
- Runs monitors in parallel (Pastebin, GitHub, Reddit, HIBP)
- Handles failures with circuit breaker pattern
- Sends alerts for critical issues
- Manages failed items with dead letter queue

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Monitoring Daemon                         │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │           Scheduler (APScheduler)                   │    │
│  │  - Interval-based triggers (15-30 min)             │    │
│  │  - Graceful shutdown on signals                    │    │
│  └────────────────┬───────────────────────────────────┘    │
│                   │                                          │
│                   ▼                                          │
│  ┌────────────────────────────────────────────────────┐    │
│  │        MonitorOrchestrator                          │    │
│  │  - Fetches active brands from MongoDB              │    │
│  │  - Runs monitors in parallel                       │    │
│  │  - Circuit breaker protection                      │    │
│  └────────────────┬───────────────────────────────────┘    │
│                   │                                          │
│                   ▼                                          │
│  ┌────────────────────────────────────────────────────┐    │
│  │     Individual Monitors                             │    │
│  │  - Rate limiting                                    │    │
│  │  - Retry logic                                      │    │
│  │  - Error isolation                                  │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Install Dependencies

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` file or set environment variables:

```bash
# Required
MONGODB_URI=mongodb://localhost:27017

# Optional - Scheduling
SCAN_INTERVAL_MINUTES=15
MAX_CONCURRENT_BRANDS=10

# Optional - Alerting
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
ALERT_EMAIL=alerts@yourdomain.com

# Optional - Features
CIRCUIT_BREAKER_ENABLED=true
DLQ_ENABLED=true
LOG_LEVEL=INFO
```

### 3. Run Daemon

```bash
# Development
python daemon.py

# Production (with systemd)
sudo systemctl start brand-intel-monitor
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MONGODB_URI` | `mongodb://localhost:27017` | MongoDB connection string |
| `SCAN_INTERVAL_MINUTES` | `15` | Minutes between scans |
| `MAX_CONCURRENT_BRANDS` | `10` | Parallel brand scans |
| `MAX_CONCURRENT_MONITORS` | `4` | Monitors per brand |
| `PASTEBIN_RATE_LIMIT` | `60` | Requests per minute |
| `GITHUB_RATE_LIMIT` | `30` | Requests per minute |
| `REDDIT_RATE_LIMIT` | `60` | Requests per minute |
| `HIBP_RATE_LIMIT` | `60` | Requests per minute |
| `MONITOR_TIMEOUT_SECONDS` | `30` | Monitor timeout |
| `MAX_RETRIES` | `3` | Retry attempts |
| `CIRCUIT_BREAKER_ENABLED` | `true` | Enable circuit breaker |
| `CIRCUIT_BREAKER_FAILURE_THRESHOLD` | `5` | Failures before opening |
| `CIRCUIT_BREAKER_TIMEOUT_SECONDS` | `300` | Timeout before retry |
| `SLACK_WEBHOOK_URL` | - | Slack webhook for alerts |
| `ALERT_EMAIL` | - | Email for alerts |
| `ALERT_ON_MONITOR_FAILURE` | `true` | Alert on failures |
| `ALERT_FAILURE_THRESHOLD` | `3` | Failures before alert |
| `HEALTH_CHECK_ENABLED` | `true` | Enable health endpoint |
| `HEALTH_CHECK_PORT` | `8001` | Health check port |
| `LOG_LEVEL` | `INFO` | Logging level |
| `DLQ_ENABLED` | `true` | Enable dead letter queue |
| `DLQ_MAX_RETRIES` | `3` | DLQ retry attempts |

### Full Configuration

See `app/daemon/config.py` for all available options.

## Deployment

### Systemd Service (Linux)

1. **Copy service file:**
```bash
sudo cp brand-intel-monitor.service /etc/systemd/system/
```

2. **Edit configuration:**
```bash
sudo nano /etc/systemd/system/brand-intel-monitor.service
# Update paths and environment variables
```

3. **Create user:**
```bash
sudo useradd -r -s /bin/false brandmonitor
```

4. **Set permissions:**
```bash
sudo chown -R brandmonitor:brandmonitor /opt/brand-intel
```

5. **Enable and start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable brand-intel-monitor
sudo systemctl start brand-intel-monitor
```

6. **Check status:**
```bash
sudo systemctl status brand-intel-monitor
sudo journalctl -u brand-intel-monitor -f
```

### Docker Deployment

```dockerfile
# Dockerfile.daemon
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY daemon.py .

CMD ["python", "daemon.py"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  mongodb:
    image: mongo:7
    volumes:
      - mongo_data:/data/db
    ports:
      - "27017:27017"
  
  monitor-daemon:
    build:
      context: ./backend
      dockerfile: Dockerfile.daemon
    environment:
      - MONGODB_URI=mongodb://mongodb:27017
      - SCAN_INTERVAL_MINUTES=15
      - MAX_CONCURRENT_BRANDS=10
    depends_on:
      - mongodb
    restart: unless-stopped
    ports:
      - "8001:8001"  # Health check

volumes:
  mongo_data:
```

Run with:
```bash
docker-compose up -d
```

## Health Checks

The daemon exposes health check endpoints on port 8001:

### Endpoints

- **`GET /health`** - Overall health status
- **`GET /ready`** - Readiness check
- **`GET /alive`** - Liveness check
- **`GET /stats`** - Detailed statistics

### Example

```bash
# Check health
curl http://localhost:8001/health

# Response
{
  "status": "healthy",
  "database": "healthy",
  "active_brands": 25,
  "total_runs": 1543,
  "timestamp": "2026-05-16T08:00:00Z"
}
```

## Monitoring & Alerts

### Slack Alerts

Configure Slack webhook to receive alerts for:
- Monitor failures (after threshold)
- High error rates
- No scans running
- Database errors
- DLQ overflow

### Alert Types

| Alert | Trigger | Frequency |
|-------|---------|-----------|
| Monitor Down | 3+ consecutive failures | Once per hour |
| Monitor Recovered | Circuit breaker closes | Immediate |
| High Error Rate | >50% failures | Once per 2 hours |
| No Scans | No runs in 2+ hours | Once per 4 hours |
| Database Error | Connection failure | Once per hour |
| DLQ Overflow | >100 pending items | Once per 6 hours |

## Circuit Breaker

Prevents cascading failures by temporarily disabling failing monitors.

### States

1. **CLOSED** - Normal operation
2. **OPEN** - Monitor disabled after failures
3. **HALF_OPEN** - Testing if monitor recovered

### Configuration

```python
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5  # Failures before opening
CIRCUIT_BREAKER_TIMEOUT_SECONDS=300  # Wait before retry
```

## Dead Letter Queue (DLQ)

Failed hits are stored in DLQ for retry and manual review.

### Features

- Automatic retry with exponential backoff
- Deduplication
- Manual requeue
- Permanent failure tracking

### Management

```python
# Get DLQ stats
from app.daemon.dlq import DeadLetterQueue
dlq = DeadLetterQueue(db_client)
stats = await dlq.get_stats()

# Get failed items
failed = await dlq.get_failed_items(limit=50)

# Requeue item
await dlq.requeue_failed(dlq_id)

# Clear resolved items
await dlq.clear_resolved(days_old=7)
```

## Troubleshooting

### Daemon Won't Start

1. **Check logs:**
```bash
sudo journalctl -u brand-intel-monitor -n 50
```

2. **Verify MongoDB connection:**
```bash
mongosh $MONGODB_URI
```

3. **Check permissions:**
```bash
ls -la /opt/brand-intel/backend
```

### High Memory Usage

- Reduce `MAX_CONCURRENT_BRANDS`
- Increase `SCAN_INTERVAL_MINUTES`
- Check for memory leaks in monitors

### Monitors Failing

1. **Check circuit breaker status:**
```bash
curl http://localhost:8001/stats
```

2. **Review error logs:**
```bash
tail -f daemon.log
```

3. **Manually reset circuit breaker:**
```python
from app.daemon.circuit_breaker import CircuitBreaker
cb = CircuitBreaker()
cb.reset('monitor_name')
```

### No Scans Running

1. **Check daemon status:**
```bash
sudo systemctl status brand-intel-monitor
```

2. **Verify scheduler:**
```bash
# Check logs for "Starting scheduled scan"
sudo journalctl -u brand-intel-monitor | grep "scheduled scan"
```

3. **Check active brands:**
```bash
mongosh $MONGODB_URI
use brand_intel
db.brands.countDocuments({active: true})
```

## Performance Tuning

### For 10-50 Brands

```bash
SCAN_INTERVAL_MINUTES=15
MAX_CONCURRENT_BRANDS=10
MAX_CONCURRENT_MONITORS=4
```

**Expected:**
- Scan cycle: 5-10 minutes
- Memory: 500 MB - 1 GB
- CPU: 1-2 cores

### For 50-100 Brands

```bash
SCAN_INTERVAL_MINUTES=20
MAX_CONCURRENT_BRANDS=15
MAX_CONCURRENT_MONITORS=4
```

**Expected:**
- Scan cycle: 10-15 minutes
- Memory: 1-2 GB
- CPU: 2-4 cores

### For 100+ Brands

Consider horizontal scaling with message queue (RabbitMQ/Redis).

## Maintenance

### Regular Tasks

1. **Clear old alerts (monthly):**
```python
await alert_manager.clear_old_alerts(days=30)
```

2. **Clear resolved DLQ items (weekly):**
```python
await dlq.clear_resolved(days_old=7)
```

3. **Review failed DLQ items (weekly):**
```python
failed = await dlq.get_failed_items(limit=50)
```

4. **Monitor disk usage:**
```bash
du -sh /opt/brand-intel/backend/daemon.log
```

### Backup

Backup MongoDB regularly:
```bash
mongodump --uri=$MONGODB_URI --out=/backup/$(date +%Y%m%d)
```

## Development

### Running Locally

```bash
# Terminal 1: MongoDB
mongod --dbpath ./data

# Terminal 2: Daemon
python daemon.py
```

### Testing

```bash
# Run tests
pytest backend/tests/

# Test specific monitor
pytest backend/tests/test_monitors.py::test_pastebin_monitor
```

### Adding New Monitor

1. Create monitor class in `app/monitors/`
2. Inherit from `BaseMonitor`
3. Implement `search()` and `is_available()`
4. Add to `_create_monitors()` in `scheduler.py`

## Support

- **Documentation:** See `monitoring-architecture-review.md`
- **Issues:** Check logs and health endpoints
- **Alerts:** Configure Slack for proactive monitoring

## License

[Your License]