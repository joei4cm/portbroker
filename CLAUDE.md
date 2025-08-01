# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PortBroker is an API service built with FastAPI that translates between Anthropic and OpenAI API formats while managing multiple AI providers. It acts as a universal API gateway that allows clients to use either API format seamlessly, with intelligent model mapping and provider failover.

## Development Commands

### Environment Setup
```bash
# Install dependencies with uv
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
```

### Python Execution
```bash
# Run any Python script
uv run python <script_name>.py

# Run the application directly
uv run python run.py

# Run development server with auto-reload
uv run uvicorn app.main:app --reload
```

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
- Database type and connection strings
- Server host/port
- Default provider settings
- Security configuration

The application uses `pydantic-settings` for configuration management with `.env` file support.