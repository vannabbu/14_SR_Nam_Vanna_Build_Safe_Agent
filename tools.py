from typing import Dict, Any, Callable, List
from schemas import SearchCourseArgs, CheckScheduleArgs, RegisterCourseArgs

# Simulated Course Database
COURSES_DB = {
    101: {
        "course_id": 101,
        "course_code": "CS101",
        "course_name": "Introduction to Computer Science",
        "instructor": "Dr. Alan Turing",
        "credits": 3,
        "description": "Foundational programming concepts, algorithms, and computational thinking.",
        "meeting_days": "Mon / Wed",
        "time_slot": "09:00 AM - 10:30 AM",
        "room": "Lab 301",
        "enrolled_count": 28,
        "capacity": 30,
        "status": "Open",
    },
    102: {
        "course_id": 102,
        "course_code": "CS202",
        "course_name": "Data Structures and Algorithms",
        "instructor": "Dr. Grace Hopper",
        "credits": 4,
        "description": "Arrays, linked lists, trees, graphs, sorting, and algorithmic complexity.",
        "meeting_days": "Tue / Thu",
        "time_slot": "11:00 AM - 12:30 PM",
        "room": "Auditorium A",
        "enrolled_count": 30,
        "capacity": 30,
        "status": "Full",
    },
    301: {
        "course_id": 301,
        "course_code": "AI301",
        "course_name": "Artificial Intelligence & Safe Agents",
        "instructor": "Prof. Geoffrey Hinton",
        "credits": 3,
        "description": "LLM agents, tool usage, safety harness, and alignment principles.",
        "meeting_days": "Fri",
        "time_slot": "01:30 PM - 04:30 PM",
        "room": "AI Center 102",
        "enrolled_count": 15,
        "capacity": 25,
        "status": "Open",
    },
    201: {
        "course_id": 201,
        "course_code": "MATH201",
        "course_name": "Linear Algebra & Calculus",
        "instructor": "Dr. Carl Gauss",
        "credits": 3,
        "description": "Matrices, vector spaces, eigenvalues, derivatives, and integration.",
        "meeting_days": "Mon / Wed",
        "time_slot": "02:00 PM - 03:30 PM",
        "room": "Math Bldg 204",
        "enrolled_count": 22,
        "capacity": 35,
        "status": "Open",
    },
}

# Simulated Student Enrollment Records
ENROLLMENT_DB = {
    "STD1001": [101, 301],
    "STD1002": [101, 201],
    "STD1003": [102, 301],
    "STD1004": [],
    "STD1005": [],
}

def add_student(student_id: str, course_ids: List[int]) -> str:
    """Add a new student with a list of enrolled course IDs.

    Args:
        student_id: Identifier for the student (e.g., "STD1003").
        course_ids: List of integer course IDs the student should be enrolled in.

    Returns:
        A status string indicating success or any errors.
    """
    std_clean = student_id.upper().strip()
    if std_clean in ENROLLMENT_DB:
        return f"Error: Student '{std_clean}' already exists."
    # Validate each course ID exists
    for cid in course_ids:
        if cid not in COURSES_DB:
            return f"Error: Course ID {cid} does not exist. Cannot enroll student in nonexistent course."
    ENROLLMENT_DB[std_clean] = []
    # Enroll in each validated course and update enrollment counts
    for cid in course_ids:
        ENROLLMENT_DB[std_clean].append(cid)
        COURSES_DB[cid]["enrolled_count"] += 1
        if COURSES_DB[cid]["enrolled_count"] >= COURSES_DB[cid]["capacity"]:
            COURSES_DB[cid]["status"] = "Full"
    return f"SUCCESS: Student '{std_clean}' added and enrolled in courses {course_ids}."


# Tool 1: search_course
def search_course(query: str) -> str:
    """Searches for courses by title or course code (e.g., 'AI', 'CS101')."""
    query_clean = str(query).upper().strip()
    query_lower = str(query).lower().strip()

    # Handle generic queries like 'available courses', 'all', 'list', 'courses'
    if not query_clean or any(kw == query_lower for kw in ["all", "courses", "available", "available courses", "list", "list courses"]):
        matches = [
            f"- ID: {info['course_id']} | Code: {info['course_code']} | Name: {info['course_name']} | Instructor: {info['instructor']} | Credits: {info['credits']}"
            for cid, info in COURSES_DB.items()
        ]
        return "Found available courses:\n" + "\n".join(matches)

    matches = []
    for cid, info in COURSES_DB.items():
        if (
            query_clean in info["course_code"].upper()
            or query_clean in str(cid)
            or query_lower in info["course_name"].lower()
            or query_lower in info["description"].lower()
        ):
            matches.append(
                f"- ID: {info['course_id']} | Code: {info['course_code']} | Name: {info['course_name']} | Instructor: {info['instructor']} | Credits: {info['credits']}"
            )

    if matches:
        return "Found matching courses:\n" + "\n".join(matches)
    else:
        available_ids = ", ".join([f"{cid} ({info['course_code']})" for cid, info in COURSES_DB.items()])
        return f"No courses found matching query '{query}'. Available course IDs: {available_ids}"


# Tool 2: check_schedule
def check_schedule(course_id: int) -> str:
    """Retrieves timetable, meeting hours, and details for a specific course ID (must be a positive integer)."""
    try:
        cid = int(course_id)
    except (ValueError, TypeError):
        return f"Error: course_id must be a positive integer. Provided value: {course_id}"

    if cid <= 0:
        return f"Error: course_id must be a positive integer (received {cid})."

    if cid not in COURSES_DB:
        available_ids = ", ".join([f"{c} ({info['course_code']})" for c, info in COURSES_DB.items()])
        return f"Course ID '{cid}' not found. Available course IDs: {available_ids}"

    info = COURSES_DB[cid]
    return (
        f"Schedule & Enrollment Info for Course ID [{info['course_id']}] ({info['course_code']} - {info['course_name']}):\n"
        f"- Meeting Days: {info['meeting_days']}\n"
        f"- Time Slot: {info['time_slot']}\n"
        f"- Room: {info['room']}\n"
        f"- Enrolled: {info['enrolled_count']} / {info['capacity']}\n"
        f"- Status: {info['status']}"
    )


# Tool 3: register_course (Admin action)
def register_course(course_id: int, student_id: str = "STD1001") -> str:
    """Enrolls a student into an existing course (admin action)."""
    try:
        cid = int(course_id)
    except (ValueError, TypeError):
        return f"Error: course_id must be a positive integer. Provided value: {course_id}"

    if cid <= 0:
        return f"Error: course_id must be a positive integer (received {cid})."

    std_clean = str(student_id).upper().strip()

    if cid not in COURSES_DB:
        return f"Error: Course ID '{cid}' does not exist."

    # Ensure student record exists
    if std_clean not in ENROLLMENT_DB:
        ENROLLMENT_DB[std_clean] = []

    student_courses = ENROLLMENT_DB[std_clean]
    if cid in student_courses:
        return f"Notice: Student '{std_clean}' is already enrolled in Course ID '{cid}' ({COURSES_DB[cid]['course_code']})."

    # Check capacity before enrolling
    if COURSES_DB[cid]["enrolled_count"] >= COURSES_DB[cid]["capacity"]:
        return f"Notice: Course '{COURSES_DB[cid]['course_code']}' is full. Cannot enroll additional students."
    student_courses.append(cid)
    COURSES_DB[cid]["enrolled_count"] += 1
    # Update status
    if COURSES_DB[cid]["enrolled_count"] >= COURSES_DB[cid]["capacity"]:
        COURSES_DB[cid]["status"] = "Full"
    else:
        COURSES_DB[cid]["status"] = "Open"
    return f"SUCCESS: Student '{std_clean}' has been successfully enrolled in Course ID '{cid}' ({COURSES_DB[cid]['course_code']})."


# Tool registry map
TOOL_FUNCTIONS: Dict[str, Callable] = {
    "search_course": search_course,
    "check_schedule": check_schedule,
    "register_course": register_course,
}


# OpenAI tool schema definitions (generated from Pydantic models)
OPENAI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_course",
            "description": "Searches for courses by title or course code (e.g., 'AI', 'CS101'). Returns course details including course_id.",
            "parameters": SearchCourseArgs.model_json_schema(),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_schedule",
            "description": "Retrieves timetable, meeting hours, and details for a specific course ID (must be a positive integer).",
            "parameters": CheckScheduleArgs.model_json_schema(),
        },
    },
    {
        "type": "function",
        "function": {
            "name": "register_course",
            "description": "Enrolls a student into a course (admin action).",
            "parameters": RegisterCourseArgs.model_json_schema(),
        },
    },
]
