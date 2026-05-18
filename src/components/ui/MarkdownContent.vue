<!--
  MarkdownContent — renders markdown text as styled prose.

  Owns both the parsing (marked) and the typography CSS.
  Use this anywhere LLM or user-authored markdown needs to be displayed.

  Props:
    text  String  — raw markdown text

  Usage:
    <MarkdownContent :text="msg.content" />
-->
<template>
  <div class="prose" v-html="rendered" />
</template>

<script setup>
import { computed } from 'vue'
import { marked }   from 'marked'

const props = defineProps({
  text: { type: String, default: '' },
})

const rendered = computed(() => {
  if (!props.text) return ''
  try { return marked.parse(props.text) } catch { return props.text }
})
</script>

<style scoped>
.prose {
  font-size: 18px;
  line-height: 1.7;
  color: inherit;
  word-break: break-word;
}

/* ── Headings ── */
.prose :deep(h1), .prose :deep(h2), .prose :deep(h3),
.prose :deep(h4), .prose :deep(h5), .prose :deep(h6) {
  font-weight: 700;
  line-height: 1.3;
  margin: 1em 0 0.4em;
  color: inherit;
}
.prose :deep(h1) { font-size: 1.5em; }
.prose :deep(h2) { font-size: 1.25em; }
.prose :deep(h3) { font-size: 1.1em; }

/* ── Paragraphs ── */
.prose :deep(p) {
  margin: 0 0 0.75em;
}
.prose :deep(p:last-child) { margin-bottom: 0; }

/* ── Lists ── */
.prose :deep(ul), .prose :deep(ol) {
  margin: 0.5em 0 0.75em 1.4em;
  padding: 0;
}
.prose :deep(ul)  { list-style-type: disc; }
.prose :deep(ol)  { list-style-type: decimal; }
.prose :deep(li)  { margin: 0.25em 0; }
.prose :deep(li > ul), .prose :deep(li > ol) { margin-top: 0.25em; margin-bottom: 0; }

/* ── Inline ── */
.prose :deep(strong) { font-weight: 700; }
.prose :deep(em)     { font-style: italic; }
.prose :deep(del)    { text-decoration: line-through; opacity: 0.7; }

.prose :deep(a) {
  color: var(--pri);
  text-decoration: underline;
  text-underline-offset: 2px;
}
.prose :deep(a:hover) { opacity: 0.8; }

/* ── Code ── */
.prose :deep(code) {
  font-family: 'Courier New', monospace;
  font-size: 0.88em;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 1px 5px;
}

.prose :deep(pre) {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px 14px;
  overflow-x: auto;
  margin: 0.75em 0;
}
.prose :deep(pre code) {
  background: none;
  border: none;
  padding: 0;
  font-size: 0.85em;
  line-height: 1.6;
}

/* ── Blockquote ── */
.prose :deep(blockquote) {
  border-left: 3px solid var(--border);
  margin: 0.75em 0;
  padding: 0.25em 0 0.25em 1em;
  color: var(--muted);
  font-style: italic;
}

/* ── Table ── */
.prose :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 0.75em 0;
  font-size: 0.9em;
}
.prose :deep(th), .prose :deep(td) {
  border: 1px solid var(--border);
  padding: 6px 12px;
  text-align: left;
}
.prose :deep(th) { background: var(--surface-2); font-weight: 600; }

/* ── Horizontal rule ── */
.prose :deep(hr) {
  border: none;
  border-top: 1px solid var(--border);
  margin: 1em 0;
}
</style>
