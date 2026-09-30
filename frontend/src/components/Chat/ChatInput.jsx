import React, { useState, useRef, useEffect } from 'react';
import { Send, Mic, MicOff, AlertCircle } from 'lucide-react';

const ChatInput = ({ onSendMessage, disabled }) => {
  const [message, setMessage] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [isSupported, setIsSupported] = useState(false);
  const [error, setError] = useState('');
  const [permissionGranted, setPermissionGranted] = useState(false);
  const recognitionRef = useRef(null);
  const restartTimeoutRef = useRef(null);

  // Initialize speech recognition with multi-language support
  const initializeSpeechRecognition = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    
    if (!SpeechRecognition) {
      setError('Speech recognition not supported. Please use Chrome, Edge, or Safari.');
      return null;
    }
    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    
    // UNIVERSAL LANGUAGE SUPPORT - Detects Hindi, Marathi, English automatically
    recognition.lang = 'en-IN'; // Indian English base - best for multi-language detection
    recognition.maxAlternatives = 3; // Get multiple alternatives for better accuracy
    // Handle results
    recognition.onresult = (event) => {
      let finalTranscript = '';
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += transcript;
        }
      }
      if (finalTranscript) {
        // Clean and normalize the text (already in Roman/English format)
        const cleanedText = finalTranscript.trim();
        setMessage(prev => prev + cleanedText + ' ');
      }
    };
    // Handle end - restart if still recording
    recognition.onend = () => {
      console.log('Speech recognition ended');
      
      if (isRecording) {
        restartTimeoutRef.current = setTimeout(() => {
          if (isRecording && recognitionRef.current) {
            try {
              recognitionRef.current.start();
            } catch (err) {
              console.log('Restart failed:', err);
              setIsRecording(false);
            }
          }
        }, 100);
      }
    };
    // Handle errors
    recognition.onerror = (event) => {
      console.log('Speech error:', event.error);
      
      switch (event.error) {
        case 'aborted':
          console.log('Speech recognition aborted');
          break;
        case 'not-allowed':
          setError('Microphone access denied. Please allow microphone permissions and refresh.');
          setIsRecording(false);
          setPermissionGranted(false);
          break;
        case 'no-speech':
          // Don't show error for no speech
          break;
        case 'network':
          setError('Speech recognition network error. Check internet connection.');
          setIsRecording(false);
          break;
        case 'audio-capture':
          setError('Microphone not found. Please check your microphone.');
          setIsRecording(false);
          break;
        default:
          setError(`Speech error: ${event.error}`);
          setIsRecording(false);
      }
      
      if (event.error !== 'no-speech' && event.error !== 'aborted') {
        setTimeout(() => setError(''), 4000);
      }
    };
    recognition.onstart = () => {
      console.log('Multi-language speech recognition started');
      setError('');
    };
    return recognition;
  };

  // Check browser support and permissions
  useEffect(() => {
    const checkSupportAndPermissions = async () => {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      
      if (!SpeechRecognition) {
        setError('Speech recognition not supported. Please use Chrome, Edge, or Safari.');
        return;
      }
      setIsSupported(true);
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        stream.getTracks().forEach(track => track.stop());
        setPermissionGranted(true);
        
        // Initialize speech recognition
        recognitionRef.current = initializeSpeechRecognition();
      } catch (err) {
        console.log('Microphone permission error:', err);
        setError('Microphone access denied. Please allow microphone permissions.');
        setPermissionGranted(false);
      }
    };
    checkSupportAndPermissions();
    return () => {
      if (restartTimeoutRef.current) {
        clearTimeout(restartTimeoutRef.current);
      }
    };
  }, [isRecording]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (message.trim() && !disabled) {
      onSendMessage(message.trim());
      setMessage('');
    }
  };

  const requestMicrophonePermission = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach(track => track.stop());
      setPermissionGranted(true);
      setError('');
      window.location.reload();
    } catch (err) {
      setError('Please allow microphone access in browser settings and refresh the page.');
    }
  };

  const toggleRecording = async () => {
    if (!isSupported) {
      setError('Speech recognition not supported. Please use Chrome, Edge, or Safari.');
      setTimeout(() => setError(''), 4000);
      return;
    }
    if (!permissionGranted) {
      await requestMicrophonePermission();
      return;
    }
    if (isRecording) {
      console.log('Stopping multi-language recording');
      setIsRecording(false);
      
      if (restartTimeoutRef.current) {
        clearTimeout(restartTimeoutRef.current);
        restartTimeoutRef.current = null;
      }
      
      try {
        recognitionRef.current?.stop();
      } catch (err) {
        console.log('Stop error:', err);
      }
    } else {
      console.log('Starting multi-language recording');
      try {
        setIsRecording(true);
        recognitionRef.current?.start();
        setError('');
      } catch (err) {
        console.log('Start error:', err);
        setError('Failed to start recording. Please try again.');
        setIsRecording(false);
        setTimeout(() => setError(''), 3000);
      }
    }
  };

   return (
    <div className="border-t border-background-dark bg-background-card px-4 py-3">
      {/* Error message */}
      {error && (
        <div className="px-4 py-2 bg-red-900 border-b border-red-700 rounded text-red-300 flex items-center justify-between mb-2">
          <div className="flex items-center space-x-2">
            <AlertCircle className="h-4 w-4" />
            <span className="text-sm">{error}</span>
          </div>
          {error.includes('permission') && (
            <button
              onClick={requestMicrophonePermission}
              className="text-sm bg-red-600 hover:bg-red-700 px-3 py-1 rounded"
            >
              Allow Microphone
            </button>
          )}
        </div>
      )}

      {/* Recording indicator */}
      {isRecording && (
        <div className="px-4 py-2 bg-gradient-to-r from-green-900 to-primary-700 border-b border-green-700 rounded mb-2">
          <div className="flex items-center justify-center space-x-2 text-green-300">
            <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
            <span className="text-sm font-medium">
              🎤 Listening... Speak in Hindi, Hinglish, Marathi, or English
            </span>
            <div className="w-2 h-2 bg-blue-600 rounded-full animate-pulse"></div>
          </div>
        </div>
      )}

      {/* Input form */}
      <form onSubmit={handleSubmit} className="flex items-center space-x-2">
        <input
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder={
            isRecording
              ? '🎤 Listening for your voice...'
              : "Ask APSIT's AI Assistant"
          }
          className="flex-1 px-4 py-2 rounded-lg border border-background-dark bg-background-dark text-gray-200 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent disabled:bg-gray-900"
          disabled={disabled}
        />
        <button
          type="button"
          onClick={toggleRecording}
          disabled={disabled}
          className={`px-3 py-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-offset-2 transition-all duration-200 ${
            isRecording
              ? 'bg-red-700 hover:bg-red-800 focus:ring-red-600 text-white animate-pulse'
              : !permissionGranted
              ? 'bg-yellow-600 hover:bg-yellow-700 focus:ring-yellow-600 text-white'
              : 'bg-gray-800 hover:bg-gray-700 focus:ring-gray-700 text-gray-300'
          } disabled:opacity-50 disabled:cursor-not-allowed`}
          title={
            !permissionGranted
              ? 'Click to allow microphone access'
              : isRecording
              ? 'Stop recording'
              : 'Start voice input (Multi-language)'
          }
        >
          {isRecording ? <MicOff className="h-4 w-4" /> : <Mic className="h-4 w-4" />}
        </button>
        <button
          type="submit"
          disabled={disabled || !message.trim()}
          className="px-4 py-2 bg-primary-500 hover:bg-primary-600 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
        >
          <Send className="h-4 w-4" />
        </button>
      </form>

      {/* Help text */}
      <div className="mt-2 text-xs text-gray-400 text-center">
        {!isSupported
          ? 'Speech recognition not supported - Please use Chrome, Edge, or Safari'
          : !permissionGranted
          ? '🔒 Click microphone to allow voice input'
          : isRecording
          ? '🎤 Recording active - Speak in Hindi, Hinglish, Marathi ya English'
          : 'Smart Campus Connect is here, Ask about A. P Shah Institute of Technology'}
      </div>
    </div>
  );
};

export default ChatInput;