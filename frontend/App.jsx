import React, { useState, useEffect } from "react";
import { BrowserRouter, Routes, Route, useNavigate, useLocation, Navigate } from "react-router-dom";
import ChatWindow from "./src/components/ChatWindow";
import Sidebar from "./src/components/Sidebar";
import Header from "./src/components/Header";
import Education from "./src/components/Education";
import MyScans from "./src/components/MyScans";
import AdminDashboard from "./src/components/AdminDashboard";
import SystemLogs from "./src/components/SystemLogs";
import LandingPage from "./src/components/LandingPage";
import Auth from "./src/components/Auth";
import Profile from "./src/components/Profile";
import "./App.css";
import "./src/styles/homecare.css";

// Protected Route for admin pages
function ProtectedAdminRoute({ component: Component, user, ...props }) {
  return user?.role === "system_admin" ? <Component {...props} /> : <Navigate to="/chat" />;
}

function App() {
  const [user, setUser] = useState(null);
  const [showAuth, setShowAuth] = useState(false);
  const [messages, setMessages] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [activeView, setActiveView] = useState("chat");
  const [isSidebarOpen, setIsSidebarOpen] = useState(window.innerWidth > 768);
  const [theme, setTheme] = useState(
    localStorage.getItem("pregai_theme") || "light"
  );

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("pregai_theme", theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === "light" ? "dark" : "light"));
  };

  // react-router hooks (will be initialized inside Router wrapper)
  const navigate = useNavigate();
  const location = useLocation();

  // Load user from localStorage on mount (Enrich user data with fetch if needed)
  useEffect(() => {
    const fetchUserData = async () => {
      const savedUser = localStorage.getItem("pregai_user");
      const token = localStorage.getItem("pregai_token");

      if (savedUser && token) {
        try {
          // Verify token and get fresh user data
          const response = await fetch("/api/v1/auth/me", {
            headers: { Authorization: `Bearer ${token}` },
          });

          if (response.ok) {
            const freshUser = await response.json();
            setUser(freshUser);
            localStorage.setItem("pregai_user", JSON.stringify(freshUser));

            if (freshUser.role === "system_admin" && activeView === "chat") {
              navigate('/admin');
            }
          } else {
            // Token expired or invalid
            handleLogout();
          }
        } catch (error) {
          // Network error, just use saved user for now
          setUser(JSON.parse(savedUser));
        }
      }
    };

    const pathToView = (p) => {
      if (!p || p === "/") return "chat";
      if (p.startsWith("/admin/logs")) return "system_logs";
      if (p.startsWith("/admin")) return "admin_dashboard";
      if (p.startsWith("/education")) return "education";
      if (p.startsWith("/scans")) return "scans";
      if (p.startsWith("/profile")) return "profile";
      if (p.startsWith("/chat")) return "chat";
      return "chat";
    };

    const initialView = pathToView(window.location.pathname);
    setActiveView(initialView);

    fetchUserData();

    return undefined;
  }, []);

  const handleAuthSuccess = (username, role) => {
    window.location.reload();
  };

  const handleLogout = () => {
    localStorage.removeItem("pregai_token");
    localStorage.removeItem("pregai_user");
    setUser(null);
    setMessages([]);
    setCurrentSessionId(null);
    setSessions([]);
    navigate('/chat');
  };

  // Fetch sessions for logged-in user
  useEffect(() => {
    if (user) {
      fetchSessions();
    }
  }, [user]);

  const fetchSessions = async () => {
    try {
      const token = localStorage.getItem("pregai_token");
      const response = await fetch("/api/v1/chat/sessions", {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setSessions(data);
      }
    } catch (error) {
      console.error("Failed to fetch sessions:", error);
    }
  };

  const loadSession = async (sessionId) => {
    try {
      const token = localStorage.getItem("pregai_token");
      const response = await fetch(`/api/v1/chat/sessions/${sessionId}/messages`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        // Format messages for UI
        const formatted = data.map(m => ({
          id: m.message_id,
          role: m.role,
          text: m.content,
          timestamp: m.timestamp,
          type: m.type,
          imageUrl: m.imageUrl,
          prediction: m.mlContext?.classification,
          scanName: m.scanName,
          mlContext: m.mlContext
        }));
        setMessages(formatted);
        setCurrentSessionId(sessionId);
        navigate('/chat');
      }
    } catch (error) {
      console.error("Failed to load session:", error);
    }
  };

  const startNewChat = () => {
    setMessages([]);
    setCurrentSessionId(null);
    navigate('/chat');
  };

  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth <= 768) {
        setIsSidebarOpen(false);
      } else {
        setIsSidebarOpen(true);
      }
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  const addMessage = (role, text, metadata = {}) => {
    const newMessage = {
      id: metadata.id || Date.now().toString(),
      role,
      text,
      timestamp: new Date().toISOString(),
      ...metadata,
    };
    setMessages((prev) => [...prev, newMessage]);
  };

  const updateMessage = (id, newText) => {
    setMessages((prev) =>
      prev.map((msg) => (msg.id === id ? { ...msg, text: newText } : msg))
    );
  };

  const renameSession = async (sessionId, newTitle) => {
    try {
      const token = localStorage.getItem("pregai_token");
      const response = await fetch(`/api/v1/chat/sessions/${sessionId}`, {
        method: "PATCH",
        headers: { 
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}` 
        },
        body: JSON.stringify({ title: newTitle }),
      });
      if (response.ok) {
        setSessions(prev => 
          prev.map(s => s.session_id === sessionId ? { ...s, title: newTitle } : s)
        );
      }
    } catch (error) {
      console.error("Failed to rename session:", error);
    }
  };

  const deleteSession = async (sessionId) => {
    try {
      const token = localStorage.getItem("pregai_token");
      const response = await fetch(`/api/v1/chat/sessions/${sessionId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        setSessions(prev => prev.filter(s => s.session_id !== sessionId));
        if (currentSessionId === sessionId) {
          startNewChat();
        }
        return true;
      }
      return false;
    } catch (error) {
      console.error("Failed to delete session:", error);
      return false;
    }
  };

  return (
    <div
      className={`app-container ${
        isSidebarOpen ? "sidebar-open" : "sidebar-closed"
      }`}
    >
      <Header
        toggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
        theme={theme}
        toggleTheme={toggleTheme}
        showMenu={!!user}
        isLanding={!user}
      />

      {!user && !showAuth ? (
        <LandingPage onGetStarted={() => setShowAuth(true)} />
      ) : !user && showAuth ? (
        <Auth onAuthSuccess={handleAuthSuccess} />
      ) : (
        <div className="app-main-layout">
          <Sidebar
            user={user}
            isOpen={isSidebarOpen}
            toggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
            activeView={activeView}
            onLogout={handleLogout}
            sessions={sessions}
            currentSessionId={currentSessionId}
            onLoadSession={loadSession}
            onNewChat={startNewChat}
            onRenameSession={renameSession}
            onDeleteSession={deleteSession}
            setActiveView={(view) => {
              const _map = { chat: '/chat', education: '/education', scans: '/scans', profile: '/profile', admin_dashboard: '/admin', system_logs: '/admin/logs' };
              navigate(_map[view] || '/chat');
              if (window.innerWidth <= 768) setIsSidebarOpen(false);
            }}
          />
          <main className="main-content">
            <div className={`view-container ${location.pathname.startsWith('/chat') ? 'chat-view' : ''}`}>
              <Routes>
                <Route path="/" element={<Navigate to="/chat" replace />} />
                <Route path="/chat" element={
                  <ChatWindow
                    messages={messages}
                    addMessage={addMessage}
                    updateMessage={updateMessage}
                    currentSessionId={currentSessionId}
                    setCurrentSessionId={(id) => {
                      setCurrentSessionId(id);
                      fetchSessions(); // Refresh session list after new session ID received
                    }}
                  />
                } />
                <Route path="/education" element={<Education />} />
                <Route path="/scans" element={<MyScans />} />
                <Route path="/profile" element={<Profile user={user} onLogout={handleLogout} />} />
                <Route path="/admin" element={user?.role === 'system_admin' ? <AdminDashboard onNavigateToLogs={() => navigate('/admin/logs')} /> : <Navigate to="/chat" />} />
                <Route path="/admin/logs" element={user?.role === 'system_admin' ? <SystemLogs /> : <Navigate to="/chat" />} />
              </Routes>
            </div>
          </main>
        </div>
      )}
    </div>
  );
}

export default function AppWrapper() {
  return (
    <BrowserRouter>
      <App />
    </BrowserRouter>
  );
}
