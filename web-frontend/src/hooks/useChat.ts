import { useState, useEffect, useRef } from 'react';
import type { CompactFlightDeal, Message, Tool, BookingOption } from '../types';
import { fetchEventSource } from '@microsoft/fetch-event-source';

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

    const baseUrl = import.meta.env.VITE_API_BASE_URL || 'https://web-server-304334704110.us-central1.run.app';
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
                          if (parsedResult.deals && parsedResult.legend) {
                            const { legend, deals } = parsedResult;
                            const { cabin_codes, programs, banks, booking_urls } = legend;

                            const decompressedDeals: CompactFlightDeal[] = deals.map((deal: any, index: number) => {
                                const [segments, options, duration_minutes] = deal;

                                const firstSegment = segments[0];
                                const lastSegment = segments[segments.length - 1];
                                const departure_time = firstSegment[3];
                                const arrival_time = lastSegment[4];
                                const route = `${firstSegment[1]} -> ${lastSegment[2]}`;
                                
                                const stops = segments.slice(0, -1).map((seg: any) => seg[2]);
                                const airlines = [...new Set(segments.map((seg: any) => seg[0].substring(0, 2)))];
                                const flight_numbers = segments.map((seg: any) => seg[0]);
                                const layover_lengths = segments.slice(0, -1).map((seg: any) => seg[5]);
                                
                                let overnight_layover = false;
                                for (let i = 0; i < segments.length - 1; i++) {
                                    const arr_time = new Date(segments[i][4]);
                                    const dep_time = new Date(segments[i+1][3]);
                                    if (arr_time.getDate() !== dep_time.getDate()) {
                                        overnight_layover = true;
                                        break;
                                    }
                                }

                                const bookingOptions: BookingOption[] = options.map((opt: any) => {
                                    const [program_code, transfer_partner_codes, url_params, cabin_deals] = opt;
                                    
                                    const program = programs[program_code] || program_code;
                                    const booking_url = booking_urls[program_code]?.replace('{params}', url_params) || '';
                                    const transfer_info = transfer_partner_codes.map((code: string) => banks[code] || code);

                                    const bookingOption: BookingOption = {
                                        program,
                                        booking_url,
                                        transfer_info,
                                    };

                                    for (const cabin_code in cabin_deals) {
                                        const [points, tax, cash_price, cpp] = cabin_deals[cabin_code];
                                        const cabin_name_full = cabin_codes[cabin_code] || cabin_code;
                                        const cabin_name = cabin_name_full.toLowerCase().replace(' ', '');
                                        
                                        let cabin_key: 'economy' | 'premium' | 'business' | 'first' = 'economy';
                                        if (cabin_name.startsWith('premium')) cabin_key = 'premium';
                                        else if (cabin_name.startsWith('business')) cabin_key = 'business';
                                        else if (cabin_name.startsWith('first')) cabin_key = 'first';

                                        bookingOption[cabin_key] = {
                                            points,
                                            fees: `${tax}`,
                                            bonus: null,
                                            exact_cash_price: cash_price,
                                            exact_cpp: cpp,
                                        };
                                    }
                                    return bookingOption;
                                });

                                return {
                                    id: `${route}-${departure_time}-${index}`,
                                    route,
                                    departure_time,
                                    arrival_time,
                                    duration_minutes,
                                    stops,
                                    airlines,
                                    overnight_layover,
                                    layover_duration: layover_lengths.reduce((a: number, b: number) => a + b, 0),
                                    flight_numbers,
                                    layover_lengths,
                                    options: bookingOptions,
                                };
                            });

                            newFlightData = [...newFlightData, ...decompressedDeals];
                          }
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

    if (message.startsWith('Find a multi-city trip for me.')) {
      const body = parseMultiCityMessage(message);
      fetchEventSource(`${baseUrl}/multi-city?sessionId=${sessionIdRef.current}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
        onmessage: onMessage,
        onclose: () => stopStreaming(),
        onerror: (err) => {
          console.error('EventSource failed:', err);
          setMessages((prev) => [...prev, { sender: 'bot', text: 'An unexpected error occurred. Please check the console for details.' }]);
          stopStreaming();
        },
      });
    } else {
      const eventSource = new EventSource(
        `${baseUrl}/chat?message=${encodeURIComponent(
          message,
        )}&sessionId=${sessionIdRef.current}`,
      );
      eventSourceRef.current = eventSource;
      eventSource.addEventListener('content', (event) => onMessage({ event: 'content', data: event.data }));
      eventSource.addEventListener('thought', (event) => onMessage({ event: 'thought', data: event.data }));
      eventSource.addEventListener('tool_code', (event) => onMessage({ event: 'tool_code', data: event.data }));
      eventSource.addEventListener('tool_result', (event) => onMessage({ event: 'tool_result', data: event.data }));
      eventSource.addEventListener('end', () => stopStreaming());
      eventSource.addEventListener('error', (err) => {
        console.error('EventSource failed:', err);
        stopStreaming();
      });
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
