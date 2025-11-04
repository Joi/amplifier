"""
Agent-Callable API for Bug Prediction

Provides simple API that coding agents can call to get probabilistic
risk assessments before making changes.
"""

from __future__ import annotations

import ast
from pathlib import Path

from amplifier.prob_tools.bug_models import BugPredictor
from amplifier.prob_tools.event_store import EventStore


class CodeAnalyzer:
    """Analyze code to extract features for bug prediction"""

    @staticmethod
    def analyze_function(source_code: str, function_name: str) -> dict:
        """Extract features from a function"""

        tree = ast.parse(source_code)

        # Find the function
        func_node = None
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == function_name:
                func_node = node
                break

        if not func_node:
            return {}

        # Extract features
        has_null_check = CodeAnalyzer._has_null_checks(func_node)
        has_error_handling = CodeAnalyzer._has_error_handling(func_node)
        complexity = CodeAnalyzer._calculate_complexity(func_node)
        is_async = isinstance(func_node, ast.AsyncFunctionDef)

        return {
            "has_null_check": has_null_check,
            "has_error_handling": has_error_handling,
            "complexity": min(complexity / 20.0, 1.0),  # Normalize to 0-1
            "is_async": is_async,
        }

    @staticmethod
    def _has_null_checks(func_node: ast.FunctionDef) -> bool:
        """Check if function has null/None checks"""
        for node in ast.walk(func_node):
            if isinstance(node, ast.Compare):
                # Look for comparisons with None
                if any(isinstance(comp, ast.Is) or isinstance(comp, ast.IsNot) for comp in node.ops):
                    return True
        return False

    @staticmethod
    def _has_error_handling(func_node: ast.FunctionDef) -> bool:
        """Check if function has try/except"""
        for node in ast.walk(func_node):
            if isinstance(node, ast.Try):
                return True
        return False

    @staticmethod
    def _calculate_complexity(func_node: ast.FunctionDef) -> int:
        """Calculate cyclomatic complexity"""
        complexity = 1
        for node in ast.walk(func_node):
            if isinstance(node, (ast.If, ast.For, ast.While, ast.ExceptHandler)):
                complexity += 1
        return complexity


class AgentAPI:
    """Simple API for coding agents to query bug predictions"""

    def __init__(self, storage_path: Path | None = None):
        self.event_store = EventStore(storage_path)
        self.bug_predictor = BugPredictor(self.event_store)
        self.code_analyzer = CodeAnalyzer()

    def check_code_before_commit(self, file_path: str, function_name: str | None = None) -> dict:
        """
        Check code before committing.

        Agents call this before making changes.

        Args:
            file_path: Path to file being changed
            function_name: Optional specific function to check

        Returns:
            Risk assessment with recommendations
        """

        with open(file_path) as f:
            source_code = f.read()

        if function_name:
            # Analyze specific function
            features = self.code_analyzer.analyze_function(source_code, function_name)
            if not features:
                return {"error": f"Function {function_name} not found"}

            prediction = self.bug_predictor.predict_bug_probability(
                has_null_check=features["has_null_check"],
                has_error_handling=features["has_error_handling"],
                complexity=features["complexity"],
                is_async=features["is_async"],
            )

            return {
                "file": file_path,
                "function": function_name,
                "features": features,
                "prediction": prediction,
            }

        # Analyze whole file
        tree = ast.parse(source_code)
        functions = [node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]

        results = []
        for func in functions[:5]:  # Top 5 functions
            features = self.code_analyzer.analyze_function(source_code, func.name)
            if features:
                prediction = self.bug_predictor.predict_bug_probability(
                    has_null_check=features["has_null_check"],
                    has_error_handling=features["has_error_handling"],
                    complexity=features["complexity"],
                    is_async=features["is_async"],
                )
                results.append({"function": func.name, "prediction": prediction})

        return {"file": file_path, "functions_analyzed": len(results), "results": results}

    def get_historical_patterns(self) -> dict:
        """Get summary of learned patterns"""
        return {
            "bug_patterns": self.event_store.get_bug_patterns(),
            "total_bug_events": len(self.event_store.get_all_bug_events()),
            "total_refactoring_events": len(self.event_store.get_all_refactoring_events()),
        }
