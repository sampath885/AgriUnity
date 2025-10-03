import React, { useState, useRef, forwardRef, useImperativeHandle } from 'react';
import './PhotoUploader.css';

const PhotoUploader = forwardRef(({ onSend, onClose, isMobile = false }, ref) => {
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [caption, setCaption] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  
  const fileInputRef = useRef(null);
  const dropZoneRef = useRef(null);

  useImperativeHandle(ref, () => ({
    selectFile: () => fileInputRef.current?.click(),
    clearFile: () => handleClearFile()
  }));

  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    if (file && file.type.startsWith('image/')) {
      processFile(file);
    } else {
      alert('Please select a valid image file.');
    }
  };

  const processFile = (file) => {
    setSelectedFile(file);
    
    // Create preview URL
    const reader = new FileReader();
    reader.onload = (e) => {
      setPreviewUrl(e.target.result);
    };
    reader.readAsDataURL(file);
  };

  const handleDragEnter = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      const file = files[0];
      if (file.type.startsWith('image/')) {
        processFile(file);
      } else {
        alert('Please drop a valid image file.');
      }
    }
  };

  const handleClearFile = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
    setCaption('');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleSend = async () => {
    if (!selectedFile) return;
    
    setIsUploading(true);
    try {
      // Simulate upload delay
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      onSend(selectedFile);
    } catch (error) {
      console.error('Error uploading photo:', error);
      alert('Failed to upload photo. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleCaptionChange = (e) => {
    setCaption(e.target.value);
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getImageDimensions = (file) => {
    return new Promise((resolve) => {
      const img = new Image();
      img.onload = () => {
        resolve({ width: img.width, height: img.height });
      };
      img.src = URL.createObjectURL(file);
    });
  };

  const [imageDimensions, setImageDimensions] = useState(null);

  React.useEffect(() => {
    if (selectedFile) {
      getImageDimensions(selectedFile).then(setImageDimensions);
    }
  }, [selectedFile]);

  return (
    <div className={`photo-uploader-modal ${isMobile ? 'mobile' : ''}`}>
      <div className="photo-uploader-content">
        <div className="photo-uploader-header">
          <h3>📷 Photo Message</h3>
          <button className="close-btn" onClick={onClose}>✕</button>
        </div>

        <div className="photo-uploader-body">
          {!selectedFile ? (
            <div className="upload-section">
              <div 
                ref={dropZoneRef}
                className={`drop-zone ${dragActive ? 'drag-active' : ''}`}
                onDragEnter={handleDragEnter}
                onDragLeave={handleDragLeave}
                onDragOver={handleDragOver}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
              >
                <div className="drop-zone-content">
                  <div className="upload-icon">📷</div>
                  <h4>Click or drag to upload</h4>
                  <p>Support for JPG, PNG, GIF up to 10MB</p>
                  <button className="browse-btn">Browse Files</button>
                </div>
              </div>
              
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={handleFileSelect}
                style={{ display: 'none' }}
              />
            </div>
          ) : (
            <div className="preview-section">
              <div className="image-preview">
                <img src={previewUrl} alt="Preview" />
                <div className="image-overlay">
                  <button className="remove-btn" onClick={handleClearFile}>
                    ✕
                  </button>
                </div>
              </div>
              
              <div className="image-info">
                <div className="info-row">
                  <span className="label">File:</span>
                  <span className="value">{selectedFile.name}</span>
                </div>
                <div className="info-row">
                  <span className="label">Size:</span>
                  <span className="value">{formatFileSize(selectedFile.size)}</span>
                </div>
                {imageDimensions && (
                  <div className="info-row">
                    <span className="label">Dimensions:</span>
                    <span className="value">{imageDimensions.width} × {imageDimensions.height}</span>
                  </div>
                )}
                <div className="info-row">
                  <span className="label">Type:</span>
                  <span className="value">{selectedFile.type}</span>
                </div>
              </div>
              
              <div className="caption-section">
                <label htmlFor="caption">Add a caption (optional):</label>
                <textarea
                  id="caption"
                  value={caption}
                  onChange={handleCaptionChange}
                  placeholder="Describe your photo..."
                  rows="3"
                  maxLength="200"
                />
                <div className="caption-counter">
                  {caption.length}/200
                </div>
              </div>
              
              <div className="upload-actions">
                <button className="retry-btn" onClick={handleClearFile}>
                  🔄 Choose Different Photo
                </button>
                <button 
                  className={`send-btn ${isUploading ? 'uploading' : ''}`}
                  onClick={handleSend}
                  disabled={isUploading}
                >
                  {isUploading ? '📤 Uploading...' : '📤 Send Photo'}
                </button>
              </div>
            </div>
          )}
        </div>

        <div className="photo-uploader-footer">
          <div className="upload-tips">
            <p>💡 Tips:</p>
            <ul>
              <li>Use high-quality images for better clarity</li>
              <li>Keep file sizes under 10MB for faster uploads</li>
              <li>Add descriptive captions to help others understand</li>
              <li>Supported formats: JPG, PNG, GIF, WebP</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
});

PhotoUploader.displayName = 'PhotoUploader';

export default PhotoUploader;
