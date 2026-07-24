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

type Component = {
  name: string;
  purpose?: string;
  region?: string;
  source?: string;
};

type Architecture = {
  project: { name: string; environment?: string };
  ibm_cloud: Record<string, Component[] | string[]>;
  sources?: Array<{ file: string; type: string; records: number }>;
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

type AnsweredQuestion = AnsweredQuestionType;

type PendingComponent = {
  id: string;
  name: string;
  suggestedKey: string;
  confidence: number;
  notes?: string;
};

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
const ACCEPTED_FILE_TYPES = ['.xlsx', '.csv', '.tsv', '.json', '.md', '.txt'];
const IBM_CLOUD_KEYS = [
  'regions', 'vpcs', 'zones', 'subnets', 'connectivity', 'ingress',
  'compute', 'data', 'private_endpoints', 'dns', 'security', 'observability', 'backup_dr',
];

async function postJson<T>(url: string, body: unknown): Promise<T> {
  const response = await fetch(url, { method: 'POST', headers: API_HEADERS, body: JSON.stringify(body) });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.error || `Request failed: ${response.status}`);
  }
  return response.json();
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

// Re-export utilities for tests
export { questionKey, mergeQuestions };

export default function App() {
  // Wizard state
  const [step, setStep] = useState<Step>('upload');
  const [activeNav, setActiveNav] = useState<'wizard' | 'settings'>('wizard');

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
  const [diagramPath, setDiagramPath]     = useState('');
  const [requirementsText, setRequirementsText] = useState('');
  const [requirementsSaved, setRequirementsSaved] = useState(false);
  const requirementsFileRef = useRef<HTMLInputElement>(null);
  const [previewXml, setPreviewXml]       = useState<string | null>(null);
  const [previewReady, setPreviewReady]   = useState(false);
  const previewRef = useRef<HTMLIFrameElement>(null);

  // UI state
  // Holds XML pending delivery to a diagrams.net popup (Option C)
  const pendingPopupXml = useRef<string | null>(null);

  const [status, setStatus]   = useState('');
  const [error, setError]     = useState('');
  const [busy, setBusy]       = useState(false);

  // Settings state
  const [settings, setSettings]           = useState<AppSettings>(DEFAULT_SETTINGS);
  const [ollamaModels, setOllamaModels]   = useState<string[]>([]);
  const [settingsStatus, setSettingsStatus] = useState('');
  const [connectionStatus, setConnectionStatus] = useState<'idle' | 'ok' | 'fail'>('idle');

  // Project state
  const [projectTree, setProjectTree]     = useState<ProjectNode[]>([]);
  const [activeProject, setActiveProject] = useState<ProjectNode | null>(null);
  const [showNewProjectModal, setShowNewProjectModal] = useState(false);
  const [newCustomerName, setNewCustomerName] = useState('');
  const [newProjectName, setNewProjectName]   = useState('');
  const importInputRef = useRef<HTMLInputElement>(null);

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

    refreshProjectTree();
  }, []);

  // ── Project helpers ──────────────────────────────────────────────────────────

  function refreshProjectTree() {
    fetch('/api/projects')
      .then((r) => r.json())
      .then((data: { projects: ProjectNode[] }) => setProjectTree(data.projects || []))
      .catch(() => {});
  }

  async function createProject() {
    if (!newCustomerName.trim()) return;
    try {
      const result = await postJson<{ path: string }>('/api/projects', {
        customer: newCustomerName.trim(),
        project: newProjectName.trim() || undefined,
      });
      setShowNewProjectModal(false);
      setNewCustomerName('');
      setNewProjectName('');
      refreshProjectTree();
      setStatus(`Project created: ${result.path}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create project');
    }
  }

  function selectProject(node: ProjectNode) {
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
    setPreviewXml(null);
    setRequirementsText('');
    setRequirementsSaved(false);
    setStatus('');
    setError('');
    setActiveNav('wizard');
    setStep('upload');
  }

  function exportArchitecture() {
    if (!activeProject) return;
    const a = document.createElement('a');
    a.href = `/api/project-export?path=${encodeURIComponent(activeProject.path)}`;
    a.download = 'architecture.json';
    a.click();
  }

  async function importArchitecture(file: File) {
    if (!activeProject) return;
    const body = new FormData();
    body.append('path', activeProject.path);
    body.append('architecture', file, 'architecture.json');
    try {
      await postForm('/api/project-import', body);
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

  async function uploadAndRunIntake() {
    setBusy(true);
    setError('');
    setStatus('Uploading and parsing files…');
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
      if (payload.pendingComponents?.length) {
        setPendingComponents(payload.pendingComponents);
      }
      setStatus(`Parsed ${payload.files.length} file${payload.files.length === 1 ? '' : 's'} — ${payload.questions.length} design question${payload.questions.length === 1 ? '' : 's'} found`);
      // Auto-advance: if there are pending low-confidence components stay on review, else go to questions
      setStep(payload.pendingComponents?.length ? 'review' : 'questions');
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
      await postJson('/api/answer', { architecturePath, area: question.area, question: question.question, answer, source: 'architect' });
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
      await postJson('/api/answer', { architecturePath, area: question.area, question: question.question, answer, source: 'coaching' });
    } catch { console.warn('Failed to persist coaching answer'); }
  }

  async function saveRequirements(text: string, source: 'text' | 'file', filename = '') {
    if (!text.trim()) return;
    try {
      await postJson('/api/requirements', {
        architecturePath,
        requirements: text.trim(),
        source,
        filename,
      });
      setRequirementsSaved(true);
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
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to confirm components');
    } finally {
      setBusy(false);
    }
  }

  // ── Diagram ──────────────────────────────────────────────────────────────────

  async function generateDiagram() {
    setBusy(true);
    setError('');
    setStatus('Generating diagram…');
    try {
      const payload = await postJson<{ outputPath: string }>('/api/generate-drawio', {
        architecture, architecturePath, diagramType,
        outputPath: `outputs/network-picasso-${diagramType}.drawio`,
      });
      setDiagramPath(payload.outputPath);
      setStatus('Draw.io file saved to ' + payload.outputPath);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Diagram generation failed');
      setStatus('');
    } finally {
      setBusy(false);
    }
  }

  async function copyDiagramXml() {
    setBusy(true);
    try {
      const response = await fetch('/api/drawio-xml', {
        method: 'POST', headers: API_HEADERS,
        body: JSON.stringify({ architecture, diagramType }),
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
        body: JSON.stringify({ architecture, diagramType }),
      });
      if (!response.ok) throw new Error('Failed to get XML');
      const xml = await response.text();
      // Store the XML so the message listener can deliver it once the popup fires
      // its 'init' event — same protocol as the inline preview (Option D).
      pendingPopupXml.current = xml;
      window.open(
        'https://embed.diagrams.net/?embed=1&proto=json&spin=1&analytics=0',
        '_blank',
        'noopener,width=1200,height=800',
      );
      setStatus('Opening diagrams.net — diagram will load automatically when the editor is ready.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Open failed');
    } finally {
      setBusy(false);
    }
  }

  async function loadPreview() {
    if (!architecture) return;
    setBusy(true);
    setError('');
    try {
      const response = await fetch('/api/drawio-xml', {
        method: 'POST', headers: API_HEADERS,
        body: JSON.stringify({ architecture, diagramType }),
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
          // Option C — popup window: deliver pending XML then clear it
          const xml = pendingPopupXml.current;
          if (xml && event.source) {
            (event.source as Window).postMessage(
              JSON.stringify({ action: 'load', xml }),
              'https://embed.diagrams.net',
            );
            pendingPopupXml.current = null;
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

  // ── Render ───────────────────────────────────────────────────────────────────

  return (
    <>
      <Header aria-label="Network Picasso">
        <HeaderName href="#" prefix="IBM Cloud">
          Network Picasso
        </HeaderName>
      </Header>

      <SideNav aria-label="Workspace navigation" expanded isPersistent>
        <SideNavItems>
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
          <SideNavLink renderIcon={Add} onClick={() => setShowNewProjectModal(true)}>
            New project
          </SideNavLink>
          {/* Dynamic project tree */}
          {(() => {
            const customers = Array.from(new Set(projectTree.map((n) => n.customer)));
            return customers.map((customer) => {
              const nodes = projectTree.filter((n) => n.customer === customer);
              const hasSubs = nodes.some((n) => n.project);
              if (hasSubs) {
                return (
                  <SideNavMenu key={customer} title={customer} renderIcon={IbmCloud}>
                    {nodes.map((node) => (
                      <SideNavMenuItem
                        key={node.path}
                        isActive={activeProject?.path === node.path}
                        onClick={() => selectProject(node)}
                      >
                        {node.project || customer}
                      </SideNavMenuItem>
                    ))}
                  </SideNavMenu>
                );
              }
              return nodes.map((node) => (
                <SideNavLink
                  key={node.path}
                  renderIcon={IbmCloud}
                  isActive={activeProject?.path === node.path}
                  onClick={() => selectProject(node)}
                >
                  {node.isLegacy ? 'Unsaved workspace' : node.customer}
                </SideNavLink>
              ));
            });
          })()}
        </SideNavItems>
      </SideNav>

      {/* New Project Modal */}
      <Modal
        open={showNewProjectModal}
        modalHeading="New project"
        primaryButtonText="Create"
        secondaryButtonText="Cancel"
        onRequestSubmit={createProject}
        onRequestClose={() => setShowNewProjectModal(false)}
        onSecondarySubmit={() => setShowNewProjectModal(false)}
      >
        <Stack gap={5}>
          <TextInput id="new-customer-name" labelText="Customer name" placeholder="Acme Bank"
            value={newCustomerName}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNewCustomerName(e.target.value)} />
          <TextInput id="new-project-name" labelText="Project name (optional)" placeholder="Q1 Modernisation"
            value={newProjectName}
            onChange={(e: React.ChangeEvent<HTMLInputElement>) => setNewProjectName(e.target.value)} />
          <p style={{ fontSize: '0.875rem', color: '#525252' }}>
            Leave project name blank to create a single-project customer folder.
          </p>
        </Stack>
      </Modal>

      <Content className="app-content">
        <Grid className="workspace" fullWidth>

          {/* ── Page header ── */}
          <Column sm={4} md={8} lg={16}>
            <div className="page-heading">
              <div>
                <p className="eyebrow">IBM Cloud architecture workbench</p>
                <h1>{activeNav === 'settings' ? 'Settings' : STEP_LABELS[step]}</h1>
                {activeNav !== 'settings' && (
                  <p className="eyebrow" style={{ marginTop: '0.25rem' }}>{STEP_DESCRIPTIONS[step]}</p>
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
                      <h2>Source files parsed</h2>
                      <div className="source-list">
                        {(architecture?.sources || []).map((src) => (
                          <div className="source-item" key={src.file}>
                            <strong>{src.file}</strong>
                            <span>{src.type} · {src.records} records</span>
                          </div>
                        ))}
                      </div>
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
                      items={['context', 'logical', 'deployment']}
                      onChange={({ selectedItem }) => selectedItem && setDiagramType(String(selectedItem))}
                    />
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
    </>
  );
}
