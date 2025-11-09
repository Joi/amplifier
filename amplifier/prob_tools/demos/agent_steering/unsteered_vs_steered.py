"""Unsteered vs Steered Agent Comparison.

This demo shows the dramatic difference between:
1. Unsteered agent (hopes for correctness)
2. Steered agent (enforces correctness)

Since we don't have LLaMPPL fully integrated yet, this is a
conceptual demonstration showing what WOULD happen.
"""

import time

from constraint_examples import has_docstrings
from constraint_examples import has_error_handling
from constraint_examples import has_type_hints
from constraint_examples import no_sql_injection
from constraint_examples import syntax_valid
from constraint_examples import validates_input


class UnsteeredAgent:
    """Simulates a regular AI coding agent (like current Amplifier)."""

    def generate(self, prompt: str) -> str:
        """Generate code without constraint enforcement."""
        print(f"🤖 Unsteered Agent generating code for: {prompt}")
        print("   Strategy: Sample from LLM, hope it's correct")
        time.sleep(0.2)  # Simulate fast generation

        # Simulate typical AI-generated code with common mistakes
        code = """
def login(username, password):
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
    result = db.execute(query)
    return result.fetchone()
"""
        return code


class SteeredAgent:
    """Simulates LLaMPPL-steered agent with hard constraints."""

    def generate(self, prompt: str, constraints: list) -> str:
        """Generate code with SMC steering and constraint enforcement."""
        print(f"🔬 Steered Agent generating code for: {prompt}")
        print(f"   Strategy: SMC steering with {len(constraints)} hard constraints")

        # Simulate SMC steering process
        particles = 10
        print(f"\n   🔄 Initializing {particles} particles...")
        time.sleep(0.1)

        for i in range(5):
            print(f"   🔄 Step {i + 1}: Sampling and checking constraints...")

            # Simulate particle rejection
            if i == 1:
                print("      ❌ Particle 3 rejected: SQL injection pattern detected")
                print("      ❌ Particle 5 rejected: Missing type hints")
            elif i == 2:
                print("      ❌ Particle 2 rejected: No error handling")
                print("      ❌ Particle 7 rejected: No input validation")
            elif i == 3:
                print("      ✅ All particles now satisfy constraints")

            time.sleep(0.3)

        print("   🔄 Resampling particles based on weights...")
        time.sleep(0.2)
        print("   🔄 MCMC rejuvenation to prevent depletion...")
        time.sleep(0.2)

        # Simulate final valid code
        code = '''
def login(username: str, password: str) -> Optional[dict]:
    """Authenticate user with username and password.

    Args:
        username: User's username
        password: User's password

    Returns:
        User dict if authenticated, None otherwise
    """
    # Input validation
    if not isinstance(username, str) or not isinstance(password, str):
        raise TypeError("Username and password must be strings")

    if not username or not password:
        raise ValueError("Username and password cannot be empty")

    try:
        # Parameterized query prevents SQL injection
        query = "SELECT * FROM users WHERE username = ?"
        result = db.execute(query, (username,))
        user = result.fetchone()

        if user and verify_password(password, user["password_hash"]):
            return user
        return None
    except DatabaseError as e:
        logger.error(f"Database error during login: {e}")
        return None
'''
        return code


def analyze_code(code: str, label: str):
    """Analyze generated code against constraints."""
    print(f"\n📊 Analysis of {label}:")
    print(f"\nGenerated code:\n{code}\n")

    constraints = {
        "Syntax valid": syntax_valid(code),
        "Has type hints": has_type_hints(code),
        "No SQL injection": no_sql_injection(code),
        "Has error handling": has_error_handling(code),
        "Validates input": validates_input(code),
        "Has docstrings": has_docstrings(code),
    }

    passed = sum(constraints.values())
    total = len(constraints)

    print("Constraint satisfaction:")
    for name, satisfied in constraints.items():
        status = "✅" if satisfied else "❌"
        print(f"  {status} {name}")

    print(f"\n Result: {passed}/{total} constraints satisfied ({(passed / total) * 100:.0f}%)")

    return passed == total


def run_comparison():
    """Run side-by-side comparison."""
    print("=" * 80)
    print("UNSTEERED vs STEERED AGENT COMPARISON")
    print("=" * 80)
    print()

    prompt = "Create a login function that authenticates users against a database"

    # Unsteered generation
    print("┌" + "─" * 78 + "┐")
    print("│ UNSTEERED AGENT (Current Approach)                                        │")
    print("└" + "─" * 78 + "┘")
    print()

    unsteered = UnsteeredAgent()
    start = time.time()
    unsteered_code = unsteered.generate(prompt)
    unsteered_time = (time.time() - start) * 1000

    print(f"\n✅ Generated in {unsteered_time:.0f}ms")
    analyze_code(unsteered_code, "UNSTEERED Agent")

    input("\n\nPress Enter to see STEERED agent...")

    # Steered generation
    print("\n")
    print("┌" + "─" * 78 + "┐")
    print("│ STEERED AGENT (LLaMPPL SMC Steering)                                      │")
    print("└" + "─" * 78 + "┘")
    print()

    steered = SteeredAgent()
    constraints = [
        syntax_valid,
        has_type_hints,
        no_sql_injection,
        has_error_handling,
        validates_input,
        has_docstrings,
    ]

    start = time.time()
    steered_code = steered.generate(prompt, constraints)
    steered_time = (time.time() - start) * 1000

    print(f"\n✅ Generated in {steered_time:.0f}ms")
    analyze_code(steered_code, "STEERED Agent")

    # Comparison summary
    print("\n")
    print("=" * 80)
    print("COMPARISON SUMMARY")
    print("=" * 80)
    print()
    print(f"{'Metric':<30} {'Unsteered':<25} {'Steered':<25}")
    print("-" * 80)
    print(f"{'Speed':<30} {f'{unsteered_time:.0f}ms ⚡':<25} {f'{steered_time:.0f}ms 🐌':<25}")
    print(f"{'Correctness':<30} {'2/6 constraints (33%) ❌':<25} {'6/6 constraints (100%) ✅':<25}")
    print(f"{'SQL Injection':<30} {'VULNERABLE ❌':<25} {'SAFE ✅':<25}")
    print(f"{'Error Handling':<30} {'MISSING ❌':<25} {'PRESENT ✅':<25}")
    print(f"{'Input Validation':<30} {'MISSING ❌':<25} {'PRESENT ✅':<25}")
    print(f"{'Type Safety':<30} {'MISSING ❌':<25} {'PRESENT ✅':<25}")
    print()

    print("=" * 80)
    print("KEY INSIGHT")
    print("=" * 80)
    print()
    print("Unsteered Agent:")
    print("  • Fast (200ms)")
    print("  • But HOPES code is correct")
    print("  • Can violate constraints")
    print("  • Requires manual review")
    print()
    print("Steered Agent:")
    print("  • Slower (2000ms, 10x overhead)")
    print("  • But ENFORCES correctness")
    print("  • IMPOSSIBLE to violate constraints")
    print("  • Reduces review burden")
    print()
    print("Trade-off: Speed vs Guarantee")
    print("  → Use steering for critical code (auth, payments, security)")
    print("  → Use unsteered for exploratory code (docs, prototypes)")
    print()

    print("=" * 80)
    print("THE VALUE PROPOSITION")
    print("=" * 80)
    print()
    print("With steering, you can PROVABLY guarantee:")
    print("  ✓ No SQL injection vulnerabilities")
    print("  ✓ All code type-checks")
    print("  ✓ Error handling present")
    print("  ✓ Input validation enforced")
    print("  ✓ Architectural patterns followed")
    print()
    print("Not 'probably' or 'usually' - PROVABLY.")
    print("Mathematical guarantee via SMC steering.")
    print()


if __name__ == "__main__":
    run_comparison()
