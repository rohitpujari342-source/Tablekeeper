import asyncio
import unittest
from datetime import date, datetime, timedelta

from app.service import TablekeeperService


def fixture(*, cutoff=0, reservations=None):
    return {
        "users": [
            {"id": "u_ada", "email": "ada@example.com", "password": "correct horse", "display_name": "Ada"},
            {"id": "u_bob", "email": "bob@example.com", "password": "correct horse", "display_name": "Bob"},
        ],
        "restaurants": [
            {
                "id": "r_anker",
                "name": "Zum Anker",
                "timezone": "Europe/Berlin",
                "slot_minutes": 30,
                "reservation_duration_minutes": 90,
                "cancellation_cutoff_minutes": cutoff,
                "opening_hours": [
                    {"weekday": day, "opens": "08:00", "closes": "23:00"}
                    for day in ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
                ],
                "tables": [
                    {"id": "t_1", "label": "1", "capacity": 2},
                    {"id": "t_2", "label": "2", "capacity": 4},
                    {"id": "t_3", "label": "3", "capacity": 6},
                ],
            }
        ],
        "reservations": reservations or [],
    }


class ServiceApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.api = TablekeeperService()
        response = await self.request("POST", "/_test/reset", fixture())
        self.assertEqual(response.status, 204)
        self.ada = await self.login("ada@example.com")
        self.bob = await self.login("bob@example.com")
        self.day = (date.today() + timedelta(days=14)).isoformat()

    async def request(self, method, path, body=None, *, token=None, key=None):
        headers = {}
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        if key is not None:
            headers["Idempotency-Key"] = key
        return await self.api.handle(method, path, headers, body)

    async def login(self, email):
        result = await self.request(
            "POST", "/auth/login", {"email": email, "password": "correct horse"}
        )
        self.assertEqual(result.status, 200)
        return result.body["token"]

    def booking(self, *, table="t_2", at="19:00", party=4, **extra):
        return {
            "restaurant_id": "r_anker",
            "table_id": table,
            "starts_at_local": at if "T" in at else f"{self.day}T{at}",
            "party_size": party,
            **extra,
        }

    async def book(self, *, token=None, key="booking-key", **kwargs):
        return await self.request(
            "POST",
            "/reservations",
            self.booking(**kwargs),
            token=token or self.ada,
            key=key,
        )

    async def test_public_restaurant_and_availability_shapes(self):
        listing = await self.request("GET", "/restaurants")
        self.assertEqual(listing.status, 200)
        self.assertEqual(listing.body["restaurants"], [
            {"id": "r_anker", "name": "Zum Anker", "timezone": "Europe/Berlin"}
        ])
        detail = await self.request("GET", "/restaurants/r_anker")
        self.assertEqual(detail.status, 200)
        self.assertEqual(len(detail.body["tables"]), 3)
        result = await self.request(
            "GET",
            f"/availability?restaurant_id=r_anker&date={self.day}&party_size=4&ignored=x",
        )
        self.assertEqual(result.status, 200)
        self.assertEqual(result.body["slots"][0]["available_table_ids"], ["t_2", "t_3"])
        self.assertTrue(result.body["slots"][0]["starts_at"].endswith(("+01:00", "+02:00")))

    async def test_availability_parameter_validation_and_closed_day(self):
        for path in (
            "/availability",
            f"/availability?restaurant_id=r_anker&date={self.day}",
            f"/availability?restaurant_id=r_anker&date={self.day}&party_size=4.0",
            "/availability?restaurant_id=r_anker&date=2026-02-30&party_size=2",
            f"/availability?restaurant_id=r_anker&date={self.day}&party_size=0",
        ):
            response = await self.request("GET", path)
            self.assertEqual((response.status, response.body["error"]["code"]), (422, "validation_failed"))
        snapshot = fixture()
        snapshot["restaurants"][0]["opening_hours"] = []
        await self.request("POST", "/_test/reset", snapshot)
        closed = await self.request(
            "GET", f"/availability?restaurant_id=r_anker&date={self.day}&party_size=1"
        )
        self.assertEqual(closed.body["slots"], [])

    async def test_large_numeric_inputs_do_not_cause_server_errors(self):
        huge_party = await self.request(
            "GET",
            f"/availability?restaurant_id=r_anker&date={self.day}&party_size={'9' * 5000}",
        )
        self.assertEqual(huge_party.status, 200)
        self.assertTrue(huge_party.body["slots"])
        self.assertTrue(all(not slot["available_table_ids"] for slot in huge_party.body["slots"]))

        snapshot = fixture()
        snapshot["restaurants"][0]["reservation_duration_minutes"] = 10**30
        reset = await self.request("POST", "/_test/reset", snapshot)
        self.assertEqual(reset.status, 204)
        self.ada = await self.login("ada@example.com")
        no_slots = await self.request(
            "GET", f"/availability?restaurant_id=r_anker&date={self.day}&party_size=2"
        )
        self.assertEqual((no_slots.status, no_slots.body["slots"]), (200, []))
        booking = await self.book(key="duration-too-long")
        self.assertEqual(
            (booking.status, booking.body["error"]["code"]),
            (422, "outside_opening_hours"),
        )

    async def test_signup_login_and_bearer_authentication(self):
        signup = await self.request(
            "POST",
            "/auth/signup",
            {"email": "new@example.com", "password": "eight chars", "display_name": "New"},
        )
        self.assertEqual(signup.status, 201)
        protected = await self.request("GET", "/reservations", token=signup.body["token"])
        self.assertEqual(protected.body, {"reservations": []})
        duplicate = await self.request(
            "POST",
            "/auth/signup",
            {"email": "ADA@example.com", "password": "correct horse", "display_name": "X"},
        )
        self.assertEqual((duplicate.status, duplicate.body["error"]["code"]), (409, "email_taken"))
        wrong_type = await self.request(
            "POST", "/auth/signup", {"email": 5, "password": "correct horse", "display_name": "X"}
        )
        self.assertEqual((wrong_type.status, wrong_type.body["error"]["code"]), (400, "malformed_request"))
        unauthorized = await self.request("GET", "/reservations", token="unknown")
        self.assertEqual((unauthorized.status, unauthorized.body["error"]["code"]), (401, "unauthenticated"))

    async def test_create_conflict_half_open_and_availability_release(self):
        first = await self.book(key="first", at="19:00")
        self.assertEqual(first.status, 201)
        self.assertRegex(first.body["reference"], r"^[A-Z0-9]{6,12}$")
        self.assertTrue(first.body["starts_at"].endswith(("+01:00", "+02:00")))
        blocked = await self.book(key="second", at="20:00")
        self.assertEqual((blocked.status, blocked.body["error"]["code"]), (409, "table_unavailable"))
        adjacent = await self.book(key="third", at="20:30")
        self.assertEqual(adjacent.status, 201)
        availability = await self.request(
            "GET", f"/availability?restaurant_id=r_anker&date={self.day}&party_size=4"
        )
        times = {
            slot["starts_at_local"].split("T")[1]: slot["available_table_ids"]
            for slot in availability.body["slots"]
        }
        self.assertNotIn("t_2", times["19:00"])
        self.assertNotIn("t_2", times["21:30"])

    async def test_create_validation_codes_and_malformed_json_shape(self):
        cases = [
            (self.booking(at="19:15"), "not_on_slot_grid"),
            (self.booking(at="23:00"), "outside_opening_hours"),
            (self.booking(table="t_1"), "party_exceeds_capacity"),
            (self.booking(party="4"), "validation_failed"),
            (self.booking(at="2026-10-25T08:15"), "not_on_slot_grid"),
            ({"restaurant_id": "r_anker", "table_id": "t_2", "party_size": 4}, "validation_failed"),
            (self.booking(restaurant_id="r_nope"), "not_found"),
            (self.booking(table="t_missing"), "not_found"),
        ]
        for body, code in cases:
            response = await self.request("POST", "/reservations", body, token=self.ada, key=f"key-{code}-{id(body)}")
            self.assertEqual(response.body["error"]["code"], code)
        missing_key = await self.request("POST", "/reservations", self.booking(), token=self.ada)
        self.assertEqual((missing_key.status, missing_key.body["error"]["code"]), (400, "missing_idempotency_key"))

    async def test_idempotency_replay_scope_failure_retry_and_replay_after_cancel(self):
        key = "same-key"
        first = await self.book(key=key)
        replay = await self.book(key=key)
        self.assertEqual(first.status, 201)
        self.assertEqual((replay.status, replay.body), (200, first.body))
        changed = await self.request(
            "POST", "/reservations", self.booking(party=3), token=self.ada, key=key
        )
        self.assertEqual((changed.status, changed.body["error"]["code"]), (409, "idempotency_key_reuse"))
        bob = await self.book(token=self.bob, key=key, table="t_3")
        self.assertEqual(bob.status, 201)
        canceled = await self.request(
            "POST", f"/reservations/{first.body['reference']}/cancel", token=self.ada
        )
        self.assertEqual(canceled.status, 200)
        replay_after_cancel = await self.book(key=key)
        self.assertEqual(replay_after_cancel.body, first.body)

        retry = await self.book(key="retry", table="missing")
        self.assertEqual(retry.status, 404)
        retry = await self.book(key="retry", table="t_2")
        self.assertEqual(retry.status, 201)

    async def test_concurrent_same_key_creates_once(self):
        results = await asyncio.gather(*[self.book(key="concurrent") for _ in range(20)])
        self.assertEqual(sum(result.status == 201 for result in results), 1)
        self.assertEqual(sum(result.status == 200 for result in results), 19)
        self.assertEqual(len({result.body["reference"] for result in results}), 1)

    async def test_concurrent_distinct_keys_never_double_book(self):
        results = await asyncio.gather(*[self.book(key=f"race-{index}") for index in range(20)])
        self.assertEqual(sum(result.status == 201 for result in results), 1)
        self.assertEqual(sum(
            result.status == 409 and result.body["error"]["code"] == "table_unavailable"
            for result in results
        ), 19)

    async def test_owner_only_reads_cancel_and_amendment(self):
        created = await self.book(key="owner")
        reference = created.body["reference"]
        hidden = await self.request("GET", f"/reservations/{reference}", token=self.bob)
        self.assertEqual((hidden.status, hidden.body["error"]["code"]), (404, "not_found"))
        own = await self.request("GET", f"/reservations/{reference}", token=self.ada)
        self.assertEqual(own.body, created.body)
        amended = await self.request(
            "PATCH",
            f"/reservations/{reference}",
            {"table_id": "t_3", "ignored": "yes"},
            token=self.ada,
        )
        self.assertEqual(amended.status, 200)
        self.assertEqual(amended.body["reference"], reference)
        self.assertEqual(amended.body["reservation_id"], created.body["reservation_id"])
        cancelled = await self.request("POST", f"/reservations/{reference}/cancel", token=self.ada)
        self.assertEqual(cancelled.body["status"], "cancelled")
        slots = await self.request(
            "GET", f"/availability?restaurant_id=r_anker&date={self.day}&party_size=4"
        )
        at_seven = next(s for s in slots.body["slots"] if s["starts_at_local"].endswith("T19:00"))
        self.assertIn("t_2", at_seven["available_table_ids"])
        again = await self.request("POST", f"/reservations/{reference}/cancel", token=self.ada)
        self.assertEqual(again.body["status"], "cancelled")
        patch_cancelled = await self.request("PATCH", f"/reservations/{reference}", {"party_size": 1}, token=self.ada)
        self.assertEqual((patch_cancelled.status, patch_cancelled.body["error"]["code"]), (409, "reservation_cancelled"))

    async def test_failed_patch_does_not_change_existing_booking(self):
        created = await self.book(key="patch-atomic")
        reference = created.body["reference"]
        blocker = await self.book(key="blocker", at="19:00", table="t_3")
        self.assertEqual(blocker.status, 201)
        failed = await self.request(
            "PATCH", f"/reservations/{reference}", {"table_id": "t_3"}, token=self.ada
        )
        self.assertEqual((failed.status, failed.body["error"]["code"]), (409, "table_unavailable"))
        current = await self.request("GET", f"/reservations/{reference}", token=self.ada)
        self.assertEqual(current.body["table_id"], "t_2")

    async def test_cutoff_applies_to_cancel_and_patch(self):
        snapshot = fixture(cutoff=60 * 24 * 3650)
        await self.request("POST", "/_test/reset", snapshot)
        self.ada = await self.login("ada@example.com")
        created = await self.book(key="cutoff")
        reference = created.body["reference"]
        for method, payload in (("POST", None), ("PATCH", {"table_id": "t_3"})):
            result = await self.request(
                method, f"/reservations/{reference}/cancel" if method == "POST" else f"/reservations/{reference}",
                payload, token=self.ada,
            )
            self.assertEqual((result.status, result.body["error"]["code"]), (409, "cutoff_passed"))

    async def test_timezone_gap_fold_and_absolute_duration(self):
        snapshot = fixture()
        snapshot["restaurants"][0]["opening_hours"] = [
            {"weekday": day, "opens": "00:00", "closes": "23:30"}
            for day in ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
        ]
        await self.request("POST", "/_test/reset", snapshot)
        self.ada = await self.login("ada@example.com")
        self.bob = await self.login("bob@example.com")
        spring = await self.book(
            key="spring", at="2026-03-29T02:30", table="t_2"
        )
        self.assertEqual((spring.status, spring.body["error"]["code"]), (422, "invalid_local_time"))
        folded = await self.book(key="fold", at="2026-10-25T02:00", table="t_2")
        self.assertEqual(folded.status, 201)
        self.assertTrue(folded.body["starts_at"].endswith("+02:00"))
        early = await self.book(key="fall-duration", at="2026-10-25T01:30", table="t_3")
        self.assertEqual(early.status, 201)
        self.assertIn("T02:00:00+01:00", early.body["ends_at"])
        slots = await self.request(
            "GET", "/availability?restaurant_id=r_anker&date=2026-10-25&party_size=4"
        )
        times = [slot["starts_at_local"] for slot in slots.body["slots"]]
        self.assertEqual(times.count("2026-10-25T02:00"), 1)
        self.assertEqual(times.count("2026-10-25T02:30"), 1)

    async def test_new_york_dst_and_cross_timezone_instants(self):
        snapshot = fixture()
        all_day = [
            {"weekday": day, "opens": "00:00", "closes": "23:30"}
            for day in ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
        ]
        snapshot["restaurants"][0]["opening_hours"] = all_day
        new_york = dict(snapshot["restaurants"][0])
        new_york.update(
            id="r_ny",
            name="New York",
            timezone="America/New_York",
            opening_hours=all_day,
            tables=[{"id": "t_ny", "label": "NY", "capacity": 4}],
        )
        snapshot["restaurants"].append(new_york)
        await self.request("POST", "/_test/reset", snapshot)
        self.ada = await self.login("ada@example.com")

        spring = await self.request(
            "POST",
            "/reservations",
            {"restaurant_id": "r_ny", "table_id": "t_ny", "starts_at_local": "2026-03-08T02:30", "party_size": 4},
            token=self.ada,
            key="ny-spring",
        )
        self.assertEqual((spring.status, spring.body["error"]["code"]), (422, "invalid_local_time"))
        fall = await self.request(
            "POST",
            "/reservations",
            {"restaurant_id": "r_ny", "table_id": "t_ny", "starts_at_local": "2026-11-01T01:00", "party_size": 4},
            token=self.ada,
            key="ny-fall",
        )
        self.assertEqual(fall.status, 201)
        self.assertTrue(fall.body["starts_at"].endswith("-04:00"))

        berlin = await self.request(
            "POST",
            "/reservations",
            {"restaurant_id": "r_anker", "table_id": "t_2", "starts_at_local": "2026-12-01T18:00", "party_size": 4},
            token=self.ada,
            key="berlin-instant",
        )
        ny = await self.request(
            "POST",
            "/reservations",
            {"restaurant_id": "r_ny", "table_id": "t_ny", "starts_at_local": "2026-12-01T12:00", "party_size": 4},
            token=self.ada,
            key="ny-instant",
        )
        self.assertEqual(berlin.status, 201)
        self.assertEqual(ny.status, 201)
        self.assertEqual(
            datetime.fromisoformat(berlin.body["starts_at"]),
            datetime.fromisoformat(ny.body["starts_at"]),
        )

    async def test_seeded_reservation_occupies_slot_and_is_owned(self):
        seeded = {
            "id": "res_seed",
            "reference": "SEED01",
            "user_id": "u_ada",
            **self.booking(),
        }
        await self.request("POST", "/_test/reset", fixture(reservations=[seeded]))
        self.ada = await self.login("ada@example.com")
        self.bob = await self.login("bob@example.com")
        booked = await self.book(key="seed-block")
        self.assertEqual((booked.status, booked.body["error"]["code"]), (409, "table_unavailable"))
        own = await self.request("GET", "/reservations/SEED01", token=self.ada)
        self.assertEqual(own.status, 200)
        other = await self.request("GET", "/reservations/SEED01", token=self.bob)
        self.assertEqual(other.status, 404)
        canceled = await self.request("POST", "/reservations/SEED01/cancel", token=self.ada)
        self.assertEqual(canceled.status, 200)

    async def test_atomic_batch_swap_and_conflict_rollback(self):
        first = await self.book(key="move-a", table="t_2", at="18:00")
        second = await self.book(key="move-b", table="t_3", at="18:00")
        swapped = await self.request(
            "POST",
            "/reservation-moves",
            {"moves": [
                {"reference": first.body["reference"], "table_id": "t_3"},
                {"reference": second.body["reference"], "table_id": "t_2"},
            ]},
            token=self.ada,
            key="swap",
        )
        self.assertEqual(swapped.status, 201)
        self.assertEqual([row["table_id"] for row in swapped.body["reservations"]], ["t_3", "t_2"])
        replay = await self.request(
            "POST", "/reservation-moves",
            {"moves": [
                {"reference": first.body["reference"], "table_id": "t_3"},
                {"reference": second.body["reference"], "table_id": "t_2"},
            ]}, token=self.ada, key="swap",
        )
        self.assertEqual((replay.status, replay.body), (200, swapped.body))

        third = await self.book(key="move-c", table="t_1", party=2, at="20:00")
        fourth = await self.book(key="move-d", table="t_2", party=4, at="20:00")
        failed = await self.request(
            "POST",
            "/reservation-moves",
            {"moves": [
                {"reference": third.body["reference"], "table_id": "t_3"},
                {"reference": fourth.body["reference"], "table_id": "t_3"},
            ]},
            token=self.ada,
            key="atomic-fail",
        )
        self.assertEqual((failed.status, failed.body["error"]["code"]), (409, "table_unavailable"))
        current = await self.request("GET", f"/reservations/{third.body['reference']}", token=self.ada)
        self.assertEqual(current.body["table_id"], "t_1")

    async def test_move_validation_and_cross_restaurant_rejection(self):
        booking = await self.book(key="move-validation")
        for moves in ([], [{}], [{"reference": booking.body["reference"]}] * 2):
            response = await self.request(
                "POST", "/reservation-moves", {"moves": moves}, token=self.ada, key=f"bad-{len(moves)}-{id(moves)}"
            )
            self.assertEqual((response.status, response.body["error"]["code"]), (422, "validation_failed"))
        hidden = await self.request(
            "POST", "/reservation-moves",
            {"moves": [{"reference": booking.body["reference"]}]},
            token=self.bob, key="wrong-owner",
        )
        self.assertEqual((hidden.status, hidden.body["error"]["code"]), (404, "not_found"))

    async def test_export_import_preserves_tokens_reservations_and_idempotency_receipts(self):
        first = await self.book(key="preserved-receipt")
        export = await self.request("GET", "/_test/export")
        self.assertEqual(export.status, 200)
        await self.request("POST", "/_test/reset", fixture())
        imported = await self.request("POST", "/_test/import", export.body)
        self.assertEqual(imported.status, 204)
        record = await self.request("GET", f"/reservations/{first.body['reference']}", token=self.ada)
        self.assertEqual(record.body, first.body)
        replay = await self.book(key="preserved-receipt")
        self.assertEqual((replay.status, replay.body), (200, first.body))
        bob_rows = await self.request("GET", "/reservations", token=self.bob)
        self.assertEqual(bob_rows.body, {"reservations": []})

    async def test_invalid_import_and_reset_leave_current_state_safe(self):
        first = await self.book(key="state-safe")
        second = await self.book(key="state-safe-second", table="t_1", party=2)
        before = await self.request("GET", "/_test/export")
        for envelope in (
            {},
            {"track": "other", "format_version": 1, "state": {}},
            {"track": "tablekeeper", "format_version": 2, "state": {}},
            {"track": "tablekeeper", "format_version": 1, "state": {"users": []}},
        ):
            result = await self.request("POST", "/_test/import", envelope)
            self.assertEqual(result.status, 422)
        malformed_hash = await self.request("GET", "/_test/export")
        malformed_hash.body["state"]["users"]["u_ada"]["password_hash"] = (
            "scrypt$999999999$8$1$YWJj$YWJj"
        )
        rejected_hash = await self.request("POST", "/_test/import", malformed_hash.body)
        self.assertEqual(rejected_hash.status, 422)
        duplicate_id = await self.request("GET", "/_test/export")
        first_id = duplicate_id.body["state"]["reservations"][first.body["reference"]]["reservation_id"]
        duplicate_id.body["state"]["reservations"][second.body["reference"]]["reservation_id"] = first_id
        rejected_id = await self.request("POST", "/_test/import", duplicate_id.body)
        self.assertEqual(rejected_id.status, 422)
        after = await self.request("GET", "/_test/export")
        self.assertEqual(after.body, before.body)
        bad_fixture = fixture()
        bad_fixture["users"][0]["id"] = "x" * 65
        bad = await self.request("POST", "/_test/reset", bad_fixture)
        self.assertEqual((bad.status, bad.body["error"]["code"]), (422, "validation_failed"))
        remains = await self.request("GET", f"/reservations/{first.body['reference']}", token=self.ada)
        self.assertEqual(remains.status, 200)

    async def test_list_includes_cancelled_and_orders_start_descending(self):
        one = await self.book(key="order-one", at="18:00")
        two = await self.book(key="order-two", at="21:00")
        three = await self.book(key="order-three", at="19:30")
        rows = await self.request("GET", "/reservations", token=self.ada)
        self.assertEqual(
            [row["reference"] for row in rows.body["reservations"]],
            [two.body["reference"], three.body["reference"], one.body["reference"]],
        )
        await self.request("POST", f"/reservations/{one.body['reference']}/cancel", token=self.ada)
        rows = await self.request("GET", "/reservations", token=self.ada)
        self.assertIn("cancelled", [row["status"] for row in rows.body["reservations"]])


if __name__ == "__main__":
    unittest.main()