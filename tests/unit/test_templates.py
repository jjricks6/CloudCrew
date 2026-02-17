"""Tests for src/templates/."""

import pytest
from src.templates import load_template


@pytest.mark.unit
class TestLoadTemplate:
    """Verify template loading."""

    def test_load_adr_template(self) -> None:
        content = load_template("adr.md")
        assert "{title}" in content
        assert "{status}" in content
        assert "{context}" in content
        assert "{decision}" in content
        assert "{consequences}" in content

    def test_load_architecture_doc_template(self) -> None:
        content = load_template("architecture_doc.md")
        assert "{title}" in content
        assert "{overview}" in content
        assert "{architecture}" in content

    def test_missing_template_raises(self) -> None:
        with pytest.raises(FileNotFoundError, match="Template not found"):
            load_template("nonexistent.md")

    def test_load_security_review_template(self) -> None:
        content = load_template("security_review.md")
        assert "{title}" in content
        assert "{date}" in content
        assert "{scope}" in content
        assert "{verdict}" in content
        assert "{critical_count}" in content
        assert "{findings}" in content
        assert "{recommendations}" in content

    def test_templates_are_nonempty(self) -> None:
        for name in ("adr.md", "architecture_doc.md", "security_review.md"):
            content = load_template(name)
            assert len(content.strip()) > 0, f"Template {name} is empty"
