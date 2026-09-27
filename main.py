import sys
from schemas import Role
from agent import SafeAgent

# Set console encoding to UTF-8 on Windows if possible
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def print_banner(current_role: Role):
    banner = f"""
================================================================
          STUDENT ACADEMIC ADVISING ASSISTANT AGENT
================================================================
Active Role: [{current_role.value.upper()}]
----------------------------------------------------------------
Tools & Permission Rules:
  1. search_course(query: str)      : Search by title or code    [student, admin]
  2. check_schedule(course_id: int) : Timetable & details        [student, admin]
  3. register_course(course_id: int, student_id: str = "STD1001")    : Enroll a student into a course     [ADMIN ONLY]    : Unenroll active course     [ADMIN ONLY]
----------------------------------------------------------------
Commands:
  - 'role student' / 'role admin' : Switch active user role
  - 'help'                        : Show usage guide & details
  - 'clear'                       : Clear conversation history
  - 'history'                     : View conversation log
  - 'exit'                        : Quit application
================================================================
"""
    print(banner)


def show_help(current_role: Role):
    help_text = f"""
CURRENT ACTIVE ROLE: [{current_role.value.upper()}]

OPERATIONAL RULES & POLICIES:
  1. Grounded Execution: Always search_course first to discover IDs, then check_schedule for timetable.
  2. Tool Failure & Permissions: If PERMISSION_DENIED is returned, operation stops immediately.
  3. Input Boundaries: Ensure course IDs passed to check_schedule or drop_course are positive integers.

PERMISSION RULE APPLIED:
  - Role 'student': Can search courses & view schedules (search_course, check_schedule).
  - Role 'admin'  : Full permissions, including dropping courses (drop_course).

SAMPLE PROMPTS TO TEST:
  1. "Search for Introduction to Computer Science"
  2. "Check schedule for course ID 101"
  3. "Register course ID 101"  (Will be BLOCKED for 'student', APPROVED for 'admin')

TO SWITCH ROLE:
  Type 'role admin' or 'role student'
"""
    print(help_text)


def main():
    agent = SafeAgent(role=Role.STUDENT)
    print_banner(agent.role)

    print(f"Course Advisor Agent Ready. Current Role: [{agent.role.value.upper()}]\n")

    while True:
        try:
            prompt_label = f"You ({agent.role.value}) > "
            user_input = input(prompt_label).strip()
            if not user_input:
                continue

            cmd_lower = user_input.lower().strip()

            # Command: exit / quit
            if cmd_lower in ["exit", "quit"]:
                print("Goodbye!")
                sys.exit(0)

            # Command: help
            elif cmd_lower == "help":
                show_help(agent.role)
                continue

            # Command: role switch
            elif cmd_lower.startswith("role"):
                parts = cmd_lower.split()
                if len(parts) >= 2 and parts[1] in ["admin", "student"]:
                    new_role = Role.ADMIN if parts[1] == "admin" else Role.STUDENT
                    agent.set_role(new_role)
                    print(f"[ROLE UPDATED]: Active role is now [{agent.role.value.upper()}]\n")
                else:
                    print("Usage: 'role student' or 'role admin'\n")
                continue

            # Command: clear
            elif cmd_lower == "clear":
                agent.history = [{"role": "system", "content": agent.SYSTEM_PROMPT}]
                print("[CLEARED] Conversation history reset.\n")
                continue

            # Command: history
            elif cmd_lower == "history":
                print("\n--- Conversation History ---")
                for msg in agent.history:
                    print(f"[{msg.get('role').upper()}]: {msg.get('content') or msg.get('tool_calls')}")
                print("----------------------------\n")
                continue

            print("\n------------------------------------------------")
            response = agent.process_input(user_input)
            print(f"\nAgent > {response}")
            print("------------------------------------------------\n")

        except KeyboardInterrupt:
            print("\nExiting... Goodbye!")
            sys.exit(0)
        except Exception as e:
            print(f"\n[ERROR] Unexpected Error: {e}\n")


if __name__ == "__main__":
    main()
