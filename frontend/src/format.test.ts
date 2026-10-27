import { describe, it, expect } from 'vitest';
import { number, money, percent, dateLabel } from './format';
describe('measurement presentation', () => {
    it('distinguishes unavailable values from actual zero', () => { expect(number(null)).toBe('—'); expect(number(0)).toBe('0'); expect(money(null)).toBe('Not configured'); expect(money(0)).toBe('₹0'); });
    it('preserves comparison sign and precision', () => { expect(percent(3.11368)).toBe('+3.11%'); expect(percent(-5)).toBe('-5.00%'); expect(percent(null)).toBe('No baseline'); });
    it('preserves bill calendar dates regardless of client timezone', () => { expect(dateLabel('2026-08-31')).toBe('31 Aug 2026'); });
});
