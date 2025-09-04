import { jsx as _jsx } from 'react/jsx-runtime';
import { render, fireEvent, screen } from '@testing-library/react';
import ChatPanel from './ChatPanel';
import { Provider } from 'react-redux';
import { makeStore } from '../store';
jest.mock('../services/api', () => ({
  postChat: jest.fn(async () => ({ answer: 'Hello World' })),
  fetchState: async () => ({ operator_intent: 'Answering' }),
  postVision: async () => ({ answer: 'This is an image.' }),
}));
const renderWithProviders = ui => {
  const store = makeStore();
  return render(_jsx(Provider, { store: store, children: ui }));
};
test('renders chat input and sends a message', async () => {
  renderWithProviders(_jsx(ChatPanel, {}));
  const input = screen.getByPlaceholderText(/type a message/i);
  fireEvent.change(input, { target: { value: 'Hello' } });
  fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });
  expect(await screen.findByText('Hello World')).toBeInTheDocument();
});
// New vision test
test('sends an image when a file is selected', async () => {
  renderWithProviders(_jsx(ChatPanel, {}));
  const file = new File(['(⌐□_□)'], 'chucknorris.png', { type: 'image/png' });
  const fileInput = screen.getByLabelText(/attach file/i);
  // Simulate file upload
  fireEvent.change(fileInput, { target: { files: [file] } });
  const sendImageButton = screen.getByRole('button', { name: /send image/i });
  fireEvent.click(sendImageButton);
  expect(await screen.findByText('This is an image.')).toBeInTheDocument();
});
test('copy and regenerate actions work for assistant messages', async () => {
  const { postChat } = require('../services/api');
  renderWithProviders(_jsx(ChatPanel, {}));
  const input = screen.getByPlaceholderText(/type a message/i);
  fireEvent.change(input, { target: { value: 'Hello' } });
  fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });
  expect(await screen.findByText('Hello World')).toBeInTheDocument();
  // Copy button should be present
  const copyBtns = screen.getAllByRole('button', { name: /copy message/i });
  const copyBtn = copyBtns[0];
  // Mock clipboard
  Object.assign(navigator, { clipboard: { writeText: jest.fn().mockResolvedValue(undefined) } });
  fireEvent.click(copyBtn);
  expect(navigator.clipboard.writeText).toHaveBeenCalledWith('Hello World');
  // Regenerate should call postChat again with previous prompt
  postChat.mockResolvedValueOnce({ answer: 'Hello Again' });
  const regenBtns = screen.getAllByRole('button', { name: /regenerate response/i });
  const regenBtn = regenBtns[0];
  fireEvent.click(regenBtn);
  expect(await screen.findByText('Hello Again')).toBeInTheDocument();
});
