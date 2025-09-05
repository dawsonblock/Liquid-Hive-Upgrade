import CheckIcon from '@mui/icons-material/Check';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import { Box, IconButton, Tooltip, useTheme } from '@mui/material';
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import ReactMarkdown from 'react-markdown';

type Props = { children: string };

export default function Markdown({ children }: Props) {
  const theme = useTheme();
  const [Highlighter, setHighlighter] = useState<any>(null);
  const [styles, setStyles] = useState<{ oneDark?: any; oneLight?: any }>({});
  const [copied, setCopied] = React.useState<string | null>(null);
  const onCopy = useCallback(async (text: string, key: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(key);
      setTimeout(() => setCopied(c => (c === key ? null : c)), 1500);
    } catch {
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
          import('react-syntax-highlighter/dist/esm/styles/prism'),
        ] as any);
        if (!mounted) return;
        setHighlighter(() => Prism);
        setStyles({ oneDark: prismStyles.oneDark, oneLight: prismStyles.oneLight });
      } catch {
        // fallback silently
      }
    })();
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <ReactMarkdown
      components={{
        code(nodeProps: any) {
          const { inline, className, children, ...props } = nodeProps as any;
          const match = /language-(\w+)/.exec(className || '');
          const code = String(children).replace(/\n$/, '');
          const key = `${match?.[1] || 'text'}-${code.slice(0, 16)}`;
          if (inline) {
            return (
              <code className={className} {...props}>
                {children}
              </code>
            );
          }
          // If highlighter not yet loaded, render a simple pre/code fallback
          if (!Highlighter || !styles) {
            return (
              <Box
                sx={{
                  position: 'relative',
                  borderRadius: 2,
                  overflow: 'hidden',
                  border: t => `1px solid ${t.palette.divider}`,
                }}
              >
                <Box sx={{ position: 'absolute', right: 6, top: 6, zIndex: 1 }}>
                  <Tooltip title={copied === key ? 'Copied' : 'Copy'}>
                    <IconButton
                      size='small'
                      onClick={() => onCopy(code, key)}
                      aria-label='Copy code block'
                    >
                      {copied === key ? (
                        <CheckIcon fontSize='small' />
                      ) : (
                        <ContentCopyIcon fontSize='small' />
                      )}
                    </IconButton>
                  </Tooltip>
                </Box>
                <pre
                  style={{
                    margin: 0,
                    padding: '14px 16px',
                    fontSize: '0.875rem',
                    overflow: 'auto',
                  }}
                >
                  <code>{code}</code>
                </pre>
              </Box>
            );
          }
          const style =
            theme.palette.mode === 'dark' ? (styles.oneDark as any) : (styles.oneLight as any);
          const SyntaxHighlighter: any = Highlighter;
          return (
            <Box
              sx={{
                position: 'relative',
                borderRadius: 2,
                overflow: 'hidden',
                border: t => `1px solid ${t.palette.divider}`,
              }}
            >
              <Box sx={{ position: 'absolute', right: 6, top: 6, zIndex: 1 }}>
                <Tooltip title={copied === key ? 'Copied' : 'Copy'}>
                  <IconButton
                    size='small'
                    onClick={() => onCopy(code, key)}
                    aria-label='Copy code block'
                  >
                    {copied === key ? (
                      <CheckIcon fontSize='small' />
                    ) : (
                      <ContentCopyIcon fontSize='small' />
                    )}
                  </IconButton>
                </Tooltip>
              </Box>
              <SyntaxHighlighter
                style={style}
                language={match?.[1] || 'text'}
                PreTag='div'
                customStyle={{ margin: 0, padding: '14px 16px', background: 'transparent' }}
                codeTagProps={{ style: { fontSize: '0.875rem' } }}
                {...props}
              >
                {code}
              </SyntaxHighlighter>
            </Box>
          );
        },
      }}
    >
      {children}
    </ReactMarkdown>
  );
}
