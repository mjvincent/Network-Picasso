import {
  Button,
  Column,
  Content,
  Dropdown,
  FileUploaderDropContainer,
  FileUploaderItem,
  Grid,
  Header,
  HeaderName,
  InlineLoading,
  InlineNotification,
  Layer,
  Modal,
  OverflowMenu,
  OverflowMenuItem,
  ProgressIndicator,
  ProgressStep,
  Select,
  SelectItem,
  SideNav,
  SideNavItems,
  SideNavLink,
  SideNavMenu,
  SideNavMenuItem,
  Stack,
  StructuredListBody,
  StructuredListCell,
  StructuredListHead,
  StructuredListRow,
  StructuredListWrapper,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  Tag,
  TextArea,
  TextInput,
  Tile,
  Toggle,
  Tooltip,
} from '@carbon/react';
import {
  Add,
  ArrowRight,
  ArrowLeft,
  Checkmark,
  Copy,
  Diagram,
  DocumentImport,
  Download,
  IbmCloud,
  Information,
  Launch,
  ListChecked,
  Layers,
  Renew,
  Settings,
  Upload,
} from '@carbon/icons-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import {
  type AnsweredQuestion as AnsweredQuestionType,
  type Question,
  mergeQuestions,
  questionKey,
} from './utils';
import { deflateRaw } from 'pako';

type Component = {
  name: string;
  purpose?: string;
  region?: string;
  source?: string;
};

type PatternResult = {
  id: string;
  name: string;
  description: string;
  url: string;
  score: number;
  matched: string[];
  missing: string[];
};

type PillarReview = {
  name: string;
  score: number;
  status: string;
  evidence: string[];
  gaps: string[];
  recommendation: string;
};

type LogicalDesignItem = {
  area: string;
  design: string;
};

type ArchitectureReview = {
  recommendedPattern: PatternResult | null;
  alternativePatterns: PatternResult[];
  wellArchitected: PillarReview[];
  openDecisionCount: number;
  priorityQuestions: Question[];
  sellerNextActions: string[];
  patternFoundation?: {
    name: string;
    rationale: string;
    requiredElements: string[];
  };
  logicalDesign: LogicalDesignItem[];
};

type DiagramQualityFinding = {
  severity: 'info' | 'warning' | 'error';
  area: string;
  message: string;
  recommendation: string;
  evidence?: string[];
};

type DiagramQualityReview = {
  score: number;
  status: string;
  diagramType: string;
  pattern: string;
  ibmPatternSource: string;
  checkedCells: number;
  summary: string;
  findings: DiagramQualityFinding[];
  ibmPatternChecks: {
    id: string;
    name: string;
    source: string;
    checks: Array<{ name: string; present: boolean; tokens: string[] }>;
  };
};

type Architecture = {
  project: { name: string; environment?: string };
  ibm_cloud: Record<string, Component[] | string[]>;
  questions?: { answered?: AnsweredQuestionType[]; open?: Question[] | string[] };
  quality?: {
    lastReview?: {
      score: number;
      status: string;
      diagramType: string;
      summary: string;
      findingCount: number;
      timestamp: string;
    };
  };
  sources?: Array<{ file: string; type: string; records: number; role?: string; skipped?: boolean; skip_reason?: string }>;
};

type FileRole = {
  file: string;
  role: string;
};

type AppSettings = {
  mode: 'rules' | 'ollama';
  ollamaModel: string;
  confidenceThreshold: number;
  projectsRoot: string;
};

type ProjectNode = {
  customer: string;
  project: string;
  path: string;
  hasArchitecture: boolean;
  isLegacy: boolean;
};

type ProjectSnapshot = {
  id: number;
  label: string;
  eventType: string;
  qualityScore?: number | null;
  createdAt: string;
};

type RestoreFilter = 'all' | 'milestones' | 'autosave' | 'intake' | 'decisions' | 'quality' | 'restores';

type RestorePreview = {
  snapshot: {
    id: number;
    label: string;
    eventType: string;
    createdAt: string;
  };
  comparison: {
    changes: Array<{ label: string; current: unknown; restore: unknown }>;
    addedServices: string[];
    removedServices: string[];
  };
};

type ProjectActivity = {
  id: string;
  customer: string;
  project: string;
  file: {
    path: string;
    architecturePath: string;
    hasArchitecture: boolean;
    architectureSize: number;
    architectureModifiedAt: string;
  };
  persistence: {
    enabled: boolean;
    connected: boolean;
    schemaVersion: number;
    message: string;
  };
  persisted?: {
    updatedAt?: string;
    createdAt?: string;
    hasArchitecture?: boolean;
  } | null;
  events: Array<{
    eventType: string;
    detail: Record<string, unknown>;
    createdAt: string;
  }>;
  snapshots: ProjectSnapshot[];
  retention?: {
    autosaveLimit: number;
    milestonesRetained: boolean;
    description: string;
    autosaveCount?: number;
    milestoneCount?: number;
    totalCount?: number;
  };
};

type AnsweredQuestion = AnsweredQuestionType;

type PendingComponent = {
  id: string;
  name: string;
  suggestedKey: string;
  confidence: number;
  notes?: string;
};

type CarbonTagType =
  | 'green'
  | 'teal'
  | 'red'
  | 'blue'
  | 'purple'
  | 'cyan'
  | 'gray'
  | 'magenta'
  | 'cool-gray'
  | 'warm-gray'
  | 'high-contrast'
  | 'outline';

// Step IDs drive the wizard
type Step = 'upload' | 'review' | 'questions' | 'diagram';
const STEPS: Step[] = ['upload', 'review', 'questions', 'diagram'];
const STEP_LABELS: Record<Step, string> = {
  upload:    '1. Upload',
  review:    '2. Review model',
  questions: '3. Answer questions',
  diagram:   '4. Generate diagram',
};
const STEP_DESCRIPTIONS: Record<Step, string> = {
  upload:    'Add your source files',
  review:    'Check what was extracted',
  questions: 'Fill design gaps',
  diagram:   'Create your Draw.io file',
};

const API_HEADERS = { 'Content-Type': 'application/json' };
const BROWSER_MCP_EDITOR_URL = 'http://127.0.0.1:4000';
const ACCEPTED_FILE_TYPES = ['.xlsx', '.csv', '.tsv', '.json', '.md', '.txt'];
const IBM_CLOUD_KEYS = [
  'regions', 'vpcs', 'zones', 'subnets', 'connectivity', 'ingress',
  'compute', 'data', 'private_endpoints', 'dns', 'security', 'observability', 'backup_dr',
];
const BOB_PROMPT_CATEGORY_HELP: Record<string, string> = {
  Start: 'Use this first when Bob has just connected to the Draw.io MCP editor. It tells Bob to inspect before editing and to preserve the generated architecture.',
  Layout: 'Use these when the diagram is technically correct but looks crowded, has overlapping labels, awkward connector paths, or uneven container alignment.',
  'IBM Pattern': 'Use these when you want the diagram to better resemble IBM architecture pattern guidance, landing zone conventions, or expected IBM Cloud structure.',
  'Seller Review': 'Use these when preparing for a customer conversation. They improve clarity, audience fit, naming, and executive readability.',
  Security: 'Use these when the diagram needs stronger compliance, audit, encryption, private access, or zero-trust evidence.',
  Resiliency: 'Use this when primary and recovery regions, replication, failover, RPO/RTO, or DR responsibilities need to be clearer.',
  Data: 'Use this when data movement, storage, archive, retrieval, replication, or backup paths are unclear.',
  'Final QA': 'Use these at the end. Customer Ready is a broad final polish; No Topology Change is safest when you only want presentation changes.',
};

async function postJson<T>(url: string, body: unknown): Promise<T> {
  const response = await fetch(url, { method: 'POST', headers: API_HEADERS, body: JSON.stringify(body) });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.error || `Request failed: ${response.status}`);
  }
  return response.json();
}

function encodeDrawioUrlPayload(xml: string): string {
  const compressed = deflateRaw(new TextEncoder().encode(xml), { level: 9 });
  let binary = '';
  const chunkSize = 0x8000;
  for (let i = 0; i < compressed.length; i += chunkSize) {
    binary += String.fromCharCode(...compressed.slice(i, i + chunkSize));
  }
  return encodeURIComponent(btoa(binary));
}

function bobPromptTemplates(diagramType: string) {
  const pageName = diagramType === 'executive'
    ? 'Executive Overview'
    : diagramType === 'logical'
      ? 'Logical Architecture'
      : diagramType === 'context'
        ? 'Context'
        : 'Deployment';
  return [
    {
      category: 'Start',
      label: 'Setup Bob',
      text: 'Use the ibm-drawio-editing skill. Inspect the open Draw.io MCP document before making changes. Use IBM Cloud stencil patterns, keep labels non-overlapping, and preserve the existing architecture pages.',
    },
    {
      category: 'Layout',
      label: 'Clean Labels',
      text: `Use the ibm-drawio-editing skill. Inspect the ${pageName} page in the open Draw.io MCP document. Improve label placement, spacing, and connector routing while preserving the architecture, IBM Cloud container boundaries, and page structure.`,
    },
    {
      category: 'Layout',
      label: 'Fix Connectors',
      text: `Use the ibm-drawio-editing skill. Inspect the ${pageName} page and clean connector routing. Use orthogonal routing, move edge labels off lines and shapes, reduce line crossings, and preserve all existing source-to-target relationships.`,
    },
    {
      category: 'Layout',
      label: 'Align Containers',
      text: `Use the ibm-drawio-editing skill. Inspect the ${pageName} page and align IBM Cloud account, region, VPC, zone, subnet, shared service, and PowerVS containers to a clean grid. Keep container hierarchy intact and leave enough whitespace for labels.`,
    },
    {
      category: 'IBM Pattern',
      label: 'IBM Pattern Check',
      text: `Use the ibm-drawio-editing skill. Inspect the ${pageName} page for IBM architecture pattern clarity. Verify the diagram visibly reflects the chosen IBM pattern foundation, including cloud account boundary, regions, VPC or landing zone structure, connectivity, security services, observability, and resiliency elements. Add only missing pattern-evidence labels or service nodes that are already supported by the architecture model.`,
    },
    {
      category: 'IBM Pattern',
      label: 'Landing Zone Polish',
      text: `Use the ibm-drawio-editing skill. Inspect the ${pageName} page and make the IBM Cloud landing zone structure clearer. Emphasize account, region, VPC, subnet tiering, private endpoints, security controls, logging/monitoring, and connectivity. Preserve customer-specific naming and topology.`,
    },
    {
      category: 'Seller Review',
      label: 'Architecture Polish',
      text: `Use the ibm-drawio-editing skill. Review the ${pageName} page for IBM Cloud architecture clarity. Make only targeted polish changes: align containers, reduce overlapping labels, improve edge labels, and keep seller-friendly naming.`,
    },
    {
      category: 'Seller Review',
      label: 'Exec Simplify',
      text: 'Use the ibm-drawio-editing skill. Inspect the Executive Overview page and simplify it for a customer executive audience. Keep the business flow, primary/DR posture, compliance evidence, and IBM Cloud value clear. Remove unnecessary implementation-level labels from this page only, without changing the detailed deployment page.',
    },
    {
      category: 'Security',
      label: 'Add Evidence',
      text: 'Use the ibm-drawio-editing skill. On the Deployment page, add or refine security and compliance evidence elements for HIPAA: Security and Compliance Center, Activity Tracker, VPC Flow Logs, Key Protect or HPCS, Secrets Manager, and Virtual Private Endpoints. Preserve the existing DAL/WDC PowerVS DR topology.',
    },
    {
      category: 'Security',
      label: 'Zero Trust Review',
      text: `Use the ibm-drawio-editing skill. Inspect the ${pageName} page for zero-trust clarity. Show private connectivity, least-privilege service access, encryption/key management, audit logging, private endpoints, and controlled ingress/egress where already implied by the architecture. Do not invent public exposure.`,
    },
    {
      category: 'Resiliency',
      label: 'DR Storyline',
      text: `Use the ibm-drawio-editing skill. Inspect the ${pageName} page and clarify the disaster recovery storyline. Make primary and recovery regions visually distinct, label replication paths with RPO/RTO placeholders only if unknown, and show which workloads, data stores, and connectivity components participate in failover. Preserve the current architecture facts.`,
    },
    {
      category: 'Data',
      label: 'Data Flow Review',
      text: `Use the ibm-drawio-editing skill. Inspect the ${pageName} page and improve data-flow readability. Label intake, application, storage, replication, backup/archive, and retrieval paths. Keep labels outside shapes and avoid crossing connectors through subnet or service labels.`,
    },
    {
      category: 'Final QA',
      label: 'Customer Ready',
      text: `Use the ibm-drawio-editing skill. Perform a final customer-readiness review of the ${pageName} page. Fix visible overlaps, ambiguous labels, inconsistent casing, cramped text, missing legends, poor spacing, and unclear flow direction. Make targeted edits only and summarize every change.`,
    },
    {
      category: 'Final QA',
      label: 'No Topology Change',
      text: `Use the ibm-drawio-editing skill. Inspect the ${pageName} page and make presentation-only improvements. Do not add, delete, reconnect, or rename architecture components. Only adjust size, spacing, alignment, connector routing, label placement, and visual hierarchy.`,
    },
  ];
}

function qualityRemediationPrompt(diagramType: string, review: DiagramQualityReview): string {
  const findings = review.findings.slice(0, 8);
  const findingText = findings.length
    ? findings.map((finding, index) =>
        `${index + 1}. ${finding.area}: ${finding.message} Recommendation: ${finding.recommendation}`
      ).join('\n')
    : 'No analyzer findings were reported. Inspect the page for final presentation polish.';
  const missingPatternChecks = review.ibmPatternChecks.checks
    .filter((check) => !check.present)
    .map((check) => `- ${check.name}`)
    .join('\n') || '- No missing IBM pattern checks reported.';

  return `Use the ibm-drawio-editing skill. Inspect the currently open ${diagramType} Draw.io page in the MCP editor and remediate the Network Picasso quality analyzer findings below.

Quality score: ${review.score}/100 (${review.status})
IBM pattern foundation: ${review.ibmPatternChecks.name}

Findings to address:
${findingText}

IBM pattern checks to review:
${missingPatternChecks}

Make targeted, professional-grade edits only. Preserve the customer-specific architecture, IBM Cloud stencil language, page structure, and intended network topology. Improve label placement, shape sizing, connector routing, and pattern clarity. After editing, summarize what changed so Network Picasso can re-analyze the diagram.`;
}

function recommendedBobPrompt(review: DiagramQualityReview | null): { label: string; reason: string } {
  if (!review) {
    return {
      label: 'Setup Bob',
      reason: 'Start here after opening the diagram in MCP so Bob inspects the document before editing.',
    };
  }
  const findingText = review.findings.map((finding) =>
    `${finding.area} ${finding.message} ${finding.recommendation}`.toLowerCase()
  ).join(' ');
  const missingPattern = review.ibmPatternChecks.checks.some((check) => !check.present);
  if (findingText.includes('connector') || findingText.includes('edge') || findingText.includes('line')) {
    return { label: 'Fix Connectors', reason: 'Quality findings mention connector or edge readability.' };
  }
  if (findingText.includes('label') || findingText.includes('overlap') || findingText.includes('text')) {
    return { label: 'Clean Labels', reason: 'Quality findings indicate label fit or overlap risk.' };
  }
  if (missingPattern) {
    return { label: 'IBM Pattern Check', reason: 'IBM pattern checks show missing or unclear pattern elements.' };
  }
  if (findingText.includes('density') || findingText.includes('crowd') || findingText.includes('container')) {
    return { label: 'Align Containers', reason: 'The page would benefit from spacing and container alignment polish.' };
  }
  if (review.score >= 90) {
    return { label: 'Customer Ready', reason: 'The score is strong; use a final presentation review before sharing.' };
  }
  return { label: 'Architecture Polish', reason: 'Use a broad architecture clarity pass for the current quality findings.' };
}

async function postForm<T>(url: string, body: FormData): Promise<T> {
  const response = await fetch(url, { method: 'POST', body });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.error || `Request failed: ${response.status}`);
  }
  return response.json();
}

const DEFAULT_SETTINGS: AppSettings = {
  mode: 'rules',
  ollamaModel: 'phi4-mini:latest',
  confidenceThreshold: 0.8,
  projectsRoot: 'inputs/projects',
};

/** Return Carbon Tag props for a file role string, or null if no badge needed. */
function roleTagProps(role?: string): { type: CarbonTagType; label: string } | null {
  switch (role) {
    case 'bom':                  return { type: 'green',     label: 'BOM' };
    case 'unified_pricing':      return { type: 'teal',      label: 'Unified pricing' };
    case 'pricing_catalog':      return { type: 'red',       label: 'Pricing catalog' };
    case 'solution_description': return { type: 'blue',      label: 'Notes' };
    case 'existing_architecture':return { type: 'purple',    label: 'Architecture' };
    default:                     return null;
  }
}

function formatRestoreValue(value: unknown): string {
  if (Array.isArray(value)) {
    return value.length ? value.join(', ') : 'None';
  }
  if (typeof value === 'number') {
    return String(value);
  }
  if (typeof value === 'string') {
    return value.trim() || 'Not set';
  }
  if (value == null) {
    return 'Not set';
  }
  return JSON.stringify(value);
}

const RESTORE_FILTERS: Array<{ id: RestoreFilter; label: string }> = [
  { id: 'milestones', label: 'Milestones' },
  { id: 'all', label: 'All restore points' },
  { id: 'autosave', label: 'Autosaves' },
  { id: 'intake', label: 'Intake and imports' },
  { id: 'decisions', label: 'Design decisions' },
  { id: 'quality', label: 'Quality checks' },
  { id: 'restores', label: 'Restores and syncs' },
];

function restoreFilterForEvent(eventType: string): RestoreFilter {
  if (eventType === 'autosave') return 'autosave';
  if (['intake', 'upload-intake', 'project-imported', 'project-duplicated'].includes(eventType)) return 'intake';
  if (['answer-saved', 'requirements-saved', 'components-confirmed', 'pattern-set'].includes(eventType)) return 'decisions';
  if (eventType === 'diagram-quality') return 'quality';
  if (['restore-point', 'manual-sync'].includes(eventType)) return 'restores';
  return 'milestones';
}

function restoreEventLabel(eventType: string): string {
  switch (restoreFilterForEvent(eventType)) {
    case 'autosave': return 'Autosave';
    case 'intake': return 'Intake';
    case 'decisions': return 'Decision';
    case 'quality': return 'Quality';
    case 'restores': return 'Restore';
    default: return 'Milestone';
  }
}

function restoreEventTagType(eventType: string): CarbonTagType {
  switch (restoreFilterForEvent(eventType)) {
    case 'autosave': return 'gray';
    case 'intake': return 'blue';
    case 'decisions': return 'teal';
    case 'quality': return 'purple';
    case 'restores': return 'green';
    default: return 'cool-gray';
  }
}

// Re-export utilities for tests
export { questionKey, mergeQuestions };

type FolderNode = {
  name: string;
  path: string;
  projectCount: number;
  childCount: number;
};

export default function App() {
  // Wizard state
  const [step, setStep] = useState<Step>('upload');
  const [activeNav, setActiveNav] = useState<'wizard' | 'settings' | 'projects'>('wizard');

  // Intake state
  const [projectName, setProjectName]     = useState('');
  const [architecturePath, setArchitecturePath] = useState('examples/sample/architecture.json');
  const [diagramType, setDiagramType]     = useState('deployment');
  const [architecture, setArchitecture]   = useState<Architecture | null>(null);
  const [questions, setQuestions]         = useState<Question[]>([]);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [questionAnswers, setQuestionAnswers] = useState<Record<string, string>>({});
  const [answeredQuestions, setAnsweredQuestions] = useState<AnsweredQuestion[]>([]);
  const [pendingComponents, setPendingComponents] = useState<PendingComponent[]>([]);
  const [pendingAssignments, setPendingAssignments] = useState<Record<string, string>>({});
  const [fileRoles, setFileRoles] = useState<FileRole[]>([]);
  const [patternResults, setPatternResults] = useState<PatternResult[]>([]);
  const [chosenPattern, setChosenPatternState] = useState<PatternResult | null>(null);
  const [patternBusy, setPatternBusy] = useState(false);
  const [architectureReview, setArchitectureReview] = useState<ArchitectureReview | null>(null);
  const [architectureReviewBusy, setArchitectureReviewBusy] = useState(false);
  const [diagramQuality, setDiagramQuality] = useState<DiagramQualityReview | null>(null);
  const [diagramQualityBusy, setDiagramQualityBusy] = useState(false);
  const [diagramPath, setDiagramPath]     = useState('');
  const [requirementsText, setRequirementsText] = useState('');
  const [requirementsSaved, setRequirementsSaved] = useState(false);
  const requirementsFileRef = useRef<HTMLInputElement>(null);
  const [previewXml, setPreviewXml]       = useState<string | null>(null);
  const [previewReady, setPreviewReady]   = useState(false);
  const previewRef = useRef<HTMLIFrameElement>(null);

  // UI state
  // Holds XML pending delivery to a diagrams.net popup (Option C).
  // Also store the window reference — required because we can't use noopener
  // (that would null out window.opener, making event.source unusable).
  const pendingPopupXml = useRef<string | null>(null);
  const popupWindowRef  = useRef<Window | null>(null);

  const [status, setStatus]   = useState('');
  const [error, setError]     = useState('');
  const [busy, setBusy]       = useState(false);

  // Settings state
  const [settings, setSettings]           = useState<AppSettings>(DEFAULT_SETTINGS);
  const [ollamaModels, setOllamaModels]   = useState<string[]>([]);
  const [settingsStatus, setSettingsStatus] = useState('');
  const [connectionStatus, setConnectionStatus] = useState<'idle' | 'ok' | 'fail'>('idle');

  // Draw.io MCP editor state
  const [mcpRunning, setMcpRunning] = useState(false);
  const [mcpStatus, setMcpStatus]   = useState('');
  const [mcpEditorOpened, setMcpEditorOpened] = useState(false);
  const [mcpDiagramPushed, setMcpDiagramPushed] = useState(false);
  const [copiedPrompt, setCopiedPrompt] = useState('');

  // Project state
  const [projectTree, setProjectTree]     = useState<ProjectNode[]>([]);
  const [activeProject, setActiveProject] = useState<ProjectNode | null>(null);
  const [showNewProjectModal, setShowNewProjectModal] = useState(false);
  const [showNewFolderModal, setShowNewFolderModal] = useState(false);
  const [newCustomerName, setNewCustomerName] = useState('');
  const [newProjectName, setNewProjectName]   = useState('');
  const [newFolderName, setNewFolderName] = useState('');
  const [autosaveStatus, setAutosaveStatus] = useState('');
  const autosaveTimerRef = useRef<number | null>(null);
  const [projectActivity, setProjectActivity] = useState<ProjectActivity | null>(null);
  const [projectActivityBusy, setProjectActivityBusy] = useState(false);
  const [restoreTarget, setRestoreTarget] = useState<ProjectSnapshot | null>(null);
  const [restorePreview, setRestorePreview] = useState<RestorePreview | null>(null);
  const [restorePreviewBusy, setRestorePreviewBusy] = useState(false);
  const [restoreBusy, setRestoreBusy] = useState(false);
  const [restoreFilter, setRestoreFilter] = useState<RestoreFilter>('milestones');
  const importInputRef = useRef<HTMLInputElement>(null);

  // Projects page state (folder browser)
  const [folders, setFolders]             = useState<FolderNode[]>([]);
  const [browseFolder, setBrowseFolder]   = useState<FolderNode | null>(null); // null = root
  const [folderProjects, setFolderProjects] = useState<ProjectNode[]>([]);
  const [foldersLoading, setFoldersLoading] = useState(false);
  // Project action modals
  const [renameTarget, setRenameTarget]   = useState<ProjectNode | null>(null);
  const [renameValue, setRenameValue]     = useState('');
  const [deleteTarget, setDeleteTarget]   = useState<{ kind: 'project' | 'folder'; node: ProjectNode | FolderNode } | null>(null);
  const [duplicateTarget, setDuplicateTarget] = useState<ProjectNode | null>(null);
  const [duplicateName, setDuplicateName] = useState('');
  const [moveTarget, setMoveTarget]       = useState<ProjectNode | null>(null);
  const [moveDest, setMoveDest]           = useState('');
  const [renameFolderTarget, setRenameFolderTarget] = useState<FolderNode | null>(null);
  const [renameFolderValue, setRenameFolderValue]   = useState('');
  const [projectsActionBusy, setProjectsActionBusy] = useState(false);
  const [projectsError, setProjectsError] = useState('');

  // Send XML to the embed iframe whenever both are ready
  useEffect(() => {
    if (previewReady && previewXml && previewRef.current?.contentWindow) {
      previewRef.current.contentWindow.postMessage(
        JSON.stringify({ action: 'load', xml: previewXml }),
        'https://embed.diagrams.net',
      );
    }
  }, [previewReady, previewXml]);

  // Reset preview state when diagram type changes so the iframe reloads
  useEffect(() => {
    setPreviewXml(null);
    setPreviewReady(false);
    setDiagramQuality(null);
  }, [diagramType]);

  useEffect(() => {
    fetch('/api/example')
      .then((r) => r.json())
      .then((payload) => {
        // Do NOT load answeredQuestions from the example — it's a demo warmup only.
        // Answered state must only come from a real project intake run.
        setArchitecture(payload.architecture);
        setQuestions(payload.questions || []);
        setArchitecturePath(payload.architecturePath);
        runArchitectureReview(payload.architecture, '');
      })
      .catch(() => setStatus('Start the local API server to use this app.'));

    fetch('/api/settings')
      .then((r) => r.json())
      .then((s: AppSettings) => setSettings({ ...DEFAULT_SETTINGS, ...s }))
      .catch(() => {});

    fetch('/api/ollama/models')
      .then((r) => r.json())
      .then((data: { models: string[] }) => setOllamaModels(data.models || []))
      .catch(() => {});

    // Probe the MCP editor on startup (non-blocking)
    fetch('/api/drawio-mcp/health')
      .then((r) => r.json())
      .then((d: { running: boolean }) => setMcpRunning(d.running))
      .catch(() => setMcpRunning(false));

    refreshProjectTree();
  }, []);

  useEffect(() => {
    if (!architecture || !activeProject || activeProject.isLegacy) return;
    if (autosaveTimerRef.current) window.clearTimeout(autosaveTimerRef.current);
    setAutosaveStatus('Autosaving...');
    autosaveTimerRef.current = window.setTimeout(async () => {
      try {
        const payload = await postJson<{ outputPath: string }>('/api/projects/autosave', {
          path: activeProject.path,
          architecture,
        });
        setArchitecturePath(payload.outputPath);
        setActiveProject((current) =>
          current?.path === activeProject.path && !current.hasArchitecture
            ? { ...current, hasArchitecture: true }
            : current
        );
        setProjectTree((current) =>
          current.map((node) =>
            node.path === activeProject.path && !node.hasArchitecture
              ? { ...node, hasArchitecture: true }
              : node
          )
        );
        setAutosaveStatus(`Saved ${new Date().toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })}`);
        await loadProjectActivity(activeProject);
      } catch {
        setAutosaveStatus('Autosave failed');
      }
    }, 900);
    return () => {
      if (autosaveTimerRef.current) window.clearTimeout(autosaveTimerRef.current);
    };
  }, [architecture, activeProject]);

  // ── Project helpers ──────────────────────────────────────────────────────────

  function refreshProjectTree() {
    fetch('/api/projects')
      .then((r) => r.json())
      .then((data: { projects: ProjectNode[] }) => setProjectTree(data.projects || []))
      .catch(() => {});
  }

  async function loadProjectActivity(node = activeProject) {
    if (!node || node.isLegacy) {
      setProjectActivity(null);
      return;
    }
    setProjectActivityBusy(true);
    try {
      const data = await fetch(`/api/project-activity?path=${encodeURIComponent(node.path)}`)
        .then((r) => r.json()) as ProjectActivity;
      setProjectActivity(data);
    } catch {
      setProjectActivity(null);
    } finally {
      setProjectActivityBusy(false);
    }
  }

  // ── Folder browser (Projects page) ──────────────────────────────────────

  async function loadFolders() {
    setFoldersLoading(true);
    setProjectsError('');
    try {
      const data: { folders: FolderNode[] } = await fetch('/api/folders').then((r) => r.json());
      setFolders(data.folders || []);
      setBrowseFolder(null);
      setFolderProjects([]);
    } catch { setProjectsError('Could not load folders.'); }
    finally { setFoldersLoading(false); }
  }

  async function loadFolderProjects(folder: FolderNode) {
    setFoldersLoading(true);
    setProjectsError('');
    try {
      const data: { projects: ProjectNode[] } = await fetch(
        `/api/folders?folder=${encodeURIComponent(folder.name)}`
      ).then((r) => r.json());
      setFolderProjects(data.projects || []);
      setBrowseFolder(folder);
    } catch { setProjectsError('Could not load projects.'); }
    finally { setFoldersLoading(false); }
  }

  // ── Project / folder actions ─────────────────────────────────────────────

  async function doRenameFolder() {
    if (!renameFolderTarget || !renameFolderValue.trim()) return;
    setProjectsActionBusy(true);
    try {
      const result = await postJson<{ path: string; name: string }>('/api/folders/rename', {
        path: renameFolderTarget.path,
        name: renameFolderValue.trim(),
      });
      if (activeProject?.path === renameFolderTarget.path || activeProject?.path.startsWith(`${renameFolderTarget.path}/`)) {
        const nextPath = activeProject.path.replace(renameFolderTarget.path, result.path);
        setActiveProject({
          ...activeProject,
          customer: result.name,
          path: nextPath,
        });
        setArchitecturePath(`${nextPath}/architecture.json`);
      }
      setRenameFolderTarget(null);
      await loadFolders();
      refreshProjectTree();
    } catch (e: any) { setProjectsError(e.message || 'Rename failed'); }
    finally { setProjectsActionBusy(false); }
  }

  async function doDeleteFolder(folder: FolderNode) {
    setProjectsActionBusy(true);
    try {
      await postJson('/api/folders/delete', { path: folder.path });
      setDeleteTarget(null);
      if (activeProject?.path === folder.path || activeProject?.path.startsWith(`${folder.path}/`)) {
        setActiveProject(null);
        setArchitecture(null);
        setQuestions([]);
        setAnsweredQuestions([]);
        setQuestionAnswers({});
        setPendingComponents([]);
        setPendingAssignments({});
        setArchitectureReview(null);
        setDiagramQuality(null);
        setAutosaveStatus('');
        setProjectActivity(null);
        setStep('upload');
      }
      await loadFolders();
      refreshProjectTree();
    } catch (e: any) { setProjectsError(e.message || 'Delete failed'); }
    finally { setProjectsActionBusy(false); }
  }

  async function doRenameProject() {
    if (!renameTarget || !renameValue.trim()) return;
    setProjectsActionBusy(true);
    try {
      const result = await postJson<{ path: string; name: string }>('/api/projects/rename', {
        path: renameTarget.path,
        name: renameValue.trim(),
      });
      if (activeProject?.path === renameTarget.path) {
        setActiveProject({ ...renameTarget, path: result.path, project: result.name });
        setArchitecturePath(`${result.path}/architecture.json`);
      }
      setRenameTarget(null);
      if (browseFolder) await loadFolderProjects(browseFolder); else await loadFolders();
      refreshProjectTree();
    } catch (e: any) { setProjectsError(e.message || 'Rename failed'); }
    finally { setProjectsActionBusy(false); }
  }

  async function doDeleteProject(node: ProjectNode) {
    setProjectsActionBusy(true);
    try {
      await postJson('/api/projects/delete', { path: node.path });
      setDeleteTarget(null);
      if (activeProject?.path === node.path) {
        setActiveProject(null);
        setArchitecture(null);
        setQuestions([]);
        setAnsweredQuestions([]);
        setQuestionAnswers({});
        setPendingComponents([]);
        setPendingAssignments({});
        setArchitectureReview(null);
        setDiagramQuality(null);
        setAutosaveStatus('');
        setProjectActivity(null);
        setStep('upload');
      }
      if (browseFolder) await loadFolderProjects(browseFolder); else await loadFolders();
      refreshProjectTree();
    } catch (e: any) { setProjectsError(e.message || 'Delete failed'); }
    finally { setProjectsActionBusy(false); }
  }

  async function doDuplicateProject() {
    if (!duplicateTarget || !duplicateName.trim()) return;
    setProjectsActionBusy(true);
    try {
      await postJson('/api/projects/duplicate', { path: duplicateTarget.path, name: duplicateName.trim() });
      setDuplicateTarget(null);
      if (browseFolder) await loadFolderProjects(browseFolder); else await loadFolders();
      refreshProjectTree();
    } catch (e: any) { setProjectsError(e.message || 'Duplicate failed'); }
    finally { setProjectsActionBusy(false); }
  }

  async function doMoveProject() {
    if (!moveTarget || !moveDest) return;
    setProjectsActionBusy(true);
    try {
      const result = await postJson<ProjectNode>('/api/projects/move', { path: moveTarget.path, destFolder: moveDest });
      if (activeProject?.path === moveTarget.path) {
        setActiveProject(result);
        setArchitecturePath(`${result.path}/architecture.json`);
      }
      setMoveTarget(null);
      if (browseFolder) await loadFolderProjects(browseFolder); else await loadFolders();
      refreshProjectTree();
    } catch (e: any) { setProjectsError(e.message || 'Move failed'); }
    finally { setProjectsActionBusy(false); }
  }

  function openProjectsPage() {
    setActiveNav('projects');
    loadFolders();
  }

  async function createCustomerFolder() {
    const customer = newFolderName.trim();
    if (!customer) return;
    setProjectsActionBusy(true);
    setProjectsError('');
    try {
      await postJson('/api/folders', { customer });
      setShowNewFolderModal(false);
      setNewFolderName('');
      await loadFolders();
      refreshProjectTree();
      setStatus('Customer folder created');
    } catch (err) {
      setProjectsError(err instanceof Error ? err.message : 'Failed to create folder');
    } finally {
      setProjectsActionBusy(false);
    }
  }

  async function createProject() {
    // When inside a folder, that folder IS the customer — only need a project name.
    const inFolder = activeNav === 'projects' && browseFolder != null;
    const customer = inFolder ? browseFolder!.name : newCustomerName.trim();
    const project  = newProjectName.trim();
    if (!customer) return;
    if (!project) {
      setError('Project name is required.');
      return;
    }
    setProjectsActionBusy(true);
    try {
      const result = await postJson<ProjectNode>('/api/projects', {
        customer,
        project,
      });
      setShowNewProjectModal(false);
      setNewCustomerName('');
      setNewProjectName('');
      const nextProject = {
        customer: result.customer,
        project: result.project,
        path: result.path,
        hasArchitecture: false,
        isLegacy: false,
      };
      setActiveProject(nextProject);
      setArchitecturePath(`${result.path}/architecture.json`);
      setArchitecture(null);
      setQuestions([]);
      setAnsweredQuestions([]);
      setQuestionAnswers({});
      setPendingComponents([]);
      setPendingAssignments({});
      setDiagramPath('');
      setArchitectureReview(null);
      setDiagramQuality(null);
      setPatternResults([]);
      setChosenPatternState(null);
      setPreviewXml(null);
      setRequirementsText('');
      setRequirementsSaved(false);
      setAutosaveStatus('');
      setProjectActivity(null);
      setProjectName(project);
      if (inFolder) await loadFolderProjects(browseFolder!); else await loadFolders();
      refreshProjectTree();
      setStatus(`Project created: ${result.path}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create project');
    } finally {
      setProjectsActionBusy(false);
    }
  }

  function normalizeSavedQuestions(items: Question[] | string[] | undefined): Question[] {
    return (items || []).map((item) => {
      if (typeof item !== 'string') return item;
      return { area: 'Saved decision', question: item, source: 'rules' };
    });
  }

  async function selectProject(node: ProjectNode) {
    // Reset all intake state so the new project starts completely fresh.
    setActiveProject(node);
    setArchitecturePath(`${node.path}/architecture.json`);
    setArchitecture(null);
    setQuestions([]);
    setAnsweredQuestions([]);
    setQuestionAnswers({});
    setPendingComponents([]);
    setPendingAssignments({});
    setSelectedFiles([]);
    setDiagramPath('');
    setArchitectureReview(null);
    setDiagramQuality(null);
    setPatternResults([]);
    setChosenPatternState(null);
    setPreviewXml(null);
    setMcpEditorOpened(false);
    setMcpDiagramPushed(false);
    setCopiedPrompt('');
    setRequirementsText('');
    setRequirementsSaved(false);
    setProjectActivity(null);
    setStatus('');
    setError('');
    setActiveNav('wizard');
    setStep('upload');
    setProjectName(node.project || node.customer);
    await loadProjectActivity(node);
    if (!node.hasArchitecture) return;
    try {
      const response = await fetch(`/api/project-export?path=${encodeURIComponent(node.path)}`);
      if (!response.ok) throw new Error('Project has no saved architecture yet.');
      const savedArchitecture = await response.json() as Architecture;
      const answered = savedArchitecture.questions?.answered || [];
      const open = normalizeSavedQuestions(savedArchitecture.questions?.open);
      setArchitecture(savedArchitecture);
      setAnsweredQuestions(answered);
      setQuestions(mergeQuestions([], open, answered));
      setProjectName(savedArchitecture.project?.name || node.project || node.customer);
      await runArchitectureReview(savedArchitecture, requirementsText);
      setStep('review');
      setStatus('Project loaded');
      await loadProjectActivity(node);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Project load failed');
    }
  }

  async function startMoveProject(node: ProjectNode) {
    setMoveTarget(node);
    setMoveDest('');
    if (folders.length === 0) {
      try {
        const data: { folders: FolderNode[] } = await fetch('/api/folders').then((r) => r.json());
        setFolders(data.folders || []);
      } catch { setProjectsError('Could not load folders.'); }
    }
  }

  function exportArchitecture() {
    if (!activeProject) return;
    const a = document.createElement('a');
    a.href = `/api/project-export?path=${encodeURIComponent(activeProject.path)}`;
    a.download = 'architecture.json';
    a.click();
  }

  async function openRestorePreview(snapshot: ProjectSnapshot) {
    if (!activeProject) return;
    setRestoreTarget(snapshot);
    setRestorePreview(null);
    setRestorePreviewBusy(true);
    setProjectsError('');
    try {
      const preview = await postJson<RestorePreview>('/api/projects/restore-preview', {
        path: activeProject.path,
        snapshotId: snapshot.id,
      });
      setRestorePreview(preview);
    } catch (err) {
      setProjectsError(err instanceof Error ? err.message : 'Restore preview failed');
    } finally {
      setRestorePreviewBusy(false);
    }
  }

  function closeRestoreModal() {
    setRestoreTarget(null);
    setRestorePreview(null);
    setRestorePreviewBusy(false);
  }

  async function restoreProjectSnapshot() {
    if (!activeProject || !restoreTarget) return;
    setRestoreBusy(true);
    setProjectsError('');
    try {
      const result = await postJson<{
        architecture: Architecture;
        outputPath: string;
        restoredFrom: { label: string; createdAt: string };
      }>('/api/projects/restore', {
        path: activeProject.path,
        snapshotId: restoreTarget.id,
      });
      const restoredArchitecture = result.architecture;
      const answered = restoredArchitecture.questions?.answered || [];
      const open = normalizeSavedQuestions(restoredArchitecture.questions?.open);
      setArchitecture(restoredArchitecture);
      setArchitecturePath(result.outputPath);
      setAnsweredQuestions(answered);
      setQuestions(mergeQuestions([], open, answered));
      setProjectName(restoredArchitecture.project?.name || activeProject.project || activeProject.customer);
      setDiagramQuality(null);
      setPreviewXml(null);
      setMcpDiagramPushed(false);
      setAutosaveStatus(`Restored ${formatActivityDate(result.restoredFrom.createdAt)}`);
      closeRestoreModal();
      await runArchitectureReview(restoredArchitecture, requirementsText);
      await loadProjectActivity(activeProject);
      setStep('review');
      setActiveNav('wizard');
      setStatus(`Restored restore point: ${result.restoredFrom.label}`);
    } catch (err) {
      setProjectsError(err instanceof Error ? err.message : 'Restore failed');
    } finally {
      setRestoreBusy(false);
    }
  }

  async function importArchitecture(file: File) {
    if (!activeProject) return;
    const body = new FormData();
    body.append('path', activeProject.path);
    body.append('architecture', file, 'architecture.json');
    try {
      await postForm('/api/project-import', body);
      await selectProject({ ...activeProject, hasArchitecture: true });
      refreshProjectTree();
      setStatus('Architecture imported');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Import failed');
    }
  }

  // ── Intake ───────────────────────────────────────────────────────────────────

  const summary = useMemo(() => {
    if (!architecture) return [];
    return Object.entries(architecture.ibm_cloud)
      .filter(([, v]) => Array.isArray(v))
      .map(([key, value]) => ({ key, count: (value as unknown[]).length }))
      .filter((item) => item.count > 0);
  }, [architecture]);

  const answeredKeys = useMemo(
    () => new Set(answeredQuestions.map((a) => a.question)),
    [answeredQuestions],
  );

  const openQuestions = useMemo(
    () => questions.filter((q) => !answeredKeys.has(q.question)),
    [answeredKeys, questions],
  );

  const restoreSnapshots = useMemo(() => {
    const snapshots = projectActivity?.snapshots || [];
    if (restoreFilter === 'all') return snapshots;
    if (restoreFilter === 'milestones') {
      return snapshots.filter((snapshot) => snapshot.eventType !== 'autosave');
    }
    return snapshots.filter((snapshot) => restoreFilterForEvent(snapshot.eventType) === restoreFilter);
  }, [projectActivity?.snapshots, restoreFilter]);

  async function uploadAndRunIntake() {
    setBusy(true);
    setError('');
    setStatus(
      settings.mode === 'ollama'
        ? `Uploading files and running AI extraction (${settings.ollamaModel}) — this may take up to a minute…`
        : 'Uploading and parsing files…'
    );
    try {
      const body = new FormData();
      body.append('projectName', projectName || 'Customer Architecture');
      body.append('mode', settings.mode);
      body.append('ollamaModel', settings.ollamaModel);
      if (activeProject && !activeProject.isLegacy) {
        body.append('customer', activeProject.customer);
        if (activeProject.project) body.append('project', activeProject.project);
      }
      selectedFiles.forEach((file) => body.append('files', file));
      const payload = await postForm<{
        architecture: Architecture;
        questions: Question[];
        inputPath: string;
        outputPath: string;
        files: string[];
        fileRoles?: FileRole[];
        answeredQuestions?: AnsweredQuestion[];
        pendingComponents?: PendingComponent[];
      }>('/api/upload-intake', body);
      // Always reset answered/question state on a fresh intake run so answers
      // from previous projects don't bleed into the new one.
      const answered: AnsweredQuestion[] = payload.answeredQuestions || [];
      setAnsweredQuestions(answered);
      setQuestionAnswers({});
      setArchitecture(payload.architecture);
      setQuestions(mergeQuestions([], payload.questions, answered));
      setArchitecturePath(payload.outputPath);
      setDiagramPath('');
      setFileRoles(payload.fileRoles || []);
      if (payload.pendingComponents?.length) {
        setPendingComponents(payload.pendingComponents);
      }
      setStatus(`Parsed ${payload.files.length} file${payload.files.length === 1 ? '' : 's'} — ${payload.questions.length} design question${payload.questions.length === 1 ? '' : 's'} found`);
      await runArchitectureReview(payload.architecture, requirementsText);
      setStep('review');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
      setStatus('');
    } finally {
      setBusy(false);
    }
  }

  function addFiles(files: File[]) {
    const valid = files.filter((f) =>
      ACCEPTED_FILE_TYPES.some((ext) => f.name.toLowerCase().endsWith(ext))
    );
    setSelectedFiles((current) => {
      const existing = new Set(current.map((f) => `${f.name}:${f.size}`));
      const next = [...current];
      valid.forEach((f) => {
        if (!existing.has(`${f.name}:${f.size}`)) next.push(f);
      });
      return next;
    });
  }

  function removeFile(name: string) {
    setSelectedFiles((current) => current.filter((f) => f.name !== name));
  }

  // ── Questions ────────────────────────────────────────────────────────────────

  function updateAnswer(question: Question, answer: string) {
    setQuestionAnswers((current) => ({ ...current, [questionKey(question)]: answer }));
  }

  async function saveAnswer(question: Question) {
    const key = questionKey(question);
    const answer = questionAnswers[key]?.trim();
    if (!answer) { setError('Write an answer before saving.'); return; }
    setError('');
    const entry: AnsweredQuestion = {
      area: question.area, question: question.question,
      answer, source: 'architect', timestamp: new Date().toISOString(),
    };
    setAnsweredQuestions((current) => [...current, entry]);
    setStatus('Answer saved');
    try {
      const payload = await postJson<{ architecture?: Architecture }>('/api/answer', {
        architecturePath,
        area: question.area,
        question: question.question,
        answer,
        source: 'architect',
      });
      if (payload.architecture) {
        setArchitecture(payload.architecture);
        await runArchitectureReview(payload.architecture, requirementsText);
      }
    } catch { console.warn('Failed to persist answer'); }
  }

  async function acceptCoaching(question: Question) {
    const answer = question.guidance || question.question;
    setQuestionAnswers((current) => ({ ...current, [questionKey(question)]: answer }));
    const entry: AnsweredQuestion = {
      area: question.area, question: question.question,
      answer, source: 'coaching', timestamp: new Date().toISOString(),
    };
    setAnsweredQuestions((current) => [...current, entry]);
    setError('');
    setStatus('Best-practice guidance accepted');
    try {
      const payload = await postJson<{ architecture?: Architecture }>('/api/answer', {
        architecturePath,
        area: question.area,
        question: question.question,
        answer,
        source: 'coaching',
      });
      if (payload.architecture) {
        setArchitecture(payload.architecture);
        await runArchitectureReview(payload.architecture, requirementsText);
      }
    } catch { console.warn('Failed to persist coaching answer'); }
  }

  async function saveRequirements(text: string, source: 'text' | 'file', filename = '') {
    if (!text.trim()) return;
    try {
      const payload = await postJson<{ architecture?: Architecture }>('/api/requirements', {
        architecturePath,
        requirements: text.trim(),
        source,
        filename,
      });
      setRequirementsSaved(true);
      if (payload.architecture) {
        setArchitecture(payload.architecture);
        await runArchitectureReview(payload.architecture, text.trim());
      } else if (architecture) {
        await runArchitectureReview(architecture, text.trim());
      }
      setTimeout(() => setRequirementsSaved(false), 3000);
    } catch { /* non-fatal — requirements are still shown in the UI */ }
  }

  async function loadRequirementsFromFile(file: File) {
    const text = await file.text();
    setRequirementsText(text);
    await saveRequirements(text, 'file', file.name);
  }

  async function confirmComponents(
    confirmed: { id: string; name: string; key: string; purpose: string; notes: string }[],
    discarded: string[],
  ) {
    setBusy(true);
    try {
      await postJson('/api/confirm-components', {
        architecturePath,
        confirmed: confirmed.map(({ name, key, purpose, notes }) => ({ name, key, purpose, notes })),
        discarded,
      });
      setPendingComponents((current) =>
        current.filter((c) => !discarded.includes(c.id) && !confirmed.find((cf) => cf.id === c.id))
      );
      setStatus('Components confirmed');
      if (architecture) await runArchitectureReview(architecture, requirementsText);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to confirm components');
    } finally {
      setBusy(false);
    }
  }

  // ── Pattern matching ─────────────────────────────────────────────────────────

  async function runArchitectureReview(archOverride?: Architecture | null, requirementsOverride?: string) {
    const arch = archOverride ?? architecture;
    if (!arch) return;
    setArchitectureReviewBusy(true);
    setError('');
    try {
      const review = await postJson<ArchitectureReview>('/api/architecture-review', {
        architecture: arch,
        requirements: requirementsOverride ?? requirementsText,
      });
      setArchitectureReview(review);
      const ranked = [
        review.recommendedPattern,
        ...(review.alternativePatterns || []),
      ].filter(Boolean) as PatternResult[];
      setPatternResults(ranked);
      if (!chosenPattern && review.recommendedPattern) {
        setChosenPatternState(review.recommendedPattern);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Architecture review failed');
    } finally {
      setArchitectureReviewBusy(false);
    }
  }

  async function runPatternMatch() {
    if (!architecture) return;
    setPatternBusy(true);
    setError('');
    try {
      const payload = await postJson<{ patterns: PatternResult[]; best: PatternResult | null }>(
        '/api/pattern-match',
        { architecture, requirements: requirementsText },
      );
      setPatternResults(payload.patterns || []);
      // Auto-select top match if not already chosen
      if (!chosenPattern && payload.best) {
        setChosenPatternState(payload.best);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Pattern match failed');
    } finally {
      setPatternBusy(false);
    }
  }

  async function confirmPattern(pattern: PatternResult) {
    setChosenPatternState(pattern);
    try {
      await postJson('/api/set-pattern', {
        architecturePath,
        patternId: pattern.id,
        patternName: pattern.name,
        score: pattern.score,
      });
      setStatus(`Pattern set: ${pattern.name}`);
    } catch (err) {
      // Non-fatal — pattern is still set in local state
      console.warn('set-pattern failed:', err);
    }
  }

  // ── Diagram ──────────────────────────────────────────────────────────────────

  async function generateDiagram() {
    setBusy(true);
    setError('');
    setStatus('Generating diagram…');
    try {
      const payload = await postJson<{ outputPath: string }>('/api/generate-drawio', {
        architecturePath, diagramType, mode: settings.mode, ollamaModel: settings.ollamaModel,
        outputPath: `outputs/network-picasso-${diagramType}.drawio`,
      });
      setDiagramPath(payload.outputPath);
      setStatus('Draw.io file saved to ' + payload.outputPath);
      await runDiagramQuality();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Diagram generation failed');
      setStatus('');
    } finally {
      setBusy(false);
    }
  }

  async function runDiagramQuality() {
    if (!architecture) return;
    setDiagramQualityBusy(true);
    setError('');
    try {
      const review = await postJson<DiagramQualityReview>('/api/diagram-quality', {
        architecturePath,
        diagramType,
      });
      setDiagramQuality(review);
      setArchitecture((current) => current ? {
        ...current,
        quality: {
          ...(current.quality || {}),
          lastReview: {
            score: review.score,
            status: review.status,
            diagramType,
            summary: review.summary,
            findingCount: review.findings.length,
            timestamp: new Date().toISOString(),
          },
        },
      } : current);
      await loadProjectActivity();
      setStatus(`Diagram quality analyzed: ${review.score}/100 (${review.status})`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Diagram quality analysis failed');
    } finally {
      setDiagramQualityBusy(false);
    }
  }

  async function copyDiagramXml() {
    setBusy(true);
    try {
      const response = await fetch('/api/drawio-xml', {
        method: 'POST', headers: API_HEADERS,
        body: JSON.stringify({ architecturePath, diagramType }),
      });
      if (!response.ok) throw new Error('Failed to get XML');
      const xml = await response.text();
      await navigator.clipboard.writeText(xml);
      setStatus('XML copied to clipboard');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Copy failed');
    } finally {
      setBusy(false);
    }
  }

  async function openInDiagramsNet() {
    if (!architecture) return;
    setBusy(true);
    setError('');
    try {
      const response = await fetch('/api/drawio-xml', {
        method: 'POST', headers: API_HEADERS,
        body: JSON.stringify({ architecturePath, diagramType }),
      });
      if (!response.ok) throw new Error('Failed to get XML');
      const xml = await response.text();
      // Store the XML so the message listener can deliver it once the popup fires
      // its 'init' event — same protocol as the inline preview (Option D).
      // Do NOT use noopener — it nullifies event.source in the message listener,
      // making it impossible to postMessage back to the popup.
      pendingPopupXml.current = xml;
      const popup = window.open(
        'https://embed.diagrams.net/?embed=1&proto=json&spin=1&analytics=0',
        'drawio-popup',
        'width=1200,height=800',
      );
      popupWindowRef.current = popup;
      setStatus('Opening diagrams.net — diagram will load automatically when the editor is ready.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Open failed');
    } finally {
      setBusy(false);
    }
  }

  function openXmlInDiagramsNet(xml: string, statusMessage: string) {
    pendingPopupXml.current = xml;
    const popup = window.open(
      'https://embed.diagrams.net/?embed=1&proto=json&spin=1&analytics=0',
      'drawio-popup',
      'width=1200,height=800',
    );
    popupWindowRef.current = popup;
    setStatus(statusMessage);
  }

  async function loadPreview() {
    if (!architecture) return;
    setBusy(true);
    setError('');
    try {
      const response = await fetch('/api/drawio-xml', {
        method: 'POST', headers: API_HEADERS,
        body: JSON.stringify({ architecturePath, diagramType }),
      });
      if (!response.ok) throw new Error('Failed to get XML');
      const xml = await response.text();
      setPreviewXml(xml);
      setPreviewReady(false); // iframe will fire init event when loaded
      setStatus('Preview loaded');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Preview failed');
    } finally {
      setBusy(false);
    }
  }

  async function openInMcpEditor() {
    if (!architecture) return;
    setBusy(true);
    setMcpStatus('');
    setError('');
    try {
      const result = await postJson<{ ok: boolean; editorUrl: string }>(
        '/api/drawio-mcp-open',
        { architecturePath, diagramType },
      );
      setMcpRunning(true);
      setMcpDiagramPushed(true);
      // Focus the already-open editor tab rather than opening a new one each time.
      // Only open a new tab if this is the first successful push (tab not yet open).
      if (!mcpRunning) {
        window.open(BROWSER_MCP_EDITOR_URL, 'drawio-mcp-editor');
        setMcpEditorOpened(true);
      }
      setMcpStatus(`Diagram pushed to the live editor (${diagramType})`);
      setStatus(`Diagram is open in the live Draw.io editor at ${BROWSER_MCP_EDITOR_URL}`);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'MCP open failed';
      setMcpStatus(msg);
      setError(msg);
    } finally {
      setBusy(false);
    }
  }

  async function saveAndOpenAllPages() {
    const payload = await postJson<{ outputPath: string; xml?: string }>(
      '/api/drawio-multipage',
      { architecturePath, outputPath: 'outputs/network-picasso-all.drawio', includeXml: true },
    );
    setDiagramPath(payload.outputPath);
    if (payload.xml) {
      const drawioUrl = `https://app.diagrams.net/#R${encodeDrawioUrlPayload(payload.xml)}`;
      window.open(drawioUrl, 'drawio-all-pages');
      setStatus(
        `Four-page Draw.io file saved to ${payload.outputPath}; opening as a multipage diagrams.net file.`,
      );
    } else {
      setStatus(`Four-page Draw.io file saved to ${payload.outputPath}`);
    }
  }

  async function generateAllPages() {
    if (!architecture) return;
    setBusy(true);
    setMcpStatus('');
    setError('');
    if (mcpRunning) {
      // Push all architecture diagrams to the MCP editor as pages.
      try {
        const result = await postJson<{ ok: boolean; editorUrl: string; pages: number }>(
          '/api/drawio-mcp-all-pages',
          { architecturePath },
        );
        window.open(BROWSER_MCP_EDITOR_URL, 'drawio-mcp-editor');
        setMcpEditorOpened(true);
        setMcpDiagramPushed(true);
        setStatus(`All ${result.pages} diagram pages opened in MCP editor`);
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Multi-page MCP open failed';
        setMcpStatus(msg);
        setMcpRunning(false);
        try {
          await saveAndOpenAllPages();
          setMcpStatus(`${msg}; opened the all-pages file in diagrams.net instead.`);
        } catch (fallbackErr) {
          setError(fallbackErr instanceof Error ? fallbackErr.message : msg);
        }
      } finally {
        setBusy(false);
      }
    } else {
      // Fallback: save a multi-page .drawio file and open it in diagrams.net.
      try {
        await saveAndOpenAllPages();
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Multi-page export failed');
      } finally {
        setBusy(false);
      }
    }
  }

  async function probeMcpEditor() {
    try {
      const d = await fetch('/api/drawio-mcp/health').then((r) => r.json()) as { running: boolean };
      setMcpRunning(d.running);
      setMcpStatus(d.running ? `MCP editor service is running. Open ${BROWSER_MCP_EDITOR_URL} before pushing a diagram.` : 'MCP editor service not detected');
    } catch {
      setMcpRunning(false);
      setMcpStatus('MCP editor not detected at localhost:4000');
    }
  }

  function openMcpEditorTab() {
    window.open(BROWSER_MCP_EDITOR_URL, 'drawio-mcp-editor');
    setMcpEditorOpened(true);
    setStatus(`MCP editor opened at ${BROWSER_MCP_EDITOR_URL}`);
  }

  async function copyBobPrompt(label: string, prompt: string) {
    try {
      await navigator.clipboard.writeText(prompt);
      setCopiedPrompt(label);
      setStatus(`Bob prompt copied: ${label}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Prompt copy failed');
    }
  }

  // ── Settings ─────────────────────────────────────────────────────────────────

  async function testOllamaConnection() {
    setConnectionStatus('idle');
    try {
      const data = await fetch('/api/ollama/models').then((r) => r.json());
      const models: string[] = data.models || [];
      setOllamaModels(models);
      setConnectionStatus(models.length > 0 ? 'ok' : 'fail');
    } catch { setConnectionStatus('fail'); }
  }

  async function saveSettings() {
    try {
      await postJson('/api/settings', settings);
      setSettingsStatus('Settings saved');
    } catch { setSettingsStatus('Failed to save'); }
  }

  // Listen for diagrams.net embed init event.
  // Handles both the inline preview iframe (Option D) and popup windows (Option C).
  useEffect(() => {
    function handleMessage(event: MessageEvent) {
      if (event.origin !== 'https://embed.diagrams.net') return;
      try {
        const msg = typeof event.data === 'string' ? JSON.parse(event.data) : event.data;
        if (msg?.event === 'init') {
          // Option D — inline preview iframe
          if (event.source === previewRef.current?.contentWindow) {
            setPreviewReady(true);
            return;
          }
          // Option C — popup window: deliver pending XML then clear it.
          // Use the stored window ref — event.source is only reliable when
          // the popup was opened without noopener.
          const xml = pendingPopupXml.current;
          const target = popupWindowRef.current ?? (event.source as Window | null);
          if (xml && target) {
            target.postMessage(
              JSON.stringify({ action: 'load', xml }),
              'https://embed.diagrams.net',
            );
            pendingPopupXml.current = null;
            popupWindowRef.current = null;
            setStatus('Diagram loaded in diagrams.net editor.');
          }
        }
      } catch { /* ignore */ }
    }
    window.addEventListener('message', handleMessage);
    return () => window.removeEventListener('message', handleMessage);
  }, []);

  // ── Step helpers ─────────────────────────────────────────────────────────────

  const stepIndex = STEPS.indexOf(step);

  function InfoTip({ text }: { text: string }) {
    return (
      <Tooltip label={text} align="right">
        <button type="button" className="info-tip" aria-label="More information">
          <Information size={16} />
        </button>
      </Tooltip>
    );
  }

  function formatActivityDate(value?: string) {
    if (!value) return 'Not saved yet';
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return value;
    return parsed.toLocaleString([], {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    });
  }

  function formatBytes(value: number) {
    if (!value) return '0 KB';
    if (value < 1024) return `${value} B`;
    return `${Math.round(value / 1024)} KB`;
  }

  // ── Render ───────────────────────────────────────────────────────────────────
  const bobPromptsByCategory = bobPromptTemplates(diagramType).reduce(
    (groups, prompt) => {
      const list = groups.get(prompt.category) || [];
      list.push(prompt);
      groups.set(prompt.category, list);
      return groups;
    },
    new Map<string, ReturnType<typeof bobPromptTemplates>>(),
  );
  const bobPromptRecommendation = recommendedBobPrompt(diagramQuality);

  return (
    <>
      <Header aria-label="Network Picasso">
        <HeaderName href="#" prefix="IBM Cloud">
          Network Picasso
        </HeaderName>
      </Header>

      <SideNav aria-label="Workspace navigation" expanded isPersistent>
        <SideNavItems>
          <SideNavLink
            renderIcon={Add}
            isActive={activeNav === 'projects'}
            onClick={openProjectsPage}
          >
            Projects
          </SideNavLink>
          {/* Wizard steps */}
          <SideNavLink
            renderIcon={DocumentImport}
            isActive={activeNav === 'wizard' && step === 'upload'}
            onClick={() => { setActiveNav('wizard'); setStep('upload'); }}
          >
            1 · Upload files
          </SideNavLink>
          <SideNavLink
            renderIcon={IbmCloud}
            isActive={activeNav === 'wizard' && step === 'review'}
            onClick={() => { setActiveNav('wizard'); setStep('review'); }}
          >
            2 · Review model
          </SideNavLink>
          <SideNavLink
            renderIcon={ListChecked}
            isActive={activeNav === 'wizard' && step === 'questions'}
            onClick={() => { setActiveNav('wizard'); setStep('questions'); }}
          >
            3 · Questions {openQuestions.length > 0 && `(${openQuestions.length})`}
          </SideNavLink>
          <SideNavLink
            renderIcon={Diagram}
            isActive={activeNav === 'wizard' && step === 'diagram'}
            onClick={() => { setActiveNav('wizard'); setStep('diagram'); }}
          >
            4 · Diagram
          </SideNavLink>
          <SideNavLink
            renderIcon={Settings}
            isActive={activeNav === 'settings'}
            onClick={() => setActiveNav('settings')}
          >
            Settings
          </SideNavLink>
          {/* Active project indicator */}
          {activeProject && activeNav === 'wizard' && (
            <SideNavLink renderIcon={IbmCloud} isActive={false} style={{ opacity: 0.75 }}>
              {(activeProject.project || activeProject.customer) + (autosaveStatus ? ` · ${autosaveStatus}` : '')}
            </SideNavLink>
          )}
        </SideNavItems>
      </SideNav>

      {/* New Customer Folder Modal */}
      <Modal
        open={showNewFolderModal}
        modalHeading="New customer folder"
        primaryButtonText={projectsActionBusy ? 'Creating...' : 'Create folder'}
        secondaryButtonText="Cancel"
        primaryButtonDisabled={projectsActionBusy || !newFolderName.trim()}
        onRequestSubmit={createCustomerFolder}
        onRequestClose={() => { setShowNewFolderModal(false); setNewFolderName(''); }}
        onSecondarySubmit={() => { setShowNewFolderModal(false); setNewFolderName(''); }}
      >
        <Stack gap={5}>
          <TextInput
            id="new-folder-name"
            labelText="Customer name"
            placeholder="Acme Bank"
            value={newFolderName}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNewFolderName(e.target.value)}
          />
          <p style={{ fontSize: '0.875rem', color: '#525252' }}>
            Creates a top-level customer folder. Add one or more project workspaces inside it.
          </p>
        </Stack>
      </Modal>

      {/* New Project Modal */}
      <Modal
        open={showNewProjectModal}
        modalHeading={activeNav === 'projects' && browseFolder ? `New project in ${browseFolder.name}` : 'New project'}
        primaryButtonText={projectsActionBusy ? 'Creating...' : 'Create project'}
        secondaryButtonText="Cancel"
        primaryButtonDisabled={projectsActionBusy || !newProjectName.trim() || (!(activeNav === 'projects' && browseFolder) && !newCustomerName.trim())}
        onRequestSubmit={createProject}
        onRequestClose={() => { setShowNewProjectModal(false); setNewCustomerName(''); setNewProjectName(''); }}
        onSecondarySubmit={() => { setShowNewProjectModal(false); setNewCustomerName(''); setNewProjectName(''); }}
      >
        <Stack gap={5}>
          {!(activeNav === 'projects' && browseFolder) && (
            <TextInput id="new-customer-name" labelText="Customer name" placeholder="Acme Bank"
              value={newCustomerName}
              onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNewCustomerName(e.target.value)} />
          )}
          <TextInput id="new-project-name"
            labelText="Project name"
            placeholder="Q1 Modernisation"
            value={newProjectName}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNewProjectName(e.target.value)} />
          {!(activeNav === 'projects' && browseFolder) && (
            <p style={{ fontSize: '0.875rem', color: '#525252' }}>
              Creates a customer folder with a project subfolder.
            </p>
          )}
        </Stack>
      </Modal>

      <Content className="app-content">
        <Grid className="workspace" fullWidth>

          {/* ── Page header ── */}
          <Column sm={4} md={8} lg={16}>
            <div className="page-heading">
              <div>
                <p className="eyebrow">IBM Cloud architecture workbench</p>
                <h1>
                  {activeNav === 'settings' ? 'Settings'
                    : activeNav === 'projects' ? 'Projects'
                    : STEP_LABELS[step]}
                </h1>
                {activeNav === 'wizard' && (
                  <p className="eyebrow" style={{ marginTop: '0.25rem' }}>{STEP_DESCRIPTIONS[step]}</p>
                )}
                {activeNav === 'wizard' && activeProject && (
                  <p className="eyebrow" style={{ marginTop: '0.25rem' }}>
                    Project: {activeProject.customer}{activeProject.project ? ` / ${activeProject.project}` : ''}
                    {autosaveStatus && ` · ${autosaveStatus}`}
                  </p>
                )}
                {activeNav === 'projects' && (
                  <p className="eyebrow" style={{ marginTop: '0.25rem' }}>
                    {browseFolder ? `Customer: ${browseFolder.name}` : 'All customer folders'}
                  </p>
                )}
              </div>
              <div className="status-line">
                {busy && <InlineLoading description={status} />}
                {!busy && status && <Tag type="green">{status}</Tag>}
                {error && <Tag type="red">{error}</Tag>}
              </div>
            </div>

            {/* Progress indicator — only shown in wizard mode */}
            {activeNav === 'wizard' && (
              <div className="progress-bar">
                <ProgressIndicator currentIndex={stepIndex} spaceEqually>
                  {STEPS.map((s) => (
                    <ProgressStep
                      key={s}
                      label={STEP_LABELS[s]}
                      description={STEP_DESCRIPTIONS[s]}
                      onClick={() => setStep(s)}
                    />
                  ))}
                </ProgressIndicator>
              </div>
            )}
          </Column>

          {/* ══════════════════════════════════════════════════════════════════
              PROJECTS PAGE — folder browser
          ══════════════════════════════════════════════════════════════════ */}
          {activeNav === 'projects' && (
            <Column sm={4} md={8} lg={12}>
              {projectsError && (
                <InlineNotification kind="error" title={projectsError} lowContrast
                  style={{ marginBottom: '1rem' }} onCloseButtonClick={() => setProjectsError('')} />
              )}

              {/* Toolbar */}
              <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.25rem', flexWrap: 'wrap', alignItems: 'center' }}>
                {browseFolder && (
                  <Button kind="ghost" size="sm" onClick={() => loadFolders()}>
                    ← All folders
                  </Button>
                )}
                {browseFolder ? (
                  <Button size="sm" renderIcon={Add} onClick={() => setShowNewProjectModal(true)}>
                    New project in this folder
                  </Button>
                ) : (
                  <>
                    <Button size="sm" renderIcon={Add} onClick={() => setShowNewFolderModal(true)}>
                      New customer folder
                    </Button>
                    <Button kind="secondary" size="sm" renderIcon={Add} onClick={() => setShowNewProjectModal(true)}>
                      New project with customer
                    </Button>
                  </>
                )}
              </div>

              {foldersLoading && <InlineLoading description="Loading…" style={{ marginBottom: '1rem' }} />}

              {/* ── Root view: show folders ── */}
              {!browseFolder && !foldersLoading && (
                <>
                  {folders.length === 0 ? (
                    <Tile className="panel" style={{ textAlign: 'center', padding: '2.5rem 1rem' }}>
                      <IbmCloud size={48} style={{ color: '#a8a8a8', marginBottom: '0.75rem' }} />
                      <p style={{ fontWeight: 600, marginBottom: '0.5rem' }}>No projects yet</p>
                      <p style={{ color: '#525252', fontSize: '0.875rem' }}>
                        Create a customer folder to start. Each folder can hold one or more project workspaces.
                      </p>
                    </Tile>
                  ) : (
                    <div className="project-browser-list">
                      {folders.map((folder) => (
                        <div key={folder.path}
                          className="project-browser-row folder-row"
                          onClick={() => loadFolderProjects(folder)}
                          role="button" tabIndex={0}
                          onKeyDown={(e) => e.key === 'Enter' && loadFolderProjects(folder)}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', minWidth: 0 }}>
                            <IbmCloud size={20} style={{ color: '#0043ce', flexShrink: 0 }} />
                            <div>
                              <p className="project-browser-name" style={{ color: '#0043ce' }}>{folder.name}</p>
                              <p className="project-browser-meta">
                                {folder.projectCount} project{folder.projectCount !== 1 ? 's' : ''}
                                {folder.childCount > 0 && ` · ${folder.childCount} sub-folder${folder.childCount !== 1 ? 's' : ''}`}
                              </p>
                            </div>
                          </div>
                          <div onClick={(e) => e.stopPropagation()}>
                            <OverflowMenu aria-label="Folder actions" size="sm" flipped>
                              <OverflowMenuItem itemText="Rename folder"
                                onClick={() => { setRenameFolderTarget(folder); setRenameFolderValue(folder.name); }} />
                              <OverflowMenuItem itemText="Delete folder" isDelete hasDivider
                                onClick={() => setDeleteTarget({ kind: 'folder', node: folder })} />
                            </OverflowMenu>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}

              {/* ── Folder view: show projects inside ── */}
              {browseFolder && !foldersLoading && (
                <>
                  {folderProjects.length === 0 ? (
                    <Tile className="panel" style={{ textAlign: 'center', padding: '2.5rem 1rem' }}>
                      <p style={{ fontWeight: 600, marginBottom: '0.5rem' }}>No projects in {browseFolder.name}</p>
                      <p style={{ color: '#525252', fontSize: '0.875rem' }}>
                        Use &quot;New project in this folder&quot; above to add one.
                      </p>
                    </Tile>
                  ) : (
                    <div className="project-browser-list">
                      {folderProjects.map((node) => (
                        <div key={node.path}
                          className="project-browser-row"
                          onClick={() => { selectProject(node); setActiveNav('wizard'); }}
                          role="button" tabIndex={0}
                          onKeyDown={(e) => e.key === 'Enter' && (() => { selectProject(node); setActiveNav('wizard'); })()}
                        >
                          <div>
                            <p className="project-browser-name">{node.project || node.customer}</p>
                            <p className="project-browser-meta">
                              {node.hasArchitecture ? '✓ Has architecture' : 'No architecture yet'}
                              {activeProject?.path === node.path && ' · Active'}
                            </p>
                          </div>
                          <div onClick={(e) => e.stopPropagation()}>
                            <OverflowMenu aria-label="Project actions" size="sm" flipped>
                              <OverflowMenuItem itemText="Open project"
                                onClick={() => { selectProject(node); setActiveNav('wizard'); }} />
                              <OverflowMenuItem itemText="Rename project"
                                onClick={() => { setRenameTarget(node); setRenameValue(node.project || node.customer); }} />
                              <OverflowMenuItem itemText="Duplicate project"
                                onClick={() => { setDuplicateTarget(node); setDuplicateName(`${node.project || node.customer}-copy`); }} />
                              <OverflowMenuItem itemText="Move to another folder"
                                onClick={() => startMoveProject(node)} />
                              <OverflowMenuItem itemText="Delete project" isDelete hasDivider
                                onClick={() => setDeleteTarget({ kind: 'project', node })} />
                            </OverflowMenu>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}
            </Column>
          )}

          {activeNav === 'projects' && (
            <Column sm={4} md={8} lg={4}>
              <Tile className="panel project-activity-panel">
                <Stack gap={5}>
                  <div className="step-header">
                    <h2>Project activity</h2>
                    <InfoTip text="Shows the active project's autosave status, architecture JSON location, optional Postgres sync status, latest diagram quality score, and recent project events." />
                  </div>

                  {!activeProject ? (
                    <p className="panel-copy">
                      Open a project to see autosave, quality, and recovery details.
                    </p>
                  ) : (
                    <>
                      <div className="project-activity-summary">
                        <strong>{activeProject.project || activeProject.customer}</strong>
                        <span>{activeProject.customer}{activeProject.project ? ` / ${activeProject.project}` : ''}</span>
                        {autosaveStatus && <Tag type={autosaveStatus.includes('failed') ? 'red' : 'green'} size="sm">{autosaveStatus}</Tag>}
                      </div>

                      <div className="project-activity-actions">
                        <Button
                          kind="secondary"
                          size="sm"
                          renderIcon={Renew}
                          onClick={() => loadProjectActivity()}
                          disabled={projectActivityBusy || activeProject.isLegacy}
                        >
                          {projectActivityBusy ? 'Refreshing...' : 'Refresh activity'}
                        </Button>
                        <Button
                          kind="ghost"
                          size="sm"
                          renderIcon={Download}
                          onClick={exportArchitecture}
                          disabled={!activeProject.hasArchitecture}
                        >
                          Export JSON
                        </Button>
                      </div>

                      {projectActivity?.file && (
                        <div className="project-activity-facts">
                          <div>
                            <span>Architecture file</span>
                            <code>{projectActivity.file.architecturePath}</code>
                          </div>
                          <div>
                            <span>Last file save</span>
                            <strong>{formatActivityDate(projectActivity.file.architectureModifiedAt)}</strong>
                          </div>
                          <div>
                            <span>File size</span>
                            <strong>{formatBytes(projectActivity.file.architectureSize)}</strong>
                          </div>
                          <div>
                            <span>Postgres</span>
                            <Tag type={projectActivity.persistence.connected ? 'green' : 'gray'} size="sm">
                              {projectActivity.persistence.connected ? 'Connected' : 'Not connected'}
                            </Tag>
                          </div>
                        </div>
                      )}

                      {architecture?.quality?.lastReview && (
                        <div className="project-activity-quality">
                          <span>Latest quality score</span>
                          <strong>{architecture.quality.lastReview.score}/100 · {architecture.quality.lastReview.status}</strong>
                          <p>{architecture.quality.lastReview.summary}</p>
                        </div>
                      )}

                      <div className="project-restore-points">
                        <div className="project-restore-header">
                          <span className="advisor-label">Restore points</span>
                          {projectActivity?.persistence.connected && (
                            <Tag type="cool-gray" size="sm">
                              {restoreSnapshots.length}/{(projectActivity.snapshots || []).length}
                            </Tag>
                          )}
                        </div>
                        {!projectActivity?.persistence.connected && (
                          <p className="panel-copy">Connect Postgres to keep recoverable architecture restore points.</p>
                        )}
                        {projectActivity?.persistence.connected && !projectActivityBusy && (projectActivity.snapshots || []).length === 0 && (
                          <p className="panel-copy">No restore points yet. Intake, quality checks, pattern changes, and periodic autosaves create them.</p>
                        )}
                        {projectActivity?.persistence.connected && (projectActivity?.snapshots || []).length > 0 && (
                          <Select
                            id="restore-filter-select"
                            labelText="Timeline filter"
                            size="sm"
                            value={restoreFilter}
                            onChange={(event: React.ChangeEvent<HTMLSelectElement>) => setRestoreFilter(event.target.value as RestoreFilter)}
                          >
                            {RESTORE_FILTERS.map((filter) => (
                              <SelectItem key={filter.id} value={filter.id} text={filter.label} />
                            ))}
                          </Select>
                        )}
                        {projectActivity?.retention && (
                          <p className="project-retention-note">
                            Autosaves capped at {projectActivity.retention.autosaveLimit}; milestones retained
                            {projectActivity.retention.autosaveCount != null
                              ? ` (${projectActivity.retention.autosaveCount} autosaves, ${projectActivity.retention.milestoneCount || 0} milestones).`
                              : '.'}
                          </p>
                        )}
                        {projectActivity?.persistence.connected && !projectActivityBusy && (projectActivity.snapshots || []).length > 0 && restoreSnapshots.length === 0 && (
                          <p className="panel-copy">No restore points match this filter.</p>
                        )}
                        {!projectActivityBusy && restoreSnapshots.slice(0, 8).map((snapshot) => (
                          <div className="project-restore-point" key={snapshot.id}>
                            <div>
                              <div className="project-restore-title">
                                <strong>{snapshot.label}</strong>
                                <Tag type={restoreEventTagType(snapshot.eventType)} size="sm">
                                  {restoreEventLabel(snapshot.eventType)}
                                </Tag>
                              </div>
                              <span>
                                {formatActivityDate(snapshot.createdAt)}
                                {snapshot.qualityScore != null ? ` · ${snapshot.qualityScore}/100` : ''}
                              </span>
                            </div>
                            <Button
                              kind="ghost"
                              size="sm"
                              renderIcon={Renew}
                              onClick={() => openRestorePreview(snapshot)}
                              disabled={restoreBusy || restorePreviewBusy}
                            >
                              Restore
                            </Button>
                          </div>
                        ))}
                      </div>

                      <div className="project-events">
                        <span className="advisor-label">Recent events</span>
                        {projectActivityBusy && <InlineLoading description="Loading activity..." />}
                        {!projectActivityBusy && projectActivity?.events?.length === 0 && (
                          <p className="panel-copy">No recorded events yet. The next autosave or quality check will appear here.</p>
                        )}
                        {!projectActivityBusy && (projectActivity?.events || []).slice(0, 8).map((event) => (
                          <div className="project-event" key={`${event.eventType}-${event.createdAt}`}>
                            <strong>{event.eventType.replace(/-/g, ' ')}</strong>
                            <span>{formatActivityDate(event.createdAt)}</span>
                          </div>
                        ))}
                      </div>
                    </>
                  )}
                </Stack>
              </Tile>
            </Column>
          )}

          {/* ══════════════════════════════════════════════════════════════════
              STEP 1 — UPLOAD
          ══════════════════════════════════════════════════════════════════ */}
          {activeNav === 'wizard' && step === 'upload' && (
            <Column sm={4} md={8} lg={10}>
              <Tile className="panel">
                <Stack gap={6}>
                  <div className="step-header">
                    <h2>Upload your source files</h2>
                    <InfoTip text="Accepted formats: IBM Cloud Solutioning pricing workbooks (.xlsx), bills of material (.csv, .tsv), architecture notes (.md, .txt), or structured data (.json). You can upload multiple files at once." />
                  </div>
                  <p className="panel-copy">
                    Drag in your BOM, IBM Cloud Solutioning pricing export, architecture notes, or any customer spreadsheet.
                    Network Picasso will extract IBM Cloud components automatically.
                    {settings.mode === 'ollama' && (
                      <span className="ai-badge"> AI-assisted extraction is on ({settings.ollamaModel}).</span>
                    )}
                  </p>

                  <TextInput
                    id="project-name"
                    labelText="Project name"
                    value={projectName}
                    placeholder="e.g. Acme Bank — Healthcare Platform"
                    onChange={(e) => setProjectName(e.target.value)}
                  />

                  <div>
                    <div className="field-label-row">
                      <span className="cds--label">Source files</span>
                      <InfoTip text="Supported: .xlsx, .csv, .tsv, .json, .md, .txt. IBM Cloud Solutioning workbooks are automatically recognised and parsed using the correct column mapping." />
                    </div>
                    <FileUploaderDropContainer
                      id="source-files"
                      labelText="Drag files here or click to browse"
                      multiple
                      accept={ACCEPTED_FILE_TYPES}
                      onAddFiles={(_e, { addedFiles }) => addFiles(addedFiles)}
                    />
                  </div>

                  <div className="selected-files">
                    {selectedFiles.map((file) => (
                      <FileUploaderItem
                        key={`${file.name}-${file.size}`}
                        name={file.name}
                        status="edit"
                        size="md"
                        iconDescription="Remove file"
                        onDelete={() => removeFile(file.name)}
                      />
                    ))}
                  </div>

                  {selectedFiles.length === 0 && (
                    <InlineNotification
                      kind="info"
                      title="No files selected"
                      subtitle="Add at least one file to continue."
                      lowContrast
                      hideCloseButton
                    />
                  )}

                  <div className="step-actions">
                    <Button
                      renderIcon={ArrowRight}
                      onClick={uploadAndRunIntake}
                      disabled={busy || selectedFiles.length === 0}
                    >
                      Parse files and continue
                    </Button>
                  </div>
                </Stack>
              </Tile>
            </Column>
          )}

          {/* ══════════════════════════════════════════════════════════════════
              STEP 2 — REVIEW MODEL
          ══════════════════════════════════════════════════════════════════ */}
          {activeNav === 'wizard' && step === 'review' && (
            <Column sm={4} md={8} lg={12}>
              <Stack gap={6}>

                {/* Component Verification — only when low-confidence items exist */}
                {pendingComponents.length > 0 && (
                  <Tile className="panel">
                    <Stack gap={5}>
                      <div className="step-header">
                        <h2>Confirm uncertain components</h2>
                        <InfoTip text="These components were extracted by the AI with lower confidence. Confirm the correct architecture category for each, reassign using the dropdown, or discard if the item is not relevant." />
                      </div>
                      <p className="panel-copy">
                        {pendingComponents.length} component{pendingComponents.length > 1 ? 's' : ''} need your review before being added to the model.
                      </p>
                      <Table size="md" aria-label="Pending components">
                        <TableHead>
                          <TableRow>
                            <TableHeader>Component</TableHeader>
                            <TableHeader>Category</TableHeader>
                            <TableHeader>Confidence</TableHeader>
                            <TableHeader>Notes</TableHeader>
                            <TableHeader>Action</TableHeader>
                          </TableRow>
                        </TableHead>
                        <TableBody>
                          {pendingComponents.map((c) => (
                            <TableRow key={c.id}>
                              <TableCell>{c.name}</TableCell>
                              <TableCell>
                                <Select id={`reassign-${c.id}`} labelText="" hideLabel
                                  value={pendingAssignments[c.id] ?? c.suggestedKey}
                                  onChange={(e) => setPendingAssignments((cur) => ({ ...cur, [c.id]: e.target.value }))}>
                                  {IBM_CLOUD_KEYS.map((k) => (
                                    <SelectItem key={k} value={k} text={k.replace(/_/g, ' ')} />
                                  ))}
                                </Select>
                              </TableCell>
                              <TableCell>{Math.round(c.confidence * 100)}%</TableCell>
                              <TableCell>{c.notes || '—'}</TableCell>
                              <TableCell>
                                <div style={{ display: 'flex', gap: '0.5rem' }}>
                                  <Button size="sm" onClick={() => confirmComponents([{ id: c.id, name: c.name, key: pendingAssignments[c.id] ?? c.suggestedKey, purpose: '', notes: c.notes || '' }], [])} disabled={busy}>Confirm</Button>
                                  <Button kind="danger--ghost" size="sm" onClick={() => confirmComponents([], [c.id])} disabled={busy}>Discard</Button>
                                </div>
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                      <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end' }}>
                        <Button kind="secondary" onClick={() => confirmComponents(pendingComponents.map((c) => ({ id: c.id, name: c.name, key: pendingAssignments[c.id] ?? c.suggestedKey, purpose: '', notes: c.notes || '' })), [])} disabled={busy}>Confirm all</Button>
                        <Button kind="danger" onClick={() => confirmComponents([], pendingComponents.map((c) => c.id))} disabled={busy}>Discard all</Button>
                      </div>
                    </Stack>
                  </Tile>
                )}

                {architecture && (
                  <Tile className="panel advisor-panel">
                    <Stack gap={5}>
                      <div className="step-header">
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <ListChecked size={20} />
                          <h2>Architecture advisor</h2>
                        </div>
                        <InfoTip text="This review combines IBM pattern scoring, Well-Architected coverage, open design decisions, and a recommended logical network design." />
                      </div>

                      {architectureReviewBusy && (
                        <InlineLoading description="Reviewing architecture…" />
                      )}

                      {!architectureReviewBusy && !architectureReview && (
                        <div>
                          <Button size="sm" renderIcon={Renew} onClick={() => runArchitectureReview()}>
                            Review architecture
                          </Button>
                        </div>
                      )}

                      {architectureReview && (
                        <>
                          <div className="advisor-hero">
                            <div>
                              <span className="advisor-label">Recommended IBM pattern</span>
                              <h3>{architectureReview.recommendedPattern?.name || 'Pattern not selected'}</h3>
                              <p>
                                {architectureReview.recommendedPattern
                                  ? `${architectureReview.recommendedPattern.score}% match based on uploaded facts and requirements.`
                                  : 'Add requirements or answer design questions to improve the recommendation.'}
                              </p>
                            </div>
                            {architectureReview.recommendedPattern && (
                              <Button
                                size="sm"
                                renderIcon={Checkmark}
                                onClick={() => confirmPattern(architectureReview.recommendedPattern!)}
                              >
                                Confirm pattern
                              </Button>
                            )}
                          </div>

                          <div className="advisor-grid">
                            {architectureReview.patternFoundation && (
                              <div className="advisor-section advisor-section--foundation">
                                <h3>IBM pattern foundation</h3>
                                <strong>{architectureReview.patternFoundation.name}</strong>
                                <p>{architectureReview.patternFoundation.rationale}</p>
                                <div className="foundation-tags">
                                  {architectureReview.patternFoundation.requiredElements.slice(0, 5).map((item) => (
                                    <Tag key={item} type="cool-gray" size="sm">{item}</Tag>
                                  ))}
                                </div>
                              </div>
                            )}
                            <div className="advisor-section">
                              <h3>Next seller actions</h3>
                              <ul>
                                {architectureReview.sellerNextActions.map((action, idx) => (
                                  <li key={idx}>{action}</li>
                                ))}
                              </ul>
                            </div>
                            <div className="advisor-section">
                              <h3>Logical design</h3>
                              <div className="logical-design-list">
                                {architectureReview.logicalDesign.map((item) => (
                                  <div key={item.area}>
                                    <strong>{item.area}</strong>
                                    <p>{item.design}</p>
                                  </div>
                                ))}
                              </div>
                            </div>
                          </div>

                          <div className="pillar-scorecard">
                            {architectureReview.wellArchitected.map((pillar) => (
                              <div key={pillar.name} className="pillar-card">
                                <div className="pillar-card__header">
                                  <strong>{pillar.name}</strong>
                                  <Tag
                                    type={pillar.status === 'Strong' ? 'green' : pillar.status === 'Needs detail' ? 'blue' : 'red'}
                                    size="sm"
                                  >
                                    {pillar.status}
                                  </Tag>
                                </div>
                                <div className="pillar-meter" aria-label={`${pillar.name} score ${pillar.score}%`}>
                                  <div style={{ width: `${pillar.score}%` }} />
                                </div>
                                <span className="pillar-score">{pillar.score}%</span>
                                {pillar.gaps.length > 0 && (
                                  <p>{pillar.gaps.slice(0, 2).join('; ')}</p>
                                )}
                              </div>
                            ))}
                          </div>

                          {architectureReview.priorityQuestions.length > 0 && (
                            <InlineNotification
                              kind="warning"
                              title={`${architectureReview.openDecisionCount} open architecture decisions`}
                              subtitle={architectureReview.priorityQuestions.slice(0, 2).map((q) => q.question).join(' ')}
                              lowContrast
                              hideCloseButton
                            />
                          )}
                        </>
                      )}
                    </Stack>
                  </Tile>
                )}

                {/* Architecture Model summary */}
                <Tile className="panel">
                  <Stack gap={5}>
                    <div className="step-header">
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <h2>Extracted architecture model</h2>
                          <InfoTip text="This table shows every IBM Cloud component category that was found across your uploaded files. Each number is the count of distinct components detected. If a category you expect is missing, it may not be explicitly named in your source files — the questions in Step 3 will prompt you to fill those gaps." />
                        </div>
                        {activeProject && (
                          <div style={{ display: 'flex', gap: '0.5rem' }}>
                            <Button kind="ghost" size="sm" renderIcon={Download} iconDescription="Export architecture JSON" hasIconOnly onClick={exportArchitecture} disabled={!activeProject.hasArchitecture} tooltipPosition="left" />
                            <Button kind="ghost" size="sm" renderIcon={Upload} iconDescription="Import architecture JSON" hasIconOnly onClick={() => importInputRef.current?.click()} tooltipPosition="left" />
                            <input ref={importInputRef} type="file" accept=".json" style={{ display: 'none' }} onChange={(e) => { const f = e.target.files?.[0]; if (f) importArchitecture(f); e.target.value = ''; }} />
                          </div>
                        )}
                      </div>
                    </div>

                    {summary.length === 0 ? (
                      <p className="panel-copy">No components detected yet. Go back and upload source files.</p>
                    ) : (
                      <StructuredListWrapper aria-label="Architecture model summary">
                        <StructuredListHead>
                          <StructuredListRow head>
                            <StructuredListCell head>Category</StructuredListCell>
                            <StructuredListCell head>Components detected</StructuredListCell>
                          </StructuredListRow>
                        </StructuredListHead>
                        <StructuredListBody>
                          {summary.map((item) => (
                            <StructuredListRow key={item.key}>
                              <StructuredListCell>{item.key.replace(/_/g, ' ')}</StructuredListCell>
                              <StructuredListCell>{item.count}</StructuredListCell>
                            </StructuredListRow>
                          ))}
                        </StructuredListBody>
                      </StructuredListWrapper>
                    )}
                  </Stack>
                </Tile>

                {/* Sources */}
                {(architecture?.sources || []).length > 0 && (
                  <Tile className="panel">
                    <Stack gap={4}>
                      <div className="step-header">
                        <h2>Source files parsed</h2>
                        <InfoTip text="Each file is classified by role. Pricing catalogs are skipped — they contain SKU rows, not topology. BOM and unified pricing files are the primary architecture sources." />
                      </div>
                      <div className="source-list">
                        {(architecture?.sources || []).map((src) => {
                          const basename = src.file.split('/').pop() || src.file;
                          const roleBadge = roleTagProps(src.role);
                          return (
                            <div className="source-item" key={src.file}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                                <strong>{basename}</strong>
                                {roleBadge && (
                                  <Tag type={roleBadge.type} size="sm">{roleBadge.label}</Tag>
                                )}
                                {src.skipped && (
                                  <Tag type="warm-gray" size="sm">skipped</Tag>
                                )}
                              </div>
                              <span style={{ color: src.skipped ? '#8d8d8d' : undefined }}>
                                {src.type}{src.skipped ? ' · ' + (src.skip_reason || 'skipped') : ` · ${src.records} records`}
                              </span>
                            </div>
                          );
                        })}
                      </div>
                    </Stack>
                  </Tile>
                )}

                {/* ── IBM Think Architecture Pattern Match ─────────────────── */}
                {architecture && (
                  <Tile className="panel">
                    <Stack gap={5}>
                      <div className="step-header">
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                          <IbmCloud size={20} />
                          <h2>IBM Think Architecture pattern match</h2>
                        </div>
                        <InfoTip text="Network Picasso scores your extracted architecture and requirements against all IBM Cloud reference patterns from ibm.com/think/architectures. The top match is recommended as the basis for your diagram. You can override it if you know the intended pattern." />
                      </div>

                      {chosenPattern && (
                        <InlineNotification
                          kind="success"
                          title={`Pattern confirmed: ${chosenPattern.name}`}
                          subtitle={`Score ${chosenPattern.score}% match — this pattern will be used as the basis for your diagram.`}
                          lowContrast
                          hideCloseButton
                        />
                      )}

                      {patternResults.length === 0 ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                          <p className="panel-copy">
                            Click <strong>Match patterns</strong> to score your uploaded documents and requirements
                            against every IBM Cloud reference architecture pattern.
                            Network Picasso will recommend the best fit and show you exactly which signals matched.
                          </p>
                          <div>
                            <Button
                              renderIcon={patternBusy ? undefined : Diagram}
                              onClick={runPatternMatch}
                              disabled={patternBusy}
                              size="md"
                            >
                              {patternBusy ? <InlineLoading description="Scoring patterns…" /> : 'Match patterns'}
                            </Button>
                          </div>
                        </div>
                      ) : (
                        <Stack gap={4}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <p className="panel-copy" style={{ margin: 0 }}>
                              {patternResults.length} patterns scored — top match: <strong>{patternResults[0]?.name}</strong> ({patternResults[0]?.score}%)
                            </p>
                            <Button kind="ghost" size="sm" renderIcon={Renew} onClick={runPatternMatch} disabled={patternBusy}>
                              Re-score
                            </Button>
                          </div>
                          <div className="pattern-list">
                            {patternResults.map((pat, idx) => {
                              const isChosen = chosenPattern?.id === pat.id;
                              const isTop = idx === 0;
                              return (
                                <div key={pat.id} className={`pattern-card${isChosen ? ' pattern-card--chosen' : ''}${isTop ? ' pattern-card--top' : ''}`}>
                                  <div className="pattern-card__header">
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                                      <strong>{pat.name}</strong>
                                      {isTop && <Tag type="blue" size="sm">Best match</Tag>}
                                      {isChosen && <Tag type="green" size="sm">Confirmed</Tag>}
                                    </div>
                                    <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                                      <span className="pattern-score">{pat.score}%</span>
                                      <Button
                                        kind={isChosen ? 'tertiary' : 'primary'}
                                        size="sm"
                                        renderIcon={isChosen ? Checkmark : undefined}
                                        onClick={() => confirmPattern(pat)}
                                      >
                                        {isChosen ? 'Confirmed' : 'Use this pattern'}
                                      </Button>
                                    </div>
                                  </div>
                                  <p className="pattern-card__desc">{pat.description}</p>
                                  {/* Score bar */}
                                  <div className="pattern-score-bar">
                                    <div className="pattern-score-bar__fill" style={{ width: `${pat.score}%` }} />
                                  </div>
                                  {/* Matched / missing signals */}
                                  <details className="pattern-signals">
                                    <summary>
                                      {pat.matched.filter(s => !s.startsWith('⚠')).length} signals matched,{' '}
                                      {pat.missing.length} missing
                                      {pat.matched.filter(s => s.startsWith('⚠')).length > 0 && (
                                        <span style={{ color: '#f1c21b' }}> · {pat.matched.filter(s => s.startsWith('⚠')).length} conflicts</span>
                                      )}
                                    </summary>
                                    <div className="pattern-signals__grid">
                                      {pat.matched.map((s, i) => (
                                        <span key={i} className={s.startsWith('⚠') ? 'signal signal--warn' : 'signal signal--ok'}>{s}</span>
                                      ))}
                                      {pat.missing.map((s, i) => (
                                        <span key={i} className="signal signal--missing">{s}</span>
                                      ))}
                                    </div>
                                  </details>
                                  <a href={pat.url} target="_blank" rel="noreferrer" className="pattern-card__link">
                                    View on IBM Think Architectures →
                                  </a>
                                </div>
                              );
                            })}
                          </div>
                        </Stack>
                      )}
                    </Stack>
                  </Tile>
                )}

                <div className="step-actions">
                  <Button kind="secondary" renderIcon={ArrowLeft} onClick={() => setStep('upload')}>Back</Button>
                  <Button renderIcon={ArrowRight} onClick={() => setStep('questions')}>
                    Continue to questions {openQuestions.length > 0 ? `(${openQuestions.length} open)` : ''}
                  </Button>
                </div>
              </Stack>
            </Column>
          )}

          {/* ══════════════════════════════════════════════════════════════════
              STEP 3 — QUESTIONS
          ══════════════════════════════════════════════════════════════════ */}
          {activeNav === 'wizard' && step === 'questions' && (
            <Column sm={4} md={8} lg={12}>
              <Stack gap={5}>

              {/* ── Customer requirements ──────────────────────────────────── */}
              <Tile className="panel">
                <Stack gap={4}>
                  <div className="step-header">
                    <h2>Customer requirements</h2>
                    <InfoTip text="Paste or upload the customer's documented requirements before answering the design questions. This context helps you give accurate, specific answers and will be saved alongside your architecture model." />
                  </div>
                  <p className="panel-copy">
                    Provide a comprehensive list of requirements. Be as detailed and specific as possible, including:
                    functional requirements, data sources, workflow steps, non-functional requirements,
                    performance expectations, compliance or regulatory needs, and scalability considerations.
                  </p>
                  <TextArea
                    id="customer-requirements"
                    labelText=""
                    placeholder={[
                      'Provide a comprehensive list of requirements. Be as detailed and specific as possible, including:',
                      '  - Functional requirements',
                      '    - Data sources to be used',
                      '    - Workflow steps and logic',
                      '    - Automation needs or triggers',
                      '  - Non-functional requirements',
                      '    - Performance expectations',
                      '    - Compliance or regulatory needs',
                      '    - Formatting and layout preferences',
                      '    - Accessibility considerations',
                      '    - Scalability or future-proofing needs',
                    ].join('\n')}
                    rows={10}
                    value={requirementsText}
                    onChange={(e) => setRequirementsText(e.target.value)}
                  />
                  <div className="requirements-actions">
                    <Button
                      size="sm"
                      renderIcon={requirementsSaved ? Checkmark : DocumentImport}
                      onClick={() => saveRequirements(requirementsText, 'text')}
                      disabled={!requirementsText.trim()}
                    >
                      {requirementsSaved ? 'Saved' : 'Save requirements'}
                    </Button>
                    <Button
                      kind="ghost"
                      size="sm"
                      renderIcon={Upload}
                      onClick={() => requirementsFileRef.current?.click()}
                    >
                      Upload requirements file
                    </Button>
                    <input
                      ref={requirementsFileRef}
                      type="file"
                      accept=".txt,.md,.pdf,.docx"
                      style={{ display: 'none' }}
                      onChange={(e) => {
                        const f = e.target.files?.[0];
                        if (f) loadRequirementsFromFile(f);
                        e.target.value = '';
                      }}
                    />
                  </div>
                  {requirementsSaved && (
                    <InlineNotification
                      kind="success"
                      title="Requirements saved"
                      subtitle="Stored in your architecture model."
                      lowContrast
                      hideCloseButton
                    />
                  )}
                </Stack>
              </Tile>

              {/* ── Design questions ───────────────────────────────────────── */}
              <Tile className="panel">
                <Stack gap={5}>
                  <div className="step-header">
                    <h2>Guided design questions</h2>
                    <InfoTip text="These questions identify missing design decisions based on what was not found in your source files. Answer each one to improve the accuracy of your diagram. Use 'Accept coaching' to apply IBM Cloud best-practice guidance as the answer if you are unsure." />
                  </div>

                  {openQuestions.length === 0 ? (
                    <InlineNotification
                      kind="success"
                      title="All questions answered"
                      subtitle="Your architecture model is complete. Continue to generate your diagram."
                      lowContrast
                      hideCloseButton
                    />
                  ) : (
                    <p className="panel-copy">
                      {openQuestions.length} design decision{openQuestions.length > 1 ? 's' : ''} still need{openQuestions.length === 1 ? 's' : ''} an answer.
                      {answeredQuestions.length > 0 && ` ${answeredQuestions.length} already answered.`}
                    </p>
                  )}

                  <div className="question-list">
                    {openQuestions.map((item, index) => (
                      <Layer key={questionKey(item)}>
                        <div className="question-item">
                          <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
                            <Tag type="blue">{item.area}</Tag>
                            {item.source === 'llm'   && <Tag type="purple">AI</Tag>}
                            {item.source === 'rules' && <Tag type="cool-gray">Rules</Tag>}
                          </div>
                          <p>{item.question}</p>
                          {item.guidance && (
                            <div className="coaching">
                              <span>IBM Cloud best-practice guidance</span>
                              <p>{item.guidance}</p>
                            </div>
                          )}
                          <TextArea
                            id={`answer-${index}`}
                            labelText="Your answer"
                            placeholder="Describe the design decision, assumption, or constraint for this area."
                            value={questionAnswers[questionKey(item)] || ''}
                            onChange={(e) => updateAnswer(item, e.target.value)}
                          />
                          <div className="question-actions">
                            {item.guidance && (
                              <Button kind="tertiary" size="sm" onClick={() => acceptCoaching(item)}>
                                Accept guidance as answer
                              </Button>
                            )}
                            <Button renderIcon={Checkmark} size="sm" onClick={() => saveAnswer(item)}>
                              Save answer
                            </Button>
                          </div>
                        </div>
                      </Layer>
                    ))}
                  </div>

                  <div className="step-actions">
                    <Button kind="secondary" renderIcon={ArrowLeft} onClick={() => setStep('review')}>Back</Button>
                    <Button renderIcon={ArrowRight} onClick={() => setStep('diagram')}>
                      {openQuestions.length === 0 ? 'Continue to diagram' : 'Skip to diagram'}
                    </Button>
                  </div>
                </Stack>
              </Tile>

              </Stack>
            </Column>
          )}

          {/* ══════════════════════════════════════════════════════════════════
              STEP 4 — DIAGRAM
          ══════════════════════════════════════════════════════════════════ */}
          {activeNav === 'wizard' && step === 'diagram' && (
            <Column sm={4} md={8} lg={10}>
              <Tile className="panel">
                <Stack gap={6}>
                  <div className="step-header">
                    <h2>Generate your diagram</h2>
                    <InfoTip text="Network Picasso generates a Draw.io (.drawio) XML diagram from your architecture model. Choose the diagram type, then use one of the three options below to get your diagram." />
                  </div>

                  <div>
                    <div className="field-label-row">
                      <span className="cds--label">Diagram type</span>
                      <InfoTip text="Context: high-level for executive audiences. Logical: component relationships for architects. Deployment: full AZ and subnet layout for implementation teams." />
                    </div>
                    <Dropdown
                      id="diagram-type"
                      titleText=""
                      label="Select diagram type"
                      selectedItem={diagramType}
                      items={['executive', 'context', 'logical', 'deployment']}
                      onChange={({ selectedItem }) => selectedItem && setDiagramType(String(selectedItem))}
                    />
                  </div>

                  <div className="quality-panel">
                    <div className="quality-header">
                      <div>
                        <div className="diagram-action-header">
                          <strong>Diagram quality analyzer</strong>
                          <InfoTip text="Checks generated Draw.io XML for label fit, overlap risk, density, and alignment to IBM Think Architecture pattern elements such as VPC landing zone, VSI on VPC, and PowerVS with VPC landing zone." />
                        </div>
                        <p className="panel-copy">
                          Validate the selected page before opening it with a customer or asking Bob for final polish.
                        </p>
                      </div>
                      <Button
                        kind="tertiary"
                        size="sm"
                        renderIcon={ListChecked}
                        onClick={runDiagramQuality}
                        disabled={busy || diagramQualityBusy || !architecture}
                      >
                        {diagramQualityBusy ? 'Analyzing…' : 'Analyze quality'}
                      </Button>
                    </div>

                    {diagramQuality && (
                      <div className="quality-results">
                        <div className="quality-score">
                          <span>{diagramQuality.score}</span>
                          <div>
                            <strong>{diagramQuality.status}</strong>
                            <p>{diagramQuality.summary}</p>
                          </div>
                        </div>
                        <div className="quality-remediation">
                          <div>
                            <strong>Recommended remediation loop</strong>
                            <p>Open the diagram in the MCP editor, copy the quality fix prompt to Bob, let Bob make targeted layout/pattern edits, then re-run this analyzer.</p>
                          </div>
                          <div className="quality-remediation-actions">
                            <Button
                              kind="secondary"
                              size="sm"
                              renderIcon={Launch}
                              onClick={openInMcpEditor}
                              disabled={busy || !architecture || !mcpRunning}
                            >
                              Open in MCP editor
                            </Button>
                            <Button
                              kind="tertiary"
                              size="sm"
                              renderIcon={Copy}
                              onClick={() => copyBobPrompt('Quality Fix', qualityRemediationPrompt(diagramType, diagramQuality))}
                              disabled={busy}
                            >
                              {copiedPrompt === 'Quality Fix' ? 'Quality fix copied' : 'Copy quality fix prompt'}
                            </Button>
                            <Button
                              kind="ghost"
                              size="sm"
                              renderIcon={Renew}
                              onClick={runDiagramQuality}
                              disabled={busy || diagramQualityBusy || !architecture}
                            >
                              Re-analyze
                            </Button>
                          </div>
                          {!mcpRunning && (
                            <p className="quality-remediation-note">
                              MCP editor is not detected. Use Option E below to check/start Bob MCP before applying fixes.
                            </p>
                          )}
                        </div>
                        <div className="quality-pattern">
                          <span className="advisor-label">IBM pattern foundation</span>
                          <strong>{diagramQuality.ibmPatternChecks.name}</strong>
                          <a href={diagramQuality.ibmPatternSource} target="_blank" rel="noreferrer">
                            IBM Think Architectures
                          </a>
                          <div className="quality-checks">
                            {diagramQuality.ibmPatternChecks.checks.map((check) => (
                              <Tag key={check.name} type={check.present ? 'green' : 'red'}>
                                {check.present ? 'Present' : 'Review'}: {check.name}
                              </Tag>
                            ))}
                          </div>
                        </div>
                        {diagramQuality.findings.length > 0 && (
                          <div className="quality-findings">
                            {diagramQuality.findings.slice(0, 6).map((finding, index) => (
                              <div className="quality-finding" key={`${finding.area}-${index}`}>
                                <Tag
                                  type={
                                    finding.severity === 'error'
                                      ? 'red'
                                      : finding.severity === 'warning'
                                        ? 'magenta'
                                        : 'blue'
                                  }
                                >
                                  {finding.severity}
                                </Tag>
                                <div>
                                  <strong>{finding.area}</strong>
                                  <p>{finding.message}</p>
                                  <p>{finding.recommendation}</p>
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}
                  </div>

                  <div className="diagram-actions">
                    {/* Option A */}
                    <div className="diagram-action-card">
                      <div className="diagram-action-header">
                        <strong>Option A — Save to file</strong>
                        <InfoTip text="Writes the .drawio XML file to the outputs/ folder inside this repository. Open the saved file in the Draw.io desktop app or diagrams.net." />
                      </div>
                      <p className="panel-copy">Saves the diagram to <code>outputs/</code> on disk.</p>
                      <Button renderIcon={Diagram} onClick={generateDiagram} disabled={busy || !architecture}>
                        Save Draw.io file
                      </Button>
                      {diagramPath && (
                        <div className="artifact-path">
                          <span>Saved to</span>
                          <code>{diagramPath}</code>
                        </div>
                      )}
                    </div>

                    {/* Option B */}
                    <div className="diagram-action-card">
                      <div className="diagram-action-header">
                        <strong>Option B — Copy XML</strong>
                        <InfoTip text="Copies the raw Draw.io XML to your clipboard. Paste it into diagrams.net using Edit › XML, or into any tool that accepts Draw.io XML." />
                      </div>
                      <p className="panel-copy">Copy the diagram XML to your clipboard, then paste into diagrams.net via Edit › XML.</p>
                      <Button kind="secondary" renderIcon={Copy} onClick={copyDiagramXml} disabled={busy || !architecture}>
                        Copy XML to clipboard
                      </Button>
                    </div>

                    {/* Option C */}
                    <div className="diagram-action-card">
                      <div className="diagram-action-header">
                        <strong>Option C — Open in diagrams.net</strong>
                        <InfoTip text="Opens diagrams.net in a new window using the embed API. The diagram XML is delivered automatically via postMessage once the editor loads — nothing is uploaded externally. Requires internet access and that your browser permits the popup." />
                      </div>
                      <p className="panel-copy">Open your diagram directly in diagrams.net in a new tab.</p>
                      <Button kind="secondary" renderIcon={Launch} onClick={openInDiagramsNet} disabled={busy || !architecture}>
                        Open in diagrams.net
                      </Button>
                    </div>

                    {/* Option D — Inline preview */}
                    <div className="diagram-action-card">
                      <div className="diagram-action-header">
                        <strong>Option D — Preview here</strong>
                        <InfoTip text="Renders a live interactive preview of the diagram using the diagrams.net embed API. Requires an internet connection to load the embed viewer. The diagram is sent to the iframe via postMessage — nothing is stored externally." />
                      </div>
                      <p className="panel-copy">Render an interactive preview inline. Requires internet access to load the embed viewer.</p>
                      <Button kind="secondary" renderIcon={Diagram} onClick={loadPreview} disabled={busy || !architecture}>
                        {previewXml ? 'Refresh preview' : 'Load preview'}
                      </Button>
                      {previewXml && (
                        <div className="diagram-preview">
                          <iframe
                            ref={previewRef}
                            src="https://embed.diagrams.net/?embed=1&proto=json&spin=1&analytics=0&noSaveBtn=1&noExitBtn=1"
                            title="Diagram preview"
                            className="diagram-preview-frame"
                          />
                        </div>
                      )}
                    </div>

                    {/* Option E — Open in MCP editor */}
                    <div className="diagram-action-card">
                      <div className="diagram-action-header">
                        <strong>Option E — Open in MCP editor</strong>
                        <InfoTip text="MCP works against a live Draw.io browser tab at localhost:4000. Start the drawio-mcp-server, open that editor tab, then push the diagram here." />
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                        {mcpRunning
                          ? <Tag type="green">MCP editor running</Tag>
                          : <Tag type="gray">MCP editor not detected</Tag>
                        }
                        <Button kind="ghost" size="sm" onClick={probeMcpEditor}>Check</Button>
                      </div>
                      <p className="panel-copy">
                        {mcpRunning
                          ? `Open ${BROWSER_MCP_EDITOR_URL} in your browser, then push this diagram into that live editor tab.`
                          : 'Start the drawio MCP server from Bob\'s MCP panel, then click Check.'}
                      </p>
                      <div className="mcp-checklist">
                        <div className="mcp-checklist-item">
                          <Tag type={mcpRunning ? 'green' : 'gray'}>{mcpRunning ? 'Ready' : 'Needed'}</Tag>
                          <span>Bob MCP server connected</span>
                        </div>
                        <div className="mcp-checklist-item">
                          <Tag type={mcpEditorOpened ? 'green' : 'gray'}>{mcpEditorOpened ? 'Open' : 'Next'}</Tag>
                          <span>Draw.io MCP editor tab open</span>
                        </div>
                        <div className="mcp-checklist-item">
                          <Tag type={mcpDiagramPushed ? 'green' : 'gray'}>{mcpDiagramPushed ? 'Pushed' : 'Next'}</Tag>
                          <span>Diagram loaded into MCP editor</span>
                        </div>
                        <div className="mcp-checklist-item">
                          <Tag type={copiedPrompt ? 'green' : 'gray'}>{copiedPrompt ? 'Copied' : 'Then'}</Tag>
                          <span>Prompt Bob for targeted editing</span>
                        </div>
                      </div>
                      <Button kind="ghost" size="sm" renderIcon={Launch} onClick={openMcpEditorTab} disabled={!mcpRunning}>
                        Open MCP editor tab
                      </Button>
                      <Button kind="secondary" renderIcon={Launch} onClick={openInMcpEditor}
                        disabled={busy || !architecture || !mcpRunning}>
                        Open in MCP editor
                      </Button>
                      {mcpStatus && (
                        <p style={{ fontSize: '0.8rem', color: mcpRunning ? '#198038' : '#da1e28', marginTop: '0.5rem' }}>
                          {mcpStatus}
                        </p>
                      )}
                    </div>

                    {/* All pages — multi-diagram export */}
                    <div className="diagram-action-card">
                      <div className="diagram-action-header">
                        <strong>Generate all diagram types</strong>
                        <InfoTip text="Generates executive, context, logical, and deployment diagrams in one step. Opens them as pages in one diagrams.net file and also saves the multi-page .drawio file to outputs/." />
                      </div>
                      <p className="panel-copy">
                        {mcpRunning
                          ? 'Opens all four diagram pages in the MCP editor.'
                          : 'Saves and opens a four-page .drawio file: executive, context, logical, and deployment.'}
                      </p>
                      <Button renderIcon={Layers} onClick={generateAllPages}
                        disabled={busy || !architecture}>
                        {mcpRunning ? 'Open all pages in MCP editor' : 'Open all-pages .drawio file'}
                      </Button>
                    </div>
                  </div>

                  <div className="bob-prompts-panel">
                    <div className="diagram-action-header">
                      <strong>Bob editing prompts</strong>
                      <InfoTip text="Copy one of these prompts after the diagram is loaded in the MCP editor. They tell Bob to inspect the current Draw.io document, use the IBM editing skill, and make targeted changes." />
                    </div>
                    <InlineNotification
                      kind="info"
                      title={`Recommended next prompt: ${bobPromptRecommendation.label}`}
                      subtitle={bobPromptRecommendation.reason}
                      lowContrast
                      hideCloseButton
                    />
                    <div className="bob-prompt-sections">
                      {Array.from(bobPromptsByCategory.entries()).map(([category, prompts]) => (
                        <div className="bob-prompt-section" key={category}>
                          <div className="bob-prompt-section-header">
                            <span>{category}</span>
                            <InfoTip text={BOB_PROMPT_CATEGORY_HELP[category] || 'Use these prompts for targeted Bob editing in the Draw.io MCP editor.'} />
                          </div>
                          <div className="bob-prompt-grid">
                            {prompts.map((prompt) => (
                              <Button
                                key={prompt.label}
                                kind={copiedPrompt === prompt.label ? 'primary' : 'tertiary'}
                                size="sm"
                                renderIcon={copiedPrompt === prompt.label ? Checkmark : Copy}
                                onClick={() => copyBobPrompt(prompt.label, prompt.text)}
                                disabled={busy}
                              >
                                {copiedPrompt === prompt.label ? `${prompt.label} copied` : prompt.label}
                              </Button>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                    <p className="panel-copy">
                      Start with <strong>Setup Bob</strong>, then use the smallest focused prompt that matches the improvement you want.
                    </p>
                  </div>

                  <div className="step-actions">
                    <Button kind="secondary" renderIcon={ArrowLeft} onClick={() => setStep('questions')}>Back to questions</Button>
                    <Button kind="ghost" renderIcon={Renew} onClick={() => setStep('upload')}>Start new intake</Button>
                  </div>
                </Stack>
              </Tile>
            </Column>
          )}

          {/* ══════════════════════════════════════════════════════════════════
              SETTINGS
          ══════════════════════════════════════════════════════════════════ */}
          {activeNav === 'settings' && (
            <Column sm={4} md={8} lg={10}>
              <Tile className="panel">
                <Stack gap={6}>
                  <div className="step-header">
                    <h2>Intake mode</h2>
                    <InfoTip text="Rules only uses fast keyword-based extraction with no AI. Ollama assisted sends your document text to a local Ollama model for deeper component extraction and additional design questions. Ollama must be running on this machine." />
                  </div>
                  <Toggle
                    id="mode-toggle"
                    labelText="AI mode"
                    labelA="Rules only"
                    labelB="Ollama assisted"
                    toggled={settings.mode === 'ollama'}
                    onToggle={(checked: boolean) =>
                      setSettings((s) => ({ ...s, mode: checked ? 'ollama' : 'rules' }))
                    }
                  />

                  <div className="step-header">
                    <h2>Ollama model</h2>
                    <InfoTip text="Select the local model to use for component extraction and gap analysis. Click 'Test connection' to load the list of models currently available in Ollama." />
                  </div>
                  <TextInput id="ollama-base-url" labelText="Ollama base URL" value="http://localhost:11434" readOnly />
                  <Dropdown
                    id="ollama-model"
                    titleText="Model"
                    label={ollamaModels.length === 0 ? 'phi4-mini:latest (default)' : 'Select model'}
                    selectedItem={settings.ollamaModel}
                    items={ollamaModels.length > 0 ? ollamaModels : ['phi4-mini:latest']}
                    onChange={({ selectedItem }: { selectedItem: string | null }) =>
                      selectedItem && setSettings((s) => ({ ...s, ollamaModel: selectedItem }))
                    }
                  />
                  <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                    <Button kind="secondary" size="md" onClick={testOllamaConnection}>
                      Test connection
                    </Button>
                    {connectionStatus === 'ok' && (
                      <Tag type="green">Connected — {ollamaModels.length} model{ollamaModels.length === 1 ? '' : 's'} available</Tag>
                    )}
                    {connectionStatus === 'fail' && <Tag type="red">Ollama not reachable at localhost:11434</Tag>}
                  </div>

                  <div className="step-header" style={{ marginTop: '1rem' }}>
                    <h2>Draw.io MCP editor</h2>
                    <InfoTip text="The drawio-mcp-server enables conversational diagram editing. Bob starts it automatically when the drawio MCP server is registered. After generation, use Option E to push diagrams into the live editor and ask Bob to make changes." />
                  </div>
                  <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                    <TextInput id="mcp-url" labelText="MCP editor URL" value="http://127.0.0.1:4000" readOnly />
                  </div>
                  <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                    <Button kind="secondary" size="md" onClick={probeMcpEditor}>
                      Check MCP editor
                    </Button>
                    {mcpRunning && <Tag type="green">Running at localhost:4000</Tag>}
                    {!mcpRunning && mcpStatus && <Tag type="gray">Not running</Tag>}
                  </div>

                  <div className="step-header" style={{ marginTop: '1rem' }}>
                    <h2>Projects folder</h2>
                    <InfoTip text="The folder where customer projects are stored. You can use an absolute path outside this repository, e.g. ~/Documents/NetworkPicasso/projects. Changes take effect immediately after saving." />
                  </div>
                  <TextInput
                    id="projects-root"
                    labelText="Projects root folder"
                    value={settings.projectsRoot}
                    placeholder="inputs/projects"
                    onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
                      setSettings((s) => ({ ...s, projectsRoot: e.target.value }))
                    }
                  />

                  <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                    <Button renderIcon={Checkmark} onClick={saveSettings}>Save settings</Button>
                    {settingsStatus && (
                      <Tag type={settingsStatus.includes('Failed') ? 'red' : 'green'}>{settingsStatus}</Tag>
                    )}
                  </div>
                </Stack>
              </Tile>
            </Column>
          )}

        </Grid>
      </Content>

      {/* ── Projects page modals ─────────────────────────────────────── */}

      {/* Rename folder */}
      <Modal
        open={!!renameFolderTarget}
        modalHeading={`Rename folder "${renameFolderTarget?.name}"`}
        primaryButtonText={projectsActionBusy ? 'Saving…' : 'Save'}
        secondaryButtonText="Cancel"
        primaryButtonDisabled={projectsActionBusy || !renameFolderValue.trim()}
        onRequestSubmit={doRenameFolder}
        onRequestClose={() => setRenameFolderTarget(null)}
      >
        <TextInput
          id="rename-folder-input"
          labelText="Folder name"
          value={renameFolderValue}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) => setRenameFolderValue(e.target.value)}
        />
      </Modal>

      {/* Rename project */}
      <Modal
        open={!!renameTarget}
        modalHeading={`Rename project "${renameTarget?.project || renameTarget?.customer}"`}
        primaryButtonText={projectsActionBusy ? 'Saving…' : 'Rename'}
        secondaryButtonText="Cancel"
        primaryButtonDisabled={projectsActionBusy || !renameValue.trim()}
        onRequestSubmit={doRenameProject}
        onRequestClose={() => setRenameTarget(null)}
      >
        <TextInput
          id="rename-project-input"
          labelText="Project name"
          value={renameValue}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) => setRenameValue(e.target.value)}
        />
        <p style={{ fontSize: '0.8125rem', color: '#6f6f6f', marginTop: '0.5rem' }}>
          The folder name on disk will be converted to a lowercase slug (e.g. &quot;Acme Q1&quot; → &quot;acme-q1&quot;).
        </p>
      </Modal>

      {/* Duplicate project */}
      <Modal
        open={!!duplicateTarget}
        modalHeading={`Duplicate "${duplicateTarget?.project || duplicateTarget?.customer}"`}
        primaryButtonText={projectsActionBusy ? 'Duplicating…' : 'Duplicate'}
        secondaryButtonText="Cancel"
        primaryButtonDisabled={projectsActionBusy || !duplicateName.trim()}
        onRequestSubmit={doDuplicateProject}
        onRequestClose={() => setDuplicateTarget(null)}
      >
        <p style={{ color: '#525252', lineHeight: 1.6, marginBottom: '1rem', fontSize: '0.875rem' }}>
          Creates a copy with the same architecture JSON. Uploaded source files are not copied — upload new files to the duplicate project.
        </p>
        <TextInput
          id="duplicate-project-name"
          labelText="New project name"
          value={duplicateName}
          onChange={(e: React.ChangeEvent<HTMLInputElement>) => setDuplicateName(e.target.value)}
        />
      </Modal>

      {/* Move project */}
      <Modal
        open={!!moveTarget}
        modalHeading={`Move "${moveTarget?.project || moveTarget?.customer}" to another folder`}
        primaryButtonText={projectsActionBusy ? 'Moving…' : 'Move'}
        secondaryButtonText="Cancel"
        primaryButtonDisabled={projectsActionBusy || !moveDest}
        onRequestSubmit={doMoveProject}
        onRequestClose={() => setMoveTarget(null)}
      >
        <Select
          id="move-dest-select"
          labelText="Destination folder"
          value={moveDest}
          onChange={(e: React.ChangeEvent<HTMLSelectElement>) => setMoveDest(e.target.value)}
        >
          <SelectItem value="" text="— Select a folder —" />
          {folders
            .filter((f) => f.path !== (moveTarget ? moveTarget.path.split('/').slice(0, -1).join('/') : ''))
            .map((f) => (
              <SelectItem key={f.path} value={f.path} text={f.name} />
            ))}
        </Select>
      </Modal>

      {/* Restore point */}
      <Modal
        open={!!restoreTarget}
        modalHeading={`Restore "${restoreTarget?.label}"?`}
        primaryButtonText={restoreBusy ? 'Restoring…' : 'Restore'}
        secondaryButtonText="Cancel"
        primaryButtonDisabled={restoreBusy || restorePreviewBusy}
        onRequestSubmit={restoreProjectSnapshot}
        onRequestClose={closeRestoreModal}
      >
        <p style={{ color: '#525252', lineHeight: 1.6 }}>
          This replaces the current architecture JSON with the selected restore point. Current work will remain in
          the event history if it was already autosaved.
        </p>
        {restoreTarget && (
          <p style={{ color: '#6f6f6f', marginTop: '0.75rem', fontSize: '0.875rem' }}>
            Created {formatActivityDate(restoreTarget.createdAt)}
            {restoreTarget.qualityScore != null ? ` · Quality ${restoreTarget.qualityScore}/100` : ''}
          </p>
        )}
        {restorePreviewBusy && (
          <div style={{ marginTop: '1rem' }}>
            <InlineLoading description="Comparing current architecture with restore point..." />
          </div>
        )}
        {!restorePreviewBusy && restorePreview && (
          <div className="restore-preview">
            <span className="advisor-label">What will change</span>
            {restorePreview.comparison.changes.length === 0 ? (
              <p className="panel-copy">No material architecture model differences were found.</p>
            ) : (
              <div className="restore-preview-grid">
                {restorePreview.comparison.changes.map((change) => (
                  <div className="restore-preview-row" key={change.label}>
                    <strong>{change.label}</strong>
                    <div>
                      <span>Current</span>
                      <p>{formatRestoreValue(change.current)}</p>
                    </div>
                    <div>
                      <span>Restore point</span>
                      <p>{formatRestoreValue(change.restore)}</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
            {(restorePreview.comparison.addedServices.length > 0 || restorePreview.comparison.removedServices.length > 0) && (
              <div className="restore-preview-services">
                {restorePreview.comparison.addedServices.length > 0 && (
                  <div>
                    <span>Services restored into model</span>
                    <p>{restorePreview.comparison.addedServices.slice(0, 12).join(', ')}</p>
                  </div>
                )}
                {restorePreview.comparison.removedServices.length > 0 && (
                  <div>
                    <span>Services removed from current model</span>
                    <p>{restorePreview.comparison.removedServices.slice(0, 12).join(', ')}</p>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </Modal>

      {/* Delete confirmation (folder or project) */}
      <Modal
        open={!!deleteTarget}
        danger
        modalHeading={
          deleteTarget?.kind === 'folder'
            ? `Delete folder "${(deleteTarget.node as FolderNode).name}"?`
            : `Delete project "${(deleteTarget?.node as ProjectNode)?.project || (deleteTarget?.node as ProjectNode)?.customer}"?`
        }
        primaryButtonText={projectsActionBusy ? 'Deleting…' : 'Delete'}
        secondaryButtonText="Cancel"
        primaryButtonDisabled={projectsActionBusy}
        onRequestSubmit={() => {
          if (!deleteTarget) return;
          if (deleteTarget.kind === 'folder') doDeleteFolder(deleteTarget.node as FolderNode);
          else doDeleteProject(deleteTarget.node as ProjectNode);
        }}
        onRequestClose={() => setDeleteTarget(null)}
      >
        {deleteTarget?.kind === 'folder' ? (
          <p style={{ color: '#525252', lineHeight: 1.6 }}>
            The folder and <strong>all projects inside it</strong> will be permanently removed from disk.
            This cannot be undone.
          </p>
        ) : (
          <p style={{ color: '#525252', lineHeight: 1.6 }}>
            The project directory and all its files (architecture JSON, uploads) will be permanently deleted.
            This cannot be undone.
          </p>
        )}
      </Modal>

    </>
  );
}
