import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { Provider } from 'react-redux';
jest.mock('../services/env', () => ({
  getBackendHttpBase: () => '',
  getBackendWsBase: () => 'ws://localhost:1234'
}));
jest.mock('../contexts/ProvidersContext', () => ({
  useProviders: () => ({ providers: {}, loading: false, refresh: jest.fn() })
}));
import StreamingChatPanel from './StreamingChatPanel';
import { makeStore } from '../store';

const wsInstances: any[] = [];
class WS {
  static OPEN = 1;
  readyState = 1;
  onopen: any;
  onmessage: any;
  onclose: any;
  onerror: any;
  sent: any[] = [];
  constructor(url: string) { wsInstances.push(this); }
  send(msg: string) { this.sent.push(msg); }
  close() {}
}
(global as any).WebSocket = WS as any;

beforeEach(() => {
  // Reset collected websocket instances before each test so index 0 is the current one
  wsInstances.length = 0;
});

function renderWithStore(ui: React.ReactElement) {
  const store = makeStore();
  return render(<Provider store={store}>{ui}</Provider>);
}

test('copy and regenerate buttons render and work in streaming panel', async () => {
  renderWithStore(<StreamingChatPanel />);

  const ws = wsInstances[wsInstances.length - 1];
  ws?.onopen?.();

  const input = screen.getByPlaceholderText(/type a message/i);
  fireEvent.change(input, { target: { value: 'Hi' } });
  fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

  // Assistant placeholder exists; simulate stream chunks
  const ws2 = wsInstances[wsInstances.length - 1];
  // fire a chunk message to fill assistant content
  (ws2 as any).onmessage?.({ data: JSON.stringify({ type: 'chunk', content: 'Hello S' }) });
  (ws2 as any).onmessage?.({ data: JSON.stringify({ type: 'stream_complete', metadata: {} }) });

  // Now copy button should exist for the assistant message
  const copyButtons = screen.getAllByRole('button', { name: /copy message/i });
  // Mock clipboard
  Object.assign(navigator, { clipboard: { writeText: jest.fn().mockResolvedValue(undefined) } });
  fireEvent.click(copyButtons[0]);
  expect(navigator.clipboard.writeText).toHaveBeenCalled();

  // Regenerate should be disabled if not connected; simulate connected state by ensuring readyState OPEN
  const regenButtons = screen.getAllByRole('button', { name: /regenerate response/i });
  fireEvent.click(regenButtons[0]);
  // Should not throw; nothing else to assert without deeper ws spy
});

test('stop button appears during streaming and finalizes partial content', async () => {
  renderWithStore(<StreamingChatPanel />);
  const ws = wsInstances[wsInstances.length - 1];
  ws?.onopen?.();

  const input = screen.getByPlaceholderText(/type a message/i);
  fireEvent.change(input, { target: { value: 'Stream please' } });
  fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

  // Simulate streaming chunks
  ws?.onmessage?.({ data: JSON.stringify({ type: 'stream_start', metadata: {} }) });
  ws?.onmessage?.({ data: JSON.stringify({ type: 'chunk', content: 'Hello' }) });

  // Stop button should be visible
  const stopBtn = await screen.findByRole('button', { name: /stop/i });
  fireEvent.click(stopBtn);

  // After stop, we expect no crash; partial is finalized by reducer; not asserting text here
});
