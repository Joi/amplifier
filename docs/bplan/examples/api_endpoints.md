# Example: Building REST API Endpoints with /bplan

This example demonstrates using /bplan to create a set of REST API endpoints for a blog system.

## Initial Request

```
/bplan Create REST API endpoints for a blog: create post, list posts, get post by ID, update post, delete post
```

## Stage 1: Interactive Intake

**Q: Is there any existing documentation or planning for this project?**
A: No, new feature

**Q: What are the key requirements that must be included?**
A:
- CRUD operations for blog posts
- Each post has: title, content, author_id, created_at, updated_at
- List endpoint with pagination
- Validation for required fields

**Q: Are there any constraints?**
A: Use existing FastAPI app, integrate with PostgreSQL

**Q: Definition of done?**
A: All 5 endpoints working with tests, proper error handling

**Q: Context files?**
A: `@amplifier/api/main.py`, `@amplifier/db/models.py`

**Brief approved by user**

## Stage 2: Planning

project-planner creates 3-phase plan:

**Phase 1 (amplifier-20)**: Post Model & Database
- Create Post model
- Database migration
- CRUD utilities

**Phase 2 (amplifier-21)**: Read Endpoints
- GET /posts (list with pagination)
- GET /posts/{id} (single post)

**Phase 3 (amplifier-22)**: Write Endpoints
- POST /posts (create)
- PUT /posts/{id} (update)
- DELETE /posts/{id} (delete)

**Plan approved by user**

## Stage 3: Execution

### Phase 1: Post Model

**Tests First:**

```python
# tests/test_post_model.py
def test_create_post():
    """Test creating a blog post."""
    db = get_test_db()
    post = Post(
        title="Test Post",
        content="This is test content",
        author_id=1
    )
    db.add(post)
    db.commit()

    assert post.id is not None
    assert post.title == "Test Post"
    assert post.created_at is not None

def test_post_requires_title():
    """Test that title is required."""
    db = get_test_db()
    post = Post(content="Content", author_id=1)  # No title

    db.add(post)
    with pytest.raises(IntegrityError):
        db.commit()

def test_post_crud_operations():
    """Test full CRUD cycle."""
    db = get_test_db()

    # Create
    post = Post(title="CRUD Test", content="Content", author_id=1)
    db.add(post)
    db.commit()

    # Read
    retrieved = db.query(Post).get(post.id)
    assert retrieved.title == "CRUD Test"

    # Update
    retrieved.title = "Updated Title"
    db.commit()
    assert db.query(Post).get(post.id).title == "Updated Title"

    # Delete
    db.delete(retrieved)
    db.commit()
    assert db.query(Post).get(post.id) is None
```

**Implementation:**

```python
# amplifier/blog/models.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from amplifier.db import Base

class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

# amplifier/blog/crud.py
from sqlalchemy.orm import Session
from .models import Post

def create_post(db: Session, title: str, content: str, author_id: int) -> Post:
    """Create a new blog post."""
    post = Post(title=title, content=content, author_id=author_id)
    db.add(post)
    db.commit()
    db.refresh(post)
    return post

def get_post(db: Session, post_id: int) -> Post | None:
    """Get post by ID."""
    return db.query(Post).get(post_id)

def list_posts(db: Session, skip: int = 0, limit: int = 10) -> list[Post]:
    """List posts with pagination."""
    return db.query(Post).offset(skip).limit(limit).all()

def update_post(db: Session, post_id: int, title: str, content: str) -> Post | None:
    """Update a post."""
    post = db.query(Post).get(post_id)
    if post:
        post.title = title
        post.content = content
        db.commit()
        db.refresh(post)
    return post

def delete_post(db: Session, post_id: int) -> bool:
    """Delete a post."""
    post = db.query(Post).get(post_id)
    if post:
        db.delete(post)
        db.commit()
        return True
    return False
```

**Phase 1 APPROVED** (all tests pass, no cheating detected)

### Phase 2: Read Endpoints

**Tests First:**

```python
# tests/test_blog_api.py
from fastapi.testclient import TestClient

def test_list_posts_empty(client: TestClient):
    """Test listing posts when none exist."""
    response = client.get("/posts")
    assert response.status_code == 200
    assert response.json() == {"posts": [], "total": 0}

def test_list_posts_with_data(client: TestClient, test_posts):
    """Test listing posts with existing data."""
    response = client.get("/posts")
    assert response.status_code == 200
    data = response.json()
    assert len(data["posts"]) == len(test_posts)
    assert data["total"] == len(test_posts)

def test_list_posts_pagination(client: TestClient, test_posts):
    """Test pagination works correctly."""
    response = client.get("/posts?skip=1&limit=2")
    assert response.status_code == 200
    data = response.json()
    assert len(data["posts"]) == 2
    assert data["posts"][0]["id"] == test_posts[1].id

def test_get_post_success(client: TestClient, test_posts):
    """Test getting a specific post."""
    post_id = test_posts[0].id
    response = client.get(f"/posts/{post_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == post_id
    assert data["title"] == test_posts[0].title

def test_get_post_not_found(client: TestClient):
    """Test getting nonexistent post returns 404."""
    response = client.get("/posts/99999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
```

**Implementation:**

```python
# amplifier/blog/api.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from amplifier.db import get_db
from . import crud

router = APIRouter(prefix="/posts", tags=["blog"])

class PostResponse(BaseModel):
    id: int
    title: str
    content: str
    author_id: int
    created_at: str
    updated_at: str | None

    class Config:
        from_attributes = True

class PostListResponse(BaseModel):
    posts: list[PostResponse]
    total: int

@router.get("/", response_model=PostListResponse)
async def list_posts(
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """List all blog posts with pagination."""
    posts = crud.list_posts(db, skip=skip, limit=limit)
    total = db.query(crud.Post).count()
    return PostListResponse(posts=posts, total=total)

@router.get("/{post_id}", response_model=PostResponse)
async def get_post(post_id: int, db: Session = Depends(get_db)):
    """Get a specific blog post by ID."""
    post = crud.get_post(db, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post
```

**Phase 2 APPROVED**

### Phase 3: Write Endpoints

**Tests First:**

```python
def test_create_post_success(client: TestClient, auth_headers):
    """Test creating a new post."""
    response = client.post(
        "/posts",
        json={"title": "New Post", "content": "Content here"},
        headers=auth_headers
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "New Post"
    assert data["id"] is not None

def test_create_post_missing_title(client: TestClient, auth_headers):
    """Test creating post without title fails."""
    response = client.post(
        "/posts",
        json={"content": "Content without title"},
        headers=auth_headers
    )
    assert response.status_code == 422

def test_update_post_success(client: TestClient, test_posts, auth_headers):
    """Test updating an existing post."""
    post_id = test_posts[0].id
    response = client.put(
        f"/posts/{post_id}",
        json={"title": "Updated", "content": "Updated content"},
        headers=auth_headers
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Updated"

def test_update_nonexistent_post(client: TestClient, auth_headers):
    """Test updating nonexistent post returns 404."""
    response = client.put(
        "/posts/99999",
        json={"title": "Updated", "content": "Content"},
        headers=auth_headers
    )
    assert response.status_code == 404

def test_delete_post_success(client: TestClient, test_posts, auth_headers):
    """Test deleting a post."""
    post_id = test_posts[0].id
    response = client.delete(f"/posts/{post_id}", headers=auth_headers)

    assert response.status_code == 204
    # Verify post is gone
    get_response = client.get(f"/posts/{post_id}")
    assert get_response.status_code == 404

def test_delete_nonexistent_post(client: TestClient, auth_headers):
    """Test deleting nonexistent post returns 404."""
    response = client.delete("/posts/99999", headers=auth_headers)
    assert response.status_code == 404
```

**Implementation:**

```python
# amplifier/blog/api.py (additions)

class PostCreate(BaseModel):
    title: str
    content: str

class PostUpdate(BaseModel):
    title: str
    content: str

@router.post("/", response_model=PostResponse, status_code=201)
async def create_post(
    post_data: PostCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new blog post."""
    post = crud.create_post(
        db,
        title=post_data.title,
        content=post_data.content,
        author_id=current_user.id
    )
    return post

@router.put("/{post_id}", response_model=PostResponse)
async def update_post(
    post_id: int,
    post_data: PostUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update an existing blog post."""
    post = crud.update_post(
        db,
        post_id=post_id,
        title=post_data.title,
        content=post_data.content
    )
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return post

@router.delete("/{post_id}", status_code=204)
async def delete_post(
    post_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a blog post."""
    deleted = crud.delete_post(db, post_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Post not found")
```

**Phase 3 APPROVED**

## Stage 4: Integration Tests

Full API integration tests run - all pass.

## Stage 5: Reconciliation

project-planner validates:
- ✅ All 5 endpoints implemented
- ✅ Validation working
- ✅ Pagination working
- ✅ Error handling correct
- ✅ 42 tests passing

**Epic CLOSED**

## Result

Complete blog API with:
- 3 phases
- 5 REST endpoints
- 42 tests (all passing)
- ~400 lines of code
- Full error handling

Time: ~2 hours with /bplan

## Key Lessons

1. **Breaking into phases** - Read operations separate from write operations
2. **Test pagination early** - Caught off-by-one errors in tests
3. **Error cases matter** - Half the tests are error handling
4. **Real database tests** - No mocks, caught real integration issues

## Try It Yourself

Use this example as a template for your own API endpoints:

1. Start with `/bplan Create REST API for [your resource]`
2. Answer intake questions carefully
3. Review the phase plan
4. Let the system execute with test-first discipline
5. Review final results

The /bplan system handles the workflow, you focus on requirements and validation.
