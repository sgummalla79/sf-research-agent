<template>
  <div class="sfd-wrap">
    <svg
      :width="svgWidth"
      :height="svgHeight"
      :viewBox="`0 0 ${svgWidth} ${svgHeight}`"
      class="sfd-svg"
    >
      <!-- Connector lines -->
      <g v-for="c in connections" :key="c.key">
        <!-- Straight horizontal line -->
        <line v-if="c.type === 'line'"
          :x1="c.x1" :y1="c.y1" :x2="c.x2" :y2="c.y2"
          class="sfd-line"
        />
        <!-- Elbow: horizontal then vertical then horizontal -->
        <path v-else-if="c.type === 'elbow'"
          :d="elbowPath(c)"
          class="sfd-line" fill="none"
        />
        <!-- Feedback arc below -->
        <path v-else-if="c.type === 'feedback'"
          :d="feedbackPath(c)"
          class="sfd-feedback" fill="none"
        />
      </g>

      <!-- Junction dots -->
      <circle
        v-for="d in dots"
        :key="d.key"
        :cx="d.x" :cy="d.y" :r="DOT_R"
        class="sfd-dot"
      />

      <!-- Boxes -->
      <g v-for="n in nodes" :key="n.key" class="sfd-node-group">
        <rect
          :x="n.x - BOX_W / 2"
          :y="n.y - BOX_H / 2"
          :width="BOX_W"
          :height="BOX_H"
          :rx="BOX_R"
          class="sfd-box"
        />
        <text
          :x="n.x"
          :y="n.y - 6"
          text-anchor="middle"
          class="sfd-box-label"
        >{{ n.line1 }}</text>
        <text
          v-if="n.line2"
          :x="n.x"
          :y="n.y + 10"
          text-anchor="middle"
          class="sfd-box-label sfd-box-label-sub"
        >{{ n.line2 }}</text>
        <text
          v-else
          :x="n.x"
          :y="n.y + 7"
          text-anchor="middle"
          class="sfd-box-label"
        >{{ n.line1 }}</text>
      </g>

      <!-- Feedback labels -->
      <text
        v-for="c in connections.filter(x => x.type === 'feedback')"
        :key="`lbl-${c.key}`"
        :x="(c.x1 + c.x2) / 2"
        :y="svgHeight - 6"
        text-anchor="middle"
        class="sfd-fb-label"
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

// ── Layout constants ────────────────────────────────────────────────────────
const BOX_W      = 130
const BOX_H      = 48
const BOX_R      = 10
const DOT_R      = 5
const COL_W      = 170   // horizontal distance between box centres
const LANE_H     = 80    // vertical distance between lanes
const PAD_X      = 80
const PAD_TOP    = 60
const PAD_BOT    = 60
const FB_DIP     = 36

// ── Build layout from stage data ────────────────────────────────────────────
const layout = computed(() => {
  const nodes       = []
  const connections = []
  const dots        = []
  const MAIN        = 0   // main lane index (centre)
  let   col         = 0
  let   prevBoxRight = null
  let   prevY        = null

  const boxX   = (c) => PAD_X + c * COL_W
  const laneY  = (lane) => PAD_TOP + (lane + 1) * LANE_H
  const mainY  = () => laneY(MAIN)

  const addBox = (key, c, lane, line1, line2 = null) => {
    const x = boxX(c)
    const y = laneY(lane)
    nodes.push({ key, x, y, line1, line2 })
    return { x, y, left: x - BOX_W / 2, right: x + BOX_W / 2 }
  }

  const hLine = (x1, x2, y) =>
    connections.push({ key: `l${col}-${x1}`, type: 'line', x1, y1: y, x2, y2: y })

  for (const stage of props.stages) {
    if (stage.execution === 'fanout_merge') {
      // ── Fork dot ──────────────────────────────────────────────────────────
      const forkX = boxX(col)
      if (prevBoxRight !== null) hLine(prevBoxRight, forkX, mainY())
      dots.push({ key: `fork-dot-${col}`, x: forkX, y: mainY() })

      col++
      const branches = stage.fanout ?? []
      const bLanes   = branches.length > 1 ? [-1, 1] : [-1]
      const branchBoxes = []

      for (let i = 0; i < branches.length; i++) {
        const bLane = MAIN + bLanes[i]
        const lbl   = props.labels[branches[i].agent] || branches[i].agent
        const parts = lbl.split(':').map(s => s.trim())
        const box   = addBox(`branch-${i}`, col, bLane, parts[0], parts[1] ?? null)
        // elbow from fork dot to branch box
        connections.push({
          key: `fork-elbow-${i}`, type: 'elbow',
          fx: forkX, fy: mainY(), tx: box.left, ty: box.y,
        })
        branchBoxes.push(box)
      }
      col++

      // ── Merge dot ─────────────────────────────────────────────────────────
      const mergeX  = boxX(col)
      const mergeY  = mainY()
      dots.push({ key: `merge-dot-${col}`, x: mergeX, y: mergeY })
      for (const b of branchBoxes) {
        connections.push({
          key: `merge-elbow-${b.y}`, type: 'elbow',
          fx: b.x, fy: b.y, tx: mergeX, ty: mergeY, reverse: true,
        })
      }
      col++

      // ── Writer box ────────────────────────────────────────────────────────
      const mLabel = props.labels[stage.merge?.agent] || stage.merge?.agent || 'Writer'
      const mParts = mLabel.split(':').map(s => s.trim())
      const mBox   = addBox(`merge-box-${col}`, col, MAIN, mParts[0], mParts[1] ?? null)
      hLine(mergeX, mBox.left, mergeY)
      prevBoxRight = mBox.right
      prevY        = mBox.y
      col++

    } else {
      // ── Linear stage ──────────────────────────────────────────────────────
      const lbl   = props.labels[stage.agent] || stage.id
      const parts = lbl.split(':').map(s => s.trim())
      const box   = addBox(stage.id, col, MAIN, parts[0], parts[1] ?? null)

      if (prevBoxRight !== null) hLine(prevBoxRight, box.left, mainY())

      // Feedback arcs
      const writerBox = nodes.find(n => n.key.startsWith('merge-box'))
      if (stage.on_fail && writerBox) {
        connections.push({ key: `fail-${stage.id}`, type: 'feedback', x1: writerBox.x, x2: box.x, y: mainY(), label: '↺ fail' })
      }
      if (stage.on_reject && writerBox) {
        connections.push({ key: `rej-${stage.id}`, type: 'feedback', x1: writerBox.x, x2: box.x, y: mainY(), label: '↺ reject' })
      }

      prevBoxRight = box.right
      prevY        = box.y
      col++
    }
  }

  // ── Done box ──────────────────────────────────────────────────────────────
  const doneBox = addBox('done', col, MAIN, 'Done')
  if (prevBoxRight !== null) hLine(prevBoxRight, doneBox.left, mainY())

  // Total lanes needed
  const hasTopBranch = nodes.some(n => n.y < laneY(MAIN))
  const hasBotBranch = nodes.some(n => n.y > laneY(MAIN))
  const totalLanes   = 1 + (hasTopBranch ? 1 : 0) + (hasBotBranch ? 1 : 0)

  return { nodes, connections, dots, totalLanes, cols: col + 1 }
})

const nodes       = computed(() => layout.value.nodes)
const connections = computed(() => layout.value.connections)
const dots        = computed(() => layout.value.dots)
const totalLanes  = computed(() => layout.value.totalLanes)
const totalCols   = computed(() => layout.value.cols)

const svgWidth  = computed(() => PAD_X * 2 + totalCols.value * COL_W)
const svgHeight = computed(() => PAD_TOP + (totalLanes.value + 1) * LANE_H + PAD_BOT + FB_DIP)

// Elbow path: horizontal from fork/merge dot, then vertical, then horizontal to box
const elbowPath = (c) => {
  const midX = (c.fx + c.tx) / 2
  if (c.reverse) {
    // from box right edge to merge dot
    return `M ${c.fx} ${c.fy} H ${midX} V ${c.ty} H ${c.tx}`
  }
  // from fork dot to box left edge
  return `M ${c.fx} ${c.fy} H ${midX} V ${c.ty} H ${c.tx}`
}

const feedbackPath = (c) => {
  const bot = c.y + BOX_H / 2 + FB_DIP
  return `M ${c.x2} ${c.y + BOX_H / 2} V ${bot} Q ${(c.x1 + c.x2) / 2} ${bot + 16} ${c.x1} ${bot} V ${c.y + BOX_H / 2}`
}
</script>

<style scoped>
.sfd-wrap { overflow-x: auto; padding: 4px 0 8px; }
.sfd-svg  { display: block; }

/* Lines */
.sfd-line     { stroke: var(--bdr); stroke-width: 2; }
.sfd-feedback { stroke: var(--muted); stroke-width: 1.5; stroke-dasharray: 5 3; }

/* Junction dots */
.sfd-dot { fill: var(--bdr); }

/* Boxes */
.sfd-box {
  fill:   var(--surf);
  stroke: var(--bdr);
  stroke-width: 1.5;
  filter: drop-shadow(0 2px 6px rgba(0,0,0,.18));
}
.sfd-node-group:hover .sfd-box {
  stroke: var(--tx);
}

/* Labels */
.sfd-box-label     { font-size: 11px; font-weight: 600; fill: var(--tx); }
.sfd-box-label-sub { font-size: 10px; font-weight: 400; fill: var(--muted); }

/* Feedback labels */
.sfd-fb-label { font-size: 10px; fill: var(--muted); font-weight: 600; }
</style>
