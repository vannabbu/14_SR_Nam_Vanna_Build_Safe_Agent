from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Role(str, Enum):
    STUDENT = "student"
    ADMIN = "admin"


class SafetyLevel(str, Enum):
    SAFE = "SAFE"
    SUSPICIOUS = "SUSPICIOUS"
    BLOCKED = "BLOCKED"


class SafetyCheckResult(BaseModel):
    is_safe: bool = Field(..., description="Whether the check passed")
    level: SafetyLevel = Field(default=SafetyLevel.SAFE, description="Safety level assessment")
    reason: str = Field(default="Allowed", description="Reason for safety determination")
    sanitized_input: Optional[str] = Field(None, description="Sanitized text if modified")


class CourseInfo(BaseModel):
    course_id: int = Field(..., description="Unique positive integer ID for the course")
    course_code: str
    course_name: str
    instructor: str
    credits: int
    description: str


class ScheduleInfo(BaseModel):
    course_id: int = Field(..., description="Unique positive integer ID for the course")
    course_code: str
    course_name: str
    meeting_days: str
    time_slot: str
    room: str
    enrolled_count: int
    capacity: int
    status: str


# =====================================================================
# Tool Input Schemas (Pydantic Models)
# =====================================================================

class SearchCourseArgs(BaseModel):
    """Schema describing inputs for the search_course tool."""
    query: str = Field(
        ...,
        description="Course code (e.g. 'CS101') or keyword (e.g. 'Computer Science', 'AI')"
    )


class CheckScheduleArgs(BaseModel):
    """Schema describing inputs for the check_schedule tool."""
    course_id: int = Field(
        ...,
        gt=0,
        description="Course ID to inspect timetable and schedule (must be a positive integer, e.g. 101, 102, 301)"
    )



class RegisterCourseArgs(BaseModel):
    """Schema describing inputs for the register_course tool."""
    course_id: int = Field(
        ..., gt=0, description="Course ID to register/enroll (must be a positive integer, e.g. 101)"
    )
    student_id: str = Field(
        default="STD1001",
        description="Student ID (defaults to 'STD1001')"
    )
