import { useState } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { ScrollableTerms } from '../components/ScrollableTerms';
import { setTermsAcceptance } from '../lib/storage';
import { CURRENT_TERMS_VERSION } from '../lib/terms';
import termsContent from '../content/terms.md?raw';

export function Accept() {
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string })?.from || '/app';

  const [hasScrolledToBottom, setHasScrolledToBottom] = useState(false);
  const [termsChecked, setTermsChecked] = useState(false);
  const [privacyChecked, setPrivacyChecked] = useState(false);

  const canContinue = hasScrolledToBottom && termsChecked && privacyChecked;

  const handleAccept = () => {
    if (!canContinue) return;
    setTermsAcceptance(CURRENT_TERMS_VERSION);
    navigate(from, { replace: true });
  };

  return (
    <div className="max-w-2xl mx-auto px-4 py-8">
      <h1 className="text-2xl md:text-3xl font-bold mb-2 text-text-primary">
        Accept Terms to Continue
      </h1>
      <p className="text-text-secondary mb-6">
        Please read and accept our Terms of Service and acknowledge our Privacy
        Policy before using Oura Coach.
      </p>

      {/* Scrollable terms panel */}
      <div className="mb-6">
        <h2 className="text-lg font-semibold mb-2 text-text-primary">
          Terms of Service
        </h2>
        <ScrollableTerms
          content={termsContent}
          onScrolledToBottom={setHasScrolledToBottom}
        />
        {!hasScrolledToBottom && (
          <p className="text-sm text-warning mt-2">
            Please scroll to the bottom to continue
          </p>
        )}
      </div>

      {/* Checkboxes */}
      <div className="space-y-4 mb-8">
        <label className="flex items-start gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={termsChecked}
            onChange={(e) => setTermsChecked(e.target.checked)}
            disabled={!hasScrolledToBottom}
            className="mt-1 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          />
          <span
            className={`text-sm ${
              hasScrolledToBottom ? 'text-text-primary' : 'text-text-muted'
            }`}
          >
            I have read and accept the{' '}
            <Link to="/terms" target="_blank" className="text-accent underline">
              Terms of Service
            </Link>
          </span>
        </label>

        <label className="flex items-start gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={privacyChecked}
            onChange={(e) => setPrivacyChecked(e.target.checked)}
            className="mt-1 cursor-pointer"
          />
          <span className="text-sm text-text-primary">
            I have read the{' '}
            <Link
              to="/privacy"
              target="_blank"
              className="text-accent underline"
            >
              Privacy Policy
            </Link>
          </span>
        </label>
      </div>

      {/* Actions */}
      <div className="flex flex-col sm:flex-row gap-4">
        <button
          onClick={handleAccept}
          disabled={!canContinue}
          className={`flex-1 px-6 py-4 rounded-lg font-semibold transition-colors ${
            canContinue
              ? 'bg-accent hover:bg-accent-hover text-background cursor-pointer'
              : 'bg-surface-elevated text-text-muted cursor-not-allowed'
          }`}
        >
          Continue to App
        </button>
        <Link
          to="/"
          className="flex-1 px-6 py-4 rounded-lg font-semibold text-center border border-border text-text-secondary hover:text-text-primary hover:border-text-secondary transition-colors"
        >
          Go Back
        </Link>
      </div>

      {/* Status indicator */}
      <div className="mt-6 text-xs text-text-muted">
        <p>Requirements:</p>
        <ul className="mt-1 space-y-1">
          <li className={hasScrolledToBottom ? 'text-success' : ''}>
            {hasScrolledToBottom ? '✓' : '○'} Scroll to bottom of Terms
          </li>
          <li className={termsChecked ? 'text-success' : ''}>
            {termsChecked ? '✓' : '○'} Accept Terms of Service
          </li>
          <li className={privacyChecked ? 'text-success' : ''}>
            {privacyChecked ? '✓' : '○'} Acknowledge Privacy Policy
          </li>
        </ul>
      </div>
    </div>
  );
}
