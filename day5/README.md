# Student LangChain Agent (Gemini + SQLite)

LangChain **agent** that answers student questions by **choosing tools** (not a fixed chain).

## What is included

| File | Purpose |
|------|---------|
| `students.db` | SQLite database with sample students |
| `seed_db.py` | Recreate the database |
| `db.py` | DB helper |
| `tools.py` | Four LangChain tools (`@tool`) |
| `agent.py` | Gemini ReAct agent |
| `main.py` | Demo + interactive CLI |
| `requirements.txt` | Dependencies |
| `.env.example` | API key template |

## Tools

1. **`get_student_info(student_id)`** — name & department  
2. **`get_student_marks(student_id)`** — python, database, ai, web  
3. **`calculator(expression)`** — total / average (safe math)  
4. **`get_passing_rules()`** — min average 40%, min each subject 35%

The **LLM decides** which tools to call and in what order.

## Setup

```bash
cd student-langchain-agent

python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt

copy .env.example .env    # Windows
# cp .env.example .env    # macOS/Linux
```

Edit `.env` and set:

```env
GOOGLE_API_KEY=your_key_from_https://aistudio.google.com/apikey
```

Optional: recreate DB

```bash
python seed_db.py
```

## Run

**Sample questions (assignment demo):**

```bash
python main.py --demo
```

**Interactive chat:**

```bash
python main.py
```

## Example questions

1. What is the name and department of student 22CS045?  
   → `get_student_info`

2. What are the marks of 22CS047?  
   → `get_student_marks`

3. What is the total and average mark of 22CS045?  
   → `get_student_marks` → `calculator`

4. Is 22CS045 eligible to pass according to the university rules?  
   → `get_student_marks` → `get_passing_rules` → `calculator`

**Challenge:**

> I am 22CS045. Tell me my name, department, total marks, average marks, and whether I satisfy the university passing requirements.

Agent should use multiple tools automatically, then answer.

## How the agent works

```text
User Question
     ↓
  Gemini LLM
     ↓
Which tool is needed?
     ↓
   Tool result
     ↓
  Gemini LLM
     ↓
Need another tool?
     ↓
   ...
     ↓
Final Answer
```

This is an **agentic** workflow (LLM chooses tools), not a hard-coded pipeline.

## Learning objectives covered

- `@tool` decorator and docstrings  
- Type hints → tool input schema  
- Multi-tool agent with Gemini  
- Tool selection by the LLM  
- Chaining tool results (marks → calculator → rules)  
- Agent vs fixed chain  

## Note on API keys

Never commit your real `.env` file. Only `.env.example` belongs in git.
