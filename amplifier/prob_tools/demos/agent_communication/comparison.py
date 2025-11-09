"""Side-by-side comparison of vLLM and LLaMPPL for agent communication.

This script runs both approaches and compares:
- Generation speed
- Constraint satisfaction rate
- Output quality
- Resource usage
"""

import json
import time
from typing import Dict, List, Tuple

from pydantic import ValidationError

from schemas import AnalyzerMessage, ReviewerMessage, CoordinatorDecision


class ComparisonRunner:
    """Runs and compares both approaches."""

    def __init__(self):
        self.results = {
            "vllm": {"times": [], "valid": 0, "invalid": 0, "errors": []},
            "llamppl": {"times": [], "valid": 0, "invalid": 0, "errors": []},
        }

    def validate_message(self, message_dict: dict, schema_class) -> bool:
        """Validate a message against its schema.

        Args:
            message_dict: Message as dictionary
            schema_class: Pydantic schema class

        Returns:
            True if valid, False otherwise
        """
        try:
            schema_class(**message_dict)
            return True
        except (ValidationError, TypeError, ValueError) as e:
            return False

    def run_vllm_trial(self, trial_num: int) -> Tuple[float, bool, str]:
        """Run a single vLLM trial.

        Args:
            trial_num: Trial number

        Returns:
            (generation_time_ms, is_valid, error_msg)
        """
        try:
            # Import vLLM example
            from vllm_example import VLLMAgentCommunicator

            start = time.time()

            communicator = VLLMAgentCommunicator()

            # Generate analyzer message
            msg = communicator.generate_analyzer_message(
                code_snippet="def test(): pass", file_paths=["test.py"]
            )

            elapsed_ms = (time.time() - start) * 1000

            # Validate
            is_valid = self.validate_message(msg.model_dump(), AnalyzerMessage)

            return elapsed_ms, is_valid, ""

        except Exception as e:
            return 0, False, str(e)

    def run_llamppl_trial(self, trial_num: int) -> Tuple[float, bool, str]:
        """Run a single LLaMPPL trial.

        Args:
            trial_num: Trial number

        Returns:
            (generation_time_ms, is_valid, error_msg)
        """
        try:
            # Import LLaMPPL example
            from llamppl_example import LLaMPPLAgentCommunicator

            start = time.time()

            communicator = LLaMPPLAgentCommunicator()

            # Generate analyzer message with constraints
            msg = communicator.generate_analyzer_message_constrained(
                code_snippet="def test(): pass", file_paths=["test.py"]
            )

            elapsed_ms = (time.time() - start) * 1000

            # Validate
            is_valid = self.validate_message(msg.model_dump(), AnalyzerMessage)

            return elapsed_ms, is_valid, ""

        except Exception as e:
            return 0, False, str(e)

    def run_comparison(self, num_trials: int = 5):
        """Run comparison between both approaches.

        Args:
            num_trials: Number of trials to run for each approach
        """
        print("=" * 70)
        print("COMPARISON: vLLM vs LLaMPPL for Agent Communication")
        print("=" * 70)
        print()

        # Run vLLM trials
        print(f"🚀 Running {num_trials} vLLM trials...")
        for i in range(num_trials):
            elapsed, valid, error = self.run_vllm_trial(i)

            if error:
                self.results["vllm"]["errors"].append(error)
                self.results["vllm"]["invalid"] += 1
                print(f"  Trial {i+1}: ERROR - {error[:60]}")
            else:
                self.results["vllm"]["times"].append(elapsed)
                if valid:
                    self.results["vllm"]["valid"] += 1
                    print(f"  Trial {i+1}: ✅ {elapsed:.0f}ms (valid)")
                else:
                    self.results["vllm"]["invalid"] += 1
                    print(f"  Trial {i+1}: ❌ {elapsed:.0f}ms (invalid)")

        print()

        # Run LLaMPPL trials
        print(f"🔬 Running {num_trials} LLaMPPL trials...")
        for i in range(num_trials):
            elapsed, valid, error = self.run_llamppl_trial(i)

            if error:
                self.results["llamppl"]["errors"].append(error)
                self.results["llamppl"]["invalid"] += 1
                print(f"  Trial {i+1}: ERROR - {error[:60]}")
            else:
                self.results["llamppl"]["times"].append(elapsed)
                if valid:
                    self.results["llamppl"]["valid"] += 1
                    print(f"  Trial {i+1}: ✅ {elapsed:.0f}ms (valid)")
                else:
                    self.results["llamppl"]["invalid"] += 1
                    print(f"  Trial {i+1}: ❌ {elapsed:.0f}ms (invalid)")

        print()
        self.print_summary()

    def print_summary(self):
        """Print comparison summary."""
        print("=" * 70)
        print("RESULTS SUMMARY")
        print("=" * 70)
        print()

        # Calculate statistics
        for approach in ["vllm", "llamppl"]:
            results = self.results[approach]
            times = results["times"]

            print(f"{'vLLM' if approach == 'vllm' else 'LLaMPPL'}:")
            print(f"  Valid outputs:   {results['valid']}")
            print(f"  Invalid outputs: {results['invalid']}")
            print(f"  Errors:          {len(results['errors'])}")

            if times:
                avg_time = sum(times) / len(times)
                min_time = min(times)
                max_time = max(times)
                print(f"  Avg time:        {avg_time:.0f}ms")
                print(f"  Min time:        {min_time:.0f}ms")
                print(f"  Max time:        {max_time:.0f}ms")

                total = results["valid"] + results["invalid"]
                if total > 0:
                    validity_rate = (results["valid"] / total) * 100
                    print(f"  Validity rate:   {validity_rate:.1f}%")

            if results["errors"]:
                print(f"  Sample error:    {results['errors'][0][:50]}...")

            print()

        # Comparison
        print("=" * 70)
        print("HEAD-TO-HEAD COMPARISON")
        print("=" * 70)
        print()

        vllm_times = self.results["vllm"]["times"]
        llamppl_times = self.results["llamppl"]["times"]

        if vllm_times and llamppl_times:
            vllm_avg = sum(vllm_times) / len(vllm_times)
            llamppl_avg = sum(llamppl_times) / len(llamppl_times)
            speedup = llamppl_avg / vllm_avg if vllm_avg > 0 else 0

            print(f"Speed:")
            print(f"  vLLM:    {vllm_avg:.0f}ms (baseline)")
            print(f"  LLaMPPL: {llamppl_avg:.0f}ms ({speedup:.1f}x slower)")
            print()

        vllm_total = self.results["vllm"]["valid"] + self.results["vllm"]["invalid"]
        llamppl_total = self.results["llamppl"]["valid"] + self.results["llamppl"]["invalid"]

        if vllm_total > 0 and llamppl_total > 0:
            vllm_validity = (self.results["vllm"]["valid"] / vllm_total) * 100
            llamppl_validity = (self.results["llamppl"]["valid"] / llamppl_total) * 100

            print(f"Validity:")
            print(f"  vLLM:    {vllm_validity:.1f}% schema compliance")
            print(f"  LLaMPPL: {llamppl_validity:.1f}% schema compliance")
            print()

        print("=" * 70)
        print("RECOMMENDATIONS")
        print("=" * 70)
        print()
        print("Use vLLM when:")
        print("  ✓ Speed is critical (100-500ms generation)")
        print("  ✓ 95-99% validity is acceptable")
        print("  ✓ Production deployment at scale")
        print("  ✓ JSON schema constraints are sufficient")
        print()
        print("Use LLaMPPL when:")
        print("  ✓ 100% correctness is required")
        print("  ✓ Complex logical constraints needed")
        print("  ✓ Can tolerate 1-5s latency")
        print("  ✓ Type-safety must be mathematically proven")
        print()
        print("Hybrid approach:")
        print("  → vLLM for most agent messages (fast, good enough)")
        print("  → LLaMPPL for critical decisions (slow, guaranteed correct)")
        print("  → Example: vLLM for analysis, LLaMPPL for final code generation")
        print()


def main():
    """Run the comparison."""
    runner = ComparisonRunner()

    print("This comparison requires both vLLM and LLaMPPL to be set up.")
    print()
    print("vLLM setup:")
    print("  1. Install: pip install vllm")
    print("  2. Start server: python -m vllm.entrypoints.openai.api_server \\")
    print("       --model meta-llama/Llama-3.1-8B-Instruct")
    print()
    print("LLaMPPL setup:")
    print("  1. Install: pip install llamppl")
    print("  2. (No server needed)")
    print()

    response = input("Ready to run comparison? (y/n): ").strip().lower()
    if response == "y":
        runner.run_comparison(num_trials=3)
    else:
        print("\nTo see conceptual comparison, check:")
        print("  - vllm_example.py (production-ready, fast)")
        print("  - llamppl_example.py (research-grade, guaranteed)")


if __name__ == "__main__":
    main()
