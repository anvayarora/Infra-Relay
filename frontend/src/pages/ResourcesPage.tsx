import { useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import {
  Cpu,
  Database,
  MapPin,
  Plus,
  Server,
  Shapes,
  Trash2,
} from 'lucide-react'
import { toast } from 'sonner'

import { api } from '../lib/api'
import type {
  Resource,
  ResourceType,
  ResourceTypeField,
} from '../lib/types'
import {
  getError,
  relative,
  spring,
} from '../lib/utils'
import {
  Badge,
  statusTone,
} from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { Card } from '../components/ui/Card'
import {
  Dialog,
  DialogContent,
} from '../components/ui/Dialog'
import {
  Input,
  Label,
  Textarea,
} from '../components/ui/Input'
import {
  Page,
  PageHeader,
} from '../components/ui/Page'
import { Select } from '../components/ui/Select'
import { Switch } from '../components/ui/Switch'

type ResourceForm = {
  name: string
  resource_type: string
  status: string
  location: string
  tags: string
  field_values: Record<string, any>
  bookable: boolean
  approval_required: boolean
  maximum_duration_hours: number
  minimum_notice_hours: number
  allow_extensions: boolean
  cleanup_required: boolean
}

type ResourceTypeForm = {
  name: string
  key: string
  description: string
  fields: ResourceTypeField[]
  booking_defaults: {
    bookable: boolean
    approval_required: boolean
    maximum_duration_hours: number
    minimum_notice_hours: number
    allow_extensions: boolean
    cleanup_required: boolean
  }
}

const emptyResourceForm = (): ResourceForm => ({
  name: '',
  resource_type: '',
  status: 'available',
  location: '',
  tags: '',
  field_values: {},
  bookable: true,
  approval_required: false,
  maximum_duration_hours: 8,
  minimum_notice_hours: 0,
  allow_extensions: true,
  cleanup_required: false,
})

const emptyTypeForm = (): ResourceTypeForm => ({
  name: '',
  key: '',
  description: '',
  fields: [],
  booking_defaults: {
    bookable: true,
    approval_required: false,
    maximum_duration_hours: 8,
    minimum_notice_hours: 0,
    allow_extensions: true,
    cleanup_required: false,
  },
})

const slug = (value: string) =>
  value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')

function applyTypeDefaults(
  form: ResourceForm,
  definition: ResourceType,
): ResourceForm {
  const defaults = definition.booking_defaults || {}

  const fieldValues = Object.fromEntries(
    (definition.fields || []).map((field) => [
      field.key,
      field.default ?? (field.type === 'boolean' ? false : ''),
    ]),
  )

  return {
    ...form,
    resource_type: definition.key,
    field_values: fieldValues,
    bookable: defaults.bookable ?? true,
    approval_required: defaults.approval_required ?? false,
    maximum_duration_hours: Number(
      defaults.maximum_duration_hours ?? 8,
    ),
    minimum_notice_hours: Number(
      defaults.minimum_notice_hours ?? 0,
    ),
    allow_extensions: defaults.allow_extensions ?? true,
    cleanup_required: defaults.cleanup_required ?? false,
  }
}

export function ResourcesPage() {
  const [items, setItems] = useState<Resource[]>([])
  const [resourceTypes, setResourceTypes] =
    useState<ResourceType[]>([])
  const [filter, setFilter] = useState('all')
  const [resourceOpen, setResourceOpen] = useState(false)
  const [typeOpen, setTypeOpen] = useState(false)

  const [resourceForm, setResourceForm] =
    useState<ResourceForm>(emptyResourceForm)

  const [typeForm, setTypeForm] =
    useState<ResourceTypeForm>(emptyTypeForm)

  const load = async () => {
    const [resourcesResponse, typesResponse] =
      await Promise.all([
        api.get('/resources'),
        api.get('/resource-types'),
      ])

    const nextTypes =
      typesResponse.data.items as ResourceType[]

    setItems(resourcesResponse.data.items)
    setResourceTypes(nextTypes)

    setResourceForm((current) => {
      if (current.resource_type || !nextTypes.length) {
        return current
      }

      return applyTypeDefaults(current, nextTypes[0])
    })
  }

  useEffect(() => {
    void load().catch((error) =>
      toast.error(getError(error)),
    )
  }, [])

  const selectedType = resourceTypes.find(
    (item) => item.key === resourceForm.resource_type,
  )

  const visible = useMemo(
    () =>
      filter === 'all'
        ? items
        : items.filter(
            (item) => item.resource_type === filter,
          ),
    [items, filter],
  )

  function openResourceModal() {
    if (!resourceTypes.length) {
      toast.info('Create a resource type first')
      setTypeOpen(true)
      return
    }

    setResourceForm(
      applyTypeDefaults(
        emptyResourceForm(),
        resourceTypes[0],
      ),
    )

    setResourceOpen(true)
  }

  function selectResourceType(resourceTypeKey: string) {
    const definition = resourceTypes.find(
      (item) => item.key === resourceTypeKey,
    )

    if (!definition) return

    setResourceForm((current) =>
      applyTypeDefaults(
        {
          ...current,
          resource_type: resourceTypeKey,
        },
        definition,
      ),
    )
  }

  async function createResource() {
    if (!resourceForm.name.trim()) {
      toast.error('Resource name is required')
      return
    }

    if (!selectedType) {
      toast.error('Select a resource type')
      return
    }

    const missingFields = selectedType.fields
      .filter((field) => field.required)
      .filter((field) => {
        const value =
          resourceForm.field_values[field.key]

        return (
          value === undefined ||
          value === null ||
          value === ''
        )
      })

    if (missingFields.length) {
      toast.error(
        `Complete: ${missingFields
          .map((field) => field.label)
          .join(', ')}`,
      )
      return
    }

    try {
      await api.post('/resources', {
        name: resourceForm.name.trim(),
        resource_type: resourceForm.resource_type,
        status: resourceForm.status,
        location: resourceForm.location.trim(),
        capabilities: resourceForm.field_values,
        booking_policy: {
          bookable: resourceForm.bookable,
          approval_required:
            resourceForm.approval_required,
          maximum_duration_hours: Number(
            resourceForm.maximum_duration_hours || 0,
          ),
          minimum_notice_hours: Number(
            resourceForm.minimum_notice_hours || 0,
          ),
          allow_extensions:
            resourceForm.allow_extensions,
          cleanup_required:
            resourceForm.cleanup_required,
        },
        maintenance: {},
        tags: resourceForm.tags
          .split(',')
          .map((tag) => tag.trim())
          .filter(Boolean),
      })

      toast.success('Resource registered')
      setResourceOpen(false)
      setResourceForm(emptyResourceForm())
      await load()
    } catch (error) {
      toast.error(getError(error))
    }
  }

  async function createType() {
    if (!typeForm.name.trim()) {
      toast.error('Type name is required')
      return
    }

    const invalidField = typeForm.fields.find(
      (field) =>
        !field.label.trim() || !field.key.trim(),
    )

    if (invalidField) {
      toast.error(
        'Every custom field needs a label and key',
      )
      return
    }

    try {
      const response = await api.post(
        '/resource-types',
        {
          name: typeForm.name.trim(),
          key: typeForm.key || slug(typeForm.name),
          description: typeForm.description.trim(),
          fields: typeForm.fields,
          booking_defaults:
            typeForm.booking_defaults,
        },
      )

      toast.success('Resource type created')
      setTypeOpen(false)
      setTypeForm(emptyTypeForm())
      await load()

      setResourceForm((current) =>
        applyTypeDefaults(current, response.data),
      )
    } catch (error) {
      toast.error(getError(error))
    }
  }

  function addField() {
    setTypeForm((current) => ({
      ...current,
      fields: [
        ...current.fields,
        {
          key: '',
          label: '',
          type: 'text',
          required: false,
          placeholder: '',
          default: '',
          options: [],
        },
      ],
    }))
  }

  function updateField(
    index: number,
    patch: Partial<ResourceTypeField>,
  ) {
    setTypeForm((current) => ({
      ...current,
      fields: current.fields.map(
        (field, position) =>
          position === index
            ? {
                ...field,
                ...patch,
              }
            : field,
      ),
    }))
  }

  function removeField(index: number) {
    setTypeForm((current) => ({
      ...current,
      fields: current.fields.filter(
        (_, position) => position !== index,
      ),
    }))
  }

  return (
    <Page>
      <PageHeader
        eyebrow="Inventory"
        title="Resources"
        description="Define reusable resource types, register infrastructure, and control how each resource can be reserved."
        actions={
          <div className="flex gap-2">
            <Button
              variant="secondary"
              onClick={() => setTypeOpen(true)}
            >
              <Shapes size={15} />
              Add type
            </Button>

            <Button onClick={openResourceModal}>
              <Plus size={15} />
              Add resource
            </Button>
          </div>
        }
      />

      <div className="mb-5 flex gap-2 overflow-x-auto pb-1">
        {[
          'all',
          ...resourceTypes.map((item) => item.key),
        ].map((value) => {
          const label =
            value === 'all'
              ? 'all'
              : resourceTypes.find(
                  (item) => item.key === value,
                )?.name || value

          return (
            <button
              key={value}
              type="button"
              onClick={() => setFilter(value)}
              className={
                filter === value
                  ? 'whitespace-nowrap rounded-full border border-zinc-950 bg-zinc-950 px-3 py-1.5 text-xs font-medium text-white dark:border-white dark:bg-white dark:text-zinc-950'
                  : 'whitespace-nowrap rounded-full border border-zinc-200 px-3 py-1.5 text-xs font-medium text-zinc-500 transition-colors hover:text-zinc-950 dark:border-zinc-800 dark:hover:text-white'
              }
            >
              {label}
            </button>
          )
        })}
      </div>

      {!resourceTypes.length ? (
        <Card className="mb-5 border-dashed p-8 text-center">
          <Shapes
            className="mx-auto text-zinc-400"
            size={22}
          />

          <h3 className="mt-4 text-sm font-semibold">
            Create your first resource type
          </h3>

          <p className="mx-auto mt-2 max-w-md text-xs leading-5 text-zinc-500">
            Define the required fields for servers,
            GPUs, virtual machines, storage, lab
            devices, or other infrastructure.
          </p>

          <Button
            className="mt-5"
            onClick={() => setTypeOpen(true)}
          >
            <Plus size={14} />
            Add type
          </Button>
        </Card>
      ) : null}

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {visible.map((item, index) => (
          <motion.div
            key={item.id}
            initial={{
              opacity: 0,
              y: 8,
            }}
            animate={{
              opacity: 1,
              y: 0,
            }}
            transition={{
              ...spring,
              delay: index * 0.035,
            }}
          >
            <Card className="h-full p-5">
              <div className="flex justify-between">
                <div className="rounded-lg border border-zinc-200 p-2 text-zinc-500 dark:border-zinc-800">
                  {item.capabilities?.gpu_model ? (
                    <Cpu size={17} />
                  ) : (
                    <Server size={17} />
                  )}
                </div>

                <Badge tone={statusTone(item.status)}>
                  {item.status}
                </Badge>
              </div>

              <h3 className="mt-5 text-sm font-semibold">
                {item.name}
              </h3>

              <p className="mt-1 text-[11px] text-zinc-500">
                {resourceTypes.find(
                  (type) =>
                    type.key === item.resource_type,
                )?.name ||
                  item.resource_type.replaceAll(
                    '_',
                    ' ',
                  )}
              </p>

              <div className="mt-5 grid grid-cols-2 gap-2 text-[10px]">
                <div className="rounded-md bg-zinc-50 p-2.5 dark:bg-zinc-900">
                  <MapPin
                    size={12}
                    className="mb-2"
                  />
                  {item.location || 'Unspecified'}
                </div>

                <div className="rounded-md bg-zinc-50 p-2.5 dark:bg-zinc-900">
                  <Database
                    size={12}
                    className="mb-2"
                  />
                  {item.booking_policy?.bookable
                    ? 'Reservable'
                    : 'Managed only'}
                </div>
              </div>

              <div className="mt-4 flex flex-wrap gap-1">
                {item.tags.map((tag) => (
                  <Badge key={tag}>{tag}</Badge>
                ))}
              </div>

              <p className="mt-4 border-t border-zinc-100 pt-3 text-[10px] text-zinc-500 dark:border-zinc-900">
                Updated {relative(item.updated_at)}
              </p>
            </Card>
          </motion.div>
        ))}
      </div>

      <Dialog
        open={resourceOpen}
        onOpenChange={setResourceOpen}
      >
        <DialogContent
          className="max-w-3xl"
          title="Add resource"
          description="Register infrastructure using the fields defined by its resource type."
        >
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <Label>Name</Label>
              <Input
                value={resourceForm.name}
                onChange={(event) =>
                  setResourceForm((current) => ({
                    ...current,
                    name: event.target.value,
                  }))
                }
              />
            </div>

            <div>
              <Label>Type</Label>
              <Select
                value={resourceForm.resource_type}
                onValueChange={selectResourceType}
                options={resourceTypes.map((item) => ({
                  value: item.key,
                  label: item.name,
                }))}
              />
            </div>

            <div>
              <Label>Status</Label>
              <Select
                value={resourceForm.status}
                onValueChange={(status) =>
                  setResourceForm((current) => ({
                    ...current,
                    status,
                  }))
                }
                options={[
                  'available',
                  'reserved',
                  'maintenance',
                  'offline',
                ].map((value) => ({
                  value,
                  label: value,
                }))}
              />
            </div>

            <div>
              <Label>Location</Label>
              <Input
                value={resourceForm.location}
                onChange={(event) =>
                  setResourceForm((current) => ({
                    ...current,
                    location: event.target.value,
                  }))
                }
              />
            </div>

            <div className="md:col-span-2">
              <Label>Tags</Label>
              <Input
                value={resourceForm.tags}
                onChange={(event) =>
                  setResourceForm((current) => ({
                    ...current,
                    tags: event.target.value,
                  }))
                }
                placeholder="gpu, training, shared"
              />
            </div>
          </div>

          {selectedType?.fields.length ? (
            <section className="mt-6">
              <div className="mb-3">
                <p className="text-sm font-semibold">
                  Type details
                </p>
                <p className="mt-1 text-xs text-zinc-500">
                  Required fields are defined by{' '}
                  {selectedType.name}.
                </p>
              </div>

              <div className="grid gap-4 md:grid-cols-2">
                {selectedType.fields.map((field) => (
                  <ResourceField
                    key={field.key}
                    field={field}
                    value={
                      resourceForm.field_values[
                        field.key
                      ]
                    }
                    onChange={(value) =>
                      setResourceForm((current) => ({
                        ...current,
                        field_values: {
                          ...current.field_values,
                          [field.key]: value,
                        },
                      }))
                    }
                  />
                ))}
              </div>
            </section>
          ) : null}

          <section className="mt-6">
            <div className="mb-3">
              <p className="text-sm font-semibold">
                Reservation rules
              </p>
              <p className="mt-1 text-xs text-zinc-500">
                Configure availability with switches and
                limits instead of JSON.
              </p>
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <Switch
                checked={resourceForm.bookable}
                onCheckedChange={(bookable) =>
                  setResourceForm((current) => ({
                    ...current,
                    bookable,
                  }))
                }
                label="Allow reservations"
                description="Users can reserve this resource for a time window."
              />

              <Switch
                checked={
                  resourceForm.approval_required
                }
                onCheckedChange={(
                  approval_required,
                ) =>
                  setResourceForm((current) => ({
                    ...current,
                    approval_required,
                  }))
                }
                label="Require approval"
                description="A reservation must be approved before confirmation."
              />

              <Switch
                checked={resourceForm.allow_extensions}
                onCheckedChange={(allow_extensions) =>
                  setResourceForm((current) => ({
                    ...current,
                    allow_extensions,
                  }))
                }
                label="Allow extensions"
                description="Active reservations can request more time."
              />

              <Switch
                checked={resourceForm.cleanup_required}
                onCheckedChange={(cleanup_required) =>
                  setResourceForm((current) => ({
                    ...current,
                    cleanup_required,
                  }))
                }
                label="Cleanup after use"
                description="Run cleanup after the reservation ends."
              />

              <div>
                <Label>
                  Maximum duration in hours
                </Label>
                <Input
                  type="number"
                  min="1"
                  value={
                    resourceForm.maximum_duration_hours
                  }
                  onChange={(event) =>
                    setResourceForm((current) => ({
                      ...current,
                      maximum_duration_hours: Number(
                        event.target.value,
                      ),
                    }))
                  }
                />
              </div>

              <div>
                <Label>
                  Minimum notice in hours
                </Label>
                <Input
                  type="number"
                  min="0"
                  value={
                    resourceForm.minimum_notice_hours
                  }
                  onChange={(event) =>
                    setResourceForm((current) => ({
                      ...current,
                      minimum_notice_hours: Number(
                        event.target.value,
                      ),
                    }))
                  }
                />
              </div>
            </div>
          </section>

          <Button
            className="mt-6 w-full"
            onClick={createResource}
          >
            Add resource
          </Button>
        </DialogContent>
      </Dialog>

      <Dialog
        open={typeOpen}
        onOpenChange={setTypeOpen}
      >
        <DialogContent
          className="max-w-4xl"
          title="Add resource type"
          description="Define the information InfraRelay should collect whenever this type of resource is added."
        >
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <Label>Type name</Label>
              <Input
                value={typeForm.name}
                onChange={(event) =>
                  setTypeForm((current) => ({
                    ...current,
                    name: event.target.value,
                    key:
                      current.key ||
                      slug(event.target.value),
                  }))
                }
                placeholder="GPU server"
              />
            </div>

            <div>
              <Label>Type key</Label>
              <Input
                value={typeForm.key}
                onChange={(event) =>
                  setTypeForm((current) => ({
                    ...current,
                    key: slug(event.target.value),
                  }))
                }
                placeholder="gpu_server"
              />
            </div>

            <div className="md:col-span-2">
              <Label>Description</Label>
              <Textarea
                value={typeForm.description}
                onChange={(event) =>
                  setTypeForm((current) => ({
                    ...current,
                    description: event.target.value,
                  }))
                }
                placeholder="Physical servers equipped with NVIDIA GPUs."
              />
            </div>
          </div>

          <section className="mt-6">
            <div className="mb-3 flex items-center justify-between gap-4">
              <div>
                <p className="text-sm font-semibold">
                  Required fields
                </p>
                <p className="mt-1 text-xs text-zinc-500">
                  These fields appear whenever this
                  resource type is added.
                </p>
              </div>

              <Button
                variant="secondary"
                size="sm"
                onClick={addField}
              >
                <Plus size={13} />
                Add field
              </Button>
            </div>

            <div className="space-y-3">
              {typeForm.fields.map(
                (field, index) => (
                  <div
                    key={`${field.key}-${index}`}
                    className="rounded-xl border border-zinc-200 p-4 dark:border-zinc-800"
                  >
                    <div className="grid gap-3 md:grid-cols-[1fr_1fr_150px_auto]">
                      <div>
                        <Label>Label</Label>
                        <Input
                          value={field.label}
                          onChange={(event) =>
                            updateField(index, {
                              label:
                                event.target.value,
                              key:
                                field.key ||
                                slug(
                                  event.target.value,
                                ),
                            })
                          }
                          placeholder="GPU model"
                        />
                      </div>

                      <div>
                        <Label>Key</Label>
                        <Input
                          value={field.key}
                          onChange={(event) =>
                            updateField(index, {
                              key: slug(
                                event.target.value,
                              ),
                            })
                          }
                          placeholder="gpu_model"
                        />
                      </div>

                      <div>
                        <Label>Field type</Label>
                        <Select
                          value={field.type}
                          onValueChange={(value) =>
                            updateField(index, {
                              type:
                                value as ResourceTypeField['type'],
                            })
                          }
                          options={[
                            'text',
                            'number',
                            'boolean',
                            'select',
                            'textarea',
                          ].map((value) => ({
                            value,
                            label: value,
                          }))}
                        />
                      </div>

                      <div className="flex items-end">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() =>
                            removeField(index)
                          }
                        >
                          <Trash2 size={15} />
                        </Button>
                      </div>
                    </div>

                    <div className="mt-3 grid gap-3 md:grid-cols-2">
                      <div>
                        <Label>
                          {field.type === 'select'
                            ? 'Options, comma separated'
                            : 'Placeholder'}
                        </Label>

                        <Input
                          value={
                            field.type === 'select'
                              ? (
                                  field.options || []
                                ).join(', ')
                              : field.placeholder || ''
                          }
                          onChange={(event) => {
                            if (
                              field.type === 'select'
                            ) {
                              updateField(index, {
                                options:
                                  event.target.value
                                    .split(',')
                                    .map((value) =>
                                      value.trim(),
                                    )
                                    .filter(Boolean),
                              })
                            } else {
                              updateField(index, {
                                placeholder:
                                  event.target.value,
                              })
                            }
                          }}
                        />
                      </div>

                      <Switch
                        checked={field.required}
                        onCheckedChange={(required) =>
                          updateField(index, {
                            required,
                          })
                        }
                        label="Required field"
                        description="The resource cannot be created without this value."
                      />
                    </div>
                  </div>
                ),
              )}

              {!typeForm.fields.length ? (
                <div className="rounded-xl border border-dashed border-zinc-300 p-6 text-center text-xs text-zinc-500 dark:border-zinc-700">
                  No custom fields yet. Add fields such
                  as hostname, IP address, GPU model,
                  serial number, operating system, or
                  capacity.
                </div>
              ) : null}
            </div>
          </section>

          <section className="mt-6">
            <div className="mb-3">
              <p className="text-sm font-semibold">
                Default reservation rules
              </p>
              <p className="mt-1 text-xs text-zinc-500">
                New resources of this type begin with
                these settings.
              </p>
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <Switch
                checked={
                  typeForm.booking_defaults.bookable
                }
                onCheckedChange={(bookable) =>
                  setTypeForm((current) => ({
                    ...current,
                    booking_defaults: {
                      ...current.booking_defaults,
                      bookable,
                    },
                  }))
                }
                label="Allow reservations by default"
              />

              <Switch
                checked={
                  typeForm.booking_defaults
                    .approval_required
                }
                onCheckedChange={(
                  approval_required,
                ) =>
                  setTypeForm((current) => ({
                    ...current,
                    booking_defaults: {
                      ...current.booking_defaults,
                      approval_required,
                    },
                  }))
                }
                label="Require approval by default"
              />

              <Switch
                checked={
                  typeForm.booking_defaults
                    .allow_extensions
                }
                onCheckedChange={(allow_extensions) =>
                  setTypeForm((current) => ({
                    ...current,
                    booking_defaults: {
                      ...current.booking_defaults,
                      allow_extensions,
                    },
                  }))
                }
                label="Allow extensions by default"
              />

              <Switch
                checked={
                  typeForm.booking_defaults
                    .cleanup_required
                }
                onCheckedChange={(cleanup_required) =>
                  setTypeForm((current) => ({
                    ...current,
                    booking_defaults: {
                      ...current.booking_defaults,
                      cleanup_required,
                    },
                  }))
                }
                label="Cleanup after use by default"
              />

              <div>
                <Label>
                  Default maximum duration
                </Label>
                <Input
                  type="number"
                  min="1"
                  value={
                    typeForm.booking_defaults
                      .maximum_duration_hours
                  }
                  onChange={(event) =>
                    setTypeForm((current) => ({
                      ...current,
                      booking_defaults: {
                        ...current.booking_defaults,
                        maximum_duration_hours:
                          Number(
                            event.target.value,
                          ),
                      },
                    }))
                  }
                />
              </div>

              <div>
                <Label>
                  Default minimum notice
                </Label>
                <Input
                  type="number"
                  min="0"
                  value={
                    typeForm.booking_defaults
                      .minimum_notice_hours
                  }
                  onChange={(event) =>
                    setTypeForm((current) => ({
                      ...current,
                      booking_defaults: {
                        ...current.booking_defaults,
                        minimum_notice_hours:
                          Number(
                            event.target.value,
                          ),
                      },
                    }))
                  }
                />
              </div>
            </div>
          </section>

          <Button
            className="mt-6 w-full"
            onClick={createType}
          >
            Create resource type
          </Button>
        </DialogContent>
      </Dialog>
    </Page>
  )
}

function ResourceField({
  field,
  value,
  onChange,
}: {
  field: ResourceTypeField
  value: any
  onChange: (value: any) => void
}) {
  if (field.type === 'boolean') {
    return (
      <div className="md:col-span-2">
        <Switch
          checked={Boolean(value)}
          onCheckedChange={onChange}
          label={field.label}
          description={
            field.required
              ? 'Required for this resource type'
              : undefined
          }
        />
      </div>
    )
  }

  if (field.type === 'select') {
    return (
      <div>
        <Label>
          {field.label}
          {field.required ? ' *' : ''}
        </Label>

        <Select
          value={String(value ?? '')}
          onValueChange={onChange}
          placeholder={field.placeholder || 'Select'}
          options={(field.options || []).map(
            (option) => ({
              value: option,
              label: option,
            }),
          )}
        />
      </div>
    )
  }

  if (field.type === 'textarea') {
    return (
      <div className="md:col-span-2">
        <Label>
          {field.label}
          {field.required ? ' *' : ''}
        </Label>

        <Textarea
          value={String(value ?? '')}
          onChange={(event) =>
            onChange(event.target.value)
          }
          placeholder={field.placeholder}
        />
      </div>
    )
  }

  return (
    <div>
      <Label>
        {field.label}
        {field.required ? ' *' : ''}
      </Label>

      <Input
        type={
          field.type === 'number'
            ? 'number'
            : 'text'
        }
        value={value ?? ''}
        onChange={(event) =>
          onChange(
            field.type === 'number'
              ? Number(event.target.value)
              : event.target.value,
          )
        }
        placeholder={field.placeholder}
        required={field.required}
      />
    </div>
  )
}
