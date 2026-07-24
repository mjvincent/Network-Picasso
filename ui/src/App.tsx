import {
  Button,
  Column,
  Content,
  Dropdown,
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
  TextInput,
  Tile,
} from '@carbon/react';
import {
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
};

const API_HEADERS = { 'Content-Type': 'application/json' };

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

export default function App() {
  const [projectName, setProjectName] = useState('OmniCare');
  const [inputPath, setInputPath] = useState('examples/customer-inputs');
  const [architecturePath, setArchitecturePath] = useState('examples/omnicare/intake-architecture.json');
  const [diagramType, setDiagramType] = useState('deployment');
  const [architecture, setArchitecture] = useState<Architecture | null>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [diagramPath, setDiagramPath] = useState('');
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetch('/api/example')
      .then((response) => response.json())
      .then((payload) => {
        setArchitecture(payload.architecture);
        setQuestions(payload.questions);
        setArchitecturePath(payload.architecturePath);
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
        projectName,
        outputPath: architecturePath,
      });
      setArchitecture(payload.architecture);
      setQuestions(payload.questions);
      setArchitecturePath(payload.outputPath);
      setStatus('Architecture model updated');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Intake failed');
      setStatus('');
    } finally {
      setBusy(false);
    }
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
                <p className="eyebrow">Local architecture workbench</p>
                <h1>IBM Cloud diagram intake</h1>
              </div>
              <div className="status-line">
                {busy && <InlineLoading description={status} />}
                {!busy && status && <Tag type="green">{status}</Tag>}
                {error && <Tag type="red">{error}</Tag>}
              </div>
            </div>
          </Column>

          <Column sm={4} md={4} lg={5}>
            <Tile className="panel">
              <Stack gap={6}>
                <h2>Inputs</h2>
                <TextInput
                  id="project-name"
                  labelText="Project name"
                  value={projectName}
                  onChange={(event) => setProjectName(event.target.value)}
                />
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

          <Column sm={4} md={4} lg={6}>
            <Tile className="panel">
              <Stack gap={5}>
                <h2>Open Design Questions</h2>
                <div className="question-list">
                  {questions.length === 0 && <p>No open questions detected.</p>}
                  {questions.map((item) => (
                    <Layer key={`${item.area}-${item.question}`}>
                      <div className="question-item">
                        <Tag type="blue">{item.area}</Tag>
                        <p>{item.question}</p>
                      </div>
                    </Layer>
                  ))}
                </div>
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
                <Button renderIcon={Diagram} onClick={generateDiagram} disabled={busy}>
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

          <Column sm={4} md={8} lg={7}>
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
