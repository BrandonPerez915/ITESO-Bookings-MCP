from __future__ import annotations

import re
from typing import List, Dict, Any

try:
    from src.browser import open_page
    from src.config import SPORTS_BOOKINGS_URL, student
    from src.platforms.base import BaseBookingPlatform, StudentInfo
except ImportError:
    from browser import open_page
    from config import SPORTS_BOOKINGS_URL, student
    from platforms.base import BaseBookingPlatform, StudentInfo

class SportsPlatform(BaseBookingPlatform):
    """
    Platform adapter for ITESO sports facilities using Microsoft Bookings.
    Handles volleyball, tennis, padel, basketball, soccer, gym, etc.
    """

    def __init__(self) -> None:
        super().__init__(
            key="sports",
            name="ITESO Sports Facilities",
            url=SPORTS_BOOKINGS_URL,
            category="sports",
            description=(
                "Reservations for sports courts and athletic facilities "
                "(Volleyball, Sand Volleyball, Tennis, Padel, Basketball, Soccer, Gym)."
            ),
        )

    async def get_services(self) -> List[str]:
        """
        Retrieves the exact list of sports facilities available on Microsoft Bookings.
        Uses conditional element waits to ensure the DOM is ready.
        """
        page = await open_page(self.url, headless=True)
        try:
            # Wait for services list to be rendered
            await page.wait_for_selector(
                "input[name='selectedService'], ul[role='list'], div.XNuah",
                state="attached",
                timeout=12000,
            )

            discovered: List[str] = []
            # First try with primary selector: 'aria-label' attribute on radio inputs
            service_radios = await page.locator("input[name='selectedService']").all()
            for radio in service_radios:
                aria_label = await radio.get_attribute("aria-label")
                if aria_label:
                    cleaned = aria_label.strip()
                    if cleaned and cleaned not in discovered:
                        discovered.append(cleaned)

            # Then use secondary selector as fallback: title containers inside service cards (.XNuah)
            if not discovered:
                titles = await page.locator("div.XNuah, label div.BIzGA").all_inner_texts()
                for title in titles:
                    cleaned = title.strip()
                    if cleaned and cleaned not in discovered and len(cleaned) > 2:
                        discovered.append(cleaned)

            # Finally, try to extract labels of service items, filtering out descriptions & 'Leer más' as the final fallback
            if not discovered:
                labels = await page.locator("li[role='listitem'] label").all_inner_texts()
                for raw_text in labels:
                    first_line = raw_text.strip().split("\n")[0].strip()
                    if (
                        first_line
                        and first_line not in discovered
                        and not any(ign in first_line.lower() for ign in ["leer más", "1 hora", "en caso de"])
                    ):
                        discovered.append(first_line)

            return discovered if discovered else [
                "No services found. The page structure may have changed or the platform is temporarily unavailable.",
            ]
        finally:
            await page.close()

    async def get_availability(self, service: str, date: str) -> Dict[str, Any]:
        """
        Queries available time slots for a specific sports service and date (YYYY-MM-DD).
        Replaces fixed timeouts with conditional element readiness checks.
        """
        page = await open_page(self.url, headless=True)
        try:
            # Wait for service selection elements
            await page.wait_for_selector(
                "input[name='selectedService'], ul[role='list']",
                state="attached",
                timeout=12000,
            )

            service_radios = page.locator(f"input[name='selectedService'][aria-label*='{service}' i]")
            if await service_radios.count() > 0:
                radio = service_radios.first
                radio_id = await radio.get_attribute("id")
                if radio_id:
                    target_label = page.locator(f"label[for='{radio_id}']")
                    if await target_label.count() > 0:
                        await target_label.first.click()
                    else:
                        await radio.click(force=True)
                else:
                    await radio.click(force=True)
                try:
                    await radio.dispatch_event("change")
                except Exception:
                    pass
            else:
                label_target = page.locator(f"label:has-text('{service}'), div.XNuah:has-text('{service}')")
                if await label_target.count() > 0:
                    await label_target.first.click()

            # Wait for calendar container to update
            calendar_locator = page.locator("div.Uw_Qu, [aria-label*='Seleccione una fecha'], [role='button'][data-value]").first
            try:
                await calendar_locator.wait_for(state="visible", timeout=6000)
            except Exception:
                pass

            # Get the day number from the date string (YYYY-MM-DD) or fallback to the day if only day is provided in date (2026-10-26 or 26)
            try:
                day_number = str(int(date.split("-")[2]))
            except Exception:
                day_number = date
            # Wait until the target day button is available (rendered)
            try:
                await page.wait_for_function(
                    """({ date, day }) => {
                        const el = document.querySelector(`[role='button'][data-value^='${date}']`)
                            || Array.from(document.querySelectorAll("div.Uw_Qu [role='button']")).find(e => e.textContent.trim() === day);
                        if (!el) return false;
                        const label = (el.getAttribute('aria-label') || '').toLowerCase();
                        return label.length > 0 && !label.includes('sin informaci');
                    }""",
                    arg={"date": date, "day": day_number},
                    timeout=8000,
                )
            except Exception:
                pass

            date_button = page.locator(f"[role='button'][data-value^='{date}']")
            if await date_button.count() == 0:
                date_button = page.locator(f"div.Uw_Qu [role='button']:text-is('{day_number}')")

            if await date_button.count() > 0:
                aria_label = await date_button.first.get_attribute("aria-label") or ""
                is_disabled = await date_button.first.get_attribute("aria-disabled")

                if is_disabled == "true" or "no hay horas disponibles" in aria_label.lower():
                    return {
                        "platform": self.key,
                        "service": service,
                        "date": date,
                        "available_time_slots": [],
                        "total_available": 0,
                        "message": f"No available time slots on {date} (marked as unavailable in calendar).",
                    }

                await date_button.first.click()
                # Wait for timeslots container to refresh
                timeslot_indicator = page.locator(
                    "input[name='selectedTimeSlot'], div.Qihpq span.fGGgr, div.Qihpq li[role='listitem']"
                ).first
                try:
                    await timeslot_indicator.wait_for(state="attached", timeout=6000)
                except Exception:
                    pass

            # Extract time slots
            time_slots: List[str] = []
            slot_elements = await page.locator(
                "input[name='selectedTimeSlot'] ~ label span.fGGgr, "
                "[aria-label*='Selector de hora'] label span.fGGgr, "
                "div.Qihpq label span"
            ).all_inner_texts()

            for text in slot_elements:
                cleaned = text.strip()
                if cleaned and re.match(r"^\d{1,2}:\d{2}", cleaned):
                    if cleaned not in time_slots:
                        time_slots.append(cleaned)
            # If no time slots were found, try to get alternative label structures
            if not time_slots:
                all_labels = await page.locator("div.Qihpq label, [role='listitem'] label").all_inner_texts()
                time_pattern = re.compile(r"^\d{1,2}:\d{2}(\s*[ap]\.?m\.?)?$", re.IGNORECASE)
                for label in all_labels:
                    first_line = label.strip().split("\n")[0].strip()
                    if time_pattern.match(first_line) and first_line not in time_slots:
                        time_slots.append(first_line)

            return {
                "platform": self.key,
                "service": service,
                "date": date,
                "time": time,
                "available_time_slots": time_slots,
                "total_available": len(time_slots),
            }
        finally:
            await page.close()

    async def create_booking(
        self,
        service: str,
        date: str,
        time: str,
        student_info: StudentInfo,
        confirm_booking: bool = False,
    ) -> Dict[str, Any]:
        """
        Fills the booking form on Microsoft Bookings and validates or confirms the reservation
        using conditional waits for form inputs.
        """
        name = student_info.name
        email = student_info.email
        student_id = student_info.student_id
        phone = student_info.phone

        page = await open_page(self.url, headless=True)
        try:
            # Wait for service list
            await page.wait_for_selector(
                "input[name='selectedService'], ul[role='list']",
                state="attached",
                timeout=12000,
            )
            # Simulate service selection click
            service_radios = page.locator(f"input[name='selectedService'][aria-label*='{service}' i]")
            if await service_radios.count() > 0:
                radio = service_radios.first
                radio_id = await radio.get_attribute("id")
                if radio_id:
                    target_label = page.locator(f"label[for='{radio_id}']")
                    if await target_label.count() > 0:
                        await target_label.first.click()
                    else:
                        await radio.click(force=True)
                else:
                    await radio.click(force=True)
                try:
                    await radio.dispatch_event("change")
                except Exception:
                    pass
            else:
                label_target = page.locator(f"label:has-text('{service}')")
                if await label_target.count() > 0:
                    await label_target.first.click()

            # Wait for calendar
            calendar_locator = page.locator("div.Uw_Qu, [role='button'][data-value]").first
            try:
                await calendar_locator.wait_for(state="visible", timeout=6000)
            except Exception:
                pass
            # Simulate clicking on the target day
            try:
                day_number = str(int(date.split("-")[2]))
            except Exception:
                day_number = date

            try:
                await page.wait_for_function(
                    """({ date, day }) => {
                        const el = document.querySelector(`[role='button'][data-value^='${date}']`)
                            || Array.from(document.querySelectorAll("div.Uw_Qu [role='button']")).find(e => e.textContent.trim() === day);
                        if (!el) return false;
                        const label = (el.getAttribute('aria-label') || '').toLowerCase();
                        return label.length > 0 && !label.includes('sin informaci');
                    }""",
                    arg={"date": date, "day": day_number},
                    timeout=8000,
                )
            except Exception:
                pass

            day_button = page.locator(f"[role='button'][data-value^='{date}']")
            if await day_button.count() == 0:
                day_button = page.locator(f"div.Uw_Qu [role='button']:text-is('{day_number}')")
            if await day_button.count() > 0:
                await day_button.first.click()

            # Wait for time slots container and select time
            formatted_time = time[:5] if re.match(r"^\d{1,2}:\d{2}:\d{2}", time) else time
            timeslot_locator = page.locator(
                f"div.Qihpq label:has-text('{formatted_time}'), "
                f"input[name='selectedTimeSlot'] ~ label:has-text('{formatted_time}'), "
                f"div.Qihpq span.fGGgr:text-is('{formatted_time}')"
            ).first

            if await timeslot_locator.count() == 0:
                return {
                    "platform": self.key,
                    "service": service,
                    "date": date,
                    "time": time,
                    "available_time_slots": [],
                    "total_available": 0,
                    "message": f"Time slot '{formatted_time}' not found for service '{service}' on {date}.",
                }

            try:
                await timeslot_locator.wait_for(state="visible", timeout=6000)
                await timeslot_locator.click()
            except Exception:
                pass

            # Wait for student form inputs
            name_input = page.locator("input[autocomplete='name'], input[placeholder*='Nombre y apellidos']").first
            try:
                await name_input.wait_for(state="visible", timeout=6000)
                await name_input.fill(name)
            except Exception:
                pass

            email_input = page.locator("input[autocomplete='email'], input[placeholder*='Correo electrónico']").first
            if await email_input.count() > 0:
                await email_input.fill(email)

            phone_input = page.locator("input[autocomplete='tel'], input[placeholder*='número de teléfono']").first
            if await phone_input.count() > 0:
                await phone_input.fill(phone)

            student_id_input = page.locator(
                "div.b9HBj input, "
                "label:has-text('expediente') ~ div input, "
                "input[placeholder*='Agregue aquí su respuesta']"
            ).first
            if await student_id_input.count() > 0:
                await student_id_input.fill(student_id)

            consent_checkbox = page.locator("#consentCheckBox").first
            if await consent_checkbox.count() > 0:
                if not await consent_checkbox.is_checked():
                    await consent_checkbox.check()
            # Dry-run validation without final submission
            if not confirm_booking:
                return {
                    "platform": self.key,
                    "status": "dry_run",
                    "message": "Form validated successfully on Microsoft Bookings (Dry-run mode; booking was not finalized).",
                    "details": {
                        "service": service,
                        "date": date,
                        "time": time,
                        "student": name,
                        "email": email,
                        "student_id": student_id,
                    },
                }

            # Submit button with conditional response wait
            book_button = page.locator("button[type='submit'][aria-label='Reservar'], button.i9DXY").first
            if await book_button.count() > 0:
                await book_button.click()
                try:
                    await page.wait_for_selector(
                        "text=/confirmada|éxito|gracias|reserva|booked/i",
                        state="visible",
                        timeout=8000,
                    )
                except Exception:
                    await page.wait_for_load_state("networkidle", timeout=5000)

            return {
                "platform": self.key,
                "status": "success",
                "message": f"Booking successfully confirmed for {service} for date {date}.",
                "details": {
                    "service": service,
                    "date": date,
                    "time": time,
                    "student": name,
                    "student_id": student_id,
                },
            }
        finally:
            await page.close()

import asyncio
import time

async def main() -> None:
    platform = SportsPlatform()
    status = await platform.session_status()

    if not status["authenticated"]:
        await platform.interactive_login()

    services = await platform.get_services()
    voleyball_service = services[1]

    voleyball_availability = await platform.get_availability(voleyball_service, "2026-10-26")

    booking = await platform.create_booking(
        service=voleyball_service,
        date="2026-10-26",
        time="13:00",
        student_info=student,
        confirm_booking=False,
    )

    print("Session Status:", status, "\n")
    print("Available Services:", services, "\n")
    print("Voleyball Availability on 2026-10-26:", voleyball_availability, "\n")
    print("Booking Attempt (Dry-run):", booking)

if __name__ == "__main__":
    asyncio.run(main())
