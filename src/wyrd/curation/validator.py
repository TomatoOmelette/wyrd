"""Validation for curated content."""

from dataclasses import dataclass
from pathlib import Path

from wyrd.curation.models import CuratedBook, load_curated_book


@dataclass
class ValidationError:
    """A validation error."""

    file: str
    field: str
    message: str


@dataclass
class ValidationResult:
    """Result of validating curated content."""

    valid: bool
    errors: list[ValidationError]
    warnings: list[ValidationError]


def validate_curated_book(book: CuratedBook) -> ValidationResult:
    """
    Validate a curated book's content.

    Checks:
    - Required fields are present
    - IDs are unique
    - Topics and concepts are properly formatted
    - Source citations have required fields

    Args:
        book: The curated book to validate

    Returns:
        ValidationResult with any errors or warnings
    """
    errors: list[ValidationError] = []
    warnings: list[ValidationError] = []

    # Check required metadata
    if not book.slug:
        errors.append(ValidationError("metadata.yaml", "slug", "slug is required"))
    if not book.title:
        errors.append(ValidationError("metadata.yaml", "title", "title is required"))
    if not book.author:
        warnings.append(ValidationError("metadata.yaml", "author", "author is missing"))

    # Validate principles
    principle_ids = set()
    for i, principle in enumerate(book.principles):
        prefix = f"principles[{i}]"

        if not principle.id:
            errors.append(ValidationError("principles.yaml", f"{prefix}.id", "id is required"))
        elif principle.id in principle_ids:
            errors.append(ValidationError(
                "principles.yaml", f"{prefix}.id",
                f"duplicate id: {principle.id}"
            ))
        else:
            principle_ids.add(principle.id)

        if not principle.title:
            errors.append(ValidationError("principles.yaml", f"{prefix}.title", "title is required"))
        if not principle.summary:
            warnings.append(ValidationError("principles.yaml", f"{prefix}.summary", "summary is empty"))
        if not principle.topics:
            warnings.append(ValidationError("principles.yaml", f"{prefix}.topics", "no topics specified"))
        if not principle.source.chapter:
            warnings.append(ValidationError(
                "principles.yaml", f"{prefix}.source.chapter",
                "source chapter not specified"
            ))

    # Validate strategies
    strategy_ids = set()
    for i, strategy in enumerate(book.strategies):
        prefix = f"strategies[{i}]"

        if not strategy.id:
            errors.append(ValidationError("strategies.yaml", f"{prefix}.id", "id is required"))
        elif strategy.id in strategy_ids:
            errors.append(ValidationError(
                "strategies.yaml", f"{prefix}.id",
                f"duplicate id: {strategy.id}"
            ))
        else:
            strategy_ids.add(strategy.id)

        if not strategy.title:
            errors.append(ValidationError("strategies.yaml", f"{prefix}.title", "title is required"))
        if not strategy.summary:
            warnings.append(ValidationError("strategies.yaml", f"{prefix}.summary", "summary is empty"))
        if not strategy.steps:
            warnings.append(ValidationError("strategies.yaml", f"{prefix}.steps", "no steps specified"))
        if not strategy.topics:
            warnings.append(ValidationError("strategies.yaml", f"{prefix}.topics", "no topics specified"))

    # Validate philosophy if present
    if book.philosophy:
        if not book.philosophy.core_belief:
            warnings.append(ValidationError("philosophy.yaml", "core_belief", "core_belief is empty"))
        if not book.philosophy.key_ideas:
            warnings.append(ValidationError("philosophy.yaml", "key_ideas", "no key ideas specified"))

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def validate_book_directory(book_dir: Path) -> ValidationResult:
    """
    Validate curated content from a directory.

    Args:
        book_dir: Path to the book's curation directory

    Returns:
        ValidationResult with any errors or warnings
    """
    errors: list[ValidationError] = []

    # Check metadata exists
    metadata_path = book_dir / "metadata.yaml"
    if not metadata_path.exists():
        errors.append(ValidationError(
            str(book_dir), "metadata.yaml",
            "metadata.yaml is required"
        ))
        return ValidationResult(valid=False, errors=errors, warnings=[])

    # Try to load and validate
    try:
        book = load_curated_book(book_dir)
        return validate_curated_book(book)
    except Exception as e:
        errors.append(ValidationError(
            str(book_dir), "parse",
            f"Failed to parse: {e}"
        ))
        return ValidationResult(valid=False, errors=errors, warnings=[])


def format_validation_result(result: ValidationResult) -> str:
    """Format validation result as readable text."""
    parts = []

    if result.valid:
        parts.append("Validation passed!")
    else:
        parts.append("Validation failed!")

    if result.errors:
        parts.append(f"\nErrors ({len(result.errors)}):")
        for error in result.errors:
            parts.append(f"  [{error.file}] {error.field}: {error.message}")

    if result.warnings:
        parts.append(f"\nWarnings ({len(result.warnings)}):")
        for warning in result.warnings:
            parts.append(f"  [{warning.file}] {warning.field}: {warning.message}")

    return "\n".join(parts)
