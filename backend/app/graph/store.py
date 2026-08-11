from typing import Any

from neo4j import GraphDatabase

from app.core.config import settings


class Neo4jGraphStore:
    def __init__(self):
        if not settings.neo4j_uri:
            raise ValueError(
                "NEO4J_URI is not configured"
            )

        if not settings.neo4j_username:
            raise ValueError(
                "NEO4J_USERNAME is not configured"
            )

        if not settings.neo4j_password:
            raise ValueError(
                "NEO4J_PASSWORD is not configured"
            )

        self.database = settings.neo4j_database

        self.driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(
                settings.neo4j_username,
                settings.neo4j_password,
            ),
        )

    def verify_connectivity(self) -> None:
        self.driver.verify_connectivity()

    def query(
        self,
        cypher: str,
        parameters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        records, _, _ = self.driver.execute_query(
            cypher,
            parameters_=parameters or {},
            database_=self.database,
        )

        return [
            record.data()
            for record in records
        ]

    def close(self) -> None:
        self.driver.close()