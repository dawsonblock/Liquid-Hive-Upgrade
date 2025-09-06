from src.logging_config import get_logger
"""Database Query Tool for LIQUID-HIVE
===================================

A secure database query tool that can interact with the Neo4j knowledge graph
and other configured databases with proper security restrictions.
"""

from typing import Any

from .base_tool import BaseTool, ToolParameter, ToolParameterType, ToolResult

try:
    import neo4j

    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False


class DatabaseQueryTool(BaseTool):
    """Secure database query tool for Neo4j and other databases."""

    def __init__(self):
        self.neo4j_driver: neo4j.Driver | None = None
        self._initialize_connections()

    def _initialize_connections(self):
        """Initialize database connections."""
        if NEO4J_AVAILABLE:
            try:
                import os

                neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
                neo4j_user = os.getenv("NEO4J_USER", "neo4j")
                neo4j_password = os.getenv("NEO4J_PASSWORD", "change_this_password")

                self.neo4j_driver = neo4j.GraphDatabase.driver(
                    neo4j_uri, auth=(neo4j_user, neo4j_password), max_connection_lifetime=3600
                )
            except Exception as e:
                logger.info(f"Failed to connect to Neo4j: {e}")

    @property
    def name(self) -> str:
        return "database_query"

    @property
    def description(self) -> str:
        return "Execute safe database queries against Neo4j knowledge graph and other configured databases"

    @property
    def parameters(self) -> list[ToolParameter]:
        return [
            ToolParameter(
                name="database",
                type=ToolParameterType.STRING,
                description="Target database",
                required=True,
                choices=["neo4j", "knowledge_graph"],
            ),
            ToolParameter(
                name="query",
                type=ToolParameterType.STRING,
                description="Database query to execute (Cypher for Neo4j)",
                required=True,
            ),
            ToolParameter(
                name="parameters",
                type=ToolParameterType.DICT,
                description="Query parameters",
                required=False,
                default={},
            ),
            ToolParameter(
                name="limit",
                type=ToolParameterType.INTEGER,
                description="Maximum number of results to return",
                required=False,
                default=100,
                min_value=1,
                max_value=1000,
            ),
            ToolParameter(
                name="read_only",
                type=ToolParameterType.BOOLEAN,
                description="Ensure query is read-only (recommended)",
                required=False,
                default=True,
            ),
        ]

    @property
    def category(self) -> str:
        return "data"

    @property
    def requires_approval(self) -> bool:
        return True  # Database access requires approval

    @property
    def risk_level(self) -> str:
        return "high"  # Database queries can be dangerous

    def _validate_cypher_query(self, query: str, read_only: bool) -> list[str]:
        """Validate Cypher query for safety."""
        errors = []
        query_lower = query.lower().strip()

        # Check for dangerous operations if read_only is True
        if read_only:
            dangerous_keywords = [
                "create",
                "merge",
                "set",
                "delete",
                "remove",
                "drop",
                "detach",
                "foreach",
                "load csv",
            ]

            for keyword in dangerous_keywords:
                if keyword in query_lower:
                    errors.append(
                        f"Query contains dangerous keyword '{keyword}' but read_only is True"
                    )

        # Check for administrative operations (always dangerous)
        admin_keywords = ["call dbms", "call db.", "create database", "drop database"]
        for keyword in admin_keywords:
            if keyword in query_lower:
                errors.append(
                    f"Query contains administrative operation '{keyword}' which is not allowed"
                )

        # Basic syntax check
        if not query.strip():
            errors.append("Query cannot be empty")

        return errors

    async def execute(self, parameters: dict[str, Any]) -> ToolResult:
        """Execute database query."""
        database = parameters["database"]
        query = parameters["query"]
        query_params = parameters.get("parameters", {})
        limit = parameters.get("limit", 100)
        read_only = parameters.get("read_only", True)

        try:
            if database in ["neo4j", "knowledge_graph"]:
                return await self._execute_neo4j_query(query, query_params, limit, read_only)
            else:
                return ToolResult(success=False, error=f"Unsupported database: {database}")

        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Database query failed: {e!s}",
                metadata={"database": database, "query_preview": query[:100]},
            )

    async def _execute_neo4j_query(
        self, query: str, params: dict[str, Any], limit: int, read_only: bool
    ) -> ToolResult:
        """Execute Neo4j Cypher query."""
        if not NEO4J_AVAILABLE:
            return ToolResult(
                success=False, error="Neo4j driver not available. Install neo4j package."
            )

        if not self.neo4j_driver:
            return ToolResult(success=False, error="Neo4j connection not established")

        # Validate query
        validation_errors = self._validate_cypher_query(query, read_only)
        if validation_errors:
            return ToolResult(
                success=False, error=f"Query validation failed: {'; '.join(validation_errors)}"
            )

        # Add LIMIT clause if not present and limit is set
        query_with_limit = query
        if limit and "limit" not in query.lower():
            query_with_limit += f" LIMIT {limit}"

        try:

            def run_query(tx, query_str, parameters):
                result = tx.run(query_str, parameters)
                records = []
                for record in result:
                    # Convert record to dict, handling Neo4j types
                    record_dict = {}
                    for key in record.keys():
                        value = record[key]
                        if hasattr(value, "__dict__"):
                            # Handle Neo4j node/relationship objects
                            if hasattr(value, "labels") and hasattr(value, "id"):  # Node
                                record_dict[key] = {
                                    "id": value.id,
                                    "labels": list(value.labels),
                                    "properties": dict(value),
                                }
                            elif hasattr(value, "type") and hasattr(value, "id"):  # Relationship
                                record_dict[key] = {
                                    "id": value.id,
                                    "type": value.type,
                                    "properties": dict(value),
                                    "start_node": value.start_node.id,
                                    "end_node": value.end_node.id,
                                }
                            else:
                                record_dict[key] = str(value)
                        else:
                            record_dict[key] = value
                    records.append(record_dict)

                return records, result.consume()

            # Execute query
            with self.neo4j_driver.session() as session:
                if read_only:
                    records, summary = session.read_transaction(run_query, query_with_limit, params)
                else:
                    records, summary = session.write_transaction(
                        run_query, query_with_limit, params
                    )

            return ToolResult(
                success=True,
                data=records,
                metadata={
                    "database": "neo4j",
                    "query": query,
                    "parameters": params,
                    "records_returned": len(records),
                    "query_type": summary.query_type,
                    "execution_time_ms": summary.result_consumed_after,
                    "read_only": read_only,
                },
            )

        except neo4j.CypherSyntaxError as e:
            return ToolResult(success=False, error=f"Cypher syntax error: {e!s}")
        except neo4j.CypherTypeError as e:
            return ToolResult(success=False, error=f"Cypher type error: {e!s}")
        except neo4j.ServiceUnavailable as e:
            return ToolResult(success=False, error=f"Neo4j service unavailable: {e!s}")
        except Exception as e:
            return ToolResult(success=False, error=f"Neo4j query execution failed: {e!s}")

    def __del__(self):
        """Clean up database connections."""
        if self.neo4j_driver:
            self.neo4j_driver.close()
