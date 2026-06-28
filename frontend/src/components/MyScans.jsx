import React, { useState, useEffect } from 'react';
import { Calendar, ChevronRight, Activity, Loader2, Trash2 } from 'lucide-react';
import './MyScans.css';
import { formatToLocalTime, formatDateOnly } from '../utils/dateUtils';
import ConfirmDialog from './ConfirmDialog';

const ReportImage = ({ src, alt, fallbackUrl, allowFallback = false }) => {
  const [failed, setFailed] = useState(false);

  if (!src || failed) {
    return <div className="image-unavailable">{alt} unavailable</div>;
  }

  return (
    <img
      src={src}
      alt={alt}
      onError={(event) => {
        if (allowFallback && fallbackUrl && !event.currentTarget.dataset.fallbackApplied) {
          event.currentTarget.dataset.fallbackApplied = 'true';
          event.currentTarget.src = fallbackUrl;
          return;
        }
        setFailed(true);
      }}
    />
  );
};

const MyScans = () => {
  const [scans, setScans] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedScan, setSelectedScan] = useState(null);
  const [pendingDeleteImageId, setPendingDeleteImageId] = useState(null);
  const [isDeletingScan, setIsDeletingScan] = useState(false);
  const [deleteError, setDeleteError] = useState(null);

  const fetchHistory = async () => {
    try {
      const token = localStorage.getItem('pregai_token');
      const response = await fetch('/api/v1/analysis/history', {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (response.ok) {
        const data = await response.json();
        setScans(data);
      }
    } catch (error) {
      console.error("Failed to fetch history:", error);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, []);

  const handleDeleteScan = (e, imageId) => {
    e.stopPropagation();
    setPendingDeleteImageId(imageId);
    setDeleteError(null);
  };

  const closeDeleteDialog = () => {
    if (isDeletingScan) return;
    setPendingDeleteImageId(null);
    setDeleteError(null);
  };

  const confirmDeleteScan = async () => {
    if (pendingDeleteImageId == null) return;

    setIsDeletingScan(true);
    setDeleteError(null);
    try {
      const token = localStorage.getItem('pregai_token');
      const response = await fetch(`/api/v1/analysis/scan/${pendingDeleteImageId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      if (response.ok) {
        setScans(prev => prev.filter(s => s.image_id !== pendingDeleteImageId));
        if (selectedScan && selectedScan.image_id === pendingDeleteImageId) {
          setSelectedScan(null);
        }
        setPendingDeleteImageId(null);
      } else {
        setDeleteError('We could not delete this report. Please try again.');
      }
    } catch (error) {
      console.error("Failed to delete scan:", error);
      setDeleteError('A connection problem stopped the deletion. Please try again.');
    } finally {
      setIsDeletingScan(false);
    }
  };

  const renderReportModal = () => {
    if (!selectedScan) return null;

    const isSuccess = selectedScan.status === 'success';
    const ml = selectedScan.ml_context;

    return (
      <div className="modal-overlay fade-in" onClick={() => setSelectedScan(null)}>
        <div className="report-modal glass-card" onClick={e => e.stopPropagation()}>
          <button className="close-modal" onClick={() => setSelectedScan(null)}>&times;</button>
          
          <div className="report-header">
            <div className={selectedScan.status === 'success' ? 'success-badge' : `status-badge ${selectedScan.status}`}>
              {selectedScan.status.toUpperCase()}
            </div>
          <h2>{selectedScan.scan_name || 'Fetal brain screening report'}</h2>
            <p className="report-id">Scan ID: {selectedScan.image_id} - {formatToLocalTime(selectedScan.created_at)}</p>
          </div>

          <div className="report-content">
            <div className="image-comparison">
              <div className="img-box">
                <span className="img-label">Original Scan</span>
                <ReportImage
                  src={selectedScan.original_url}
                  alt="Original scan"
                />
              </div>
              {isSuccess && selectedScan.grad_cam_url && (
                <div className="img-box">
                  <span className="img-label">AI Heatmap Result</span>
                  <ReportImage
                    src={selectedScan.grad_cam_url}
                    alt="AI heatmap result"
                    fallbackUrl={selectedScan.original_url}
                    allowFallback
                  />
                </div>
              )}
            </div>

            <div className="metrics-grid">
              <div className="metric-card">
                <span className="metric-label">Image check</span>
                <span className="metric-value">
                  {ml?.module_a?.prediction || 'N/A'} 
                  <small>({ml?.module_a?.confidence || 0}%)</small>
                </span>
                <p className="metric-desc">Checks whether this looks like a fetal brain ultrasound image.</p>
              </div>
              <div className={`metric-card ${!isSuccess ? 'disabled' : ''}`}>
                <span className="metric-label">Screening result</span>
                <span className="metric-value">
                  {isSuccess ? selectedScan.prediction : 'N/A'}
                  {isSuccess && <small>({selectedScan.confidence}%)</small>}
                </span>
                <p className="metric-desc">Screens the image pattern and prepares an educational report.</p>
              </div>
            </div>

            <div className={`report-summary ${selectedScan.status}`}>
              <h3>{isSuccess ? 'Analysis Summary' : 'Rejection Reason'}</h3>
              <p>
                {isSuccess 
                  ? `AI analysis identified the scan as "${selectedScan.prediction}" with ${selectedScan.confidence}% confidence. This suggests a pattern consistent with ${selectedScan.prediction.toLowerCase()} fetal brain development.`
                  : selectedScan.message || "This upload was not recognized as a valid fetal brain ultrasound. Please ensure the scan is clear and focuses on the correct anatomical plane."
                }
              </p>
              <div className="disclaimer-box">
                <strong>Important:</strong> This is an educational screening result, not a diagnosis. Please review it with your healthcare provider.
              </div>
            </div>
          </div>

          <div className="report-footer">
            <button className="action-btn secondary" onClick={() => window.print()}>Export report</button>
            <button className="action-btn primary" onClick={() => setSelectedScan(null)}>Close report</button>
          </div>
        </div>
      </div>
    );
  };

  if (isLoading) {
    return (
      <div className="loading-container">
        <Loader2 className="animate-spin" size={48} color="var(--primary)" />
        <p>Retrieving your scan history...</p>
      </div>
    );
  }

  return (
    <div className="scans-view fade-in">
      <div className="scans-header">
        <h2>Your saved reports</h2>
        <p>Open, export, or delete reports whenever you need.</p>
      </div>

      {scans.length > 0 ? (
        <div className="scans-grid">
          {scans.map(scan => (
            <div 
              key={scan.id} 
              className={`scan-card glass-card ${scan.status}`}
              onClick={() => setSelectedScan(scan)}
            >
              <div className="scan-img-container">
                <img 
                  src={scan.grad_cam_url || scan.original_url} 
                  alt="Scan result" 
                  className="scan-img" 
                />
                <div className="scan-overlay">
                  {scan.status === 'success' ? (
                    <span className="conf-tag analyzed">{scan.confidence}% Match</span>
                  ) : (
                    <span className="conf-tag rejected">Rejected</span>
                  )}
                  <button 
                    className="delete-scan-btn" 
                    onClick={(e) => handleDeleteScan(e, scan.image_id)}
                    title="Delete Scan"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
              <div className="scan-details">
                <div className="scan-date-row">
                  <Calendar size={14} />
                  <span className="scan-date">{formatDateOnly(scan.created_at)}</span>
                </div>
                <div className="scan-prediction">
                  {scan.scan_name || (scan.status === 'success' ? scan.prediction : 'Invalid Scan')}
                </div>
                <div className="scan-result-label">
                  {scan.status === 'success' ? scan.prediction : 'Invalid Scan'}
                </div>
                <button 
                  className="view-details-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelectedScan(scan);
                  }}
                >
                  Read my report <ChevronRight size={18} />
                </button>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="empty-state glass">
          <div className="empty-icon-wrapper">
            <Activity size={48} />
          </div>
          <h3>No scans uploaded yet</h3>
          <p>Upload your first ultrasound scan from Ask PregAI when you are ready.</p>
        </div>
      )}

      {renderReportModal()}
      <ConfirmDialog
        isOpen={pendingDeleteImageId != null}
        title="Delete report?"
        message="This scan, heatmap, and saved report will be permanently removed from your history."
        confirmLabel="Delete report"
        cancelLabel="Keep report"
        isBusy={isDeletingScan}
        error={deleteError}
        onCancel={closeDeleteDialog}
        onConfirm={confirmDeleteScan}
      />
    </div>
  );
};

export default MyScans;
