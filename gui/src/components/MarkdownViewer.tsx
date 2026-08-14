import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface Props {
  content: string;
  className?: string;
}

/**
 * Renders markdown (incl. GFM tables/task lists) with the app's
 * dark design tokens applied via the .markdown-body stylesheet.
 */
export function MarkdownViewer({ content, className = '' }: Props) {
  return (
    <div className={`markdown-body ${className}`.trim()}>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
  );
}
