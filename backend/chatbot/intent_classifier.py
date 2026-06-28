"""Intent classifier using local DistilBERT only (no LLM fallback)"""
import os
import pickle
from typing import Tuple, Optional
from loguru import logger

# Compute paths relative to this file's location
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR = os.path.join(os.path.dirname(_THIS_DIR), 'data')

class IntentClassifier:
    """Intent classifier using local DistilBERT model"""
    LOCAL_MODEL_PATH = os.path.join(_DATA_DIR, 'distilbert_local')
    TRAINED_MODEL_PATH = os.path.join(_DATA_DIR, 'intent_training', 'trained_model')

    VALID_INTENTS = [
        'general_pregnancy_education',
        'ml_result_explanation',
        'brain_development',
        'medical_advice_request',
        'image_upload_help',
        'emergency_query',
        'small_talk'
    ]

    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or self.TRAINED_MODEL_PATH
        self.tokenizer = None
        self.model = None
        self.label_map = None
        self.inverse_label_map = None
        self.class_weights_tensor = None
        self.is_loaded = False

        if os.path.exists(self.model_path):
            self.load_model(self.model_path)

    def train(self, csv_path: str, output_dir: str, epochs: int = 10):
        """Train intent classifier using locally downloaded DistilBERT"""
        try:
            import torch
            import numpy as np
            from transformers import (
                DistilBertTokenizer,
                DistilBertForSequenceClassification,
                Trainer,
                TrainingArguments,
                EarlyStoppingCallback
            )
            from sklearn.model_selection import train_test_split
            from sklearn.metrics import accuracy_score, precision_recall_fscore_support
            from sklearn.utils import class_weight
            import pandas as pd
            from torch.utils.data import Dataset

            logger.info(f'Loading dataset from {csv_path}...')
            df = pd.read_csv(csv_path)
            texts = df['text'].tolist()
            labels = df['intent_label'].tolist()

            unique_labels = sorted(list(set(labels)))
            self.label_map = {label: idx for idx, label in enumerate(unique_labels)}
            self.inverse_label_map = {idx: label for label, idx in self.label_map.items()}

            encoded_labels = [self.label_map[label] for label in labels]
            class_weights = class_weight.compute_class_weight(
                class_weight='balanced',
                classes=np.unique(encoded_labels),
                y=encoded_labels
            )
            self.class_weights_tensor = torch.tensor(class_weights, dtype=torch.float)
            logger.info(f'Class Weights: {self.class_weights_tensor}')

            train_texts, val_texts, train_labels, val_labels = train_test_split(
                texts, encoded_labels, test_size=0.2, random_state=42, stratify=encoded_labels
            )

            if not os.path.exists(self.LOCAL_MODEL_PATH):
                logger.error(f'Local model not found at {self.LOCAL_MODEL_PATH}')
                logger.info('Please download DistilBERT files from HuggingFace:')
                logger.info('  - config.json, vocab.txt, tokenizer.json')
                logger.info('  - tokenizer_config.json, pytorch_model.bin, special_tokens_map.json')
                return

            self.tokenizer = DistilBertTokenizer.from_pretrained(self.LOCAL_MODEL_PATH)
            self.model = DistilBertForSequenceClassification.from_pretrained(
                self.LOCAL_MODEL_PATH,
                num_labels=len(unique_labels)
            )

            class IntentDataset(Dataset):
                def __init__(self, texts, labels, tokenizer):
                    self.encodings = tokenizer(texts, truncation=True, padding=True, max_length=128)
                    self.labels = labels

                def __getitem__(self, idx):
                    item = {key: torch.tensor(val[idx]) for key, val in self.encodings.items()}
                    item['labels'] = torch.tensor(self.labels[idx])
                    return item

                def __len__(self):
                    return len(self.labels)

            train_dataset = IntentDataset(train_texts, train_labels, self.tokenizer)
            val_dataset = IntentDataset(val_texts, val_labels, self.tokenizer)

            training_args = TrainingArguments(
                output_dir=output_dir,
                num_train_epochs=epochs,
                per_device_train_batch_size=16,
                per_device_eval_batch_size=16,
                warmup_steps=100,
                weight_decay=0.01,
                logging_dir=f'{output_dir}/logs',
                logging_steps=10,
                evaluation_strategy='epoch',
                save_strategy='epoch',
                load_best_model_at_end=True,
            )

            def compute_metrics(eval_pred):
                predictions, labels = eval_pred
                predictions = np.argmax(predictions, axis=1)
                precision, recall, f1, _ = precision_recall_fscore_support(labels, predictions, average='weighted')
                acc = accuracy_score(labels, predictions)
                return {'accuracy': acc, 'f1': f1, 'precision': precision, 'recall': recall}

            trainer = Trainer(
                model=self.model,
                args=training_args,
                train_dataset=train_dataset,
                eval_dataset=val_dataset,
                compute_metrics=compute_metrics,
                callbacks=[EarlyStoppingCallback(early_stopping_patience=3)]
            )

            trainer.train()
            self.save_model(output_dir)
            self.is_loaded = True
            logger.info(f'Training complete. Model saved to {output_dir}')

        except ImportError as e:
            logger.error(f'Missing dependencies: {e}')
        except Exception as e:
            logger.error(f'Training failed: {e}')

    def predict(self, text: str, llm_client=None) -> Tuple[str, float]:
        """
        Predict intent using local model only.
        
        Args:
            text: User input text
            llm_client: Ignored (kept for API compatibility)
            
        Returns:
            Tuple of (intent_label, confidence)
        """
        if not self.is_loaded or not self.model or not self.tokenizer:
            logger.warning('Intent classifier model not loaded. Using default intent.')
            return 'small_talk', 0.5

        try:
            import torch

            inputs = self.tokenizer(
                text, 
                return_tensors='pt', 
                truncation=True, 
                padding=True, 
                max_length=128
            )
            self.model.eval()

            with torch.no_grad():
                outputs = self.model(**inputs)
                probs = torch.nn.functional.softmax(outputs.logits, dim=1)
                confidence, predicted = torch.max(probs, 1)
                intent_label = self.inverse_label_map.get(predicted.item(), 'small_talk')
                conf_value = confidence.item()

            if intent_label not in self.VALID_INTENTS:
                logger.warning(f'Unknown intent label: {intent_label}, defaulting to small_talk')
                return 'small_talk', conf_value

            return intent_label, conf_value

        except Exception as e:
            logger.error(f'Local model prediction failed: {e}')
            return 'small_talk', 0.5

    def save_model(self, output_dir: str):
        """Save the trained model to disk"""
        os.makedirs(output_dir, exist_ok=True)
        self.model.save_pretrained(output_dir)
        self.tokenizer.save_pretrained(output_dir)

        with open(os.path.join(output_dir, 'inverse_label_map.pkl'), 'wb') as f:
            pickle.dump(self.inverse_label_map, f)

        logger.info(f'Model saved to {output_dir}')

    def load_model(self, model_dir: str):
        """Load a trained model from disk"""
        try:
            from transformers import DistilBertTokenizer, DistilBertForSequenceClassification

            self.model = DistilBertForSequenceClassification.from_pretrained(model_dir)
            self.tokenizer = DistilBertTokenizer.from_pretrained(model_dir)

            label_map_path = os.path.join(model_dir, 'inverse_label_map.pkl')
            if os.path.exists(label_map_path):
                with open(label_map_path, 'rb') as f:
                    self.inverse_label_map = pickle.load(f)
            else:
                self.inverse_label_map = {i: intent for i, intent in enumerate(self.VALID_INTENTS)}

            self.is_loaded = True
            logger.info(f'Intent model loaded from {model_dir}')

        except Exception as e:
            logger.error(f'Failed to load model from {model_dir}: {e}')
            self.is_loaded = False