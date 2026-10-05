"""Stage 1 Tablekeeper HTTP behavior, implemented on the existing state store."""

from __future__ import annotations

import asyncio
import copy
import json
import os
import re
import secrets
import uuid
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from urllib.parse import parse_qs, unquote, urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .domain import DomainError
from .security import hash_password, is_valid_password_hash, issue_token, verify_password
from .state import ServiceState, StateStore
from .time_rules import resolve_local, rfc3339
from .validation import canonical_json

UTC = timezone.utc
WEEKDAYS = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
REFERENCE_RE = re.compile(r"^[A-Z0-9]{6,12}$")
LOCAL_DATETIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIME_RE = re.compile(r"^\d{2}:\d{2}$")
DECIMAL_RE = re.compile(r"^[0-9]+$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+$")
REFERENCE_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
MISSING = object()


@dataclass(frozen=True)
class ApiResponse:
    status: int
    body: Any = None
    content_type: str = "application/json; charset=utf-8"


def _error(status: int, code: str, message: str) -> DomainError:
    return DomainError(status, code, message)


def _invalid(message: str = "validation failed") -> DomainError:
    return _error(422, "validation_failed", message)


def _not_found() -> DomainError:
    return _error(404, "not_found", "not found")


def _require_object(value: Any, *, missing_is_malformed: bool = True) -> dict[str, Any]:
    if value is None and missing_is_malformed:
        raise _error(400, "malformed_request", "request body must be a JSON object")
    if not isinstance(value, dict):
        raise _error(400, "malformed_request", "request body must be a JSON object")
    return value


def _required_string(value: dict[str, Any], name: str) -> str:
    if name not in value:
        raise _invalid(f"{name} is required")
    field = value[name]
    if not isinstance(field, str):
        raise _error(400, "malformed_request", f"{name} must be a string")
    return field


def _required_id(value: dict[str, Any], name: str) -> str:
    result = _required_string(value, name)
    if not result or len(result) > 64:
        raise _invalid(f"{name} must contain 1 to 64 characters")
    return result


def _party_size(value: dict[str, Any], *, required: bool = True, default: int | None = None) -> int:
    if "party_size" not in value:
        if required:
            raise _invalid("party_size is required")
        assert default is not None
        return default
    result = value["party_size"]
    # This field has a specific Stage 1 rule: even a string or boolean is 422.
    if isinstance(result, bool) or not isinstance(result, int) or result < 1:
        raise _invalid("party_size must be a positive integer")
    return result


def _parse_local(value: Any) -> datetime:
    if not isinstance(value, str):
        raise _error(400, "malformed_request", "starts_at_local must be a string")
    if not LOCAL_DATETIME_RE.fullmatch(value):
        raise _invalid("starts_at_local must be YYYY-MM-DDTHH:MM")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M")
    except ValueError as exc:
        raise _invalid("invalid local date or time") from exc


def _strict_date(value: str) -> date:
    if not DATE_RE.fullmatch(value):
        raise _invalid("date must be YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise _invalid("invalid date") from exc


def _parse_hhmm(value: Any, name: str) -> time:
    if not isinstance(value, str):
        if value is MISSING:
            raise _invalid(f"{name} is required")
        raise _error(400, "malformed_request", f"{name} must be a string")
    if not TIME_RE.fullmatch(value):
        raise _invalid(f"{name} must be HH:MM")
    try:
        return time.fromisoformat(value)
    except ValueError as exc:
        raise _invalid(f"{name} must be HH:MM") from exc


def _integer(value: Any, name: str, *, minimum: int) -> int:
    if value is MISSING:
        raise _invalid(f"{name} is required")
    if isinstance(value, bool) or not isinstance(value, int):
        raise _error(400, "malformed_request", f"{name} must be an integer")
    if value < minimum:
        raise _invalid(f"{name} must be an integer of at least {minimum}")
    return value


def _fixture_string(value: Any, name: str, *, nonempty: bool = False) -> str:
    if value is MISSING:
        raise _invalid(f"{name} is required")
    if not isinstance(value, str):
        raise _error(400, "malformed_request", f"{name} must be a string")
    if nonempty and not value:
        raise _invalid(f"{name} must not be empty")
    return value


def _json_shape(value: Any) -> Any:
    """Ensure parsed request JSON follows JSON's finite-number rules."""
    if isinstance(value, float) and not (float("-inf") < value < float("inf")):
        raise _error(400, "malformed_request", "invalid JSON number")
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise _error(400, "malformed_request", "invalid JSON object")
            _json_shape(child)
    elif isinstance(value, list):
        for child in value:
            _json_shape(child)
    return value


def _aware(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise _invalid("invalid timestamp in state") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise _invalid("timestamp must include an offset")
    return parsed


def _instant(value: datetime) -> datetime:
    return value.astimezone(UTC)


def _overlap(start_a: datetime, end_a: datetime, start_b: datetime, end_b: datetime) -> bool:
    return _instant(start_a) < _instant(end_b) and _instant(start_b) < _instant(end_a)


def _make_error_response(error: DomainError) -> ApiResponse:
    return ApiResponse(error.status, error.error_body())


def _fixture_state(fixture: Any) -> ServiceState:
    if not isinstance(fixture, dict):
        raise _invalid("fixture must be an object")
    users_data = fixture.get("users", [])
    restaurants_data = fixture.get("restaurants", [])
    reservations_data = fixture.get("reservations", [])
    if not isinstance(users_data, list) or not isinstance(restaurants_data, list) or not isinstance(reservations_data, list):
        raise _error(400, "malformed_request", "fixture collections must be arrays")

    state = ServiceState()
    for item in users_data:
        if not isinstance(item, dict):
            raise _error(400, "malformed_request", "each user must be an object")
        user_id = _fixture_id(item.get("id", MISSING), "user id")
        email = _fixture_string(item.get("email", MISSING), "email")
        password = _fixture_string(item.get("password", MISSING), "password")
        display_name = _fixture_string(item.get("display_name", MISSING), "display_name")
        if not email:
            raise _invalid("email must not be empty")
        email_key = email.casefold()
        if user_id in state.users or any(user["email"].casefold() == email_key for user in state.users.values()):
            raise _invalid("duplicate user id or email")
        state.users[user_id] = {
            "id": user_id,
            "email": email,
            "password_hash": hash_password(password),
            "display_name": display_name,
        }

    for item in restaurants_data:
        if not isinstance(item, dict):
            raise _error(400, "malformed_request", "each restaurant must be an object")
        restaurant_id = _fixture_id(item.get("id", MISSING), "restaurant id")
        if restaurant_id in state.restaurants:
            raise _invalid("duplicate restaurant id")
        name = _fixture_string(item.get("name", MISSING), "name")
        timezone_name = _fixture_string(item.get("timezone", MISSING), "timezone", nonempty=True)
        try:
            ZoneInfo(timezone_name)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise _invalid("invalid restaurant timezone") from exc
        slot_minutes = _integer(item.get("slot_minutes", MISSING), "slot_minutes", minimum=1)
        duration = _integer(item.get("reservation_duration_minutes", MISSING), "reservation_duration_minutes", minimum=1)
        cutoff = _integer(item.get("cancellation_cutoff_minutes", MISSING), "cancellation_cutoff_minutes", minimum=0)
        hours = item.get("opening_hours", MISSING)
        tables = item.get("tables", MISSING)
        if hours is MISSING or tables is MISSING:
            raise _invalid("opening_hours and tables are required")
        if not isinstance(hours, list) or not isinstance(tables, list):
            raise _error(400, "malformed_request", "opening_hours and tables must be arrays")
        normalized_hours = []
        seen_weekdays: set[str] = set()
        for opening in hours:
            if not isinstance(opening, dict):
                raise _error(400, "malformed_request", "each opening hour must be an object")
            weekday = _fixture_string(opening.get("weekday", MISSING), "weekday")
            if weekday not in WEEKDAYS or weekday in seen_weekdays:
                raise _invalid("invalid or duplicate weekday")
            opens = _parse_hhmm(opening.get("opens", MISSING), "opens")
            closes = _parse_hhmm(opening.get("closes", MISSING), "closes")
            if closes <= opens:
                raise _invalid("closes must be later than opens")
            seen_weekdays.add(weekday)
            normalized_hours.append({"weekday": weekday, "opens": opens.strftime("%H:%M"), "closes": closes.strftime("%H:%M")})
        normalized_tables = []
        seen_table_ids: set[str] = set()
        for table in tables:
            if not isinstance(table, dict):
                raise _error(400, "malformed_request", "each table must be an object")
            table_id = _fixture_id(table.get("id", MISSING), "table id")
            label = _fixture_string(table.get("label", MISSING), "label")
            capacity = _integer(table.get("capacity", MISSING), "capacity", minimum=1)
            if table_id in seen_table_ids:
                raise _invalid("invalid or duplicate table")
            seen_table_ids.add(table_id)
            normalized_tables.append({"id": table_id, "label": label, "capacity": capacity})
        state.restaurants[restaurant_id] = {
            "id": restaurant_id,
            "name": name,
            "timezone": timezone_name,
            "slot_minutes": slot_minutes,
            "reservation_duration_minutes": duration,
            "cancellation_cutoff_minutes": cutoff,
            "opening_hours": normalized_hours,
            "tables": normalized_tables,
        }

    now = rfc3339(datetime.now(UTC))
    seen_reservation_ids: set[str] = set()
    seen_references: set[str] = set()
    for item in reservations_data:
        if not isinstance(item, dict):
            raise _error(400, "malformed_request", "each reservation must be an object")
        if not all(name in item for name in ("restaurant_id", "table_id", "starts_at_local", "party_size")):
            raise _invalid("seeded reservation is missing required fields")
        reservation_id = _fixture_id(item.get("id", MISSING), "reservation id")
        reference = item.get("reference", MISSING)
        user_id = item.get("user_id", MISSING)
        if reference is MISSING or user_id is MISSING:
            raise _invalid("seeded reservation is missing identity fields")
        if not isinstance(reference, str):
            raise _error(400, "malformed_request", "reservation reference must be a string")
        if not REFERENCE_RE.fullmatch(reference):
            raise _invalid("invalid reservation reference")
        if not isinstance(user_id, str):
            raise _error(400, "malformed_request", "reservation user_id must be a string")
        if user_id not in state.users:
            raise _invalid("reservation user does not exist")
        if reservation_id in seen_reservation_ids or reference in seen_references:
            raise _invalid("duplicate reservation id or reference")
        try:
            record = _new_reservation(
                state,
                user_id,
                {
                    "restaurant_id": item.get("restaurant_id"),
                    "table_id": item.get("table_id"),
                    "starts_at_local": item.get("starts_at_local"),
                    "party_size": item.get("party_size"),
                },
                reservation_id=reservation_id,
                reference=reference,
                created_at=now,
            )
        except DomainError as exc:
            if exc.status == 400:
                raise
            raise _invalid("invalid seeded reservation") from exc
        state.reservations[reference] = record
        seen_reservation_ids.add(reservation_id)
        seen_references.add(reference)
    return state


def _fixture_id(value: Any, name: str) -> str:
    if value is MISSING:
        raise _invalid(f"{name} is required")
    if not isinstance(value, str):
        raise _error(400, "malformed_request", f"{name} must be a string")
    if not value or len(value) > 64:
        raise _invalid(f"{name} must contain 1 to 64 characters")
    return value


def _restaurant_table(state: ServiceState, restaurant_id: str, table_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    restaurant = state.restaurants.get(restaurant_id)
    if restaurant is None:
        raise _not_found()
    table = next((candidate for candidate in restaurant["tables"] if candidate["id"] == table_id), None)
    if table is None:
        raise _not_found()
    return restaurant, table


def _opening_for(restaurant: dict[str, Any], local_date: date) -> dict[str, str] | None:
    day = WEEKDAYS[local_date.weekday()]
    return next((entry for entry in restaurant["opening_hours"] if entry["weekday"] == day), None)


def _closing_instant(local_date: date, closing: str, timezone_name: str) -> datetime:
    # Opening-hour boundaries are configured as wall-clock times. ZoneInfo's fold=0
    # interpretation maps a nonexistent boundary to the transition's post-gap instant.
    naive = datetime.combine(local_date, time.fromisoformat(closing))
    return naive.replace(tzinfo=ZoneInfo(timezone_name), fold=0).astimezone(UTC)


def _resolve_booking_time(restaurant: dict[str, Any], local_value: Any) -> tuple[datetime, str]:
    naive = _parse_local(local_value)
    local_string = naive.strftime("%Y-%m-%dT%H:%M")
    try:
        start = resolve_local(local_string, restaurant["timezone"])
    except DomainError as exc:
        raise _error(422, "invalid_local_time", exc.message) from exc
    opening = _opening_for(restaurant, naive.date())
    if opening is None:
        raise _error(422, "outside_opening_hours", "restaurant is closed")
    opens = time.fromisoformat(opening["opens"])
    closes = time.fromisoformat(opening["closes"])
    if not (opens <= naive.time() < closes):
        raise _error(422, "outside_opening_hours", "time is outside opening hours")
    opens_minutes = opens.hour * 60 + opens.minute
    start_minutes = naive.hour * 60 + naive.minute
    if (start_minutes - opens_minutes) % restaurant["slot_minutes"] != 0:
        raise _error(422, "not_on_slot_grid", "time is not on the slot grid")
    close_instant = _closing_instant(naive.date(), opening["closes"], restaurant["timezone"])
    available_seconds = (close_instant - _instant(start)).total_seconds()
    if restaurant["reservation_duration_minutes"] * 60 > available_seconds:
        raise _error(422, "outside_opening_hours", "reservation ends after closing")
    return start, local_string


def _record_end(record: dict[str, Any]) -> datetime:
    return _aware(record["ends_at"])


def _has_conflict(
    state: ServiceState,
    restaurant_id: str,
    table_id: str,
    start: datetime,
    end: datetime,
    *,
    ignore_references: set[str] | None = None,
) -> bool:
    ignored = ignore_references or set()
    for reference, existing in state.reservations.items():
        if reference in ignored or existing.get("status") != "confirmed":
            continue
        if existing["restaurant_id"] != restaurant_id or existing["table_id"] != table_id:
            continue
        if _overlap(start, end, _aware(existing["starts_at"]), _record_end(existing)):
            return True
    return False


def _new_reservation(
    state: ServiceState,
    user_id: str,
    values: dict[str, Any],
    *,
    reservation_id: str | None = None,
    reference: str | None = None,
    created_at: str | None = None,
    ignore_references: set[str] | None = None,
) -> dict[str, Any]:
    restaurant_id = _required_id(values, "restaurant_id")
    table_id = _required_id(values, "table_id")
    party_size = _party_size(values)
    if "starts_at_local" not in values:
        raise _invalid("starts_at_local is required")
    restaurant, table = _restaurant_table(state, restaurant_id, table_id)
    if party_size > table["capacity"]:
        raise _error(422, "party_exceeds_capacity", "party size exceeds table capacity")
    start, local_string = _resolve_booking_time(restaurant, values.get("starts_at_local"))
    end = _instant(start) + timedelta(minutes=restaurant["reservation_duration_minutes"])
    end_local = end.astimezone(ZoneInfo(restaurant["timezone"]))
    if _has_conflict(
        state,
        restaurant_id,
        table_id,
        start,
        end,
        ignore_references=ignore_references,
    ):
        raise _error(409, "table_unavailable", "table is unavailable")
    if reference is None:
        while True:
            candidate = "".join(secrets.choice(REFERENCE_ALPHABET) for _ in range(8))
            if candidate not in state.reservations:
                reference = candidate
                break
    assert reference is not None
    record = {
        "reservation_id": reservation_id or uuid.uuid4().hex,
        "reference": reference,
        "user_id": user_id,
        "restaurant_id": restaurant_id,
        "table_id": table_id,
        "party_size": party_size,
        "status": "confirmed",
        "starts_at_local": local_string,
        "starts_at": rfc3339(start),
        "ends_at": rfc3339(end_local),
        "created_at": created_at or rfc3339(datetime.now(UTC)),
    }
    return record


def _validate_idempotency_key(headers: dict[str, str]) -> str:
    key = headers.get("idempotency-key", "")
    if not key:
        raise _error(400, "missing_idempotency_key", "Idempotency-Key is required")
    if not 1 <= len(key) <= 255:
        raise _invalid("Idempotency-Key must contain 1 to 255 characters")
    return key


def _bearer(headers: dict[str, str]) -> str:
    authorization = headers.get("authorization", "")
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer" or not parts[1]:
        raise _error(401, "unauthenticated", "valid bearer token required")
    return parts[1]


def _query_one(query: dict[str, list[str]], name: str) -> str:
    values = query.get(name)
    if not values or values[0] == "":
        raise _invalid(f"{name} is required")
    return values[0]


def _default_seed_state() -> ServiceState:
    weekdays = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    default_hours = [{"weekday": d, "opens": "08:00", "closes": "23:30"} for d in weekdays]

    def make_tables(count: int) -> list[dict[str, Any]]:
        tables = []
        capacities = [2, 2, 4, 4, 6, 8]
        for i in range(1, count + 1):
            cap = capacities[(i - 1) % len(capacities)]
            tables.append({"id": f"t_{i}", "label": str(i), "capacity": cap})
        return tables

    venues = [
        # MUMBAI (India)
        {"id": "r_mumbai_royal", "name": "The Royal Pavilion & Palace", "city": "Mumbai", "timezone": "Asia/Kolkata", "category": "Indian Royal Fine Dining", "theme": "mumbai_royal", "bg_image": "/assets/mumbai.jpg"},
        {"id": "r_mumbai_bastian", "name": "Bastian Rooftop & Grill", "city": "Mumbai", "timezone": "Asia/Kolkata", "category": "Rooftop Seafood & Bar", "theme": "rooftop_sky", "bg_image": "/assets/rooftop.jpg"},
        {"id": "r_mumbai_trident", "name": "Trident Bay Lounge", "city": "Mumbai", "timezone": "Asia/Kolkata", "category": "Luxury Bay Pub & Lounge", "theme": "rooftop_sky", "bg_image": "/assets/rooftop.jpg"},
        {"id": "r_mumbai_canteen", "name": "The Bombay Canteen Bar", "city": "Mumbai", "timezone": "Asia/Kolkata", "category": "Modern Indian Pub", "theme": "mumbai_royal", "bg_image": "/assets/mumbai.jpg"},
        {"id": "r_mumbai_zuma", "name": "Masala Library Gastronomy", "city": "Mumbai", "timezone": "Asia/Kolkata", "category": "Molecular Indian Dining", "theme": "mumbai_royal", "bg_image": "/assets/mumbai.jpg"},

        # PARIS (France)
        {"id": "r_lumiere", "name": "Lumière Gastronomy", "city": "Paris", "timezone": "Europe/Paris", "category": "Modern French Fine Dining", "theme": "parisian_gold", "bg_image": "/assets/lumiere.jpg"},
        {"id": "r_maison", "name": "Maison Rouge Bistro", "city": "Paris", "timezone": "Europe/Paris", "category": "Classic French Bistro", "theme": "dark_velvet", "bg_image": "/assets/anker.jpg"},
        {"id": "r_paris_jules", "name": "Le Jules Verne Eiffel", "city": "Paris", "timezone": "Europe/Paris", "category": "Eiffel Tower Fine Dining", "theme": "parisian_gold", "bg_image": "/assets/hero.jpg"},
        {"id": "r_paris_meurice", "name": "Le Meurice Alain Ducasse", "city": "Paris", "timezone": "Europe/Paris", "category": "Palace Hotel Dining", "theme": "parisian_gold", "bg_image": "/assets/hero.jpg"},
        {"id": "r_paris_laperouse", "name": "Lapérouse Historic Lounge", "city": "Paris", "timezone": "Europe/Paris", "category": "Historic Lounge Bar", "theme": "dark_velvet", "bg_image": "/assets/anker.jpg"},

        # TOKYO (Japan)
        {"id": "r_omakase", "name": "Ginza Omakase Counter", "city": "Tokyo", "timezone": "Asia/Tokyo", "category": "Japanese Omakase", "theme": "tokyo_slate", "bg_image": "/assets/lumiere.jpg"},
        {"id": "r_tokyo_roppongi", "name": "Roppongi Sky Lounge", "city": "Tokyo", "timezone": "Asia/Tokyo", "category": "Cocktail Lounge & Pub", "theme": "rooftop_sky", "bg_image": "/assets/rooftop.jpg"},
        {"id": "r_tokyo_sukiyabashi", "name": "Sukiyabashi Sushi Bar", "city": "Tokyo", "timezone": "Asia/Tokyo", "category": "Traditional Sushi Counter", "theme": "tokyo_slate", "bg_image": "/assets/lumiere.jpg"},
        {"id": "r_tokyo_narisawa", "name": "Narisawa Innovative Grill", "city": "Tokyo", "timezone": "Asia/Tokyo", "category": "Avant-Garde Dining", "theme": "tokyo_slate", "bg_image": "/assets/lumiere.jpg"},
        {"id": "r_tokyo_parkhyatt", "name": "New York Grill Tokyo", "city": "Tokyo", "timezone": "Asia/Tokyo", "category": "Skyline Steakhouse & Bar", "theme": "rooftop_sky", "bg_image": "/assets/rooftop.jpg"},

        # LONDON (UK)
        {"id": "r_velvet", "name": "Velvet & Oak Gastropub", "city": "London", "timezone": "Europe/London", "category": "British Gastropub & Grill", "theme": "dark_velvet", "bg_image": "/assets/anker.jpg"},
        {"id": "r_london_wolseley", "name": "The Wolseley Piccadilly", "city": "London", "timezone": "Europe/London", "category": "Grand European Cafe", "theme": "parisian_gold", "bg_image": "/assets/hero.jpg"},
        {"id": "r_london_mayfair", "name": "Mayfair Prime Steakhouse", "city": "London", "timezone": "Europe/London", "category": "Mayfair Steak & Wine", "theme": "dark_velvet", "bg_image": "/assets/anker.jpg"},
        {"id": "r_london_sketch", "name": "Sketch Gallery Lounge", "city": "London", "timezone": "Europe/London", "category": "Artisan Cocktail Lounge", "theme": "rooftop_sky", "bg_image": "/assets/rooftop.jpg"},
        {"id": "r_london_ritz", "name": "The Ritz Restaurant", "city": "London", "timezone": "Europe/London", "category": "British Palace Dining", "theme": "parisian_gold", "bg_image": "/assets/hero.jpg"},

        # NEW YORK (USA)
        {"id": "r_nocturne", "name": "Nocturne Sky Lounge", "city": "New York", "timezone": "America/New_York", "category": "Manhattan Rooftop Lounge", "theme": "rooftop_sky", "bg_image": "/assets/rooftop.jpg"},
        {"id": "r_ny_manhatta", "name": "Manhatta High-Rise Grill", "city": "New York", "timezone": "America/New_York", "category": "Downtown Panoramic Grill", "theme": "rooftop_sky", "bg_image": "/assets/rooftop.jpg"},
        {"id": "r_ny_balthazar", "name": "Balthazar SoHo Bistro", "city": "New York", "timezone": "America/New_York", "category": "SoHo French Bistro", "theme": "dark_velvet", "bg_image": "/assets/anker.jpg"},
        {"id": "r_ny_eleven", "name": "Eleven Madison Fine Dining", "city": "New York", "timezone": "America/New_York", "category": "3-Star Fine Dining", "theme": "parisian_gold", "bg_image": "/assets/hero.jpg"},
        {"id": "r_ny_bernardin", "name": "Le Bernardin Seafood", "city": "New York", "timezone": "America/New_York", "category": "Luxury Seafood Dining", "theme": "tokyo_slate", "bg_image": "/assets/lumiere.jpg"},

        # DUBAI (UAE)
        {"id": "r_dubai_atmosphere", "name": "At.mosphere Burj Khalifa", "city": "Dubai", "timezone": "Asia/Dubai", "category": "Burj Skyline Lounge", "theme": "rooftop_sky", "bg_image": "/assets/rooftop.jpg"},
        {"id": "r_dubai_zuma", "name": "Zuma Dubai Lounge", "city": "Dubai", "timezone": "Asia/Dubai", "category": "Contemporary Asian Pub", "theme": "tokyo_slate", "bg_image": "/assets/lumiere.jpg"},
        {"id": "r_dubai_ossiano", "name": "Ossiano Underwater Dining", "city": "Dubai", "timezone": "Asia/Dubai", "category": "Underwater Fine Dining", "theme": "mumbai_royal", "bg_image": "/assets/mumbai.jpg"},
        {"id": "r_dubai_tresind", "name": "Trèsind Studio Gastronomy", "city": "Dubai", "timezone": "Asia/Dubai", "category": "Modern Indian Gastronomy", "theme": "mumbai_royal", "bg_image": "/assets/mumbai.jpg"},
        {"id": "r_dubai_nusr", "name": "Nusr-Et Steakhouse Dubai", "city": "Dubai", "timezone": "Asia/Dubai", "category": "Luxury Steakhouse Pub", "theme": "dark_velvet", "bg_image": "/assets/anker.jpg"},

        # ROME (Italy)
        {"id": "r_toscana", "name": "Villa Toscana Cellar", "city": "Rome", "timezone": "Europe/Rome", "category": "Tuscan Trattoria & Wine", "theme": "dark_velvet", "bg_image": "/assets/anker.jpg"},
        {"id": "r_rome_pergola", "name": "La Pergola Rome", "city": "Rome", "timezone": "Europe/Rome", "category": "Panoromic Fine Dining", "theme": "parisian_gold", "bg_image": "/assets/hero.jpg"},
        {"id": "r_rome_aroma", "name": "Aroma Rooftop Colosseum", "city": "Rome", "timezone": "Europe/Rome", "category": "Colosseum View Lounge", "theme": "rooftop_sky", "bg_image": "/assets/rooftop.jpg"},
        {"id": "r_rome_imago", "name": "Imàgo Rooftop Bar", "city": "Rome", "timezone": "Europe/Rome", "category": "Hassler Rooftop Bar", "theme": "rooftop_sky", "bg_image": "/assets/rooftop.jpg"},
        {"id": "r_rome_roscioli", "name": "Salumeria Roscioli", "city": "Rome", "timezone": "Europe/Rome", "category": "Historic Italian Bistro", "theme": "dark_velvet", "bg_image": "/assets/anker.jpg"},

        # SINGAPORE (Singapore)
        {"id": "r_opium", "name": "Opium Night Lounge", "city": "Singapore", "timezone": "Asia/Singapore", "category": "Asian Fusion Lounge", "theme": "rooftop_sky", "bg_image": "/assets/rooftop.jpg"},
        {"id": "r_sg_mbs", "name": "Marina Bay Sands Grill", "city": "Singapore", "timezone": "Asia/Singapore", "category": "Rooftop SkyPark Bar", "theme": "rooftop_sky", "bg_image": "/assets/rooftop.jpg"},
        {"id": "r_sg_odette", "name": "Odette Fine Dining", "city": "Singapore", "timezone": "Asia/Singapore", "category": "Modern French Dining", "theme": "parisian_gold", "bg_image": "/assets/hero.jpg"},
        {"id": "r_sg_jumbo", "name": "Jumbo Seafood Bay", "city": "Singapore", "timezone": "Asia/Singapore", "category": "Coastal Seafood & Pub", "theme": "mumbai_royal", "bg_image": "/assets/mumbai.jpg"},
        {"id": "r_sg_atlas", "name": "Atlas Bar & Lounge", "city": "Singapore", "timezone": "Asia/Singapore", "category": "Art Deco Gin Lounge", "theme": "dark_velvet", "bg_image": "/assets/anker.jpg"},

        # LOS ANGELES (USA)
        {"id": "r_celestial", "name": "Celestial Rooftop & Hotel", "city": "Los Angeles", "timezone": "America/Los_Angeles", "category": "Rooftop Hotel & Bar", "theme": "rooftop_sky", "bg_image": "/assets/rooftop.jpg"},
        {"id": "r_la_spago", "name": "Spago Beverly Hills", "city": "Los Angeles", "timezone": "America/Los_Angeles", "category": "Beverly Hills Dining", "theme": "parisian_gold", "bg_image": "/assets/hero.jpg"},
        {"id": "r_la_nobu", "name": "Nobu Malibu Beach", "city": "Los Angeles", "timezone": "America/Los_Angeles", "category": "Coastal Japanese Lounge", "theme": "tokyo_slate", "bg_image": "/assets/lumiere.jpg"},
        {"id": "r_la_republicue", "name": "République Brasserie", "city": "Los Angeles", "timezone": "America/Los_Angeles", "category": "French Brasserie Pub", "theme": "dark_velvet", "bg_image": "/assets/anker.jpg"},
        {"id": "r_la_providence", "name": "Providence Seafood", "city": "Los Angeles", "timezone": "America/Los_Angeles", "category": "Michelin Seafood", "theme": "tokyo_slate", "bg_image": "/assets/lumiere.jpg"},

        # BERLIN (Germany)
        {"id": "r_anker", "name": "Zum Anker Fine Dining", "city": "Berlin", "timezone": "Europe/Berlin", "category": "German Fine Dining", "theme": "dark_velvet", "bg_image": "/assets/anker.jpg"},
        {"id": "r_berlin_borchardt", "name": "Borchardt Gastronomy", "city": "Berlin", "timezone": "Europe/Berlin", "category": "Classic Berlin Bistro", "theme": "dark_velvet", "bg_image": "/assets/anker.jpg"},
        {"id": "r_berlin_grill", "name": "Grill Royal Spree", "city": "Berlin", "timezone": "Europe/Berlin", "category": "Waterfront Steakhouse", "theme": "rooftop_sky", "bg_image": "/assets/rooftop.jpg"},
        {"id": "r_berlin_timraue", "name": "Restaurant Tim Raue", "city": "Berlin", "timezone": "Europe/Berlin", "category": "Asian Inspired Dining", "theme": "mumbai_royal", "bg_image": "/assets/mumbai.jpg"},
        {"id": "r_berlin_facil", "name": "FACIL Garden Restaurant", "city": "Berlin", "timezone": "Europe/Berlin", "category": "Glasshouse Fine Dining", "theme": "parisian_gold", "bg_image": "/assets/hero.jpg"},
    ]

    restaurants_dict = {}
    for v in venues:
        restaurants_dict[v["id"]] = {
            "id": v["id"],
            "name": v["name"],
            "city": v["city"],
            "timezone": v["timezone"],
            "category": v["category"],
            "theme": v["theme"],
            "bg_image": v["bg_image"],
            "slot_minutes": 30,
            "reservation_duration_minutes": 90,
            "cancellation_cutoff_minutes": 0,
            "opening_hours": default_hours,
            "tables": make_tables(6),
        }

    user_guest_id = "u_guest"
    user_ada_id = "u_ada"
    user_bob_id = "u_bob"

    users_dict = {
        user_guest_id: {
            "id": user_guest_id,
            "email": "guest@example.com",
            "password_hash": hash_password("correct horse"),
            "display_name": "Guest User",
        },
        user_ada_id: {
            "id": user_ada_id,
            "email": "ada@example.com",
            "password_hash": hash_password("correct horse"),
            "display_name": "Ada",
        },
        user_bob_id: {
            "id": user_bob_id,
            "email": "bob@example.com",
            "password_hash": hash_password("correct horse"),
            "display_name": "Bob",
        },
    }

    tokens_dict = {
        "guest-token-123456": user_guest_id,
        "token-ada-123456": user_ada_id,
        "token-bob-123456": user_bob_id,
    }

    return ServiceState(
        users=users_dict,
        tokens=tokens_dict,
        restaurants=restaurants_dict,
        reservations={},
        receipts={},
    )


class TablekeeperService:
    """Implements the public Stage 1 contract over a single transactional state."""

    def __init__(self, store: StateStore | None = None) -> None:
        self.store = store if store is not None else StateStore(initial=_default_seed_state())

    async def handle(self, method: str, target: str, headers: dict[str, str], body: Any = None) -> ApiResponse:
        try:
            return await self._dispatch(method.upper(), target, {k.lower(): v for k, v in headers.items()}, _json_shape(body))
        except DomainError as error:
            return _make_error_response(error)
        except RecursionError:
            return _make_error_response(_error(400, "malformed_request", "request body is too deeply nested"))
        except OverflowError:
            return _make_error_response(_invalid("value is outside the supported range"))

    async def _dispatch(
        self, method: str, target: str, headers: dict[str, str], body: Any
    ) -> ApiResponse:
        parsed = urlsplit(target)
        raw_path = parsed.path or "/"
        path = raw_path
        query = parse_qs(parsed.query, keep_blank_values=True)

        if method == "GET" and path == "/health":
            return ApiResponse(200, {"status": "ok"})

        if method == "POST" and path == "/_test/reset":
            fixture = _require_object(body)
            candidate = await asyncio.to_thread(_fixture_state, fixture)
            await self.store.replace(candidate)
            return ApiResponse(204)

        if method == "GET" and path == "/_test/export":
            return ApiResponse(200, await self.store.export())

        if method == "POST" and path == "/_test/import":
            envelope = _require_object(body)
            candidate = self._validated_import_state(envelope)
            await self.store.replace(candidate)
            return ApiResponse(204)

        if method == "GET" and path in ("/", "/index.html"):
            accept = headers.get("accept", "")
            if "text/html" in accept or "application/json" not in accept:
                web_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web")
                index_path = os.path.join(web_dir, "index.html")
                if os.path.isfile(index_path):
                    with open(index_path, "rb") as f:
                        return ApiResponse(200, f.read(), content_type="text/html; charset=utf-8")
            return ApiResponse(200, {"service": "Tablekeeper", "stage": 2, "health": "/health"})

        if method == "GET" and (path.startswith(("/static/", "/assets/")) or path.endswith((".css", ".js", ".jpg", ".jpeg", ".png", ".webp", ".svg", ".woff2", ".ico"))):
            rel_path = path.lstrip("/")
            if rel_path.startswith("static/"):
                rel_path = rel_path[len("static/"):]
            web_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "web")
            file_path = os.path.abspath(os.path.join(web_dir, rel_path))
            if file_path.startswith(web_dir) and os.path.isfile(file_path):
                content_type = self._guess_content_type(file_path)
                with open(file_path, "rb") as f:
                    return ApiResponse(200, f.read(), content_type=content_type)

        if method == "POST" and path in ("/auth/signup", "/auth/login"):
            payload = _require_object(body)
            if path.endswith("signup"):
                return await self._signup(payload)
            return await self._login(payload)

        if method == "GET" and path == "/restaurants":
            state = await self.store.snapshot()
            return ApiResponse(
                200,
                {
                    "restaurants": [
                        {key: restaurant[key] for key in ("id", "name", "timezone")}
                        for restaurant in state.restaurants.values()
                    ]
                },
            )

        if method == "GET" and path.startswith("/restaurants/"):
            restaurant_id = unquote(path[len("/restaurants/"):])
            if not restaurant_id or len(restaurant_id) > 64:
                raise _invalid("restaurant id must contain 1 to 64 characters")
            state = await self.store.snapshot()
            restaurant = state.restaurants.get(restaurant_id)
            if restaurant is None:
                raise _not_found()
            return ApiResponse(200, copy.deepcopy(restaurant))

        if method == "GET" and path == "/availability":
            return await self._availability(query)

        if method == "POST" and path == "/reservations":
            payload = _require_object(body)
            user_id = await self._authenticated_user(headers)
            key = _validate_idempotency_key(headers)
            return await self._create_reservation(user_id, payload, key)

        if method == "POST" and path == "/reservation-moves":
            payload = _require_object(body)
            user_id = await self._authenticated_user(headers)
            key = _validate_idempotency_key(headers)
            return await self._move_reservations(user_id, payload, key)

        if method == "GET" and path == "/reservations":
            user_id = await self._authenticated_user(headers)
            state = await self.store.snapshot()
            rows = [
                {k: v for k, v in r.items() if k != "user_id"}
                for r in state.reservations.values()
                if r["user_id"] == user_id
            ]
            rows.sort(key=lambda r: _instant(_aware(r["starts_at"])), reverse=True)
            return ApiResponse(200, {"reservations": rows})

        match = re.fullmatch(r"/reservations/([^/]+)(/cancel)?", path)
        if match:
            reference = unquote(match.group(1))
            is_cancel = bool(match.group(2))
            user_id = await self._authenticated_user(headers)
            if method == "GET" and not is_cancel:
                state = await self.store.snapshot()
                record = state.reservations.get(reference)
                if record is None or record["user_id"] != user_id:
                    raise _not_found()
                return ApiResponse(200, {k: v for k, v in record.items() if k != "user_id"})
            if method == "POST" and is_cancel:
                return await self._cancel_reservation(reference, user_id)
            if method == "PATCH" and not is_cancel:
                payload = _require_object(body)
                return await self._patch_reservation(reference, user_id, payload)

        raise _not_found()

    def _guess_content_type(self, path: str) -> str:
        if path.endswith(".html"):
            return "text/html; charset=utf-8"
        if path.endswith(".css"):
            return "text/css; charset=utf-8"
        if path.endswith(".js"):
            return "application/javascript; charset=utf-8"
        if path.endswith((".jpg", ".jpeg")):
            return "image/jpeg"
        if path.endswith(".png"):
            return "image/png"
        if path.endswith(".webp"):
            return "image/webp"
        if path.endswith(".svg"):
            return "image/svg+xml"
        if path.endswith(".woff2"):
            return "font/woff2"
        return "application/octet-stream"

    async def _authenticated_user(self, headers: dict[str, str]) -> str:
        token = _bearer(headers)
        state = await self.store.snapshot()
        user_id = state.tokens.get(token)
        if user_id is None or user_id not in state.users:
            raise _error(401, "unauthenticated", "unknown bearer token")
        return user_id

    def _validated_import_state(self, envelope: dict[str, Any]) -> ServiceState:
        if set(envelope) != {"track", "format_version", "state"}:
            raise _invalid("invalid export envelope")
        if envelope["track"] != "tablekeeper" or envelope["format_version"] != 1:
            raise _invalid("unsupported export envelope")
        try:
            candidate = ServiceState.from_dict(envelope["state"])

            seen_email_addresses: set[str] = set()
            for user_id, user in candidate.users.items():
                if not isinstance(user_id, str) or not 1 <= len(user_id) <= 64 or not isinstance(user, dict):
                    raise _invalid("invalid user state")
                if set(user) != {"id", "email", "password_hash", "display_name"}:
                    raise _invalid("invalid user state")
                if (
                    user["id"] != user_id
                    or not isinstance(user["email"], str)
                    or not isinstance(user["password_hash"], str)
                    or not isinstance(user["display_name"], str)
                ):
                    raise _invalid("invalid user state")
                email_key = user["email"].casefold()
                if email_key in seen_email_addresses:
                    raise _invalid("duplicate email in user state")
                seen_email_addresses.add(email_key)
                if not is_valid_password_hash(user["password_hash"]):
                    raise _invalid("invalid password hash in state")

            if any(
                not isinstance(token, str) or not token or not isinstance(user_id, str) or user_id not in candidate.users
                for token, user_id in candidate.tokens.items()
            ):
                raise _invalid("invalid token state")

            # Reuse the reset-fixture validator for restaurant configuration, without
            # rehashing accounts or mutating the imported snapshot.
            normalized_restaurants = _fixture_state(
                {"restaurants": list(candidate.restaurants.values())}
            ).restaurants
            if normalized_restaurants != candidate.restaurants:
                raise _invalid("invalid restaurant state")

            all_references = set(candidate.reservations)
            required_reservation_fields = {
                "reservation_id",
                "reference",
                "user_id",
                "restaurant_id",
                "table_id",
                "party_size",
                "status",
                "starts_at_local",
                "starts_at",
                "ends_at",
                "created_at",
            }
            seen_reservation_ids: set[str] = set()
            for reference, record in candidate.reservations.items():
                if not isinstance(reference, str) or not REFERENCE_RE.fullmatch(reference) or not isinstance(record, dict):
                    raise _invalid("invalid reservation state")
                if set(record) != required_reservation_fields or record["reference"] != reference:
                    raise _invalid("invalid reservation state")
                if (
                    not isinstance(record["reservation_id"], str)
                    or not 1 <= len(record["reservation_id"]) <= 64
                    or record["user_id"] not in candidate.users
                    or record["status"] not in ("confirmed", "cancelled")
                ):
                    raise _invalid("invalid reservation state")
                if record["reservation_id"] in seen_reservation_ids:
                    raise _invalid("duplicate reservation id in state")
                seen_reservation_ids.add(record["reservation_id"])
                _aware(record["starts_at"])
                _aware(record["ends_at"])
                _aware(record["created_at"])
                expected = self._amended_record(
                    candidate, record, {}, check_occupancy=False
                )
                if (
                    expected["starts_at"] != record["starts_at"]
                    or expected["ends_at"] != record["ends_at"]
                ):
                    raise _invalid("reservation timestamps do not match its booking")

            confirmed = [
                record
                for record in candidate.reservations.values()
                if record["status"] == "confirmed"
            ]
            for index, first in enumerate(confirmed):
                for second in confirmed[index + 1 :]:
                    if (
                        first["restaurant_id"] == second["restaurant_id"]
                        and first["table_id"] == second["table_id"]
                        and _overlap(
                            _aware(first["starts_at"]),
                            _record_end(first),
                            _aware(second["starts_at"]),
                            _record_end(second),
                        )
                    ):
                        raise _invalid("overlapping confirmed reservations in state")

            for receipt in candidate.receipts.values():
                if (
                    receipt.user_id not in candidate.users
                    or not 1 <= len(receipt.key) <= 255
                    or receipt.method != "POST"
                    or receipt.path not in ("/reservations", "/reservation-moves")
                    or receipt.status != 201
                ):
                    raise _invalid("invalid idempotency receipt")
                body = json.loads(receipt.request_json)
                if not isinstance(body, dict) or canonical_json(body) != receipt.request_json:
                    raise _invalid("invalid idempotency request body")
        except DomainError as exc:
            if exc.status == 422 and exc.code == "validation_failed":
                raise
            raise _invalid("invalid imported state") from exc
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            raise _invalid("invalid imported state") from exc
        return candidate

    async def _signup(self, payload: dict[str, Any]) -> ApiResponse:
        email = _required_string(payload, "email")
        password = _required_string(payload, "password")
        display_name = _required_string(payload, "display_name")
        if not EMAIL_RE.fullmatch(email):
            raise _invalid("email must be of the form local@domain")
        if len(password) < 8:
            raise _invalid("password must be at least 8 characters")
        token = issue_token()
        password_hash = await asyncio.to_thread(hash_password, password)

        def mutation(state: ServiceState) -> dict[str, Any]:
            email_key = email.casefold()
            if any(user["email"].casefold() == email_key for user in state.users.values()):
                raise _error(409, "email_taken", "email is already registered")
            user_id = "u_" + uuid.uuid4().hex
            state.users[user_id] = {
                "id": user_id,
                "email": email,
                "password_hash": password_hash,
                "display_name": display_name,
            }
            state.tokens[token] = user_id
            return {"user_id": user_id, "display_name": display_name, "token": token}

        response = await self.store.transaction(mutation)
        return ApiResponse(201, response)

    async def _login(self, payload: dict[str, Any]) -> ApiResponse:
        email = _required_string(payload, "email")
        password = _required_string(payload, "password")
        state = await self.store.snapshot()
        user = next((candidate for candidate in state.users.values() if candidate["email"].casefold() == email.casefold()), None)
        if user is None or not await asyncio.to_thread(verify_password, password, user["password_hash"]):
            raise _error(401, "unauthenticated", "email or password is incorrect")
        token = issue_token()
        user_id = user["id"]

        def mutation(candidate: ServiceState) -> None:
            current = candidate.users.get(user_id)
            if current is None or current["password_hash"] != user["password_hash"]:
                raise _error(401, "unauthenticated", "email or password is incorrect")
            candidate.tokens[token] = user_id

        await self.store.transaction(mutation)
        return ApiResponse(200, {"user_id": user_id, "display_name": user["display_name"], "token": token})

    async def _availability(self, query: dict[str, list[str]]) -> ApiResponse:
        restaurant_id = _query_one(query, "restaurant_id")
        if len(restaurant_id) > 64:
            raise _invalid("restaurant_id must be at most 64 characters")
        date_value = _query_one(query, "date")
        party_text = _query_one(query, "party_size")
        if not DECIMAL_RE.fullmatch(party_text):
            raise _invalid("party_size must be plain decimal digits")
        party_size_digits = party_text.lstrip("0") or "0"
        if party_size_digits == "0":
            raise _invalid("party_size must be a positive integer")
        local_date = _strict_date(date_value)
        state = await self.store.snapshot()
        restaurant = state.restaurants.get(restaurant_id)
        if restaurant is None:
            raise _not_found()
        opening = _opening_for(restaurant, local_date)
        slots = []
        if opening is not None:
            opens = time.fromisoformat(opening["opens"])
            closes = time.fromisoformat(opening["closes"])
            open_minutes = opens.hour * 60 + opens.minute
            close_minutes = closes.hour * 60 + closes.minute
            zone = ZoneInfo(restaurant["timezone"])
            close_instant = _closing_instant(local_date, opening["closes"], restaurant["timezone"])
            minute = open_minutes
            while minute < close_minutes:
                naive = datetime.combine(local_date, time(minute // 60, minute % 60))
                local_value = naive.strftime("%Y-%m-%dT%H:%M")
                try:
                    start = resolve_local(local_value, restaurant["timezone"])
                except DomainError:
                    minute += restaurant["slot_minutes"]
                    continue
                start_instant = _instant(start)
                duration_seconds = restaurant["reservation_duration_minutes"] * 60
                if duration_seconds <= (close_instant - start_instant).total_seconds():
                    end = start_instant + timedelta(minutes=restaurant["reservation_duration_minutes"])
                    available = []
                    for table in restaurant["tables"]:
                        capacity = str(table["capacity"])
                        if (
                            len(party_size_digits) > len(capacity)
                            or (
                                len(party_size_digits) == len(capacity)
                                and party_size_digits > capacity
                            )
                        ):
                            continue
                        if not _has_conflict(
                            state,
                            restaurant_id,
                            table["id"],
                            start,
                            end,
                        ):
                            available.append(table["id"])
                    slots.append(
                        {
                            "starts_at_local": local_value,
                            "starts_at": rfc3339(start),
                            "available_table_ids": available,
                        }
                    )
                minute += restaurant["slot_minutes"]
        return ApiResponse(
            200,
            {
                "restaurant_id": restaurant_id,
                "date": local_date.isoformat(),
                "timezone": restaurant["timezone"],
                "slots": slots,
            },
        )

    async def _create_reservation(self, user_id: str, payload: dict[str, Any], key: str) -> ApiResponse:
        async def mutation(state: ServiceState) -> tuple[int, dict[str, Any]]:
            record = _new_reservation(state, user_id, payload)
            state.reservations[record["reference"]] = record
            return 201, {k: v for k, v in record.items() if k != "user_id"}

        status, response, _ = await self.store.idempotent_write(
            user_id=user_id,
            method="POST",
            path="/reservations",
            key=key,
            request_body=payload,
            mutation=mutation,
        )
        return ApiResponse(status, response)

    def _owned_reservation(self, state: ServiceState, reference: str, user_id: str) -> dict[str, Any]:
        record = state.reservations.get(reference)
        if record is None or record["user_id"] != user_id:
            raise _not_found()
        return record

    def _check_cutoff(self, state: ServiceState, record: dict[str, Any]) -> None:
        restaurant = state.restaurants.get(record["restaurant_id"])
        if restaurant is None:
            raise _not_found()
        starts_at = _instant(_aware(record["starts_at"]))
        now = datetime.now(UTC)
        if starts_at <= now:
            raise _error(409, "cutoff_passed", "cancellation cutoff has passed")
        cutoff_minutes = restaurant["cancellation_cutoff_minutes"]
        if (starts_at - now).total_seconds() <= cutoff_minutes * 60:
            raise _error(409, "cutoff_passed", "cancellation cutoff has passed")

    async def _cancel_reservation(self, reference: str, user_id: str) -> ApiResponse:
        def mutation(state: ServiceState) -> dict[str, Any]:
            record = self._owned_reservation(state, reference, user_id)
            if record["status"] == "cancelled":
                return copy.deepcopy(record)
            self._check_cutoff(state, record)
            record["status"] = "cancelled"
            return copy.deepcopy(record)

        result = await self.store.transaction(mutation)
        return ApiResponse(200, {k: v for k, v in result.items() if k != "user_id"})

    def _amended_record(
        self,
        state: ServiceState,
        record: dict[str, Any],
        changes: dict[str, Any],
        *,
        ignore_references: set[str] | None = None,
        check_occupancy: bool = True,
    ) -> dict[str, Any]:
        values = {
            "restaurant_id": record["restaurant_id"],
            "table_id": record["table_id"],
            "starts_at_local": record["starts_at_local"],
            "party_size": record["party_size"],
        }
        if "table_id" in changes:
            values["table_id"] = _required_id(changes, "table_id")
        if "starts_at_local" in changes:
            values["starts_at_local"] = changes["starts_at_local"]
        if "party_size" in changes:
            values["party_size"] = _party_size(changes)
        restaurant_id = values["restaurant_id"]
        table_id = values["table_id"]
        party_size = _party_size(values)
        restaurant, table = _restaurant_table(state, restaurant_id, table_id)
        if party_size > table["capacity"]:
            raise _error(422, "party_exceeds_capacity", "party size exceeds table capacity")
        start, local_string = _resolve_booking_time(restaurant, values["starts_at_local"])
        end = _instant(start) + timedelta(minutes=restaurant["reservation_duration_minutes"])
        if check_occupancy and _has_conflict(
            state,
            restaurant_id,
            table_id,
            start,
            end,
            ignore_references=ignore_references,
        ):
            raise _error(409, "table_unavailable", "table is unavailable")
        updated = copy.deepcopy(record)
        updated.update(
            {
                "table_id": table_id,
                "party_size": party_size,
                "starts_at_local": local_string,
                "starts_at": rfc3339(start),
                "ends_at": rfc3339(end.astimezone(ZoneInfo(restaurant["timezone"]))),
            }
        )
        return updated

    async def _patch_reservation(
        self, reference: str, user_id: str, payload: dict[str, Any]
    ) -> ApiResponse:
        def mutation(state: ServiceState) -> dict[str, Any]:
            current = self._owned_reservation(state, reference, user_id)
            if current["status"] == "cancelled":
                raise _error(409, "reservation_cancelled", "reservation is cancelled")
            self._check_cutoff(state, current)
            updated = self._amended_record(state, current, payload, ignore_references={reference})
            state.reservations[reference] = updated
            return {k: v for k, v in updated.items() if k != "user_id"}

        return ApiResponse(200, await self.store.transaction(mutation))

    async def _move_reservations(
        self, user_id: str, payload: dict[str, Any], key: str
    ) -> ApiResponse:
        async def mutation(state: ServiceState) -> tuple[int, dict[str, Any]]:
            moves = payload.get("moves")
            if not isinstance(moves, list) or not 1 <= len(moves) <= 8:
                raise _invalid("moves must contain 1 to 8 items")
            seen: set[str] = set()
            references: list[str] = []
            for item in moves:
                if not isinstance(item, dict):
                    raise _invalid("each move must be an object")
                reference = item.get("reference")
                if not isinstance(reference, str) or not reference:
                    raise _invalid("each move requires a reference")
                if reference in seen:
                    raise _invalid("move references must be distinct")
                seen.add(reference)
                references.append(reference)

            originals: list[dict[str, Any]] = []
            restaurant_ids: set[str] = set()
            for reference in references:
                current = self._owned_reservation(state, reference, user_id)
                originals.append(current)
                restaurant_ids.add(current["restaurant_id"])
            if len(restaurant_ids) > 1:
                raise _invalid("all moved reservations must belong to the same restaurant")

            # Per-item non-occupancy errors are checked in input order. A booking's
            # cutoff is checked before any proposed changes for that same booking.
            updated_records: list[dict[str, Any]] = []
            for item, current in zip(moves, originals):
                if current["status"] == "cancelled":
                    raise _error(409, "reservation_cancelled", "reservation is cancelled")
                self._check_cutoff(state, current)
                changes = {name: item[name] for name in ("table_id", "starts_at_local", "party_size") if name in item}
                updated_records.append(
                    self._amended_record(
                        state,
                        current,
                        changes,
                        ignore_references=seen,
                        check_occupancy=False,
                    )
                )

            # The listed records are removed together, then their proposed occupancy
            # is checked against each other and every unlisted confirmed reservation.
            for updated in updated_records:
                start = _aware(updated["starts_at"])
                end = _record_end(updated)
                if _has_conflict(
                    state,
                    updated["restaurant_id"],
                    updated["table_id"],
                    start,
                    end,
                    ignore_references=seen,
                ):
                    raise _error(409, "table_unavailable", "table is unavailable")
            for index, first in enumerate(updated_records):
                for second in updated_records[index + 1 :]:
                    if (
                        first["restaurant_id"] == second["restaurant_id"]
                        and first["table_id"] == second["table_id"]
                        and _overlap(
                            _aware(first["starts_at"]),
                            _record_end(first),
                            _aware(second["starts_at"]),
                            _record_end(second),
                        )
                    ):
                        raise _error(409, "table_unavailable", "table is unavailable")

            for updated in updated_records:
                state.reservations[updated["reference"]] = updated
            return 201, {
                "reservations": [
                    {k: v for k, v in record.items() if k != "user_id"}
                    for record in updated_records
                ]
            }

        status, response, _ = await self.store.idempotent_write(
            user_id=user_id,
            method="POST",
            path="/reservation-moves",
            key=key,
            request_body=payload,
            mutation=mutation,
        )
        return ApiResponse(status, response)