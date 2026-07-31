from langchain_aws import ChatBedrock
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI


def get_llm_model() -> ChatOpenAI | ChatBedrock | ChatOllama | ChatGoogleGenerativeAI:
    
