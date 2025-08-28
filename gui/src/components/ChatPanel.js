import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from 'react';
import { Box, Paper, TextField, IconButton, Stack, Typography, Button, Switch, FormControlLabel } from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import AttachFileIcon from '@mui/icons-material/AttachFile';
import ReactMarkdown from 'react-markdown';
import { postChat, postVision, fetchState } from '@services/api';
import { useDispatch, useSelector } from 'react-redux';
import { addChat } from '../store';
const ChatPanel = () => {
    const [input, setInput] = useState('');
    const [imageFile, setImageFile] = useState(null);
    const [groundingRequired, setGroundingRequired] = useState(false);
    const dispatch = useDispatch();
    const history = useSelector((s) => s.chatHistory);
    const sendText = async () => {
        if (!input.trim())
            return;
        dispatch(addChat({ role: 'user', content: input }));
        const res = await postChat(input);
        dispatch(addChat({ role: 'assistant', content: res.answer }));
        try {
            await fetchState();
        }
        catch { }
        setInput('');
    };
    const sendVision = async () => {
        if (!imageFile)
            return;
        const form = new FormData();
        form.append('file', imageFile);
        form.append('question', input || 'What is in this image?');
        const res = await postVision(form, groundingRequired);
        dispatch(addChat({ role: 'assistant', content: res.answer }));
        try {
            await fetchState();
        }
        catch { }
    };
    return (_jsxs(Stack, { spacing: 2, children: [_jsxs(Paper, { variant: "outlined", sx: { p: 2, height: 500, overflowY: 'auto', bgcolor: 'background.default' }, children: [history.length === 0 && (_jsx(Typography, { variant: "body2", color: "text.secondary", children: "Start the conversation with the Cognitive Core. Attach an image to ask visual questions." })), history.map((m, i) => (_jsxs(Box, { sx: { mb: 2 }, children: [_jsx(Typography, { variant: "caption", color: "text.secondary", children: m.role.toUpperCase() }), _jsx(ReactMarkdown, { children: m.content })] }, i)))] }), _jsxs(Stack, { direction: "row", spacing: 1, alignItems: "center", children: [_jsx(TextField, { fullWidth: true, size: "small", placeholder: "Type a message...", value: input, onChange: e => setInput(e.target.value), onKeyDown: (e) => { if (e.key === 'Enter' && !e.shiftKey) {
                            e.preventDefault();
                            sendText();
                        } } }), _jsxs(IconButton, { component: "label", color: imageFile ? 'secondary' : 'default', children: [_jsx(AttachFileIcon, {}), _jsx("input", { type: "file", hidden: true, accept: "image/*", onChange: e => setImageFile(e.target.files?.[0] || null) })] }), _jsx(IconButton, { color: "primary", onClick: sendText, children: _jsx(SendIcon, {}) }), _jsx(Button, { variant: "outlined", onClick: sendVision, disabled: !imageFile, children: "Send Image" })] }), _jsx(FormControlLabel, { control: _jsx(Switch, { checked: groundingRequired, onChange: e => setGroundingRequired(e.target.checked) }), label: "Grounding Required" })] }));
};
export default ChatPanel;
