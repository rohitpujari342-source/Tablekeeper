import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import unittest

sys.path.insert(0, str(Path(__file__).parents[1]))

from app.domain import DomainError
from app.security import hash_password, verify_password
from app.state import ServiceState, StateStore
from app.time_rules import has_overlap, resolve_local


class DomainCoreTests(unittest.TestCase):
    def test_scrypt_hashes_are_salted_and_verifiable(self):
        first = hash_password("correct horse battery staple")
        second = hash_password("correct horse battery staple")
        self.assertNotEqual(first, second)
        self.assertTrue(verify_password("correct horse battery staple", first))
        self.assertFalse(verify_password("wrong", first))

    def test_spring_gap_is_rejected_and_fallback_uses_first_occurrence(self):
        try:
            ZoneInfo("America/New_York")
        except ZoneInfoNotFoundError:
            self.skipTest("IANA timezone data is unavailable in this interpreter")
        with self.assertRaises(DomainError) as error:
            resolve_local("2024-03-10T02:30", "America/New_York")
        self.assertEqual(error.exception.code, "invalid_local_time")
        self.assertEqual(resolve_local("2024-11-03T01:30", "America/New_York").fold, 0)

    def test_half_open_intervals_allow_back_to_back_bookings(self):
        start = datetime(2024, 1, 1, 12, tzinfo=timezone.utc)
        self.assertFalse(has_overlap(start, start + timedelta(hours=1), [(start + timedelta(hours=1), start + timedelta(hours=2))]))

    def test_failed_transaction_never_swaps_candidate(self):
        async def run():
            store = StateStore()

            def mutation(candidate):
                candidate.users["u1"] = {"email": "owner@example.test"}
                raise DomainError(422, "validation_failed", "nope")

            with self.assertRaises(DomainError):
                await store.transaction(mutation)
            self.assertEqual((await store.snapshot()).users, {})

        asyncio.run(run())

    def test_concurrent_identical_idempotency_key_commits_once_and_replays(self):
        async def run():
            store = StateStore()
            calls = 0

            async def mutation(candidate):
                nonlocal calls
                calls += 1
                candidate.reservations["R1"] = {"reference": "R1"}
                return 201, {"reference": "R1"}

            results = await asyncio.gather(*[
                store.idempotent_write(user_id="u", method="POST", path="/reservations", key="k", request_body={"x": 1}, mutation=mutation)
                for _ in range(8)
            ])
            self.assertEqual(calls, 1)
            self.assertEqual(sum(not replay for _, _, replay in results), 1)
            self.assertEqual({status for status, _, _ in results}, {200, 201})
            with self.assertRaises(DomainError) as error:
                await store.idempotent_write(user_id="u", method="POST", path="/reservations", key="k", request_body={"x": 2}, mutation=mutation)
            self.assertEqual(error.exception.code, "idempotency_key_reuse")

        asyncio.run(run())

    def test_failed_idempotent_write_leaves_key_and_state_reusable(self):
        async def run():
            store = StateStore()

            def rejected(candidate):
                candidate.reservations["R1"] = {"reference": "R1"}
                raise DomainError(422, "validation_failed", "invalid booking")

            with self.assertRaises(DomainError):
                await store.idempotent_write(user_id="u", method="POST", path="/reservations", key="k", request_body={"x": 1}, mutation=rejected)
            self.assertEqual((await store.snapshot()).reservations, {})

            def accepted(candidate):
                candidate.reservations["R1"] = {"reference": "R1"}
                return 201, {"reference": "R1"}

            status, body, replayed = await store.idempotent_write(user_id="u", method="POST", path="/reservations", key="k", request_body={"x": 1}, mutation=accepted)
            self.assertEqual((status, body, replayed), (201, {"reference": "R1"}, False))

        asyncio.run(run())

    def test_export_import_preserves_successful_receipts_and_secrets(self):
        async def run():
            store = StateStore(ServiceState(users={"u": {"password_hash": hash_password("p")}}, tokens={"t": "u"}))

            def mutation(candidate):
                candidate.reservations["R1"] = {"reference": "R1", "created_at": "2024-01-01T00:00:00+00:00"}
                return 201, {"reference": "R1"}

            await store.idempotent_write(user_id="u", method="POST", path="/reservations", key="k", request_body={"a": 1}, mutation=mutation)
            snapshot = await store.export()
            restored = StateStore()
            await restored.import_snapshot(snapshot)
            status, body, replayed = await restored.idempotent_write(user_id="u", method="POST", path="/reservations", key="k", request_body={"a": 1}, mutation=mutation)
            self.assertEqual((status, body, replayed), (200, {"reference": "R1"}, True))
            state = await restored.snapshot()
            self.assertTrue(verify_password("p", state.users["u"]["password_hash"]))
            self.assertEqual(state.tokens, {"t": "u"})

        asyncio.run(run())

    def test_invalid_import_does_not_replace_live_state(self):
        async def run():
            store = StateStore(ServiceState(users={"u": {"email": "owner@example.test"}}))
            with self.assertRaises(DomainError):
                await store.import_snapshot({"track": "tablekeeper", "format_version": 1, "state": {}})
            self.assertIn("u", (await store.snapshot()).users)

        asyncio.run(run())
