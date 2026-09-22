"""
LangChain tools for the student agent.

Each tool has:
- a clear docstring (the LLM reads this to decide when to call it)
- type hints (used to build the tool input schema)
"""

from __future__ import annotations

import ast
import operator
from typing import Any

from langchain_core.tools import tool

from db import fetch_student


@tool
def get_student_info(student_id: str) -> str:
    """Get a student's name and department by student_id.

    Use this when the user asks for name, department, or basic identity
    of a student (for example: 'Who is 22CS045?' or 'What department is Priya in?').

    Args:
        student_id: The student register number, e.g. '22CS045'.
    """
    student = fetch_student(student_id)
    if not student:
        return f"No student found with id '{student_id}'."
    return (
        f"student_id: {student['student_id']}\n"
        f"name: {student['name']}\n"
        f"department: {student['department']}"
    )


@tool
def get_student_marks(student_id: str) -> str:
    """Get subject marks (python, database, ai, web) for a student.

    Use this when the user asks for marks, scores, totals, averages,
    or pass eligibility for a given student_id.

    Args:
        student_id: The student register number, e.g. '22CS045'.
    """
    student = fetch_student(student_id)
    if not student:
        return f"No student found with id '{student_id}'."
    return (
        f"student_id: {student['student_id']}\n"
        f"python: {student['python']}\n"
        f"database: {student['database']}\n"
        f"ai: {student['ai']}\n"
        f"web: {student['web']}"
    )


# Safe arithmetic only (no arbitrary Python eval)
_ALLOWED_BINOPS: dict[type, Any] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_ALLOWED_UNARY: dict[type, Any] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _eval_node(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _eval_node(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BINOPS:
        return _ALLOWED_BINOPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_UNARY:
        return _ALLOWED_UNARY[type(node.op)](_eval_node(node.operand))
    raise ValueError("Only basic arithmetic expressions are allowed.")


@tool
def calculator(expression: str) -> str:
    """Evaluate a basic arithmetic expression and return the numeric result.

    Use this to compute total marks, average marks, percentages, or any
    sum/division needed after fetching marks.
    Examples of expression: '85+72+90+78', '(85+72+90+78)/4'.

    Args:
        expression: A pure math expression using numbers and + - * / ( ).
    """
    try:
        tree = ast.parse(expression.strip(), mode="eval")
        result = _eval_node(tree)
        # Prefer int display when whole number
        if result == int(result):
            return str(int(result))
        return f"{result:.2f}"
    except Exception as exc:  # noqa: BLE001
        return f"Calculator error: {exc}"


@tool
def get_passing_rules() -> str:
    """Return the university passing rules.

    Use this when the user asks whether a student is eligible to pass,
    has failed, or what the minimum marks/average requirements are.
    """
    return (
        "University passing rules:\n"
        "1. Minimum overall average: 40%\n"
        "2. Minimum mark in each subject: 35%\n"
        "A student must satisfy BOTH conditions to pass."
    )


# Export list for the agent
ALL_TOOLS = [
    get_student_info,
    get_student_marks,
    calculator,
    get_passing_rules,
]
