import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import React, { useCallback, useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import CheckIcon from '@mui/icons-material/Check';
import { Box, IconButton, Tooltip, useTheme } from '@mui/material';
export default function Markdown({ children }) {
    const theme = useTheme();
    const [Highlighter, setHighlighter] = useState(null);
    const [styles, setStyles] = useState({});
    const [copied, setCopied] = React.useState(null);
    const onCopy = useCallback(async (text, key) => {
        try {
            await navigator.clipboard.writeText(text);
            setCopied(key);
            setTimeout(() => setCopied((c) => (c === key ? null : c)), 1500);
        }
        catch {
            // ignore
        }
    }, []);
    useEffect(() => {
        let mounted = true;
        // Dynamically import the highlighter and styles to shrink initial bundle
        (async () => {
            try {
                const [{ Prism }, prismStyles] = await Promise.all([
                    import('react-syntax-highlighter'),
                    import('react-syntax-highlighter/dist/esm/styles/prism')
                ]);
                if (!mounted)
                    return;
                setHighlighter(() => Prism);
                setStyles({ oneDark: prismStyles.oneDark, oneLight: prismStyles.oneLight });
            }
            catch {
                // fallback silently
            }
        })();
        return () => { mounted = false; };
    }, []);
    return (_jsx(ReactMarkdown, { components: {
            code(nodeProps) {
                const { inline, className, children, ...props } = nodeProps;
                const match = /language-(\w+)/.exec(className || '');
                const code = String(children).replace(/\n$/, '');
                const key = `${match?.[1] || 'text'}-${code.slice(0, 16)}`;
                if (inline) {
                    return (_jsx("code", { className: className, ...props, children: children }));
                }
                // If highlighter not yet loaded, render a simple pre/code fallback
                if (!Highlighter || !styles) {
                    return (_jsxs(Box, { sx: { position: 'relative', borderRadius: 2, overflow: 'hidden', border: (t) => `1px solid ${t.palette.divider}` }, children: [_jsx(Box, { sx: { position: 'absolute', right: 6, top: 6, zIndex: 1 }, children: _jsx(Tooltip, { title: copied === key ? 'Copied' : 'Copy', children: _jsx(IconButton, { size: "small", onClick: () => onCopy(code, key), "aria-label": "Copy code block", children: copied === key ? _jsx(CheckIcon, { fontSize: "small" }) : _jsx(ContentCopyIcon, { fontSize: "small" }) }) }) }), _jsx("pre", { style: { margin: 0, padding: '14px 16px', fontSize: '0.875rem', overflow: 'auto' }, children: _jsx("code", { children: code }) })] }));
                }
                const style = theme.palette.mode === 'dark' ? styles.oneDark : styles.oneLight;
                const SyntaxHighlighter = Highlighter;
                return (_jsxs(Box, { sx: { position: 'relative', borderRadius: 2, overflow: 'hidden', border: (t) => `1px solid ${t.palette.divider}` }, children: [_jsx(Box, { sx: { position: 'absolute', right: 6, top: 6, zIndex: 1 }, children: _jsx(Tooltip, { title: copied === key ? 'Copied' : 'Copy', children: _jsx(IconButton, { size: "small", onClick: () => onCopy(code, key), "aria-label": "Copy code block", children: copied === key ? _jsx(CheckIcon, { fontSize: "small" }) : _jsx(ContentCopyIcon, { fontSize: "small" }) }) }) }), _jsx(SyntaxHighlighter, { style: style, language: match?.[1] || 'text', PreTag: "div", customStyle: { margin: 0, padding: '14px 16px', background: 'transparent' }, codeTagProps: { style: { fontSize: '0.875rem' } }, ...props, children: code })] }));
            },
        }, children: children }));
}
