"""
Model Factory - Creates LLM model instances based on configuration
"""

import os
from typing import Dict, Any


def create_model(config: Dict) -> Any:
    """
    Create and return a model instance based on configuration

    Supports: OpenAI, Anthropic, AWS Bedrock, Ollama
    """
    models_config = config.get('models', {})
    provider = models_config.get('default_provider', 'anthropic')

    if provider == 'openai':
        return _create_openai_model(models_config['openai'])
    elif provider == 'anthropic':
        return _create_anthropic_model(models_config['anthropic'])
    elif provider == 'bedrock':
        return _create_bedrock_model(models_config['bedrock'])
    elif provider == 'ollama':
        return _create_ollama_model(models_config['ollama'])
    else:
        raise ValueError(f"Unsupported model provider: {provider}")


def _create_openai_model(config: Dict) -> Any:
    """Create OpenAI model instance"""
    from strands.models import OpenAIModel

    api_key = os.getenv(config['api_key_env'])
    if not api_key:
        raise ValueError(f"API key not found in environment: {config['api_key_env']}")

    return OpenAIModel(
        model=config['model'],
        api_key=api_key,
        temperature=config.get('temperature', 0.1),
        max_tokens=config.get('max_tokens', 4000)
    )


def _create_anthropic_model(config: Dict) -> Any:
    """Create Anthropic model instance"""
    from strands.models import AnthropicModel

    api_key = os.getenv(config['api_key_env'])
    if not api_key:
        raise ValueError(f"API key not found in environment: {config['api_key_env']}")

    return AnthropicModel(
        model=config['model'],
        api_key=api_key,
        temperature=config.get('temperature', 0.1),
        max_tokens=config.get('max_tokens', 4000)
    )


def _create_bedrock_model(config: Dict) -> Any:
    """Create AWS Bedrock model instance"""
    from strands.models import BedrockModel

    return BedrockModel(
        model=config['model'],
        region=config.get('region', 'us-east-1'),
        temperature=config.get('temperature', 0.1)
    )


def _create_ollama_model(config: Dict) -> Any:
    """Create Ollama model instance"""
    from strands.models import OllamaModel

    return OllamaModel(
        model=config['model'],
        base_url=config.get('base_url', 'http://localhost:11434'),
        temperature=config.get('temperature', 0.1)
    )
