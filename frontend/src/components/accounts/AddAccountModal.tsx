import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { PlaidLink } from '../plaid/PlaidLink';

interface AddAccountModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function AddAccountModal({ isOpen, onClose, onSuccess }: AddAccountModalProps) {
  const handlePlaidSuccess = () => {
    onSuccess();
    onClose();
  };

  const handlePlaidError = () => {
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Connect Bank Account"
      size="md"
    >
      <div className="space-y-4">
        <PlaidLink onSuccess={handlePlaidSuccess} onError={handlePlaidError} />
        <Button onClick={onClose} variant="ghost" size="sm" className="w-full">
          Cancel
        </Button>
      </div>
    </Modal>
  );
}