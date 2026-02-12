# Session 4: POE App Development — Phase 6

**Date:** Feb 15, 2026
**Status:** Ready to begin
**Prerequisites:** Phase 1-5 complete ✅ (Bridge + ESP32 fully operational)

## Current Status

**Completed:**
- ✅ Phase 1 (Foundation): Bridge server with Claude streaming + 7 tools working
- ✅ Phase 2 (Audio Pipeline): Full speech-to-speech via WebSocket operational
- ✅ Phase 3 (ESP32 Integration): End-to-end hardware working
- ✅ Phase 4 (Polish & Demo): Tests passing, demo data seeded, demo video recorded
- ✅ Phase 5 (Submission): README polished, GitHub prepared, submitted to hackathon
- ✅ Custom Ultra-Light Framework: 23+ files, 1956+ lines, 26+ tests passing

**POE App Context:**
- **What:** Proof of Execution app for running code experiments on the codebase
- **Purpose:** Users create experiments with shell commands, execute them, capture proof (logs, exit codes, timing)
- **Workflow:** Create experiment → Execute → View proof → Promote to codebase (if passed)
- **Tech Stack:** Next.js 15 + App Router + React 19 Server Components + TypeScript + Tailwind CSS
- **Location:** `/Users/apple/Documents/aegis1/.worktrees/poe/` (feature/poe branch)
- **Plan Reference:** `/Users/apple/.claude/plans/warm-scribbling-tide.md`

---

## Session Objectives

1. **Scaffold Next.js 15 project** in POE worktree with TypeScript, Tailwind, App Router
2. **Build core experiment system** (types, storage, executor, validation)
3. **Create UI components** (experiment cards, forms, logs, proof artifacts)
4. **Build pages** (dashboard, create form, detail view)
5. **Verify end-to-end** (create → execute → view proof → delete flows)

---

## Task Checklist

### Task 1: Set Up POE Worktree & Scaffold Next.js

**Prerequisites check:**
```bash
# Verify POE worktree exists
ls -la /Users/apple/Documents/aegis1/.worktrees/poe/

# Verify feature/poe branch
cd /Users/apple/Documents/aegis1/.worktrees/poe/
git branch --show-current  # Should show: feature/poe
```

**If worktree doesn't exist, create it:**
```bash
cd /Users/apple/Documents/aegis1
git worktree add .worktrees/poe -b feature/poe
cd .worktrees/poe
```

**Scaffold Next.js project:**
```bash
cd /Users/apple/Documents/aegis1/.worktrees/poe/

# Run create-next-app
npx create-next-app@latest . --typescript --tailwind --eslint --app --src-dir --import-alias "@/*"

# Expected prompts:
# ✔ Would you like to use TypeScript? … Yes
# ✔ Would you like to use ESLint? … Yes
# ✔ Would you like to use Tailwind CSS? … Yes
# ✔ Would you like to use `src/` directory? … Yes
# ✔ Would you like to use App Router? … Yes
# ✔ Would you like to customize the default import alias (@/*)? … No
```

**Install additional dependencies:**
```bash
npm install zod date-fns
npm install -D @types/node
```

**Update package.json scripts:**
```json
{
  "scripts": {
    "dev": "next dev -p 3001",
    "build": "next build",
    "start": "next start -p 3001",
    "lint": "next lint",
    "type-check": "tsc --noEmit"
  }
}
```

**Create data directory:**
```bash
mkdir -p data
echo '{"experiments":[]}' > data/experiments.json
```

**Verify setup:**
```bash
npm run dev
# Should start on http://localhost:3001
# Visit in browser to confirm Next.js welcome page
```

---

### Task 2: Create Core Types & Utilities

**File:** `src/types/experiment.ts`

```typescript
export type ExperimentStatus = 'draft' | 'running' | 'passed' | 'failed'

export interface Command {
  id: string
  command: string
  description: string
}

export interface ExecutionLog {
  commandId: string
  command: string
  stdout: string
  stderr: string
  exitCode: number
  duration: number
  timestamp: string
}

export interface Experiment {
  id: string
  name: string
  description: string
  commands: Command[]
  status: ExperimentStatus
  executionLogs: ExecutionLog[]
  createdAt: string
  updatedAt: string
  lastExecutedAt?: string
  totalDuration?: number
}
```

**File:** `src/shared/utils/formatting.ts`

```typescript
export function formatDate(date: string): string {
  return new Date(date).toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(2)}s`
  return `${Math.floor(ms / 60000)}m ${((ms % 60000) / 1000).toFixed(0)}s`
}

export function getStatusColor(status: ExperimentStatus): string {
  const colors = {
    draft: 'bg-gray-100 text-gray-800',
    running: 'bg-blue-100 text-blue-800',
    passed: 'bg-green-100 text-green-800',
    failed: 'bg-red-100 text-red-800',
  }
  return colors[status]
}
```

**File:** `src/shared/utils/constants.ts`

```typescript
import path from 'path'

export const STORAGE_PATH = path.join(process.cwd(), 'data', 'experiments.json')
export const COMMAND_TIMEOUT = 300000 // 5 minutes
export const MAX_COMMANDS = 10
```

**File:** `src/features/experiments/validations.ts`

```typescript
import { z } from 'zod'

export const commandSchema = z.object({
  command: z.string().min(1, 'Command is required'),
  description: z.string().min(1, 'Description is required'),
})

export const createExperimentSchema = z.object({
  name: z.string().min(1, 'Name is required').max(100, 'Name too long'),
  description: z.string().min(1, 'Description is required').max(500, 'Description too long'),
  commands: z.array(commandSchema).min(1, 'At least one command is required').max(10, 'Too many commands'),
})

export type CreateExperimentInput = z.infer<typeof createExperimentSchema>
```

---

### Task 3: Build Storage Layer

**File:** `src/features/experiments/services/storage.ts`

```typescript
import fs from 'fs/promises'
import { Experiment } from '@/types/experiment'
import { STORAGE_PATH } from '@/shared/utils/constants'

interface StorageData {
  experiments: Experiment[]
}

async function readStorage(): Promise<StorageData> {
  try {
    const data = await fs.readFile(STORAGE_PATH, 'utf-8')
    return JSON.parse(data)
  } catch (error) {
    // Initialize if file doesn't exist
    const initial: StorageData = { experiments: [] }
    await writeStorage(initial)
    return initial
  }
}

async function writeStorage(data: StorageData): Promise<void> {
  await fs.writeFile(STORAGE_PATH, JSON.stringify(data, null, 2), 'utf-8')
}

export async function getAllExperiments(): Promise<Experiment[]> {
  const data = await readStorage()
  return data.experiments.sort((a, b) =>
    new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
  )
}

export async function getExperimentById(id: string): Promise<Experiment | null> {
  const data = await readStorage()
  return data.experiments.find(exp => exp.id === id) || null
}

export async function createExperiment(experiment: Experiment): Promise<Experiment> {
  const data = await readStorage()
  data.experiments.push(experiment)
  await writeStorage(data)
  return experiment
}

export async function updateExperiment(id: string, updates: Partial<Experiment>): Promise<Experiment> {
  const data = await readStorage()
  const index = data.experiments.findIndex(exp => exp.id === id)
  if (index === -1) throw new Error('Experiment not found')

  data.experiments[index] = { ...data.experiments[index], ...updates, updatedAt: new Date().toISOString() }
  await writeStorage(data)
  return data.experiments[index]
}

export async function deleteExperiment(id: string): Promise<void> {
  const data = await readStorage()
  data.experiments = data.experiments.filter(exp => exp.id !== id)
  await writeStorage(data)
}
```

---

### Task 4: Build Execution Engine

**File:** `src/features/experiments/services/executor.ts`

```typescript
import { exec } from 'child_process'
import { promisify } from 'util'
import { Experiment, ExecutionLog, Command } from '@/types/experiment'
import { COMMAND_TIMEOUT } from '@/shared/utils/constants'

const execAsync = promisify(exec)

interface ExecutionResult {
  logs: ExecutionLog[]
  status: 'passed' | 'failed'
  totalDuration: number
}

async function executeCommand(cmd: Command): Promise<ExecutionLog> {
  const startTime = Date.now()

  try {
    const { stdout, stderr } = await execAsync(cmd.command, {
      timeout: COMMAND_TIMEOUT,
      cwd: process.cwd(),
    })

    return {
      commandId: cmd.id,
      command: cmd.command,
      stdout: stdout || '',
      stderr: stderr || '',
      exitCode: 0,
      duration: Date.now() - startTime,
      timestamp: new Date().toISOString(),
    }
  } catch (error: any) {
    return {
      commandId: cmd.id,
      command: cmd.command,
      stdout: error.stdout || '',
      stderr: error.stderr || error.message,
      exitCode: error.code || 1,
      duration: Date.now() - startTime,
      timestamp: new Date().toISOString(),
    }
  }
}

export async function executeExperiment(experiment: Experiment): Promise<ExecutionResult> {
  const logs: ExecutionLog[] = []
  const startTime = Date.now()

  // Execute commands sequentially
  for (const command of experiment.commands) {
    const log = await executeCommand(command)
    logs.push(log)

    // Stop on first failure
    if (log.exitCode !== 0) {
      return {
        logs,
        status: 'failed',
        totalDuration: Date.now() - startTime,
      }
    }
  }

  return {
    logs,
    status: 'passed',
    totalDuration: Date.now() - startTime,
  }
}
```

---

### Task 5: Create Server Actions

**File:** `src/features/experiments/actions.ts`

```typescript
'use server'

import { revalidatePath } from 'next/cache'
import { nanoid } from 'nanoid'
import { createExperiment, updateExperiment, deleteExperiment } from './services/storage'
import { executeExperiment } from './services/executor'
import { createExperimentSchema, CreateExperimentInput } from './validations'
import { Experiment } from '@/types/experiment'

export async function createExperimentAction(input: CreateExperimentInput) {
  const result = createExperimentSchema.safeParse(input)
  if (!result.success) {
    return { success: false, error: result.error.format() }
  }

  const experiment: Experiment = {
    id: nanoid(),
    name: input.name,
    description: input.description,
    commands: input.commands.map(cmd => ({ ...cmd, id: nanoid() })),
    status: 'draft',
    executionLogs: [],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  }

  await createExperiment(experiment)
  revalidatePath('/')
  return { success: true, data: experiment }
}

export async function executeExperimentAction(experimentId: string) {
  const experiment = await getExperimentById(experimentId)
  if (!experiment) return { success: false, error: 'Experiment not found' }

  // Mark as running
  await updateExperiment(experimentId, { status: 'running' })
  revalidatePath(`/experiments/${experimentId}`)

  // Execute
  const result = await executeExperiment(experiment)

  // Update with results
  await updateExperiment(experimentId, {
    status: result.status,
    executionLogs: result.logs,
    lastExecutedAt: new Date().toISOString(),
    totalDuration: result.totalDuration,
  })

  revalidatePath(`/experiments/${experimentId}`)
  return { success: true, data: result }
}

export async function deleteExperimentAction(experimentId: string) {
  await deleteExperiment(experimentId)
  revalidatePath('/')
  return { success: true }
}
```

---

### Task 6: Build UI Components

**File:** `src/shared/components/Button.tsx`

```typescript
import { ButtonHTMLAttributes, forwardRef } from 'react'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger'
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'primary', className = '', ...props }, ref) => {
    const variants = {
      primary: 'bg-blue-600 text-white hover:bg-blue-700',
      secondary: 'bg-gray-200 text-gray-800 hover:bg-gray-300',
      danger: 'bg-red-600 text-white hover:bg-red-700',
    }

    return (
      <button
        ref={ref}
        className={`px-4 py-2 rounded-md font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${variants[variant]} ${className}`}
        {...props}
      />
    )
  }
)

Button.displayName = 'Button'
```

**File:** `src/features/experiments/components/StatusBadge.tsx`

```typescript
import { ExperimentStatus } from '@/types/experiment'
import { getStatusColor } from '@/shared/utils/formatting'

interface StatusBadgeProps {
  status: ExperimentStatus
}

export function StatusBadge({ status }: StatusBadgeProps) {
  return (
    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(status)}`}>
      {status.toUpperCase()}
    </span>
  )
}
```

**File:** `src/features/experiments/components/ExecutionLogs.tsx`

```typescript
import { ExecutionLog } from '@/types/experiment'
import { formatDuration } from '@/shared/utils/formatting'

interface ExecutionLogsProps {
  logs: ExecutionLog[]
}

export function ExecutionLogs({ logs }: ExecutionLogsProps) {
  if (logs.length === 0) {
    return <p className="text-gray-500 text-sm">No execution logs yet.</p>
  }

  return (
    <div className="space-y-4">
      {logs.map((log, i) => (
        <div key={log.commandId} className="border rounded-lg p-4">
          <div className="flex items-center justify-between mb-2">
            <h4 className="font-medium">Command {i + 1}</h4>
            <span className={`px-2 py-1 rounded text-xs font-medium ${
              log.exitCode === 0 ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
            }`}>
              Exit {log.exitCode} • {formatDuration(log.duration)}
            </span>
          </div>

          <code className="block bg-gray-100 p-2 rounded text-sm mb-2">{log.command}</code>

          {log.stdout && (
            <div className="mb-2">
              <p className="text-xs font-medium text-gray-600 mb-1">STDOUT:</p>
              <pre className="bg-gray-50 p-2 rounded text-xs overflow-x-auto">{log.stdout}</pre>
            </div>
          )}

          {log.stderr && (
            <div>
              <p className="text-xs font-medium text-gray-600 mb-1">STDERR:</p>
              <pre className="bg-red-50 p-2 rounded text-xs overflow-x-auto text-red-800">{log.stderr}</pre>
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
```

---

### Task 7: Build Pages

**File:** `src/app/page.tsx` (Dashboard)

```typescript
import Link from 'next/link'
import { getAllExperiments } from '@/features/experiments/services/storage'
import { StatusBadge } from '@/features/experiments/components/StatusBadge'
import { formatDate } from '@/shared/utils/formatting'
import { Button } from '@/shared/components/Button'

export default async function HomePage() {
  const experiments = await getAllExperiments()

  return (
    <main className="container mx-auto px-4 py-8 max-w-4xl">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold">POE — Proof of Execution</h1>
          <p className="text-gray-600 mt-1">Run code experiments and capture proof</p>
        </div>
        <Link href="/experiments/new">
          <Button>+ New Experiment</Button>
        </Link>
      </div>

      {experiments.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 rounded-lg">
          <p className="text-gray-500 mb-4">No experiments yet.</p>
          <Link href="/experiments/new">
            <Button>Create Your First Experiment</Button>
          </Link>
        </div>
      ) : (
        <div className="space-y-4">
          {experiments.map(exp => (
            <Link key={exp.id} href={`/experiments/${exp.id}`}>
              <div className="border rounded-lg p-4 hover:bg-gray-50 transition-colors">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="font-semibold text-lg">{exp.name}</h3>
                      <StatusBadge status={exp.status} />
                    </div>
                    <p className="text-gray-600 text-sm mb-2">{exp.description}</p>
                    <div className="flex items-center gap-4 text-xs text-gray-500">
                      <span>{exp.commands.length} command{exp.commands.length !== 1 ? 's' : ''}</span>
                      <span>Created {formatDate(exp.createdAt)}</span>
                      {exp.lastExecutedAt && <span>Last run {formatDate(exp.lastExecutedAt)}</span>}
                    </div>
                  </div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </main>
  )
}
```

**File:** `src/app/experiments/new/page.tsx` (Create Form)

```typescript
'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { createExperimentAction } from '@/features/experiments/actions'
import { Button } from '@/shared/components/Button'

export default function NewExperimentPage() {
  const router = useRouter()
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [commands, setCommands] = useState([{ command: '', description: '' }])
  const [isSubmitting, setIsSubmitting] = useState(false)

  const addCommand = () => {
    if (commands.length < 10) {
      setCommands([...commands, { command: '', description: '' }])
    }
  }

  const removeCommand = (index: number) => {
    setCommands(commands.filter((_, i) => i !== index))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)

    const result = await createExperimentAction({ name, description, commands })

    if (result.success) {
      router.push(`/experiments/${result.data.id}`)
    } else {
      alert('Failed to create experiment')
      setIsSubmitting(false)
    }
  }

  return (
    <main className="container mx-auto px-4 py-8 max-w-2xl">
      <h1 className="text-3xl font-bold mb-6">Create New Experiment</h1>

      <form onSubmit={handleSubmit} className="space-y-6">
        <div>
          <label className="block text-sm font-medium mb-1">Experiment Name</label>
          <input
            type="text"
            value={name}
            onChange={e => setName(e.target.value)}
            className="w-full border rounded-md px-3 py-2"
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-1">Description</label>
          <textarea
            value={description}
            onChange={e => setDescription(e.target.value)}
            className="w-full border rounded-md px-3 py-2"
            rows={3}
            required
          />
        </div>

        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="block text-sm font-medium">Commands</label>
            <Button type="button" onClick={addCommand} variant="secondary" className="text-sm">
              + Add Command
            </Button>
          </div>

          <div className="space-y-4">
            {commands.map((cmd, i) => (
              <div key={i} className="border rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium">Command {i + 1}</span>
                  {commands.length > 1 && (
                    <button
                      type="button"
                      onClick={() => removeCommand(i)}
                      className="text-red-600 text-sm hover:text-red-700"
                    >
                      Remove
                    </button>
                  )}
                </div>

                <input
                  type="text"
                  placeholder="e.g., npm test"
                  value={cmd.command}
                  onChange={e => {
                    const updated = [...commands]
                    updated[i].command = e.target.value
                    setCommands(updated)
                  }}
                  className="w-full border rounded-md px-3 py-2 mb-2"
                  required
                />

                <input
                  type="text"
                  placeholder="Description of what this command does"
                  value={cmd.description}
                  onChange={e => {
                    const updated = [...commands]
                    updated[i].description = e.target.value
                    setCommands(updated)
                  }}
                  className="w-full border rounded-md px-3 py-2"
                  required
                />
              </div>
            ))}
          </div>
        </div>

        <div className="flex gap-4">
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? 'Creating...' : 'Create Experiment'}
          </Button>
          <Button type="button" variant="secondary" onClick={() => router.back()}>
            Cancel
          </Button>
        </div>
      </form>
    </main>
  )
}
```

**File:** `src/app/experiments/[id]/page.tsx` (Detail View)

```typescript
import { notFound } from 'next/navigation'
import { getExperimentById } from '@/features/experiments/services/storage'
import { StatusBadge } from '@/features/experiments/components/StatusBadge'
import { ExecutionLogs } from '@/features/experiments/components/ExecutionLogs'
import { formatDate, formatDuration } from '@/shared/utils/formatting'
import { ExecuteButton } from './ExecuteButton'
import { DeleteButton } from './DeleteButton'

export default async function ExperimentDetailPage({ params }: { params: { id: string } }) {
  const experiment = await getExperimentById(params.id)
  if (!experiment) notFound()

  return (
    <main className="container mx-auto px-4 py-8 max-w-4xl">
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <h1 className="text-3xl font-bold">{experiment.name}</h1>
          <StatusBadge status={experiment.status} />
        </div>
        <p className="text-gray-600">{experiment.description}</p>
      </div>

      <div className="flex gap-4 mb-8">
        <ExecuteButton experimentId={experiment.id} />
        <DeleteButton experimentId={experiment.id} />
      </div>

      <div className="grid md:grid-cols-2 gap-8 mb-8">
        <div>
          <h2 className="text-xl font-semibold mb-4">Commands</h2>
          <div className="space-y-3">
            {experiment.commands.map((cmd, i) => (
              <div key={cmd.id} className="border rounded-lg p-3">
                <p className="text-sm font-medium text-gray-600 mb-1">{cmd.description}</p>
                <code className="block bg-gray-100 p-2 rounded text-sm">{cmd.command}</code>
              </div>
            ))}
          </div>
        </div>

        <div>
          <h2 className="text-xl font-semibold mb-4">Metadata</h2>
          <dl className="space-y-2 text-sm">
            <div>
              <dt className="text-gray-600">Created</dt>
              <dd>{formatDate(experiment.createdAt)}</dd>
            </div>
            <div>
              <dt className="text-gray-600">Last Updated</dt>
              <dd>{formatDate(experiment.updatedAt)}</dd>
            </div>
            {experiment.lastExecutedAt && (
              <div>
                <dt className="text-gray-600">Last Executed</dt>
                <dd>{formatDate(experiment.lastExecutedAt)}</dd>
              </div>
            )}
            {experiment.totalDuration && (
              <div>
                <dt className="text-gray-600">Total Duration</dt>
                <dd>{formatDuration(experiment.totalDuration)}</dd>
              </div>
            )}
          </dl>
        </div>
      </div>

      <div>
        <h2 className="text-xl font-semibold mb-4">Execution Logs</h2>
        <ExecutionLogs logs={experiment.executionLogs} />
      </div>
    </main>
  )
}
```

---

### Task 8: Build Client Components

**File:** `src/app/experiments/[id]/ExecuteButton.tsx`

```typescript
'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { executeExperimentAction } from '@/features/experiments/actions'
import { Button } from '@/shared/components/Button'

export function ExecuteButton({ experimentId }: { experimentId: string }) {
  const router = useRouter()
  const [isExecuting, setIsExecuting] = useState(false)

  const handleExecute = async () => {
    setIsExecuting(true)
    await executeExperimentAction(experimentId)
    router.refresh()
    setIsExecuting(false)
  }

  return (
    <Button onClick={handleExecute} disabled={isExecuting}>
      {isExecuting ? 'Executing...' : '▶ Execute'}
    </Button>
  )
}
```

**File:** `src/app/experiments/[id]/DeleteButton.tsx`

```typescript
'use client'

import { useRouter } from 'next/navigation'
import { deleteExperimentAction } from '@/features/experiments/actions'
import { Button } from '@/shared/components/Button'

export function DeleteButton({ experimentId }: { experimentId: string }) {
  const router = useRouter()

  const handleDelete = async () => {
    if (!confirm('Delete this experiment? This cannot be undone.')) return

    await deleteExperimentAction(experimentId)
    router.push('/')
  }

  return (
    <Button onClick={handleDelete} variant="danger">
      Delete
    </Button>
  )
}
```

---

## Success Criteria

- [ ] Next.js 15 project scaffolded with TypeScript + Tailwind + App Router
- [ ] Core types defined (Experiment, ExecutionLog, Command, Status)
- [ ] Storage layer operational (CRUD on experiments.json)
- [ ] Execution engine works (sequential command execution, captures logs)
- [ ] Server actions implemented (create, execute, delete)
- [ ] UI components built (Button, StatusBadge, ExecutionLogs)
- [ ] Dashboard page shows all experiments
- [ ] Create form works (add/remove commands, validation)
- [ ] Detail page shows experiment + logs + execute/delete buttons
- [ ] End-to-end flow verified:
  - [ ] Create experiment with 2 commands
  - [ ] Execute experiment, verify logs captured
  - [ ] Re-execute, verify new logs replace old
  - [ ] Delete experiment
- [ ] App runs on port 3001 (`npm run dev`)
- [ ] Build succeeds (`npm run build`)
- [ ] Type checking passes (`npm run type-check`)
- [ ] No console errors or warnings

---

## Troubleshooting

### Port 3000 already in use
```bash
# Change port in package.json scripts
"dev": "next dev -p 3001"
```

### File system errors (experiments.json)
```bash
# Ensure data directory exists
mkdir -p data
echo '{"experiments":[]}' > data/experiments.json
```

### Server actions not working
```bash
# Verify 'use server' directive at top of actions.ts
# Verify revalidatePath() is called after mutations
```

### Execution logs not showing
```bash
# Check executor.ts executeCommand function
# Verify logs are being written to executionLogs array
# Check ExecutionLogs component is receiving logs prop
```

### Commands timing out
```bash
# Increase COMMAND_TIMEOUT in constants.ts
# Default is 300000ms (5 minutes)
```

---

## Files Modified This Session

Track all changes:
```bash
# List new files
git status

# Review changes
git diff

# Commit with descriptive message
git add .
git commit -m "feat(poe): POE app MVP with experiment execution system

- Scaffolded Next.js 15 + TypeScript + Tailwind + App Router
- Implemented core types: Experiment, ExecutionLog, Command, Status
- Built storage layer with JSON file-based CRUD
- Created execution engine with sequential command execution
- Added server actions: create, execute, delete experiments
- Built UI components: Button, StatusBadge, ExecutionLogs
- Created pages: dashboard, create form, detail view
- Added client components: ExecuteButton, DeleteButton
- Verified end-to-end flow: create → execute → view logs → delete
- App running on port 3001"
```

---

## Next Session

After POE App complete, move to **Session 5: Performance Optimization & Final Polish**
