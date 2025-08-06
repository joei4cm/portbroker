# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PortBroker is an API service built with FastAPI that translates between Anthropic and OpenAI API formats while managing multiple AI providers. It acts as a universal API gateway that allows clients to use either API format seamlessly, with intelligent model mapping and provider failover.

The system includes both a backend API service and a Vue.js-based portal interface for comprehensive provider and strategy management.

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
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=app

# Run tests with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_portal.py

# Run specific test class
uv run pytest tests/test_portal.py::TestPortalAuth

# Run specific test method
uv run pytest tests/test_portal.py::TestPortalAuth::test_portal_login_page

# Run tests with coverage report
uv run pytest --cov=app --cov-report=html

# Run tests by category
uv run pytest -m unit          # Unit tests only
uv run pytest -m integration   # Integration tests only
uv run pytest -m api           # API tests only
uv run pytest -m portal        # Portal tests only
```

### Testing Guidelines

**IMPORTANT**: Always run tests after making changes to ensure functionality is preserved:

1. **Before committing changes**: Run `uv run pytest` to verify all tests pass
2. **After API changes**: Run relevant test files and ensure new functionality is tested
3. **After UI changes**: Run portal tests to verify authentication and permissions work
4. **After database changes**: Run all tests to ensure data integrity

**Test Coverage Requirements**:
- **API Endpoints**: All endpoints must have tests for success and error cases
- **Authentication**: Both admin and non-admin user scenarios must be tested
- **Portal UI**: Login, navigation, and role-based access must be tested
- **Database Operations**: CRUD operations must be tested with proper cleanup
- **Error Handling**: All error paths must have corresponding tests

**Test Structure**:
- `test_api.py`: Core API functionality and endpoints
- `test_portal.py`: Portal authentication and UI functionality
- `test_providers.py`: Provider management and operations
- `test_api_keys.py`: API key management and authentication
- `test_provider_service.py`: Business logic for provider operations
- `test_translation.py`: API translation service
- `test_utils.py`: Utility functions and helpers

**Testing Best Practices**:
- Use fixtures for common test data (providers, API keys, etc.)
- Test both success and failure scenarios
- Verify role-based access controls (admin vs non-admin)
- Clean up test data to avoid test pollution
- Use async testing for database operations
- Test authentication and authorization separately

### Python Execution
```bash
# Run any Python script (ALWAYS use uv run)
uv run python <script_name>.py

# Run the application directly
uv run python run.py

# Run development server with auto-reload
uv run uvicorn app.main:app --reload
```

## Portal Authentication

**IMPORTANT**: The portal uses JWT token authentication, not direct API key authentication. When working with the portal:

1. **Login via web interface**: Access `/portal` and use the login form
2. **JWT tokens are stored**: After login, JWT tokens are stored in localStorage and used for API requests
3. **API key authentication is separate**: API keys are used for external API access, not portal login
4. **Admin vs non-admin users**: Portal permissions are controlled by JWT claims, not API keys

### Debugging Authentication Issues
- Check browser console for authentication errors
- Verify JWT token is present in localStorage
- Use browser dev tools to inspect network requests for Authorization headers
- Admin users have additional permissions for provider management

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
- **Run tests before committing**: Ensure all functionality works after changes
- **Write tests for new features**: All new functionality must have corresponding tests

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