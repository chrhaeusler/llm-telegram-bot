import pytest
from src.char_loader import get_all_characters, get_character


def test_char_loader_finds_yaml_files(tmp_path, monkeypatch):
    # Arrange: point loader at a temp “config/chars” directory with one sample
    sample = tmp_path / "python-teacher-otto.yaml"
    sample.write_text(
        """
        key: python-teacher-otto
        role: teacher
        description: A patient Python teacher.
        identity:
          name: Ottochen
        scenario:
          greeting: "Hi!"
        """
    )
    monkeypatch.setenv("CHAR_CONFIG_DIR", str(tmp_path))  # if you support env override
    # Act
    all_chars = get_all_characters()
    char = get_character("python-teacher-otto")
    # Assert
    assert "python-teacher-otto" in all_chars
    assert char["identity"]["name"] == "Ottochen"
