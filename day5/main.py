"""
Interactive and demo runner for the student LangChain agent.

Usage:
  python main.py              # interactive chat
  python main.py --demo       # run sample questions including the challenge
"""

from __future__ import annotations

import argparse
import os
import sys

from dotenv import load_dotenv

load_dotenv()


def run_demo(agent) -> None:
    from agent import ask

    questions = [
        "What is the name and department of student 22CS045?",
        "What are the marks of 22CS047?",
        "What is the total and average mark of 22CS045?",
        "Is 22CS045 eligible to pass according to the university rules?",
        (
            "I am 22CS045. Tell me my name, department, total marks, "
            "average marks, and whether I satisfy the university passing requirements."
        ),
    ]

    for i, q in enumerate(questions, 1):
        print("\n" + "=" * 70)
        print(f"Q{i}: {q}")
        print("-" * 70)
        try:
            answer = ask(agent, q)
            print(answer)
        except Exception as exc:  # noqa: BLE001
            print(f"Error: {exc}")
    print("\n" + "=" * 70)


def run_interactive(agent) -> None:
    from agent import ask

    print("Student Agent ready. Type a question (or 'quit' to exit).\n")
    while True:
        try:
            q = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break
        if not q:
            continue
        if q.lower() in {"quit", "exit", "q"}:
            print("Bye.")
            break
        try:
            answer = ask(agent, q)
            print(f"\nAgent: {answer}\n")
        except Exception as exc:  # noqa: BLE001
            print(f"Error: {exc}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Student LangChain + Gemini agent")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run the sample questions from the assignment",
    )
    args = parser.parse_args()

    try:
        from agent import build_agent

        agent = build_agent()
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to build agent: {exc}", file=sys.stderr)
        print(
            "\nMake sure you installed requirements and set GOOGLE_API_KEY in .env",
            file=sys.stderr,
        )
        return 1

    if args.demo:
        run_demo(agent)
    else:
        run_interactive(agent)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
