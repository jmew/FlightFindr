import { useState, useEffect, useRef } from 'react';
import type { CompactFlightDeal, Message, Tool } from '../types';
import { streamChat, streamMultiCityChat } from '../services/api';
import { decompressFlightData } from '../utils/data-processing';

function parseMultiCityMessage(message: string) {
  const startMatch = message.match(/I want to start in (.*?) and end in (.*?)\. /);
  const startLocation = startMatch ? startMatch[1] : '';
  const endLocation = startMatch ? startMatch[2] : '';

  const stopsMatch = message.match(/I want to visit the following places: (.*?)\. /);
  const intermediateStops = stopsMatch ? stopsMatch[1].split(', ') : [];

  const datesMatch = message.match(/I want to travel between (.*?) and (.*?),/);
  const startDate = datesMatch ? datesMatch[1] : '';
  const endDate = datesMatch ? datesMatch[2] : '';

  const maxLengthMatch = message.match(/with a maximum trip length of (.*?) days/);
  const maxLength = maxLengthMatch ? maxLengthMatch[1] : '';

  const flexibleMatch = message.match(/The order of the intermediate stops is flexible\. /);
  const flexible = !!flexibleMatch;

  const constraintsMatch = message.match(/Please also consider the following constraints: (.*)/);
  const constraints = constraintsMatch ? constraintsMatch[1] : '';

  return { startLocation, endLocation, intermediateStops, startDate, endDate, maxLength, constraints, flexible };
}

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [thought, setThought] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const startTimeRef = useRef<number | null>(null);
  const [elapsedTime, setElapsedTime] = useState(0);
  const sessionIdRef = useRef<string | null>(null);

  useEffect(() => {
    sessionIdRef.current = crypto.randomUUID();
  }, []);

  const stopStreaming = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    startTimeRef.current = null;
    setIsLoading(false);
    setThought(null);
    setElapsedTime(0);
  };

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && isLoading) {
        stopStreaming();
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isLoading]);

  const handleSendMessage = (message: string) => {
    if (!message.trim() || isLoading) return;

    const userMessage: Message = { sender: 'user', text: message };
    setMessages((prevMessages) => [...prevMessages, userMessage]);
    setInput('');
    setIsLoading(true);
    setThought('Thinking...');
    setElapsedTime(0);
    startTimeRef.current = Date.now();

    timerRef.current = setInterval(() => {
      if (startTimeRef.current) {
        const seconds = Math.floor((Date.now() - startTimeRef.current) / 1000);
        setElapsedTime(seconds);
      }
    }, 1000);

    if (!sessionIdRef.current) {
      console.error('Session ID not initialized');
      setIsLoading(false);
      setThought(null);
      return;
    }

    let currentBotMessage = '';
    let botMessageIndex = -1;

    const onMessage = (event: any) => {
      const data = JSON.parse(event.data);
      switch (event.event) {
        case 'content':
          currentBotMessage += data.chunk;
          setMessages((prevMessages) => {
            const newMessages = [...prevMessages];
            if (botMessageIndex === -1) {
              botMessageIndex = newMessages.length;
              newMessages.push({ sender: 'bot', text: currentBotMessage });
            } else {
              newMessages[botMessageIndex] = {
                ...newMessages[botMessageIndex],
                text: currentBotMessage,
              };
            }
            return newMessages;
          });
          break;
        case 'thought':
          setThought(data.subject || data.description || 'Thinking...');
          break;
        case 'tool_code':
          const newTool: Tool = {
            callId: data.callId,
            name: data.name,
            args: data.args,
          };
          setMessages((prev) => {
            const lastMessage = prev[prev.length - 1];
            if (lastMessage?.sender === 'bot' && lastMessage.tools) {
              const updatedMessages = [...prev];
              updatedMessages[prev.length - 1] = {
                ...lastMessage,
                tools: [...lastMessage.tools, newTool],
              };
              return updatedMessages;
            } else {
              const newToolMessage: Message = {
                sender: 'bot',
                text: '',
                tools: [newTool],
              };
              return [...prev, newToolMessage];
            }
          });
          break;
        case 'error':
          setMessages((prev) => [...prev, { sender: 'bot', text: `An error occurred: ${data.error}` }]);
          stopStreaming();
          break;
        case 'tool_result':
          setMessages((prev) =>
            prev.map((msg) => {
              if (msg.tools && msg.tools.some((t: Tool) => t.callId === data.callId)) {
                let newFlightData: CompactFlightDeal[] = msg.flightData || [];
                const updatedTools = msg.tools.map((tool: Tool) => {
                  if (tool.callId === data.callId) {
                    const updatedTool = {
                      ...tool,
                      result: data.result,
                      error: data.error,
                    };
                    if (tool.name === 'check_flight_points_prices') {
                      try {
                        if (typeof data.result === 'string' && data.result.trim().startsWith('{')) {
                          const parsedResult = JSON.parse(data.result);
                          const decompressedDeals = decompressFlightData(parsedResult);
                          newFlightData = [...newFlightData, ...decompressedDeals];
                        } else if (data.result) {
                          console.warn('Tool result is not a valid JSON object:', data.result);
                        }
                      } catch (e) {
                        console.error('Error parsing or decompressing flight data:', e);
                      }
                    }
                    return updatedTool;
                  }
                  return tool;
                });
                return { ...msg, tools: updatedTools, flightData: newFlightData };
              }
              return msg;
            }),
          );
          break;
      }
    };

    const onStop = () => stopStreaming();
    const onError = (err: any) => {
      console.error('EventSource failed:', err);
      setMessages((prev) => [...prev, { sender: 'bot', text: 'An unexpected error occurred. Please check the console for details.' }]);
      stopStreaming();
    }

    if (message.startsWith('Find a multi-city trip for me.')) {
      const body = parseMultiCityMessage(message);
      streamMultiCityChat(body, sessionIdRef.current, onMessage, onStop, onError);
    } else {
      eventSourceRef.current = streamChat(message, sessionIdRef.current, onMessage, onStop, onError);
    }
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleSendMessage(input);
  };

  const handleStop = () => {
    stopStreaming();
  };

  return {
    messages,
    input,
    setInput,
    isLoading,
    thought,
    elapsedTime,
    handleFormSubmit,
    handleSendMessage,
    handleStop,
  };
}