"""library schema on Supabase: members, books, reservations, policy, idempotency."""
import time
from collections.abc import Callable
from app.db import get_client


class LibraryDb:
    def __init__(self, clock: Callable[[], float] = time.time):
        self.client = get_client()
        self.clock = clock

    # ------------------------------------------------------------------ reads

    def get_member(self, roll_no: str) -> dict | None:
        r = (
            self.client.schema("library")
            .table("member")
            .select("*")
            .eq("roll_no", roll_no)
            .maybe_single()
            .execute()
        )
        return r.data

    def policy(self, name: str) -> int:
        r = (
            self.client.schema("library")
            .table("policy")
            .select("value")
            .eq("name", name)
            .single()
            .execute()
        )
        return r.data["value"]

    def active_reservations(self, member_id: int) -> list[dict]:
        r = (
            self.client.schema("library")
            .table("reservation")
            .select("book_id, book:book_id(title)")
            .eq("member_id", member_id)
            .execute()
        )
        rows = r.data or []
        return [{"book_id": row["book_id"], "title": row["book"]["title"]} for row in rows]

    def search_books(self, text: str, limit: int = 5) -> list[dict]:
        like = f"%{text.strip()}%"
        r = (
            self.client.schema("library")
            .table("book")
            .select("id, title, author, subject, copies_available")
            .or_(f"title.ilike.{like},author.ilike.{like},subject.ilike.{like}")
            .limit(limit)
            .execute()
        )
        return r.data or []

    def get_book(self, book_id: int) -> dict | None:
        r = (
            self.client.schema("library")
            .table("book")
            .select("*")
            .eq("id", book_id)
            .maybe_single()
            .execute()
        )
        return r.data

    def count(self, table: str) -> int:
        r = (
            self.client.schema("library")
            .table(table)
            .select("*", count="exact")
            .execute()
        )
        return r.count or 0

    # ------------------------------------------------------------------ safe writes

    def reserve(self, member_id: int, book_id: int) -> str:
        """Returns 'reserved', 'already_reserved' or 'no_copies'. Safe to repeat."""
        # already reserved?
        existing = (
            self.client.schema("library")
            .table("reservation")
            .select("id")
            .eq("member_id", member_id)
            .eq("book_id", book_id)
            .maybe_single()
            .execute()
        )
        if existing.data:
            return "already_reserved"

        # get current book state
        book = (
            self.client.schema("library")
            .table("book")
            .select("version, copies_available")
            .eq("id", book_id)
            .single()
            .execute()
        ).data

        if book["copies_available"] <= 0:
            return "no_copies"

        # optimistic update with version check
        updated = (
            self.client.schema("library")
            .table("book")
            .update({
                "copies_available": book["copies_available"] - 1,
                "version": book["version"] + 1,
            })
            .eq("id", book_id)
            .eq("version", book["version"])
            .eq("copies_available", book["copies_available"])
            .execute()
        )

        if not updated.data:
            return "no_copies"  # lost the race

        # create reservation
        self.client.schema("library").table("reservation").insert({
            "member_id": member_id,
            "book_id": book_id,
        }).execute()

        return "reserved"

    def record_notification(self, roll_no: str, message: str, dedupe_key: str) -> tuple[int, bool]:
        try:
            r = (
                self.client.schema("library")
                .table("notification")
                .insert({
                    "roll_no": roll_no,
                    "message": message,
                    "dedupe_key": dedupe_key,
                })
                .execute()
            )
            return r.data[0]["id"], True
        except Exception:
            # already exists
            r = (
                self.client.schema("library")
                .table("notification")
                .select("id")
                .eq("dedupe_key", dedupe_key)
                .single()
                .execute()
            )
            return r.data["id"], False

    def once(self, key: str, tool_name: str, effect: Callable[[], dict]) -> tuple[dict, bool]:
        """Run a side effect at most once per idempotency key."""
        existing = (
            self.client.schema("library")
            .table("idempotency")
            .select("result")
            .eq("key", key)
            .maybe_single()
            .execute()
        )
        if existing.data is not None:
            return existing.data["result"], False

        result = effect()
        self.client.schema("library").table("idempotency").insert({
            "key": key,
            "tool_name": tool_name,
            "result": result,
        }).execute()
        return result, True