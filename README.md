# PortBroker

An API service built with uv + FastAPI that translates Anthropic API calls to OpenAI-compatible format and manages multiple AI providers.

## Features

- **API Translation**: Converts between Anthropic API format (`/api/anthropic/v1/messages`) and OpenAI format (`/v1/chat/completions`)
- **Multi-Provider Support**: Manage multiple OpenAI-compatible providers with automatic failover
- **Database Flexibility**: Support for SQLite, PostgreSQL, and Supabase
- **Provider Management**: Full CRUD operations for AI providers and API keys
- **Model Mapping**: Intelligent mapping of Claude models (haiku/sonnet/opus) to provider-specific models
- **Streaming Support**: Full streaming response support for both API formats

## Quick Start

1. **Install dependencies with uv**:
   ```bash
   uv sync
   ```

2. **Set up environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Run the server**:
   ```bash
   uv run python run.py
   ```

## Configuration

### Environment Variables

- `DATABASE_TYPE`: `sqlite`, `postgresql`, or `supabase`
- `DATABASE_URL`: Database connection string
- `HOST`: Server host (default: 0.0.0.0)
- `PORT`: Server port (default: 8000)
- `SECRET_KEY`: JWT secret key

### Database Setup

#### SQLite (Default)
```env
DATABASE_TYPE=sqlite
DATABASE_URL=sqlite:///./portbroker.db
```

#### PostgreSQL
```env
DATABASE_TYPE=postgresql
DATABASE_URL=postgresql://user:password@localhost/portbroker
```

#### Supabase
```env
DATABASE_TYPE=supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
```

## API Endpoints

### OpenAI Compatible
- `POST /v1/chat/completions` - OpenAI chat completions endpoint

### Anthropic Compatible
- `POST /api/anthropic/v1/messages` - Anthropic messages endpoint

### Provider Management
- `GET /admin/providers` - List all providers
- `POST /admin/providers` - Create new provider
- `PUT /admin/providers/{id}` - Update provider
- `DELETE /admin/providers/{id}` - Delete provider

### API Key Management
- `GET /admin/api-keys` - List API keys
- `POST /admin/api-keys` - Create API key
- `PUT /admin/api-keys/{id}` - Update API key
- `DELETE /admin/api-keys/{id}` - Delete API key

## Provider Configuration

Example provider configuration:

```json
{
  "name": "OpenAI",
  "provider_type": "openai",
  "base_url": "https://api.openai.com/v1",
  "api_key": "sk-your-key",
  "big_model": "gpt-4o",
  "medium_model": "gpt-4o",
  "small_model": "gpt-4o-mini",
  "is_active": true,
  "priority": 1
}
```

## Model Mapping

Claude models are automatically mapped to provider models:
- `haiku` → `small_model`
- `sonnet` → `medium_model` 
- `opus` → `big_model`

## Development

```bash
# Install development dependencies
uv sync --dev

# Run with auto-reload
uv run uvicorn app.main:app --reload

# Format code
uv run black .
uv run isort .

# Type checking
uv run mypy .
```

## License

MIT License