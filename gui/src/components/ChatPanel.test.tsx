import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import ChatPanel from './ChatPanel';
import { Provider } from 'react-redux';
import { store } from '../../store';

jest.mock('../services/api', () => ({
  postChat: async () => ({ answer: 'Hello World' }),
  fetchState: async () => ({ operator_intent: 'Answering' }),
}));

const renderWithProviders = (ui: React.ReactElement) => render(<Provider store={store}>{ui}</Provider>);

test('renders chat input and sends a message', async () => {
  renderWithProviders(<ChatPanel />);
  const input = screen.getByPlaceholderText(/type a message/i);
  fireEvent.change(input, { target: { value: 'Hello' } });
  fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });
  expect(await screen.findByText('Hello World')).toBeInTheDocument();
});