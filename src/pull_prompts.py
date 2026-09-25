"""
Script para fazer pull de prompts do LangSmith Prompt Hub.

Este script:
1. Conecta ao LangSmith usando credenciais do .env
2. Faz pull do prompt semente do desafio
3. Salva localmente em prompts/bug_to_user_story_v1.yml

DICAS DE IMPLEMENTAÇÃO:

- O pull é feito pelo cliente do LangSmith:

      from langsmith import Client
      client = Client()
      prompt = client.pull_prompt(
          "leonanluppi/bug_to_user_story_v1",
          dangerously_pull_public_prompt=True,
      )

- O parâmetro `dangerously_pull_public_prompt=True` é obrigatório sempre que o
  identificador tem dono explícito ("owner/nome"). O LangSmith bloqueia esse pull
  por padrão porque um prompt do Hub é um objeto LangChain serializado, que pode
  vir de terceiros. Aqui o prompt é o do desafio, então o risco é conhecido.

- O retorno é um ChatPromptTemplate. Para extrair o conteúdo das mensagens,
  use a serialização nativa do LangChain (`prompt.messages`, e o atributo
  `.prompt.template` de cada mensagem).

- Use `save_yaml` de utils.py para gravar o resultado no arquivo .yml.
"""

import sys
from pathlib import Path
from dotenv import load_dotenv
from langsmith import Client
from langchain_core.prompts import HumanMessagePromptTemplate, SystemMessagePromptTemplate
from utils import save_yaml, check_env_vars, print_section_header

load_dotenv()

PROMPT_NAME = "leonanluppi/bug_to_user_story_v1"
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "bug_to_user_story_v1.yml"


def pull_prompts_from_langsmith() -> bool:
    """Baixa o prompt semente e salva suas mensagens no formato YAML do projeto."""
    try:
        prompt = Client().pull_prompt(
            PROMPT_NAME,
            dangerously_pull_public_prompt=True,
        )
        messages = {}
        for message in prompt.messages:
            if isinstance(message, SystemMessagePromptTemplate):
                role = "system"
            elif isinstance(message, HumanMessagePromptTemplate):
                role = "human"
            else:
                raise ValueError(f"Tipo de mensagem não suportado: {type(message).__name__}")
            template = getattr(getattr(message, "prompt", None), "template", None)
            if not isinstance(template, str):
                raise ValueError(f"Mensagem {role} não contém um template de texto")
            key = "system_prompt" if role == "system" else "user_prompt"
            if key in messages:
                raise ValueError(f"Mais de uma mensagem {role} no prompt semente")
            messages[key] = template

        if not messages.get("system_prompt") or not messages.get("user_prompt"):
            raise ValueError("O prompt precisa ter mensagens system e user")

        data = {
            "bug_to_user_story_v1": {
                "description": "Prompt original do LangSmith Prompt Hub para converter bugs em histórias de usuário",
                **messages,
                "version": "v1",
                "source": PROMPT_NAME,
            }
        }
        if not save_yaml(data, str(OUTPUT_PATH)):
            return False
        print(f"Prompt salvo em {OUTPUT_PATH}")
        return True
    except Exception as exc:
        print(f"Erro ao baixar o prompt {PROMPT_NAME}: {exc}", file=sys.stderr)
        return False


def main():
    print_section_header("PULL DO PROMPT ORIGINAL")
    if not check_env_vars(["LANGSMITH_API_KEY"]):
        return 1
    return 0 if pull_prompts_from_langsmith() else 1


if __name__ == "__main__":
    sys.exit(main())
