"""Utility functions for PregAI chatbot"""
from loguru import logger


def format_ml_result(label: str, confidence: float) -> str:
    """Format ML output for user messaging"""
    percentage = confidence * 100 if confidence <= 1.0 else confidence
    return f'Classification: {label.title()}, Confidence: {percentage:.2f}%'


def clean_text(text: str) -> str:
    """Clean user input text"""
    if not text:
        return ''
    return text.strip()


def log_api_call(user_id: str, intent: str, status: str):
    """Log chatbot interaction for monitoring"""
    logger.info(f'User: {user_id} | Intent: {intent} | Status: {status}')