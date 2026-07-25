export type Json =
  Record<string, any>;

export interface BlockDefinition {
  type: string;
  name: string;
  category: string;
  description: string;
  icon: string;
  accent: string;
  settings: Array<{
    key: string;
    label: string;
    type: string;
    default: any;
    options?: string[];
  }>;
  inputs: string[];
  outputs: string[];
}

export interface Workflow {
  id: string;
  name: string;
  description: string;
  status: string;
  current_version: number;
  graph?: {
    nodes: any[];
    edges: any[];
  };
  settings: Json;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface Sandbox {
  id: string;
  name: string;
  slug: string;
  description: string;
  status: string;
  environment: string;
  workflow_ids: string[];
  settings: Json;
  interface_manifest: Json;
  created_at: string;
  updated_at: string;
}

export interface ResourceTypeField {
  key: string;
  label: string;
  type:
    | 'text'
    | 'number'
    | 'boolean'
    | 'select'
    | 'textarea';
  required: boolean;
  placeholder?: string;
  default?: any;
  options?: string[];
}

export interface ResourceType {
  id: string;
  key: string;
  name: string;
  description: string;
  fields: ResourceTypeField[];
  booking_defaults: Json;
  active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Resource {
  id: string;
  name: string;
  resource_type: string;
  status: string;
  location: string;
  connection_ref?: string;
  capabilities: Json;
  booking_policy: Json;
  maintenance: Json;
  tags: string[];
  created_at: string;
  updated_at: string;
}

export interface Booking {
  id: string;
  resource_id: string;
  resource_name: string;
  requested_by: string;
  purpose: string;
  starts_at: string;
  ends_at: string;
  status: string;
  metadata: Json;
  created_at: string;
}

export interface Execution {
  id: string;
  workflow_id: string;
  workflow_name: string;
  sandbox_id?: string;
  sandbox_name?: string;
  status: string;
  trigger_type: string;
  input: Json;
  output: Json;
  error?: string;
  started_at?: string;
  completed_at?: string;
  created_at: string;
  updated_at: string;
  blocks?: any[];
  context?: Json;
}

export interface UITransaction {
  id: string;
  execution_id: string;
  sandbox_id?: string;
  workflow_id: string;
  block_id: string;
  direction: string;
  status: string;
  intent: string;
  schema: Json;
  payload: Json;
  response: Json;
  allowed_actions: string[];
  token?: string;
  expires_at?: string;
  responded_at?: string;
  responded_by?: string;
  created_at: string;
}
