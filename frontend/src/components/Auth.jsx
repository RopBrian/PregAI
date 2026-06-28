import React, { useState } from 'react';
import { Mail, Lock, User, ArrowRight, Loader2, AlertCircle, Calendar, Eye, EyeOff } from 'lucide-react';
import TermsModal from './TermsModal';
import './Auth.css';

const Auth = ({ onAuthSuccess }) => {
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    first_name: '',
    last_name: '',
    date_of_birth: ''
  });
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [showTerms, setShowTerms] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [showPassword, setShowPassword] = useState(false);

  const handleInputChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError('');

    if (!isLogin && !termsAccepted) {
        setError('Please confirm you understand PregAI is educational support before creating your account.');
        setIsLoading(false);
        return;
    }

    const endpoint = isLogin ? '/api/v1/auth/login' : '/api/v1/auth/register';
    
    let body;
    let headers = {};
    
    if (isLogin) {
      const form = new FormData();
      form.append('username', formData.username);
      form.append('password', formData.password);
      body = form;
    } else {
      headers['Content-Type'] = 'application/json';
      body = JSON.stringify({
        username: formData.username,
        email: formData.email,
        password: formData.password,
        first_name: formData.first_name,
        last_name: formData.last_name,
        date_of_birth: formData.date_of_birth || null,
        terms_accepted: termsAccepted
      });
    }

    try {
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: headers,
        body: body
      });

      const data = await response.json();
      
      if (!response.ok) {
        throw new Error(data.detail || 'Authentication failed');
      }

      // If registration was successful but didn't return a token (because it returns User model)
      if (!isLogin) {
        setIsLogin(true);
        setError('Your account is ready. Please sign in to continue.');
        setIsLoading(false);
        return;
      }

      // Success! Store token and user info
      localStorage.setItem('pregai_token', data.access_token);
      localStorage.setItem('pregai_role', data.role);
      localStorage.setItem('pregai_user', JSON.stringify({
        username: formData.username,
        role: data.role
      }));
      
      onAuthSuccess(formData.username, data.role);
    } catch (err) {
      setError(err.message || 'An unexpected error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="auth-overlay">
      <TermsModal isOpen={showTerms} onClose={() => setShowTerms(false)} />
      
      <div className="auth-container glass-card">
        <div className="auth-header">
          <h2>{isLogin ? 'Welcome back' : 'Create your private space'}</h2>
          <p>{isLogin ? 'Sign in to continue your chats, scans, and reports.' : 'Save scan reports, continue conversations, and manage your data whenever you need.'}</p>
        </div>

        {error && (
          <div className={`auth-error fade-in ${error.includes('Account created') ? 'success-msg' : ''}`}>
            {error.includes('Account created') ? null : <AlertCircle size={20} />}
            <span>{error}</span>
          </div>
        )}

        <form className="auth-form" onSubmit={handleSubmit}>
          {!isLogin && (
            <>
              <div className="form-row">
                <div className="input-group">
                  <label><User size={16} /> First name</label>
                  <input 
                    name="first_name" 
                    value={formData.first_name} 
                    onChange={handleInputChange}
                    placeholder="Jane"
                    required
                  />
                </div>
                <div className="input-group">
                  <label><User size={16} /> Last name</label>
                  <input 
                    name="last_name" 
                    value={formData.last_name} 
                    onChange={handleInputChange}
                    placeholder="Doe"
                    required
                  />
                </div>
              </div>

              <div className="input-group">
                  <label><Mail size={16} /> Email</label>
                <input 
                  type="email" 
                  name="email" 
                  value={formData.email} 
                  onChange={handleInputChange}
                  placeholder="jane@example.com"
                  required
                />
              </div>

              <div className="input-group">
                <label><Calendar size={16} /> Date of Birth</label>
                <input 
                  type="date" 
                  name="date_of_birth" 
                  value={formData.date_of_birth} 
                  onChange={handleInputChange}
                />
              </div>
            </>
          )}

          <div className="input-group">
            <label><User size={16} /> Username</label>
            <input 
              name="username" 
              value={formData.username} 
              onChange={handleInputChange}
              placeholder="Your username"
              required
            />
          </div>

          <div className="input-group">
            <label><Lock size={16} /> Password</label>
            <div className="input-with-icon">
              <input 
                type={showPassword ? 'text' : 'password'} 
                name="password" 
                value={formData.password} 
                onChange={handleInputChange}
                placeholder="••••••••"
                required
              />
              <button
                type="button"
                className="input-icon-btn"
                onClick={() => setShowPassword((s) => !s)}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </div>

          {!isLogin && (
            <div className="terms-checkbox">
              <input 
                type="checkbox" 
                id="terms" 
                checked={termsAccepted} 
                onChange={(e) => setTermsAccepted(e.target.checked)}
              />
              <label htmlFor="terms">
                I understand PregAI is educational support, not a diagnosis or emergency service. <button type="button" className="terms-link" onClick={() => setShowTerms(true)}>Read the terms</button>
              </label>
            </div>
          )}

          <button className="auth-submit-btn" type="submit" disabled={isLoading}>
            {isLoading ? <Loader2 className="animate-spin" size={24} /> : (
              <>
                {isLogin ? 'Sign in' : 'Create my account'}
                <ArrowRight size={20} />
              </>
            )}
          </button>
        </form>

        <div className="auth-toggle">
          <span>{isLogin ? "Need a private account?" : "Already have an account?"}</span>
          <button onClick={() => setIsLogin(!isLogin)}>
            {isLogin ? 'Create one' : 'Sign in'}
          </button>
        </div>
      </div>
    </div>
  );
};
export default Auth;
