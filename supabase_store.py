"""Authenticated-only cloud persistence. No administrator key or SQLite fallback."""
from copy import deepcopy

from auth_service import AccountError
from progress_store import PROFILE_FIELDS, validate_profile, validate_payload, validate_rating, history_frame


class SupabaseProgressStore:
    def __init__(self, session, page_size=500):
        self.session = session
        self.owner_id = session.user_id
        self.page_size = page_size

    def _pages(self, table, order):
        def load(client):
            result = []
            offset = 0
            while True:
                query = client.table(table).select("*").eq("user_id", self.owner_id)
                for column in order:
                    query = query.order(column)
                rows = query.range(offset, offset + self.page_size - 1).execute().data
                result.extend(rows)
                # Do not assume the server's configured page cap equals our page size.
                if not rows:
                    break
                offset += len(rows)
            if any(r.get("user_id") != self.owner_id for r in result):
                raise AccountError("Unexpected ownership in server response.")
            return result
        return self.session.protected(load)

    def load_profile(self):
        rows = self._pages("profiles", ["user_id"])
        if len(rows) != 1:
            raise AccountError("Account profile is unavailable. Ask the administrator to apply the accounts migration.")
        return validate_profile({k: rows[0][k] for k in PROFILE_FIELDS})

    def save_profile(self, profile):
        profile = validate_profile(profile)
        def save(client):
            rows = client.table("profiles").update(profile).eq("user_id", self.owner_id).execute().data
            if len(rows) != 1 or rows[0]["user_id"] != self.owner_id:
                raise AccountError("Profile was not saved. Retry.")
        self.session.protected(save)

    def save_attempts(self, attempts):
        payload = deepcopy(attempts)
        for attempt in payload:
            validate_payload(attempt)
        self.session.protected(lambda c: c.rpc("save_attempts", {"p_attempts": payload}).execute())

    def load_attempts(self):
        # The immutable payload is the authoritative saved snapshot, including verdicts.
        return [deepcopy(row["payload"]) for row in self._pages("attempts", ["submitted_at", "attempt_id"])]

    def load_history(self):
        return history_frame(self.load_attempts())

    def load_feedback_events(self):
        return self._pages("feedback_events", ["created_at", "feedback_event_id"])

    def record_feedback(self, attempt_id, rating):
        validate_rating(rating)
        response = self.session.protected(lambda c: c.rpc("record_feedback", {
            "p_attempt_id": attempt_id, "p_rating": deepcopy(rating),
        }).execute())
        return response.data is True
