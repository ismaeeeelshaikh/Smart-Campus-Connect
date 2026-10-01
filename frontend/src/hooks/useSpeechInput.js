import { useCallback, useEffect, useRef, useState } from 'react';

const ERRORS = {
  'not-allowed': "Microphone access is blocked. Allow it from the lock icon in the browser's address bar.",
  'service-not-allowed': "Microphone access is blocked. Allow it from the lock icon in the browser's address bar.",
  'audio-capture': 'No microphone found. Please connect one and try again.',
  network: 'Voice input needs an internet connection.',
};

/**
 * Voice typing with the browser's Web Speech API (Chrome / Edge).
 * The microphone permission is asked only when the user presses the mic button.
 * `en-IN` understands Indian English and Hinglish well.
 */
export function useSpeechInput({ onText, lang = 'en-IN' }) {
  const Recognition = typeof window !== 'undefined' && (window.SpeechRecognition || window.webkitSpeechRecognition);
  const supported = Boolean(Recognition);
  const [listening, setListening] = useState(false);
  const [error, setError] = useState('');
  const recognitionRef = useRef(null);
  const keepListeningRef = useRef(false); // the browser stops after a pause; restart while the user wants it
  const onTextRef = useRef(onText);

  useEffect(() => {
    onTextRef.current = onText;
  }, [onText]);

  const stop = useCallback(() => {
    keepListeningRef.current = false;
    setListening(false);
    recognitionRef.current?.stop();
  }, []);

  const start = useCallback(() => {
    if (!supported) {
      setError('Voice input works in Chrome or Edge.');
      return;
    }
    if (!recognitionRef.current) {
      const recognition = new Recognition();
      recognition.lang = lang;
      recognition.continuous = true;
      recognition.interimResults = false;
      recognition.onresult = (event) => {
        let text = '';
        for (let i = event.resultIndex; i < event.results.length; i++) {
          if (event.results[i].isFinal) text += event.results[i][0].transcript;
        }
        if (text.trim()) onTextRef.current?.(text.trim());
      };
      recognition.onerror = (event) => {
        if (event.error === 'no-speech' || event.error === 'aborted') return;
        keepListeningRef.current = false;
        setListening(false);
        setError(ERRORS[event.error] || 'Voice input stopped. Please try again.');
      };
      recognition.onend = () => {
        if (keepListeningRef.current) {
          try {
            recognition.start();
          } catch {
            /* already restarting */
          }
        } else {
          setListening(false);
        }
      };
      recognitionRef.current = recognition;
    }
    setError('');
    keepListeningRef.current = true;
    setListening(true);
    try {
      recognitionRef.current.start();
    } catch {
      /* already listening */
    }
  }, [Recognition, lang, supported]);

  useEffect(
    () => () => {
      keepListeningRef.current = false;
      recognitionRef.current?.abort();
    },
    []
  );

  return { supported, listening, error, start, stop, toggle: listening ? stop : start, clearError: () => setError('') };
}
