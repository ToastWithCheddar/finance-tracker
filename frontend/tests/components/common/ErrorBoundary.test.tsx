/**
 * ErrorBoundary — child throws → fallback renders; reset clears the error.
 *
 * The `fallback` prop short-circuits the default UI, which keeps this test
 * free of the Card/Button visual deps. We deliberately don't test the
 * default UI (would pull in styling assumptions from Tailwind).
 */
import { describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { ErrorBoundary } from '@/components/common/ErrorBoundary';

function Boom({ shouldThrow }: { shouldThrow: boolean }) {
  if (shouldThrow) throw new Error('kaboom');
  return <div>healthy child</div>;
}

describe('ErrorBoundary', () => {
  it('renders the fallback when a child throws', () => {
    // React logs the error to console.error — silence it for cleaner test output
    const errSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    render(
      <ErrorBoundary fallback={<div>fallback ui</div>}>
        <Boom shouldThrow />
      </ErrorBoundary>,
    );
    expect(screen.getByText('fallback ui')).toBeInTheDocument();
    errSpy.mockRestore();
  });

  it('invokes onError with the thrown error', () => {
    const errSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    const onError = vi.fn();
    render(
      <ErrorBoundary fallback={<div>fb</div>} onError={onError}>
        <Boom shouldThrow />
      </ErrorBoundary>,
    );
    expect(onError).toHaveBeenCalledTimes(1);
    expect(onError.mock.calls[0][0]).toBeInstanceOf(Error);
    expect((onError.mock.calls[0][0] as Error).message).toBe('kaboom');
    errSpy.mockRestore();
  });

  it('resets and re-renders children when the parent flips the throwing flag', async () => {
    const errSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    function Harness() {
      const [throws, setThrows] = useState(true);
      return (
        <div>
          <button onClick={() => setThrows(false)}>fix</button>
          <ErrorBoundary fallback={<div>fallback ui</div>} key={String(throws)}>
            <Boom shouldThrow={throws} />
          </ErrorBoundary>
        </div>
      );
    }

    render(<Harness />);
    expect(screen.getByText('fallback ui')).toBeInTheDocument();
    await userEvent.click(screen.getByText('fix'));
    // After flipping the flag, the boundary remounts (key change) and shows
    // the healthy child — this is the canonical "reset on prop change" idiom.
    expect(screen.getByText('healthy child')).toBeInTheDocument();
    errSpy.mockRestore();
  });
});
