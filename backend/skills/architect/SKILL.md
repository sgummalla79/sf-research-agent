---
name: Technical Architect
id: architect
description: >
  Formal Architecture Recommendation Document via a 5-stage pipeline.
  Platform-agnostic: works with any enterprise or SaaS technology stack.
icon: "⚡"
version: 1
agent_labels:
  intake-document:    "Intake: Document"
  intake-image:       "Intake: Image Analysis"
  discovery:          "Discovery Agent"
  research-search:    "Research: Web Search"
  research-reasoning: "Research: Architecture"
  research-writer:    "Research: Writer"
  review:             "Review Agent"
  approval:           "Approver Gate"
---

## Pipeline

intake → discovery → research → review → approval

## Agent Flow

```mermaid
flowchart LR
    A([📥 Intake\nDocument / Image]) --> B([🔍 Discovery\nQ&A])

    B --> C([🔎 Web Search])
    B --> D([🧠 Architecture\nReasoning])

    C --> E([✍️ Writer])
    D --> E

    E --> F{📋 Review}

    F -->|pass| G{✅ Approval}
    F -->|fail ↺| C

    G -->|approve| H([🏁 Done])
    G -->|reject ↺| C

    style A fill:#3b5bdb,color:#fff,stroke:#3b5bdb
    style B fill:#7950f2,color:#fff,stroke:#7950f2
    style C fill:#1098ad,color:#fff,stroke:#1098ad
    style D fill:#1098ad,color:#fff,stroke:#1098ad
    style E fill:#0ca678,color:#fff,stroke:#0ca678
    style F fill:#f08c00,color:#fff,stroke:#f08c00
    style G fill:#2f9e44,color:#fff,stroke:#2f9e44
    style H fill:#495057,color:#fff,stroke:#495057
```

## Stage: intake

execution: intake
llm_slot: intake
agents:
  document: intake-document
  image: intake-image
interrupt: confirm_understanding

## Stage: discovery

execution: structured_interrupt
llm_slot: discovery
agent: discovery
output_schema: DiscoveryOutput
interrupt: question

## Stage: research

execution: fanout_merge
llm_slot: researcher_search
fanout:
  - llm_slot: researcher_search
    agent: research-search
  - llm_slot: researcher_reasoning
    agent: research-reasoning
merge:
  llm_slot: researcher_writer
  agent: research-writer

## Stage: review

execution: structured
llm_slot: reviewer
agent: review
output_schema: ReviewResult
context: [document_draft, document_version, discovery_questions]
on_pass: approval
on_fail: research

## Stage: approval

execution: structured
llm_slot: approver
agent: approval
output_schema: ApprovalResult
context: [project_brief, document_draft, document_version, discovery_questions, review_result, revision_count]
on_approve: complete
on_reject: research
max_revisions: 5
