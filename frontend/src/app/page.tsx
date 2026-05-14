'use client';

import { useEffect, useState, useRef, useCallback } from 'react';
import { Mic, MicOff } from 'lucide-react';
import { useVoiceRecognition, useTextToSpeech } from '@/hooks/useVoice';
import { useWebSocket } from '@/hooks/useWebSocket';
import { getOrCreateUserId, formatTime, isToday, isTomorrow } from '@/lib/utils';

interface Task {
  id: string;
  title: string;
  description?: string;
  dueDate?: string;
  dueTime?: string;
  completed: boolean;
  priority?: 'low' | 'medium' | 'high';
  tags?: string[];
  createdAt: string;
  updatedAt: string;
}

interface ChatMessage {
  type: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export default function Home() {
  const [userId, setUserId] = useState('');
  const [tasks, setTasks] = useState<Task[]>([]);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [awaitingConfirmation, setAwaitingConfirmation] = useState(false);
  const [demoInitialized, setDemoInitialized] = useState<boolean>(false);

  const { speak, stop: stopSpeaking, isSpeaking, isSupported: isTextToSpeechSupported } = useTextToSpeech();
  const { isListening, transcript, interimTranscript, startListening, stopListening, resetTranscript, isSupported: isSpeechRecognitionSupported } =
    useVoiceRecognition(stopSpeaking);
  const { isConnected, send, lastMessage } = useWebSocket(
    process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8888/ws/chat'
  );

  const chatEndRef = useRef<HTMLDivElement>(null);

  // Scroll to latest message
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages]);

  // Handle incoming WebSocket messages
  useEffect(() => {
    if (lastMessage) {
      const assistantMessage: ChatMessage = {
        type: 'assistant',
        content: (lastMessage.message || lastMessage.response || 'Task processed') as string,
        timestamp: new Date(),
      };

      setChatMessages(prev => [...prev, assistantMessage]);

      // Update tasks if provided
      if (Array.isArray(lastMessage.tasks)) {
        setTasks(lastMessage.tasks as unknown as Task[]);
      }

      // Speak the response
      const spoken = String(lastMessage.message || lastMessage.response || '');
      if (isTextToSpeechSupported && spoken) {
        speak(spoken);
      }

      if (lastMessage.requiresConfirmation) {
        setAwaitingConfirmation(true);
      } else {
        setAwaitingConfirmation(false);
      }

      setIsProcessing(false);
    }
  }, [lastMessage, speak, isTextToSpeechSupported]);

  const initDemo = useCallback(async () => {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8888'}/init-demo`, {
        method: 'POST',
      });
      const data = await res.json();
      if (data && data.userId) {
        localStorage.setItem('userId', data.userId);
        setUserId(data.userId);
        setDemoInitialized(true);
        setChatMessages(prev => [
          ...prev,
          { type: 'assistant', content: `Initialized demo user: ${data.userId}`, timestamp: new Date() }
        ]);
      } else if (data && data.error) {
        setError(data.error);
      }
    } catch (e: any) {
      setError(e.message || 'Init failed');
    }
  }, []);

  useEffect(() => {
    const stored = localStorage.getItem('userId');
    if (stored) {
      setUserId(stored);
      setDemoInitialized(true);
    } else {
      setUserId(getOrCreateUserId());
    }
  }, []);

  // Handle user input (transcript)
  useEffect(() => {
    if (!isListening && transcript && transcript.trim()) {
      handleUserMessage(transcript);
      resetTranscript();
    }
  }, [isListening, transcript, resetTranscript]);

  const lastSentRef = useRef<{text: string; ts: number} | null>(null);

  const handleUserMessage = useCallback(
    (message: string) => {
      if (!message.trim() || !isConnected) {
        setError(!isConnected ? 'Not connected to server' : 'Empty message');
        return;
      }

      stopSpeaking();

      // De-duplicate rapid repeated messages (same text within 2s)
      const now = Date.now();
      if (lastSentRef.current && lastSentRef.current.text === message && (now - lastSentRef.current.ts) < 2000) {
        console.log('[Chat] Duplicate message suppressed');
        return;
      }

      setError(null);
      setIsProcessing(true);

      // Add user message to chat
      const userMessage: ChatMessage = {
        type: 'user',
        content: message,
        timestamp: new Date(),
      };
      setChatMessages(prev => [...prev, userMessage]);

      // Check if we're awaiting confirmation
      const isConfirmation = awaitingConfirmation && (
        message.toLowerCase().startsWith('yes') ||
        message.toLowerCase().startsWith('yeah') ||
        message.toLowerCase().startsWith('confirm') ||
        message.toLowerCase() === 'y'
      );

      // Send to backend via WebSocket
      send({
        userId,
        message,
        isConfirmation,
      });

      lastSentRef.current = { text: message, ts: Date.now() };
    },
    [isConnected, send, userId, awaitingConfirmation, stopSpeaking]
  );

  const toggleMicrophone = () => {
    if (isListening) {
      stopListening();
    } else {
      startListening();
    }
  };

  return (
    <main className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-4 md:p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl md:text-5xl font-bold text-gray-800 mb-2">
            Voice Task Manager
          </h1>
          <p className="text-gray-600 text-lg">
            Manage your tasks completely through voice conversation
          </p>
          <div className="mt-4">
            <button
              onClick={initDemo}
              className="px-3 py-2 bg-indigo-100 text-indigo-800 rounded-md text-sm hover:bg-indigo-200"
            >
              Initialize Demo Data
            </button>
          </div>
          <div className="mt-3 flex items-center gap-2">
            <div className="px-2 py-1 bg-white border rounded-full text-xs font-medium">
              User: {userId ? userId.slice(0, 8) : '…'}
            </div>
            <div className={`px-2 py-1 rounded-full text-xs font-medium ${demoInitialized ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'}`}>
              {demoInitialized ? 'Demo ready' : 'Demo not initialized'}
            </div>
            <div className={`px-2 py-1 rounded-full text-xs font-medium ${isConnected ? 'bg-green-50 text-green-800 border' : 'bg-red-50 text-red-800 border'}`}>
              {isConnected ? 'Connected' : 'Offline'}
            </div>
            <div className={`px-2 py-1 rounded-full text-xs font-medium ${isListening ? 'bg-blue-50 text-blue-800' : 'bg-gray-50 text-gray-600'}`}>
              {isListening ? 'Listening' : 'Idle'}
            </div>
            {isTextToSpeechSupported && (
              <div
                className={`px-2 py-1 rounded-full text-xs font-medium ${
                  isSpeaking ? 'bg-violet-100 text-violet-900 border border-violet-200' : 'bg-gray-50 text-gray-500'
                }`}
              >
                {isSpeaking ? 'Assistant speaking' : 'Assistant silent'}
              </div>
            )}
          </div>
          {!isConnected && (
            <div className="mt-3 p-3 bg-red-100 text-red-800 rounded-lg text-sm">
              ⚠️ Connecting to server...
            </div>
          )}
          {!isSpeechRecognitionSupported && (
            <div className="mt-3 p-3 bg-yellow-100 text-yellow-800 rounded-lg text-sm">
              ⚠️ Speech recognition is not supported in your browser. Please use Chrome, Firefox, or Safari.
            </div>
          )}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Chat Section */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-2xl shadow-xl overflow-hidden flex flex-col h-[600px]">
              {/* Chat Messages */}
              <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-gray-50">
                {chatMessages.length === 0 ? (
                  <div className="h-full flex flex-col items-center justify-center text-center text-gray-500">
                    <Mic size={48} className="mb-4 opacity-50" />
                    <p className="text-lg font-semibold mb-2">Welcome to Voice Task Manager</p>
                    <p className="text-sm max-w-xs">
                      Click the microphone button and start speaking to manage your tasks naturally.
                    </p>
                  </div>
                ) : (
                  <>
                    {chatMessages.map((msg, idx) => (
                      <div
                        key={idx}
                        className={`flex ${
                          msg.type === 'user' ? 'justify-end' : 'justify-start'
                        } animate-fade-in`}
                      >
                        <div
                          className={`max-w-xs px-4 py-3 rounded-lg ${
                            msg.type === 'user'
                              ? 'bg-indigo-600 text-white rounded-br-none'
                              : 'bg-gray-200 text-gray-800 rounded-bl-none'
                          }`}
                        >
                          <p className="text-sm">{msg.content}</p>
                        </div>
                      </div>
                    ))}
                    {isProcessing && (
                      <div className="flex justify-start">
                        <div className="bg-gray-200 text-gray-800 px-4 py-3 rounded-lg rounded-bl-none">
                          <div className="flex space-x-2">
                            <div className="w-2 h-2 bg-gray-600 rounded-full animate-bounce"></div>
                            <div className="w-2 h-2 bg-gray-600 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                            <div className="w-2 h-2 bg-gray-600 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                          </div>
                        </div>
                      </div>
                    )}
                    <div ref={chatEndRef} />
                  </>
                )}
              </div>

              {/* Input Area */}
              <div className="bg-white border-t border-gray-200 p-4">
                {error && (
                  <div className="mb-3 p-2 bg-red-100 text-red-800 rounded text-sm">
                    {error}
                  </div>
                )}

                {transcript && (
                  <div className="mb-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                    <p className="text-xs text-gray-600 mb-1">Listening...</p>
                    <p className="text-sm text-gray-800">
                      {transcript}
                      {interimTranscript && (
                        <span className="text-gray-400">{interimTranscript}</span>
                      )}
                    </p>
                  </div>
                )}

                <div className="flex items-center justify-center gap-4">
                  <button
                    onClick={toggleMicrophone}
                    disabled={!isSpeechRecognitionSupported}
                    className={`btn-voice flex-1 max-w-xs py-4 rounded-full font-semibold transition-smooth ${
                      isListening
                        ? 'bg-red-500 hover:bg-red-600 text-white animate-pulse-ring'
                        : 'bg-indigo-600 hover:bg-indigo-700 text-white'
                    } disabled:opacity-50 disabled:cursor-not-allowed`}
                  >
                    {isListening ? (
                      <div className="flex items-center gap-2">
                        <MicOff size={20} />
                        <span>Stop Listening</span>
                      </div>
                    ) : (
                      <div className="flex items-center gap-2">
                        <Mic size={20} />
                        <span>{isSpeaking ? 'Interrupt & speak' : 'Start Speaking'}</span>
                      </div>
                    )}
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Tasks Sidebar */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-2xl shadow-xl overflow-hidden flex flex-col h-[600px]">
              {/* Sidebar Header */}
              <div className="bg-gradient-to-r from-indigo-600 to-blue-600 text-white p-6">
                <h2 className="text-xl font-bold mb-2">Your Tasks</h2>
                <p className="text-sm opacity-90">{tasks.length} tasks</p>
              </div>

              {/* Tasks List */}
              <div className="flex-1 overflow-y-auto p-4 space-y-3">
                {tasks.length === 0 ? (
                  <div className="h-full flex flex-col items-center justify-center text-center text-gray-500">
                    <p className="text-sm">No tasks yet</p>
                    <p className="text-xs opacity-70 mt-1">Say "Create a task..."</p>
                  </div>
                ) : (
                  <>
                    {/* Overdue/Today Tasks */}
                    {tasks.filter(t => t.dueDate && isToday(new Date(t.dueDate))).length > 0 && (
                      <div>
                        <h3 className="text-xs font-semibold text-gray-600 uppercase mb-2">Today</h3>
                        {tasks
                          .filter(t => t.dueDate && isToday(new Date(t.dueDate)))
                          .map(task => (
                            <div
                              key={task.id}
                              className="bg-gradient-to-r from-amber-50 to-orange-50 border-l-4 border-orange-400 p-3 rounded-lg hover:shadow-md transition-smooth"
                            >
                              <p className={`text-sm font-medium ${task.completed ? 'line-through text-gray-400' : 'text-gray-800'}`}>
                                {task.title}
                                {task.dueTime && (
                                  <span className="text-xs text-gray-500 font-normal ml-2">
                                    at {formatTime(task.dueTime)}
                                  </span>
                                )}
                              </p>
                              {task.description && (
                                <p className="text-xs text-gray-600 mt-1">{task.description}</p>
                              )}
                            </div>
                          ))}
                      </div>
                    )}

                    {/* Tomorrow Tasks */}
                    {tasks.filter(t => t.dueDate && isTomorrow(new Date(t.dueDate))).length > 0 && (
                      <div>
                        <h3 className="text-xs font-semibold text-gray-600 uppercase mb-2 mt-4">Tomorrow</h3>
                        {tasks
                          .filter(t => t.dueDate && isTomorrow(new Date(t.dueDate)))
                          .map(task => (
                            <div
                              key={task.id}
                              className="bg-gray-50 border border-gray-200 p-3 rounded-lg hover:shadow-md transition-smooth"
                            >
                              <p className={`text-sm font-medium ${task.completed ? 'line-through text-gray-400' : 'text-gray-800'}`}>
                                {task.title}
                                {task.dueTime && (
                                  <span className="text-xs text-gray-500 font-normal ml-2">
                                    at {formatTime(task.dueTime)}
                                  </span>
                                )}
                              </p>
                              {task.description && (
                                <p className="text-xs text-gray-600 mt-1">{task.description}</p>
                              )}
                            </div>
                          ))}
                      </div>
                    )}

                    {/* Other Tasks */}
                    {tasks.filter(t => !t.dueDate || (!isToday(new Date(t.dueDate)) && !isTomorrow(new Date(t.dueDate)))).length > 0 && (
                      <div>
                        <h3 className="text-xs font-semibold text-gray-600 uppercase mb-2 mt-4">Other</h3>
                        {tasks
                          .filter(t => !t.dueDate || (!isToday(new Date(t.dueDate)) && !isTomorrow(new Date(t.dueDate))))
                          .map(task => (
                            <div
                              key={task.id}
                              className="bg-gray-50 border border-gray-200 p-3 rounded-lg hover:shadow-md transition-smooth"
                            >
                              <p className={`text-sm font-medium ${task.completed ? 'line-through text-gray-400' : 'text-gray-800'}`}>
                                {task.title}
                                {task.dueTime && (
                                  <span className="text-xs text-gray-500 font-normal ml-2">
                                    at {formatTime(task.dueTime)}
                                  </span>
                                )}
                              </p>
                              {task.description && (
                                <p className="text-xs text-gray-600 mt-1">{task.description}</p>
                              )}
                            </div>
                          ))}
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="mt-8 text-center text-gray-600 text-sm">
          <p>💡 Tip: Try saying "Create a task for lunch at 12 PM" or "What's my agenda for today?"</p>
        </div>
      </div>
    </main>
  );
}
