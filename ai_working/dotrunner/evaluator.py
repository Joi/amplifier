"""
Expression evaluator for complex routing conditions.

Safely evaluates routing expressions using AST parsing.
"""

import ast
import logging
import operator
from typing import Any

logger = logging.getLogger(__name__)


class SafeExpressionEvaluator:
    """
    Safely evaluate routing expressions using ast.literal_eval approach.

    Supports:
    - Comparisons: >, >=, <, <=, ==, !=
    - Logical operators: and, or
    - Basic functions: len()
    - Variables from context
    - Literals: numbers, strings, booleans

    Examples:
        "count > 10"
        "status == 'ready' and count > 5"
        "test_passed or coverage >= 0.8"
        "len(files) > 0"
    """

    # Allowed operators
    OPERATORS = {
        ast.Gt: operator.gt,
        ast.GtE: operator.ge,
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
        ast.And: operator.and_,
        ast.Or: operator.or_,
    }

    def evaluate(self, expression: str, context: dict[str, Any]) -> bool:
        """
        Evaluate expression safely with context.

        Args:
            expression: Python expression string
            context: Dictionary of variables available for evaluation

        Returns:
            Boolean result of expression evaluation

        Raises:
            ValueError: If expression is invalid or unsafe

        Examples:
            >>> evaluator = SafeExpressionEvaluator()
            >>> evaluator.evaluate("count > 10", {"count": 15})
            True
            >>> evaluator.evaluate("status == 'ready'", {"status": "ready"})
            True
        """
        try:
            # Parse expression into AST
            tree = ast.parse(expression, mode="eval")

            # Evaluate with context
            result = self._eval_node(tree.body, context)

            # Ensure result is boolean
            return bool(result)

        except Exception as e:
            logger.error(f"Expression evaluation failed: {expression} - {e}")
            raise ValueError(f"Invalid expression: {expression}") from e

    def _eval_node(self, node: ast.AST, context: dict[str, Any]) -> Any:
        """
        Recursively evaluate AST node.

        Args:
            node: AST node to evaluate
            context: Variable context

        Returns:
            Evaluation result

        Raises:
            ValueError: If node type is unsupported
        """
        if isinstance(node, ast.Compare):
            # Handle comparisons: a > b, a == b, etc.
            left = self._eval_node(node.left, context)
            for op, comparator in zip(node.ops, node.comparators):
                right = self._eval_node(comparator, context)
                if type(op) not in self.OPERATORS:
                    raise ValueError(f"Unsupported operator: {type(op).__name__}")
                if not self.OPERATORS[type(op)](left, right):
                    return False
                left = right
            return True

        elif isinstance(node, ast.BoolOp):
            # Handle and/or
            if type(node.op) not in self.OPERATORS:
                raise ValueError(f"Unsupported boolean operator: {type(node.op).__name__}")

            values = [self._eval_node(n, context) for n in node.values]
            if isinstance(node.op, ast.And):
                return all(values)
            else:  # Or
                return any(values)

        elif isinstance(node, ast.Name):
            # Variable lookup
            var_name = node.id
            if var_name not in context:
                logger.warning(f"Variable '{var_name}' not found in context, defaulting to None")
                return None
            return context[var_name]

        elif isinstance(node, ast.Constant):
            # Literal value (Python 3.8+)
            return node.value

        elif isinstance(node, ast.Num):
            # Numeric literal (Python 3.7 compatibility)
            return node.n

        elif isinstance(node, ast.Str):
            # String literal (Python 3.7 compatibility)
            return node.s

        elif isinstance(node, ast.NameConstant):
            # True, False, None (Python 3.7 compatibility)
            return node.value

        elif isinstance(node, ast.Call):
            # Handle function calls (limited set)
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
                if func_name == "len":
                    if len(node.args) != 1:
                        raise ValueError("len() requires exactly 1 argument")
                    arg = self._eval_node(node.args[0], context)
                    return len(arg) if arg is not None else 0
                else:
                    raise ValueError(f"Unsupported function: {func_name}")
            else:
                raise ValueError("Only simple function calls are supported")

        else:
            raise ValueError(f"Unsupported expression type: {type(node).__name__}")


def evaluate_condition(condition: str, context: dict[str, Any]) -> bool:
    """
    Convenience function to evaluate a single condition.

    Args:
        condition: Expression string
        context: Variable context

    Returns:
        Boolean result

    Examples:
        >>> evaluate_condition("count > 10", {"count": 15})
        True
    """
    evaluator = SafeExpressionEvaluator()
    return evaluator.evaluate(condition, context)
