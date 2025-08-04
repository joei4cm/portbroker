# PortBroker Test Suite

This directory contains the test suite for the PortBroker application.

## Test Structure

The tests are organized into the following files:

- `conftest.py` - Test configuration and fixtures
- `test_api.py` - Main API endpoint tests
- `test_providers.py` - Provider management tests
- `test_api_keys.py` - API key management tests
- `test_portal.py` - Portal authentication and UI tests
- `test_translation.py` - Translation service tests
- `test_provider_service.py` - Provider service tests
- `test_utils.py` - Utility function tests

## Running Tests

### Quick Test Run
```bash
# Run all tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=app --cov-report=html
```

### Using the Test Script
```bash
# Run all tests and checks
./run_tests.sh
```

### Specific Test Categories
```bash
# Run only unit tests
uv run pytest -m unit

# Run only integration tests
uv run pytest -m integration

# Run only API tests
uv run pytest -m api

# Run only portal tests
uv run pytest -m portal

# Run specific test file
uv run pytest tests/test_api.py

# Run specific test function
uv run pytest tests/test_api.py::TestAPIEndpoints::test_health_check
```

## Test Configuration

The test suite uses the following configuration:

- **Database**: In-memory SQLite for testing
- **Authentication**: Mock API keys for testing
- **Fixtures**: Available in `conftest.py`
- **Coverage**: Minimum 80% coverage required

## Key Fixtures

- `client`: FastAPI test client with database override
- `test_db`: Async database session
- `admin_api_key`: Mock admin API key
- `user_api_key`: Mock user API key

## Writing New Tests

### Example Test
```python
def test_my_feature(client, user_api_key):
    """Test my new feature"""
    response = client.get(
        "/my-endpoint",
        headers={"Authorization": f"Bearer {user_api_key}"}
    )
    assert response.status_code == 200
    assert "expected_data" in response.json()
```

### Async Tests
```python
@pytest.mark.asyncio
async def test_my_async_feature(test_db):
    """Test my async feature"""
    # Use test_db for database operations
    result = await my_async_function(test_db)
    assert result is not None
```

## Test Categories

### Unit Tests
- Individual component testing
- Mock external dependencies
- Fast execution

### Integration Tests
- Multiple component testing
- Real database interactions
- Slower execution

### API Tests
- HTTP endpoint testing
- Authentication testing
- Request/response validation

### Portal Tests
- Web interface testing
- Authentication flows
- Permission testing

## Coverage

The test suite aims for:
- **Overall Coverage**: 80% minimum
- **Critical Paths**: 95% coverage
- **Error Handling**: Complete coverage

## Continuous Integration

The test suite is designed to run in CI/CD environments:
- No external dependencies required
- Fast execution for quick feedback
- Comprehensive coverage reporting