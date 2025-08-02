# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PortBroker is an API service built with FastAPI that translates between Anthropic and OpenAI API formats while managing multiple AI providers. It acts as a universal API gateway that allows clients to use either API format seamlessly, with intelligent model mapping and provider failover.

## Development Commands

### Environment Setup
```bash
# Install dependencies with uv (ALWAYS use uv, not venv)
uv sync

# Install development dependencies
uv sync --dev

# Set up environment
cp .env.example .env
# Edit .env with your configuration
```

### Running the Application
```bash
# Production server
uv run python run.py

# Development with auto-reload
uv run uvicorn app.main:app --reload

# Alternative development run
uv run python -m uvicorn app.main:app --reload
```

### Code Quality
```bash
# Format code
uv run black .
uv run isort .

# Type checking
uv run mypy .

# Linting
uv run flake8 .
```

### Testing
```bash
# Run tests
uv run pytest

# Run with coverage
uv run pytest --cov=app

# Run tests with verbose output
uv run pytest -v
```

### Python Execution
```bash
# Run any Python script (ALWAYS use uv run)
uv run python <script_name>.py

# Run the application directly
uv run python run.py

# Run development server with auto-reload
uv run uvicorn app.main:app --reload
```

## Debugging Ground Rules

### Dependency Management
- **ALWAYS use `uv` instead of `venv`** for dependency management
- **NEVER create virtual environments manually** - `uv` handles this automatically
- **ALWAYS prefix Python commands with `uv run`** to ensure proper dependency resolution
- **Use `uv sync` to install/update dependencies** - this reads from `pyproject.toml`
- **Use `uv sync --dev` for development dependencies** (testing, linting, formatting tools)

### Debugging Workflow
```bash
# Check database connectivity and schema
uv run python -c "from app.core.database import init_db; import asyncio; asyncio.run(init_db())"

# Test provider configuration
uv run python -c "from app.services.provider_service import ProviderService; from app.core.database import AsyncSessionLocal; import asyncio; async def test(): async with AsyncSessionLocal() as db: providers = await ProviderService.get_active_providers(db); print([p.name for p in providers]); asyncio.run(test())"

# Debug translation service
uv run python -c "from app.services.translation import TranslationService; print('Translation service loaded successfully')"

# Run with verbose logging
uv run uvicorn app.main:app --reload --log-level debug

# Test specific endpoints
uv run python -c "
import httpx
import asyncio
async def test():
    async with httpx.AsyncClient() as client:
        resp = await client.get('http://localhost:8000/docs')
        print(f'Status: {resp.status_code}')
asyncio.run(test())
"
```

### Common Debugging Scenarios
1. **Provider connection issues**: Check `base_url` and `api_key` in database
2. **Model mapping failures**: Verify `small_model`, `medium_model`, `big_model` fields
3. **Database connection errors**: Validate `DATABASE_TYPE` and `DATABASE_URL` in `.env`
4. **Translation errors**: Test with simple requests first, then complex ones
5. **Import errors**: Run `uv sync` to ensure all dependencies are installed

### Development Best Practices
- **Always use `uv run`** for Python execution to avoid dependency conflicts
- **Test incrementally**: Start with simple cases, then add complexity
- **Check logs**: Use `--log-level debug` for detailed output
- **Verify database state**: Use admin endpoints to check provider configurations
- **Use the test suite**: Run `uv run pytest` to catch issues early

## Architecture

### Core Components

1. **API Translation Layer** (`app/services/translation.py`):
   - Converts Anthropic API requests to OpenAI format and vice versa
   - Handles model mapping (claude-3-haiku/sonnet/opus → provider models)
   - Manages streaming responses and tool/function calling translation

2. **Provider Management** (`app/services/provider_service.py`):
   - Manages multiple AI providers with priority-based failover
   - Handles provider CRUD operations and health checks
   - Supports OpenAI-compatible providers (OpenAI, Azure, custom endpoints)

3. **Database Layer** (`app/core/database.py`):
   - Supports SQLite (default), PostgreSQL, and Supabase
   - Uses SQLAlchemy 2.0 with async support
   - Stores provider configurations and API keys

4. **API Endpoints** (`app/api/v1/`):
   - `/v1/chat/completions` - OpenAI-compatible endpoint
   - `/api/anthropic/v1/messages` - Anthropic-compatible endpoint
   - `/admin/providers` - Provider management
   - `/admin/api-keys` - API key management

### Design Patterns

- **Repository Pattern**: Database access through SQLAlchemy models
- **Service Layer**: Business logic separated from API handlers
- **Schema Validation**: Pydantic models for request/response validation
- **Dependency Injection**: FastAPI's dependency system for database sessions

### Model Mapping Strategy

The service intelligently maps Claude models to provider models:
- `haiku` → provider's `small_model` field
- `sonnet` → provider's `medium_model` field  
- `opus` → provider's `big_model` field

This allows seamless translation between API formats while maintaining appropriate model sizing.

### Database Schema

Key tables:
- `providers`: Stores AI provider configurations (name, base_url, api_key, model mappings)
- `api_keys`: Stores API keys for external authentication

### Configuration

Environment variables control:
- Database type and connection strings (`DATABASE_TYPE`, `DATABASE_URL`)
- Server host/port (`HOST`, `PORT`)
- Default provider settings
- Security configuration (`SECRET_KEY`)
- Supabase integration (`SUPABASE_URL`, `SUPABASE_KEY`)

The application uses `pydantic-settings` for configuration management with `.env` file support.

#### Supported Database Types:
- **SQLite** (default): `DATABASE_TYPE=sqlite`
- **PostgreSQL**: `DATABASE_TYPE=postgresql` 
- **Supabase**: `DATABASE_TYPE=supabase`