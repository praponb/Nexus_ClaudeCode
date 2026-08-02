<script setup lang="ts">
import AppIcon from '~/components/AppIcon.vue'

/**
 * Camera scanning panel (FR-017, layout §15.2).
 * - Camera permission is only requested when the user starts scanning.
 * - Uses the qr-scanner JS library when available, falling back to the
 *   native BarcodeDetector API; manual entry always remains available.
 */
const emit = defineEmits<{ (e: 'decoded', value: string): void }>()

interface QrScannerInstance {
  start: () => Promise<void>
  stop: () => void
  destroy: () => void
  hasFlash?: () => Promise<boolean>
  toggleFlash?: () => Promise<void>
  isFlashOn?: () => boolean
}

type QrScannerCtor = new (
  video: HTMLVideoElement,
  onDecode: (result: { data: string }) => void,
  options?: Record<string, unknown>,
) => QrScannerInstance

const videoRef = ref<HTMLVideoElement | null>(null)
const active = ref(false)
const starting = ref(false)
const errorMessage = ref('')
const flashOn = ref(false)
const flashAvailable = ref(false)

let scanner: QrScannerInstance | null = null
let detectorStream: MediaStream | null = null
let detectorTimer: ReturnType<typeof setInterval> | undefined

interface BarcodeDetectorLike {
  detect: (source: CanvasImageSource) => Promise<Array<{ rawValue: string }>>
}
declare global {
  interface Window {
    BarcodeDetector?: new (options?: { formats?: string[] }) => BarcodeDetectorLike
  }
}

async function start(): Promise<void> {
  if (active.value || starting.value) return
  starting.value = true
  errorMessage.value = ''
  try {
    await startQrScanner()
  } catch {
    try {
      await startBarcodeDetector()
    } catch (e) {
      errorMessage.value =
        e instanceof DOMException && e.name === 'NotAllowedError'
          ? 'Camera access was denied. Allow camera access in your browser, or use manual entry below.'
          : 'Camera scanning is not available on this device or browser. Use manual entry below.'
    }
  } finally {
    starting.value = false
  }
}

async function startQrScanner(): Promise<void> {
  const mod = (await import('qr-scanner')) as unknown as { default: QrScannerCtor }
  const QrScanner = mod.default
  if (!videoRef.value) throw new Error('video element unavailable')
  scanner = new QrScanner(
    videoRef.value,
    (result) => {
      if (result?.data) {
        emit('decoded', result.data)
      }
    },
    { returnDetailedScanResult: true, highlightScanRegion: true, highlightCodeOutline: true },
  )
  await scanner.start()
  active.value = true
  flashAvailable.value = scanner.hasFlash ? await scanner.hasFlash() : false
}

async function startBarcodeDetector(): Promise<void> {
  if (!window.BarcodeDetector || !videoRef.value) throw new Error('BarcodeDetector unavailable')
  const detector = new window.BarcodeDetector({ formats: ['qr_code'] })
  detectorStream = await navigator.mediaDevices.getUserMedia({
    video: { facingMode: 'environment' },
    audio: false,
  })
  videoRef.value.srcObject = detectorStream
  await videoRef.value.play()
  active.value = true
  detectorTimer = setInterval(() => {
    void (async () => {
      if (!videoRef.value) return
      try {
        const codes = await detector.detect(videoRef.value)
        const first = codes[0]
        if (first?.rawValue) emit('decoded', first.rawValue)
      } catch {
        // Single-frame detection errors are non-fatal; keep scanning.
      }
    })()
  }, 500)
}

function stop(): void {
  if (detectorTimer) clearInterval(detectorTimer)
  detectorTimer = undefined
  detectorStream?.getTracks().forEach((t) => t.stop())
  detectorStream = null
  scanner?.stop()
  scanner?.destroy()
  scanner = null
  if (videoRef.value) videoRef.value.srcObject = null
  active.value = false
  flashOn.value = false
  flashAvailable.value = false
}

async function toggleFlash(): Promise<void> {
  if (!scanner?.toggleFlash) return
  await scanner.toggleFlash()
  flashOn.value = !flashOn.value
}

onBeforeUnmount(stop)
</script>

<template>
  <div class="space-y-3">
    <div v-if="!active" class="rounded-xl border border-border bg-surface p-4">
      <p class="text-sm text-ink-secondary">
        Point the camera at an asset QR code. Camera access is only requested when you start
        scanning, and video never leaves your device. Manual entry below always works.
      </p>
      <button
        type="button"
        class="mt-3 inline-flex min-h-11 items-center gap-2 rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-on-accent hover:bg-accent-hover disabled:opacity-60"
        :disabled="starting"
        @click="start"
      >
        <AppIcon name="scan" size="sm" />
        {{ starting ? 'Starting camera…' : 'Start camera scanning' }}
      </button>
      <p v-if="errorMessage" class="mt-3 text-sm text-warning" role="alert">{{ errorMessage }}</p>
    </div>

    <div v-else class="overflow-hidden rounded-xl border border-border bg-black">
      <div class="relative">
        <video ref="videoRef" class="aspect-[4/3] w-full object-cover" muted playsinline aria-label="Camera view for QR scanning" />
        <div class="pointer-events-none absolute inset-0 flex items-center justify-center" aria-hidden="true">
          <div class="h-40 w-40 rounded-xl border-2 border-accent/80" />
        </div>
      </div>
      <div class="flex items-center justify-between gap-2 p-3">
        <p class="text-sm text-ink-secondary">Align the QR code inside the frame.</p>
        <div class="flex gap-2">
          <button
            v-if="flashAvailable"
            type="button"
            class="inline-flex min-h-11 items-center rounded-lg border border-border-strong bg-raised px-3 py-2 text-sm text-ink hover:bg-hover"
            :aria-pressed="flashOn"
            @click="toggleFlash"
          >
            {{ flashOn ? 'Torch off' : 'Torch on' }}
          </button>
          <button
            type="button"
            class="inline-flex min-h-11 items-center rounded-lg border border-border-strong bg-raised px-3 py-2 text-sm text-ink hover:bg-hover"
            @click="stop"
          >
            Stop camera
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
