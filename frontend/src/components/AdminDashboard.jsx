import React, { useState, useEffect } from 'react';
import { ShieldAlert, Activity, Users, Clock, AlertCircle, Info, ShieldCheck, CheckCircle, X } from 'lucide-react';
import './AdminDashboard.css';
import { formatToLocalTime } from '../utils/dateUtils';

const AdminDashboard = ({ onNavigateToLogs }) => {
  const [stats, setStats] = useState({
    totalUsers: 0,
    activeAlerts: 0,
    systemStatus: 'Loading...',
    scansToday: 0
  });

  const [recentLogs, setRecentLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      const token = localStorage.getItem('pregai_token');
      if (!token) {
        console.error("No admin token found");
        setLoading(false);
        return;
      }

      try {
        const statsRes = await fetch('/api/v1/admin/stats', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (statsRes.ok) {
          const statsData = await statsRes.json();
          setStats(statsData);
        } else {
          console.error("Failed to fetch stats:", await statsRes.text());
        }

        const logsRes = await fetch('/api/v1/admin/logs?limit=5', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        
        if (logsRes.ok) {
          const logsData = await logsRes.json();
          setRecentLogs(logsData);
        } else {
          console.error("Failed to fetch logs:", await logsRes.text());
        }
        
        setLoading(false);
      } catch (error) {
        console.error("Error fetching admin data:", error);
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  return (
    <div className="admin-dashboard fade-in">
      <div className="dashboard-header">
        <h1>Keep the care system accountable.</h1>
        <p>Real-time monitoring, scan activity, and safety logs</p>
      </div>

      <div className="stats-grid">
        <div className="stat-card glass-card">
          <div className="stat-icon users"><Users size={24} /></div>
          <div className="stat-content">
            <span className="stat-value">{stats.totalUsers.toLocaleString()}</span>
            <span className="stat-label">Total Users</span>
          </div>
        </div>
        <div className="stat-card glass-card">
          <div className="stat-icon alerts"><ShieldAlert size={24} /></div>
          <div className="stat-content">
            <span className="stat-value">{stats.activeAlerts}</span>
            <span className="stat-label">Safety alerts</span>
          </div>
        </div>
        <div className="stat-card glass-card">
          <div className="stat-icon health"><Activity size={24} /></div>
          <div className="stat-content">
            <span className="stat-value">{stats.systemStatus === 'Optimal' ? '99.9%' : '---'}</span>
            <span className="stat-label">System uptime</span>
          </div>
        </div>
        <div className="stat-card glass-card">
          <div className="stat-icon scans"><Clock size={24} /></div>
          <div className="stat-content">
            <span className="stat-value">{(stats.totalScans ?? stats.scansToday).toLocaleString()}</span>
            <span className="stat-label">Total scans</span>
            <span className="stat-sub">Today: {(stats.scansToday ?? 0).toLocaleString()}</span>
          </div>
        </div>

        <div className="stat-card glass-card">
          <div className="stat-icon validated"><CheckCircle size={20} /></div>
          <div className="stat-content">
            <span className="stat-value">{(stats.validatedTotal ?? stats.predictionsToday ?? 0).toLocaleString()}</span>
            <span className="stat-label">Validated scans</span>
            <span className="stat-sub">Today: {(stats.validatedToday ?? stats.predictionsToday ?? 0).toLocaleString()}</span>
          </div>
        </div>

        <div className="stat-card glass-card">
          <div className="stat-icon rejected"><X size={20} /></div>
          <div className="stat-content">
            <span className="stat-value">{(stats.rejectedTotal ?? 0).toLocaleString()}</span>
            <span className="stat-label">Rejected scans</span>
            <span className="stat-sub">Today: {(stats.rejectedToday ?? 0).toLocaleString()}</span>
          </div>
        </div>

        <div className="stat-card glass-card">
          <div className="stat-icon preds"><Info size={20} /></div>
          <div className="stat-content">
            <span className="stat-value">{(stats.totalPredictions ?? stats.validatedTotal ?? 0).toLocaleString()}</span>
            <span className="stat-label">Total predictions</span>
            <span className="stat-sub">Today: {(stats.predictionsToday ?? stats.validatedToday ?? 0).toLocaleString()}</span>
          </div>
        </div>
      </div>

      <div className="dashboard-main">
        <div className="logs-section glass-card">
          <div className="section-header">
            <h2>Recent activity</h2>
            <button className="view-all" onClick={onNavigateToLogs}>Open system logs</button>
          </div>
          <div className="logs-list-simple">
            {loading ? (
              <p>Loading activity...</p>
            ) : recentLogs.length > 0 ? (
              recentLogs.map(log => (
                <div key={log.id} className={`log-item-simple ${log.level.toLowerCase()}`}>
                  <div className="log-marker"></div>
                  <div className="log-icon-simple">
                    {log.level === 'ALERT' || log.level === 'ERROR' ? <ShieldAlert size={18} /> : <Activity size={18} />}
                  </div>
                  <div className="log-info-simple">
                    <div className="log-top">
                      <span className="log-badge-simple">{log.module}</span>
                      <span className="log-time-simple">{formatToLocalTime(log.timestamp)}</span>
                    </div>
                    <p className="log-msg-simple">{log.activity}</p>
                  </div>
                </div>
              ))
            ) : (
              <p>No recent activity found.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminDashboard;
