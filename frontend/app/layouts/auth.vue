<template>
  <div class="flex min-h-dvh flex-col items-center justify-center bg-canvas px-4 py-8">
    <div class="w-full max-w-md">
      <div class="mb-6 flex items-center justify-center gap-2">
        <span class="flex h-10 w-10 items-center justify-center rounded-xl bg-accent text-on-accent">
          <AppIcon name="cube" />
        </span>
        <span class="text-lg font-semibold text-ink">Asset Inventory</span>
      </div>
      <slot />
    </div>
  </div>
</template>
