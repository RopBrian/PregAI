"""OpenRouter API client for PregAI chatbot using OpenAI SDK"""
from typing import List, Dict, Optional
from loguru import logger
from openai import AsyncOpenAI
from backend.config.settings import settings
from backend.config.openrouter_config import CHATBOT_CONFIG, FALLBACK_RESPONSES


class LLMClient:
    """Client for interacting with OpenRouter API via OpenAI SDK"""

    # Optimized Model Pools (Verified Free Models - Jan 2026)
    REASONING_POOL = [
        "google/gemma-4-31b-it:free"
    ]
    
    FAST_POOL = [
        "google/gemma-4-31b-it:free"
    ]

    def __init__(self):
        self.api_key = settings.openrouter_api_key
        self.base_url = settings.openrouter_base_url
        self.default_model = settings.openrouter_model
        
        # Rotation counters
        self.reasoning_idx = 0
        self.fast_idx = 0
        
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            default_headers={
                'HTTP-Referer': 'https://pregnancy-ai.example.com',
                'X-Title': settings.app_name
            }
        )

    def _get_next_model(self, pool_type: str = 'fast') -> str:
        """Rotate through model pools to beat rate limits"""
        if pool_type == 'reasoning':
            model = self.REASONING_POOL[self.reasoning_idx]
            self.reasoning_idx = (self.reasoning_idx + 1) % len(self.REASONING_POOL)
            return model
        else:
            model = self.FAST_POOL[self.fast_idx]
            self.fast_idx = (self.fast_idx + 1) % len(self.FAST_POOL)
            return model

    async def complete(self, prompt: str, system_prompt: Optional[str] = None, pool_type: str = 'reasoning') -> str:
        """Single completion for internal tasks (like intent detection)"""
        messages = []
        if system_prompt:
            messages.append({'role': 'system', 'content': system_prompt})
        messages.append({'role': 'user', 'content': prompt})
        return await self.generate_response(messages, pool_type=pool_type)

    async def generate_response(self, messages: List[Dict[str, str]], pool_type: str = 'fast') -> str:
        """Generate response for a conversation using model rotation and robust error handling"""
        attempts = 0
        max_attempts = len(self.REASONING_POOL) if pool_type == 'reasoning' else len(self.FAST_POOL)
        max_attempts = min(max_attempts, 5) # Cap at 5 total attempts
        
        while attempts < max_attempts:
            model = self._get_next_model(pool_type)
            try:
                logger.info(f'Sending request to OpenRouter using model: {model} (Attempt {attempts + 1})')
                
                current_messages = messages

                response = await self.client.chat.completions.create(
                    model=model,
                    messages=current_messages,
                    temperature=0.7,
                    max_tokens=CHATBOT_CONFIG.get('max_tokens', 1000),
                    top_p=CHATBOT_CONFIG.get('top_p', 0.9),
                    frequency_penalty=CHATBOT_CONFIG.get('frequency_penalty', 0.0),
                    presence_penalty=CHATBOT_CONFIG.get('presence_penalty', 0.0),
                    timeout=30.0
                )

                if response.choices:
                    return response.choices[0].message.content
                return None

            except Exception as e:
                error_str = str(e)
                logger.error(f'OpenRouter API Error with model {model}: {error_str}')

                # Retry on rate limits (429), not found (404), or permission/instruction issues (400/403)
                retry_errors = ['429', '404', '400', '403', 'rate_limit', 'no endpoints found', 'instruction is not enabled']
                if any(err in error_str.lower() for err in retry_errors):
                    attempts += 1
                    logger.warning(f'Retrying with next model due to: {error_str}')
                    continue
                
                if 'timeout' in error_str.lower():
                    return FALLBACK_RESPONSES.get('timeout', "Service timed out.")

                return FALLBACK_RESPONSES.get('api_error', "An API error occurred.")
        
        return FALLBACK_RESPONSES.get('rate_limit', "Rate limit reached. Please try again later.")

    async def stream_response(self, messages: List[Dict[str, str]], pool_type: str = 'fast'):
        """Stream response for a conversation using model rotation"""
        attempts = 0
        max_attempts = len(self.REASONING_POOL) if pool_type == 'reasoning' else len(self.FAST_POOL)
        
        while attempts < max_attempts:
            model = self._get_next_model(pool_type)
            try:
                logger.info(f'Streaming request to OpenRouter using model: {model}')
                
                current_messages = messages

                stream = await self.client.chat.completions.create(
                    model=model,
                    messages=current_messages,
                    temperature=0.7,
                    max_tokens=1000,
                    stream=True
                )

                item_count = 0
                async for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        if content:
                            item_count += 1
                            yield content
                
                if item_count == 0:
                    logger.warning(f"Model {model} yielded 0 tokens. Retrying...")
                    attempts += 1
                    continue
                return

            except Exception as e:
                error_str = str(e)
                logger.error(f'Streaming Error with model {model}: {error_str}')
                
                # Retry on rate limits, not found, or other transient issues
                retry_errors = ['429', '404', '400', '403', 'rate_limit', 'limit reached', 'no endpoints found', 'instruction is not enabled']
                if any(err in error_str.lower() for err in retry_errors):
                    attempts += 1
                    continue
                
                # Check if we have a partial response already, if not, yield friendly error
                yield "I'm having trouble connecting to my AI service right now. Please try again in a moment. 💜"
                return
        
        yield "I'm currently experiencing high traffic. Please try again in a moment. 💜"
