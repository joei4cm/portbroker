# PortBroker

An API service built with uv + FastAPI that translates Anthropic API calls to OpenAI-compatible format and manages multiple AI providers.

## Features

- **API Translation**: Converts between Anthropic API format (`/api/anthropic/v1/messages`) and OpenAI format (`/v1/chat/completions`)
- **Multi-Provider Support**: Manage multiple OpenAI-compatible providers with automatic failover
- **Database Flexibility**: Support for SQLite, PostgreSQL, and Supabase
- **Provider Management**: Full CRUD operations for AI providers and API keys via admin endpoints
- **Model Mapping**: Intelligent mapping of Claude models (haiku/sonnet/opus) to provider-specific models
- **Streaming Support**: Full streaming response support for both API formats
- **Tool/Function Calling**: Complete translation of tool calling between API formats
- **Health Checks**: Provider health monitoring and automatic failover

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

Example provider configurations:

### OpenAI Provider
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

### Azure OpenAI Provider
```json
{
  "name": "Azure OpenAI",
  "provider_type": "azure",
  "base_url": "https://your-resource.openai.azure.com/openai/deployments",
  "api_key": "your-azure-key",
  "big_model": "gpt-4-deployment",
  "medium_model": "gpt-4-deployment",
  "small_model": "gpt-35-turbo-deployment",
  "is_active": true,
  "priority": 2
}
```

### Anthropic Provider (via OpenAI-Compatible API)
```json
{
  "name": "Anthropic",
  "provider_type": "anthropic",
  "base_url": "https://api.anthropic.com/v1/messages",
  "api_key": "sk-ant-your-key",
  "headers": {
    "anthropic-version": "2023-06-01"
  },
  "big_model": "claude-3-opus-20240229",
  "medium_model": "claude-3-sonnet-20240229",
  "small_model": "claude-3-haiku-20240307",
  "is_active": true,
  "priority": 3
}
```

### Google Gemini Provider
```json
{
  "name": "Google Gemini",
  "provider_type": "gemini",
  "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
  "api_key": "your-gemini-key",
  "big_model": "gemini-1.5-pro",
  "medium_model": "gemini-1.5-flash",
  "small_model": "gemini-1.5-flash",
  "is_active": true,
  "priority": 4
}
```

### Mistral AI Provider
```json
{
  "name": "Mistral AI",
  "provider_type": "mistral",
  "base_url": "https://api.mistral.ai/v1",
  "api_key": "your-mistral-key",
  "big_model": "mistral-large-latest",
  "medium_model": "mistral-medium-latest",
  "small_model": "mistral-small-latest",
  "is_active": true,
  "priority": 5
}
```

### Perplexity Provider
```json
{
  "name": "Perplexity",
  "provider_type": "perplexity",
  "base_url": "https://api.perplexity.ai",
  "api_key": "pplx-your-key",
  "big_model": "llama-3.1-sonar-large-128k-online",
  "medium_model": "llama-3.1-sonar-large-128k-online",
  "small_model": "llama-3.1-sonar-small-128k-online",
  "is_active": true,
  "priority": 6
}
```

### Local Ollama Provider
```json
{
  "name": "Local Ollama",
  "provider_type": "ollama",
  "base_url": "http://localhost:11434/v1",
  "api_key": "ollama",
  "big_model": "llama3:70b",
  "medium_model": "llama3:8b",
  "small_model": "llama3:8b",
  "is_active": true,
  "priority": 7
}
```

### Custom Provider with Additional Headers
```json
{
  "name": "Custom AI Service",
  "provider_type": "custom",
  "base_url": "https://your-custom-api.com/v1",
  "api_key": "your-custom-key",
  "headers": {
    "X-Api-Version": "2024-01-01",
    "X-Custom-Header": "custom-value"
  },
  "big_model": "custom-large-model",
  "medium_model": "custom-medium-model",
  "small_model": "custom-small-model",
  "is_active": true,
  "priority": 8
}
```

### Groq Provider
```json
{
  "name": "Groq",
  "provider_type": "groq",
  "base_url": "https://api.groq.com/openai/v1",
  "api_key": "gsk_your-groq-key",
  "big_model": "llama-3.1-70b-versatile",
  "medium_model": "llama-3.1-8b-instant",
  "small_model": "llama-3.1-8b-instant",
  "is_active": true,
  "priority": 9
}
```

### OpenRouter Provider
```json
{
  "name": "OpenRouter",
  "provider_type": "openrouter",
  "base_url": "https://openrouter.ai/api/v1",
  "api_key": "sk-or-your-key",
  "headers": {
    "HTTP-Referer": "https://your-domain.com",
    "X-Title": "Your App Name"
  },
  "big_model": "anthropic/claude-3.5-sonnet",
  "medium_model": "anthropic/claude-3.5-sonnet",
  "small_model": "anthropic/claude-3-haiku",
  "is_active": true,
  "priority": 10
}
```

## Provider Configuration Fields

All provider configurations support the following fields:

### Required Fields
- `name`: Display name for the provider
- `provider_type`: Type identifier (openai, azure, anthropic, gemini, mistral, etc.)
- `base_url`: API endpoint URL
- `api_key`: Authentication key for the provider
- `big_model`: Model name for opus-tier requests
- `medium_model`: Model name for sonnet-tier requests  
- `small_model`: Model name for haiku-tier requests
- `is_active`: Boolean to enable/disable the provider
- `priority`: Integer for failover order (lower = higher priority)

### Optional Fields
- `headers`: Additional HTTP headers (object)
- `timeout`: Request timeout in seconds (default: 300)

### Provider Best Practices

1. **Priority Setup**: Assign lower numbers to preferred providers (1=highest priority, 10=lowest priority)
2. **Model Selection**: Choose appropriate model sizes for each tier
3. **Headers**: Include required provider-specific headers (e.g., `anthropic-version`)
4. **Testing**: Verify provider connectivity after configuration
5. **Failover**: Configure multiple providers with different priorities

### Fallback Policy

The service follows a priority-based failover mechanism:
- **Priority 1**: Tried first (highest priority)
- **Priority 2**: Tried if priority 1 fails
- **Priority 3+**: Tried in ascending order
- Only active providers (`is_active=True`) are considered
- If all providers fail, an exception is raised with the last error

### Adding Providers via API

```bash
# Create a new provider
curl -X POST http://localhost:8000/admin/providers \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Provider",
    "provider_type": "openai",
    "base_url": "https://api.example.com/v1",
    "api_key": "sk-your-key",
    "big_model": "gpt-4",
    "medium_model": "gpt-3.5-turbo",
    "small_model": "gpt-3.5-turbo",
    "is_active": true,
    "priority": 10
  }'

# List all providers
curl http://localhost:8000/admin/providers

# Update a provider
curl -X PUT http://localhost:8000/admin/providers/1 \
  -H "Content-Type: application/json" \
  -d '{"is_active": false}'
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

# Linting
uv run flake8 .

# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=app
```

## Admin Interface

PortBroker includes a web-based admin interface for managing providers, API keys, and settings.

### Accessing the Admin Interface

Start the server and visit: http://localhost:8000/admin

### Features

#### Provider Management
- **Create Providers**: Add new AI providers with full configuration
- **Edit Providers**: Modify existing provider settings
- **Toggle Status**: Activate/deactivate providers without deletion
- **Delete Providers**: Remove provider configurations
- **Priority Management**: Set provider failover order
- **Model Mapping**: Configure small, medium, and large model mappings

#### API Key Management
- **Create API Keys**: Generate new authentication keys
- **Edit API Keys**: Modify key properties and expiration
- **Toggle Status**: Enable/disable API keys
- **Delete API Keys**: Remove authentication keys
- **Expiration Dates**: Set optional expiration dates
- **Description**: Add descriptive information for keys

#### Settings Configuration
- **Database Type**: Switch between SQLite, PostgreSQL, and Supabase
- **Database URL**: Configure database connection strings
- **Supabase Integration**: Configure Supabase URL and API keys
- **Server Settings**: Configure host, port, and debug settings

### Supported Provider Types

The admin interface supports all provider types:
- OpenAI
- Azure OpenAI
- Anthropic
- Google Gemini
- Mistral AI
- Perplexity
- Local Ollama
- Groq
- OpenRouter
- Custom providers

### Frontend Stack

- **TailwindCSS**: Modern utility-first CSS framework
- **Font Awesome**: Icon library for UI elements
- **Vanilla JavaScript**: No framework dependencies
- **Responsive Design**: Works on desktop and mobile devices
- **FastAPI Templates**: Server-side HTML rendering

### Admin API Endpoints

The admin interface uses these internal API endpoints:

- `GET /admin` - Admin dashboard HTML
- `GET /admin/providers` - List all providers
- `POST /admin/providers` - Create new provider
- `PUT /admin/providers/{id}` - Update provider
- `DELETE /admin/providers/{id}` - Delete provider
- `GET /admin/api-keys` - List all API keys
- `POST /admin/api-keys` - Create new API key
- `PUT /admin/api-keys/{id}` - Update API key
- `DELETE /admin/api-keys/{id}` - Delete API key
- `GET /admin/settings` - Get current settings
- `POST /admin/settings` - Update settings

## Architecture

PortBroker follows a clean architecture pattern:

- **API Layer**: FastAPI endpoints handling both Anthropic and OpenAI formats
- **Service Layer**: Business logic for translation, provider management, and failover
- **Repository Layer**: SQLAlchemy models and database operations
- **Translation Engine**: Core logic for converting between API formats

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and ensure code quality checks pass
5. Submit a pull request

## License

MIT License