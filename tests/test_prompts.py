"""
Testes automatizados para validação de prompts.
"""
from pathlib import Path

import pytest
import yaml
from langchain_core.prompts import ChatPromptTemplate


PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "bug_to_user_story_v2.yml"


@pytest.fixture(scope="module")
def prompt_data():
    with PROMPT_PATH.open(encoding="utf-8") as stream:
        document = yaml.safe_load(stream)
    assert isinstance(document, dict)
    return document["bug_to_user_story_v2"]


class TestPrompts:
    def test_prompt_has_system_prompt(self, prompt_data):
        assert isinstance(prompt_data.get("system_prompt"), str)
        assert prompt_data["system_prompt"].strip()

    def test_prompt_has_role_definition(self, prompt_data):
        assert "você é um product manager" in prompt_data["system_prompt"].lower()

    def test_prompt_mentions_format(self, prompt_data):
        system = prompt_data["system_prompt"].lower()
        assert "markdown" in system
        assert "como [persona], eu quero" in system
        assert "critérios de aceitação" in system

    def test_prompt_has_few_shot_examples(self, prompt_data):
        system = prompt_data["system_prompt"]
        assert system.count("Entrada:") >= 2
        assert system.count("Saída:") >= 2
        assert "Few-shot Learning" in prompt_data["techniques_applied"]

    def test_prompt_no_todos(self, prompt_data):
        assert "[TODO]" not in yaml.safe_dump(prompt_data, allow_unicode=True).upper()

    def test_minimum_techniques(self, prompt_data):
        techniques = prompt_data.get("techniques_applied")
        assert isinstance(techniques, list)
        assert len(set(techniques)) >= 2
        assert "Few-shot Learning" in techniques

    def test_template_uses_only_bug_report(self, prompt_data):
        template = ChatPromptTemplate.from_messages([
            ("system", prompt_data["system_prompt"]),
            ("user", prompt_data["user_prompt"]),
        ])
        assert set(template.input_variables) == {"bug_report"}
        messages = template.format_messages(bug_report="O botão não responde")
        assert "O botão não responde" in messages[-1].content
