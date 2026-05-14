'use client';

import { useEffect, useState, useRef, useCallback } from 'react';

interface SpeechRecognitionEvent extends Event {
  results: SpeechRecognitionResultList;
  isFinal: boolean;
}

interface SpeechRecognitionResultList {
  [index: number]: SpeechRecognitionResult;
  length: number;
}

interface SpeechRecognitionResult {
  [index: number]: SpeechRecognitionAlternative;
  isFinal: boolean;
}

interface SpeechRecognitionAlternative {
  transcript: string;
  confidence: number;
}

/**
 * @param onBargeIn Called when the user starts speaking while the assistant may be talking (stop TTS immediately).
 */
export const useVoiceRecognition = (onBargeIn?: () => void) => {
  const recognitionRef = useRef<any>(null);
  const onBargeInRef = useRef(onBargeIn);
  onBargeInRef.current = onBargeIn;

  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [interimTranscript, setInterimTranscript] = useState('');
  const [isSupported, setIsSupported] = useState(false);
  const lastProcessedIndexRef = useRef(0);
  const accumulatedTextRef = useRef('');

  const interruptAssistantAudio = useCallback(() => {
    if (onBargeInRef.current) {
      onBargeInRef.current();
    } else {
      try {
        window.speechSynthesis?.cancel();
      } catch (e) {
        console.warn('[Speech] Failed to cancel speechSynthesis', e);
      }
    }
  }, []);

  useEffect(() => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    setIsSupported(!!SpeechRecognition);

    if (SpeechRecognition) {
      recognitionRef.current = new SpeechRecognition();
      const recognition = recognitionRef.current;

      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = 'en-US';
      recognition.maxAlternatives = 1;

      recognition.onstart = () => {
        console.log('[Speech] Recognition started');
        interruptAssistantAudio();
        setIsListening(true);
        accumulatedTextRef.current = '';
        lastProcessedIndexRef.current = 0;
      };

      recognition.onend = () => {
        console.log('[Speech] Recognition ended');
        if (accumulatedTextRef.current.trim()) {
          console.log('[Speech] Final transcript:', accumulatedTextRef.current);
          setTranscript(accumulatedTextRef.current.trim());
        }
        setInterimTranscript('');
        setIsListening(false);
      };

      recognition.onresult = (event: SpeechRecognitionEvent) => {
        let finalAccumulated = '';
        let currentInterim = '';

        for (let i = 0; i < event.results.length; i++) {
          const text = event.results[i][0].transcript;

          if (event.results[i].isFinal) {
            finalAccumulated += text + ' ';
          } else {
            currentInterim += text;
          }
        }

        accumulatedTextRef.current = finalAccumulated.trim();
        lastProcessedIndexRef.current = event.results.length;

        const displayText = (accumulatedTextRef.current + ' ' + currentInterim).trim();
        const hasUserSpeech =
          currentInterim.trim().length > 0 || accumulatedTextRef.current.trim().length > 0;

        if (hasUserSpeech) {
          const speaking =
            typeof window !== 'undefined' &&
            window.speechSynthesis &&
            (window.speechSynthesis.speaking || window.speechSynthesis.pending);
          if (speaking) {
            interruptAssistantAudio();
          }
        }

        console.log(`[Speech] Interim: "${currentInterim}" | Final so far: "${accumulatedTextRef.current}"`);

        setTranscript(displayText);
        setInterimTranscript(currentInterim);
      };

      recognition.onerror = (event: any) => {
        console.error('[Speech] Recognition error:', event.error);
      };
    }

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.abort();
      }
    };
  }, [interruptAssistantAudio]);

  const startListening = useCallback(() => {
    if (recognitionRef.current && !isListening) {
      console.log('[Speech] Starting...');
      setTranscript('');
      setInterimTranscript('');
      accumulatedTextRef.current = '';
      lastProcessedIndexRef.current = 0;
      recognitionRef.current.start();
    }
  }, [isListening]);

  const stopListening = useCallback(() => {
    if (recognitionRef.current && isListening) {
      console.log('[Speech] Stopping...');
      recognitionRef.current.stop();
    }
  }, [isListening]);

  const resetTranscript = useCallback(() => {
    console.log('[Speech] Resetting...');
    setTranscript('');
    setInterimTranscript('');
    accumulatedTextRef.current = '';
    lastProcessedIndexRef.current = 0;
  }, []);

  return {
    isListening,
    transcript,
    interimTranscript,
    startListening,
    stopListening,
    resetTranscript,
    isSupported,
  };
};

export const useTextToSpeech = () => {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isSupported, setIsSupported] = useState(false);

  useEffect(() => {
    setIsSupported(!!window.speechSynthesis);
  }, []);

  const stop = useCallback(() => {
    if (typeof window === 'undefined' || !window.speechSynthesis) return;
    try {
      window.speechSynthesis.cancel();
      requestAnimationFrame(() => {
        try {
          window.speechSynthesis.cancel();
        } catch {
          /* ignore */
        }
      });
    } finally {
      setIsSpeaking(false);
    }
  }, []);

  const speak = useCallback(
    (text: string, onEnd?: () => void) => {
      if (!window.speechSynthesis) return;

      window.speechSynthesis.cancel();

      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 0.9;
      utterance.pitch = 1;
      utterance.volume = 1;

      utterance.onstart = () => setIsSpeaking(true);
      utterance.onend = () => {
        setIsSpeaking(false);
        onEnd?.();
      };
      utterance.onerror = () => {
        setIsSpeaking(false);
      };

      window.speechSynthesis.speak(utterance);
    },
    []
  );

  return {
    speak,
    stop,
    isSpeaking,
    isSupported,
  };
};
