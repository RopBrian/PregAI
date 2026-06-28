import React, { useState, useEffect } from 'react';
import { 
  ClipboardList, 
  Search, 
  Filter, 
  Download, 
  AlertCircle, 
  Info, 
  ShieldAlert,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';
import './SystemLogs.css';
import { formatToLocalTime } from '../utils/dateUtils';

const SystemLogs = () => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedModule, setSelectedModule] = useState('All Modules');
  
  useEffect(() => {
    const fetchLogs = async () => {
      const token = localStorage.getItem('pregai_token');
      if (!token) {
        console.error("No token found");
        setLoading(false);
        return;
      }
      try {
        const res = await fetch('/api/v1/admin/logs?limit=100', {
          headers: { 'Authorization': `Bearer ${token}` }
        });
        if (res.ok) {
          const data = await res.json();
          setLogs(data);
        } else {
          console.error("Failed to fetch logs:", await res.text());
        }
        setLoading(false);
      } catch (error) {
        console.error("Error fetching logs:", error);
        setLoading(false);
      }
    };

    fetchLogs();
  }, []);

  const exportToCSV = () => {
    if (logs.length === 0) return;
    
    const headers = ["Timestamp", "Level", "Module", "User", "Activity", "IP"];
    const csvContent = [
      headers.join(","),
      ...logs.map(log => [
        log.timestamp,
        log.level,
        log.module,
        log.user,
        `"${log.activity.replace(/"/g, '""')}"`,
        log.ip
      ].join(","))
    ].join("\n");

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `system_logs_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const getLevelIcon = (level) => {
    switch (level.toUpperCase()) {
      case 'ALERT':
      case 'ERROR': return <AlertCircle size={16} className="text-alert" />;
      case 'WARNING': return <ShieldAlert size={16} className="text-warning" />;
      default: return <Info size={16} className="text-info" />;
    }
  };

  const filteredLogs = logs.filter(log => {
    const matchesSearch = 
      log.activity.toLowerCase().includes(searchTerm.toLowerCase()) ||
      log.user.toLowerCase().includes(searchTerm.toLowerCase()) ||
      log.ip.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesModule = selectedModule === 'All Modules' || log.module === selectedModule;
    
    return matchesSearch && matchesModule;
  });

  return (
    <div className="system-logs-page fade-in">
      <div className="page-header">
        <div className="header-left">
          <ClipboardList className="icon-primary" size={32} />
          <div>
            <h1>System logs</h1>
            <p>Comprehensive audit trail for care, scan, chat, and security activity</p>
          </div>
        </div>
        <div className="header-actions">
          <button className="action-btn secondary" onClick={exportToCSV} disabled={logs.length === 0}>
            <Download size={18} />
            Export CSV
          </button>
        </div>
      </div>

      <div className="logs-filter-bar glass-card">
        <div className="search-box">
          <Search size={18} className="search-icon" />
          <input 
            type="text" 
            placeholder="Search by message, user, or IP..." 
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        <div className="filter-group">
          <button className="filter-btn" onClick={() => {
            setSearchTerm('');
            setSelectedModule('All Modules');
          }}>
            <Filter size={18} />
            Clear filters
          </button>
          <select 
            className="module-select"
            value={selectedModule}
            onChange={(e) => setSelectedModule(e.target.value)}
          >
            <option value="All Modules">All Modules</option>
            <option value="AUTH">AUTH</option>
            <option value="SAFETY">SAFETY</option>
            <option value="ML">ML</option>
            <option value="CHAT">CHAT</option>
            <option value="SECURITY">SECURITY</option>
          </select>
        </div>
      </div>

      <div className="logs-table-wrapper glass-card">
        {loading ? (
          <div className="loading-state" style={{ padding: '40px', textAlign: 'center' }}>
            <p>Loading audit trail...</p>
          </div>
        ) : (
          <>
            <table className="logs-table">
              <thead>
                <tr>
                  <th>Level</th>
                  <th>Timestamp</th>
                  <th>Module</th>
                  <th>User</th>
                  <th className="th-activity">Activity</th>
                  <th>IP Address</th>
                </tr>
              </thead>
              <tbody>
                {filteredLogs.length > 0 ? (
                  filteredLogs.map(log => (
                    <tr key={log.id} className={`log-row-item level-${log.level.toLowerCase()}`}>
                      <td className="col-level">
                        <div className="level-badge">
                          {getLevelIcon(log.level)}
                          <span>{log.level}</span>
                        </div>
                      </td>
                      <td className="col-time">{formatToLocalTime(log.timestamp, { second: '2-digit' })}</td>
                      <td className="col-module">
                        <span className="module-tag">{log.module}</span>
                      </td>
                      <td className="col-user">
                        <span className="user-mention">@{log.user}</span>
                      </td>
                      <td className="col-activity">{log.activity}</td>
                      <td className="col-ip"><code>{log.ip}</code></td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan="6" style={{ textAlign: 'center', padding: '40px' }}>No logs found matching your criteria.</td>
                  </tr>
                )}
              </tbody>
            </table>

            <div className="table-pagination">
              <p>Showing {filteredLogs.length} entries</p>
              <div className="pagination-controls">
                <button className="page-nav-btn" disabled><ChevronLeft size={18} /></button>
                <button className="page-num-btn active">1</button>
                <button className="page-nav-btn" disabled><ChevronRight size={18} /></button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default SystemLogs;
