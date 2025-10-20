# TODO: OpenAPI "Pro Max" Completion

## Status: 70% Complete ✅

**What's done:**
- ✅ `openapi/openapi_v1.json` - Generated OpenAPI v3 spec (540 lines)
- ✅ `src/api/models.py` - Pydantic models with type safety (48 lines)
- ✅ FastAPI endpoints using typed models (`/api/v1/analyze`, `/tools`, `/health`)

**What's missing for "Pro Max" level:**
- ❌ Schema diff test (prevents accidental breaking changes)
- ❌ API integration test (validates OpenAPI matches reality)
- ❌ CI automation (Makefile commands + pipeline)
- ❌ Frontend type generation workflow
- ⚠️ Swagger UI documentation page (nice-to-have)

---

## Missing Component #1: Schema Diff Test (Priority: HIGH)

**Purpose:** Fail CI build if API schema changes without explicit approval

**Estimated time:** 30 minutes

**Implementation:**

```python
# tests/test_openapi_snapshot.py
import json
from pathlib import Path
import pytest
from web_ui import app

SNAPSHOT_PATH = Path("openapi/openapi_v1.json")

def test_openapi_schema_matches_snapshot():
    """
    Prevent accidental API changes.
    If this test fails, you changed the API contract.

    To update snapshot after intentional change:
        make update-openapi-snapshot
    """
    current_schema = app.openapi()

    if not SNAPSHOT_PATH.exists():
        pytest.skip("No OpenAPI snapshot exists yet")

    with open(SNAPSHOT_PATH) as f:
        snapshot_schema = json.load(f)

    # Compare paths (endpoints)
    assert current_schema["paths"] == snapshot_schema["paths"], \
        "API paths changed! Review changes and run: make update-openapi-snapshot"

    # Compare components (schemas/models)
    assert current_schema["components"] == snapshot_schema["components"], \
        "API schemas changed! Review changes and run: make update-openapi-snapshot"


def test_openapi_has_all_v1_endpoints():
    """Ensure all v1 endpoints are documented"""
    schema = app.openapi()
    paths = schema["paths"]

    required_endpoints = [
        "/api/v1/analyze",
        "/api/v1/tools",
        "/api/v1/health"
    ]

    for endpoint in required_endpoints:
        assert endpoint in paths, f"Missing required endpoint: {endpoint}"


def test_openapi_version_info():
    """Ensure OpenAPI metadata is present"""
    schema = app.openapi()

    assert "info" in schema
    assert "title" in schema["info"]
    assert "version" in schema["info"]
    assert schema["openapi"].startswith("3."), "Should use OpenAPI 3.x"
```

**Value:**
- Catches breaking changes before they reach frontend
- Forces intentional API evolution (no accidents)
- Shows change history in git log

---

## Missing Component #2: API Integration Tests (Priority: HIGH)

**Purpose:** Validate that actual API responses match OpenAPI schema

**Estimated time:** 30 minutes

**Implementation:**

```python
# tests/test_api_v1.py
from fastapi.testclient import TestClient
import pytest
from web_ui import app
from src.api.models import AnalyzeResponse, ToolListResponse, HealthResponse

client = TestClient(app)


class TestV1AnalyzeEndpoint:
    """Test /api/v1/analyze endpoint"""

    def test_analyze_returns_valid_schema(self):
        """Validate response matches AnalyzeResponse model"""
        response = client.post(
            "/api/v1/analyze",
            data={
                "query": "find healthy breakfast",
                "use_llm": "false"  # Skip LLM for faster test
            }
        )

        assert response.status_code == 200

        # Pydantic validation - will raise if schema mismatch
        data = AnalyzeResponse(**response.json())

        # Verify required fields
        assert data.query == "find healthy breakfast"
        assert data.schema_version is not None
        assert data.pagination is not None
        assert data.intent is not None
        assert data.mcp_result is not None

    def test_analyze_with_llm(self):
        """Test with LLM enabled"""
        response = client.post(
            "/api/v1/analyze",
            data={
                "query": "healthy breakfast",
                "use_llm": "true"
            }
        )

        assert response.status_code == 200
        data = AnalyzeResponse(**response.json())
        assert data.llm_analysis is not None  # Should have analysis

    def test_analyze_pagination_fields(self):
        """Validate pagination structure"""
        response = client.post(
            "/api/v1/analyze",
            data={"query": "test", "use_llm": "false"}
        )

        data = response.json()
        assert "pagination" in data
        assert "limit" in data["pagination"]
        assert "offset" in data["pagination"]


class TestV1ToolsEndpoint:
    """Test /api/v1/tools endpoint"""

    def test_tools_returns_valid_schema(self):
        """Validate response matches ToolListResponse model"""
        response = client.get("/api/v1/tools")

        assert response.status_code == 200
        data = ToolListResponse(**response.json())

        # Should have at least one tool
        assert len(data.tools) > 0

        # Verify tool structure
        first_tool = data.tools[0]
        assert first_tool.name is not None
        assert first_tool.hints is not None


class TestV1HealthEndpoint:
    """Test /api/v1/health endpoint"""

    def test_health_returns_valid_schema(self):
        """Validate response matches HealthResponse model"""
        response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = HealthResponse(**response.json())

        assert data.status == "online"
        assert isinstance(data.config_loaded, bool)
        assert data.timestamp is not None
```

**Value:**
- Ensures OpenAPI spec matches real API behavior
- Catches runtime schema violations
- Regression testing for API stability

---

## Missing Component #3: CI Automation (Priority: MEDIUM)

**Purpose:** Automate OpenAPI workflow with make commands

**Estimated time:** 30 minutes

**Implementation:**

```makefile
# Makefile
.PHONY: update-openapi-snapshot
update-openapi-snapshot:
	@echo "📝 Regenerating OpenAPI snapshot..."
	@python3 -c "from web_ui import app; import json; \
		json.dump(app.openapi(), open('openapi/openapi_v1.json', 'w'), indent=2)"
	@echo "✅ OpenAPI snapshot updated: openapi/openapi_v1.json"
	@echo "💡 Review changes with: git diff openapi/openapi_v1.json"

.PHONY: check-openapi-diff
check-openapi-diff:
	@echo "🔍 Checking for breaking API changes..."
	@npx swagger-diff openapi/openapi_v1.json \
		<(python3 -c "from web_ui import app; import json; json.dump(app.openapi(), __import__('sys').stdout, indent=2)")

.PHONY: validate-openapi
validate-openapi:
	@echo "✓ Validating OpenAPI spec..."
	@npx @apidevtools/swagger-cli validate openapi/openapi_v1.json
	@echo "✅ OpenAPI spec is valid"

.PHONY: generate-frontend-types
generate-frontend-types:
	@echo "🔧 Generating TypeScript types from OpenAPI..."
	@npx openapi-typescript openapi/openapi_v1.json -o frontend/types/api.ts
	@echo "✅ Types generated: frontend/types/api.ts"

.PHONY: openapi-docs
openapi-docs:
	@echo "📚 OpenAPI documentation available at:"
	@echo "   Swagger UI: http://localhost:8000/docs"
	@echo "   ReDoc:      http://localhost:8000/redoc"
	@echo "   JSON:       http://localhost:8000/openapi.json"
```

**CI Pipeline (.github/workflows/openapi-check.yml):**

```yaml
name: OpenAPI Contract Check

on: [pull_request]

jobs:
  openapi-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Check OpenAPI schema unchanged
        run: |
          pytest tests/test_openapi_snapshot.py -v

      - name: Check for breaking changes
        if: failure()
        run: |
          echo "⚠️ OpenAPI schema changed!"
          echo "If this is intentional, run: make update-openapi-snapshot"
          exit 1
```

**Value:**
- One command to update snapshot
- Automated checks in CI
- Clear workflow for API changes

---

## Missing Component #4: Frontend Type Generation (Priority: HIGH)

**Purpose:** Auto-generate TypeScript types from OpenAPI spec

**Estimated time:** 15 minutes

**Implementation:**

```bash
# Install tool globally or as dev dependency
npm install -g openapi-typescript

# Generate types
npx openapi-typescript openapi/openapi_v1.json -o frontend/src/types/api.ts
```

**Usage in Frontend:**

```typescript
// frontend/src/api/client.ts
import type { paths } from './types/api'

type AnalyzeRequest = paths['/api/v1/analyze']['post']['requestBody']['content']['application/x-www-form-urlencoded']
type AnalyzeResponse = paths['/api/v1/analyze']['post']['responses']['200']['content']['application/json']

export async function analyzeQuery(query: string, useLlm: boolean = true): Promise<AnalyzeResponse> {
  const response = await fetch('/api/v1/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ query, use_llm: useLlm.toString() })
  })

  if (!response.ok) throw new Error('Analysis failed')

  return response.json() as Promise<AnalyzeResponse>
}

// TypeScript knows the exact shape:
const result = await analyzeQuery('healthy breakfast')
console.log(result.query)           // ✅ Type: string
console.log(result.pagination)      // ✅ Type: { limit: number, offset: number, ... }
console.log(result.llm_analysis)    // ✅ Type: string | undefined
```

**Value:**
- Zero API documentation needed
- Autocomplete in IDE
- Compile-time safety
- Refactoring confidence

---

## Missing Component #5: Swagger UI Docs (Priority: LOW)

**Purpose:** Interactive API documentation for judges/developers

**Estimated time:** 5 minutes

**Implementation:**

```python
# web_ui.py - Add Swagger UI route
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title=app.title + " - Swagger UI"
    )

@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    return get_redoc_html(
        openapi_url="/openapi.json",
        title=app.title + " - ReDoc"
    )

@app.get("/openapi.json", include_in_schema=False)
async def get_openapi_endpoint():
    return app.openapi()
```

**Access:**
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Raw JSON: `http://localhost:8000/openapi.json`

**Value:**
- Judges can explore API interactively
- Try endpoints from browser
- No Postman needed

---

## Completion Checklist

**Phase 1: Core Protection (30 mins - DO BEFORE HACKATHON)**
- [ ] Add `tests/test_openapi_snapshot.py`
- [ ] Add `tests/test_api_v1.py`
- [ ] Run tests: `pytest tests/test_openapi_snapshot.py tests/test_api_v1.py -v`

**Phase 2: Developer Experience (1 hour - DO BEFORE HACKATHON)**
- [ ] Create `Makefile` with OpenAPI commands
- [ ] Generate frontend types: `make generate-frontend-types`
- [ ] Add Swagger UI endpoints to `web_ui.py`
- [ ] Document OpenAPI workflow in README

**Phase 3: CI Integration (30 mins - DO POST-HACKATHON)**
- [ ] Add `.github/workflows/openapi-check.yml`
- [ ] Configure pre-commit hook to check schema diff
- [ ] Add badge to README showing API stability

---

## Benefits Summary

**Current (70% complete):**
- ✅ Frontend can generate types manually
- ✅ Pydantic prevents returning garbage
- ⚠️ No protection against breaking changes
- ⚠️ Manual coordination required

**With "Pro Max" (100% complete):**
- ✅ CI fails on accidental breaking changes
- ✅ Frontend types auto-regenerate
- ✅ One command to update entire contract
- ✅ Zero-friction parallel development
- ✅ Professional impression on judges
- ✅ Scales to complex agentic workflows

---

## Time Investment vs Value

| Component | Time | Value | Priority |
|-----------|------|-------|----------|
| Schema diff test | 30m | 🔥🔥🔥 Prevents bugs | HIGH |
| API integration tests | 30m | 🔥🔥🔥 Validates contract | HIGH |
| Frontend type gen | 15m | 🔥🔥🔥 Developer velocity | HIGH |
| Makefile automation | 30m | 🔥🔥 Convenience | MEDIUM |
| Swagger UI | 5m | 🔥 Demo polish | LOW |
| CI pipeline | 30m | 🔥🔥 Future-proofing | MEDIUM |

**Total time to 100%:** ~2.5 hours
**ROI:** Prevents 10+ hours of debugging during rapid iteration

---

## When to Complete This

**Recommended timing:**

1. **Before Frontend Dev Starts (Day 1):**
   - ✅ Done: OpenAPI spec exists
   - ✅ Done: Pydantic models exist
   - 🔲 Add: Frontend type generation (15 mins)

2. **Before Rapid Feature Iteration (Day 3-4):**
   - 🔲 Add: Schema diff test (30 mins)
   - 🔲 Add: API integration tests (30 mins)
   - 🔲 Add: Makefile commands (30 mins)

3. **Before Hackathon Demo (Day 6-7):**
   - 🔲 Add: Swagger UI (5 mins) - judges love interactive docs

4. **Post-Hackathon (Week 2+):**
   - 🔲 Add: CI pipeline (30 mins)

---

## Contact / Questions

For questions about OpenAPI "Pro Max" completion, refer to:
- Claude's analysis dated 2025-10-20
- This TODO was generated based on 70% completion assessment
- Missing tests noted in commit `e1a832d` (claimed but not delivered)

---

**Last updated:** 2025-10-20
**Status:** 70% complete, core value delivered, polish remaining
**Next action:** Add tests before rapid feature iteration begins
