import React from 'react';
import { ArrowRight, Shield, Heart, Activity, Brain } from 'lucide-react';
import logo from '../assets/Hero_section_logo.png';
import './LandingPage.css';
import logo_foot from '../assets/Header_Brandname_logo.png';

const LandingPage = ({ onGetStarted }) => {
  const features = [
    {
      icon: <Brain size={32} className="feat-icon" />,
      title: "Ask anything",
      desc: "PregAI explains scan language and pregnancy questions in words that feel clear, not cold."
    },
    {
      icon: <Shield size={32} className="feat-icon" />,
      title: "Upload privately",
      desc: "Your ultrasound image is checked securely, with simple progress updates while analysis runs."
    },
    {
      icon: <Heart size={32} className="feat-icon" />,
      title: "Keep a record",
      desc: "Save scan reports, heatmaps, and conversations so you can return to them later."
    },
    {
      icon: <Activity size={32} className="feat-icon" />,
      title: "Learn weekly",
      desc: "Read short pregnancy lessons organized around common questions and fetal development."
    }
  ];

  const scrollToFeatures = () => {
    document.querySelector('.features-section')?.scrollIntoView({ behavior: 'smooth' });
  };

  const scrollToResources = () => {
    document.querySelector('#resources')?.scrollIntoView({ behavior: 'smooth' });
  };

  const contactSupport = () => {
    window.location.href = 'mailto:support@pregai.local?subject=PregAI%20support%20request';
  };

  return (
    <div className="landing-container">
      <section className="hero-section">
        <div className="hero-content">
          <h1 className="hero-title">Understand your scan without feeling alone.</h1>
          <p className="hero-subtitle">
            PregAI helps you upload fetal brain ultrasound images, read AI screening results in plain language,
            and keep trusted pregnancy learning close by. It supports your questions; it does not replace your clinician.
          </p>
          <div className="hero-actions">
            <button className="primary-btn" onClick={onGetStarted}>
              Check my scan privately <ArrowRight size={20} />
            </button>
            <button className="secondary-btn" onClick={scrollToFeatures}>Show me how it works</button>
          </div>
        </div>
        <div className="hero-image-container">
          <div className="glass-hero-card">
            <div className="card-pulse"></div>
            <img src={logo} alt="Hero Decoration" className="floating-logo" />
            <div className="hero-stats">
              <div className="stat-item">
                <span className="stat-value">Private</span>
                <span className="stat-label">Scan review</span>
              </div>
              <div className="stat-item">
                <span className="stat-value">Saved</span>
                <span className="stat-label">Report history</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="features-section">
        <div className="section-header">
          <h2>Careful support for scan day and the days after.</h2>
          <p>PregAI keeps the AI useful, but puts your understanding, privacy, and next step first.</p>
        </div>
        <div className="features-grid" id="features">
          {features.map((feat, i) => (
            <div key={i} className="feature-card glass-card">
              <div className="icon-wrapper">{feat.icon}</div>
              <h3>{feat.title}</h3>
              <p>{feat.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="faq-section" id="faq">
        <div className="section-header">
          <h2>Questions mothers usually ask first.</h2>
          <p>Clear answers before you create an account.</p>
        </div>
        <div className="faq-grid">
          <div className="faq-card glass-card">
            <h3>Is this a diagnosis?</h3>
            <p>No. PregAI is an educational screening assistant. A qualified healthcare provider should make medical decisions and interpret your full clinical picture.</p>
          </div>
          <div className="faq-card glass-card">
            <h3>Can I delete my data?</h3>
            <p>Yes. Your profile includes controls for deleting your account, uploaded scans, AI reports, and conversation history.</p>
          </div>
          <div className="faq-card glass-card">
            <h3>What kind of image should I upload?</h3>
            <p>Use a clear fetal brain ultrasound image. If the image is not suitable, PregAI will say so and explain what to try next.</p>
          </div>
        </div>
      </section>

      <section className="resources-section" id="resources">
        <div className="section-header">
          <h2>Small lessons for a big season.</h2>
          <p>Short, reassuring education you can return to when questions come up.</p>
        </div>
        <div className="resources-grid">
          <div className="resource-card glass-card">
            <div className="res-tag">Brain Development</div>
            <h3>Fetal brain milestones</h3>
            <p>Learn which structures may be visible during different stages of pregnancy.</p>
          </div>
          <div className="resource-card glass-card">
            <div className="res-tag">Health Tips</div>
            <h3>Questions after a scan</h3>
            <p>Prepare practical questions to bring to your next clinical appointment.</p>
          </div>
        </div>
      </section>

      <section className="support-section" id="support">
        <div className="support-cta glass-card">
          <h2>Need help using PregAI?</h2>
          <p>Get support with upload steps, reports, account access, or privacy controls.</p>
          <div className="support-actions">
            <button className="primary-btn" onClick={contactSupport}>Contact support</button>
            <button className="secondary-btn" onClick={scrollToResources}>Open the guide</button>
          </div>
        </div>
      </section>

      <footer className="landing-footer">
        <div className="footer-content">
          <div className="footer-brand">
            <img src={logo_foot} alt="PregAI" />
            <span>PregAI</span>
          </div>
          <p>&copy; 2026 PregAI. All rights reserved. Your Intelligent Fetal Health Assistant.</p>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
