import pytest
from pathlib import Path
from prompt_manager import PromptManager
from exceptions import TemplateError

TEST_TEMPLATE_PATH = Path("assets/uml_diagram.prompty")

def test_load_template_success(tmp_path):
    template_file = tmp_path / "template.prompty"
    template_file.write_text("Diagram: {diagram_type}, Desc: {description}")
    pm = PromptManager(template_file)
    loaded = pm.load_template()
    assert "{diagram_type}" in loaded and "{description}" in loaded

def test_load_template_missing_file(tmp_path):
    pm = PromptManager(tmp_path / "missing.prompty")
    with pytest.raises(TemplateError):
        pm.load_template()

def test_validate_success():
    template = "Diagram: {diagram_type}, Desc: {description}"
    pm = PromptManager(TEST_TEMPLATE_PATH)
    pm.validate(template)  # Should not raise

def test_validate_missing_placeholder():
    template = "Diagram: {diagram_type}"
    pm = PromptManager(TEST_TEMPLATE_PATH)
    with pytest.raises(TemplateError):
        pm.validate(template)

def test_render_success(tmp_path):
    template_file = tmp_path / "template.prompty"
    template_file.write_text("Type: {diagram_type}, Desc: {description}")
    pm = PromptManager(template_file)
    pm.load_template()
    result = pm.render({"diagram_type": "UML", "description": "Test"})
    assert "UML" in result and "Test" in result

def test_render_missing_variable(tmp_path):
    template_file = tmp_path / "template.prompty"
    template_file.write_text("Type: {diagram_type}, Desc: {description}")
    pm = PromptManager(template_file)
    pm.load_template()
    with pytest.raises(TemplateError):
        pm.render({"diagram_type": "UML"})