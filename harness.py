import re
from typing import Dict, Any, List
from schemas import SafetyCheckResult, SafetyLevel, Role


class SafetyHarness:
    """Safety Harness enforcing Role-Based Access Control (RBAC) and Guardrails for Course Advisor Agent."""

    # Role Permission Mapping:
    # Role 'student': Can search courses and view schedules (search_course, check_schedule).
    # Role 'admin': Full permissions, including registering courses (register_course).
    ROLE_PERMISSIONS: Dict[Role, List[str]] = {
        Role.STUDENT: ["search_course", "check_schedule"],
        Role.ADMIN: ["search_course", "check_schedule", "register_course"],
    }

    # Forbidden prompt injection / role spoofing attempts
    PROMPT_INJECTION_PATTERNS = [
        r"ignore (all )?previous instructions",
        r"disregard (all )?prior rules",
        r"you are now (an )?admin",
        r"override my role",
        r"grant me admin",
        r"system override",
        r"bypass (safety|permissions|guardrails)",
        r"reveal (your |the )system prompt",
    ]

    # Sensitive patterns to prevent leaks in responses
    SENSITIVE_PATTERNS = [
        r"sk-[a-zA-Z0-9]{20,}",  # OpenAI API Keys
        r"SSN-\d{3}-\d{2}-\d{4}",  # Social security numbers
    ]

    def check_input(self, user_input: str, current_role: Role) -> SafetyCheckResult:
        """Validate user input against prompt injection and role spoofing attempts."""
        if not user_input or not user_input.strip():
            return SafetyCheckResult(is_safe=False, level=SafetyLevel.BLOCKED, reason="Input cannot be empty.")

        # Check for prompt injection or role elevation attempts
        for pattern in self.PROMPT_INJECTION_PATTERNS:
            if re.search(pattern, user_input, re.IGNORECASE):
                return SafetyCheckResult(
                    is_safe=False,
                    level=SafetyLevel.BLOCKED,
                    reason=f"Blocked by input safety harness: Detected prompt injection or role-elevation attempt ('{pattern}')."
                )

        return SafetyCheckResult(is_safe=True, level=SafetyLevel.SAFE, reason="User input passed safety checks.")

    def check_tool_permission(self, tool_name: str, arguments: Dict[str, Any], current_role: Role) -> SafetyCheckResult:
        """Enforce Permission Rules and Input Boundaries for tool execution based on user role."""
        allowed_tools = self.ROLE_PERMISSIONS.get(current_role, [])

        # Permission check: Is the tool allowed for current_role?
        if tool_name not in allowed_tools:
            return SafetyCheckResult(
                is_safe=False,
                level=SafetyLevel.BLOCKED,
                reason=(
                    f"PERMISSION_DENIED: Role '{current_role.value}' is NOT authorized to execute tool '{tool_name}'. "
                    f"Action 'register_course' requires 'admin' role permissions."
                )
            )

        # Input Boundaries Check: Ensure course_id is a positive integer for check_schedule & register_course
        if tool_name in ["check_schedule", "register_course"]:
            course_id = arguments.get("course_id")
            try:
                cid_int = int(course_id)
                if cid_int <= 0:
                    return SafetyCheckResult(
                        is_safe=False,
                        level=SafetyLevel.BLOCKED,
                        reason=f"INPUT BOUNDARY ERROR: course_id must be a positive integer (received {course_id})."
                    )
            except (ValueError, TypeError):
                return SafetyCheckResult(
                    is_safe=False,
                    level=SafetyLevel.BLOCKED,
                    reason=f"INPUT BOUNDARY ERROR: course_id must be a positive integer (received {course_id})."
                )

        return SafetyCheckResult(
            is_safe=True,
            level=SafetyLevel.SAFE,
            reason=f"Permission granted: Role '{current_role.value}' is authorized to execute '{tool_name}'."
        )

    def check_output(self, model_output: str) -> SafetyCheckResult:
        """Validate agent model response to prevent data leaks."""
        if not model_output:
            return SafetyCheckResult(is_safe=True, level=SafetyLevel.SAFE, reason="Empty output.")

        for pattern in self.SENSITIVE_PATTERNS:
            if re.search(pattern, model_output):
                sanitized = re.sub(pattern, "[REDACTED]", model_output)
                return SafetyCheckResult(
                    is_safe=True,
                    level=SafetyLevel.SUSPICIOUS,
                    reason="Sensitive key/data detected in output and redacted.",
                    sanitized_input=sanitized
                )

        return SafetyCheckResult(is_safe=True, level=SafetyLevel.SAFE, reason="Output passed safety check.")
