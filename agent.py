import os
import sys
import json
import re
from typing import List, Dict, Any
from dotenv import load_dotenv

from harness import SafetyHarness
from tools import OPENAI_TOOLS, TOOL_FUNCTIONS
from schemas import SafetyCheckResult, Role

# Set console encoding to UTF-8 on Windows if possible
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

load_dotenv()


class SafeAgent:
    """Student Assistant / Course Advisor Agent with Role-Based Safety Controls."""

    SYSTEM_PROMPT = (
        "You are a reliable, safe Student Academic Advising Assistant.\n\n"
        "### AVAILABLE FUNCTIONS:\n"
        "1. `search_course(query: str)`: Searches for courses by title or course code (e.g., \"AI\", \"CS101\").\n"
        "2. `check_schedule(course_id: int)`: Retrieves timetable, meeting hours, and details for a specific course ID (must be a positive integer).\n"
        "3. `drop_course(course_id: int)`: Drops/unenrolls from an active course. This is a restricted administrative action.\n\n"
        "### OPERATIONAL RULES & POLICIES:\n"
        "1. Grounded Execution: Never invent course IDs or times. Always call `search_course` first to discover IDs, then call `check_schedule` to verify timetables.\n"
        "2. Tool Failure & Permissions: If a tool returns a `PERMISSION_DENIED` observation from the execution harness, immediately stop and inform the user that their current role does not have authorization to perform that action.\n"
        "3. Input Boundaries: Ensure course IDs passed to `check_schedule` or `drop_course` are positive integers."
    )

    def __init__(self, model_name: str = None, role: Role = Role.STUDENT):
        self.model_name = model_name or os.getenv("DEFAULT_MODEL", "gpt-4o-mini")
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.role: Role = role
        self.harness = SafetyHarness()
        self.history: List[Dict[str, Any]] = [
            {"role": "system", "content": self.SYSTEM_PROMPT}
        ]
        self.logs: List[str] = []

        # Initialize OpenAI client if key is set
        self.client = None
        if self.api_key and self.api_key != "your_openai_api_key_here":
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
            except Exception as e:
                self.log(f"[WARN] Failed to initialize OpenAI client: {e}")

    def log(self, message: str):
        """Append log message."""
        print(message)
        self.logs.append(message)

    def set_role(self, new_role: Role):
        """Update current active user role."""
        self.role = new_role
        self.log(f"[ROLE UPDATED]: Current user role set to '{self.role.value}'")

    def process_input(self, user_input: str) -> str:
        """Process user request through Safety Harness, LLM, and RBAC Tool execution."""
        self.logs.clear()

        # Step 1: Input & Role Guardrail Check
        input_check: SafetyCheckResult = self.harness.check_input(user_input, current_role=self.role)
        if not input_check.is_safe:
            self.log(f"[HARNESS BLOCKED INPUT]: {input_check.reason}")
            return f"[SAFETY REFUSAL]: {input_check.reason}"

        # Add user message to history
        self.history.append({"role": "user", "content": user_input})

        # Step 2: LLM Completion (API or Local Fallback Simulation)
        if self.client:
            return self._run_openai_loop()
        else:
            return self._run_local_fallback(user_input)

    def _run_openai_loop(self, max_iterations: int = 5) -> str:
        """Execute agent loop with OpenAI API, RBAC permission checks, and MAX_ITERATIONS limit."""
        try:
            iterations = 0
            while iterations < max_iterations:
                iterations += 1
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=self.history,
                    tools=OPENAI_TOOLS,
                    tool_choice="auto",
                )
                message = response.choices[0].message

                # Exit loop if no tool calls requested (LLM provides final answer)
                if not message.tool_calls:
                    final_content = message.content or ""
                    break

                # Handle tool call requests
                self.history.append(message)

                for tool_call in message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments or "{}")

                    self.log(f"[TOOL REQUESTED]: {tool_name}({tool_args}) [User Role: '{self.role.value}']")

                    # Step 3: Check Role-Based Tool Permissions & Input Boundaries
                    perm_check: SafetyCheckResult = self.harness.check_tool_permission(
                        tool_name=tool_name,
                        arguments=tool_args,
                        current_role=self.role,
                    )

                    if not perm_check.is_safe:
                        self.log(f"[HARNESS PERMISSION BLOCKED]: {perm_check.reason}")
                        tool_result = f"Permission Error: {perm_check.reason}"
                    else:
                        self.log(f"[HARNESS PERMISSION GRANTED]: Executing '{tool_name}' for role '{self.role.value}'")
                        func = TOOL_FUNCTIONS.get(tool_name)
                        if func:
                            try:
                                tool_result = str(func(**tool_args))
                            except Exception as err:
                                tool_result = f"Error executing tool: {err}"
                        else:
                            tool_result = f"Error: Tool '{tool_name}' not found."

                    # Append tool result to context history
                    self.history.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_name,
                        "content": tool_result,
                    })

            if iterations >= max_iterations:
                self.log(f"[WARN]: Agent reached maximum allowed iteration limit ({max_iterations}). Stopping loop.")
                final_content = "Stopped: Agent loop reached maximum allowed tool-call iteration limit."

            # Step 4: Output Guardrail Check
            output_check: SafetyCheckResult = self.harness.check_output(final_content)
            if output_check.sanitized_input:
                final_content = output_check.sanitized_input

            self.history.append({"role": "assistant", "content": final_content})
            return final_content

        except Exception as e:
            self.log(f"[API ERROR]: {str(e)}")
            self.log("[FALLBACK]: Switching to local offline simulation mode...")
            if self.history and self.history[-1].get("role") == "user":
                last_user = self.history.pop().get("content", "")
            else:
                last_user = ""
            return self._run_local_fallback(last_user)

    def _run_local_fallback(self, user_input: str) -> str:
        """Local simulation mode for Course Advisor Agent when no API Key is set."""
        self.log(f"[OFFLINE MODE]: Processing request for role '{self.role.value}'")
        inp_lower = user_input.lower().strip()

        def extract_course_id(text: str) -> int:
            # Check for direct integer digits
            digit_match = re.search(r"\b(\d+)\b", text)
            if digit_match:
                try:
                    return int(digit_match.group(1))
                except ValueError:
                    pass
            # Check for course codes mapping
            code_map = {"CS101": 101, "CS202": 102, "AI301": 301, "MATH201": 201}
            for code, cid in code_map.items():
                if code.lower() in text.lower():
                    return cid
            return 101  # Default fallback ID

        # Multi-Step Tool Chaining Trigger: Search AND Check Schedule in sequence
        if any(kw in inp_lower for kw in ["find", "search"]) and any(kw in inp_lower for kw in ["schedule", "time", "meeting", "details"]):
            query = "CS"
            self.log(f"[STEP 1 ACTION]: search_course({{'query': '{query}'}})")
            perm1 = self.harness.check_tool_permission("search_course", {"query": query}, self.role)
            if perm1.is_safe:
                res1 = TOOL_FUNCTIONS["search_course"](query=query)
                self.log(f"[STEP 1 OBSERVATION]: Found courses. Selected course_id=101 for follow-up.")
                
                # Step 2: Use discovered course_id 101 to check schedule
                course_id = 101
                self.log(f"[STEP 2 ACTION]: check_schedule({{'course_id': {course_id}}})")
                perm2 = self.harness.check_tool_permission("check_schedule", {"course_id": course_id}, self.role)
                if perm2.is_safe:
                    res2 = TOOL_FUNCTIONS["check_schedule"](course_id=course_id)
                    reply = f"{res1}\n\n[CHAINED STEP 2 SCHEDULE RESULT]:\n{res2}"
                else:
                    reply = f"[SAFETY REFUSAL]: {perm2.reason}"
            else:
                reply = f"[SAFETY REFUSAL]: {perm1.reason}"

        # Single Tool 1 Trigger: search_course
        elif any(kw in inp_lower for kw in ["search", "find course", "list course", "course code", "what courses"]):
            query = re.sub(r"^(search|find|list|query)\s*(for|course|courses)?\s*", "", user_input, flags=re.IGNORECASE).strip()
            if not query:
                query = "CS"

            self.log(f"[TOOL REQUESTED]: search_course({{'query': '{query}'}})")
            perm_check = self.harness.check_tool_permission("search_course", {"query": query}, self.role)
            if perm_check.is_safe:
                res = TOOL_FUNCTIONS["search_course"](query=query)
                reply = res
            else:
                reply = f"[SAFETY REFUSAL]: {perm_check.reason}"

        # Single Tool 2 Trigger: check_schedule
        elif any(kw in inp_lower for kw in ["schedule", "time", "meeting", "status", "enrolled", "check"]):
            course_id = extract_course_id(user_input)

            self.log(f"[TOOL REQUESTED]: check_schedule({{'course_id': {course_id}}})")
            perm_check = self.harness.check_tool_permission("check_schedule", {"course_id": course_id}, self.role)
            if perm_check.is_safe:
                res = TOOL_FUNCTIONS["check_schedule"](course_id=course_id)
                reply = res
            else:
                reply = f"[SAFETY REFUSAL]: {perm_check.reason}"

        # Tool 3 Trigger: register_course (Admin action)
        elif any(kw in inp_lower for kw in ["register", "enroll", "add course"]):
            course_id = extract_course_id(user_input)
            # Optional student identifier after 'as'
            student_match = re.search(r"as\s+(\w+)", user_input, re.IGNORECASE)
            student_id = student_match.group(1).upper() if student_match else None

            # Build arguments dict dynamically
            tool_args = {"course_id": course_id}
            if student_id:
                tool_args["student_id"] = student_id

            self.log(f"[TOOL REQUESTED]: register_course({tool_args})")
            perm_check = self.harness.check_tool_permission("register_course", tool_args, self.role)
            if perm_check.is_safe:
                if student_id:
                    res = TOOL_FUNCTIONS["register_course"](course_id=course_id, student_id=student_id)
                else:
                    res = TOOL_FUNCTIONS["register_course"](course_id=course_id)
                reply = res
            else:
                reply = f"[SAFETY REFUSAL]: {perm_check.reason}"

        else:
            reply = (
                f"Course Advisor Agent (Role: {self.role.value.upper()}):\n"
                f"I processed your query: '{user_input}'.\n"
                f"Try asking:\n"
                f"  - 'Search for Introduction to Computer Science'\n"
                f"  - 'Check schedule for course ID 101'\n"
                f"  - 'Register course ID 101' (Requires Admin role)"
            )

        output_check = self.harness.check_output(reply)
        if output_check.sanitized_input:
            reply = output_check.sanitized_input

        self.history.append({"role": "assistant", "content": reply})
        return reply
