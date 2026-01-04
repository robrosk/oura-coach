import { Link } from 'react-router-dom';
import { clearTermsAcceptance } from '../lib/storage';

export function Footer() {
  const handleResetAcceptance = () => {
    clearTermsAcceptance();
    window.location.reload();
  };

  return (
    <footer className="bg-surface border-t border-border mt-auto">
      <div className="max-w-4xl mx-auto px-4 py-6">
        {/* Medical disclaimer - always visible */}
        <div className="text-center mb-4">
          <p className="text-text-muted text-sm font-medium">
            Not medical advice.
          </p>
        </div>

        {/* Links and info */}
        <div className="flex flex-col md:flex-row items-center justify-between gap-4 text-sm text-text-secondary">
          <div className="flex items-center gap-4">
            <Link to="/privacy" className="hover:text-accent transition-colors">
              Privacy Policy
            </Link>
            <span className="text-border">|</span>
            <Link to="/terms" className="hover:text-accent transition-colors">
              Terms of Service
            </Link>
          </div>

          <div className="text-text-muted">
            Contact:{' '}
            <a
              href="mailto:rob.roskowski@gmail.com"
              className="text-text-secondary hover:text-accent transition-colors"
            >
              rob.roskowski@gmail.com
            </a>
          </div>
        </div>

        {/* Copyright */}
        <div className="text-center mt-4 text-xs text-text-muted">
          &copy; {new Date().getFullYear()} Oura Coach (Beta)
        </div>

        {/* Dev reset button - very subtle */}
        <div className="text-center mt-4">
          <button
            onClick={handleResetAcceptance}
            className="text-xs text-text-muted hover:text-text-secondary transition-colors opacity-50 hover:opacity-100"
          >
            Reset acceptance (dev)
          </button>
        </div>
      </div>
    </footer>
  );
}
