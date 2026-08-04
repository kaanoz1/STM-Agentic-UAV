import time

from langchain_aws import ChatBedrock
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
import os
from typing import Union
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_aws import ChatBedrock
from langchain_community.chat_models import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
from datetime import datetime
import os

load_dotenv()

import os
from pydantic import SecretStr

import os
from typing import Union
from datetime import datetime

def get_required_env(key: str) -> str:
    value: str | None = os.getenv(key)
    if not value:
        timestamp: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        raise ValueError(f"[{timestamp}] [ERROR] Environment variable '{key}' is missing or empty.")
    return value


def get_llm_model() -> Union[ChatOpenAI, ChatBedrock, ChatOllama, ChatGoogleGenerativeAI]:
    provider: str = os.getenv("LLM_PROVIDER", "unknown").lower()

    if provider == "openai":
        api_key: str = get_required_env("OPENAI_API_KEY")
        model: str = get_required_env("OPENAI_MODEL")

        return ChatOpenAI(
            model=model,
            api_key=SecretStr(api_key),
            temperature=0.7,
        )

    elif provider == "google":
        google_api_key: str = get_required_env("GOOGLE_API_KEY")
        model: str = get_required_env("GOOGLE_MODEL")

        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=google_api_key,
            temperature=0.7,
            streaming=True,
        )

    elif provider == "bedrock":
        model = get_required_env("BEDROCK_MODEL_ID")
        aws_access_key_id: str = get_required_env("AWS_ACCESS_KEY_ID")
        aws_secret_access_key: str = get_required_env("AWS_SECRET_ACCESS_KEY")
        region: str = os.getenv("AWS_REGION_NAME", "us-east-1")

        return ChatBedrock(
            model=model,
            region=region,
            aws_access_key_id=SecretStr(aws_access_key_id),
            aws_secret_access_key=SecretStr(aws_secret_access_key),
        )

    elif provider == "ollama":
        model: str = get_required_env("OLLAMA_MODEL")
        base_url: str = get_required_env("OLLAMA_BASE_URL")

        return ChatOllama(
            model=model,
            base_url=base_url,
            temperature=0.7,
        )

    elif provider == "openrouter":
        api_key: str = get_required_env("OPENROUTER_API_KEY")
        model: str = get_required_env("OPENROUTER_MODEL")

        return ChatOpenAI(
            model=model,
            api_key=SecretStr(api_key),
            base_url="https://openrouter.ai/api/v1",
            temperature=0.7,
            streaming=True
        )

    else:
        timestamp: str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        raise ValueError(f"[{timestamp}] [ERROR] Unsupported or unknown LLM Provider: '{provider}'")
