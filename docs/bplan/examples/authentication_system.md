# Example: Building an Authentication System with /bplan

This example walks through using /bplan to build a JWT-based authentication system from scratch.

## Initial Request

```
/bplan Build a JWT-based authentication system with user registration, login, password hashing with bcrypt, and session management
```

## Stage 1: Interactive Intake

The system asks clarifying questions:

**Q: Is there any existing documentation or planning for this project?**
A: No, starting from scratch

**Q: What are the key requirements that must be included?**
A:
- User registration with email/password
- Secure password hashing (bcrypt)
- JWT token generation and validation
- Refresh token support
- Session management
- Password reset capability

**Q: Are there any constraints (technical, time, resource)?**
A: Must use existing FastAPI framework, integrate with existing PostgreSQL database

**Q: How will we know the project is complete (definition of done)?**
A: All features working, comprehensive tests passing, can register, login, and maintain sessions

**Q: Which existing files or modules should we review for context?**
A:
- `@amplifier/api/main.py` - Existing FastAPI app
- `@amplifier/db/models.py` - Database models
- `@amplifier/config.py` - Configuration patterns

**Project Brief Generated:**

```
Build JWT-based authentication system for existing FastAPI application.

Requirements:
- User registration with email/password validation
- Bcrypt password hashing
- JWT token generation (access + refresh tokens)
- Session management with token refresh
- Password reset flow with email verification

Constraints:
- Integrate with existing FastAPI app at amplifier/api/main.py
- Use existing PostgreSQL database via amplifier/db/
- Follow existing configuration patterns

Success Criteria:
- All authentication flows tested and working
- 90%+ test coverage
- Integration with existing API
- Documentation for usage
```

**User approves brief**

## Stage 2: Discovery & Planning

project-planner agent analyzes the codebase and creates a phased plan:

### Phase Breakdown

**Phase 1: User Model & Database (amplifier-14)**
- Dependencies: None
- Deliverables:
  - User database model with email, password_hash fields
  - Database migration script
  - Basic CRUD operations
- Test Strategy:
  - Unit tests for model validation
  - Integration tests with test database
  - Migration tests (up/down)
- Acceptance Criteria:
  - User model created and migrated
  - Can create/read users from database
  - Email uniqueness enforced
  - All tests passing

**Phase 2: Password Hashing (amplifier-15)**
- Dependencies: Phase 1 (User model)
- Deliverables:
  - Password hashing utilities using bcrypt
  - Password validation functions
  - Integration with User model
- Test Strategy:
  - Antagonistic tests (verify salt usage)
  - Performance tests (hash timing)
  - Edge case tests (empty passwords, long passwords)
- Acceptance Criteria:
  - Passwords hashed with bcrypt
  - Each hash unique (salted)
  - Validation works correctly
  - Timing attack resistant

**Phase 3: JWT Token Generation (amplifier-16)**
- Dependencies: Phase 1, Phase 2
- Deliverables:
  - JWT token generation (access + refresh)
  - Token validation and decoding
  - Token expiration handling
- Test Strategy:
  - Token structure validation
  - Expiration tests
  - Invalid token rejection
  - Signing verification
- Acceptance Criteria:
  - Access tokens (15 min expiry)
  - Refresh tokens (7 day expiry)
  - Proper signing and validation
  - Expiration enforced

**Phase 4: Registration & Login Endpoints (amplifier-17)**
- Dependencies: Phase 1, 2, 3
- Deliverables:
  - POST /auth/register endpoint
  - POST /auth/login endpoint
  - Request/response validation
  - Error handling
- Test Strategy:
  - Integration tests with test API client
  - Validation error tests
  - Duplicate registration rejection
  - Invalid login handling
- Acceptance Criteria:
  - Registration creates user + returns tokens
  - Login validates credentials + returns tokens
  - Proper error responses
  - Request validation working

**Phase 5: Session Management (amplifier-18)**
- Dependencies: Phase 3, 4
- Deliverables:
  - POST /auth/refresh endpoint
  - Token storage/retrieval
  - Session invalidation
- Test Strategy:
  - Refresh token flow tests
  - Expired token handling
  - Invalid refresh token rejection
  - Session cleanup tests
- Acceptance Criteria:
  - Refresh endpoint works
  - Old tokens properly invalidated
  - Session state tracked
  - Cleanup on logout

**Phase 6: Password Reset (amplifier-19)**
- Dependencies: Phase 1, 2, 4
- Deliverables:
  - POST /auth/password-reset/request endpoint
  - POST /auth/password-reset/confirm endpoint
  - Reset token generation
  - Email integration (mocked for testing)
- Test Strategy:
  - Reset flow integration tests
  - Token expiration tests
  - Invalid token rejection
  - Email mock validation
- Acceptance Criteria:
  - Reset request generates token
  - Confirmation updates password
  - Tokens expire appropriately
  - Secure token generation

### Beads Structure Created

```
amplifier-13 (EPIC): JWT Authentication System
├── amplifier-14 (TASK): Phase 1 - User Model & Database
├── amplifier-15 (TASK): Phase 2 - Password Hashing
├── amplifier-16 (TASK): Phase 3 - JWT Token Generation
├── amplifier-17 (TASK): Phase 4 - Registration & Login
├── amplifier-18 (TASK): Phase 5 - Session Management
└── amplifier-19 (TASK): Phase 6 - Password Reset
```

**User approves plan**

## Stage 3: Phase Execution

### Phase 1: User Model & Database

**phase-executor spawned**

#### RED Phase: Write Tests First

```python
# tests/test_user_model.py
import pytest
from amplifier.auth.models import User
from amplifier.db import get_test_db

def test_create_user():
    """Test creating a user with email and password."""
    db = get_test_db()
    user = User(email="test@example.com", password_hash="hashed")
    db.add(user)
    db.commit()

    assert user.id is not None
    assert user.email == "test@example.com"

def test_email_uniqueness():
    """Test that duplicate emails are rejected."""
    db = get_test_db()
    user1 = User(email="test@example.com", password_hash="hash1")
    user2 = User(email="test@example.com", password_hash="hash2")

    db.add(user1)
    db.commit()

    db.add(user2)
    with pytest.raises(IntegrityError):
        db.commit()

def test_user_crud_operations():
    """Test full CRUD cycle for users."""
    db = get_test_db()

    # Create
    user = User(email="crud@example.com", password_hash="hash")
    db.add(user)
    db.commit()
    user_id = user.id

    # Read
    retrieved = db.query(User).filter_by(id=user_id).first()
    assert retrieved.email == "crud@example.com"

    # Update
    retrieved.email = "updated@example.com"
    db.commit()
    assert db.query(User).get(user_id).email == "updated@example.com"

    # Delete
    db.delete(retrieved)
    db.commit()
    assert db.query(User).get(user_id) is None
```

**Run tests - all fail (expected)**

#### GREEN Phase: Minimal Implementation

```python
# amplifier/auth/models.py
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from amplifier.db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

# amplifier/auth/crud.py
from sqlalchemy.orm import Session
from .models import User

def create_user(db: Session, email: str, password_hash: str) -> User:
    """Create a new user."""
    user = User(email=email, password_hash=password_hash)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def get_user_by_email(db: Session, email: str) -> User | None:
    """Get user by email."""
    return db.query(User).filter_by(email=email).first()

def get_user_by_id(db: Session, user_id: int) -> User | None:
    """Get user by ID."""
    return db.query(User).get(user_id)
```

**Run tests - all pass**

#### REFACTOR Phase

Code is minimal and clean - no refactoring needed.

**Beads updated: amplifier-14 status → IN_PROGRESS → CLOSED**

**phase-reviewer validates Phase 1**

- ✅ All tests pass
- ✅ No test cheating (real database used)
- ✅ Acceptance criteria met
- ✅ Code quality good

**Phase 1: APPROVED**

### Phases 2-6 Execute Similarly

Each phase follows:
1. Spawn phase-executor
2. Write comprehensive tests first
3. Implement minimal code
4. Validate with phase-reviewer
5. Update beads

### Phase 4 Example: Registration Endpoint

```python
# tests/test_auth_api.py
from fastapi.testclient import TestClient

def test_register_success(client: TestClient):
    """Test successful user registration."""
    response = client.post("/auth/register", json={
        "email": "new@example.com",
        "password": "SecurePass123!"
    })

    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

def test_register_duplicate_email(client: TestClient):
    """Test registration with duplicate email fails."""
    # Register first user
    client.post("/auth/register", json={
        "email": "duplicate@example.com",
        "password": "Pass123!"
    })

    # Try to register again with same email
    response = client.post("/auth/register", json={
        "email": "duplicate@example.com",
        "password": "DifferentPass123!"
    })

    assert response.status_code == 400
    assert "already registered" in response.json()["detail"].lower()

def test_register_weak_password(client: TestClient):
    """Test registration with weak password fails."""
    response = client.post("/auth/register", json={
        "email": "weak@example.com",
        "password": "123"
    })

    assert response.status_code == 422
```

## Stage 4: Inter-Phase Validation

After all phases complete, run full integration tests:

```bash
pytest tests/test_auth_integration.py -v
```

All tests pass - no regressions detected.

## Stage 5: Final Reconciliation

project-planner reviews completed work:

- ✅ All 6 phases completed
- ✅ All acceptance criteria met
- ✅ Integration tests passing
- ✅ Philosophy aligned (simple, direct code)
- ✅ Nothing missed from original brief

**Epic amplifier-13 CLOSED**

## Result

Complete JWT authentication system with:
- 6 phases executed
- 85 tests written (all passing)
- ~800 lines of implementation code
- Full documentation
- Ready for production use

Total time: ~4 hours (with /bplan managing workflow)

## Key Takeaways

1. **Test-first discipline enforced** - No shortcuts possible
2. **Clear phase boundaries** - Each phase self-contained
3. **Beads tracking essential** - Can resume after interruptions
4. **Fresh agent sessions** - No context pollution between phases
5. **Validation at every step** - Quality baked in, not added later

## Next Steps

See `docs/bplan/examples/` for more examples:
- `api_endpoints.md` - Building REST APIs with /bplan
- `data_pipeline.md` - Creating ETL pipelines with phases
