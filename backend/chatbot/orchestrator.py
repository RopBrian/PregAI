import os
import random
import asyncio
import uuid
import datetime
from typing import Dict, Any, Optional, Tuple, AsyncGenerator, List
from sqlalchemy.orm import Session
from loguru import logger
from backend.chatbot.safety_layer import SafetyLayer
from backend.chatbot.intent_classifier import IntentClassifier
from backend.chatbot.llm_client import LLMClient
from backend.chatbot.rate_limiter import rate_limiter
from backend.chatbot.prompts import BASE_SYSTEM_PROMPT, ML_RESULT_EXPLAINER_PROMPT, INTENT_DETECTION_PROMPT
from backend.chatbot.utils import log_api_call


# Predefined responses for intents that don't need LLM
LOCAL_RESPONSES = {
    'emergency_query': [
        "This sounds like an emergency situation. Please call 911 or your local emergency services immediately, or go to the nearest hospital. Your safety and your baby's safety are the top priority. I'm here for educational support, but right now you need medical professionals.",
        "I'm concerned about what you've described. Please contact emergency services right away or go to your nearest emergency room. Don't wait - seek medical help immediately. Your health comes first.",
        "What you're describing needs urgent medical attention. Please call your doctor, midwife, or emergency services (911) right now. If you can't reach them, go directly to the hospital. Please take care of yourself 💜"
    ],
    
    'medical_advice_request': [
        "I understand you're looking for medical guidance, and I appreciate your trust. However, I'm an educational assistant and can't provide personalized medical advice. Please consult with your obstetrician, midwife, or healthcare provider - they know your unique situation and can give you proper guidance. Is there something educational about pregnancy I can help explain instead?",
        "That's a great question for your healthcare provider! While I can share educational information about pregnancy, I'm not able to give personalized medical advice. Your doctor or midwife is the best person to address your specific concerns. Would you like me to explain any general pregnancy topics instead?",
        "I wish I could help with that directly, but medical decisions should always involve your healthcare team who knows your complete history. What I can do is provide educational information about pregnancy and fetal development. Feel free to ask about those topics!"
    ],
    
    'image_upload_help': [
        "To upload an ultrasound scan, click the camera icon next to the message input. Select your fetal brain ultrasound image (supports JPEG, PNG formats). I'll analyze it using our AI and show you the results with a heatmap! 💜",
        "Need help uploading? Just tap the camera button at the bottom of the chat and select your ultrasound image. For best results, use a clear fetal brain ultrasound image. Let me know if you run into any issues!",
        "Here's how to upload your scan:\n1. Click the camera icon (📷) next to the text input\n2. Select your ultrasound image file\n3. Wait for the AI analysis\n\nI'll show you the results with an explanation! 💚"
    ],
    
    'small_talk': {
        'greeting': [
            "Hello! I'm PregAI, your pregnancy education assistant. I'm here to help you understand fetal brain development and answer your pregnancy questions. How can I support you today?",
            "Hi there! Welcome to PregAI. I'm here to provide educational information about pregnancy and fetal health. What would you like to know?",
            "Hey! I'm so glad you're here. I'm your AI pregnancy companion, ready to help with educational questions about your pregnancy journey. What's on your mind?"
        ],
        'thanks': [
            "You're so welcome! I'm always here to help. Is there anything else you'd like to know about your pregnancy?",
            "Happy to help! Don't hesitate to ask if you have more questions. Wishing you a healthy pregnancy!",
            "Anytime! It's my pleasure to support you on this journey. Feel free to come back whenever you need me!"
        ],
        'goodbye': [
            "Take care! Remember, I'm here whenever you have questions. Wishing you and your little one all the best!",
            "Goodbye for now! Take good care of yourself and your baby. Come back anytime you need support!",
            "See you later! Rest well and don't hesitate to reach out if you have any questions. You're doing great!"
        ],
        'how_are_you': [
            "I'm doing great, thank you for asking! More importantly, how are YOU feeling? Pregnancy can be quite a journey. Is there anything I can help you with today?",
            "I'm here and ready to help! The real question is - how are you doing? Anything I can assist you with?",
            "Thanks for asking! I'm always here for you. How's your day going? Is there anything pregnancy-related I can help explain?"
        ],
        'who_are_you': [
            "I'm PregAI, your AI-powered pregnancy education assistant! I can help you understand fetal brain development, explain ultrasound results, and provide educational information about pregnancy. What would you like to know?",
            "Great question! I'm PregAI - an AI assistant designed to support expectant mothers with educational information about pregnancy and fetal health. I can also analyze fetal brain ultrasounds! How can I help you today?",
            "I'm your friendly PregAI assistant! I specialize in pregnancy education, fetal brain development, and can analyze ultrasound images. While I can't give medical advice, I'm here to help you understand and learn. What's on your mind?"
        ],
        'default': [
            "Hi there! Is there something specific about pregnancy or fetal development I can help you with?",
            "I'm here to help! Feel free to ask me about pregnancy education, fetal development, or upload an ultrasound for analysis.",
            "Hello! I'd love to help you. You can ask me questions about pregnancy or upload an ultrasound image for AI analysis."
        ]
    }
}

# Keywords to detect small talk subcategories
SMALL_TALK_KEYWORDS = {
    'greeting': ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening', 'howdy', 'greetings'],
    'thanks': ['thank', 'thanks', 'appreciate', 'grateful', 'cheers'],
    'goodbye': ['bye', 'goodbye', 'see you', 'take care', 'later', 'gotta go', 'leaving'],
    'how_are_you': ['how are you', 'how r u', 'how do you do', 'whats up', "what's up", 'howdy'],
    'who_are_you': ['who are you', 'what are you', 'your name', 'introduce yourself', 'what can you do']
}


class ChatOrchestrator:
    """Coordinates safety, intent classification, and LLM response generation"""

    # Intents that should be handled locally without LLM
    LOCAL_INTENTS = ['emergency_query', 'medical_advice_request', 'image_upload_help', 'small_talk']

    def __init__(self):
        self.safety = SafetyLayer()
        self.intent_classifier = IntentClassifier()
        self.llm = LLMClient()

    async def _get_session_context(self, db: Session, session_id: uuid.UUID, limit: int = 5) -> List[Dict[str, str]]:
        """Fetch previous messages in the session to provide context for the LLM"""
        from backend.database import crud
        messages = crud.get_session_messages(db, session_id, limit=limit)
        context = []
        for msg in messages:
            context.append({"role": msg['role'], "content": msg['content']})
        return context

    def _get_recent_scan_context(self, db: Session, user_id: int, limit: int = 8) -> Optional[str]:
        """Build a compact scan memory block for LLM turns."""
        if not user_id:
            return None

        try:
            from backend.database.models import Image, Prediction

            images = (
                db.query(Image)
                .filter(Image.user_id == user_id)
                .order_by(Image.upload_timestamp.desc())
                .limit(limit)
                .all()
            )
            if not images:
                return None

            lines = []
            for index, img in enumerate(images, start=1):
                metadata = img.metadata_json or {}
                scan_name = metadata.get('scan_name') or img.original_filename or f"Scan {img.image_id}"
                pred = db.query(Prediction).filter(Prediction.image_id == img.image_id).first()
                uploaded_at = img.upload_timestamp.isoformat() if img.upload_timestamp else "unknown date"
                recency_label = "latest" if index == 1 else f"recent #{index}"

                if pred:
                    lines.append(
                        "- "
                        f"{recency_label}: scan_name='{scan_name}', image_id={img.image_id}, "
                        f"prediction_id={pred.prediction_id}, uploaded_at={uploaded_at}, "
                        f"image_check={pred.module_a_result} ({float(pred.module_a_confidence or 0):.2f}%), "
                        f"screening_result={pred.module_b_result} ({float(pred.module_b_confidence or 0):.2f}%)."
                    )
                else:
                    module_a = metadata.get('module_a') or {}
                    lines.append(
                        "- "
                        f"{recency_label}: scan_name='{scan_name}', image_id={img.image_id}, "
                        f"uploaded_at={uploaded_at}, status=rejected, "
                        f"image_check={module_a.get('prediction', 'unknown')} "
                        f"({float(module_a.get('confidence') or 0):.2f}%)."
                    )

            return (
                "The user has these saved scan results available for reference. "
                "Use scan_name, image_id, prediction_id, and recency to resolve phrases like "
                "'that scan', 'latest scan', or a named scan. Do not claim you saw the original "
                "image pixels unless image content was explicitly provided in this chat; answer "
                "from these stored screening results and remind the user this is educational, not a diagnosis.\n"
                + "\n".join(lines)
            )
        except Exception as e:
            logger.warning(f"Failed to build scan context: {e}")
            return None

    def _message_references_scan(self, message: str, scan_context: Optional[str]) -> bool:
        if not scan_context:
            return False

        message_lower = message.lower()
        reference_terms = [
            'scan', 'screening', 'ultrasound', 'heatmap', 'result', 'report',
            'image', 'normal', 'abnormal', 'confidence', 'latest', 'previous',
            'uploaded', 'upload'
        ]
        return any(term in message_lower for term in reference_terms)

    async def _generate_session_title(self, session_id: uuid.UUID, user_msg: str, ai_msg: str):
        """Generate a title for a new session based on the first interaction (background task)"""
        from backend.database import crud
        from backend.database.database import SessionLocal
        
        # Use a fresh DB session because this runs in the background
        db = SessionLocal()
        try:
            session = crud.get_conversation_session(db, session_id)
            if not session or session.is_custom_title:
                return

            # Short summary prompt
            prompt = (
                "Write a concise 3-5 word conversation title, like ChatGPT sidebar titles.\n"
                "Rules: no quotes, no punctuation at the end, no generic words like Chat or Conversation.\n\n"
                f"User message: {user_msg}\n"
                f"Assistant response: {ai_msg[:500]}"
            )
            title = await self.llm.complete(prompt, pool_type='fast')
            if title:
                # Clean up title (remove quotes/newlines)
                clean_title = title.strip().replace('"', '').replace("'", "").split('\n')[0]
                clean_title = clean_title.rstrip('.:;- ')
                if len(clean_title) > 60:
                    clean_title = clean_title[:60].rsplit(' ', 1)[0] or clean_title[:60]
                crud.update_session_title(db, session_id, clean_title, is_custom=False)
                logger.info(f"Generated title for session {session_id}: {clean_title}")
        except Exception as e:
            logger.error(f"Failed to generate session title: {e}")
        finally:
            db.close()

    def _schedule_title_generation(self, db: Session, session_id: uuid.UUID, user_msg: str, ai_msg: str):
        """Generate an automatic title after the first full exchange."""
        from backend.database import crud

        session = crud.get_conversation_session(db, session_id)
        if not session or session.is_custom_title:
            return

        title = (session.title or '').strip()
        can_auto_title = title in ["", "New Conversation"] or title.startswith("Scan:")
        if not can_auto_title:
            return

        message_count = len(crud.get_session_messages(db, session_id, limit=3))
        if message_count <= 2:
            asyncio.create_task(self._generate_session_title(session_id, user_msg, ai_msg))

    def _get_small_talk_response(self, message: str) -> str:
        """Get appropriate small talk response based on message content"""
        message_lower = message.lower()
        
        for category, keywords in SMALL_TALK_KEYWORDS.items():
            if any(keyword in message_lower for keyword in keywords):
                return random.choice(LOCAL_RESPONSES['small_talk'][category])
        
        return random.choice(LOCAL_RESPONSES['small_talk']['default'])

    def _get_local_response(self, intent: str, message: str) -> Optional[str]:
        """Get a local response for intents that don't need LLM"""
        if intent == 'small_talk':
            return self._get_small_talk_response(message)
        
        responses = LOCAL_RESPONSES.get(intent, [])
        if responses:
            return random.choice(responses)
        
        return None

    async def _verify_intent_with_llm(self, message: str, suggested_intent: str) -> Optional[str]:
        """Perform a second-opinion check on the suggested intent using the LLM"""
        from backend.chatbot.prompts import INTENT_VERIFICATION_PROMPT
        
        prompt = INTENT_VERIFICATION_PROMPT.format(
            message=message,
            suggested_intent=suggested_intent
        )
        
        try:
            # Use the fast pool for quick verification
            response = await self.llm.complete(prompt, pool_type='fast')
            if response:
                verified_intent = response.strip().lower()
                # Validate that the response is one of our known intents
                if verified_intent in self.intent_classifier.VALID_INTENTS:
                    return verified_intent
        except Exception as e:
            logger.error(f"Intent verification failed: {e}")
            
        return None

    async def _classify_intent(self, message: str, ml_context: Optional[Dict[str, Any]] = None) -> Tuple[str, float]:
        """
        Unified context-aware intent classification.
        
        Pipeline:
        1. DistilBERT prediction
        2. Context-aware overrides (emergency/medical detection)
        3. Educational context bypass
        4. Technical keyword upgrades
        5. LLM fallback for low confidence
        """
        message_lower = message.lower().strip()
        
        # 1. Base classification from local model
        intent, confidence = await asyncio.to_thread(self.intent_classifier.predict, message)
        logger.info(f"Base Classification: {intent} ({confidence:.2f})")

        # 2. Context-Aware Overrides
        # We check for emergency/medical keywords regardless of base intent 
        # to catch misclassifications (common in class-imbalanced models)
        
        # A. Emergency check (Context-aware: skips if educational signals present)
        emergency_intent = self.safety.detect_emergency(message)
        if emergency_intent:
            logger.info("Override: Emergency detected via context-aware stem matching.")
            return emergency_intent, 1.0
            
        # B. Medical Advice check (Context-aware: skips if educational signals present)
        medical_intent = self.safety.detect_medical_keywords(message)
        if medical_intent:
            logger.info("Override: Medical advice keywords detected.")
            return medical_intent, 1.0

        # C. Technical Keyword Upgrade (Upgrade small_talk/low-conf/safe-medical queries to education)
        technical_keywords = [
            'brain', 'fetus', 'fetal', 'ultrasound', 'scan', 'nutrition', 'symptom', 
            'cerebellum', 'ventricle', 'anatomy', 'growth', 'week', 'trimester',
            'explain', 'describe', 'tell me about', 'table', 'generate', 'list',
            'normal', 'typical', 'usual', 'common', 'food', 'diet', 'eat', 'vitamin', 'supplement'
        ]
        
        # Safe keywords that allow bypassing even high-confidence medical_advice_request
        safe_edu_keywords = ['nutrition', 'food', 'diet', 'eat', 'vitamin', 'supplement', 'exercise', 'development']
        
        should_upgrade = False
        if intent in ['small_talk', 'unknown'] or confidence < 0.65:
            if any(kw in message_lower for kw in technical_keywords):
                should_upgrade = True
        elif intent == 'medical_advice_request':
            # Downgrade medical_advice to education if it's clearly about nutrition/lifestyle
            if any(kw in message_lower for kw in safe_edu_keywords):
                logger.info(f"Downgrade: Detected safe educational keywords in medical query. Overriding intent.")
                should_upgrade = True

        if should_upgrade:
            logger.info("Intent Override: Upgrading to general_pregnancy_education.")
            return 'general_pregnancy_education', 0.95

        # 3. LLM Fallback & Verification (Second Opinion)
        # We trigger the LLM in two cases:
        # A. Low confidence / unknown (Fallback)
        # B. Potentially over-cautious medical/small_talk classification (Verification)
        
        needs_fallback = (confidence < 0.65 or intent == 'unknown') and not ml_context
        needs_verification = intent in ['medical_advice_request', 'small_talk', 'emergency_query'] and not ml_context
        
        if needs_fallback:
            logger.info("Fallback: Low confidence, triggering Reasoning LLM intent detection.")
            llm_intent = await self.llm.complete(
                prompt=message,
                system_prompt=INTENT_DETECTION_PROMPT,
                pool_type='reasoning'
            )
            llm_intent = llm_intent.strip().lower() if llm_intent else ""
            if llm_intent in self.intent_classifier.VALID_INTENTS:
                logger.info(f"Fallback: Reasoning LLM classified as: {llm_intent}")
                return llm_intent, 0.95
        
        elif needs_verification:
            logger.info(f"Verification: Requesting second opinion for intent '{intent}'")
            verified_intent = await self._verify_intent_with_llm(message, intent)
            if verified_intent and verified_intent != intent:
                logger.info(f"Verification: LLM corrected intent from '{intent}' to '{verified_intent}'")
                return verified_intent, 0.95
            
        # 4. ML Context Override
        if ml_context and intent not in self.LOCAL_INTENTS:
            logger.info("ML Override: Forcing ml_result_explanation due to active scan results.")
            return 'ml_result_explanation', 0.95

        return intent, confidence

    async def chat(
        self, 
        user_id: int, 
        message: str, 
        db: Session,
        session_id: Optional[uuid.UUID] = None,
        ml_context: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, str, float, uuid.UUID]:
        """Main entry point for chatbot logic."""
        from backend.database import crud
        
        # 1. Session and Persistence
        if not session_id:
            db_session = crud.create_conversation_session(db, user_id)
            session_id = db_session.session_id
        assert session_id is not None
        
        crud.create_chat_message(db, session_id, user_id, "user", message)

        scan_context = self._get_recent_scan_context(db, user_id)

        # 2. UNIFIED INTENT CLASSIFICATION
        intent, confidence = await self._classify_intent(message, ml_context)
        if not ml_context and self._message_references_scan(message, scan_context) and intent not in ['emergency_query', 'medical_advice_request']:
            intent, confidence = 'ml_result_explanation', 0.95

        # 3. SAFETY GATE
        is_safe, safety_category = self.safety.check_medical_safety(message, intent)
        if not is_safe:
            # TRY to get a local response first (richer/more empathetic)
            response = self._get_local_response(intent, message)
            if not response:
                response = self.safety.get_safety_response(safety_category or 'medical_advice')
            
            crud.create_chat_message(db, session_id, user_id, "assistant", response, intent)
            self._schedule_title_generation(db, session_id, message, response)
            return response, intent, confidence, session_id

        # 4. RESPONSE GENERATION
        if intent in self.LOCAL_INTENTS and not ml_context:
            response = self._get_local_response(intent, message)
        else:
            history = await self._get_session_context(db, session_id)
            messages = [{'role': 'system', 'content': BASE_SYSTEM_PROMPT}]
            if scan_context:
                messages.append({'role': 'system', 'content': scan_context})
            
            if ml_context:
                ml_prompt = ML_RESULT_EXPLAINER_PROMPT.format(
                    classification=ml_context.get('classification', 'Unknown'),
                    confidence=ml_context.get('confidence', 0),
                    module_a_classification=ml_context.get('module_a_classification', 'N/A'),
                    module_a_confidence=ml_context.get('module_a_confidence', 0)
                )
                messages.append({'role': 'system', 'content': ml_prompt})
                if not message.strip():
                    messages.append({'role': 'user', 'content': "Please explain these ultrasound analysis results to me."})
            
            messages.extend(history)
            response = await self.llm.generate_response(messages, pool_type='fast')

        # 5. POST-GENERATION SAFETY
        if response and not self.safety.validate_output(response):
            logger.warning('LLM failed validation, replacing with safety response.')
            response = self.safety.get_safety_response('medical_advice')
        
        # 6. PERSISTENCE
        final_response = response or "I'm sorry, I couldn't generate a response. Please try again."
        prediction_id = ml_context.get('prediction_id') if ml_context else None
        crud.create_chat_message(db, session_id, user_id, "assistant", final_response, intent, prediction_id=prediction_id)
        self._schedule_title_generation(db, session_id, message, final_response)

        return final_response, intent, confidence, session_id

    async def stream_chat(
        self, 
        user_id: int, 
        message: str, 
        db: Session,
        session_id: Optional[uuid.UUID] = None,
        ml_context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[str, None]:
        """Streaming version of chat."""
        from backend.database import crud
        
        if not session_id:
            db_session = crud.create_conversation_session(db, user_id)
            session_id = db_session.session_id
        assert session_id is not None
        
        crud.create_chat_message(db, session_id, user_id, "user", message)

        scan_context = self._get_recent_scan_context(db, user_id)

        # 1. UNIFIED INTENT CLASSIFICATION
        intent, confidence = await self._classify_intent(message, ml_context)
        if not ml_context and self._message_references_scan(message, scan_context) and intent not in ['emergency_query', 'medical_advice_request']:
            intent, confidence = 'ml_result_explanation', 0.95

        # 2. SAFETY GATE
        is_safe, safety_category = self.safety.check_medical_safety(message, intent)
        if not is_safe:
            # TRY to get a local response first (richer/more empathetic)
            response = self._get_local_response(intent, message)
            if not response:
                response = self.safety.get_safety_response(safety_category or 'medical_advice')
            
            crud.create_chat_message(db, session_id, user_id, "assistant", response, intent)
            self._schedule_title_generation(db, session_id, message, response)
            yield response
            import json
            metadata = {"session_id": str(session_id), "intent": intent}
            yield f"\n__METADATA__:{json.dumps(metadata)}"
            return

        # 3. LOCAL RESPONSE HANDLING
        if intent in self.LOCAL_INTENTS and not ml_context:
            response = self._get_local_response(intent, message)
            if not response:
                response = self.safety.get_safety_response('medical_advice')
            crud.create_chat_message(db, session_id, user_id, "assistant", response, intent)
            self._schedule_title_generation(db, session_id, message, response)
            yield response
            import json
            metadata = {"session_id": str(session_id), "intent": intent}
            yield f"\n__METADATA__:{json.dumps(metadata)}"
            return

        # 4. STREAMING LLM RESPONSE
        history = await self._get_session_context(db, session_id)
        messages = [{'role': 'system', 'content': BASE_SYSTEM_PROMPT}]
        if scan_context:
            messages.append({'role': 'system', 'content': scan_context})
        
        if ml_context:
            ml_prompt = ML_RESULT_EXPLAINER_PROMPT.format(
                classification=ml_context.get('classification', 'Unknown'),
                confidence=ml_context.get('confidence', 0),
                module_a_classification=ml_context.get('module_a_classification', 'N/A'),
                module_a_confidence=ml_context.get('module_a_confidence', 0)
            )
            messages.append({'role': 'system', 'content': ml_prompt})
            if not message.strip():
                message = "Please explain these ultrasound analysis results to me."

        messages.extend(history)

        full_response_accum = ""
        async for chunk in self.llm.stream_response(messages, pool_type='fast'):
            full_response_accum += chunk
            yield chunk

        # 5. PERSISTENCE AND METADATA
        prediction_id = ml_context.get('prediction_id') if ml_context else None
        if full_response_accum:
            crud.create_chat_message(db, session_id, user_id, "assistant", full_response_accum, intent, prediction_id=prediction_id)
            self._schedule_title_generation(db, session_id, message, full_response_accum)
            
            # Metadata chunk for frontend
            import json
            metadata = {"session_id": str(session_id), "intent": intent}
            yield f"\n__METADATA__:{json.dumps(metadata)}"

    async def explain_scan_result(self, user_id: int, db: Session, ml_context: Dict[str, Any]) -> Tuple[str, str, float, uuid.UUID]:
        """Convenience method for scan result explanation."""
        return await self.chat(
            user_id=user_id,
            db=db,
            message="Can you explain what these scan results mean?",
            ml_context=ml_context
        )


_orchestrator_instance = None

def get_orchestrator():
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = ChatOrchestrator()
    return _orchestrator_instance
