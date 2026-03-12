"""Dispatcher - Routes events to Amplifier agents via recipes.

The Dispatcher matches events against subscription actions and invokes
Amplifier agents (preferably via recipes for resumability and audit trails).
"""

import asyncio
import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .models import Action, Event, EventType, Subscription
from .state import StateStore

logger = logging.getLogger(__name__)

# Event type to recipe mapping
# These are the recipes we created in amplifier-ado-event-monitor/recipes/
EVENT_RECIPE_MAP: dict[EventType, str] = {
    # PR events
    EventType.PR_COMMENT_NEW: "handle-pr-comment",
    EventType.PR_STATUS_CHANGED: "handle-pr-build-failure",
    EventType.PR_VOTE_CHANGED: "handle-pr-vote-change",
    # Work item events
    EventType.WI_COMMENT_ADDED: "handle-work-item-comment",
}

# Base path for recipes (relative to this package)
RECIPES_DIR = Path(__file__).parent.parent.parent / "recipes"


@dataclass
class DispatchResult:
    """Result of dispatching an event to an agent."""

    success: bool
    agent: str
    session_id: str | None = None
    error: str | None = None
    output: str | None = None


class Dispatcher:
    """Dispatches events to Amplifier agents."""

    def __init__(
        self,
        subscriptions: dict[str, Subscription],
        state_store: StateStore | None = None,
        amplifier_cmd: str = "amplifier",
    ) -> None:
        """Initialize the dispatcher.

        Args:
            subscriptions: Map of subscription_id -> Subscription
            state_store: State store for dispatch logging and DLQ
            amplifier_cmd: Path to amplifier CLI
        """
        self.subscriptions = subscriptions
        self.state_store = state_store
        self.amplifier_cmd = amplifier_cmd
        # Mutex per subscription to prevent concurrent dispatches
        self._locks: dict[str, asyncio.Lock] = {}

    def _get_lock(self, subscription_id: str) -> asyncio.Lock:
        """Get or create a lock for a subscription."""
        if subscription_id not in self._locks:
            self._locks[subscription_id] = asyncio.Lock()
        return self._locks[subscription_id]

    async def dispatch(self, event: Event) -> DispatchResult | None:
        """Dispatch an event to the appropriate agent.

        Uses a per-subscription mutex to prevent concurrent dispatches
        on the same entity (prevents race conditions).

        Dispatch priority:
        1. Recipe from EVENT_RECIPE_MAP (preferred - built-in recipes)
        2. Recipe from subscription action config
        3. Direct agent invocation (fallback)

        Args:
            event: The event to dispatch

        Returns:
            DispatchResult if an action was triggered, None if no matching action
        """
        subscription = self.subscriptions.get(event.subscription_id)
        if not subscription:
            logger.warning(f"No subscription found for event: {event.subscription_id}")
            return None

        # Check if we have a built-in recipe for this event type
        recipe_name = EVENT_RECIPE_MAP.get(event.event_type)
        if recipe_name:
            # Use built-in recipe
            recipe_path = RECIPES_DIR / f"{recipe_name}.yaml"
            if recipe_path.exists():
                lock = self._get_lock(event.subscription_id)
                async with lock:
                    context = self._build_recipe_context(event, subscription)
                    logger.info(f"Dispatching {event.event_type.value} via recipe {recipe_name}")
                    return await self._invoke_recipe(str(recipe_path), context)
            else:
                logger.warning(f"Recipe not found: {recipe_path}")

        # Fall back to subscription-configured action
        action = self._find_matching_action(event, subscription)
        if not action:
            logger.debug(f"No action matches event type: {event.event_type.value}")
            return None

        # Acquire lock for this subscription
        lock = self._get_lock(event.subscription_id)
        async with lock:
            return await self._invoke_agent(event, action, subscription)

    def _find_matching_action(self, event: Event, subscription: Subscription) -> Action | None:
        """Find the action that matches the event type."""
        event_type_str = event.event_type.value
        for action in subscription.actions:
            # Match trigger against event type (supports wildcards)
            if self._trigger_matches(action.trigger, event_type_str):
                return action
        return None

    def _trigger_matches(self, trigger: str, event_type: str) -> bool:
        """Check if a trigger pattern matches an event type.

        Supports:
        - Exact match: "pr.comment.new" matches "pr.comment.new"
        - Prefix wildcard: "pr.*" matches "pr.comment.new"
        - Category match: "new-comments" matches "pr.comment.new"
        """
        if trigger == event_type:
            return True
        if trigger.endswith(".*"):
            prefix = trigger[:-2]
            return event_type.startswith(prefix + ".")
        # Map friendly names to event types
        friendly_map = {
            "new-comments": ["pr.comment.new", "wi.comment.added"],
            "status-change": ["pr.status.changed", "wi.state.changed"],
            "vote-change": ["pr.vote.changed"],
            "push-update": ["pr.push"],
            "state-change": ["wi.state.changed"],
            "field-update": ["wi.field.updated"],
            "comment-added": ["wi.comment.added"],
        }
        if trigger in friendly_map:
            return event_type in friendly_map[trigger]
        return False

    async def _invoke_agent(
        self, event: Event, action: Action, subscription: Subscription
    ) -> DispatchResult:
        """Invoke an Amplifier agent for the event."""
        logger.info(f"Dispatching {event.event_type.value} to {action.agent} for {subscription.id}")

        # Build context for the agent
        context = self._build_context(event, action, subscription)

        try:
            if action.recipe:
                return await self._invoke_recipe(action.recipe, context)
            return await self._invoke_agent_direct(action.agent, action.behavior, context)
        except Exception as e:
            logger.exception(f"Failed to invoke agent {action.agent}")
            return DispatchResult(
                success=False,
                agent=action.agent,
                error=str(e),
            )

    def _build_context(
        self, event: Event, action: Action, subscription: Subscription
    ) -> dict[str, Any]:
        """Build context dictionary for agent invocation."""
        return {
            "event_type": event.event_type.value,
            "subscription_id": subscription.id,
            "org": subscription.org,
            "project": subscription.project,
            "repo": subscription.repo,
            "pr_id": subscription.pr_id,
            "work_item_id": subscription.work_item_id,
            "payload": event.payload,
            "behavior": action.behavior,
        }

    def _build_recipe_context(self, event: Event, subscription: Subscription) -> dict[str, Any]:
        """Build context dictionary for recipe invocation.

        Extracts relevant fields from event payload for recipe context variables.
        """
        context: dict[str, Any] = {
            "org": subscription.org,
            "project": subscription.project,
            "repo": subscription.repo,
            "pr_id": subscription.pr_id,
            "work_item_id": subscription.work_item_id,
        }

        payload = event.payload or {}

        # PR comment context
        if event.event_type == EventType.PR_COMMENT_NEW:
            context.update(
                {
                    "thread_id": payload.get("thread_id"),
                    "comment_id": payload.get("comment_id"),
                    "comment_author": payload.get("author") or event.author,
                    "comment_text": payload.get("content", ""),
                    "file_path": payload.get("file_path"),
                    "line_number": payload.get("line_number"),
                }
            )

        # PR vote change context
        elif event.event_type == EventType.PR_VOTE_CHANGED:
            context.update(
                {
                    "voter_name": payload.get("reviewer") or event.author,
                    "vote_type": payload.get("vote"),
                    "vote_comment": payload.get("comment"),
                }
            )

        # PR status/build failure context
        elif event.event_type == EventType.PR_STATUS_CHANGED:
            context.update(
                {
                    "build_id": payload.get("build_id"),
                    "failure_type": payload.get("status_type", "build"),
                    "build_url": payload.get("build_url"),
                }
            )

        # Work item comment context
        elif event.event_type == EventType.WI_COMMENT_ADDED:
            context.update(
                {
                    "comment_author": payload.get("author") or event.author,
                    "comment_text": payload.get("content", ""),
                    "comment_id": payload.get("comment_id"),
                }
            )

        return context

    async def _invoke_recipe(self, recipe_path: str, context: dict[str, Any]) -> DispatchResult:
        """Invoke an Amplifier recipe.

        Recipes provide resumability, approval gates, and audit trails.
        """
        cmd = [
            self.amplifier_cmd,
            "tool",
            "invoke",
            "recipes",
            "operation=execute",
            f"recipe_path={recipe_path}",
            f"context={json.dumps(context)}",
        ]

        result = await asyncio.to_thread(
            subprocess.run,
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode == 0:
            return DispatchResult(
                success=True,
                agent=f"recipe:{recipe_path}",
                output=result.stdout,
            )
        return DispatchResult(
            success=False,
            agent=f"recipe:{recipe_path}",
            error=result.stderr or result.stdout,
        )

    async def _invoke_agent_direct(
        self, agent: str, behavior: str | None, context: dict[str, Any]
    ) -> DispatchResult:
        """Invoke an Amplifier agent directly (fallback when no recipe)."""
        # Build instruction based on behavior
        instruction = self._build_instruction(behavior, context)

        cmd = [
            self.amplifier_cmd,
            "run",
            "--agent",
            agent,
            "--instruction",
            instruction,
            "--context",
            json.dumps(context),
        ]

        result = await asyncio.to_thread(
            subprocess.run,
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode == 0:
            return DispatchResult(
                success=True,
                agent=agent,
                output=result.stdout,
            )
        return DispatchResult(
            success=False,
            agent=agent,
            error=result.stderr or result.stdout,
        )

    def _build_instruction(self, behavior: str | None, context: dict[str, Any]) -> str:
        """Build agent instruction from behavior and context."""
        event_type = context.get("event_type", "unknown")

        if behavior == "address-feedback":
            return (
                f"A new comment was posted on PR #{context.get('pr_id')}. "
                "Review the feedback and implement any requested changes."
            )
        if behavior == "monitor-build":
            return (
                f"A new push was made to PR #{context.get('pr_id')}. "
                "Monitor the build status and report any failures."
            )
        if behavior == "sync-status":
            return (
                f"Work item #{context.get('work_item_id')} state changed. "
                "Sync the status and update any related items."
            )
        # Default instruction
        return f"Handle {event_type} event for subscription {context.get('subscription_id')}"
