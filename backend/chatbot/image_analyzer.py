"""Image analysis module for fetal brain ultrasound classification"""
import os
import torch
import torch.nn as nn
import torch.nn.functional as F
from torchvision import models, transforms
from PIL import Image
import numpy as np
import cv2
from io import BytesIO
from typing import Any
from loguru import logger
from backend.config.settings import settings

IMG_SIZE = 224
MEAN = [0.485, 0.456, 0.406]
STD = [0.229, 0.224, 0.225]


class GradCAMPlusPlus:
    """Grad-CAM++ explainability for Module C.

    Grad-CAM++ uses higher-order gradient weighting, which can produce sharper
    localization than classic Grad-CAM when multiple small regions influence the
    predicted class.
    """

    def __init__(self, model, target_layer):
        self.model = model
        self.target_layer = target_layer
        self.gradients = None
        self.activations = None
        self.target_layer.register_forward_hook(self.save_activation)
        self.target_layer.register_full_backward_hook(self.save_gradient)

    def save_activation(self, module, input, output):
        self.activations = output.detach()

    def save_gradient(self, module, grad_input, grad_output):
        self.gradients = grad_output[0].detach()

    def generate_cam(self, input_tensor, target_class=None):
        self.model.zero_grad()
        output = self.model(input_tensor)
        probs = F.softmax(output, dim=1)
        confidence, predicted = torch.max(probs, 1)

        if target_class is None:
            target_class = predicted.item()

        score = output[:, target_class]
        score.backward(retain_graph=True)

        gradients = self.gradients
        activations = self.activations
        gradients_power_2 = gradients.pow(2)
        gradients_power_3 = gradients_power_2 * gradients

        denominator = (
            2 * gradients_power_2
            + torch.sum(activations * gradients_power_3, dim=[2, 3], keepdim=True)
        )
        denominator = torch.where(
            denominator != 0,
            denominator,
            torch.ones_like(denominator),
        )
        alpha = gradients_power_2 / denominator
        weights = torch.sum(alpha * F.relu(gradients), dim=[2, 3], keepdim=True)
        cam = torch.sum(weights * activations, dim=1, keepdim=True)
        cam = F.relu(cam)
        cam = cam.squeeze().cpu().numpy()
        cam = (cam - cam.min()) / (cam.max() - cam.min() + 1e-08)
        cam = cv2.resize(cam, (IMG_SIZE, IMG_SIZE))

        return cam, predicted.item(), confidence.item()


class ImageAnalyzer:
    """Production wrapper for fetal brain ultrasound analysis"""

    # Module A class names: index corresponds to prediction
    # Adjust these based on your actual training labels
    MODULE_A_CLASSES = ['Non-Ultrasound', 'Invalid Fetal', 'Valid Brain']
    
    # Valid ultrasound classes that should proceed to Module B
    VALID_ULTRASOUND_CLASSES = ['Valid Brain']
    
    # Module B classes: 0 = Abnormal, 1 = Normal (based on training)
    MODULE_B_CLASSES = ['Abnormal', 'Normal']

    MODEL_FILES_BY_VERSION = {
        'v1': {
            'module_a': 'module_a_3class_enhanced.pth',
            'module_b': 'abnormal_classifier.pth',
        },
        'v2': {
            'module_a': 'module_a_3class_enhanced_v2.pth',
            'module_b': 'abnormal_classifier_v2.pth',
        },
        'v3': {
            'module_a': 'module_a_3class_leakage_checked.pth',
            'module_b': 'abnormal_classifier_leakage_checked.pth',
        },
        'leakage_checked': {
            'module_a': 'module_a_3class_leakage_checked.pth',
            'module_b': 'abnormal_classifier_leakage_checked.pth',
        },
    }

    def __init__(self):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.transform = transforms.Compose([
            transforms.Resize((IMG_SIZE, IMG_SIZE)),
            transforms.ToTensor(),
            transforms.Normalize(MEAN, STD)
        ])
        self.module_a = None
        self.module_b = None
        self.grad_cam = None

        ml_work_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'ml_work'
        )
        self.model_version = self._normalize_model_version(settings.ml_model_version)
        model_files = self.MODEL_FILES_BY_VERSION[self.model_version]
        self.path_a = os.path.join(ml_work_path, model_files['module_a'])
        self.path_b = os.path.join(ml_work_path, model_files['module_b'])
        logger.info(
            f'Image analyzer configured for ML model version {self.model_version}: '
            f'{model_files["module_a"]}, {model_files["module_b"]}'
        )

    @classmethod
    def _normalize_model_version(cls, model_version):
        normalized = (model_version or 'v1').strip().lower().replace('-', '_')
        if normalized == 'leakage_check':
            normalized = 'leakage_checked'
        if normalized not in cls.MODEL_FILES_BY_VERSION:
            supported = ', '.join(sorted(cls.MODEL_FILES_BY_VERSION))
            raise ValueError(
                f'Unsupported ML_MODEL_VERSION "{model_version}". '
                f'Supported values: {supported}.'
            )
        return normalized

    def _ensure_models_loaded(self):
        """Lazy loader for torch models"""
        if self.module_a is None:
            logger.info(f'Loading Module A ({self.model_version}) from {self.path_a}...')
            self.module_a = self._load_model(self.path_a, len(self.MODULE_A_CLASSES))

        if self.module_b is None:
            logger.info(f'Loading Module B ({self.model_version}) from {self.path_b}...')
            self.module_b = self._load_model(self.path_b, len(self.MODULE_B_CLASSES))
            if self.module_b:
                target_layer = self.module_b.layer4[-1]
                self.grad_cam = GradCAMPlusPlus(self.module_b, target_layer)

    def _load_model(self, model_path, num_classes):
        """Load ResNet50 model with custom classifier"""
        if not os.path.exists(model_path):
            logger.warning(f'Model file missing: {model_path}. Analysis will be skipped.')
            return None

        try:
            model = models.resnet50(weights=None)
            model.fc = nn.Linear(model.fc.in_features, num_classes)
            model.load_state_dict(torch.load(model_path, map_location=self.device))
            model = model.to(self.device)
            model.eval()
            logger.info(f'Model loaded successfully from {model_path}')
            return model
        except Exception as e:
            logger.error(f'Failed to load model from {model_path}: {e}')
            return None

    def analyze(self, image_bytes: bytes) -> dict[str, Any]:
        """
        Run the full pipeline:
        1. Module A: Validate if image is a proper fetal ultrasound
        2. Module B: If valid, classify as Normal/Abnormal
        3. Module C: Generate Grad-CAM visualization
        """
        self._ensure_models_loaded()

        if not self.module_a or not self.module_b:
            return {'status': 'error', 'message': 'ML models not loaded on server.'}

        try:
            image = Image.open(BytesIO(image_bytes)).convert('RGB')
            input_tensor = self.transform(image).unsqueeze(0).to(self.device)

            # Step 1: Module A - Validate image type
            with torch.no_grad():
                output_a = self.module_a(input_tensor)
                probs_a = F.softmax(output_a, dim=1)
                confidence_a, predicted_a = torch.max(probs_a, 1)

            module_a_class = self.MODULE_A_CLASSES[predicted_a.item()]
            module_a_confidence = round(confidence_a.item() * 100, 2)
            
            logger.info(f'Module A: {module_a_class} ({module_a_confidence}%)')

            # Check if the image is a valid fetal brain ultrasound
            if module_a_class not in self.VALID_ULTRASOUND_CLASSES:
                return {
                    'status': 'invalid_image',
                    'message': f'This does not appear to be a valid fetal brain ultrasound. Detected: {module_a_class}',
                    'module_a': {
                        'prediction': module_a_class,
                        'confidence': module_a_confidence
                    },
                    'module_b': None,
                    'grad_cam_overlay': None
                }

            # Step 2: Module B - Classify as Normal/Abnormal
            cam, predicted_b, confidence_b = self.grad_cam.generate_cam(input_tensor)
            
            module_b_class = self.MODULE_B_CLASSES[predicted_b]
            module_b_confidence = round(confidence_b * 100, 2)
            
            logger.info(f'Module B: {module_b_class} ({module_b_confidence}%)')

            # Step 3: Generate heatmap overlay
            original_np = np.array(image.resize((IMG_SIZE, IMG_SIZE)))
            heatmap = cv2.applyColorMap(np.uint8(255 * cam), cv2.COLORMAP_JET)
            heatmap = cv2.cvtColor(heatmap, cv2.COLOR_BGR2RGB)
            overlay = cv2.addWeighted(original_np, 0.6, heatmap, 0.4, 0)

            return {
                'status': 'success',
                'module_a': {
                    'prediction': module_a_class,
                    'confidence': module_a_confidence
                },
                'module_b': {
                    'prediction': module_b_class,
                    'confidence': module_b_confidence
                },
                'grad_cam_overlay': overlay
            }
        except Exception as e:
            logger.error(f'Analysis failed: {e}')
            return {'status': 'error', 'message': str(e)}


_analyzer_instance = None


def get_analyzer():
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = ImageAnalyzer()
    return _analyzer_instance
