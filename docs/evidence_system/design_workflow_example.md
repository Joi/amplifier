# Design Review Workflow Example

This document walks through the design review workflow with context-free validation.

## Overview

The design review workflow validates design documents through independent review:

1. **Requirements Provided** - User specifies what's needed
2. **Design Created** - Designer produces design document
3. **Independent Review** - Context-free validator reviews design
4. **Evidence Stored** - Review result saved as evidence

## Example: API Design Review

### Step 1: Requirements

**User Requirements**:
```
Design a REST API for user authentication with the following features:
- User registration with email validation
- Login with JWT token generation
- Password reset functionality
- Rate limiting for security
- Input validation for all endpoints
```

### Step 2: Design Document Created

**Design Output** (`auth_api_design.md`):
```markdown
# Authentication API Design

## Endpoints

### POST /api/auth/register
- Input: { email, password, confirmPassword }
- Validation: Email format, password strength (min 8 chars)
- Output: { userId, message }
- Rate limit: 5 requests/hour per IP

### POST /api/auth/login
- Input: { email, password }
- Output: { token (JWT), expiresIn, refreshToken }
- Rate limit: 10 requests/minute per IP

### POST /api/auth/forgot-password
- Input: { email }
- Output: { message, resetTokenSent }
- Rate limit: 3 requests/hour per email

### POST /api/auth/reset-password
- Input: { resetToken, newPassword }
- Validation: Token validity, password strength
- Output: { success, message }

## Security Measures
- All passwords hashed with bcrypt
- JWT tokens expire after 1 hour
- Refresh tokens expire after 7 days
- Rate limiting via middleware
- Input sanitization on all endpoints
```

### Step 3: Independent Review

The reviewer has **zero context** from the design creation process.

**Review Process**:
```python
from amplifier.bplan.design_review import DesignReviewer

reviewer = DesignReviewer()

# Review with fresh context
result = reviewer.review(
    requirements=user_requirements,
    design=design_output,
    # No conversation history
    # No context from designer
)
```

**Review Result**:
```json
{
  "approved": true,
  "coverage": 0.95,
  "issues": [],
  "strengths": [
    "All required features covered",
    "Rate limiting included for security",
    "Input validation specified",
    "JWT token expiration defined",
    "Password hashing with bcrypt"
  ],
  "suggestions": [
    "Consider adding 2FA option",
    "Document refresh token rotation strategy"
  ],
  "requirements_met": [
    "User registration with email validation ✓",
    "Login with JWT token generation ✓",
    "Password reset functionality ✓",
    "Rate limiting for security ✓",
    "Input validation for all endpoints ✓"
  ]
}
```

### Step 4: Evidence Stored

```json
{
  "id": "evidence_design_001",
  "type": "design_review",
  "timestamp": "2025-10-15T12:34:56Z",
  "validator_id": "independent_reviewer",
  "content": {
    "requirements": "Design REST API for user authentication...",
    "design": "# Authentication API Design...",
    "approved": true,
    "coverage": 0.95,
    "issues": [],
    "review_summary": "All requirements met with strong security measures"
  }
}
```

## Using the Workflow

### Python API

```python
from amplifier.bplan.agent_interface import AgentAPI
from amplifier.bplan.design_review import DesignReviewer

api = AgentAPI()
reviewer = DesignReviewer()

# Perform review
result = reviewer.review(
    requirements="Design REST API for user authentication...",
    design=design_document
)

if result.approved:
    # Store as evidence
    evidence = api.evidence_store.add_evidence(
        type="design_review",
        content={
            "text": result.summary,
            "metadata": {
                "coverage": result.coverage,
                "requirements_met": result.requirements_met
            }
        },
        validator_id="design_reviewer"
    )

    print(f"✅ Design approved! Evidence: {evidence.id}")
else:
    print(f"❌ Design needs revision:")
    for issue in result.issues:
        print(f"  - {issue}")
```

## Context-Free Validation

### What Makes It Context-Free?

1. **Fresh LLM Context**
   - No conversation history
   - No prior knowledge of design process
   - Clean slate for each review

2. **Only Requirements + Design**
   ```python
   # Reviewer sees ONLY these inputs
   review_input = {
       "requirements": user_requirements,
       "design": design_output
   }
   # No designer notes, no drafts, no discussions
   ```

3. **Automated Comparison**
   ```python
   # Code-based matching
   requirements_list = extract_requirements(user_requirements)
   design_features = extract_features(design)

   coverage = calculate_coverage(requirements_list, design_features)
   ```

## Example: Database Schema Review

### Requirements

```
Design a database schema for an e-commerce platform:
- Products with categories and inventory
- User accounts with order history
- Shopping cart functionality
- Payment transaction records
- Product reviews and ratings
```

### Design

```sql
-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Products table
CREATE TABLE products (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL,
    inventory_count INT NOT NULL DEFAULT 0,
    category_id UUID REFERENCES categories(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Categories table
CREATE TABLE categories (
    id UUID PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    parent_id UUID REFERENCES categories(id)
);

-- Orders table
CREATE TABLE orders (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    status VARCHAR(50) NOT NULL,
    total DECIMAL(10,2) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Order items table
CREATE TABLE order_items (
    id UUID PRIMARY KEY,
    order_id UUID REFERENCES orders(id),
    product_id UUID REFERENCES products(id),
    quantity INT NOT NULL,
    price DECIMAL(10,2) NOT NULL
);

-- Shopping cart table
CREATE TABLE cart_items (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    product_id UUID REFERENCES products(id),
    quantity INT NOT NULL,
    added_at TIMESTAMP DEFAULT NOW()
);

-- Reviews table
CREATE TABLE reviews (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    product_id UUID REFERENCES products(id),
    rating INT CHECK (rating BETWEEN 1 AND 5),
    comment TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Payment transactions table
CREATE TABLE transactions (
    id UUID PRIMARY KEY,
    order_id UUID REFERENCES orders(id),
    amount DECIMAL(10,2) NOT NULL,
    payment_method VARCHAR(50),
    status VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Review Result

```
✅ Design Review APPROVED

Requirements Coverage: 100%

✓ Products with categories and inventory
  - products table with inventory_count
  - categories table with hierarchical support

✓ User accounts with order history
  - users table
  - orders table linked to users

✓ Shopping cart functionality
  - cart_items table per user

✓ Payment transaction records
  - transactions table with order linkage

✓ Product reviews and ratings
  - reviews table with 1-5 star ratings

Strengths:
- Proper foreign key relationships
- UUID primary keys for security
- Timestamp tracking
- Rating validation constraint

Suggestions:
- Consider adding indexes on foreign keys
- Add soft delete for products/users
- Consider order status enum type
```

## Validation Types

### 1. Code-Based Validation

Uses template matching and checklist validation:

```python
class CodeBasedValidator:
    def validate(self, requirements, design):
        # Extract requirements
        required_features = self.parse_requirements(requirements)

        # Extract design features
        design_features = self.parse_design(design)

        # Check coverage
        missing = []
        for req in required_features:
            if not self.feature_present(req, design_features):
                missing.append(req)

        return ValidationResult(
            approved=len(missing) == 0,
            coverage=len(required_features - missing) / len(required_features),
            issues=missing
        )
```

### 2. LLM-Based Validation

Uses fresh AI context for semantic review:

```python
class LLMBasedValidator:
    def validate(self, requirements, design):
        # Fresh context - no history
        prompt = f"""
        Review this design against requirements.

        Requirements:
        {requirements}

        Design:
        {design}

        Provide: approval status, coverage %, issues found
        """

        # Run with fresh LLM context
        result = llm.run(prompt, temperature=0)
        return parse_result(result)
```

## Integration with TodoWrite

```python
# Create design todo
todo = EvidenceRequiredTodo(
    content="Design authentication API",
    status="in_progress",
    activeForm="Designing auth API",
    evidence_ids=[],
    requires_evidence=True
)

# Create design
design = create_auth_api_design()

# Independent review
reviewer = DesignReviewer()
result = reviewer.review(requirements, design)

if result.approved:
    # Store evidence
    evidence = store.add_evidence(
        type="design_review",
        content=result.to_dict(),
        validator_id="design_reviewer"
    )

    # Add to todo
    todo.evidence_ids.append(evidence.id)

    # Can now complete
    print("✅ Todo can be completed with evidence")
```

## Best Practices

1. **Clear Requirements** - Be specific about what's needed
2. **Complete Designs** - Address all requirements explicitly
3. **Context Isolation** - Never share design process with reviewer
4. **Objective Criteria** - Use measurable quality standards
5. **Document Assumptions** - Make design decisions explicit

## Troubleshooting

### Review Fails Despite Good Design

**Problem**: Reviewer misunderstands requirements

**Solutions**:
- Make requirements more explicit
- Use structured format (numbered list)
- Include examples of expected features

### Context Pollution Suspected

**Problem**: Reviewer seems to have prior knowledge

**Solutions**:
- Verify fresh LLM context is used
- Check for shared state between reviews
- Use code-based validator for objective comparison

### Low Coverage Score

**Problem**: Design doesn't address all requirements

**Solutions**:
- Create requirements checklist
- Map each requirement to design section
- Iterate design until 100% coverage

## Summary

The design review workflow provides:

- **Context-free validation** - Reviewer has zero prior knowledge
- **Objective comparison** - Requirements vs design features
- **Multiple validators** - Code-based and LLM-based options
- **Evidence tracking** - Review results stored for task completion

This ensures designs are validated independently and objectively.
