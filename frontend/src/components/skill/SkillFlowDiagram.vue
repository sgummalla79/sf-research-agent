<template>
  <div class="sfd-wrap">
    <svg
      :width="svgWidth"
      :height="svgHeight"
      :viewBox="`0 0 ${svgWidth} ${svgHeight}`"
      class="sfd-svg"
    >
      <defs>
        <marker id="arrow-main" markerWidth="7" markerHeight="7" refX="5" refY="3" orient="auto">
          <path d="M0,0 L0,6 L7,3 z" fill="var(--bdr)" />
        </marker>
        <marker id="arrow-fail" markerWidth="7" markerHeight="7" refX="5" refY="3" orient="auto">
          <path d="M0,0 L0,6 L7,3 z" fill="#f08c00" />
        </marker>
        <marker id="arrow-reject" markerWidth="7" markerHeight="7" refX="5" refY="3" orient="auto">
          <path d="M0,0 L0,6 L7,3 z" fill="#e03131" />
        </marker>
      </defs>

      <!-- Lane tracks -->
      <line
        v-for="t in tracks"
        :key="`track-${t.lane}`"
        :x1="PADDING_X"
        :y1="laneY(t.lane)"
        :x2="svgWidth - PADDING_X"
        :y2="laneY(t.lane)"
        class="sfd-track"
      />

      <!-- Connections -->
      <g v-for="c in connections" :key="c.key">
        <!-- Feedback arcs below the diagram -->
        <path
          v-if="c.type === 'feedback'"
          :d="feedbackPath(c)"
          :class="`sfd-feedback sfd-feedback-${c.variant}`"
          fill="none"
          :marker-end="`url(#arrow-${c.variant})`"
        />
        <!-- Fork / merge diagonals -->
        <path
          v-else-if="c.type === 'fork' || c.type === 'merge'"
          :d="bezier(c.x1, laneY(c.l1), c.x2, laneY(c.l2))"
          :class="`sfd-branch sfd-branch-${c.color}`"
          fill="none"
          marker-end="url(#arrow-main)"
        />
        <!-- Straight horizontal -->
        <line
          v-else
          :x1="c.x1" :y1="laneY(c.lane)"
          :x2="c.x2" :y2="laneY(c.lane)"
          class="sfd-conn"
          marker-end="url(#arrow-main)"
        />
      </g>

      <!-- Nodes -->
      <g v-for="n in nodes" :key="n.key">
        <circle
          :cx="n.x" :cy="laneY(n.lane)" :r="NODE_R"
          :class="`sfd-node sfd-node-${n.color}`"
        />
        <text :x="n.x" :y="laneY(n.lane) + 1" text-anchor="middle" class="sfd-icon">
          {{ n.icon }}
        </text>
        <text :x="n.x" :y="laneY(n.lane) + NODE_R + 15" text-anchor="middle" class="sfd-label">
          {{ n.line1 }}
        </text>
        <text
          v-if="n.line2"
          :x="n.x" :y="laneY(n.lane) + NODE_R + 28"
          text-anchor="middle" class="sfd-label sfd-label-sub"
        >{{ n.line2 }}</text>
      </g>

      <!-- Feedback labels -->
      <text
        v-for="c in connections.filter(x => x.type === 'feedback')"
        :key="`lbl-${c.key}`"
        :x="(c.x1 + c.x2) / 2"
        :y="svgHeight - 8"
        text-anchor="middle"
        :class="`sfd-fb-label sfd-fb-label-${c.variant}`"
      >{{ c.label }}</text>
    </svg>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  stages: { type: Array,  default: () => [] },
  labels: { type: Object, default: () => ({}) },
})

const NODE_R      = 18
const LANE_H      = 76
const COL_W       = 130
const PADDING_X   = 56
const PADDING_TOP = 48
const PADDING_BOT = 72
const FB_DIP      = 42   // how far feedback arcs dip below bottom lane

const STAGE_COLOR = {
  intake:    'intake',
  discovery: 'discovery',
  fanout:    'branch',
  merge:     'merge',
  review:    'review',
  approval:  'approval',
  complete:  'done',
}
const STAGE_ICON = {
  intake:    '📥',
  discovery: '🔍',
  fanout:    '🔎',
  merge:     '✍️',
  review:    '📋',
  approval:  '✅',
  complete:  '🏁',
}

// ── Layout builder ──────────────────────────────────────────────────────────
const layout = computed(() => {
  const nodes       = []
  const connections = []
  const MAIN        = 1
  let   col         = 0
  let   prevX       = null

  const addNode = (key, lane, color, icon, label) => {
    const x      = PADDING_X + col * COL_W
    const parts  = label.split(':').map(s => s.trim())
    nodes.push({ key, lane, x, color, icon, line1: parts[0], line2: parts[1] ?? null })
    return x
  }

  const straight = (x1, x2, lane) =>
    connections.push({ key: `s${col}`, type: 'straight', x1: x1 + NODE_R, x2: x2 - NODE_R, lane })

  for (const stage of props.stages) {
    if (stage.execution === 'fanout_merge') {
      const forkX = PADDING_X + col * COL_W
      if (prevX !== null) straight(prevX, forkX, MAIN)
      col++

      const branches  = stage.fanout ?? []
      const bLanes    = branches.length > 1 ? [0, 2] : [0]
      const bXs       = []

      for (let i = 0; i < branches.length; i++) {
        const bLane = bLanes[i]
        const bX    = PADDING_X + col * COL_W
        const lbl   = props.labels[branches[i].agent] || branches[i].agent
        addNode(`branch-${i}`, bLane, 'branch', STAGE_ICON.fanout, lbl)
        connections.push({ key: `fork-${i}`, type: 'fork', x1: forkX, l1: MAIN, x2: bX - NODE_R, l2: bLane, color: 'branch' })
        bXs.push({ x: bX, lane: bLane })
      }
      col++

      const mergeX = PADDING_X + col * COL_W
      const mLabel = props.labels[stage.merge?.agent] || stage.merge?.agent || 'Writer'
      addNode(`merge-${col}`, MAIN, 'merge', STAGE_ICON.merge, mLabel)
      for (const b of bXs)
        connections.push({ key: `merge-${b.lane}`, type: 'merge', x1: b.x + NODE_R, l1: b.lane, x2: mergeX - NODE_R, l2: MAIN, color: 'merge' })

      prevX = mergeX
      col++
    } else {
      const x   = PADDING_X + col * COL_W
      const lbl = props.labels[stage.agent] || stage.id
      if (prevX !== null) straight(prevX, x, MAIN)
      addNode(stage.id, MAIN, STAGE_COLOR[stage.id] || 'done', STAGE_ICON[stage.id] || '⚙️', lbl)

      // Feedback arcs
      const researchNode = nodes.find(n => n.key === 'merge-' + (nodes.findIndex(n2 => n2.key.startsWith('merge')) + 1) || n.key.startsWith('merge'))
      if (stage.on_fail && researchNode) {
        connections.push({ key: `fail-${stage.id}`, type: 'feedback', x1: researchNode.x, x2: x, label: '↺ fail', variant: 'fail' })
      }
      if (stage.on_reject && researchNode) {
        connections.push({ key: `rej-${stage.id}`, type: 'feedback', x1: researchNode.x, x2: x, label: '↺ reject', variant: 'reject' })
      }

      prevX = x
      col++
    }
  }

  // Done node
  const doneX = PADDING_X + col * COL_W
  if (prevX !== null) straight(prevX, doneX, MAIN)
  nodes.push({ key: 'done', lane: MAIN, x: doneX, color: 'done', icon: STAGE_ICON.complete, line1: 'Done', line2: null })

  const totalLanes = nodes.some(n => n.lane === 0 || n.lane === 2) ? 3 : 1
  return { nodes, connections, totalLanes, cols: col + 1 }
})

const nodes       = computed(() => layout.value.nodes)
const connections = computed(() => layout.value.connections)
const totalLanes  = computed(() => layout.value.totalLanes)
const totalCols   = computed(() => layout.value.cols)

const svgWidth  = computed(() => PADDING_X * 2 + totalCols.value * COL_W)
const svgHeight = computed(() => PADDING_TOP + totalLanes.value * LANE_H + PADDING_BOT + FB_DIP)

const laneY  = (lane) => PADDING_TOP + lane * LANE_H
const bezier = (x1, y1, x2, y2) => {
  const cx = (x1 + x2) / 2
  return `M ${x1} ${y1} C ${cx} ${y1}, ${cx} ${y2}, ${x2} ${y2}`
}
const feedbackPath = (c) => {
  const bot = laneY(totalLanes.value - 1) + NODE_R + FB_DIP
  return `M ${c.x2} ${laneY(1) + NODE_R} L ${c.x2} ${bot} Q ${(c.x1 + c.x2) / 2} ${bot + 18} ${c.x1} ${bot} L ${c.x1} ${laneY(1) + NODE_R}`
}
</script>

<style scoped>
.sfd-wrap  { overflow-x: auto; padding: 4px 0 12px; }
.sfd-svg   { display: block; }

.sfd-track { stroke: var(--bdr); stroke-width: 1.5; }
.sfd-conn  { stroke: var(--bdr); stroke-width: 2; }

/* Bezier branches */
.sfd-branch        { stroke-width: 2; stroke-dasharray: 5 3; }
.sfd-branch-branch { stroke: #1098ad; }
.sfd-branch-merge  { stroke: #0ca678; }

/* Feedback arcs */
.sfd-feedback         { stroke-width: 1.5; stroke-dasharray: 5 3; }
.sfd-feedback-fail    { stroke: #f08c00; }
.sfd-feedback-reject  { stroke: #e03131; }

/* Nodes */
.sfd-node            { stroke-width: 0; }
.sfd-node-intake     { fill: #3b5bdb; }
.sfd-node-discovery  { fill: #7950f2; }
.sfd-node-branch     { fill: #1098ad; }
.sfd-node-merge      { fill: #0ca678; }
.sfd-node-review     { fill: #f08c00; }
.sfd-node-approval   { fill: #2f9e44; }
.sfd-node-done       { fill: #495057; }

.sfd-icon  { font-size: 11px; dominant-baseline: middle; pointer-events: none; }

/* Labels */
.sfd-label     { font-size: 10.5px; fill: var(--tx); font-weight: 600; }
.sfd-label-sub { font-size: 9.5px;  fill: var(--muted); font-weight: 400; }

/* Feedback labels */
.sfd-fb-label         { font-size: 10px; font-weight: 700; }
.sfd-fb-label-fail    { fill: #f08c00; }
.sfd-fb-label-reject  { fill: #e03131; }
</style>
