import React, { useState } from 'react';
import { 
  MessageSquare, 
  BookOpen, 
  Activity, 
  X,
  User,
  ChevronLeft,
  ChevronRight,
  LogOut,
  ShieldCheck,
  ClipboardList,
  Edit2,
  Check,
  Trash2
} from 'lucide-react';
import ConfirmDialog from './ConfirmDialog';
import { NavLink } from 'react-router-dom';

const Sidebar = ({ user, isOpen, toggleSidebar, activeView, setActiveView, onLogout, sessions = [], currentSessionId, onLoadSession, onNewChat, onRenameSession, onDeleteSession }) => {
  const [editingSessionId, setEditingSessionId] = useState(null);
  const [editingTitle, setEditingTitle] = useState("");
  const [pendingDeleteSessionId, setPendingDeleteSessionId] = useState(null);
  const [isDeletingSession, setIsDeletingSession] = useState(false);
  const [deleteError, setDeleteError] = useState(null);

  const handleEditStart = (e, session) => {
    e.stopPropagation();
    setEditingSessionId(session.session_id);
    setEditingTitle(session.title);
  };

  const handleEditSave = (e, sessionId) => {
    e.stopPropagation();
    if (editingTitle.trim()) {
      onRenameSession(sessionId, editingTitle.trim());
    }
    setEditingSessionId(null);
  };

  const handleEditCancel = (e) => {
    e.stopPropagation();
    setEditingSessionId(null);
  };

  const handleDeleteClick = (e, sessionId) => {
    e.stopPropagation();
    setPendingDeleteSessionId(sessionId);
    setDeleteError(null);
  };

  const closeDeleteDialog = () => {
    if (isDeletingSession) return;
    setPendingDeleteSessionId(null);
    setDeleteError(null);
  };

  const confirmDeleteSession = async () => {
    if (!pendingDeleteSessionId) return;

    setIsDeletingSession(true);
    setDeleteError(null);
    const wasDeleted = await onDeleteSession(pendingDeleteSessionId);

    if (wasDeleted) {
      setPendingDeleteSessionId(null);
    } else {
      setDeleteError('We could not delete this conversation. Please try again.');
    }
    setIsDeletingSession(false);
  };
  const isMother = user?.role === 'pregnant_mother';
  const isAdmin = user?.role === 'system_admin';

  const navItems = [
    // Mother Nav Items
    { id: 'chat', label: 'Ask PregAI', icon: <MessageSquare size={20} />, show: isMother },
    { id: 'education', label: 'Learning Room', icon: <BookOpen size={20} />, show: isMother },
    { id: 'scans', label: 'My Scans', icon: <Activity size={20} />, show: isMother },
    { id: 'profile', label: 'My Account', icon: <User size={20} />, show: true },
    
    // Admin Nav Items
    { id: 'admin_dashboard', label: 'Overview', icon: <ShieldCheck size={20} />, show: isAdmin },
    { id: 'system_logs', label: 'System Logs', icon: <ClipboardList size={20} />, show: isAdmin }
  ];

  const visibleItems = navItems.filter(item => item.show);

  return (
    <aside className={`sidebar glass ${isOpen ? 'open' : 'closed'}`}>
      <div className="sidebar-header">
        <button className="close-sidebar-mobile" onClick={toggleSidebar} aria-label="Close Sidebar">
          <X size={24} />
        </button>
      </div>
      
      <nav className="sidebar-nav">
        {visibleItems.map(item => {
          const pathMap = { chat: '/chat', education: '/education', scans: '/scans', profile: '/profile', admin_dashboard: '/admin', system_logs: '/admin/logs' };
          const to = pathMap[item.id] || '/chat';
          return (
            <NavLink
              key={item.id}
              to={to}
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
              style={({ isActive }) => ({ textDecoration: 'none' })}
              onClick={() => { if (window.innerWidth <= 768) toggleSidebar(); }}
            >
              <span className="nav-icon">{item.icon}</span>
              <span className="nav-label">{item.label}</span>
            </NavLink>
          );
        })}
      </nav>

      {isMother && (
        <div className="sidebar-history-section">
          <div className="history-header">
            <span>Recent chats</span>
            <button className="new-chat-btn-small" onClick={onNewChat} title="Start fresh">
              +
            </button>
          </div>
          <div className="history-list scrollbar-hidden">
            {sessions.length === 0 ? (
              <div className="history-empty">No saved chats yet</div>
            ) : (
              sessions.map(session => (
                <div 
                  key={session.session_id} 
                  className={`history-item ${currentSessionId === session.session_id ? 'active' : ''} ${editingSessionId === session.session_id ? 'editing' : ''}`}
                  onClick={() => editingSessionId !== session.session_id && onLoadSession(session.session_id)}
                >
                  <MessageSquare size={14} className="history-icon" />
                  
                  {editingSessionId === session.session_id ? (
                    <div className="history-edit-box">
                      <input 
                        type="text" 
                        value={editingTitle} 
                        onChange={(e) => setEditingTitle(e.target.value)}
                        autoFocus
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') handleEditSave(e, session.session_id);
                          if (e.key === 'Escape') handleEditCancel(e);
                        }}
                      />
                      <button className="edit-action-btn save" onClick={(e) => handleEditSave(e, session.session_id)}>
                        <Check size={12} />
                      </button>
                      <button className="edit-action-btn cancel" onClick={handleEditCancel}>
                        <X size={12} />
                      </button>
                    </div>
                  ) : (
                    <>
                      <span className="history-title">{session.title}</span>
                      <div className="history-actions">
                        <button className="edit-btn" onClick={(e) => handleEditStart(e, session)} title="Rename chat">
                          <Edit2 size={12} />
                        </button>
                        <button className="delete-btn" onClick={(e) => handleDeleteClick(e, session.session_id)} title="Delete chat">
                          <Trash2 size={12} />
                        </button>
                      </div>
                    </>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      )}

      <div className="sidebar-footer">
        <div className="user-profile glass-light">
          <div className="user-avatar">
            <User size={18} />
          </div>
          <div className="user-info">
            <span className="username">{user?.username || 'Guest'}</span>
            <span className="status">{isAdmin ? 'System admin' : 'Mother account'}</span>
          </div>
          <button className="logout-btn" onClick={onLogout} title="Log Out">
            <LogOut size={18} />
          </button>
        </div>
      </div>

      <ConfirmDialog
        isOpen={!!pendingDeleteSessionId}
        title="Delete conversation?"
        message="This conversation will be removed from your history. This cannot be undone."
        confirmLabel="Delete conversation"
        cancelLabel="Keep conversation"
        isBusy={isDeletingSession}
        error={deleteError}
        onCancel={closeDeleteDialog}
        onConfirm={confirmDeleteSession}
      />
      
    </aside>
  );
};

export default Sidebar;
