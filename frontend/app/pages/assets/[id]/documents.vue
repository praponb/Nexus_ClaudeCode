<script setup lang="ts">
import { ApiError, isNotFoundError } from '~/utils/errors'
import { formatBytes, formatDateTime } from '~/utils/format'
import type { AttachmentMeta } from '~/types/workflow'
import AppIcon from '~/components/AppIcon.vue'
import AssetDetailTabs from '~/components/asset/AssetDetailTabs.vue'
import ConfirmDialog from '~/components/ConfirmDialog.vue'
import InlineAlert from '~/components/InlineAlert.vue'
import LoadingSkeleton from '~/components/LoadingSkeleton.vue'
import EmptyState from '~/components/EmptyState.vue'

// Attachments (FR-015, design D-04): validated upload, authorized download
// endpoint only, audited delete with a confirmation naming the file.
definePageMeta({ title: 'Asset documents' })

const MAX_FILE_BYTES = 10 * 1024 * 1024
const ALLOWED_TYPES = new Set([
  'image/png',
  'image/jpeg',
  'image/webp',
  'application/pdf',
  'text/plain',
  'text/csv',
])

const route = useRoute()
const uuid = computed(() => String(route.params.id))
const assets = useAssetsService()
const api = useApi()
const toast = useToast()
const { canManageAssets } = usePermissions()

const { data: asset, error: assetError } = await useAsyncData(
  `asset-docs-head-${uuid.value}`,
  () => assets.retrieve(uuid.value),
  { server: false, watch: [uuid] },
)

const attachments = ref<AttachmentMeta[]>([])
const loading = ref(true)
const loadError = ref<ApiError | null>(null)

async function loadAttachments(): Promise<void> {
  loading.value = true
  loadError.value = null
  try {
    attachments.value = await assets.attachments(uuid.value)
  } catch (e) {
    loadError.value = ApiError.fromUnknown(e)
  } finally {
    loading.value = false
  }
}

onMounted(loadAttachments)

useHead(() => ({ title: asset.value ? `Documents · ${asset.value.tag}` : 'Asset documents' }))

const notFound = computed(() => isNotFoundError(assetError.value))

/* Upload */
const purpose = ref('')
const uploadError = ref<ApiError | null>(null)
const uploading = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

async function onFileSelected(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  uploadError.value = null
  if (!file) return
  if (file.size > MAX_FILE_BYTES) {
    uploadError.value = new ApiError('The file is larger than the 10 MB limit.', { status: 413 })
    input.value = ''
    return
  }
  if (file.type && !ALLOWED_TYPES.has(file.type)) {
    uploadError.value = new ApiError(
      'This file type is not allowed. Use PNG, JPEG, WebP, PDF, plain text, or CSV.',
      { status: 415 },
    )
    input.value = ''
    return
  }
  uploading.value = true
  try {
    await assets.uploadAttachment(uuid.value, file, purpose.value.trim() || undefined)
    toast.success(`Uploaded ${file.name}`)
    purpose.value = ''
    await loadAttachments()
  } catch (e) {
    uploadError.value = ApiError.fromUnknown(e)
  } finally {
    uploading.value = false
    input.value = ''
  }
}

/* Download via the authorized endpoint (never a direct storage URL, D-04). */
const downloading = ref<string | null>(null)

async function download(item: AttachmentMeta): Promise<void> {
  downloading.value = item.uuid
  try {
    const path = item.download_url ?? `/assets/${uuid.value}/attachments/${item.uuid}/?download=1`
    const blob = await api.getBlob(path.startsWith('http') ? new URL(path).pathname : path)
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = item.filename
    link.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    toast.error('Download failed', ApiError.fromUnknown(e).message)
  } finally {
    downloading.value = null
  }
}

/* Delete with confirmation naming the file (layout §20.3). */
const deleteTarget = ref<AttachmentMeta | null>(null)
const deleteOpen = ref(false)
const deleting = ref(false)

function askDelete(item: AttachmentMeta): void {
  deleteTarget.value = item
  deleteOpen.value = true
}

async function confirmDelete(): Promise<void> {
  if (!deleteTarget.value || deleting.value) return
  deleting.value = true
  try {
    await assets.deleteAttachment(uuid.value, deleteTarget.value.uuid)
    toast.success(`Removed ${deleteTarget.value.filename}`)
    deleteOpen.value = false
    await loadAttachments()
  } catch (e) {
    toast.error('Could not remove the attachment', ApiError.fromUnknown(e).message)
  } finally {
    deleting.value = false
  }
}

const inputClass =
  'h-11 rounded-lg border border-border bg-input px-3 text-sm text-ink placeholder:text-faint focus:border-accent'
</script>

<template>
  <div>
    <nav aria-label="Breadcrumb" class="no-print mb-4 text-sm text-muted">
      <ol class="flex items-center gap-1">
        <li><NuxtLink to="/assets" class="rounded hover:text-ink">Assets</NuxtLink></li>
        <li aria-hidden="true">/</li>
        <li><NuxtLink :to="`/assets/${uuid}`" class="rounded hover:text-ink">{{ asset?.tag || 'Asset' }}</NuxtLink></li>
        <li aria-hidden="true">/</li>
        <li aria-current="page" class="text-ink-secondary">Documents</li>
      </ol>
    </nav>

    <div class="mb-6">
      <h1 class="text-2xl font-bold text-ink">Documents</h1>
      <p v-if="asset" class="mt-1 text-sm text-muted">
        <span class="font-mono text-accent">{{ asset.tag }}</span> · {{ asset.name }}
      </p>
    </div>

    <div class="mb-6">
      <AssetDetailTabs :asset-uuid="uuid" active="documents" />
    </div>

    <EmptyState
      v-if="notFound"
      icon="search"
      title="Asset not found"
      message="This asset does not exist or is outside your organizational scope."
      action-to="/assets"
      action-label="Back to asset register"
    />

    <template v-else>
      <section v-if="canManageAssets" aria-labelledby="upload-heading" class="mb-6 rounded-xl border border-border bg-surface p-4 sm:p-6">
        <h2 id="upload-heading" class="text-base font-semibold text-ink">Upload a document</h2>
        <p class="mt-1 text-sm text-muted">
          PNG, JPEG, WebP, PDF, plain text, or CSV — up to 10 MB. Files are scanned for type and size
          and are only downloadable through this application.
        </p>
        <InlineAlert v-if="uploadError" tone="error" class="mt-3" :message="uploadError.message" :correlation-id="uploadError.correlationId" />
        <div class="mt-4 flex flex-col gap-3 sm:flex-row sm:items-end">
          <div class="flex-1">
            <label for="attachment-purpose" class="mb-1 block text-xs font-medium text-muted">Purpose (optional)</label>
            <input id="attachment-purpose" v-model="purpose" type="text" placeholder="Receipt, warranty card, photo…" :class="[inputClass, 'w-full']" autocomplete="off" >
          </div>
          <div>
            <label for="attachment-file" class="mb-1 block text-xs font-medium text-muted">File</label>
            <input
              id="attachment-file"
              ref="fileInput"
              type="file"
              class="block w-full text-sm text-ink-secondary file:mr-3 file:min-h-11 file:rounded-lg file:border-0 file:bg-accent file:px-4 file:py-2 file:text-sm file:font-semibold file:text-on-accent hover:file:bg-accent-hover"
              :disabled="uploading"
              @change="onFileSelected"
            >
          </div>
        </div>
        <p v-if="uploading" class="mt-2 text-sm text-muted" role="status">Uploading…</p>
      </section>

      <LoadingSkeleton v-if="loading && !attachments.length" :lines="3" label="Loading documents…" />
      <InlineAlert
        v-else-if="loadError"
        tone="error"
        title="Documents could not be loaded"
        :message="loadError.message"
        :correlation-id="loadError.correlationId"
        retry-label="Retry"
        @retry="loadAttachments"
      />
      <EmptyState
        v-else-if="!attachments.length"
        icon="archive"
        title="No documents yet"
        message="Receipts, warranty cards, photos, and other files attached to this asset will appear here."
      />

      <ul v-else class="space-y-3">
        <li
          v-for="item in attachments"
          :key="item.uuid"
          class="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-border bg-surface p-4"
        >
          <div class="flex min-w-0 items-center gap-3">
            <AppIcon name="archive" class="shrink-0 text-muted" />
            <div class="min-w-0">
              <p class="truncate text-sm font-medium text-ink">{{ item.filename }}</p>
              <p class="text-xs text-muted">
                {{ formatBytes(item.size) }}
                <span v-if="item.purpose"> · {{ item.purpose }}</span>
                <span v-if="item.uploaded_at"> · Uploaded {{ formatDateTime(item.uploaded_at) }}</span>
                <span v-if="item.uploaded_by"> by {{ item.uploaded_by }}</span>
              </p>
            </div>
          </div>
          <div class="flex shrink-0 items-center gap-2">
            <button
              type="button"
              class="inline-flex min-h-11 items-center gap-2 rounded-lg border border-border-strong bg-raised px-3 py-2 text-sm font-medium text-ink hover:bg-hover"
              :disabled="downloading === item.uuid"
              @click="download(item)"
            >
              {{ downloading === item.uuid ? 'Downloading…' : 'Download' }}
            </button>
            <button
              v-if="canManageAssets"
              type="button"
              class="inline-flex min-h-11 items-center gap-2 rounded-lg border border-danger/50 bg-danger/10 px-3 py-2 text-sm font-medium text-danger hover:bg-danger/20"
              @click="askDelete(item)"
            >
              Remove
            </button>
          </div>
        </li>
      </ul>
    </template>

    <ConfirmDialog
      :open="deleteOpen"
      title="Remove attachment?"
      :message="`“${deleteTarget?.filename}” will be removed from asset ${asset?.tag ?? ''}. This is recorded in the audit history.`"
      confirm-label="Remove attachment"
      tone="danger"
      :busy="deleting"
      @confirm="confirmDelete"
      @cancel="deleteOpen = false"
    />
  </div>
</template>
