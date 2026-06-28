"""OpenRouter-specific configuration"""

CHATBOT_CONFIG = {
    'model': 'google/gemma-4-31b-it:free',
    'temperature': 0.3,
    'max_tokens': 1000,
    'top_p': 0.9,
    'frequency_penalty': 0.0,
    'presence_penalty': 0.0
}

AVAILABLE_MODELS = {
    'gemma_4': 'google/gemma-4-31b-it:free'
}

FALLBACK_RESPONSES = {
    'api_error': "I'm currently experiencing technical difficulties. Please try again in a moment.",
    'rate_limit': "I've reached my rate limit. Please try again later.",
    'timeout': 'Response took too long. Please rephrase your question and try again.'
}
