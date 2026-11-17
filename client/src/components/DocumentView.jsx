import { useEffect, useId, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import hljs from 'highlight.js/lib/common';
import mermaid from 'mermaid';
import { useTheme } from '../context/ThemeContext';

function Mermaid({ chart }) {
  const { theme } = useTheme();
  const rawId = useId().replace(/:/g, '');
  const [svg, setSvg] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    mermaid.initialize({
      startOnLoad: false,
      securityLevel: 'strict',
      theme: theme === 'dark' ? 'dark' : 'neutral',
    });
    const renderId = `diagram-${rawId}-${Math.random().toString(36).slice(2, 8)}`;
    mermaid
      .render(renderId, chart)
      .then((result) => {
        if (!cancelled) setSvg(result.svg);
      })
      .catch((err) => {
        if (!cancelled) setError(err?.message || 'This diagram could not be drawn.');
      });
    return () => {
      cancelled = true;
    };
  }, [chart, theme, rawId]);

  if (error) return <pre className="codeblock">{chart}</pre>;
  if (!svg) return <p className="quiet">Drawing diagram…</p>;
  return <div className="diagram" dangerouslySetInnerHTML={{ __html: svg }} />;
}

function CodeBlock({ lang, value }) {
  let html = '';
  try {
    html = lang && hljs.getLanguage(lang) ? hljs.highlight(value, { language: lang }).value : hljs.highlightAuto(value).value;
  } catch {
    html = value.replace(/[&<>]/g, (char) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[char]));
  }
  return (
    <pre className="codeblock">
      {lang ? <span className="codelang">{lang}</span> : null}
      <code dangerouslySetInnerHTML={{ __html: html }} />
    </pre>
  );
}

export default function DocumentView({ markdown }) {
  const { theme } = useTheme();
  return (
    <article className="reader" data-theme={theme}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a({ href, children }) {
            const external = href && /^https?:/i.test(href);
            return (
              <a href={href} target={external ? '_blank' : undefined} rel={external ? 'noreferrer' : undefined}>
                {children}
              </a>
            );
          },
          table({ children }) {
            return (
              <div className="table-scroll">
                <table>{children}</table>
              </div>
            );
          },
          pre({ children }) {
            return <div className="pre-wrap">{children}</div>;
          },
          code({ className, children }) {
            const value = String(children).replace(/\n$/, '');
            const lang = /language-([\w-]+)/.exec(className || '')?.[1];
            if (!className && !value.includes('\n')) return <code className="inline-code">{children}</code>;
            if (lang === 'mermaid') return <Mermaid chart={value} />;
            return <CodeBlock lang={lang} value={value} />;
          },
        }}
      >
        {markdown || '_This document is empty._'}
      </ReactMarkdown>
    </article>
  );
}
