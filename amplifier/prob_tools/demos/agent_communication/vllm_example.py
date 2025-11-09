"""vLLM Structured Outputs Demo for Agent Communication.

This demo shows how to use vLLM's structured outputs feature to generate
type-safe agent messages that conform to Pydantic schemas.

Requirements:
    - vLLM server running (see README.md for setup)
    - OpenAI client library
"""

import json
import time
from typing import List

from openai import OpenAI

from schemas import (
    AnalyzerMessage,
    CodeFinding,
    CoordinatorDecision,
    FindingType,
    ReviewerMessage,
    ReviewStatus,
    Severity,
)


class VLLMAgentCommunicator:
    """Handles agent communication using vLLM structured outputs."""

    def __init__(self, base_url: str = "http://localhost:8000/v1", model: str = "meta-llama/Llama-3.1-8B-Instruct"):
        """Initialize vLLM client.

        Args:
            base_url: URL of the vLLM server
            model: Model name to use
        """
        self.client = OpenAI(
            api_key="EMPTY",  # vLLM doesn't require API key
            base_url=base_url,
        )
        self.model = model

    def generate_analyzer_message(self, code_snippet: str, file_paths: List[str]) -> AnalyzerMessage:
        """Generate an AnalyzerMessage using vLLM structured outputs.

        Args:
            code_snippet: Code to analyze
            file_paths: Files being analyzed

        Returns:
            AnalyzerMessage conforming to schema
        """
        start_time = time.time()

        # Create the prompt for the analyzer agent
        prompt = f"""You are a code analyzer agent. Analyze the following code and generate a structured analysis report.

Files being analyzed: {', '.join(file_paths)}

Code:
{code_snippet}

Generate a complete analysis message with findings. Include at least 2-3 findings with varying severities.
Focus on: security issues, performance problems, style violations, and maintainability concerns.
"""

        # Use vLLM's structured output with Pydantic schema
        completion = self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a code analysis agent that produces structured findings."},
                {"role": "user", "content": prompt},
            ],
            response_format=AnalyzerMessage,
            temperature=0.7,
            max_tokens=1000,
        )

        elapsed_ms = int((time.time() - start_time) * 1000)

        # Extract the structured message
        message = completion.choices[0].message.parsed

        print(f"✅ Generated AnalyzerMessage in {elapsed_ms}ms")
        print(f"   Found {len(message.findings)} issues")

        return message

    def generate_reviewer_message(self, analyzer_msg: AnalyzerMessage) -> ReviewerMessage:
        """Generate a ReviewerMessage based on analyzer findings.

        Args:
            analyzer_msg: The analyzer message to review

        Returns:
            ReviewerMessage conforming to schema
        """
        start_time = time.time()

        # Create the prompt for the reviewer agent
        findings_summary = "\n".join(
            [
                f"{i}. {f.finding_type.value} ({f.severity.value}): {f.description}"
                for i, f in enumerate(analyzer_msg.findings)
            ]
        )

        prompt = f"""You are a code reviewer agent. Review the following findings from the analyzer agent:

Analyzer ID: {analyzer_msg.agent_id}
Files analyzed: {', '.join(analyzer_msg.analyzed_files)}

Findings:
{findings_summary}

Generate a structured review with recommendations for each finding.
Decide which findings should block the PR and provide rationale.
"""

        # Use vLLM's structured output
        completion = self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a code reviewer that evaluates findings and makes structured recommendations.",
                },
                {"role": "user", "content": prompt},
            ],
            response_format=ReviewerMessage,
            temperature=0.3,  # Lower temperature for more consistent reviews
            max_tokens=800,
        )

        elapsed_ms = int((time.time() - start_time) * 1000)

        message = completion.choices[0].message.parsed

        print(f"✅ Generated ReviewerMessage in {elapsed_ms}ms")
        print(f"   Status: {message.review_status.value}")
        print(f"   Blocking issues: {message.blocking_issues_count}")

        return message

    def generate_coordinator_decision(
        self, analyzer_msgs: List[AnalyzerMessage], reviewer_msgs: List[ReviewerMessage]
    ) -> CoordinatorDecision:
        """Generate final coordinator decision based on all reviews.

        Args:
            analyzer_msgs: All analyzer messages
            reviewer_msgs: All reviewer messages

        Returns:
            CoordinatorDecision conforming to schema
        """
        start_time = time.time()

        # Summarize all findings
        total_findings = sum(len(msg.findings) for msg in analyzer_msgs)
        critical_count = sum(
            1
            for msg in analyzer_msgs
            for f in msg.findings
            if f.severity in [Severity.CRITICAL, Severity.HIGH]
        )

        review_statuses = [msg.review_status.value for msg in reviewer_msgs]
        blocking_count = sum(msg.blocking_issues_count for msg in reviewer_msgs)

        prompt = f"""You are a coordinator agent making final decisions on code reviews.

Summary:
- Total findings: {total_findings}
- Critical/High severity: {critical_count}
- Review statuses: {', '.join(review_statuses)}
- Blocking issues: {blocking_count}

Based on this information, make a final decision on whether to approve, request changes, or reject the PR.
Provide clear rationale and next steps.
"""

        # Use vLLM's structured output
        completion = self.client.beta.chat.completions.parse(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a coordinator that makes final review decisions."},
                {"role": "user", "content": prompt},
            ],
            response_format=CoordinatorDecision,
            temperature=0.2,  # Very low temperature for consistent decisions
            max_tokens=600,
        )

        elapsed_ms = int((time.time() - start_time) * 1000)

        message = completion.choices[0].message.parsed

        print(f"✅ Generated CoordinatorDecision in {elapsed_ms}ms")
        print(f"   Final status: {message.final_status.value}")
        print(f"   Must fix: {len(message.must_fix_before_merge)} items")

        return message


def run_demo():
    """Run the complete vLLM demo."""
    print("=" * 60)
    print("vLLM Structured Outputs Demo: Agent Communication")
    print("=" * 60)

    # Sample code to analyze
    code_snippet = """
def authenticate_user(username, password):
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
    result = db.execute(query)
    return result.fetchone()

def get_user_posts(user_id):
    posts = []
    for post_id in get_post_ids(user_id):
        post = db.query(f"SELECT * FROM posts WHERE id={post_id}")
        posts.append(post)
    return posts
"""

    try:
        communicator = VLLMAgentCommunicator()

        # Step 1: Analyzer generates findings
        print("\n📊 Step 1: Analyzer Agent analyzing code...")
        analyzer_msg = communicator.generate_analyzer_message(
            code_snippet=code_snippet, file_paths=["src/auth.py", "src/posts.py"]
        )

        print("\nAnalyzer Message (excerpt):")
        print(f"  Agent: {analyzer_msg.agent_id}")
        print(f"  Files: {analyzer_msg.analyzed_files}")
        print(f"  Findings: {len(analyzer_msg.findings)}")
        for finding in analyzer_msg.findings[:2]:  # Show first 2
            print(f"    - {finding.finding_type.value}: {finding.description[:60]}...")

        # Step 2: Reviewer evaluates findings
        print("\n📝 Step 2: Reviewer Agent reviewing findings...")
        reviewer_msg = communicator.generate_reviewer_message(analyzer_msg)

        print("\nReviewer Message (excerpt):")
        print(f"  Agent: {reviewer_msg.agent_id}")
        print(f"  Status: {reviewer_msg.review_status.value}")
        print(f"  Blocking issues: {reviewer_msg.blocking_issues_count}")
        print(f"  Assessment: {reviewer_msg.overall_assessment[:80]}...")

        # Step 3: Coordinator makes final decision
        print("\n🎯 Step 3: Coordinator Agent making final decision...")
        coordinator_msg = communicator.generate_coordinator_decision(
            analyzer_msgs=[analyzer_msg], reviewer_msgs=[reviewer_msg]
        )

        print("\nCoordinator Decision (excerpt):")
        print(f"  Decision ID: {coordinator_msg.decision_id}")
        print(f"  Final Status: {coordinator_msg.final_status.value}")
        print(f"  Critical Issues: {coordinator_msg.critical_issues}")
        print(f"  Must Fix: {coordinator_msg.must_fix_before_merge}")
        print(f"  Next Steps:")
        for step in coordinator_msg.next_steps[:3]:
            print(f"    - {step}")

        # Validate all messages
        print("\n✅ All messages conform to Pydantic schemas!")
        print(f"   AnalyzerMessage: {len(analyzer_msg.model_dump())} fields")
        print(f"   ReviewerMessage: {len(reviewer_msg.model_dump())} fields")
        print(f"   CoordinatorDecision: {len(coordinator_msg.model_dump())} fields")

        # Save to file for inspection
        output = {
            "analyzer": analyzer_msg.model_dump(),
            "reviewer": reviewer_msg.model_dump(),
            "coordinator": coordinator_msg.model_dump(),
        }

        with open("/tmp/vllm_agent_messages.json", "w") as f:
            json.dump(output, f, indent=2)

        print(f"\n💾 Full messages saved to: /tmp/vllm_agent_messages.json")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure vLLM server is running:")
        print("  python -m vllm.entrypoints.openai.api_server \\")
        print("    --model meta-llama/Llama-3.1-8B-Instruct \\")
        print("    --guided-decoding-backend outlines")
        raise


if __name__ == "__main__":
    run_demo()
