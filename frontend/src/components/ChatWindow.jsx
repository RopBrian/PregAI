import React, { useState, useRef, useEffect } from 'react';
import { Camera, Send, Loader2, Activity } from 'lucide-react';
import './ChatWindow.css';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { formatTimeOnly } from '../utils/dateUtils';

import brandLogo from '../assets/Header_Brandname_logo.png';

const ChatWindow = ({ messages, addMessage, updateMessage, currentSessionId, setCurrentSessionId }) => {
  const [inputText, setInputText] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(scrollToBottom, [messages]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!inputText.trim()) return;

    const userText = inputText;
    setInputText('');
    addMessage('user', userText);

    const assistantMessageId = Date.now().toString() + '-assistant';
    setIsTyping(true);
    let hasStarted = false;

    try {
      const token = localStorage.getItem('pregai_token');
      const response = await fetch('/api/v1/chat/stream', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          message: userText,
          session_id: currentSessionId
        })
      });

      if (!response.ok) throw new Error('Failed to connect to stream');

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullText = '';

      let streamBuffer = '';
      while (true) {
        try {
          const { value, done } = await reader.read();
          if (done) break;
          
          const chunk = decoder.decode(value, { stream: true });
          streamBuffer += chunk;
          
          // Handle meta marker more robustly
          if (streamBuffer.includes('__METADATA__:')) {
            const parts = streamBuffer.split('__METADATA__:');
            
            // Text before metadata (if not already processed as part of fullText)
            const remainingText = parts[0].substring(fullText.length);
            if (remainingText) {
              if (!hasStarted) {
                hasStarted = true;
                setIsTyping(false);
                addMessage('assistant', '', { id: assistantMessageId });
              }
              fullText += remainingText;
              updateMessage(assistantMessageId, fullText);
            }
            
            // Parse metadata
            try {
              const metadataContent = parts[1].trim();
              if (metadataContent) {
                 const metadata = JSON.parse(metadataContent);
                 if (metadata.session_id) {
                    setCurrentSessionId(metadata.session_id);
                    window.setTimeout(() => setCurrentSessionId(metadata.session_id), 1600);
                 }
              }
            } catch (pErr) {
              // Metadata might be partially received if there's more chunks
              console.warn("Partial metadata or parse error:", pErr);
            }
            continue; // Or keep going if more chunks possible
          }

          if (!hasStarted) {
            hasStarted = true;
            setIsTyping(false);
            addMessage('assistant', '', { id: assistantMessageId });
          }

          // Accumulate text content (exclude the metadata part if found)
          const textOnly = streamBuffer.split('__METADATA__:')[0];
          const newContent = textOnly.substring(fullText.length);
          if (newContent) {
            fullText += newContent;
            updateMessage(assistantMessageId, fullText);
          }
        } catch (readError) {
          console.error('Error reading stream:', readError);
          if (hasStarted) {
            updateMessage(assistantMessageId, fullText + "\n\n⚠️ [Connection lost. Please try again or ask a new question.]");
          } else {
            addMessage('assistant', "I'm sorry, I lost connection to the server. Please try again.");
          }
          setIsTyping(false);
          return;
        }
      }

      // Handle successful stream completion but no data (e.g. backend issue)
      if (!hasStarted) {
        setIsTyping(false);
        addMessage('assistant', "I'm having trouble responding right now. Please try again in a moment.");
      }
    } catch (error) {
      console.error('Streaming setup error:', error);
      setIsTyping(false);
      if (!hasStarted) {
        addMessage('assistant', "I'm having trouble connecting right now. Please try again.");
      }
    }
  };

  const [uploadProgress, setUploadProgress] = useState(0);
  const [analysisStatus, setAnalysisStatus] = useState('');
  const [processingStep, setProcessingStep] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const [pendingScanFile, setPendingScanFile] = useState(null);
  const [scanName, setScanName] = useState('');

  const processingSteps = [
    { label: 'Upload', detail: 'Securing the image file' },
    { label: 'Image check', detail: 'Confirming this is a fetal brain ultrasound' },
    { label: 'Screening', detail: 'Running the fetal brain pattern analysis' },
    { label: 'Heatmap', detail: 'Preparing the AI focus overlay' },
    { label: 'Report', detail: 'Saving the result for chat follow-up' }
  ];

  const getDefaultScanName = (file) => {
    if (!file?.name) return 'Untitled scan';
    return file.name.replace(/\.[^/.]+$/, '').slice(0, 80) || 'Untitled scan';
  };

  const prepareScanUpload = (file) => {
    if (!file) return;
    setPendingScanFile(file);
    setScanName(getDefaultScanName(file));
  };

  const cancelScanUpload = () => {
    setPendingScanFile(null);
    setScanName('');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const uploadFile = (file, requestedScanName) => {
    if (!file) return;

    setIsUploading(true);
    setUploadProgress(0);
    setProcessingStep(0);
    setAnalysisStatus('Getting your scan ready...');

    const formData = new FormData();
    formData.append('file', file);
    formData.append('scan_name', requestedScanName?.trim() || getDefaultScanName(file));
    if (currentSessionId) {
      formData.append('session_id', currentSessionId);
    }

    const token = localStorage.getItem('pregai_token');
    const xhr = new XMLHttpRequest();
    
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) {
        const percent = Math.round((event.loaded / event.total) * 100);
        setUploadProgress(percent);
        if (percent < 100) {
          setProcessingStep(0);
          setAnalysisStatus(`Uploading scan: ${percent}%`);
        } else {
          setProcessingStep(1);
          setAnalysisStatus('Your scan uploaded. PregAI is checking the image now...');
        }
      }
    };

    xhr.onload = async () => {
      try {
        const data = JSON.parse(xhr.responseText);
        setIsUploading(false);
        setUploadProgress(0);
        setProcessingStep(0);
        setAnalysisStatus('');

        if (xhr.status === 200) {
          if (data.status === 'success') {
            const prediction = data.module_b?.prediction || 'Unknown';
            const confidence = data.module_b?.confidence || 0;
            const displayScanName = data.scan_name || requestedScanName || getDefaultScanName(file);
            if (data.session_id) {
              setCurrentSessionId(data.session_id);
            }
            
            let resultMessage = data.result_message;
            if (prediction === 'Normal') {
              resultMessage = resultMessage || `**${displayScanName}** was reviewed successfully.\n\n` +
                `PregAI identified a **normal** fetal brain development pattern ` +
                `with ${Math.round(confidence)}% confidence.\n\n` +
                `This can be reassuring, but it is still an educational screening result. Please share the report with your healthcare provider for clinical interpretation.`;
            } else if (prediction === 'Abnormal') {
              resultMessage = resultMessage || `Thank you for uploading **${displayScanName}**. We've completed the AI analysis.\n\n` +
                `Our screening has flagged some areas that may need attention ` +
                `(${Math.round(confidence)}% confidence). ` +
                `**Please don't panic** - this is a preliminary AI screening, not a diagnosis.\n\n` +
                `**What this means:** This result suggests your doctor should take a closer look. ` +
                `Many flagged scans turn out to be perfectly fine upon professional review.\n\n` +
                `**Next step:** Please discuss this result with your obstetrician or ` +
                `maternal-fetal medicine specialist. They have the expertise to interpret ` +
                `your complete medical picture.\n\n` +
                `You can ask me questions about the wording or what to ask at your appointment.`;
            } else {
              resultMessage = resultMessage || `**${displayScanName}** analysis complete: ${prediction} (${Math.round(confidence)}% confidence).\n\n` +
                `Please consult with your healthcare provider for a professional interpretation.`;
            }
            
            addMessage('assistant', resultMessage, {
              type: 'analysis',
              imageUrl: data.grad_cam_url || data.original_url,
              prediction: prediction,
              scanName: displayScanName,
              mlContext: data.ml_context
            });
          } else if (data.status === 'invalid_image') {
            const displayScanName = data.scan_name || requestedScanName || getDefaultScanName(file);
            if (data.session_id) {
              setCurrentSessionId(data.session_id);
            }
            addMessage('assistant', data.result_message || `I wasn't able to analyze **${displayScanName}**.\n\n${data.message}\n\n` +
              `**Tip:** Please upload a clear fetal brain ultrasound image for analysis. ` +
              `If you need help, just ask!`, {
              type: 'warning',
              imageUrl: data.original_url,
              scanName: displayScanName
            });
          } else {
            addMessage('assistant', `I had trouble analyzing your scan: ${data.message || 'Please try again.'}\n\n` +
              `If this continues, try uploading a clearer image or contact support.`);
          }
        } else {
          addMessage('assistant', `I'm having trouble connecting right now. Please try uploading your scan again in a moment.`);
        }
      } catch (err) {
        setIsUploading(false);
        setUploadProgress(0);
        setProcessingStep(0);
        setAnalysisStatus('');
        addMessage('assistant', `I had trouble processing the response. Please try again.`);
      }
    };

    xhr.onerror = () => {
      setIsUploading(false);
      setUploadProgress(0);
      setProcessingStep(0);
      setAnalysisStatus('');
      addMessage('assistant', `I'm having trouble connecting right now. Please try uploading your scan again in a moment.`);
    };

    const statusMessages = [
      "Checking image quality...",
      "Looking for fetal brain landmarks...",
      "Screening the scan pattern...",
      "Preparing the heatmap...",
      "Writing your report summary..."
    ];
    let msgIndex = 0;
    const statusInterval = setInterval(() => {
      if (xhr.readyState === 4) {
        clearInterval(statusInterval);
      } else if (xhr.readyState < 4) {
        setProcessingStep(Math.min(msgIndex + 1, processingSteps.length - 1));
        setAnalysisStatus(statusMessages[msgIndex]);
        msgIndex = (msgIndex + 1) % statusMessages.length;
      }
    }, 2000);

    xhr.open('POST', '/api/v1/analysis/upload');
    xhr.setRequestHeader('Authorization', `Bearer ${token}`);
    xhr.send(formData);
  };

  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    prepareScanUpload(file);
  };

  const confirmScanUpload = (e) => {
    e.preventDefault();
    if (!pendingScanFile || isUploading) return;
    const requestedScanName = scanName.trim() || getDefaultScanName(pendingScanFile);
    const fileToUpload = pendingScanFile;
    setPendingScanFile(null);
    setScanName('');
    uploadFile(fileToUpload, requestedScanName);
  };

  const handleDragEnter = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    
    const files = e.dataTransfer.files;
    if (files && files.length > 0) {
      const file = files[0];
      if (file.type.startsWith('image/')) {
        prepareScanUpload(file);
      } else {
        addMessage('assistant', "Please upload an image file for scan analysis.");
      }
    }
  };



  const formatTime = (timestamp) => {
    return formatTimeOnly(timestamp);
  };

  const getAnalysisMetric = (msg, key) => {
    const context = msg.mlContext || {};
    if (key === 'classification') {
      return msg.prediction || context.classification || 'N/A';
    }
    if (key === 'confidence') {
      const confidence = context.confidence;
      return confidence === null || confidence === undefined ? 'N/A' : `${Math.round(Number(confidence))}%`;
    }
    if (key === 'moduleA') {
      return context.module_a?.prediction || context.module_a_classification || 'N/A';
    }
    if (key === 'moduleAConfidence') {
      const confidence = context.module_a?.confidence ?? context.module_a_confidence;
      return confidence === null || confidence === undefined ? 'N/A' : `${Math.round(Number(confidence))}%`;
    }
    return 'N/A';
  };

  const handleAnalysisImageError = (event) => {
    event.currentTarget.closest('.analysis-result')?.classList.add('heatmap-missing');
  };

  const renderHeroGreeting = () => {
    return (
      <div className="hero-greeting fade-in">
        <div className="hero-brand-wrapper">
          <div className="hero-logo circular">
            <img src={brandLogo} alt="PregAI Logo" className="hero-brand-img" />
          </div>
          <span className="hero-brand-name">PregAI</span>
        </div>
        <h1>What would you like to understand today?</h1>
        <p>Ask about your pregnancy, upload a scan, or bring a report question here. I will keep the language clear and careful.</p>
        
        <div className="quick-suggestions">
          <div className="suggestion-card" onClick={() => setInputText("Explain my report in simple words")}>
            <span className="sug-text">Explain my report</span>
          </div>
          <div className="suggestion-card" onClick={() => setInputText("Help me choose the right scan image")}>
            <span className="sug-text">Choose a scan image</span>
          </div>
          <div className="suggestion-card" onClick={() => setInputText("What should I ask my doctor about this result?")}>
            <span className="sug-text">Questions for my doctor</span>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div 
      className={`chat-window ${isDragging ? 'dragging' : ''}`}
      onDragEnter={handleDragEnter}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {isDragging && (
        <div className="drag-drop-overlay fade-in">
          <div className="drag-drop-content">
            <Camera size={48} />
            <h2>Drop your scan here</h2>
            <p>PregAI will check whether it can be analyzed.</p>
          </div>
        </div>
      )}

      {isUploading && (
        <div
          className="upload-progress-overlay glass-card fade-in"
          style={{ '--upload-progress': `${Math.max(uploadProgress, processingStep > 0 ? 100 : uploadProgress)}%` }}
        >
          <div className="progress-content">
            <div className="progress-visual">
              <div className="progress-icon-wrapper">
                <Loader2 className="animate-spin" size={30} color="var(--primary-dark)" />
              </div>
              <div className="progress-ring" aria-hidden="true">
                <span>{Math.max(uploadProgress, processingStep > 0 ? 100 : uploadProgress)}%</span>
              </div>
            </div>
            <div className="progress-text-container">
              <span className="progress-kicker">Secure scan screening</span>
              <h3>{scanName || 'Checking your scan'}</h3>
              <p>{analysisStatus}</p>
            </div>
            <div className="processing-steps" aria-label="Scan processing steps">
              {processingSteps.map((step, index) => (
                <div
                  key={step.label}
                  className={`processing-step ${index < processingStep ? 'done' : ''} ${index === processingStep ? 'active' : ''}`}
                >
                  <span className="step-dot"></span>
                  <div>
                    <strong>{step.label}</strong>
                    <small>{step.detail}</small>
                  </div>
                </div>
              ))}
            </div>
            <div className="progress-bar-wrapper">
              <div className="progress-bar-container">
                <div 
                  className="progress-bar-fill" 
                  style={{ width: `${uploadProgress}%` }}
                ></div>
              </div>
              <span className="progress-percent">{uploadProgress}%</span>
            </div>
          </div>
        </div>
      )}

      {pendingScanFile && !isUploading && (
        <div className="scan-name-overlay fade-in" onClick={cancelScanUpload}>
          <form className="scan-name-dialog glass-card" onSubmit={confirmScanUpload} onClick={e => e.stopPropagation()}>
            <div className="scan-name-icon">
              <Activity size={24} />
            </div>
            <h2>Name this scan</h2>
            <p>This label will be saved with the screening result so PregAI can identify it later.</p>
            <input
              type="text"
              value={scanName}
              onChange={(e) => setScanName(e.target.value)}
              maxLength={80}
              autoFocus
              className="scan-name-input"
              placeholder="Example: 20 week anatomy scan"
            />
            <div className="scan-name-actions">
              <button type="button" className="scan-name-cancel" onClick={cancelScanUpload}>Cancel</button>
              <button type="submit" className="scan-name-confirm">Start screening</button>
            </div>
          </form>
        </div>
      )}

      <div className="messages-container">
        {messages.length === 0 ? renderHeroGreeting() : (
          <>
            {messages.map((msg) => (
              <div key={msg.id} className={`message-wrapper ${msg.role}`}>
                <div className={`message glass ${msg.role} ${msg.type || ''}`}>
                  <div className="message-text">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {msg.text}
                    </ReactMarkdown>
                  </div>
                  {msg.imageUrl && (
                    <div className="analysis-result">
                      <div className="analysis-media-row">
                        <div className="analysis-image-panel">
                          <img
                            src={msg.imageUrl}
                            alt="Ultrasound Analysis"
                            className="heatmap-img"
                            onError={handleAnalysisImageError}
                          />
                          <div className="heatmap-label">
                            {msg.scanName || (msg.type === 'analysis' ? 'AI Heatmap Overlay' : 'Uploaded Scan')}
                          </div>
                        </div>
                        {msg.type === 'analysis' && (
                          <div className="chat-result-metrics" aria-label="Scan result metrics">
                            <div className="chat-metric-heading">
                              <span>Screening metrics</span>
                              <strong>{msg.scanName || 'Scan result'}</strong>
                            </div>
                            <div className="chat-metric-grid">
                              <div className="chat-metric">
                                <span>Result</span>
                                <strong>{getAnalysisMetric(msg, 'classification')}</strong>
                              </div>
                              <div className="chat-metric">
                                <span>Confidence</span>
                                <strong>{getAnalysisMetric(msg, 'confidence')}</strong>
                              </div>
                              <div className="chat-metric">
                                <span>Image check</span>
                                <strong>{getAnalysisMetric(msg, 'moduleA')}</strong>
                              </div>
                              <div className="chat-metric">
                                <span>Check confidence</span>
                                <strong>{getAnalysisMetric(msg, 'moduleAConfidence')}</strong>
                              </div>
                            </div>
                            <p>Educational AI screening only. Review the report with your healthcare provider.</p>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                  <div className="message-time">
                    {formatTime(msg.timestamp)}
                  </div>
                </div>
              </div>
            ))}
            {isTyping && (
              <div className="message-wrapper assistant">
                <div className="message glass typing">
                  <span className="dot-typing"></span>
                </div>
              </div>
            )}
          </>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-area glass">
        <form onSubmit={handleSend} className="input-form">
          <button 
            type="button" 
            className="upload-btn" 
            onClick={() => fileInputRef.current.click()}
            disabled={isUploading}
            aria-label="Upload Scan"
          >
            {isUploading ? <Loader2 className="animate-spin" size={24} /> : <Camera size={24} />}
          </button>
          <input 
            type="file" 
            ref={fileInputRef} 
            onChange={handleFileUpload} 
            accept="image/*" 
            style={{ display: 'none' }} 
          />
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder="Ask about your pregnancy or upload a scan..."
            className="text-input"
          />
          <button type="submit" className="send-btn" disabled={!inputText.trim()}>
            <Send size={20} />
          </button>
        </form>
      </div>
    </div>
  );
};

export default ChatWindow;
