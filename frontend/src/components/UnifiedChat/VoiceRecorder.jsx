import React, { useState, useRef, forwardRef, useImperativeHandle } from 'react';
import './VoiceRecorder.css';

const VoiceRecorder = forwardRef(({ onSend, onClose, isMobile = false }, ref) => {
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [audioBlob, setAudioBlob] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false);
  
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const timerRef = useRef(null);
  const audioRef = useRef(null);

  useImperativeHandle(ref, () => ({
    startRecording: () => handleStartRecording(),
    stopRecording: () => handleStopRecording(),
    playRecording: () => handlePlayRecording()
  }));

  const handleStartRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new MediaRecorder(stream);
      audioChunksRef.current = [];

      mediaRecorderRef.current.ondataavailable = (event) => {
        audioChunksRef.current.push(event.data);
      };

      mediaRecorderRef.current.onstop = () => {
        const blob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
        setAudioBlob(blob);
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorderRef.current.start();
      setIsRecording(true);
      setRecordingTime(0);
      
      // Start timer
      timerRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);
    } catch (error) {
      console.error('Error starting recording:', error);
      alert('Unable to access microphone. Please check permissions.');
    }
  };

  const handleStopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      clearInterval(timerRef.current);
    }
  };

  const handlePlayRecording = () => {
    if (audioBlob && audioRef.current) {
      if (isPlaying) {
        audioRef.current.pause();
        setIsPlaying(false);
      } else {
        audioRef.current.play();
        setIsPlaying(true);
      }
    }
  };

  const handleSend = () => {
    if (audioBlob) {
      onSend(audioBlob);
    }
  };

  const handleRetry = () => {
    setAudioBlob(null);
    setRecordingTime(0);
    setIsPlaying(false);
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const handleAudioEnded = () => {
    setIsPlaying(false);
  };

  return (
    <div className={`voice-recorder-modal ${isMobile ? 'mobile' : ''}`}>
      <div className="voice-recorder-content">
        <div className="voice-recorder-header">
          <h3>🎤 Voice Message</h3>
          <button className="close-btn" onClick={onClose}>✕</button>
        </div>

        <div className="voice-recorder-body">
          {!audioBlob ? (
            <div className="recording-section">
              <div className="recording-visualizer">
                {isRecording && (
                  <div className="recording-waves">
                    {[...Array(8)].map((_, i) => (
                      <div 
                        key={i} 
                        className="wave-bar"
                        style={{
                          animationDelay: `${i * 0.1}s`,
                          height: `${Math.random() * 40 + 20}px`
                        }}
                      />
                    ))}
                  </div>
                )}
              </div>

              <div className="recording-time">
                {formatTime(recordingTime)}
              </div>

              <div className="recording-controls">
                {!isRecording ? (
                  <button 
                    className="record-btn"
                    onClick={handleStartRecording}
                  >
                    🎤 Start Recording
                  </button>
                ) : (
                  <button 
                    className="stop-btn"
                    onClick={handleStopRecording}
                  >
                    ⏹️ Stop Recording
                  </button>
                )}
              </div>

              <div className="recording-tip">
                {isRecording 
                  ? 'Recording... Click stop when finished' 
                  : 'Click start to begin recording your voice message'
                }
              </div>
            </div>
          ) : (
            <div className="playback-section">
              <div className="audio-player">
                <audio 
                  ref={audioRef}
                  src={URL.createObjectURL(audioBlob)}
                  onEnded={handleAudioEnded}
                />
                
                <div className="playback-controls">
                  <button 
                    className={`play-btn ${isPlaying ? 'playing' : ''}`}
                    onClick={handlePlayRecording}
                  >
                    {isPlaying ? '⏸️' : '▶️'}
                  </button>
                  
                  <div className="audio-info">
                    <span className="duration">{formatTime(recordingTime)}</span>
                    <span className="format">WAV</span>
                  </div>
                </div>
              </div>

              <div className="playback-actions">
                <button className="retry-btn" onClick={handleRetry}>
                  🔄 Record Again
                </button>
                <button className="send-btn" onClick={handleSend}>
                  📤 Send Voice Message
                </button>
              </div>
            </div>
          )}
        </div>

        <div className="voice-recorder-footer">
          <div className="recording-tips">
            <p>💡 Tips:</p>
            <ul>
              <li>Speak clearly and at a normal pace</li>
              <li>Keep messages under 2 minutes</li>
              <li>Find a quiet environment</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
});

VoiceRecorder.displayName = 'VoiceRecorder';

export default VoiceRecorder;
