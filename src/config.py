from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Directory where cookies, MSAL tokens, and ITESO session data are stored
USER_DATA_DIR = BASE_DIR / "user_data"
USER_DATA_DIR.mkdir(exist_ok=True)

# Microsoft Bookings URL for ITESO sports bookings portal
SPORTS_BOOKINGS_URL = "https://bookings.cloud.microsoft/book/RESERVADEINSTALACIONESDEPORTIVASEFSIITESO@iteso.mx/?ismsaljsauthenabled=true"

# ITESO Smartway2book URL for library bookings (study cubicles, meeting spaces)
LIBRARY_BOOKING_URL = "https://iteso.smartway2book.com/se/#/book"

# ITESO WebCheckout URL for departmental materials, equipment, and specialized spaces
DEPARTMENTS_BOOKING_URL = "https://iteso.webcheckout.net/sso/patron#!/"

# Default student information
DEFAULT_STUDENT_NAME = os.getenv("STUDENT_NAME", "")
DEFAULT_STUDENT_EMAIL = os.getenv("STUDENT_EMAIL", "")
DEFAULT_STUDENT_ID = os.getenv("STUDENT_ID", os.getenv("STUDENT_EXPEDIENTE", ""))
DEFAULT_STUDENT_PHONE = os.getenv("STUDENT_PHONE", "")

class StudentInfo:
    """
    Represents a student's personal information required for booking.
    """

    def __init__(
        self,
        name: str,
        email: str,
        student_id: str,
        phone: str = "",
    ) -> None:
        self.name = name
        self.email = email
        self.student_id = student_id
        self.phone = phone

student = StudentInfo(
    name=DEFAULT_STUDENT_NAME,
    email=DEFAULT_STUDENT_EMAIL,
    student_id=DEFAULT_STUDENT_ID,
    phone=DEFAULT_STUDENT_PHONE,
)
