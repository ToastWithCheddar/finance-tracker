/**
 * services/queryClient.ts — query-key factory shape + uniqueness (FE-PR-005).
 *
 * Hardens the centralized factory against drift between hooks. Each entity's
 * `all` is a tuple of namespace strings, and detail/list keys spread that
 * prefix so React Query's hierarchical invalidation works as intended.
 */
import { describe, expect, it } from 'vitest';

describe('queryKeys factory (FE-PR-005)', () => {
  it('exposes stable namespace tuples', async () => {
    const { queryKeys } = await import('@/services/queryClient');
    expect(queryKeys.transactions.all).toEqual(['transactions']);
    expect(queryKeys.budgets.all).toEqual(['budgets']);
    expect(queryKeys.accounts.all).toEqual(['accounts']);
    expect(queryKeys.categories.all).toEqual(['categories']);
    expect(queryKeys.goals.all).toEqual(['goals']);
    expect(queryKeys.auth.user).toEqual(['auth', 'user']);
  });

  it('list/detail keys spread the namespace prefix', async () => {
    const { queryKeys } = await import('@/services/queryClient');
    expect(queryKeys.transactions.lists()).toEqual(['transactions', 'list']);
    expect(queryKeys.transactions.detail('tx-1')).toEqual(['transactions', 'detail', 'tx-1']);

    expect(queryKeys.budgets.lists()).toEqual(['budgets', 'list']);
    expect(queryKeys.budgets.detail('b-1')).toEqual(['budgets', 'detail', 'b-1']);
    expect(queryKeys.budgets.summary()).toEqual(['budgets', 'summary']);
    expect(queryKeys.budgets.alerts()).toEqual(['budgets', 'alerts']);
    expect(queryKeys.budgets.progress('b-1')).toEqual(['budgets', 'progress', 'b-1']);
  });

  it('list keys differ when filters differ (deterministic input → key)', async () => {
    const { queryKeys } = await import('@/services/queryClient');
    const a = queryKeys.transactions.list({ page: 1, per_page: 10 });
    const b = queryKeys.transactions.list({ page: 2, per_page: 10 });
    expect(a).not.toEqual(b);
    // Same filter object should serialize identically structurally
    const c = queryKeys.transactions.list({ page: 1, per_page: 10 });
    expect(a).toEqual(c);
  });

  it('namespaces are mutually exclusive (uniqueness across factories)', async () => {
    const { queryKeys } = await import('@/services/queryClient');
    const namespaces = [
      queryKeys.transactions.all[0],
      queryKeys.budgets.all[0],
      queryKeys.accounts.all[0],
      queryKeys.categories.all[0],
      queryKeys.goals.all[0],
    ];
    expect(new Set(namespaces).size).toBe(namespaces.length);
  });
});
