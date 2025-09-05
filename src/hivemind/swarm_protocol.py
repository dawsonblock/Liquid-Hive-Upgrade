"""Swarm Protocol: Distributed State and Task Delegation
====================================================

This module implements the foundational infrastructure for LIQUID-HIVE swarm collaboration:
1. Redis-based distributed state management
2. Task delegation API for distributed problem-solving
3. Swarm coordination and synchronization

This transforms LIQUID-HIVE from a brilliant individual into a collaborative swarm intelligence.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from dataclasses import asdict, dataclass
from typing import Any

try:
    import redis.asyncio as redis
except ImportError:
    redis = None


@dataclass
class SwarmTask:
    """Represents a task that can be delegated across the swarm."""

    task_id: str
    task_type: str
    payload: dict[str, Any]
    requester_id: str
    priority: int = 1
    timeout_seconds: int = 300
    created_at: float = None
    assigned_to: str | None = None
    status: str = "pending"  # pending, assigned, completed, failed, timeout
    result: dict[str, Any] | None = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()


@dataclass
class SwarmNode:
    """Represents a node in the LIQUID-HIVE swarm."""

    node_id: str
    instance_url: str
    capabilities: list[str]
    load_factor: float = 0.0
    last_heartbeat: float = None
    status: str = "active"  # active, busy, offline

    def __post_init__(self):
        if self.last_heartbeat is None:
            self.last_heartbeat = time.time()


class SwarmCoordinator:
    """Swarm Protocol coordinator for distributed LIQUID-HIVE instances.

    Features:
    - Distributed state management via Redis
    - Task delegation and load balancing
    - Node discovery and health monitoring
    - Distributed knowledge graph synchronization
    """

    def __init__(self, node_id: str = None, redis_url: str = None):
        self.node_id = node_id or f"liquid-hive-{uuid.uuid4().hex[:8]}"
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379")
        self.redis_client = None
        self.logger = logging.getLogger(__name__)

        # Swarm state
        self.capabilities = [
            "text_generation",
            "vision_processing",
            "reasoning",
            "ethical_analysis",
        ]
        self.active_tasks: set[str] = set()
        self.max_concurrent_tasks = 3

        # Heartbeat configuration
        self.heartbeat_interval = 30  # seconds
        self.node_timeout = 90  # seconds
        self._heartbeat_task = None

    async def initialize(self) -> bool:
        """Initialize swarm coordinator and connect to Redis."""
        if not redis:
            self.logger.warning("Redis not available. Swarm protocol disabled.")
            return False

        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)

            # Test connection
            await self.redis_client.ping()

            # Register this node
            await self._register_node()

            # Start heartbeat
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

            self.logger.info(f"Swarm coordinator initialized for node {self.node_id}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize swarm coordinator: {e}")
            return False

    async def shutdown(self):
        """Gracefully shutdown swarm coordinator."""
        try:
            # Stop heartbeat
            if self._heartbeat_task:
                self._heartbeat_task.cancel()

            # Unregister node
            await self._unregister_node()

            # Close Redis connection
            if self.redis_client:
                await self.redis_client.close()

        except Exception as e:
            self.logger.error(f"Error during swarm shutdown: {e}")

    async def delegate_task(
        self, task_type: str, payload: dict[str, Any], priority: int = 1, timeout: int = 300
    ) -> dict[str, Any] | None:
        """Delegate a task to another node in the swarm.

        Args:
            task_type: Type of task (e.g., "reasoning", "vision_analysis")
            payload: Task data and parameters
            priority: Task priority (1-10, higher = more urgent)
            timeout: Maximum execution time in seconds

        Returns:
            Task result dict or None if delegation failed
        """
        if not self.redis_client:
            return None

        try:
            # Create task
            task = SwarmTask(
                task_id=f"task-{uuid.uuid4().hex}",
                task_type=task_type,
                payload=payload,
                requester_id=self.node_id,
                priority=priority,
                timeout_seconds=timeout,
            )

            # Find suitable node
            target_node = await self._find_best_node(task_type)
            if not target_node:
                self.logger.warning(f"No suitable node found for task type: {task_type}")
                return None

            # Queue task
            await self._queue_task(task)

            # Wait for completion
            result = await self._wait_for_task_completion(task.task_id, timeout)
            return result

        except Exception as e:
            self.logger.error(f"Task delegation failed: {e}")
            return None

    async def process_delegated_tasks(self):
        """Process tasks delegated to this node."""
        if not self.redis_client:
            return

        try:
            # Check for available task slots
            if len(self.active_tasks) >= self.max_concurrent_tasks:
                return

            # Get pending tasks for our capabilities
            tasks = await self._get_pending_tasks()

            for task_data in tasks:
                if len(self.active_tasks) >= self.max_concurrent_tasks:
                    break

                try:
                    task = SwarmTask(**task_data)

                    # Check if we can handle this task
                    if task.task_type in self.capabilities:
                        # Claim task
                        if await self._claim_task(task.task_id):
                            # Process task in background
                            asyncio.create_task(self._execute_task(task))

                except Exception as e:
                    self.logger.error(f"Error processing delegated task: {e}")
                    continue

        except Exception as e:
            self.logger.error(f"Error in process_delegated_tasks: {e}")

    async def sync_distributed_state(
        self, state_key: str, local_state: dict[str, Any]
    ) -> dict[str, Any]:
        """Synchronize distributed state across swarm nodes.

        Args:
            state_key: Key identifying the state type (e.g., "knowledge_graph", "adapter_state")
            local_state: Current local state

        Returns:
            Merged distributed state
        """
        if not self.redis_client:
            return local_state

        try:
            # Get distributed state
            distributed_key = f"swarm:state:{state_key}"
            distributed_data = await self.redis_client.hgetall(distributed_key)

            # Merge states (simple last-write-wins for now)
            merged_state = local_state.copy()

            for node_id, state_json in distributed_data.items():
                try:
                    node_state = json.loads(state_json)
                    # Merge logic here - could be more sophisticated
                    for key, value in node_state.items():
                        if key not in merged_state or node_state.get(
                            "timestamp", 0
                        ) > merged_state.get("timestamp", 0):
                            merged_state[key] = value
                except Exception:
                    continue

            # Update our state in distributed store
            local_state["timestamp"] = time.time()
            local_state["node_id"] = self.node_id
            await self.redis_client.hset(distributed_key, self.node_id, json.dumps(local_state))

            return merged_state

        except Exception as e:
            self.logger.error(f"State synchronization failed: {e}")
            return local_state

    async def _register_node(self):
        """Register this node in the swarm."""
        node = SwarmNode(
            node_id=self.node_id,
            instance_url="http://localhost:8001",  # Could be configured
            capabilities=self.capabilities,
        )

        await self.redis_client.hset("swarm:nodes", self.node_id, json.dumps(asdict(node)))

    async def _unregister_node(self):
        """Unregister this node from the swarm."""
        await self.redis_client.hdel("swarm:nodes", self.node_id)

    async def _heartbeat_loop(self):
        """Maintain node heartbeat and monitor swarm health."""
        while True:
            try:
                # Update our heartbeat
                await self._update_heartbeat()

                # Clean up stale nodes
                await self._cleanup_stale_nodes()

                # Process delegated tasks
                await self.process_delegated_tasks()

                await asyncio.sleep(self.heartbeat_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Heartbeat loop error: {e}")
                await asyncio.sleep(5)

    async def _update_heartbeat(self):
        """Update this node's heartbeat timestamp."""
        node_data = await self.redis_client.hget("swarm:nodes", self.node_id)
        if node_data:
            node = SwarmNode(**json.loads(node_data))
            node.last_heartbeat = time.time()
            node.load_factor = len(self.active_tasks) / self.max_concurrent_tasks

            await self.redis_client.hset("swarm:nodes", self.node_id, json.dumps(asdict(node)))

    async def _cleanup_stale_nodes(self):
        """Remove nodes that haven't sent heartbeats recently."""
        current_time = time.time()
        nodes_data = await self.redis_client.hgetall("swarm:nodes")

        for node_id, node_json in nodes_data.items():
            try:
                node = SwarmNode(**json.loads(node_json))
                if current_time - node.last_heartbeat > self.node_timeout:
                    await self.redis_client.hdel("swarm:nodes", node_id)
                    self.logger.info(f"Removed stale node: {node_id}")
            except Exception:
                continue

    async def _find_best_node(self, task_type: str) -> str | None:
        """Find the best node to handle a specific task type."""
        nodes_data = await self.redis_client.hgetall("swarm:nodes")

        best_node = None
        best_score = float("inf")

        for node_id, node_json in nodes_data.items():
            if node_id == self.node_id:  # Don't delegate to ourselves
                continue

            try:
                node = SwarmNode(**json.loads(node_json))

                # Check if node can handle this task type
                if task_type not in node.capabilities:
                    continue

                # Check if node is healthy
                if time.time() - node.last_heartbeat > 60:
                    continue

                # Score based on load factor (lower is better)
                score = node.load_factor

                if score < best_score:
                    best_score = score
                    best_node = node_id

            except Exception:
                continue

        return best_node

    async def _queue_task(self, task: SwarmTask):
        """Add task to the swarm task queue."""
        await self.redis_client.lpush(f"swarm:tasks:{task.task_type}", json.dumps(asdict(task)))

        # Set task status
        await self.redis_client.hset(
            "swarm:task_status",
            task.task_id,
            json.dumps({"status": "pending", "created_at": task.created_at}),
        )

    async def _get_pending_tasks(self) -> list[dict[str, Any]]:
        """Get pending tasks that this node can handle."""
        tasks = []

        for capability in self.capabilities:
            task_queue = f"swarm:tasks:{capability}"

            # Get tasks from queue (non-blocking)
            task_data = await self.redis_client.rpop(task_queue)
            if task_data:
                try:
                    tasks.append(json.loads(task_data))
                except Exception:
                    continue

        return tasks

    async def _claim_task(self, task_id: str) -> bool:
        """Claim a task for processing."""
        try:
            # Atomic claim using Redis
            result = await self.redis_client.hset(
                "swarm:task_status",
                task_id,
                json.dumps(
                    {"status": "assigned", "assigned_to": self.node_id, "assigned_at": time.time()}
                ),
            )

            if result:
                self.active_tasks.add(task_id)
                return True
            return False

        except Exception:
            return False

    async def _execute_task(self, task: SwarmTask):
        """Execute a delegated task."""
        try:
            self.logger.info(f"Executing task {task.task_id} of type {task.task_type}")

            # Task processing logic would go here
            # For now, simulate processing
            await asyncio.sleep(1)

            result = {
                "status": "completed",
                "result": f"Processed {task.task_type} task",
                "processed_by": self.node_id,
                "completed_at": time.time(),
            }

            # Update task status
            await self.redis_client.hset("swarm:task_status", task.task_id, json.dumps(result))

            self.active_tasks.discard(task.task_id)

        except Exception as e:
            self.logger.error(f"Task execution failed: {e}")

            # Mark task as failed
            await self.redis_client.hset(
                "swarm:task_status",
                task.task_id,
                json.dumps({"status": "failed", "error": str(e), "failed_at": time.time()}),
            )

            self.active_tasks.discard(task.task_id)

    async def _wait_for_task_completion(self, task_id: str, timeout: int) -> dict[str, Any] | None:
        """Wait for a delegated task to complete."""
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                status_data = await self.redis_client.hget("swarm:task_status", task_id)
                if status_data:
                    status = json.loads(status_data)

                    if status.get("status") == "completed":
                        return status.get("result")
                    elif status.get("status") == "failed":
                        self.logger.error(f"Delegated task failed: {status.get('error')}")
                        return None

                await asyncio.sleep(1)

            except Exception as e:
                self.logger.error(f"Error waiting for task completion: {e}")
                break

        # Timeout
        self.logger.warning(f"Task {task_id} timed out")
        return None


# Global swarm coordinator instance
_swarm_coordinator: SwarmCoordinator | None = None


async def get_swarm_coordinator() -> SwarmCoordinator | None:
    """Get global swarm coordinator instance."""
    global _swarm_coordinator

    if _swarm_coordinator is None:
        _swarm_coordinator = SwarmCoordinator()
        await _swarm_coordinator.initialize()

    return _swarm_coordinator
