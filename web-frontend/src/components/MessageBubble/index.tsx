import ReactMarkdown from 'react-markdown';
import type { Message } from '../../types';
import FlightDeals from '../FlightDealsTable';
import ToolCall from '../ToolCall';

interface MessageBubbleProps {
  msg: Message;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ msg }) => {
  return (
    <div
      className={
        msg.sender === 'user' ? 'message user-message' : 'bot-message'
      }
    >
      {msg.text && <ReactMarkdown>{msg.text}</ReactMarkdown>}
      {msg.tools && <ToolCall tools={msg.tools} />}
      {msg.flightData && msg.flightData.length > 0 && (
        <div className="flight-deals-container">
          <FlightDeals deals={msg.flightData} />
        </div>
      )}
    </div>
  );
};

export default MessageBubble;
