"""Tests for knowledge graph."""

import pytest

from wyrd.core.indexing.graph import ConceptEdge, ConceptNode, KnowledgeGraph


class TestConceptNode:
    """Tests for ConceptNode dataclass."""

    def test_concept_node_creation(self):
        """ConceptNode can be created with required fields."""
        node = ConceptNode(
            id="emotional-safety",
            display_name="Emotional Safety",
        )

        assert node.id == "emotional-safety"
        assert node.display_name == "Emotional Safety"
        assert node.description == ""
        assert node.source_book == ""
        assert node.source_chunks == []

    def test_concept_node_with_all_fields(self):
        """ConceptNode can be created with all fields."""
        node = ConceptNode(
            id="connection",
            display_name="Connection",
            description="Building emotional bonds with children",
            source_book="good-inside",
            source_chunks=["ch001-0001", "ch002-0003"],
        )

        assert node.id == "connection"
        assert node.description == "Building emotional bonds with children"
        assert node.source_book == "good-inside"
        assert len(node.source_chunks) == 2


class TestConceptEdge:
    """Tests for ConceptEdge dataclass."""

    def test_concept_edge_creation(self):
        """ConceptEdge can be created with required fields."""
        edge = ConceptEdge(
            source="connection",
            target="correction",
            relationship="supports",
        )

        assert edge.source == "connection"
        assert edge.target == "correction"
        assert edge.relationship == "supports"
        assert edge.weight == 1.0

    def test_concept_edge_with_weight(self):
        """ConceptEdge can have custom weight."""
        edge = ConceptEdge(
            source="emotion-coaching",
            target="emotional-safety",
            relationship="elaborates",
            source_book="raising-emotionally-intelligent",
            weight=0.8,
        )

        assert edge.weight == 0.8
        assert edge.source_book == "raising-emotionally-intelligent"


class TestKnowledgeGraph:
    """Tests for KnowledgeGraph."""

    def test_create_empty_graph(self, temp_dir):
        """New graph starts empty."""
        graph = KnowledgeGraph(storage_path=temp_dir / "graph")

        concept_count, edge_count = graph.count()
        assert concept_count == 0
        assert edge_count == 0

    def test_add_concept(self, temp_dir):
        """Concepts can be added to graph."""
        graph = KnowledgeGraph(storage_path=temp_dir / "graph")

        graph.add_concept(
            concept_id="emotion-coaching",
            display_name="Emotion Coaching",
            description="Helping children understand their feelings",
            source_book="raising-emotionally-intelligent",
        )

        concept = graph.get_concept("emotion-coaching")
        assert concept is not None
        assert concept.display_name == "Emotion Coaching"
        assert concept.source_book == "raising-emotionally-intelligent"

    def test_add_concept_with_chunks(self, temp_dir):
        """Concepts can track source chunks."""
        graph = KnowledgeGraph(storage_path=temp_dir / "graph")

        graph.add_concept(
            concept_id="boundaries",
            display_name="Boundaries",
            source_chunks=["ch001-0001", "ch002-0005"],
        )

        concept = graph.get_concept("boundaries")
        assert concept is not None
        assert len(concept.source_chunks) == 2
        assert "ch001-0001" in concept.source_chunks

    def test_update_concept_merges_chunks(self, temp_dir):
        """Updating a concept merges source chunks."""
        graph = KnowledgeGraph(storage_path=temp_dir / "graph")

        graph.add_concept(
            concept_id="validation",
            display_name="Validation",
            source_chunks=["ch001-0001"],
        )
        graph.add_concept(
            concept_id="validation",
            display_name="Validation",
            source_chunks=["ch002-0002", "ch003-0001"],
        )

        concept = graph.get_concept("validation")
        assert concept is not None
        assert len(concept.source_chunks) == 3

    def test_add_relationship(self, temp_dir):
        """Relationships can be added between concepts."""
        graph = KnowledgeGraph(storage_path=temp_dir / "graph")

        graph.add_concept("connection", "Connection")
        graph.add_concept("correction", "Correction")
        graph.add_relationship(
            "connection",
            "correction",
            "supports",
            source_book="good-inside",
        )

        concept_count, edge_count = graph.count()
        assert edge_count == 1

    def test_invalid_relationship_raises(self, temp_dir):
        """Invalid relationship type raises ValueError."""
        graph = KnowledgeGraph(storage_path=temp_dir / "graph")

        graph.add_concept("a", "Concept A")
        graph.add_concept("b", "Concept B")

        with pytest.raises(ValueError, match="Invalid relationship"):
            graph.add_relationship("a", "b", "invalid_type")

    def test_valid_relationships(self, temp_dir):
        """All valid relationship types are accepted."""
        graph = KnowledgeGraph(storage_path=temp_dir / "graph")

        valid = ["supports", "elaborates", "contradicts", "related", "similar", "implements", "extends"]

        for i, rel in enumerate(valid):
            graph.add_relationship(f"src-{i}", f"tgt-{i}", rel)

        _, edge_count = graph.count()
        assert edge_count == len(valid)

    def test_relationship_auto_creates_concepts(self, temp_dir):
        """Adding relationship auto-creates missing concepts."""
        graph = KnowledgeGraph(storage_path=temp_dir / "graph")

        graph.add_relationship("new-concept-a", "new-concept-b", "related")

        assert graph.get_concept("new-concept-a") is not None
        assert graph.get_concept("new-concept-b") is not None

    def test_get_related_concepts(self, temp_dir):
        """Related concepts can be retrieved."""
        graph = KnowledgeGraph(storage_path=temp_dir / "graph")

        graph.add_concept("emotion-coaching", "Emotion Coaching")
        graph.add_concept("emotional-safety", "Emotional Safety")
        graph.add_concept("validation", "Validation")

        graph.add_relationship("emotion-coaching", "emotional-safety", "supports")
        graph.add_relationship("emotion-coaching", "validation", "elaborates")

        related = graph.get_related_concepts("emotion-coaching")
        assert len(related) == 2

        related_ids = [c.id for c, _, _ in related]
        assert "emotional-safety" in related_ids
        assert "validation" in related_ids

    def test_get_related_concepts_with_filter(self, temp_dir):
        """Related concepts can be filtered by relationship."""
        graph = KnowledgeGraph(storage_path=temp_dir / "graph")

        graph.add_concept("a", "A")
        graph.add_concept("b", "B")
        graph.add_concept("c", "C")

        graph.add_relationship("a", "b", "supports")
        graph.add_relationship("a", "c", "elaborates")

        supports_only = graph.get_related_concepts("a", relationship="supports")
        assert len(supports_only) == 1
        assert supports_only[0][0].id == "b"

    def test_get_related_concepts_bidirectional(self, temp_dir):
        """Related concepts includes incoming relationships."""
        graph = KnowledgeGraph(storage_path=temp_dir / "graph")

        graph.add_concept("source", "Source")
        graph.add_concept("target", "Target")

        graph.add_relationship("source", "target", "supports")

        # From target's perspective, source is related
        related = graph.get_related_concepts("target")
        assert len(related) == 1
        assert related[0][0].id == "source"
        assert "reverse:" in related[0][1]

    def test_get_related_concepts_depth(self, temp_dir):
        """Related concepts respects depth parameter."""
        graph = KnowledgeGraph(storage_path=temp_dir / "graph")

        graph.add_concept("a", "A")
        graph.add_concept("b", "B")
        graph.add_concept("c", "C")
        graph.add_concept("d", "D")

        graph.add_relationship("a", "b", "related")
        graph.add_relationship("b", "c", "related")
        graph.add_relationship("c", "d", "related")

        # Depth 1: only immediate neighbors
        depth1 = graph.get_related_concepts("a", depth=1)
        assert len(depth1) == 1

        # Depth 2: includes neighbors' neighbors
        depth2 = graph.get_related_concepts("a", depth=2)
        assert len(depth2) >= 2

    def test_get_nonexistent_concept(self, temp_dir):
        """Getting nonexistent concept returns None."""
        graph = KnowledgeGraph(storage_path=temp_dir / "graph")

        assert graph.get_concept("nonexistent") is None

    def test_get_all_concepts(self, temp_dir):
        """All concepts can be retrieved."""
        graph = KnowledgeGraph(storage_path=temp_dir / "graph")

        graph.add_concept("a", "Concept A")
        graph.add_concept("b", "Concept B")
        graph.add_concept("c", "Concept C")

        all_concepts = graph.get_all_concepts()
        assert len(all_concepts) == 3

    def test_get_concepts_by_book(self, temp_dir):
        """Concepts can be filtered by book."""
        graph = KnowledgeGraph(storage_path=temp_dir / "graph")

        graph.add_concept("a", "A", source_book="book1")
        graph.add_concept("b", "B", source_book="book1")
        graph.add_concept("c", "C", source_book="book2")

        book1_concepts = graph.get_concepts_by_book("book1")
        assert len(book1_concepts) == 2

        book2_concepts = graph.get_concepts_by_book("book2")
        assert len(book2_concepts) == 1

    def test_delete_by_book(self, temp_dir):
        """Concepts can be deleted by book."""
        graph = KnowledgeGraph(storage_path=temp_dir / "graph")

        graph.add_concept("a", "A", source_book="to-delete")
        graph.add_concept("b", "B", source_book="to-delete")
        graph.add_concept("c", "C", source_book="to-keep")

        deleted = graph.delete_by_book("to-delete")
        assert deleted == 2

        all_concepts = graph.get_all_concepts()
        assert len(all_concepts) == 1
        assert all_concepts[0].id == "c"

    def test_search_concepts(self, temp_dir):
        """Concepts can be searched by text."""
        graph = KnowledgeGraph(storage_path=temp_dir / "graph")

        graph.add_concept(
            "emotion-coaching",
            "Emotion Coaching",
            description="Helping children understand feelings",
        )
        graph.add_concept(
            "emotional-safety",
            "Emotional Safety",
            description="Creating secure environment",
        )
        graph.add_concept(
            "boundaries",
            "Boundaries",
            description="Setting limits",
        )

        # Search by display name
        results = graph.search_concepts("emotion")
        assert len(results) == 2

        # Search by description
        results = graph.search_concepts("limits")
        assert len(results) == 1
        assert results[0].id == "boundaries"

        # Search by ID
        results = graph.search_concepts("coaching")
        assert len(results) == 1

    def test_persistence(self, temp_dir):
        """Graph persists across instances."""
        graph1 = KnowledgeGraph(storage_path=temp_dir / "graph")
        graph1.add_concept("persistent", "Persistent Concept")
        graph1.add_relationship("persistent", "other", "related")

        # Create new instance pointing to same storage
        graph2 = KnowledgeGraph(storage_path=temp_dir / "graph")

        concept = graph2.get_concept("persistent")
        assert concept is not None
        assert concept.display_name == "Persistent Concept"

        _, edge_count = graph2.count()
        assert edge_count == 1
