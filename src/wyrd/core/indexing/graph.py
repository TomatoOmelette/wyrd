"""Knowledge graph storage using NetworkX."""

import os
import pickle
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

import networkx as nx


@dataclass
class ConceptNode:
    """A concept in the knowledge graph."""

    id: str
    display_name: str
    description: str = ""
    source_book: str = ""  # Primary source book slug
    source_chunks: list[str] = field(default_factory=list)  # Chunk IDs where found


@dataclass
class ConceptEdge:
    """A relationship between concepts."""

    source: str
    target: str
    relationship: str  # supports, elaborates, contradicts, related, similar
    source_book: str = ""  # Book where this relationship is found
    weight: float = 1.0


class KnowledgeGraph:
    """NetworkX-based knowledge graph for concepts and relationships."""

    VALID_RELATIONSHIPS = {
        "supports",
        "elaborates",
        "contradicts",
        "related",
        "similar",
        "implements",
        "extends",
    }

    def __init__(self, storage_path: str | Path | None = None):
        """
        Initialize the knowledge graph.

        Args:
            storage_path: Path to persist the graph. Defaults to WYRD_STORAGE_PATH/graph
        """
        if storage_path is None:
            base_path = os.environ.get("WYRD_STORAGE_PATH", "./storage")
            storage_path = Path(base_path) / "graph"
        else:
            storage_path = Path(storage_path)

        storage_path.mkdir(parents=True, exist_ok=True)
        self.storage_path = storage_path
        self.graph_file = storage_path / "concepts.pickle"

        self._graph: nx.DiGraph = self._load_or_create()

    def _load_or_create(self) -> nx.DiGraph:
        """Load existing graph or create new one."""
        if self.graph_file.exists():
            with open(self.graph_file, "rb") as f:
                return pickle.load(f)
        return nx.DiGraph()

    def _save(self) -> None:
        """Persist the graph to disk."""
        with open(self.graph_file, "wb") as f:
            pickle.dump(self._graph, f)

    def add_concept(
        self,
        concept_id: str,
        display_name: str,
        description: str = "",
        source_book: str = "",
        source_chunks: list[str] | None = None,
    ) -> None:
        """
        Add or update a concept node.

        Args:
            concept_id: Unique identifier (slug form)
            display_name: Human-readable name
            description: Optional description
            source_book: Book slug where this concept is primarily from
            source_chunks: List of chunk IDs where this concept appears
        """
        existing = self._graph.nodes.get(concept_id, {})
        existing_chunks = existing.get("source_chunks", [])

        # Merge source chunks
        all_chunks = list(set(existing_chunks + (source_chunks or [])))

        self._graph.add_node(
            concept_id,
            display_name=display_name,
            description=description or existing.get("description", ""),
            source_book=source_book or existing.get("source_book", ""),
            source_chunks=all_chunks,
        )
        self._save()

    def add_relationship(
        self,
        source_concept: str,
        target_concept: str,
        relationship: str,
        source_book: str = "",
        weight: float = 1.0,
    ) -> None:
        """
        Add a relationship between concepts.

        Args:
            source_concept: Source concept ID
            target_concept: Target concept ID
            relationship: Type of relationship (supports, elaborates, etc.)
            source_book: Book where this relationship is found
            weight: Strength of relationship (default 1.0)
        """
        if relationship not in self.VALID_RELATIONSHIPS:
            raise ValueError(
                f"Invalid relationship '{relationship}'. "
                f"Must be one of: {self.VALID_RELATIONSHIPS}"
            )

        # Ensure both concepts exist
        if source_concept not in self._graph:
            self.add_concept(source_concept, source_concept)
        if target_concept not in self._graph:
            self.add_concept(target_concept, target_concept)

        self._graph.add_edge(
            source_concept,
            target_concept,
            relationship=relationship,
            source_book=source_book,
            weight=weight,
        )
        self._save()

    def get_concept(self, concept_id: str) -> ConceptNode | None:
        """Get a concept by ID."""
        if concept_id not in self._graph:
            return None

        data = self._graph.nodes[concept_id]
        return ConceptNode(
            id=concept_id,
            display_name=data.get("display_name", concept_id),
            description=data.get("description", ""),
            source_book=data.get("source_book", ""),
            source_chunks=data.get("source_chunks", []),
        )

    def get_related_concepts(
        self,
        concept_id: str,
        relationship: str | None = None,
        depth: int = 1,
    ) -> list[tuple[ConceptNode, str, float]]:
        """
        Get concepts related to the given concept.

        Args:
            concept_id: The concept to find relations for
            relationship: Filter by relationship type (None for all)
            depth: How many hops to traverse (default 1)

        Returns:
            List of (concept, relationship, weight) tuples
        """
        if concept_id not in self._graph:
            return []

        results = []
        visited = {concept_id}

        def traverse(node: str, current_depth: int) -> None:
            if current_depth > depth:
                return

            # Outgoing edges
            for _, target, data in self._graph.out_edges(node, data=True):
                if target in visited:
                    continue
                rel = data.get("relationship", "related")
                if relationship is None or rel == relationship:
                    concept = self.get_concept(target)
                    if concept:
                        results.append((concept, rel, data.get("weight", 1.0)))
                        visited.add(target)
                        if current_depth < depth:
                            traverse(target, current_depth + 1)

            # Incoming edges (for bidirectional traversal)
            for source, _, data in self._graph.in_edges(node, data=True):
                if source in visited:
                    continue
                rel = data.get("relationship", "related")
                if relationship is None or rel == relationship:
                    concept = self.get_concept(source)
                    if concept:
                        # Reverse the relationship for incoming edges
                        results.append((concept, f"reverse:{rel}", data.get("weight", 1.0)))
                        visited.add(source)
                        if current_depth < depth:
                            traverse(source, current_depth + 1)

        traverse(concept_id, 1)
        return results

    def get_all_concepts(self) -> list[ConceptNode]:
        """Get all concepts in the graph."""
        return [
            ConceptNode(
                id=node_id,
                display_name=data.get("display_name", node_id),
                description=data.get("description", ""),
                source_book=data.get("source_book", ""),
                source_chunks=data.get("source_chunks", []),
            )
            for node_id, data in self._graph.nodes(data=True)
        ]

    def get_concepts_by_book(self, book_slug: str) -> list[ConceptNode]:
        """Get all concepts from a specific book."""
        return [
            c for c in self.get_all_concepts()
            if c.source_book == book_slug
        ]

    def delete_by_book(self, book_slug: str) -> int:
        """
        Delete all concepts and relationships from a book.

        Args:
            book_slug: The book identifier

        Returns:
            Number of concepts removed
        """
        to_remove = [
            node_id
            for node_id, data in self._graph.nodes(data=True)
            if data.get("source_book") == book_slug
        ]

        for node_id in to_remove:
            self._graph.remove_node(node_id)

        if to_remove:
            self._save()

        return len(to_remove)

    def count(self) -> tuple[int, int]:
        """Return (concept_count, relationship_count)."""
        return len(self._graph.nodes), len(self._graph.edges)

    def search_concepts(self, query: str) -> list[ConceptNode]:
        """
        Simple text search for concepts.

        Args:
            query: Search term (matches display_name or description)

        Returns:
            Matching concepts
        """
        query_lower = query.lower()
        results = []

        for node_id, data in self._graph.nodes(data=True):
            display_name = data.get("display_name", "").lower()
            description = data.get("description", "").lower()

            if query_lower in display_name or query_lower in description or query_lower in node_id:
                results.append(
                    ConceptNode(
                        id=node_id,
                        display_name=data.get("display_name", node_id),
                        description=data.get("description", ""),
                        source_book=data.get("source_book", ""),
                        source_chunks=data.get("source_chunks", []),
                    )
                )

        return results
