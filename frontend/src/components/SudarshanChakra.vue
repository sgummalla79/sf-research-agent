<template>
  <!--
    Sudarshana Chakra — Vishnu's disc of divine wisdom.
    12-pointed serrated rim · 12 spokes · two rings · central hub.
  -->
  <svg :width="size" :height="size" viewBox="0 0 100 100" fill="none"
    xmlns="http://www.w3.org/2000/svg">

    <!-- Outer 12-pointed star (tips r=47, notches r=37, every 15°) -->
    <polygon
      fill="none" :stroke="color" stroke-width="1.4" stroke-linejoin="round"
      points="
        50,3     60.4,13.2   73.2,9.7    77.5,23
        90.3,27.2  87,40.9   97,50    87,59.1
        90.3,72.8  77.5,77   73.2,90.3  60.4,86.8
        50,97    39.6,86.8  26.8,90.3  22.5,77
        9.7,72.8   13,59.1   3,50     13,40.9
        9.7,27.2   22.5,23   26.8,9.7   39.6,13.2
      "/>

    <!-- Outer ring -->
    <circle cx="50" cy="50" r="33" :stroke="color" stroke-width="1.3"/>

    <!-- 12 spokes — each is a vertical line rotated around center -->
    <!-- line from inner hub edge (r=9 → y=41) to outer ring (r=33 → y=17) -->
    <g :stroke="color" stroke-width="1.1">
      <line x1="50" y1="17" x2="50" y2="41"/>
      <line x1="50" y1="17" x2="50" y2="41" transform="rotate(30,50,50)"/>
      <line x1="50" y1="17" x2="50" y2="41" transform="rotate(60,50,50)"/>
      <line x1="50" y1="17" x2="50" y2="41" transform="rotate(90,50,50)"/>
      <line x1="50" y1="17" x2="50" y2="41" transform="rotate(120,50,50)"/>
      <line x1="50" y1="17" x2="50" y2="41" transform="rotate(150,50,50)"/>
      <line x1="50" y1="17" x2="50" y2="41" transform="rotate(180,50,50)"/>
      <line x1="50" y1="17" x2="50" y2="41" transform="rotate(210,50,50)"/>
      <line x1="50" y1="17" x2="50" y2="41" transform="rotate(240,50,50)"/>
      <line x1="50" y1="17" x2="50" y2="41" transform="rotate(270,50,50)"/>
      <line x1="50" y1="17" x2="50" y2="41" transform="rotate(300,50,50)"/>
      <line x1="50" y1="17" x2="50" y2="41" transform="rotate(330,50,50)"/>
    </g>

    <!-- Inner ring -->
    <circle cx="50" cy="50" r="16" :stroke="color" stroke-width="1.3"/>

    <!-- Central hub — partially filled -->
    <circle cx="50" cy="50" r="8" :stroke="color" stroke-width="1.4"
      :fill="color" fill-opacity="0.2"/>
    <circle cx="50" cy="50" r="3.5" :fill="color"/>

  </svg>
</template>

<script setup>
defineProps({
  size:  { type: [Number, String], default: 24 },
  color: { type: String, default: 'currentColor' },
})
</script>
