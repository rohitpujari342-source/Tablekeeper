import unittest
from datetime import date, timedelta
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[1]))

from app.service import (
    TablekeeperService,
    get_effective_policy,
    get_policy_0,
    extract_accepted_terms,
)


def make_fixture():
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
                "cancellation_cutoff_minutes": 60,
                "opening_hours": [
                    {"weekday": day, "opens": "08:00", "closes": "23:00"}
                    for day in ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
                ],
                "tables": [
                    {"id": "t_1", "label": "1", "capacity": 2},
                    {"id": "t_2", "label": "2", "capacity": 4},
                    {"id": "t_3", "label": "3", "capacity": 6},
                ],
                "manager_user_ids": ["u_ada"],
            }
        ],
        "reservations": [],
    }


def sample_policy_payload(effective_from="2026-10-01", **overrides):
    payload = {
        "effective_from": effective_from,
        "slot_minutes": 30,
        "reservation_duration_minutes": 120,
        "cancellation_cutoff_minutes": 60,
        "opening_hours": [
            {"weekday": "mon", "opens": "18:00", "closes": "23:00"},
            {"weekday": "tue", "opens": "18:00", "closes": "23:00"},
        ],
        "capacities": {"t_1": 2, "t_2": 4, "t_3": 6},
    }
    payload.update(overrides)
    return payload


class PolicyFoundationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.api = TablekeeperService()
        reset_res = await self.api.handle("POST", "/_test/reset", {}, make_fixture())
        self.assertEqual(reset_res.status, 204)
        login_ada = await self.api.handle(
            "POST", "/auth/login", {}, {"email": "ada@example.com", "password": "correct horse"}
        )
        self.assertEqual(login_ada.status, 200)
        self.ada_token = login_ada.body["token"]

        login_bob = await self.api.handle(
            "POST", "/auth/login", {}, {"email": "bob@example.com", "password": "correct horse"}
        )
        self.assertEqual(login_bob.status, 200)
        self.bob_token = login_bob.body["token"]

    async def test_get_policies_initially_empty(self):
        res = await self.api.handle("GET", "/restaurants/r_anker/policies", {})
        self.assertEqual(res.status, 200)
        self.assertEqual(res.body, {"policies": []})

    async def test_get_policies_unknown_restaurant_404(self):
        res = await self.api.handle("GET", "/restaurants/r_unknown/policies", {})
        self.assertEqual(res.status, 404)

    async def test_publish_policy_auth_and_permissions(self):
        body = sample_policy_payload()
        headers_no_token = {"idempotency-key": "k1"}
        res_no_token = await self.api.handle("POST", "/restaurants/r_anker/policies", headers_no_token, body)
        self.assertEqual(res_no_token.status, 401)

        headers_bob = {"authorization": f"Bearer {self.bob_token}", "idempotency-key": "k1"}
        res_bob = await self.api.handle("POST", "/restaurants/r_anker/policies", headers_bob, body)
        self.assertEqual(res_bob.status, 403)

        headers_unknown_rest = {"authorization": f"Bearer {self.ada_token}", "idempotency-key": "k1"}
        res_unknown = await self.api.handle("POST", "/restaurants/r_unknown/policies", headers_unknown_rest, body)
        self.assertEqual(res_unknown.status, 404)

        headers_no_key = {"authorization": f"Bearer {self.ada_token}"}
        res_no_key = await self.api.handle("POST", "/restaurants/r_anker/policies", headers_no_key, body)
        self.assertEqual(res_no_key.status, 400)

    async def test_publish_policy_validations(self):
        headers = {"authorization": f"Bearer {self.ada_token}", "idempotency-key": "k-val"}

        invalid_cases = [
            sample_policy_payload(effective_from="2026-02-30"),  # invalid calendar date
            sample_policy_payload(effective_from="invalid-date"),
            sample_policy_payload(slot_minutes=True),  # boolean is not integer
            sample_policy_payload(slot_minutes=0),  # < 1
            sample_policy_payload(slot_minutes=1441),  # > 1440
            sample_policy_payload(reservation_duration_minutes=False),
            sample_policy_payload(reservation_duration_minutes=0),
            sample_policy_payload(cancellation_cutoff_minutes=-1),
            sample_policy_payload(cancellation_cutoff_minutes=10081),
            sample_policy_payload(opening_hours=[{"weekday": "mon", "opens": "18:00", "closes": "18:00"}]),  # closes not > opens
            sample_policy_payload(opening_hours=[  # duplicate weekday
                {"weekday": "mon", "opens": "10:00", "closes": "14:00"},
                {"weekday": "mon", "opens": "18:00", "closes": "22:00"},
            ]),
            sample_policy_payload(capacities={"t_1": 2, "t_2": 4}),  # missing t_3
            sample_policy_payload(capacities={"t_1": 2, "t_2": 4, "t_3": 6, "t_4": 8}),  # extra table
            sample_policy_payload(capacities={"t_1": 0, "t_2": 4, "t_3": 6}),  # cap < 1
            sample_policy_payload(capacities={"t_1": 101, "t_2": 4, "t_3": 6}),  # cap > 100
            sample_policy_payload(capacities={"t_1": True, "t_2": 4, "t_3": 6}),  # bool capacity
        ]

        for i, case in enumerate(invalid_cases):
            res = await self.api.handle("POST", "/restaurants/r_anker/policies", {"idempotency-key": f"inv-{i}", "authorization": f"Bearer {self.ada_token}"}, case)
            self.assertEqual(res.status, 422, f"Case {i} failed: {res.body}")

    async def test_publish_policy_success_and_idempotent_replay(self):
        headers = {"authorization": f"Bearer {self.ada_token}", "idempotency-key": "key-p1"}
        body = sample_policy_payload(effective_from="2026-10-01", extra_ignored_field="ignored")
        res1 = await self.api.handle("POST", "/restaurants/r_anker/policies", headers, body)
        self.assertEqual(res1.status, 201)
        self.assertEqual(res1.body["policy_version"], 1)
        self.assertEqual(res1.body["effective_from"], "2026-10-01")
        self.assertEqual(res1.body["reservation_duration_minutes"], 120)
        self.assertNotIn("extra_ignored_field", res1.body)

        # Replay with identical key returns 200 with original response
        replay = await self.api.handle("POST", "/restaurants/r_anker/policies", headers, body)
        self.assertEqual(replay.status, 200)
        self.assertEqual(replay.body["policy_version"], 1)

        # Publish a second policy with a different key
        headers2 = {"authorization": f"Bearer {self.ada_token}", "idempotency-key": "key-p2"}
        body2 = sample_policy_payload(effective_from="2026-11-01", reservation_duration_minutes=60)
        res2 = await self.api.handle("POST", "/restaurants/r_anker/policies", headers2, body2)
        self.assertEqual(res2.status, 201)
        self.assertEqual(res2.body["policy_version"], 2)
        self.assertEqual(res2.body["reservation_duration_minutes"], 60)

        # GET /restaurants/r_anker/policies returns both in publication order
        listing = await self.api.handle("GET", "/restaurants/r_anker/policies", {})
        self.assertEqual(listing.status, 200)
        self.assertEqual(len(listing.body["policies"]), 2)
        self.assertEqual([p["policy_version"] for p in listing.body["policies"]], [1, 2])

    async def test_effective_policy_determination(self):
        state = await self.api.store.snapshot()
        restaurant = state.restaurants["r_anker"]

        # 1. Before any published policy, Policy 0 applies
        p0 = get_effective_policy(restaurant, "2026-09-15")
        self.assertEqual(p0["policy_version"], 0)
        self.assertEqual(p0["slot_minutes"], 30)
        self.assertEqual(p0["reservation_duration_minutes"], 90)
        self.assertEqual(p0["cancellation_cutoff_minutes"], 60)
        self.assertEqual(p0["capacities"], {"t_1": 2, "t_2": 4, "t_3": 6})

        terms0 = extract_accepted_terms(p0)
        self.assertEqual(terms0["policy_version"], 0)
        self.assertNotIn("effective_from", terms0)

        # 2. Publish Policy 1 (effective 2026-10-01, duration 120)
        h1 = {"authorization": f"Bearer {self.ada_token}", "idempotency-key": "eff-1"}
        await self.api.handle("POST", "/restaurants/r_anker/policies", h1, sample_policy_payload("2026-10-01", reservation_duration_minutes=120))

        # 3. Publish Policy 2 (effective 2026-11-01, duration 60)
        h2 = {"authorization": f"Bearer {self.ada_token}", "idempotency-key": "eff-2"}
        await self.api.handle("POST", "/restaurants/r_anker/policies", h2, sample_policy_payload("2026-11-01", reservation_duration_minutes=60))

        # 4. Publish Policy 3 (same date 2026-11-01, duration 45) -> supersedes Policy 2 for future decisions
        h3 = {"authorization": f"Bearer {self.ada_token}", "idempotency-key": "eff-3"}
        await self.api.handle("POST", "/restaurants/r_anker/policies", h3, sample_policy_payload("2026-11-01", reservation_duration_minutes=45))

        state = await self.api.store.snapshot()
        restaurant = state.restaurants["r_anker"]

        # Date before 2026-10-01 -> Policy 0
        self.assertEqual(get_effective_policy(restaurant, "2026-09-30")["policy_version"], 0)

        # Date between 2026-10-01 and 2026-10-31 -> Policy 1 (duration 120)
        eff_oct = get_effective_policy(restaurant, "2026-10-15")
        self.assertEqual(eff_oct["policy_version"], 1)
        self.assertEqual(eff_oct["reservation_duration_minutes"], 120)

        # Date on/after 2026-11-01 -> Policy 3 wins over Policy 2 due to higher version tie-break
        eff_nov = get_effective_policy(restaurant, "2026-11-01")
        self.assertEqual(eff_nov["policy_version"], 3)
        self.assertEqual(eff_nov["reservation_duration_minutes"], 45)

    async def test_restaurant_detail_preserves_fixture_configuration(self):
        # Publishing a policy should not alter GET /restaurants/r_anker
        h = {"authorization": f"Bearer {self.ada_token}", "idempotency-key": "det-1"}
        await self.api.handle("POST", "/restaurants/r_anker/policies", h, sample_policy_payload("2026-10-01", reservation_duration_minutes=120))

        detail = await self.api.handle("GET", "/restaurants/r_anker", {})
        self.assertEqual(detail.status, 200)
        self.assertEqual(detail.body["reservation_duration_minutes"], 90)  # original fixture duration, not 120
        self.assertNotIn("policies", detail.body)

    async def test_export_import_with_policies(self):
        h = {"authorization": f"Bearer {self.ada_token}", "idempotency-key": "exp-1"}
        await self.api.handle("POST", "/restaurants/r_anker/policies", h, sample_policy_payload("2026-10-01"))

        export_res = await self.api.handle("GET", "/_test/export", {})
        self.assertEqual(export_res.status, 200)
        envelope = export_res.body

        # Re-import into a clean service
        fresh_api = TablekeeperService()
        import_res = await fresh_api.handle("POST", "/_test/import", {}, envelope)
        self.assertEqual(import_res.status, 204)

        # Verify policies were restored
        policies_res = await fresh_api.handle("GET", "/restaurants/r_anker/policies", {})
        self.assertEqual(policies_res.status, 200)
        self.assertEqual(len(policies_res.body["policies"]), 1)
        self.assertEqual(policies_res.body["policies"][0]["policy_version"], 1)


if __name__ == "__main__":
    unittest.main()
