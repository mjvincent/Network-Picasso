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
  Layer,
  SideNav,
  SideNavItems,
  SideNavLink,
  Stack,
  StructuredListBody,
  StructuredListCell,
  StructuredListHead,
  StructuredListRow,
  StructuredListWrapper,
  Tag,
  TextArea,
  TextInput,
  Tile,
} from '@carbon/react';
import {
  Checkmark,
  Diagram,
  DocumentImport,
  IbmCloud,
  ListChecked,
  Renew,
  Settings,
} from '@carbon/icons-react';
import { useEffect, useMemo, useState } from 'react';

type Component = {
  name: string;
  purpose?: string;
  region?: string;
  source?: string;
};

type Architecture = {
  project: {
    name: string;
    environment?: string;
  };
  ibm_cloud: Record<string, Component[] | string[]>;
  sources?: Array<{ file: string; type: string; records: number }>;
};

type Question = {
  area: string;
  question: string;
  guidance?: string;
};

const API_HEADERS = { 'Content-Type': 'application/json' };
const ACCEPTED_FILE_TYPES = ['.xlsx', '.csv', '.tsv', '.json', '.md', '.txt'];

async function postJson<T>(url: string, body: unknown): Promise<T> {
  const response = await fetch(url, {
    method: 'POST',
    headers: API_HEADERS,
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.error || `Request failed: ${response.status}`);
  }
  return response.json();
}

async function postForm<T>(url: string, body: FormData): Promise<T> {
  const response = await fetch(url, {
    method: 'POST',
    body,
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.error || `Request failed: ${response.status}`);
  }
  return response.json();
}

function questionKey(question: Question): string {
  return `${question.area}:${question.question}`;
}

function mergeQuestions(existing: Question[], incoming: Question[]): Question[] {
  const merged = new Map(existing.map((question) => [questionKey(question), question]));
  incoming.forEach((question) => {
    merged.set(questionKey(question), {
      ...merged.get(questionKey(question)),
      ...question,
    });
  });
  return Array.from(merged.values());
}

export default function App() {
  const [projectName, setProjectName] = useState('');
  const [inputPath, setInputPath] = useState('examples/sample-inputs');
  const [architecturePath, setArchitecturePath] = useState('examples/sample/architecture.json');
  const [diagramType, setDiagramType] = useState('deployment');
  const [architecture, setArchitecture] = useState<Architecture | null>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [questionAnswers, setQuestionAnswers] = useState<Record<string, string>>({});
  const [answeredQuestions, setAnsweredQuestions] = useState<Record<string, string>>({});
  const [diagramPath, setDiagramPath] = useState('');
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetch('/api/example')
      .then((response) => response.json())
      .then((payload) => {
        setArchitecture(payload.architecture);
        setQuestions((current) => mergeQuestions(current, payload.questions));
        setArchitecturePath(payload.architecturePath);
        setProjectName('');
      })
      .catch(() => {
        setStatus('Start the local API to load the example workspace.');
      });
  }, []);

  const summary = useMemo(() => {
    if (!architecture) {
      return [];
    }
    return Object.entries(architecture.ibm_cloud)
      .filter(([, value]) => Array.isArray(value))
      .map(([key, value]) => ({
        key,
        count: (value as unknown[]).length,
      }))
      .filter((item) => item.count > 0);
  }, [architecture]);

  const openQuestions = useMemo(
    () => questions.filter((question) => !answeredQuestions[questionKey(question)]),
    [answeredQuestions, questions]
  );

  async function runIntake() {
    setBusy(true);
    setError('');
    setStatus('Running intake');
    try {
      const payload = await postJson<{
        architecture: Architecture;
        questions: Question[];
        outputPath: string;
      }>('/api/intake', {
        inputPath,
        projectName: projectName || 'Sample Architecture',
        outputPath: architecturePath,
      });
      setArchitecture(payload.architecture);
      setQuestions((current) => mergeQuestions(current, payload.questions));
      setArchitecturePath(payload.outputPath);
      setStatus('Architecture model updated');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Intake failed');
      setStatus('');
    } finally {
      setBusy(false);
    }
  }

  async function uploadAndRunIntake() {
    setBusy(true);
    setError('');
    setStatus('Uploading and parsing files');
    try {
      const body = new FormData();
      body.append('projectName', projectName || 'Customer Architecture');
      selectedFiles.forEach((file) => body.append('files', file));
      const payload = await postForm<{
        architecture: Architecture;
        questions: Question[];
        inputPath: string;
        outputPath: string;
        files: string[];
      }>('/api/upload-intake', body);
      setArchitecture(payload.architecture);
      setQuestions((current) => mergeQuestions(current, payload.questions));
      setInputPath(payload.inputPath);
      setArchitecturePath(payload.outputPath);
      setDiagramPath('');
      setStatus(`Parsed ${payload.files.length} file${payload.files.length === 1 ? '' : 's'}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload intake failed');
      setStatus('');
    } finally {
      setBusy(false);
    }
  }

  function addFiles(files: File[]) {
    const validFiles = files.filter((file) =>
      ACCEPTED_FILE_TYPES.some((extension) => file.name.toLowerCase().endsWith(extension))
    );
    setSelectedFiles((current) => {
      const existing = new Set(current.map((file) => `${file.name}:${file.size}`));
      const next = [...current];
      validFiles.forEach((file) => {
        const key = `${file.name}:${file.size}`;
        if (!existing.has(key)) {
          next.push(file);
        }
      });
      return next;
    });
  }

  function removeFile(name: string) {
    setSelectedFiles((current) => current.filter((file) => file.name !== name));
  }

  function updateAnswer(question: Question, answer: string) {
    setQuestionAnswers((current) => ({
      ...current,
      [questionKey(question)]: answer,
    }));
  }

  function saveAnswer(question: Question) {
    const key = questionKey(question);
    const answer = questionAnswers[key]?.trim();
    if (!answer) {
      setStatus('');
      setError('Add an answer before marking the question complete.');
      return;
    }
    setError('');
    setAnsweredQuestions((current) => ({
      ...current,
      [key]: answer,
    }));
    setStatus('Design answer saved');
  }

  function acceptCoaching(question: Question) {
    const key = questionKey(question);
    const answer = question.guidance || question.question;
    setQuestionAnswers((current) => ({
      ...current,
      [key]: answer,
    }));
    setAnsweredQuestions((current) => ({
      ...current,
      [key]: answer,
    }));
    setError('');
    setStatus('Best-practice guidance accepted');
  }

  async function generateDiagram() {
    setBusy(true);
    setError('');
    setStatus('Generating Draw.io');
    try {
      const payload = await postJson<{ outputPath: string }>('/api/generate-drawio', {
        architecture,
        architecturePath,
        diagramType,
        outputPath: `outputs/network-picasso-${diagramType}.drawio`,
      });
      setDiagramPath(payload.outputPath);
      setStatus('Draw.io file generated');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Diagram generation failed');
      setStatus('');
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <Header aria-label="Network Picasso">
        <HeaderName href="#" prefix="IBM Cloud">
          Network Picasso
        </HeaderName>
      </Header>
      <SideNav aria-label="Workspace navigation" expanded isPersistent>
        <SideNavItems>
          <SideNavLink renderIcon={DocumentImport} isActive>
            Intake
          </SideNavLink>
          <SideNavLink renderIcon={ListChecked}>Questions</SideNavLink>
          <SideNavLink renderIcon={IbmCloud}>Model</SideNavLink>
          <SideNavLink renderIcon={Diagram}>Diagram</SideNavLink>
          <SideNavLink renderIcon={Settings}>Settings</SideNavLink>
        </SideNavItems>
      </SideNav>
      <Content className="app-content">
        <Grid className="workspace" fullWidth>
          <Column sm={4} md={8} lg={16}>
            <div className="page-heading">
              <div>
                <p className="eyebrow">Guided local architecture workbench</p>
                <h1>Start with BOM and pricing files</h1>
              </div>
              <div className="status-line">
                {busy && <InlineLoading description={status} />}
                {!busy && status && <Tag type="green">{status}</Tag>}
                {error && <Tag type="red">{error}</Tag>}
              </div>
            </div>
          </Column>

          <Column sm={4} md={8} lg={7}>
            <Tile className="panel upload-panel">
              <Stack gap={6}>
                <div>
                  <h2>Upload source material</h2>
                  <p className="panel-copy">
                    Add a BOM, IBM Cloud Solutioning pricing export, architecture notes, or supporting customer data.
                  </p>
                </div>
                <TextInput
                  id="project-name"
                  labelText="Project name"
                  value={projectName}
                  placeholder="Customer or project name"
                  onChange={(event) => setProjectName(event.target.value)}
                />
                <FileUploaderDropContainer
                  id="source-files"
                  labelText="Drag files here or click to upload"
                  multiple
                  accept={ACCEPTED_FILE_TYPES}
                  onAddFiles={(_event, { addedFiles }) => addFiles(addedFiles)}
                />
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
                <Button renderIcon={DocumentImport} onClick={uploadAndRunIntake} disabled={busy || selectedFiles.length === 0}>
                  Parse files
                </Button>
              </Stack>
            </Tile>
          </Column>

          <Column sm={4} md={8} lg={4}>
            <Tile className="panel">
              <Stack gap={6}>
                <div>
                  <h2>Use local folder</h2>
                  <p className="panel-copy">For repeat runs, point to a local folder inside this repository.</p>
                </div>
                <TextInput
                  id="input-path"
                  labelText="Input folder or file"
                  value={inputPath}
                  onChange={(event) => setInputPath(event.target.value)}
                />
                <TextInput
                  id="architecture-path"
                  labelText="Architecture JSON"
                  value={architecturePath}
                  onChange={(event) => setArchitecturePath(event.target.value)}
                />
                <Button renderIcon={Renew} onClick={runIntake} disabled={busy}>
                  Run intake
                </Button>
              </Stack>
            </Tile>
          </Column>

          <Column sm={4} md={8} lg={5}>
            <Tile className="panel">
              <Stack gap={5}>
                <h2>Diagram</h2>
                <Dropdown
                  id="diagram-type"
                  titleText="Diagram type"
                  label="Select diagram type"
                  selectedItem={diagramType}
                  items={['context', 'logical', 'deployment']}
                  onChange={({ selectedItem }) => selectedItem && setDiagramType(String(selectedItem))}
                />
                <Button renderIcon={Diagram} onClick={generateDiagram} disabled={busy || !architecture}>
                  Generate Draw.io
                </Button>
                {diagramPath && (
                  <div className="artifact-path">
                    <span>Output</span>
                    <code>{diagramPath}</code>
                  </div>
                )}
              </Stack>
            </Tile>
          </Column>

          <Column sm={4} md={8} lg={9}>
            <Tile className="panel">
              <Stack gap={5}>
                <div>
                  <h2>Guided Design Questions</h2>
                  <p className="panel-copy">
                    Answer what you know. Use the coaching notes when a design decision is unclear.
                  </p>
                </div>
                <div className="question-list">
                  {openQuestions.length === 0 && <p>No open questions detected.</p>}
                  {openQuestions.map((item, index) => (
                    <Layer key={`${item.area}-${item.question}`}>
                      <div className="question-item">
                        <Tag type="blue">{item.area}</Tag>
                        <p>{item.question}</p>
                        {item.guidance && (
                          <div className="coaching">
                            <span>Best-practice coaching</span>
                            <p>{item.guidance}</p>
                          </div>
                        )}
                        <TextArea
                          id={`answer-${index}`}
                          labelText="Your answer"
                          placeholder="Capture the design decision, assumption, or follow-up needed."
                          value={questionAnswers[questionKey(item)] || ''}
                          onChange={(event) => updateAnswer(item, event.target.value)}
                        />
                        <div className="question-actions">
                          {item.guidance && (
                            <Button kind="tertiary" size="sm" onClick={() => acceptCoaching(item)}>
                              Accept coaching
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
              </Stack>
            </Tile>
          </Column>

          <Column sm={4} md={8} lg={7}>
            <Tile className="panel">
              <Stack gap={5}>
                <h2>Architecture Model</h2>
                <StructuredListWrapper aria-label="Architecture model summary">
                  <StructuredListHead>
                    <StructuredListRow head>
                      <StructuredListCell head>Area</StructuredListCell>
                      <StructuredListCell head>Detected</StructuredListCell>
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
              </Stack>
            </Tile>
          </Column>

          <Column sm={4} md={8} lg={9}>
            <Tile className="panel">
              <Stack gap={5}>
                <h2>Sources</h2>
                <div className="source-list">
                  {(architecture?.sources || []).map((source) => (
                    <div className="source-item" key={source.file}>
                      <strong>{source.file}</strong>
                      <span>
                        {source.type} · {source.records} records
                      </span>
                    </div>
                  ))}
                </div>
              </Stack>
            </Tile>
          </Column>
        </Grid>
      </Content>
    </>
  );
}
