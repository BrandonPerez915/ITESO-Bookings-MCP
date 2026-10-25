from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import List, Dict, Any

try:
    from src.browser import open_page, close_browser_context
    from src.config import StudentInfo
except ImportError:
    from browser import open_page, close_browser_context

class BaseBookingPlatform(ABC):
    """
    Abstract base class for all ITESO reservation platforms.
    Every platform (Sports Bookings, Library Smartway, Department WebCheckout, etc.)
    inherits from this class and implements a unified interface.
    """

    key: str
    name: str
    url: str
    category: str
    description: str

    def __init__(
        self,
        key: str,
        name: str,
        url: str,
        category: str,
        description: str,
    ) -> None:
        self.key = key
        self.name = name
        self.url = url
        self.category = category
        self.description = description

    async def interactive_login(self) -> Dict[str, Any]:
        """
        Opens the platform in a headed browser window so the user can complete
        interactive ITESO SSO / MFA login.
        """
        await close_browser_context()
        await open_page(self.url, headless=False)
        return {
            "status": "waiting_user_login",
            "platform": self.key,
            "message": (
                f"Browser window opened for {self.name} ({self.url}). "
                "Log in with your ITESO account (@iteso.mx) and approve multi-factor authentication (MFA). "
                "Once the portal loads your account, you can close the window."
            ),
        }

    async def session_status(self) -> Dict[str, Any]:
        """
        Verifies whether the session on this platform is active or expired
        """
        page = await open_page(self.url, headless=True)
        try:
            # Wait for either an auth redirect or for the initial document to load
            try:
                await page.wait_for_url(
                    re.compile(r"login\.microsoftonline\.com|adfs|saml", re.IGNORECASE),
                    timeout=3000,
                )
            except Exception:
                await page.wait_for_load_state("domcontentloaded")

            current_url = page.url
            if any(login_host in current_url for login_host in ["login.microsoftonline.com", "adfs", "saml"]):
                return {
                    "platform": self.key,
                    "authenticated": False,
                    "message": f"Session expired or not authenticated on {self.name}. Please run interactive login.",
                }
            return {
                "platform": self.key,
                "authenticated": True,
                "message": f"Active session verified on {self.name}.",
            }
        finally:
            await page.close()

    @abstractmethod
    async def get_services(self) -> List[str]:
        """
        Returns the list of bookable services, rooms, or items on this platform.
        """
        pass

    @abstractmethod
    async def get_availability(self, service: str, date: str) -> Dict[str, Any]:
        """
        Queries available time slots or windows for the given resource and date.
        """
        pass

    @abstractmethod
    async def create_booking(
        self,
        service: str,
        date: str,
        time: str,
        student_info: StudentInfo,
        confirm_booking: bool = False,
    ) -> Dict[str, Any]:
        """
        Fills out the reservation form. If confirm_booking is False, performs a dry-run validation.
        """
        pass
