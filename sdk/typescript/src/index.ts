export type SandboxManifest = {
  sandbox_id: string
  slug: string
  version: string
  interfaces: Array<{
    workflow_id: string
    workflow_name: string
    block_id: string
    direction: 'inbound' | 'outbound' | 'bidirectional'
    intent?: string
    schema: Record<string, unknown>
  }>
  event_stream: string
  transactions: string
}

export type SandboxEvent = {
  id: number
  execution_id: string
  type: string
  payload: Record<string, unknown>
  created_at: string
}

export class InfraRelaySandboxClient {
  constructor(
    private readonly options: {
      baseUrl: string
      sandboxId: string
      accessToken: string
    },
  ) {}

  private async request<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await fetch(`${this.options.baseUrl.replace(/\/$/, '')}${path}`, {
      ...init,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${this.options.accessToken}`,
        ...(init?.headers || {}),
      },
    })
    const payload = await response.json()
    if (!response.ok) throw new Error(payload.error || `InfraRelay request failed with ${response.status}`)
    return payload as T
  }

  manifest() {
    return this.request<SandboxManifest>(`/api/v1/sandboxes/${this.options.sandboxId}/manifest`)
  }

  developerKit() {
    return this.request<Record<string, unknown>>(`/api/v1/sandboxes/${this.options.sandboxId}/developer-kit`)
  }

  execute(workflowId: string, input: Record<string, unknown> = {}) {
    return this.request<{ id: string; status: string }>(`/api/v1/sandboxes/${this.options.sandboxId}/execute`, {
      method: 'POST',
      body: JSON.stringify({ workflow_id: workflowId, input }),
    })
  }

  respond(transactionId: string, action: string, values: Record<string, unknown> = {}) {
    return this.request<Record<string, unknown>>(`/api/v1/ui-transactions/${transactionId}/respond`, {
      method: 'POST',
      body: JSON.stringify({ action, values }),
    })
  }

  events(onEvent: (event: SandboxEvent) => void, onError?: (event: Event) => void) {
    const base = this.options.baseUrl.replace(/\/$/, '')
    const url = `${base}/api/v1/sandboxes/${this.options.sandboxId}/events?access_token=${encodeURIComponent(this.options.accessToken)}`
    const stream = new EventSource(url)
    const eventTypes = [
      'execution.started',
      'execution.waiting',
      'execution.completed',
      'execution.failed',
      'block.started',
      'block.completed',
      'ui.transaction.opened',
      'ui.payload.emitted',
    ]
    eventTypes.forEach(type => stream.addEventListener(type, event => onEvent(JSON.parse((event as MessageEvent).data))))
    if (onError) stream.onerror = onError
    return () => stream.close()
  }
}
