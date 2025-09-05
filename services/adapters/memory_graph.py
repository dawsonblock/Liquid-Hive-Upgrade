"""Memory graph management system for agent context and learning."""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class MemoryNode:
    """Represents a node in the memory graph."""
    
    # Identity
    node_id: str
    node_type: str  # "conversation", "fact", "preference", "context", "skill"
    
    # Content
    content: str
    metadata: Dict[str, Any] = None
    
    # Relationships
    parent_ids: List[str] = None
    child_ids: List[str] = None
    related_ids: List[str] = None
    
    # Temporal information
    created_at: datetime = None
    last_accessed: datetime = None
    access_count: int = 0
    
    # Importance and relevance
    importance_score: float = 0.5  # 0-1 scale
    decay_rate: float = 0.01  # How quickly importance decays
    
    # Context
    agent_id: str = None
    session_id: str = None
    user_id: str = None
    
    def __post_init__(self):
        """Initialize default values."""
        if self.metadata is None:
            self.metadata = {}
        if self.parent_ids is None:
            self.parent_ids = []
        if self.child_ids is None:
            self.child_ids = []
        if self.related_ids is None:
            self.related_ids = []
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.last_accessed is None:
            self.last_accessed = self.created_at
    
    def update_access(self):
        """Update access information."""
        self.last_accessed = datetime.utcnow()
        self.access_count += 1
    
    def calculate_current_importance(self) -> float:
        """Calculate current importance with decay."""
        age_hours = (datetime.utcnow() - self.created_at).total_seconds() / 3600
        decay_factor = max(0.1, 1.0 - (self.decay_rate * age_hours))
        
        # Boost importance based on recent access
        recent_access_boost = min(0.3, self.access_count * 0.05)
        
        return min(1.0, self.importance_score * decay_factor + recent_access_boost)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['last_accessed'] = self.last_accessed.isoformat()
        data['current_importance'] = self.calculate_current_importance()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryNode":
        """Create from dictionary representation."""
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['last_accessed'] = datetime.fromisoformat(data['last_accessed'])
        # Remove computed field
        data.pop('current_importance', None)
        return cls(**data)


class MemoryGraph:
    """Graph-based memory system for persistent agent learning and context."""
    
    def __init__(self, storage_path: str = "./memory", max_nodes: int = 10000):
        """Initialize the memory graph system.
        
        Args:
            storage_path: Path to store memory data
            max_nodes: Maximum number of nodes to keep in memory
        """
        self.storage_path = storage_path
        self.max_nodes = max_nodes
        
        # Core storage
        self.nodes: Dict[str, MemoryNode] = {}
        self.agent_nodes: Dict[str, Set[str]] = defaultdict(set)  # agent_id -> node_ids
        self.session_nodes: Dict[str, Set[str]] = defaultdict(set)  # session_id -> node_ids
        
        # Index structures for fast lookup
        self.content_index: Dict[str, Set[str]] = defaultdict(set)  # keyword -> node_ids
        self.type_index: Dict[str, Set[str]] = defaultdict(set)  # node_type -> node_ids
        self.importance_index = []  # List of (importance, node_id) tuples
        
        # Performance tracking
        self.memory_stats = {
            "nodes_created": 0,
            "nodes_accessed": 0,
            "nodes_pruned": 0,
            "memory_updates": 0,
            "avg_retrieval_time_ms": 0.0
        }
        
        # Recently accessed nodes cache
        self.access_cache = deque(maxlen=100)
        
        logger.info(
            "MemoryGraph initialized",
            storage_path=storage_path,
            max_nodes=max_nodes
        )
        
        # Load existing memory data
        self._load_memory()
    
    def _load_memory(self):
        """Load memory data from storage."""
        try:
            import os
            memory_file = os.path.join(self.storage_path, "memory_graph.json")
            
            if os.path.exists(memory_file):
                with open(memory_file, 'r') as f:
                    data = json.load(f)
                
                # Load nodes
                for node_data in data.get("nodes", []):
                    node = MemoryNode.from_dict(node_data)
                    self.nodes[node.node_id] = node
                    
                    # Update indices
                    self._index_node(node)
                
                logger.info("Memory graph loaded", node_count=len(self.nodes))
            else:
                logger.info("No existing memory data found")
                
        except Exception as e:
            logger.error("Error loading memory graph", error=str(e))
    
    def _save_memory(self):
        """Save memory data to storage."""
        try:
            import os
            os.makedirs(self.storage_path, exist_ok=True)
            
            memory_file = os.path.join(self.storage_path, "memory_graph.json")
            
            data = {
                "nodes": [node.to_dict() for node in self.nodes.values()],
                "stats": self.memory_stats,
                "saved_at": datetime.utcnow().isoformat()
            }
            
            with open(memory_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            logger.debug("Memory graph saved", node_count=len(self.nodes))
            
        except Exception as e:
            logger.error("Error saving memory graph", error=str(e))
    
    def _index_node(self, node: MemoryNode):
        """Add a node to indices for fast lookup.
        
        Args:
            node: Memory node to index
        """
        # Agent index
        if node.agent_id:
            self.agent_nodes[node.agent_id].add(node.node_id)
        
        # Session index
        if node.session_id:
            self.session_nodes[node.session_id].add(node.node_id)
        
        # Type index
        self.type_index[node.node_type].add(node.node_id)
        
        # Content index (simple keyword extraction)
        keywords = self._extract_keywords(node.content)
        for keyword in keywords:
            self.content_index[keyword].add(node.node_id)
        
        # Importance index (maintain sorted list)
        importance = node.calculate_current_importance()
        self.importance_index.append((importance, node.node_id))
        self.importance_index.sort(reverse=True)
        
        # Keep importance index manageable
        if len(self.importance_index) > self.max_nodes * 2:
            self.importance_index = self.importance_index[:self.max_nodes]
    
    def _extract_keywords(self, content: str, max_keywords: int = 10) -> Set[str]:
        """Extract keywords from content for indexing.
        
        Args:
            content: Text content to extract keywords from
            max_keywords: Maximum number of keywords to extract
            
        Returns:
            Set of keywords
        """
        # Simple keyword extraction (would use more sophisticated NLP in production)
        import re
        
        # Convert to lowercase and extract words
        words = re.findall(r'\b\w+\b', content.lower())
        
        # Filter out common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'can', 'must', 'i', 'you', 'he', 'she', 
            'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your',
            'his', 'her', 'its', 'our', 'their', 'this', 'that', 'these', 'those'
        }
        
        keywords = {word for word in words if len(word) > 2 and word not in stop_words}
        
        # Return most frequent keywords
        return set(list(keywords)[:max_keywords])
    
    async def store_memory(
        self,
        content: str,
        node_type: str,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        importance_score: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None,
        related_node_ids: Optional[List[str]] = None
    ) -> str:
        """Store a new memory node.
        
        Args:
            content: Memory content
            node_type: Type of memory node
            agent_id: Associated agent ID
            session_id: Associated session ID
            user_id: Associated user ID
            importance_score: Initial importance score
            metadata: Additional metadata
            related_node_ids: Related node IDs
            
        Returns:
            Node ID of created memory
        """
        try:
            # Generate unique node ID
            node_id = f"mem_{int(time.time()*1000)}_{hash(content) % 10000}"
            
            # Create memory node
            node = MemoryNode(
                node_id=node_id,
                node_type=node_type,
                content=content,
                metadata=metadata or {},
                agent_id=agent_id,
                session_id=session_id,
                user_id=user_id,
                importance_score=importance_score,
                related_ids=related_node_ids or []
            )
            
            # Store node
            self.nodes[node_id] = node
            
            # Update indices
            self._index_node(node)
            
            # Manage memory size
            await self._manage_memory_size()
            
            # Update statistics
            self.memory_stats["nodes_created"] += 1
            self.memory_stats["memory_updates"] += 1
            
            # Save periodically
            if self.memory_stats["nodes_created"] % 10 == 0:
                self._save_memory()
            
            logger.debug(
                "Memory stored",
                node_id=node_id,
                node_type=node_type,
                agent_id=agent_id,
                importance_score=importance_score
            )
            
            return node_id
            
        except Exception as e:
            logger.error("Error storing memory", error=str(e))
            return None
    
    async def retrieve_memories(
        self,
        query: Optional[str] = None,
        agent_id: Optional[str] = None,
        session_id: Optional[str] = None,
        node_type: Optional[str] = None,
        min_importance: float = 0.1,
        max_results: int = 10,
        include_related: bool = False
    ) -> List[MemoryNode]:
        """Retrieve relevant memories based on criteria.
        
        Args:
            query: Content query for semantic matching
            agent_id: Filter by agent ID
            session_id: Filter by session ID
            node_type: Filter by node type
            min_importance: Minimum importance threshold
            max_results: Maximum number of results
            include_related: Include related nodes in results
            
        Returns:
            List of matching memory nodes
        """
        start_time = time.time()
        
        try:
            candidate_nodes = set()
            
            # Filter by agent
            if agent_id and agent_id in self.agent_nodes:
                candidate_nodes = self.agent_nodes[agent_id].copy()
            else:
                candidate_nodes = set(self.nodes.keys())
            
            # Filter by session
            if session_id and session_id in self.session_nodes:
                if candidate_nodes:
                    candidate_nodes &= self.session_nodes[session_id]
                else:
                    candidate_nodes = self.session_nodes[session_id].copy()
            
            # Filter by type
            if node_type and node_type in self.type_index:
                if candidate_nodes:
                    candidate_nodes &= self.type_index[node_type]
                else:
                    candidate_nodes = self.type_index[node_type].copy()
            
            # Content-based filtering
            if query:
                query_keywords = self._extract_keywords(query)
                content_matches = set()
                
                for keyword in query_keywords:
                    if keyword in self.content_index:
                        content_matches |= self.content_index[keyword]
                
                if content_matches:
                    if candidate_nodes:
                        candidate_nodes &= content_matches
                    else:
                        candidate_nodes = content_matches
            
            # Score and rank candidates
            scored_nodes = []
            
            for node_id in candidate_nodes:
                if node_id not in self.nodes:
                    continue
                
                node = self.nodes[node_id]
                importance = node.calculate_current_importance()
                
                if importance < min_importance:
                    continue
                
                # Calculate relevance score
                relevance_score = self._calculate_relevance(node, query, agent_id, session_id)
                
                # Combined score
                combined_score = importance * 0.6 + relevance_score * 0.4
                
                scored_nodes.append((combined_score, node))
            
            # Sort by score and limit results
            scored_nodes.sort(reverse=True, key=lambda x: x[0])
            result_nodes = [node for _, node in scored_nodes[:max_results]]
            
            # Update access information
            for node in result_nodes:
                node.update_access()
                self.access_cache.append(node.node_id)
            
            # Include related nodes if requested
            if include_related:
                related_nodes = []
                related_ids = set()
                
                for node in result_nodes:
                    for related_id in node.related_ids:
                        if (related_id in self.nodes and 
                            related_id not in related_ids and 
                            len(related_nodes) < max_results // 2):
                            
                            related_nodes.append(self.nodes[related_id])
                            related_ids.add(related_id)
                
                result_nodes.extend(related_nodes)
            
            # Update statistics
            self.memory_stats["nodes_accessed"] += len(result_nodes)
            retrieval_time_ms = (time.time() - start_time) * 1000
            self._update_avg_retrieval_time(retrieval_time_ms)
            
            logger.debug(
                "Memories retrieved",
                query=query,
                agent_id=agent_id,
                session_id=session_id,
                node_type=node_type,
                results_count=len(result_nodes),
                retrieval_time_ms=retrieval_time_ms
            )
            
            return result_nodes
            
        except Exception as e:
            logger.error("Error retrieving memories", error=str(e))
            return []
    
    def _calculate_relevance(
        self, 
        node: MemoryNode, 
        query: Optional[str],
        agent_id: Optional[str],
        session_id: Optional[str]
    ) -> float:
        """Calculate relevance score for a memory node.
        
        Args:
            node: Memory node to score
            query: Query content
            agent_id: Target agent ID
            session_id: Target session ID
            
        Returns:
            Relevance score (0-1)
        """
        score = 0.0
        
        # Agent relevance
        if agent_id and node.agent_id == agent_id:
            score += 0.3
        
        # Session relevance  
        if session_id and node.session_id == session_id:
            score += 0.2
        
        # Content relevance (simplified)
        if query:
            query_keywords = self._extract_keywords(query)
            node_keywords = self._extract_keywords(node.content)
            
            if query_keywords and node_keywords:
                overlap = len(query_keywords & node_keywords)
                max_keywords = max(len(query_keywords), len(node_keywords))
                score += 0.4 * (overlap / max_keywords)
        
        # Recency boost
        age_hours = (datetime.utcnow() - node.last_accessed).total_seconds() / 3600
        if age_hours < 24:
            score += 0.1 * (1.0 - age_hours / 24)
        
        return min(1.0, score)
    
    def _update_avg_retrieval_time(self, retrieval_time_ms: float):
        """Update average retrieval time with exponential moving average.
        
        Args:
            retrieval_time_ms: Current retrieval time
        """
        alpha = 0.1
        current_avg = self.memory_stats["avg_retrieval_time_ms"]
        
        if current_avg == 0:
            self.memory_stats["avg_retrieval_time_ms"] = retrieval_time_ms
        else:
            self.memory_stats["avg_retrieval_time_ms"] = (
                alpha * retrieval_time_ms + (1 - alpha) * current_avg
            )
    
    async def _manage_memory_size(self):
        """Manage memory size by pruning least important nodes."""
        if len(self.nodes) <= self.max_nodes:
            return
        
        # Calculate current importance for all nodes
        node_importance = [
            (node.calculate_current_importance(), node_id)
            for node_id, node in self.nodes.items()
        ]
        
        # Sort by importance (lowest first)
        node_importance.sort()
        
        # Remove least important nodes
        nodes_to_remove = node_importance[:len(self.nodes) - self.max_nodes]
        
        for importance, node_id in nodes_to_remove:
            await self._remove_node(node_id)
        
        self.memory_stats["nodes_pruned"] += len(nodes_to_remove)
        
        logger.info(
            "Memory pruned",
            removed_count=len(nodes_to_remove),
            remaining_count=len(self.nodes)
        )
    
    async def _remove_node(self, node_id: str):
        """Remove a node and update indices.
        
        Args:
            node_id: Node ID to remove
        """
        if node_id not in self.nodes:
            return
        
        node = self.nodes[node_id]
        
        # Remove from indices
        if node.agent_id and node.agent_id in self.agent_nodes:
            self.agent_nodes[node.agent_id].discard(node_id)
        
        if node.session_id and node.session_id in self.session_nodes:
            self.session_nodes[node.session_id].discard(node_id)
        
        self.type_index[node.node_type].discard(node_id)
        
        # Remove from content index
        keywords = self._extract_keywords(node.content)
        for keyword in keywords:
            self.content_index[keyword].discard(node_id)
        
        # Remove from importance index
        self.importance_index = [
            (imp, nid) for imp, nid in self.importance_index 
            if nid != node_id
        ]
        
        # Remove from nodes
        del self.nodes[node_id]
    
    async def update_memory(
        self,
        node_id: str,
        content: Optional[str] = None,
        importance_score: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
        add_related_ids: Optional[List[str]] = None
    ) -> bool:
        """Update an existing memory node.
        
        Args:
            node_id: Node ID to update
            content: New content (optional)
            importance_score: New importance score (optional)
            metadata: Additional metadata (optional)
            add_related_ids: Related node IDs to add (optional)
            
        Returns:
            True if update was successful
        """
        try:
            if node_id not in self.nodes:
                logger.warning("Node not found for update", node_id=node_id)
                return False
            
            node = self.nodes[node_id]
            
            # Update content
            if content is not None:
                # Remove old content from index
                old_keywords = self._extract_keywords(node.content)
                for keyword in old_keywords:
                    self.content_index[keyword].discard(node_id)
                
                # Update content
                node.content = content
                
                # Re-index with new content
                new_keywords = self._extract_keywords(content)
                for keyword in new_keywords:
                    self.content_index[keyword].add(node_id)
            
            # Update importance
            if importance_score is not None:
                node.importance_score = importance_score
                
                # Update importance index
                self.importance_index = [
                    (imp, nid) for imp, nid in self.importance_index 
                    if nid != node_id
                ]
                self.importance_index.append((importance_score, node_id))
                self.importance_index.sort(reverse=True)
            
            # Update metadata
            if metadata is not None:
                node.metadata.update(metadata)
            
            # Add related nodes
            if add_related_ids:
                for related_id in add_related_ids:
                    if related_id not in node.related_ids:
                        node.related_ids.append(related_id)
            
            # Update access time
            node.update_access()
            
            # Update statistics
            self.memory_stats["memory_updates"] += 1
            
            logger.debug("Memory updated", node_id=node_id)
            
            return True
            
        except Exception as e:
            logger.error("Error updating memory", error=str(e))
            return False
    
    async def prune_old_memories(self, max_age_days: int = 30) -> int:
        """Prune memories older than specified age.
        
        Args:
            max_age_days: Maximum age in days
            
        Returns:
            Number of memories pruned
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=max_age_days)
            nodes_to_remove = []
            
            for node_id, node in self.nodes.items():
                if (node.last_accessed < cutoff_date and 
                    node.calculate_current_importance() < 0.2):  # Low importance threshold
                    nodes_to_remove.append(node_id)
            
            for node_id in nodes_to_remove:
                await self._remove_node(node_id)
            
            pruned_count = len(nodes_to_remove)
            self.memory_stats["nodes_pruned"] += pruned_count
            
            if pruned_count > 0:
                self._save_memory()
                
                logger.info(
                    "Old memories pruned",
                    pruned_count=pruned_count,
                    max_age_days=max_age_days
                )
            
            return pruned_count
            
        except Exception as e:
            logger.error("Error pruning old memories", error=str(e))
            return 0
    
    async def get_memory_stats(self, agent_id: Optional[str] = None) -> Dict[str, Any]:
        """Get memory statistics.
        
        Args:
            agent_id: Optional agent ID to filter stats
            
        Returns:
            Dictionary with memory statistics
        """
        try:
            total_nodes = len(self.nodes)
            
            if agent_id:
                agent_node_ids = self.agent_nodes.get(agent_id, set())
                agent_nodes = [self.nodes[nid] for nid in agent_node_ids if nid in self.nodes]
            else:
                agent_nodes = list(self.nodes.values())
            
            # Calculate statistics
            if agent_nodes:
                avg_importance = sum(node.calculate_current_importance() for node in agent_nodes) / len(agent_nodes)
                avg_age_hours = sum(
                    (datetime.utcnow() - node.created_at).total_seconds() / 3600
                    for node in agent_nodes
                ) / len(agent_nodes)
                
                # Node type distribution
                type_distribution = defaultdict(int)
                for node in agent_nodes:
                    type_distribution[node.node_type] += 1
            else:
                avg_importance = 0.0
                avg_age_hours = 0.0
                type_distribution = {}
            
            return {
                "total_nodes": total_nodes,
                "agent_nodes": len(agent_nodes) if agent_id else None,
                "avg_importance": avg_importance,
                "avg_age_hours": avg_age_hours,
                "type_distribution": dict(type_distribution),
                "statistics": self.memory_stats,
                "storage_path": self.storage_path,
                "max_nodes": self.max_nodes,
                "recent_access_count": len(self.access_cache)
            }
            
        except Exception as e:
            logger.error("Error getting memory stats", error=str(e))
            return {"error": str(e)}
    
    async def export_memories(
        self,
        export_path: str,
        agent_id: Optional[str] = None,
        format: str = "json"
    ) -> bool:
        """Export memories to file.
        
        Args:
            export_path: Path to export file
            agent_id: Optional agent ID to filter export
            format: Export format ("json" or "csv")
            
        Returns:
            True if export was successful
        """
        try:
            if agent_id:
                agent_node_ids = self.agent_nodes.get(agent_id, set())
                export_nodes = [
                    self.nodes[nid].to_dict() 
                    for nid in agent_node_ids 
                    if nid in self.nodes
                ]
            else:
                export_nodes = [node.to_dict() for node in self.nodes.values()]
            
            if format.lower() == "json":
                with open(export_path, 'w') as f:
                    json.dump(export_nodes, f, indent=2, default=str)
            elif format.lower() == "csv":
                import csv
                if export_nodes:
                    with open(export_path, 'w', newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=export_nodes[0].keys())
                        writer.writeheader()
                        writer.writerows(export_nodes)
            else:
                logger.error("Unsupported export format", format=format)
                return False
            
            logger.info(
                "Memories exported",
                export_path=export_path,
                node_count=len(export_nodes),
                format=format
            )
            
            return True
            
        except Exception as e:
            logger.error("Error exporting memories", error=str(e))
            return False