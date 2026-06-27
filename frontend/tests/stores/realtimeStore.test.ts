/**
 * realtimeStore — sliding-window cap on transactionUpdates (FE-PERF-006).
 *
 * The store appends every transaction WS event to `transactionUpdates`. Without
 * a cap this would grow unbounded over a long session. The implementation
 * uses `.slice(-50)` to keep at most the last 50 entries — push 60 and assert
 * length stays at 50.
 */
import { beforeEach, describe, expect, it } from 'vitest';

describe('realtimeStore.transactionUpdates (FE-PERF-006)', () => {
  beforeEach(async () => {
    const { useRealtimeStore } = await import('@/stores/realtimeStore');
    useRealtimeStore.setState({ transactionUpdates: [] });
  });

  it('caps transactionUpdates at 50 entries (sliding window)', async () => {
    const { useRealtimeStore } = await import('@/stores/realtimeStore');
    const { addTransactionUpdate } = useRealtimeStore.getState();

    for (let i = 0; i < 60; i += 1) {
      addTransactionUpdate({ type: 'created', transactionId: `tx-${i}` });
    }

    const updates = useRealtimeStore.getState().transactionUpdates;
    expect(updates).toHaveLength(50);
    // Sliding window keeps the *latest* 50 — first kept must be tx-10.
    expect(updates[0].transactionId).toBe('tx-10');
    expect(updates[updates.length - 1].transactionId).toBe('tx-59');
  });

  it('updateConnectionStatus flips isConnected and tracks attempts', async () => {
    const { useRealtimeStore } = await import('@/stores/realtimeStore');
    useRealtimeStore.getState().updateConnectionStatus('connected', 0);
    expect(useRealtimeStore.getState().isConnected).toBe(true);
    useRealtimeStore.getState().updateConnectionStatus('connecting', 3);
    expect(useRealtimeStore.getState().isConnected).toBe(false);
    expect(useRealtimeStore.getState().connectionStatus.reconnectAttempts).toBe(3);
  });
});
