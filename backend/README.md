# Brand Intel - Monitors Component

The Monitors component is the data ingestion backbone of the breach detection system. It continuously scrapes multiple sources (Pastebin, GitHub, HIBP, Reddit) for potential data leaks, applies sophisticated keyword matching, and stores raw hits in MongoDB for downstream processing.

## Architecture Overview

```
Monitor Orchestrator
├── Pastebin Monitor
├── GitHub Monitor
├── HIBP Monitor
└── Reddit Monitor
    ↓
Keyword Matching Engine
    ↓
Raw Hit Storage (MongoDB)
```

## Features

- **Multi-Source Monitoring**: Pastebin, GitHub, HaveIBeenPwned, Reddit
- **Advanced Keyword Matching**: Exact, fuzzy, regex, domain similarity
- **Rate Limiting**: Respects API rate limits for all sources
- **Error Handling**: Automatic retry with exponential backoff
- **Deduplication**: Content hashing to avoid duplicate storage
- **Health Monitoring**: Track monitor performance and errors
- **Parallel Execution**: Run all monitors concurrently

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys
```

3. Start MongoDB:
```bash
docker run -d -p 27017:27017 mongo:latest
```

## Configuration

### Environment Variables

See `.env.example` for all required environment variables:

- `MONGODB_URI`: MongoDB connection string
- `PASTEBIN_API_KEY`: Pastebin PRO API key
- `GITHUB_TOKEN`: GitHub personal access token
- `HIBP_API_KEY`: HaveIBeenPwned API key
- `REDDIT_CLIENT_ID`: Reddit API client ID
- `REDDIT_CLIENT_SECRET`: Reddit API client secret

### Monitor Configuration

Each brand can configure which monitors to enable:

```python
{
    "monitor_config": {
        "pastebin_enabled": True,
        "github_enabled": True,
        "hibp_enabled": True,
        "reddit_enabled": True,
        "scan_frequency_minutes": 15
    }
}
```

## Usage

### Basic Usage

```python
from motor.motor_asyncio import AsyncIOMotorClient
from app.monitors.pastebin import PastebinMonitor
from app.monitors.github import GitHubMonitor
from app.monitors.hibp import HIBPMonitor
from app.monitors.reddit import RedditMonitor
from app.monitors.orchestrator import MonitorOrchestrator
from app.monitors.storage import RawHitStorage
from app.monitors.detector import KeywordMatcher
from app.monitors.base import MonitorConfig

# Initialize MongoDB
db_client = AsyncIOMotorClient("mongodb://localhost:27017")

# Initialize monitors
config = MonitorConfig()
monitors = [
    PastebinMonitor(config, api_key="your_key"),
    GitHubMonitor(config, github_token="your_token"),
    HIBPMonitor(config, api_key="your_key"),
    RedditMonitor(config, client_id="id", client_secret="secret")
]

# Initialize orchestrator
storage = RawHitStorage(db_client)
matcher = KeywordMatcher()
orchestrator = MonitorOrchestrator(monitors, storage, matcher, db_client)

# Run monitors for all brands
result = await orchestrator.run_scheduled_scan()
print(f"Scanned {result['brands_scanned']} brands")
print(f"Found {sum(r['total_hits_found'] for r in result['results'])} hits")
```

### Running Tests

```bash
pytest backend/tests/test_monitors.py -v
```

## Component Details

### 1. Base Monitor Architecture

All monitors inherit from `BaseMonitor` which provides:
- Rate limiting
- Error handling
- API call tracking
- Availability checking

### 2. Individual Monitors

#### PastebinMonitor
- Scrapes recent pastes using Pastebin API
- Rate limit: 60 requests/minute
- Filters by size and content type

#### GitHubMonitor
- Searches code, commits for brand mentions
- Rate limit: 30 requests/minute
- Focuses on sensitive files (.env, config, etc.)

#### HIBPMonitor
- Checks for domain breaches
- Rate limit: 40 requests/minute
- Calculates severity based on data classes

#### RedditMonitor
- Monitors security subreddits
- Searches posts and comments
- Uses PRAW for API access

### 3. Keyword Matching Engine

Multi-strategy matching:
- **Exact matching**: Case-insensitive keyword search
- **Fuzzy matching**: Typosquatting detection (85% similarity)
- **Regex patterns**: Custom pattern matching
- **Email patterns**: Extract and match email addresses
- **Domain similarity**: Detect similar domains (80% similarity)

### 4. Raw Hit Storage

Features:
- Content hash deduplication
- Batch operations
- MongoDB indexing
- Processing status tracking

### 5. Monitor Orchestrator

Coordinates all monitors:
- Parallel execution
- Brand-specific configuration
- Error aggregation
- Result tracking

### 6. Health Monitoring

Track monitor health:
- Success rates
- Execution times
- Error summaries
- Stale monitor detection

## MongoDB Schema

### Collections

#### brands
```javascript
{
  "_id": ObjectId,
  "name": "Acme Corp",
  "domain": "acme.com",
  "keywords": ["acme", "acme corp"],
  "email_patterns": ["@acme.com"],
  "regex_patterns": ["acme[_-]?corp"],
  "monitor_config": {
    "pastebin_enabled": true,
    "github_enabled": true,
    "hibp_enabled": true,
    "reddit_enabled": true,
    "scan_frequency_minutes": 15
  },
  "active": true
}
```

#### raw_hits
```javascript
{
  "_id": ObjectId,
  "brand_id": ObjectId,
  "source": "pastebin",
  "source_url": "https://pastebin.com/xyz",
  "raw_content": "...",
  "content_hash": "sha256...",
  "detected_at": ISODate,
  "match_details": {
    "matched_keywords": ["acme"],
    "confidence_score": 0.95,
    "match_locations": [...]
  },
  "processing_status": "pending"
}
```

#### monitor_runs
```javascript
{
  "_id": ObjectId,
  "monitor_type": "pastebin",
  "brand_id": ObjectId,
  "started_at": ISODate,
  "completed_at": ISODate,
  "status": "completed",
  "hits_found": 10,
  "hits_stored": 8,
  "execution_time_seconds": 5.2
}
```

## Performance Considerations

1. **Parallel Execution**: All monitors run concurrently
2. **Rate Limiting**: Respects API limits to avoid bans
3. **Deduplication**: Content hashing prevents duplicates
4. **Indexing**: Proper MongoDB indexes for fast queries
5. **Batch Operations**: Store hits in batches
6. **Connection Pooling**: Reuse HTTP connections

## Security Considerations

1. **API Key Storage**: All keys in environment variables
2. **Content Sanitization**: Sanitize before storage
3. **Access Control**: Implement authentication
4. **Rate Limit Protection**: Prevent abuse
5. **Data Encryption**: Encrypt sensitive data at rest

## Troubleshooting

### Monitor Not Running

Check health status:
```python
from app.monitors.health import MonitorHealthChecker

health_checker = MonitorHealthChecker(db_client)
status = await health_checker.get_health_status()
print(status)
```

### Rate Limit Errors

Check rate limit status:
```python
status = monitor.get_rate_limit_status()
print(f"Remaining: {status['remaining']}")
print(f"Reset time: {status['reset_time']}")
```

### No Hits Found

1. Verify brand configuration (keywords, patterns)
2. Check monitor availability
3. Review error logs in `monitor_runs` collection

## API Reference

See individual module documentation:
- `app.monitors.base` - Base monitor classes
- `app.monitors.detector` - Keyword matching
- `app.monitors.storage` - Hit storage
- `app.monitors.orchestrator` - Monitor coordination
- `app.monitors.health` - Health monitoring

## Contributing

1. Follow existing code structure
2. Add tests for new features
3. Update documentation
4. Ensure all tests pass

## License

Proprietary - Brand Intel