/**
 * End-to-end cents normalization for the CurrencyInput component.
 * Source: frontend/src/components/ui/CurrencyInput.tsx
 *
 *  - typing "12.34" emits 1234 cents
 *  - typing whole numbers emits cents (5 -> 500)
 *  - clearing the input emits 0
 */
import { describe, expect, it, vi } from 'vitest';
import userEvent from '@testing-library/user-event';
import { screen } from '@testing-library/react';
import { renderWithProviders } from '../../helpers/render';
import { CurrencyInput } from '@/components/ui/CurrencyInput';

describe('CurrencyInput', () => {
  it('emits cents for decimal input', async () => {
    const onChange = vi.fn();
    renderWithProviders(<CurrencyInput onChange={onChange} placeholder="amt" />);
    const input = screen.getByPlaceholderText('amt');

    await userEvent.type(input, '12.34');

    // Last call carries the fully-typed value.
    expect(onChange).toHaveBeenLastCalledWith(1234);
  });

  it('emits cents for whole-number input', async () => {
    const onChange = vi.fn();
    renderWithProviders(<CurrencyInput onChange={onChange} placeholder="amt" />);
    const input = screen.getByPlaceholderText('amt');

    await userEvent.type(input, '5');

    expect(onChange).toHaveBeenLastCalledWith(500);
  });

  it('emits 0 when the input is cleared', async () => {
    const onChange = vi.fn();
    renderWithProviders(
      <CurrencyInput value={1234} onChange={onChange} placeholder="amt" />,
    );
    const input = screen.getByPlaceholderText('amt') as HTMLInputElement;

    await userEvent.clear(input);

    expect(onChange).toHaveBeenLastCalledWith(0);
  });
});
