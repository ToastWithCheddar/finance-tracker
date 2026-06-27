/**
 * dashboardService — endpoint shape and date-range preset helper.
 */
import { describe, expect, it } from 'vitest';
import { seedTokens, clearTokens } from '../helpers/mockTokens';

describe('dashboardService', () => {
  it('getDashboardSummary hits /dashboard/summary', async () => {
    seedTokens();
    const { dashboardService } = await import('@/services/dashboardService');
    const summary = await dashboardService.getDashboardSummary();
    expect(summary.net_worth).toBe(250000);
    expect(summary.financial_health_grade).toBe('A');
    clearTokens();
  });

  it('getNetWorthTrend returns an array of {date, net_worth} points', async () => {
    seedTokens();
    const { dashboardService } = await import('@/services/dashboardService');
    const trend = await dashboardService.getNetWorthTrend('90d');
    expect(Array.isArray(trend)).toBe(true);
    expect(trend[0]).toMatchObject({ date: expect.any(String), net_worth: expect.any(Number) });
    clearTokens();
  });

  it('getDateRangePresets returns three keyed ranges with ISO YYYY-MM-DD strings', async () => {
    const { dashboardService } = await import('@/services/dashboardService');
    const presets = dashboardService.getDateRangePresets();
    expect(Object.keys(presets)).toEqual(
      expect.arrayContaining(['Last 7 days', 'Last 30 days', 'Last year']),
    );
    expect(presets['Last 7 days'].endDate).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(presets['Last 30 days'].startDate).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });
});
