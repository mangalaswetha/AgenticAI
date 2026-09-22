"""Quick offline test of tools (no Gemini key required)."""

from tools import (
    calculator,
    get_passing_rules,
    get_student_info,
    get_student_marks,
)


def main() -> None:
    print("=== get_student_info ===")
    print(get_student_info.invoke({"student_id": "22CS045"}))

    print("\n=== get_student_marks ===")
    print(get_student_marks.invoke({"student_id": "22CS045"}))

    print("\n=== calculator ===")
    print("total:", calculator.invoke({"expression": "85+72+90+78"}))
    print("average:", calculator.invoke({"expression": "(85+72+90+78)/4"}))

    print("\n=== get_passing_rules ===")
    print(get_passing_rules.invoke({}))

    print("\nAll tools OK.")


if __name__ == "__main__":
    main()
