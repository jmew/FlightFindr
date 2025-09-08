import { FiX } from 'react-icons/fi';

interface FullScreenModalProps {
  children: React.ReactNode;
  onClose: () => void;
}

const FullScreenModal = ({ children, onClose }: FullScreenModalProps) => {
  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <button className="modal-close" onClick={onClose}>
          <FiX />
        </button>
        {children}
      </div>
    </div>
  );
};

export default FullScreenModal;