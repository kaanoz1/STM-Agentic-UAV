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

load_dotenv()

def get_llm_model() -> Union[ChatOpenAI, ChatBedrock, ChatOllama, ChatGoogleGenerativeAI]:
    provider: str = os.getenv("LLM_PROVIDER", "unknown").lower()

    if provider == "openai":
        return ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            api_key=os.getenv("OPENAI_API_KEY"), # type: ignore
            temperature=0.7,
        )

    elif provider == "google":
        return ChatGoogleGenerativeAI(
            model=os.getenv("GOOGLE_MODEL", "gemini-1.5-pro"),
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0.7,
        )

    elif provider == "bedrock":
        return ChatBedrock(
            model_id=os.getenv("BEDROCK_MODEL_ID"), # type: ignore
            region=os.getenv("AWS_REGION_NAME", "us-east-1"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        )

    elif provider == "ollama":
        return ChatOllama(
            model=os.getenv("OLLAMA_MODEL", "llama3"),
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            temperature=0.7,
        )

    else:
        raise ValueError(f"Unknown LLM Provider: {provider}")