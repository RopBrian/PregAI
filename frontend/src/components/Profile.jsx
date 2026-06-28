import React, { useState } from 'react';
import { User, Mail, Calendar, Trash2, ShieldAlert, Key, LogOut, X, AlertTriangle, CheckCircle, Eye, EyeOff } from 'lucide-react';
import './Profile.css';
import { formatDateOnly } from '../utils/dateUtils';

const Profile = ({ user, onLogout }) => {
  const [showConfirmModal, setShowConfirmModal] = useState(false);
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [error, setError] = useState(null);
  const [passwordError, setPasswordError] = useState(null);
  const [passwordSuccess, setPasswordSuccess] = useState(null);
  const [passwordForm, setPasswordForm] = useState({
    current_password: '',
    new_password: '',
    confirm_password: ''
  });
  const [showCurrentPassword, setShowCurrentPassword] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const closePasswordModal = () => {
    setShowPasswordModal(false);
    setPasswordError(null);
    setPasswordSuccess(null);
    setPasswordForm({
      current_password: '',
      new_password: '',
      confirm_password: ''
    });
  };

  const handlePasswordChange = async (e) => {
    e.preventDefault();
    setPasswordError(null);
    setPasswordSuccess(null);

    if (passwordForm.new_password.length < 8) {
      setPasswordError('New password must be at least 8 characters long.');
      return;
    }

    if (passwordForm.new_password !== passwordForm.confirm_password) {
      setPasswordError('New password and confirmation do not match.');
      return;
    }

    setIsChangingPassword(true);
    try {
      const token = localStorage.getItem('pregai_token');
      const response = await fetch('/api/v1/auth/change-password', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          current_password: passwordForm.current_password,
          new_password: passwordForm.new_password
        })
      });

      const data = await response.json();

      if (response.ok) {
        setPasswordSuccess(data.message || 'Password changed successfully.');
        setPasswordForm({
          current_password: '',
          new_password: '',
          confirm_password: ''
        });
      } else {
        setPasswordError(data.detail || 'Failed to change password. Please try again.');
      }
    } catch (error) {
      console.error('Password change error:', error);
      setPasswordError('An error occurred. Please check your connection and try again.');
    } finally {
      setIsChangingPassword(false);
    }
  };

  const handleDeleteAccount = async () => {
    setIsDeleting(true);
    setError(null);
    try {
      const token = localStorage.getItem('pregai_token');
      const response = await fetch('/api/v1/auth/profile', {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        // Successful deletion
        onLogout(); 
      } else {
        setError("Failed to delete account. Please try again or contact support.");
        setIsDeleting(false);
      }
    } catch (error) {
      console.error("Account deletion error:", error);
      setError("An error occurred. Please check your connection and try again.");
      setIsDeleting(false);
    }
  };

  if (!user) return null;

  return (
    <div className="profile-view fade-in">
      <div className="profile-container">
        <div className="profile-header">
          <div className="profile-avatar-large">
            <User size={48} />
          </div>
          <h1>Your information belongs to you.</h1>
          <p>Manage your identity, contact details, security, and scan data in one place.</p>
        </div>

        <div className="profile-grid">
          {/* Identity Card */}
          <div className="profile-card glass-card">
            <div className="card-header">
              <User size={20} className="header-icon" />
              <h3>Personal details</h3>
            </div>
            <div className="info-group">
              <label>Full Name</label>
              <div className="value">{user.first_name || 'Not provided'} {user.last_name || ''}</div>
            </div>
            <div className="info-group">
              <label>Username</label>
              <div className="value">@{user.username}</div>
            </div>
            <div className="info-group">
              <label>Account Role</label>
              <div className="role-badge">{user.role === 'system_admin' ? 'Administrator' : 'Mother Account'}</div>
            </div>
          </div>

          {/* Contact & Security */}
          <div className="profile-card glass-card">
            <div className="card-header">
              <Mail size={20} className="header-icon" />
              <h3>Contact and security</h3>
            </div>
            <div className="info-group">
              <label>Email Address</label>
              <div className="value">{user.email}</div>
            </div>
            <div className="info-group">
              <label>Member Since</label>
              <div className="value">
                <Calendar size={14} style={{ marginRight: '8px' }} />
                {formatDateOnly(user.registration_date)}
              </div>
            </div>
            <div className="info-group">
              <label>Security</label>
              <button className="secondary-action-btn" onClick={() => setShowPasswordModal(true)}>
                <Key size={16} /> Change password
              </button>
            </div>
          </div>

          {/* Danger Zone */}
          <div className="profile-card danger-zone glass-card">
            <div className="card-header">
              <ShieldAlert size={20} className="header-icon danger" />
              <h3>Delete account and data</h3>
            </div>
            <p className="danger-explanation">
              Deleting your account removes your profile, chat history, uploaded scans, and AI reports. 
              This action cannot be undone.
            </p>
            <div className="danger-actions">
              <button className="delete-account-btn" onClick={() => setShowConfirmModal(true)}>
                <Trash2 size={18} /> Delete my account and data
              </button>
            </div>
          </div>
        </div>

        <div className="profile-footer">
          <button className="logout-action-btn" onClick={onLogout}>
            <LogOut size={18} /> Sign out
          </button>
        </div>
      </div>

      {/* Custom Confirmation Modal */}
      {showConfirmModal && (
        <div className="modal-overlay fade-in">
          <div className="confirm-modal glass-card">
            <button className="modal-close" onClick={() => setShowConfirmModal(false)}>
              <X size={20} />
            </button>
            
            <div className="modal-content">
              <div className="warning-icon-bg">
                <AlertTriangle size={32} color="#ef4444" />
              </div>
              <h2>Before we delete anything</h2>
              <p>Are you sure you want to permanently delete your account, <strong>@{user.username}</strong>?</p>
              
              <div className="deletion-checklist">
                <div className="check-item">
                  <span className="dot"></span>
                  <span>All ultrasound scans and AI heatmaps will be deleted.</span>
                </div>
                <div className="check-item">
                  <span className="dot"></span>
                  <span>Your conversation history will be deleted.</span>
                </div>
                <div className="check-item">
                  <span className="dot"></span>
                  <span>Your saved reports and learning history will be removed.</span>
                </div>
              </div>

              {error && <div className="modal-error-msg">{error}</div>}

              <div className="modal-footer">
                <button 
                  className="cancel-btn" 
                  onClick={() => setShowConfirmModal(false)}
                  disabled={isDeleting}
                >
                  Keep my account
                </button>
                <button 
                  className="confirm-delete-btn" 
                  onClick={handleDeleteAccount}
                  disabled={isDeleting}
                >
                  {isDeleting ? 'Deleting data...' : 'Delete my account and data'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {showPasswordModal && (
        <div className="modal-overlay fade-in">
          <div className="confirm-modal glass-card">
            <button className="modal-close" onClick={closePasswordModal}>
              <X size={20} />
            </button>

            <div className="modal-content password-modal-content">
              <div className="warning-icon-bg security-icon-bg">
                <Key size={30} color="var(--primary-dark)" />
              </div>
              <h2>Change password</h2>
              <p>Use your current password to set a new one for <strong>@{user.username}</strong>.</p>

              <form className="password-form" onSubmit={handlePasswordChange}>
                <label>
                  Current password
                  <div className="input-with-icon">
                    <input
                      type={showCurrentPassword ? 'text' : 'password'}
                      value={passwordForm.current_password}
                      onChange={(e) => setPasswordForm(prev => ({ ...prev, current_password: e.target.value }))}
                      autoComplete="current-password"
                      required
                    />
                    <button
                      type="button"
                      className="input-icon-btn"
                      onClick={() => setShowCurrentPassword(s => !s)}
                      aria-label={showCurrentPassword ? 'Hide current password' : 'Show current password'}
                    >
                      {showCurrentPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                </label>

                <label>
                  New password
                  <div className="input-with-icon">
                    <input
                      type={showNewPassword ? 'text' : 'password'}
                      value={passwordForm.new_password}
                      onChange={(e) => setPasswordForm(prev => ({ ...prev, new_password: e.target.value }))}
                      autoComplete="new-password"
                      minLength={8}
                      required
                    />
                    <button
                      type="button"
                      className="input-icon-btn"
                      onClick={() => setShowNewPassword(s => !s)}
                      aria-label={showNewPassword ? 'Hide new password' : 'Show new password'}
                    >
                      {showNewPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                </label>

                <label>
                  Confirm new password
                  <div className="input-with-icon">
                    <input
                      type={showConfirmPassword ? 'text' : 'password'}
                      value={passwordForm.confirm_password}
                      onChange={(e) => setPasswordForm(prev => ({ ...prev, confirm_password: e.target.value }))}
                      autoComplete="new-password"
                      minLength={8}
                      required
                    />
                    <button
                      type="button"
                      className="input-icon-btn"
                      onClick={() => setShowConfirmPassword(s => !s)}
                      aria-label={showConfirmPassword ? 'Hide confirm password' : 'Show confirm password'}
                    >
                      {showConfirmPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                    </button>
                  </div>
                </label>

                {passwordError && <div className="modal-error-msg">{passwordError}</div>}
                {passwordSuccess && (
                  <div className="modal-success-msg">
                    <CheckCircle size={18} />
                    <span>{passwordSuccess}</span>
                  </div>
                )}

                <div className="modal-footer">
                  <button
                    type="button"
                    className="cancel-btn"
                    onClick={closePasswordModal}
                    disabled={isChangingPassword}
                  >
                    Close
                  </button>
                  <button
                    type="submit"
                    className="save-password-btn"
                    disabled={isChangingPassword}
                  >
                    {isChangingPassword ? 'Updating...' : 'Update password'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Profile;
