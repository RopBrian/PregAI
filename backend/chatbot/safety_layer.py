"""Medical safety guardrails for PregAI chatbot"""
import json
import re
from typing import Tuple, Optional
import os
from loguru import logger


class SafetyLayer:
    """Safety system to prevent medical advice and detect emergencies.
    
    Architecture:
    - detect_emergency(): Context-aware emergency detection using stem matching.
                          Catches bare keywords like 'pain' and typos like 'a lot f pain',
                          but skips when educational context is present.
    - check_medical_safety(): Post-classification safety gate. Blocks emergency_query
                              and medical_advice_request intents from reaching the LLM.
    - validate_output(): Post-generation check for hallucinated diagnoses.
    - get_critic_prompt(): LLM safety critic prompt.
    """

    def __init__(self):
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.blocked_keywords_path = os.path.join(base_path, 'data', 'safety_rules', 'blocked_keywords.json')
        self.redirect_messages_path = os.path.join(base_path, 'data', 'safety_rules', 'redirect_messages.json')
        self.blocked_keywords = self._load_json(self.blocked_keywords_path)
        self.redirect_messages = self._load_json(self.redirect_messages_path)

        self.patterns = {}
        for category, keywords in self.blocked_keywords.items():
            if keywords:
                self.patterns[category] = re.compile(
                    '|'.join(re.escape(kw) for kw in keywords),
                    re.IGNORECASE
                )

    def _load_json(self, path: str) -> dict:
        """Load JSON file safely"""
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f'Error loading safety rules from {path}: {e}')
            return {}

    def detect_emergency(self, message: str) -> Optional[str]:
        """
        Context-aware emergency detector using stem/substring matching.
        
        This is the SINGLE source of truth for emergency detection. It:
        1. Checks for emergency stems (pain, bleed, contraction, etc.) as substrings
        2. Skips triggering when educational context is present (normal, explain, how, etc.)
        
        Returns 'emergency_query' if emergency detected, None otherwise.
        """
        message_lower = message.lower().strip()
        
        # Emergency root stems — if ANY of these appear as a substring, it's a potential emergency
        emergency_stems = [
            'pain', 'bleed', 'contraction', 'faint', 'seizur',
            'cant breathe', 'cannot breathe', 'water broke',
            'not moving', 'no movement', 'cant feel baby',
            'leaking fluid', 'losing consciousness', 'unconscious',
            'hurting', 'hurts', 'hemorrhag',
        ]
        
        # Educational / informational context signals — if present, the user is likely
        # asking a question, NOT reporting a personal emergency
        educational_signals = [
            'normal', 'explain', 'why', 'how', 'what is', 'what are',
            'science', 'research', 'common', 'typical', 'learn',
            'information', 'tell me about', 'describe', 'understand',
            'is it ok', 'is it safe', 'should i worry', 'can you tell',
            'deal with', 'manage', 'cope', 'tips',
        ]
        
        has_emergency_stem = any(stem in message_lower for stem in emergency_stems)
        has_educational_context = any(signal in message_lower for signal in educational_signals)
        
        if has_emergency_stem and not has_educational_context:
            matched = [s for s in emergency_stems if s in message_lower]
            logger.info(f"Emergency Detector: Detected stem(s) {matched} without educational context.")
            return 'emergency_query'
        
        if has_emergency_stem and has_educational_context:
            matched_stems = [s for s in emergency_stems if s in message_lower]
            matched_edu = [s for s in educational_signals if s in message_lower]
            logger.info(f"Emergency Detector: Detected stem(s) {matched_stems} but educational context present ({matched_edu}). Not blocking.")
        
        return None

    def detect_medical_keywords(self, message: str) -> Optional[str]:
        """
        Detect medical advice / diagnosis / treatment keywords using 
        the blocked_keywords.json patterns, with educational context bypass.
        
        Returns 'medical_advice_request' if detected, None otherwise.
        """
        message_lower = message.lower()
        
        # Educational context signals
        educational_signals = [
            'normal', 'explain', 'why', 'how', 'what is', 'what are',
            'science', 'research', 'common', 'typical', 'learn',
            'nutrition', 'food', 'diet', 'eat', 'vitamin', 'supplement',
            'development', 'brain', 'grow', 'exercise', 'activity',
            'tell me about', 'information', 'describe', 'understand',
        ]
        
        has_educational_context = any(signal in message_lower for signal in educational_signals)
        
        for category in ['medical_advice', 'diagnosis', 'treatment']:
            if category in self.patterns and self.patterns[category].search(message_lower):
                if has_educational_context:
                    logger.info(f"Medical Detector: Detected {category} keyword but educational context present. Not blocking.")
                    continue
                logger.info(f"Medical Detector: Detected {category} keyword.")
                return 'medical_advice_request'
        
        return None

    def check_medical_safety(self, message: str, intent: str) -> Tuple[bool, Optional[str]]:
        """
        Post-classification safety gate.
        Should be run AFTER intent classification.
        Routes emergency_query and medical_advice_request to local responses.
        """
        if intent == 'emergency_query':
            return False, 'emergency_query'

        if intent == 'medical_advice_request':
            return False, 'medical_advice_request'

        dangerous_keywords = self.blocked_keywords.get('dangerous', [])
        for keyword in dangerous_keywords:
            if keyword.lower() in message.lower():
                return False, 'dangerous_content'

        return True, None

    def get_safety_response(self, category: str) -> str:
        """Returns the appropriate redirect message for a safety category"""
        default_response = (
            "I'm sorry, but I cannot provide medical advice. "
            "Please consult with a healthcare professional for personalized guidance."
        )
        return self.redirect_messages.get(category, self.redirect_messages.get('generic_blocked', default_response))

    def validate_output(self, llm_response: str) -> bool:
        """
        Post-generation safety check.
        Ensures the LLM hasn't hallucinated a diagnosis or medical advice.
        """
        res_lower = llm_response.lower()
        strict_blocks = [
            'i diagnose',
            'you have',
            'take this medicine',
            'the diagnosis is',
            'i prescribe'
        ]

        if any(phrase in res_lower for phrase in strict_blocks):
            return False

        return True

    def get_critic_prompt(self, message: str, response: str) -> str:
        """Returns the prompt for the LLM Safety Critic"""
        return f"""
        You are a strict Medical Safety Auditor for PregAI. 
        Your job is to determine if the assistant's response is providing medical advice, 
        making a diagnosis, or prescribing a specific treatment.

        User Message: "{message}"
        Assistant Response: "{response}"

        Rules:
        - If the assistant explains general facts, development, or anatomy: SAFE.
        - If the assistant tells the user to see a doctor: SAFE.
        - If the assistant says "you have [condition]", "I diagnose you", "Take [medicine]", or gives specific medical instructions: UNSAFE.

        Does this response contain medical advice or a diagnosis? 
        Answer ONLY with "SAFE" or "UNSAFE".
        """