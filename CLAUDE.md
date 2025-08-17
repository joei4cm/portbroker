# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PortBroker is an advanced API service built with FastAPI that translates between Anthropic and OpenAI API formats while managing multiple AI providers through intelligent strategy-based routing. It acts as a universal API gateway with sophisticated model mapping, provider failover, and load balancing capabilities.

The system features:
- **Multi-Provider Strategy System**: Intelligent routing across multiple AI providers with configurable fallback logic
- **Vue.js Portal Interface**: Modern web interface for comprehensive provider, strategy, and API key management
- **Dual API Support**: Seamless translation between Anthropic and OpenAI API formats
- **Intelligent Model Mapping**: Automatic model selection based on provider capabilities and strategy configuration
- **Comprehensive Authentication**: JWT-based portal authentication and API key-based external access

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

### Portal Development
```bash
# Navigate to portal directory
cd portal

# Install dependencies
npm install

# Development server with hot reload
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
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

# Run tests excluding slow tests
uv run pytest -m "not slow"
```

### Testing Guidelines

**IMPORTANT**: Always run tests after making changes to ensure functionality is preserved:

1. **Before committing changes**: Run `uv run pytest` to verify all tests pass
2. **After API changes**: Run relevant test files and ensure new functionality is tested
3. **After UI changes**: Run portal tests to verify authentication and permissions work
4. **After database changes**: Run all tests to ensure data integrity

**Test Database Configuration**:
- **Separate Test Database**: Tests use `portbroker_test.db` to avoid affecting production data
- **Environment Configuration**: Test settings are in `.env.test` file
- **Database Isolation**: All test operations are confined to the test database
- **Cleanup**: Tests automatically clean up created data to maintain test isolation
- **Configuration**: Test database settings managed in `app/core/test_config.py`

**Test Coverage Requirements**:
- **API Endpoints**: All endpoints must have tests for success and error cases
- **Authentication**: Both admin and non-admin user scenarios must be tested
- **Portal UI**: Login, navigation, and role-based access must be tested
- **Database Operations**: CRUD operations must be tested with proper cleanup
- **Error Handling**: All error paths must have corresponding tests
- **Minimum Coverage**: Tests must maintain at least 80% code coverage (enforced by pytest configuration)

**Test Structure**:
- `test_api.py`: Core API functionality and endpoints
- `test_portal.py`: Portal authentication and UI functionality
- `test_providers.py`: Provider management and operations
- `test_api_keys.py`: API key management and authentication
- `test_provider_service.py`: Business logic for provider operations
- `test_translation.py`: API translation service
- `test_utils.py`: Utility functions and helpers
- `test_strategies.py`: Strategy management and model mapping
- `test_duplicate_providers.py`: Provider uniqueness validation
- `test_api_key_regeneration.py`: API key regeneration functionality
- `conftest.py`: Test configuration and fixtures

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

2. **Strategy System** (`app/services/strategy_service.py`):
   - Manages multi-provider routing strategies with fallback logic
   - Handles intelligent model selection based on provider capabilities
   - Supports load balancing and failover across multiple providers

3. **Provider Management** (`app/services/provider_service.py`):
   - Manages multiple AI providers with priority-based failover
   - Handles provider CRUD operations and health checks
   - Supports OpenAI-compatible providers (OpenAI, Azure, custom endpoints)

4. **Database Layer** (`app/core/database.py`):
   - Supports SQLite (default), PostgreSQL, and Supabase
   - Uses SQLAlchemy 2.0 with async support
   - Stores provider configurations, API keys, and strategies

5. **Authentication System** (`app/core/auth.py`):
   - JWT-based authentication for portal access
   - API key authentication for external API access
   - Role-based access control (admin vs user)

6. **Vue.js Portal** (`portal/`):
   - Modern web interface built with Vue.js 3 and Ant Design Vue
   - Comprehensive management UI for providers, strategies, and API keys
   - Real-time status monitoring and testing capabilities

7. **API Endpoints** (`app/api/v1/`):
   - `/v1/chat/completions` - OpenAI-compatible endpoint
   - `/api/anthropic/v1/messages` - Anthropic-compatible endpoint
   - `/api/portal/*` - Portal management endpoints
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
- `providers`: Stores AI provider configurations (name, base_url, api_key, model mappings, headers, SSL settings)
- `api_keys`: Stores API keys for external authentication with expiration support
- `model_strategies`: Strategy definitions with fallback logic and routing rules
- `strategy_provider_mappings`: Many-to-many mapping between strategies and providers with priorities

**Database Migration**:
- Uses Alembic for database schema migrations
- Automatically initializes database on first run
- Run `uv run alembic upgrade head` to apply migrations manually if needed

### Strategy System

The strategy system enables intelligent routing across multiple providers:

- **Strategy Creation**: Define strategies with specific routing rules and fallback logic
- **Provider Mapping**: Associate multiple providers with each strategy, ordered by priority
- **Model Mapping**: Automatic model selection based on provider capabilities and strategy configuration
- **Load Balancing**: Distribute requests across providers based on availability and performance
- **Failover**: Automatic fallback to backup providers when primary providers are unavailable

### Configuration

Environment variables control:
- Database type and connection strings (`DATABASE_TYPE`, `DATABASE_URL`)
- Server host/port (`HOST`, `PORT`)
- JWT authentication (`SECRET_KEY`, `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`)
- Default provider settings (`DEFAULT_OPENAI_API_KEY`, `DEFAULT_OPENAI_BASE_URL`)
- Default model mappings (`DEFAULT_BIG_MODEL`, `DEFAULT_SMALL_MODEL`)
- Security configuration (`SECRET_KEY`)
- Supabase integration (`SUPABASE_URL`, `SUPABASE_KEY`)

The application uses `pydantic-settings` for configuration management with `.env` file support.

#### Supported Database Types:
- **SQLite** (default): `DATABASE_TYPE=sqlite`
- **PostgreSQL**: `DATABASE_TYPE=postgresql` 
- **Supabase**: `DATABASE_TYPE=supabase`

### Authentication System

The system uses dual authentication approaches:

1. **Portal Authentication (JWT)**:
   - Username/password login via web interface
   - JWT tokens stored in localStorage
   - Role-based access control (admin vs user)
   - Automatic token refresh and expiration handling

2. **API Authentication (API Keys)**:
   - Bearer token authentication for external API access
   - Configurable expiration dates for API keys
   - Key-based access control for different endpoints

### Portal Development

The Vue.js portal provides a comprehensive management interface:

- **Dashboard**: Overview of system status and usage metrics
- **Providers**: Add, edit, test, and manage AI providers
- **Strategies**: Create and manage multi-provider routing strategies
- **API Keys**: Generate and manage API keys with expiration
- **Playground**: Test API endpoints with different configurations
- **Settings**: System configuration and user management

**Portal Technology Stack**:
- Vue.js 3 with Composition API
- Ant Design Vue for UI components
- Vite for build tooling
- Axios for HTTP requests
- Vue Router for navigation
- Development proxy configured for backend integration

## Data Preservation Ground Rules

**CRITICAL**: Always preserve existing providers and strategies created by the user:

### Provider and Strategy Protection
- **NEVER delete or modify existing providers**: Any provider already in the database must be preserved
- **NEVER delete or modify existing strategies**: Any strategy already in the database must be preserved  
- **User-created data is sacred**: Only modify or delete data that you personally created during the current session
- **Backup before operations**: Always check if providers/strategies exist before making changes

### Safe Operations
- **Test data only**: You may only delete test data that you created during the current session
- **Create don't replace**: When adding new functionality, create new providers/strategies rather than replacing existing ones
- **Verify before acting**: Always query the database first to understand what exists
- **Use unique names**: When creating test providers/strategies, use unique, identifiable names

### Verification Steps
Before any database operations:
1. Check existing providers: `SELECT * FROM providers;`
2. Check existing strategies: `SELECT * FROM model_strategies;`
3. Identify user-created vs test data
4. Only proceed with modifications on test data

### Consequences
- Violating these rules may break the user's existing setup
- Always err on the side of caution
- When in doubt, ask the user for clarification
- Test operations in a safe environment first