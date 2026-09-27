# Student Academic Advising Assistant (Safe Agent)

A safe agentic application built in Python demonstrating an LLM Agent Loop, Role-Based Access Control (RBAC), Tool Execution, and Safety Harness Guardrails.

---

## 1. Project Overview

The Student Academic Advising Assistant is a safe, role-aware AI agent designed to assist students and administrators with course discovery, schedule inspection, and enrollment management. 

The application implements an Agent Loop (Decision -> Action -> Observation -> Final Answer) with an application-level Safety Harness layer. The Safety Harness intercepts tool call requests proposed by the model and evaluates them against Role-Based Access Control (RBAC) rules, input boundary constraints, and prompt injection filters before permitting execution.

---

## 2. Available Tools

The agent has access to 3 structured tools:

1. **`search_course(query: str)`**
   - **Description**: Searches for courses by title, course code (e.g., 'CS101', 'AI'), or description keyword.
   - **Output**: Returns course matching details including the unique integer `course_id`.
   - **Allowed Roles**: Student, Admin.

2. **`check_schedule(course_id: int)`**
   - **Description**: Retrieves timetable, meeting days, time slot, room location, and enrollment statistics for a specific `course_id`.
   - **Constraints**: Requires a positive integer `course_id` (`course_id > 0`).
   - **Allowed Roles**: Student, Admin.

3. **`register_course(course_id: int, student_id: str = "STD1001")`**
   - **Description**: Unenrolls a student from a course and updates class enrollment counts.
   - **Constraints**: Restricted administrative action requiring positive integer `course_id`.
   - **Allowed Roles**: Admin only.

---

## 3. Agent Loop

The application executes a 7-stage Agent Loop:

```text
User Request
    │
    ▼
1. Receive & Sanitize Request (Input Guardrails Check)
    │
    ▼
2. LLM Decision (Determines if a tool is needed)
    │
    ▼
3. Select Tool & Generate Arguments (e.g. course_id=101)
    │
    ▼
4. Intercept & Validate (Safety Harness RBAC & Boundary Check)
    │
    ├── Allowed  ──► 5. Execute Tool Business Logic
    └── Denied   ──► 5. Intercepted: Return PERMISSION_DENIED
    │
    ▼
6. Observe Result (Append tool output to context history)
    │
    ▼
7. Final Answer Generation (Redact sensitive data & respond)
```

---

## 4. Permission Rule

Access permissions are enforced dynamically based on the active user role:

| Action / Tool | Student Role | Admin Role | Permission Policy |
| :--- | :---: | :---: | :--- |
| `search_course` | Allowed | Allowed | Public discovery capability |
| `check_schedule` | Allowed | Allowed | Public timetable inspection |
| `register_course` | **BLOCKED** | Allowed | Restricted administrative action |

- **Student Role**: Can discover courses and view timetables. Any attempt to invoke `register_course` is intercepted by the harness and returns `[SAFETY REFUSAL]: PERMISSION_DENIED`.
- **Admin Role**: Possesses full administrative authorization, including enrolling students via `register_course`.

---

## 5. Safety

The application implements defense-in-depth safety controls across multiple layers:

1. **Input Validation & Prompt Injection Guardrails**:
   - `check_input()` scans user prompts for prompt injection, system prompt override, or role spoofing attempts (e.g., "ignore previous instructions", "you are now admin") and blocks them immediately.

2. **Input Boundary Enforcement**:
   - `check_tool_permission()` validates that numeric arguments like `course_id` are positive integers (`course_id > 0`). Non-integers or values <= 0 trigger an `INPUT BOUNDARY ERROR` blockage.

3. **Permission Control (RBAC)**:
   - Tool execution requests are intercepted before execution. If the active role lacks authorization, the tool execution is prevented, and a structured `PERMISSION_DENIED` message is returned.

4. **Error Handling & Exception Protection**:
   - Tool functions trap exceptions (e.g., `ValueError`, non-existent IDs, invalid inputs) and return formatted error messages to the model instead of crashing the process.

5. **Loop Limits & Recursion Protection**:
   - Tool invocation loops are capped to prevent infinite loops or runaway LLM call chains.

6. **Output Redaction**:
   - `check_output()` validates model outputs against sensitive data patterns (e.g., API key formats, SSNs) and automatically redacts sensitive items before returning final text.

---

## 6. Example Run

### Example 1: Multi-Step Chained Discovery & Timetable Inspection (Student Role)

**User Input:**
`"Find Computer Science courses and check the schedule for the first course found."`

**Execution Logs & Tool Calls:**
```text
[OFFLINE MODE]: Processing request for role 'student'

[STEP 1 ACTION]: search_course({'query': 'CS'})
[STEP 1 OBSERVATION]: Found matching courses:
- ID: 101 | Code: CS101 | Name: Introduction to Computer Science | Instructor: Dr. Alan Turing | Credits: 3
- ID: 102 | Code: CS202 | Name: Data Structures and Algorithms | Instructor: Dr. Grace Hopper | Credits: 4

[STEP 2 ACTION]: check_schedule({'course_id': 101})
[STEP 2 OBSERVATION]: Schedule & Enrollment Info for Course ID [101] (CS101):
- Meeting Days: Mon / Wed
- Time Slot: 09:00 AM - 10:30 AM
- Room: Lab 301
- Enrolled: 27 / 30
- Status: Open
```

**Final Agent Response:**
```text
Found matching courses:
- ID: 101 | Code: CS101 | Name: Introduction to Computer Science | Instructor: Dr. Alan Turing | Credits: 3
- ID: 102 | Code: CS202 | Name: Data Structures and Algorithms | Instructor: Dr. Grace Hopper | Credits: 4

Schedule & Enrollment Info for Course ID [101] (CS101 - Introduction to Computer Science):
- Meeting Days: Mon / Wed
- Time Slot: 09:00 AM - 10:30 AM
- Room: Lab 301
- Enrolled: 27 / 30
- Status: Open
```

---

### Example 2: Restricted Action Interception (Student Role Attempting Drop)

**User Input:**
`"Register course 101"`

**Execution Logs & Tool Calls:**
```text
[OFFLINE MODE]: Processing request for role 'student'
[TOOL REQUESTED]: register_course({'course_id': 101})
[HARNESS PERMISSION BLOCKED]: PERMISSION_DENIED: Role 'student' is NOT authorized to execute tool 'register_course'. Action 'register_course' requires 'admin' role permissions.
```

**Final Agent Response:**
```text
[SAFETY REFUSAL]: PERMISSION_DENIED: Role 'student' is NOT authorized to execute tool 'register_course'. Action 'register_course' requires 'admin' role permissions.
```

---

## 7. How to Run (Instructions for Grading & Role Demo)

Follow these steps to run the application and demo each role:

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Start Interactive CLI Agent
```bash
python main.py
```

---

### Step 3: Step-by-Step Role Demo Guide

#### Demo 1: Student Role (Default Active Role)
When `main.py` starts, the active role is **`[STUDENT]`**.

1. **Test Capability 1: Search Courses**
   - **Type in terminal**: `Search for Introduction to Computer Science`
   - **Result**: Agent executes `search_course`, displaying matching courses with their `course_id`s (`101`, `102`, etc.).

2. **Test Capability 2: Check Schedule**
   - **Type in terminal**: `Check schedule for course ID 101`
   - **Result**: Agent executes `check_schedule`, showing meeting days (`Mon / Wed`), time slot, room, and capacity.

3. **Test Restricted Action Interception (Register Course)**
   - **Type in terminal**: `Register course ID 101`
   - **Result**: **BLOCKED BY SAFETY HARNESS**
   - **Output**: `[SAFETY REFUSAL]: PERMISSION_DENIED: Role 'student' is NOT authorized to execute tool 'register_course'. Action 'register_course' requires 'admin' role permissions.`

---
### Sample Prompts to Test
1. `Search for Introduction to Computer Science`
2. `Check schedule for course ID 101`
3. `Register course ID 101`  (Will be BLOCKED for 'student', APPROVED for 'admin')
---

#### Demo 2: Admin Role (Elevated Permissions)

1. **Switch Role to Admin**
   - **Type in terminal**: `role admin`
   - **Output**: `[ROLE UPDATED]: Active role is now [ADMIN]`

2. **Test Restricted Action Execution (Register Course as Admin)**
   - **Type in terminal**: `Register course ID 101`
   - **Type in terminal if want to register by specific student**: `Register course ID 101 as STD1003`
   - **Type in terminal if want to register by specific student**: `Register course ID 102 as STD2001`
   - **Result**: **APPROVED & EXECUTED BY SAFETY HARNESS**
   - **Output**: `SUCCESS: Student 'STD1001' has been successfully registered in Course ID '101' (CS101).`

3. **Switch Back to Student Role**
   - **Type in terminal**: `role student`
   - **Output**: `[ROLE UPDATED]: Active role is now [STUDENT]`

---

### Useful CLI Commands
- `role student` : Switch active role to Student
- `role admin`   : Switch active role to Admin
- `help`         : Show operational rules & sample prompts
- `history`      : View full conversation log
- `clear`        : Reset conversation history
- `exit`         : Quit application

---

### Optional: Set Up Live OpenAI API Key
1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Edit `.env` and set your API key:
   ```env
   OPENAI_API_KEY=sk-...
   ```
*(Note: If no API key is set, the application operates in deterministic offline simulation mode, so you can test all features without API credits).*

---

## Project Structure

```text
my-safe-agent/
├── README.md        # Complete project documentation & run instructions
├── main.py          # Starts CLI application & user interaction loop
├── agent.py         # Agent loop, model integration, and tool routing
├── tools.py         # Tool implementations and business logic
├── schemas.py       # Pydantic input argument schemas & data models
├── harness.py       # Safety Harness (RBAC permissions & guardrails)
├── .env.example     # Environment configuration template
└── requirements.txt # Python dependency list
```
