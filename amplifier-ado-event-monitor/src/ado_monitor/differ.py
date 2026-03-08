"""Differ - Stateless snapshot comparison to produce events.

The Differ is the heart of event detection. It takes two snapshots
(previous and current) and produces a list of typed events describing
what changed. It is intentionally stateless for easy testing.
"""

from .models import Event, EventType, Snapshot

# Authors to ignore (prevents infinite loops from our own actions)
IGNORE_AUTHORS: set[str] = {"Amplifier Bot", "amplifier[bot]"}


def diff_snapshots(previous: Snapshot | None, current: Snapshot) -> list[Event]:
    """Compare two snapshots and produce events for detected changes.

    Args:
        previous: The previous snapshot (None if first poll)
        current: The current snapshot from this poll

    Returns:
        List of events describing what changed
    """
    if previous is None:
        # First poll - no events (we don't know what's "new")
        return []

    events: list[Event] = []

    # Determine entity type from snapshot data
    if "threads" in current.data:
        events.extend(_diff_pr_threads(previous, current))
    if "iterations" in current.data:
        events.extend(_diff_pr_iterations(previous, current))
    if "status" in current.data and "pr_id" in current.data:
        events.extend(_diff_pr_status(previous, current))
    if "votes" in current.data:
        events.extend(_diff_pr_votes(previous, current))
    if "latest_revision" in current.data:
        events.extend(_diff_wi_revisions(previous, current))
    if "comments" in current.data and "work_item_id" in current.data:
        events.extend(_diff_wi_comments(previous, current))

    # Filter out events from ignored authors
    return _filter_ignored_authors(events)


def _diff_pr_threads(previous: Snapshot, current: Snapshot) -> list[Event]:
    """Detect new or resolved PR comment threads."""
    events: list[Event] = []

    prev_threads: dict[int, dict] = {t["id"]: t for t in previous.data.get("threads", [])}
    curr_threads: dict[int, dict] = {t["id"]: t for t in current.data.get("threads", [])}

    # New threads
    for thread_id, thread in curr_threads.items():
        if thread_id not in prev_threads:
            events.append(
                Event(
                    event_type=EventType.PR_COMMENT_NEW,
                    subscription_id=current.subscription_id,
                    payload={"thread": thread},
                    author=_get_thread_author(thread),
                )
            )
        else:
            # Check for new comments in existing thread
            prev_comment_count = len(prev_threads[thread_id].get("comments", []))
            curr_comment_count = len(thread.get("comments", []))
            if curr_comment_count > prev_comment_count:
                new_comments = thread.get("comments", [])[prev_comment_count:]
                for comment in new_comments:
                    events.append(
                        Event(
                            event_type=EventType.PR_COMMENT_NEW,
                            subscription_id=current.subscription_id,
                            payload={"thread": thread, "comment": comment},
                            author=_get_comment_author(comment),
                        )
                    )

            # Check for status change (resolved/closed)
            prev_status = prev_threads[thread_id].get("status")
            curr_status = thread.get("status")
            if prev_status != curr_status and curr_status in ("fixed", "closed", "resolved"):
                events.append(
                    Event(
                        event_type=EventType.PR_COMMENT_RESOLVED,
                        subscription_id=current.subscription_id,
                        payload={"thread": thread, "previous_status": prev_status},
                    )
                )

    return events


def _diff_pr_iterations(previous: Snapshot, current: Snapshot) -> list[Event]:
    """Detect new pushes/iterations on a PR."""
    events: list[Event] = []

    prev_iterations = previous.data.get("iterations", [])
    curr_iterations = current.data.get("iterations", [])

    if len(curr_iterations) > len(prev_iterations):
        new_iterations = curr_iterations[len(prev_iterations) :]
        for iteration in new_iterations:
            events.append(
                Event(
                    event_type=EventType.PR_PUSH,
                    subscription_id=current.subscription_id,
                    payload={"iteration": iteration},
                    author=iteration.get("author", {}).get("displayName"),
                )
            )

    return events


def _diff_pr_status(previous: Snapshot, current: Snapshot) -> list[Event]:
    """Detect PR status changes (active -> completed, etc.)."""
    events: list[Event] = []

    prev_status = previous.data.get("status")
    curr_status = current.data.get("status")

    if prev_status != curr_status:
        events.append(
            Event(
                event_type=EventType.PR_STATUS_CHANGED,
                subscription_id=current.subscription_id,
                payload={
                    "previous_status": prev_status,
                    "current_status": curr_status,
                    "pr_id": current.data.get("pr_id"),
                },
            )
        )

    return events


def _diff_pr_votes(previous: Snapshot, current: Snapshot) -> list[Event]:
    """Detect reviewer vote changes."""
    events: list[Event] = []

    prev_votes: dict[str, int] = previous.data.get("votes", {})
    curr_votes: dict[str, int] = current.data.get("votes", {})

    for reviewer, vote in curr_votes.items():
        if reviewer not in prev_votes or prev_votes[reviewer] != vote:
            events.append(
                Event(
                    event_type=EventType.PR_VOTE_CHANGED,
                    subscription_id=current.subscription_id,
                    payload={
                        "reviewer": reviewer,
                        "previous_vote": prev_votes.get(reviewer),
                        "current_vote": vote,
                    },
                    author=reviewer,
                )
            )

    return events


def _diff_wi_revisions(previous: Snapshot, current: Snapshot) -> list[Event]:
    """Detect work item field changes via revision history."""
    events: list[Event] = []

    prev_rev = previous.data.get("latest_revision", {})
    curr_rev = current.data.get("latest_revision", {})

    if prev_rev.get("rev") != curr_rev.get("rev"):
        # State change
        prev_state = prev_rev.get("fields", {}).get("System.State")
        curr_state = curr_rev.get("fields", {}).get("System.State")
        if prev_state != curr_state:
            events.append(
                Event(
                    event_type=EventType.WI_STATE_CHANGED,
                    subscription_id=current.subscription_id,
                    payload={
                        "previous_state": prev_state,
                        "current_state": curr_state,
                        "work_item_id": current.data.get("work_item_id"),
                    },
                    author=curr_rev.get("fields", {}).get("System.ChangedBy"),
                )
            )

        # Other field changes
        prev_fields = prev_rev.get("fields", {})
        curr_fields = curr_rev.get("fields", {})
        changed_fields = {
            k: (prev_fields.get(k), v)
            for k, v in curr_fields.items()
            if prev_fields.get(k) != v and k != "System.State"
        }
        if changed_fields:
            events.append(
                Event(
                    event_type=EventType.WI_FIELD_UPDATED,
                    subscription_id=current.subscription_id,
                    payload={
                        "changed_fields": changed_fields,
                        "work_item_id": current.data.get("work_item_id"),
                    },
                    author=curr_rev.get("fields", {}).get("System.ChangedBy"),
                )
            )

    return events


def _diff_wi_comments(previous: Snapshot, current: Snapshot) -> list[Event]:
    """Detect new comments on work items."""
    events: list[Event] = []

    prev_comments = previous.data.get("comments", [])
    curr_comments = current.data.get("comments", [])

    if len(curr_comments) > len(prev_comments):
        new_comments = curr_comments[len(prev_comments) :]
        for comment in new_comments:
            events.append(
                Event(
                    event_type=EventType.WI_COMMENT_ADDED,
                    subscription_id=current.subscription_id,
                    payload={
                        "comment": comment,
                        "work_item_id": current.data.get("work_item_id"),
                    },
                    author=comment.get("createdBy", {}).get("displayName"),
                )
            )

    return events


def _get_thread_author(thread: dict) -> str | None:
    """Extract the author from a thread's first comment."""
    comments = thread.get("comments", [])
    if comments:
        return _get_comment_author(comments[0])
    return None


def _get_comment_author(comment: dict) -> str | None:
    """Extract the author from a comment."""
    author = comment.get("author", {})
    return author.get("displayName") or author.get("uniqueName")


def _filter_ignored_authors(events: list[Event]) -> list[Event]:
    """Filter out events from ignored authors (anti-loop safety)."""
    return [e for e in events if e.author not in IGNORE_AUTHORS]
