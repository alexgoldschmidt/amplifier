"""Poller - Fetches current state from Azure DevOps APIs.

The Poller is responsible for calling ADO REST APIs to get the current
state of PRs and work items. It produces Snapshot objects that the Differ
then compares against previous state.
"""

from typing import Any

import httpx

from .models import Snapshot, Subscription, SubscriptionType


class ADOClient:
    """HTTP client for Azure DevOps REST APIs."""

    def __init__(
        self,
        org: str,
        base_url: str | None = None,
    ) -> None:
        """Initialize the ADO client.

        Args:
            org: Azure DevOps organization name
            base_url: Base URL override (for on-prem ADO Server)
        """
        self.org = org
        self.base_url = base_url or f"https://dev.azure.com/{org}"
        self._token: str | None = None
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=30.0,
        )

    async def _get_token(self) -> str:
        """Get AAD token via Azure CLI.

        Tokens are cached and refreshed automatically by Azure CLI.
        """
        import asyncio
        import subprocess

        result = await asyncio.to_thread(
            subprocess.run,
            [
                "az",
                "account",
                "get-access-token",
                "--resource",
                "499b84ac-1321-427f-aa17-267ca6975798",
                "--query",
                "accessToken",
                "-o",
                "tsv",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            msg = f"Failed to get AAD token: {result.stderr}"
            raise RuntimeError(msg)
        return result.stdout.strip()

    async def _ensure_auth(self) -> dict[str, str]:
        """Build headers with fresh AAD token."""
        self._token = await self._get_token()
        return {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._token}",
        }

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def get_pr_threads(self, project: str, repo: str, pr_id: int) -> list[dict[str, Any]]:
        """Get all comment threads on a PR.

        GET /{project}/_apis/git/repositories/{repo}/pullRequests/{prId}/threads
        """
        url = f"/{project}/_apis/git/repositories/{repo}/pullRequests/{pr_id}/threads"
        headers = await self._ensure_auth()
        response = await self._client.get(url, params={"api-version": "7.1"}, headers=headers)
        response.raise_for_status()
        return response.json().get("value", [])

    async def get_pr_iterations(self, project: str, repo: str, pr_id: int) -> list[dict[str, Any]]:
        """Get all iterations (pushes) on a PR.

        GET /{project}/_apis/git/repositories/{repo}/pullRequests/{prId}/iterations
        """
        url = f"/{project}/_apis/git/repositories/{repo}/pullRequests/{pr_id}/iterations"
        headers = await self._ensure_auth()
        response = await self._client.get(url, params={"api-version": "7.1"}, headers=headers)
        response.raise_for_status()
        return response.json().get("value", [])

    async def get_pr(self, project: str, repo: str, pr_id: int) -> dict[str, Any]:
        """Get PR details including status and votes.

        GET /{project}/_apis/git/repositories/{repo}/pullRequests/{prId}
        """
        url = f"/{project}/_apis/git/repositories/{repo}/pullRequests/{pr_id}"
        headers = await self._ensure_auth()
        response = await self._client.get(url, params={"api-version": "7.1"}, headers=headers)
        response.raise_for_status()
        return response.json()

    async def get_work_item(self, project: str, work_item_id: int) -> dict[str, Any]:
        """Get work item details.

        GET /{project}/_apis/wit/workitems/{id}
        """
        url = f"/{project}/_apis/wit/workitems/{work_item_id}"
        headers = await self._ensure_auth()
        response = await self._client.get(url, params={"api-version": "7.1"}, headers=headers)
        response.raise_for_status()
        return response.json()

    async def get_work_item_comments(self, project: str, work_item_id: int) -> list[dict[str, Any]]:
        """Get work item comments.

        GET /{project}/_apis/wit/workitems/{id}/comments
        """
        url = f"/{project}/_apis/wit/workitems/{work_item_id}/comments"
        headers = await self._ensure_auth()
        response = await self._client.get(
            url, params={"api-version": "7.1-preview"}, headers=headers
        )
        response.raise_for_status()
        return response.json().get("comments", [])


class Poller:
    """Polls Azure DevOps for entity state changes."""

    def __init__(self, client: ADOClient) -> None:
        """Initialize the poller.

        Args:
            client: ADO API client
        """
        self.client = client

    async def poll(self, subscription: Subscription) -> Snapshot:
        """Poll for the current state of a subscription's entity.

        Args:
            subscription: The subscription defining what to poll

        Returns:
            Snapshot containing current state
        """
        if subscription.type == SubscriptionType.PULL_REQUEST:
            return await self._poll_pr(subscription)
        if subscription.type == SubscriptionType.WORK_ITEM:
            return await self._poll_work_item(subscription)
        msg = f"Unknown subscription type: {subscription.type}"
        raise ValueError(msg)

    async def _poll_pr(self, subscription: Subscription) -> Snapshot:
        """Poll a PR for current state."""
        if not subscription.repo or not subscription.pr_id:
            msg = f"PR subscription {subscription.id} missing repo or pr_id"
            raise ValueError(msg)

        # Fetch all PR data in parallel for efficiency
        pr_data, threads, iterations = await self._fetch_pr_data(
            subscription.project,
            subscription.repo,
            subscription.pr_id,
        )

        # Extract votes from reviewers
        votes = {}
        for reviewer in pr_data.get("reviewers", []):
            reviewer_id = reviewer.get("uniqueName") or reviewer.get("id")
            if reviewer_id:
                votes[reviewer_id] = reviewer.get("vote", 0)

        return Snapshot(
            subscription_id=subscription.id,
            data={
                "pr_id": subscription.pr_id,
                "status": pr_data.get("status"),
                "merge_status": pr_data.get("mergeStatus"),
                "threads": threads,
                "iterations": iterations,
                "votes": votes,
            },
        )

    async def _fetch_pr_data(
        self, project: str, repo: str, pr_id: int
    ) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
        """Fetch PR data, threads, and iterations concurrently."""
        import asyncio

        pr_task = self.client.get_pr(project, repo, pr_id)
        threads_task = self.client.get_pr_threads(project, repo, pr_id)
        iterations_task = self.client.get_pr_iterations(project, repo, pr_id)

        return await asyncio.gather(pr_task, threads_task, iterations_task)

    async def _poll_work_item(self, subscription: Subscription) -> Snapshot:
        """Poll a work item for current state."""
        if not subscription.work_item_id:
            msg = f"Work item subscription {subscription.id} missing work_item_id"
            raise ValueError(msg)

        # Fetch work item and comments
        work_item = await self.client.get_work_item(subscription.project, subscription.work_item_id)
        comments = await self.client.get_work_item_comments(
            subscription.project, subscription.work_item_id
        )

        return Snapshot(
            subscription_id=subscription.id,
            data={
                "work_item_id": subscription.work_item_id,
                "latest_revision": {
                    "rev": work_item.get("rev"),
                    "fields": work_item.get("fields", {}),
                },
                "comments": comments,
            },
        )
