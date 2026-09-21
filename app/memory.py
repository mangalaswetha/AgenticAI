"""agent schema on Supabase: threads, messages, runs (queue), steps, tool_calls."""
import json
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.db import get_client

TERMINAL = ("succeeded", "failed", "cancelled", "dead")


@dataclass(frozen=True)
class Claimed:
    run_id: str
    thread_id: str
    attempts: int


class RunStore:
    def __init__(self, clock: Callable[[], float] = time.time):
        self.client = get_client()
        self.clock = clock

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------------ threads & messages

    def create_thread(self, student_id: str) -> str:
        thread_id = str(uuid.uuid4())
        self.client.schema("agent").table("thread").insert({
            "id": thread_id,
            "student_id": student_id,
        }).execute()
        return thread_id

    def get_thread(self, thread_id: str) -> dict | None:
        r = (
            self.client.schema("agent")
            .table("thread")
            .select("*")
            .eq("id", thread_id)
            .maybe_single()
            .execute()
        )
        return r.data

    def append_message(self, thread_id: str, role: str, text: str) -> int:
        # get next seq
        existing = (
            self.client.schema("agent")
            .table("message")
            .select("seq")
            .eq("thread_id", thread_id)
            .order("seq", desc=True)
            .limit(1)
            .execute()
        )
        next_seq = 1
        if existing.data:
            next_seq = existing.data[0]["seq"] + 1

        r = (
            self.client.schema("agent")
            .table("message")
            .insert({
                "thread_id": thread_id,
                "seq": next_seq,
                "role": role,
                "text": text,
            })
            .execute()
        )
        return next_seq

    def load_history(self, thread_id: str) -> list[dict]:
        r = (
            self.client.schema("agent")
            .table("message")
            .select("seq, role, text")
            .eq("thread_id", thread_id)
            .order("seq")
            .execute()
        )
        return r.data or []

    # ------------------------------------------------------------------ run steps

    def record_model_step(self, run_id: str, seq: int, tokens_in: int, tokens_out: int,
                          text: str | None, tool_calls: list[dict]) -> int:
        r = (
            self.client.schema("agent")
            .table("run_step")
            .insert({
                "run_id": run_id,
                "seq": seq,
                "kind": "model",
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "text": text,
                "tool_calls": tool_calls,
            })
            .execute()
        )
        # update run totals
        self.client.schema("agent").table("run").update({
            "tokens_in": self.client.schema("agent").table("run")
                .select("tokens_in").eq("id", run_id).single().execute().data["tokens_in"] + tokens_in,
            "tokens_out": self.client.schema("agent").table("run")
                .select("tokens_out").eq("id", run_id).single().execute().data["tokens_out"] + tokens_out,
        }).eq("id", run_id).execute()
        return r.data[0]["id"]
    def reap_expired(self) -> list[str]:
        """Put expired leases back to queued (or mark dead). Return the run ids touched."""
        now = datetime.now(timezone.utc).isoformat()
        expired = (
            self.client.schema("agent")
            .table("run")
            .select("id, attempts, max_attempts")
            .eq("status", "running")
            .lt("lease_until", now)
            .execute()
        ).data or []

        touched = []
        for run in expired:
            if run["attempts"] >= run["max_attempts"]:
                new_status = "dead"
                error_code = "lease_expired"
            else:
                new_status = "queued"
                error_code = "lease_expired"

            self.client.schema("agent").table("run").update({
                "status": new_status,
                "error_code": error_code,
                "lease_owner": None,
                "lease_until": None,
                "available_at": now,
            }).eq("id", run["id"]).execute()
            touched.append(run["id"])
        return touched
    def record_tool_call(self, run_id: str, seq: int, name: str, args: dict, result: dict,
                         ok: bool, latency_ms: int, idempotency_key: str | None = None) -> int:
        step = (
            self.client.schema("agent")
            .table("run_step")
            .insert({
                "run_id": run_id,
                "seq": seq,
                "kind": "tool",
            })
            .execute()
        )
        step_id = step.data[0]["id"]

        self.client.schema("agent").table("tool_call").insert({
            "run_step_id": step_id,
            "tool_name": name,
            "args": args,
            "result": result,
            "ok": ok,
            "latency_ms": latency_ms,
            "idempotency_key": idempotency_key,
        }).execute()
        return step_id

    def load_steps(self, run_id: str) -> list[dict]:
        steps = (
            self.client.schema("agent")
            .table("run_step")
            .select("*")
            .eq("run_id", run_id)
            .order("seq")
            .execute()
        ).data or []

        result = []
        for s in steps:
            item = dict(s)
            if s["kind"] == "tool":
                tc = (
                    self.client.schema("agent")
                    .table("tool_call")
                    .select("*")
                    .eq("run_step_id", s["id"])
                    .maybe_single()
                    .execute()
                )
                if tc.data:
                    item["tool_name"] = tc.data["tool_name"]
                    item["args"] = tc.data["args"]
                    item["result"] = tc.data["result"]
                    item["ok"] = tc.data["ok"]
                    item["idempotency_key"] = tc.data.get("idempotency_key")
            result.append(item)
        return result

    # ------------------------------------------------------------------ queue / lease

    def enqueue(self, thread_id: str, text: str, model: str, max_attempts: int = 3) -> str:
        """Save the user's message and a queued run for it. Return the run id."""
        run_id = str(uuid.uuid4())
        now = self._now()

        # save the user message
        self.append_message(thread_id, "user", text)

        # create the run
        self.client.schema("agent").table("run").insert({
            "id": run_id,
            "thread_id": thread_id,
            "status": "queued",
            "model": model,
            "available_at": now,
            "attempts": 0,
            "max_attempts": max_attempts,
        }).execute()
        return run_id
    
    def claim_run(self, worker_id: str, lease_seconds: int = 30) -> Claimed | None:
        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()

        # find one claimable run
        rows = (
            self.client.schema("agent")
            .table("run")
            .select("*")
            .eq("status", "queued")
            .lte("available_at", now_iso)
            .order("available_at")
            .limit(1)
            .execute()
        ).data

        if not rows:
            return None

        run = rows[0]
        lease_until = (now + timedelta(seconds=lease_seconds)).isoformat()

        # try to take the lease
        updated = (
            self.client.schema("agent")
            .table("run")
            .update({
                "status": "running",
                "lease_owner": worker_id,
                "lease_until": lease_until,
                "attempts": run["attempts"] + 1,
                "started_at": now_iso,
            })
            .eq("id", run["id"])
            .eq("status", "queued")
            .execute()
        )

        if not updated.data:
            return None  # someone else got it

        return Claimed(
            run_id=run["id"],
            thread_id=run["thread_id"],
            attempts=run["attempts"] + 1,
        )
    def get_run(self, run_id: str) -> dict | None:
        r = (
            self.client.schema("agent")
            .table("run")
            .select("*")
            .eq("id", run_id)
            .maybe_single()
            .execute()
        )
        if not r.data:
            return None
        data = dict(r.data)
        data["steps"] = self.load_steps(run_id)
        return data

    def claim_next(self, worker_id: str, lease_seconds: float = 30) -> Claimed | None:
        """Same as claim_run – kept for compatibility with the original worker."""
        return self.claim_run(worker_id, int(lease_seconds))
    
    def heartbeat(self, run_id: str, worker_id: str, lease_seconds: int = 30) -> bool:
        now = datetime.now(timezone.utc)
        lease_until = (now + timedelta(seconds=lease_seconds)).isoformat()
        updated = (
            self.client.schema("agent")
            .table("run")
            .update({"lease_until": lease_until})
            .eq("id", run_id)
            .eq("lease_owner", worker_id)
            .eq("status", "running")
            .execute()
        )
        return bool(updated.data)

    def finish(self, run_id: str, status: str, error_code: str | None = None) -> None:
        self.client.schema("agent").table("run").update({
            "status": status,
            "finished_at": self._now(),
            "error_code": error_code,
            "lease_owner": None,
            "lease_until": None,
        }).eq("id", run_id).execute()

    def requeue_expired(self) -> int:
        """Reaper: put expired leases back to queued (or dead)."""
        now = datetime.now(timezone.utc).isoformat()
        expired = (
            self.client.schema("agent")
            .table("run")
            .select("*")
            .eq("status", "running")
            .lt("lease_until", now)
            .execute()
        ).data or []

        count = 0
        for run in expired:
            if run["attempts"] >= run["max_attempts"]:
                new_status = "dead"
            else:
                new_status = "queued"

            self.client.schema("agent").table("run").update({
                "status": new_status,
                "lease_owner": None,
                "lease_until": None,
                "available_at": now,
            }).eq("id", run["id"]).execute()
            count += 1
        return count