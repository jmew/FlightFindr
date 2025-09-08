import styles from './SuggestionBubbles.module.css';

interface SuggestionBubblesProps {
  suggestions: string[];
  onSuggestionClick: (suggestion: string) => void;
}

const SuggestionBubbles = ({
  suggestions,
  onSuggestionClick,
}: SuggestionBubblesProps) => {
  return (
    <div className={styles.suggestionBubblesContainer}>
      {suggestions.map((suggestion, index) => (
        <button
          key={index}
          className={styles.suggestionBubble}
          onClick={() => onSuggestionClick(suggestion)}
        >
          {suggestion}
        </button>
      ))}
    </div>
  );
};

export default SuggestionBubbles;
