import { Children, isValidElement, type ReactNode, type RefObject } from "react";
import Markdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import MermaidDiagram from "./MermaidDiagram";
import { slugifyHeading } from "../../lib/docs";

interface MarkdownPaneProps {
  content: string;
  containerRef?: RefObject<HTMLDivElement | null>;
}

function flattenText(node: ReactNode): string {
  return Children.toArray(node)
    .map((child) => {
      if (typeof child === "string" || typeof child === "number") {
        return String(child);
      }
      if (isValidElement<{ children?: ReactNode }>(child)) {
        return flattenText(child.props.children);
      }
      return "";
    })
    .join("");
}

function headingRenderer<T extends "h1" | "h2" | "h3" | "h4" | "h5" | "h6">(tag: T) {
  return function Heading({ children, ...props }: { children?: ReactNode }) {
    const id = slugifyHeading(flattenText(children));
    return tag === "h1" ? (
      <h1 id={id} data-doc-heading-id={id} style={{ fontSize: 28, fontWeight: 800, margin: "0 0 16px", scrollMarginTop: 12 }} {...props}>{children}</h1>
    ) : tag === "h2" ? (
      <h2 id={id} data-doc-heading-id={id} style={{ fontSize: 22, fontWeight: 800, margin: "28px 0 12px", scrollMarginTop: 12 }} {...props}>{children}</h2>
    ) : tag === "h3" ? (
      <h3 id={id} data-doc-heading-id={id} style={{ fontSize: 18, fontWeight: 700, margin: "22px 0 10px", scrollMarginTop: 12 }} {...props}>{children}</h3>
    ) : tag === "h4" ? (
      <h4 id={id} data-doc-heading-id={id} style={{ fontSize: 16, fontWeight: 700, margin: "18px 0 8px", scrollMarginTop: 12 }} {...props}>{children}</h4>
    ) : tag === "h5" ? (
      <h5 id={id} data-doc-heading-id={id} style={{ fontSize: 14, fontWeight: 700, margin: "16px 0 8px", scrollMarginTop: 12 }} {...props}>{children}</h5>
    ) : (
      <h6 id={id} data-doc-heading-id={id} style={{ fontSize: 13, fontWeight: 700, margin: "14px 0 8px", scrollMarginTop: 12 }} {...props}>{children}</h6>
    );
  };
}

const components: Components = {
  h1: headingRenderer("h1"),
  h2: headingRenderer("h2"),
  h3: headingRenderer("h3"),
  h4: headingRenderer("h4"),
  h5: headingRenderer("h5"),
  h6: headingRenderer("h6"),
  p({ children, ...props }) {
    return <p style={{ margin: "0 0 14px", lineHeight: 1.75, color: "#222" }} {...props}>{children}</p>;
  },
  ul({ children, ...props }) {
    return <ul style={{ paddingLeft: 22, margin: "0 0 14px", lineHeight: 1.7 }} {...props}>{children}</ul>;
  },
  ol({ children, ...props }) {
    return <ol style={{ paddingLeft: 22, margin: "0 0 14px", lineHeight: 1.7 }} {...props}>{children}</ol>;
  },
  li({ children, ...props }) {
    return <li style={{ marginBottom: 6 }} {...props}>{children}</li>;
  },
  blockquote({ children, ...props }) {
    return (
      <blockquote
        style={{ borderLeft: "4px solid #1A1A1A", margin: "0 0 16px", padding: "8px 0 8px 14px", background: "#F5F1E3" }}
        {...props}
      >
        {children}
      </blockquote>
    );
  },
  pre({ children, ...props }) {
    return (
      <pre
        style={{ background: "#1E2216", color: "#7DFF6B", padding: 16, overflowX: "auto", margin: "0 0 16px", border: "2px solid #1A1A1A" }}
        {...props}
      >
        {children}
      </pre>
    );
  },
  code({ children, className, node, ...props }) {
    const text = String(children).replace(/\n$/, "");
    const language = /language-([\w-]+)/.exec(className || "")?.[1]?.toLowerCase();
    const isBlockCode = Boolean(className) || text.includes("\n");

    if (language === "mermaid") {
      return <MermaidDiagram chart={text} />;
    }

    return (
      <code
        className={className}
        style={isBlockCode
          ? {
              fontFamily: "IBM Plex Mono, monospace",
              fontSize: "0.95em",
              background: "transparent",
              padding: 0,
              color: "inherit",
              whiteSpace: "pre",
            }
          : {
              fontFamily: "IBM Plex Mono, monospace",
              fontSize: "0.95em",
              background: "#F2ECDD",
              padding: "0.12em 0.3em",
            }}
        {...props}
      >
        {children}
      </code>
    );
  },
  table({ children, ...props }) {
    return (
      <div style={{ overflowX: "auto", marginBottom: 16 }}>
        <table style={{ width: "100%", borderCollapse: "collapse", border: "2px solid #1A1A1A" }} {...props}>
          {children}
        </table>
      </div>
    );
  },
  th({ children, ...props }) {
    return <th style={{ textAlign: "left", padding: "10px 12px", border: "1px solid #1A1A1A", background: "#F5F1E3" }} {...props}>{children}</th>;
  },
  td({ children, ...props }) {
    return <td style={{ padding: "10px 12px", border: "1px solid #1A1A1A", verticalAlign: "top" }} {...props}>{children}</td>;
  },
  a({ children, href, ...props }) {
    return <a href={href} target="_blank" rel="noreferrer" style={{ color: "#7B4DFF", fontWeight: 700 }} {...props}>{children}</a>;
  },
};

export default function MarkdownPane({ content, containerRef }: MarkdownPaneProps) {
  return (
    <div ref={containerRef} className="card" style={{ height: "100%", overflowY: "auto", padding: 24 }}>
      <Markdown remarkPlugins={[remarkGfm]} components={components}>
        {content}
      </Markdown>
    </div>
  );
}
