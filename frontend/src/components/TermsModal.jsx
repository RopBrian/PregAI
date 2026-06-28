import React from 'react';
import { X, Shield, AlertTriangle } from 'lucide-react';
import './Auth.css'; // Reusing Auth styles for glassmorphism

const TermsModal = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className="modal-overlay">
      <div className="modal-content glass-card terms-modal">
        <button className="modal-close" onClick={onClose}>
          <X size={24} />
        </button>
        
        <div className="terms-header">
          <Shield className="text-secondary" size={32} />
          <h2>Terms and safety notes</h2>
          <p className="text-sm opacity-75">Last Updated: January 2026</p>
        </div>

        <div className="terms-body custom-scrollbar">
          <div className="terms-alert">
            <AlertTriangle className="error-color" size={24} />
            <div>
              <h3>Educational support only</h3>
              <p>PregAI is not a medical device and does not diagnose, treat, or provide medical advice. Please use it as support for questions you discuss with qualified healthcare professionals.</p>
            </div>
          </div>

          <section>
            <h3>1. Acceptance of Terms</h3>
            <p>By creating an account and using PregAI, you agree to these terms. If you do not agree, please do not use this service.</p>
          </section>

          <section>
            <h3>2. User Responsibilities</h3>
            <ul>
              <li><strong>Talk to your provider:</strong> Always discuss scan results with qualified medical professionals.</li>
              <li><strong>Do not wait in emergencies:</strong> Seek immediate medical attention for urgent symptoms. Do not rely on this app.</li>
              <li><strong>Use accurate information:</strong> Provide truthful account and health-related information.</li>
              <li><strong>Upload only your images:</strong> Only upload images you have the legal right to use.</li>
            </ul>
          </section>

          <section>
            <h3>3. How It Works</h3>
            <p>PregAI analyzes images using machine learning and provides educational chat support. Predictions may contain errors and should never be used alone for medical decisions.</p>
          </section>

          <section>
            <h3>4. Data Privacy</h3>
            <p>We collect account information, images, and chat logs to provide the service. Your data is stored securely, and you can delete your account data from your profile.</p>
          </section>

          <section>
            <h3>5. Age Requirement</h3>
            <p>You must be <strong>18 years or older</strong> to use this service.</p>
          </section>

          <section>
            <h3>6. Disclaimers</h3>
            <p>The service is provided "AS IS" without warranties. We are NOT liable for any medical outcomes, incorrect predictions, or damages.</p>
          </section>

          <section>
            <h3>7. Emergency Disclaimer</h3>
            <p className="text-error"><strong>If you experience bleeding, severe pain, fever, reduced movement, or any urgent symptom, call emergency services or your healthcare provider immediately.</strong></p>
          </section>
        </div>

        <div className="terms-footer">
          <button className="btn-primary" onClick={onClose}>I understand</button>
        </div>
      </div>
    </div>
  );
};

export default TermsModal;
