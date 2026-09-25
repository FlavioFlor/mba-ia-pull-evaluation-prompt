"""
Script para fazer push de prompts otimizados ao LangSmith Prompt Hub.

Este script:
1. Lê os prompts otimizados de prompts/bug_to_user_story_v2.yml
2. Valida os prompts
3. Faz push PÚBLICO para o LangSmith Hub
4. Adiciona metadados (tags, descrição, técnicas utilizadas)

DICAS DE IMPLEMENTAÇÃO:

- O push é feito pelo cliente do LangSmith:

      from langsmith import Client
      from langchain_core.prompts import ChatPromptTemplate

      client = Client()
      prompt = ChatPromptTemplate.from_messages([
          ("system", system_prompt),
          ("user", user_prompt),
      ])
      url = client.push_prompt(
          f"{username}/bug_to_user_story_v2",
          object=prompt,
          is_public=True,
          description="...",
          tags=[...],
      )

- `username` vem de USERNAME_LANGSMITH_HUB no .env e precisa ser o seu handle
  do Hub. Se você ainda não tem um handle, veja as instruções no .env.example.

- A variável do template precisa ser {bug_report}, que é a chave de entrada
  usada no dataset de avaliação.

- Use `load_yaml` de utils.py para ler o arquivo .yml.
"""

import os
import re
import sys
from pathlib import Path
from dotenv import load_dotenv
from langsmith import Client
from langchain_core.prompts import ChatPromptTemplate
from utils import load_yaml, check_env_vars, print_section_header

load_dotenv()

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "bug_to_user_story_v2.yml"
PROMPT_KEY = "bug_to_user_story_v2"

def push_prompt_to_langsmith(prompt_name: str, prompt_data: dict) -> bool:
    """
    Faz push do prompt otimizado para o LangSmith Hub (PÚBLICO).

    Args:
        prompt_name: Nome do prompt
        prompt_data: Dados do prompt

    Returns:
        True se sucesso, False caso contrário
    """
    try:
        prompt = ChatPromptTemplate.from_messages([
            ("system", prompt_data["system_prompt"]),
            ("user", prompt_data["user_prompt"]),
        ])
        techniques = prompt_data["techniques_applied"]
        tags = list(dict.fromkeys([
            *prompt_data.get("tags", []),
            *(technique.lower().replace(" ", "-") for technique in techniques),
        ]))
        description = (
            f"{prompt_data['description']} "
            f"Técnicas: {', '.join(techniques)}. Versão: {prompt_data['version']}."
        )
        url = Client().push_prompt(
            prompt_name,
            object=prompt,
            is_public=True,
            description=description,
            tags=tags,
        )
        print(f"Prompt publicado: {url}")
        return True
    except Exception as exc:
        print(f"Erro ao publicar {prompt_name}: {exc}", file=sys.stderr)
        return False


def validate_prompt(prompt_data: dict) -> tuple[bool, list]:
    """
    Valida estrutura básica de um prompt (versão simplificada).

    Args:
        prompt_data: Dados do prompt

    Returns:
        (is_valid, errors) - Tupla com status e lista de erros
    """
    errors = []
    if not isinstance(prompt_data, dict):
        return False, ["O prompt deve ser um objeto YAML"]

    for field in ("description", "system_prompt", "user_prompt", "version"):
        if not isinstance(prompt_data.get(field), str) or not prompt_data[field].strip():
            errors.append(f"Campo obrigatório vazio: {field}")

    techniques = prompt_data.get("techniques_applied")
    if not isinstance(techniques, list) or len(techniques) < 2 or not all(
        isinstance(item, str) and item.strip() for item in techniques
    ):
        errors.append("Liste pelo menos duas técnicas em techniques_applied")
    elif not any("few-shot" in item.lower() for item in techniques):
        errors.append("Few-shot Learning é obrigatório")

    for field in ("system_prompt", "user_prompt"):
        if isinstance(prompt_data.get(field), str) and "[TODO]" in prompt_data[field].upper():
            errors.append(f"{field} contém [TODO]")

    tags = prompt_data.get("tags", [])
    if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
        errors.append("tags deve ser uma lista de textos")

    if not errors:
        try:
            template = ChatPromptTemplate.from_messages([
                ("system", prompt_data["system_prompt"]),
                ("user", prompt_data["user_prompt"]),
            ])
            if set(template.input_variables) != {"bug_report"}:
                errors.append("O único campo variável deve ser {bug_report}")
        except Exception as exc:
            errors.append(f"Template LangChain inválido: {exc}")

    return not errors, errors


def main():
    print_section_header("PUSH DO PROMPT OTIMIZADO")
    if not check_env_vars(["LANGSMITH_API_KEY", "USERNAME_LANGSMITH_HUB"]):
        return 1

    username = os.getenv("USERNAME_LANGSMITH_HUB", "").strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", username):
        print("USERNAME_LANGSMITH_HUB deve conter apenas o handle público, sem barras ou nome do prompt.")
        return 1

    content = load_yaml(str(PROMPT_PATH))
    if not isinstance(content, dict) or PROMPT_KEY not in content:
        print(f"Arquivo inválido: esperado o campo {PROMPT_KEY} em {PROMPT_PATH}")
        return 1

    prompt_data = content[PROMPT_KEY]
    valid, errors = validate_prompt(prompt_data)
    if not valid:
        for error in errors:
            print(f"- {error}")
        return 1

    name = f"{username}/{PROMPT_KEY}"
    return 0 if push_prompt_to_langsmith(name, prompt_data) else 1


if __name__ == "__main__":
    sys.exit(main())
