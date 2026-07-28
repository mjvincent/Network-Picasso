// Shared utility functions extracted from App.tsx for testability.

export type Question = {
  area: string;
  question: string;
  guidance?: string;
  source?: 'rules' | 'llm';
};

export type AnsweredQuestion = {
  area: string;
  question: string;
  answer: string;
  source: string;
  timestamp: string;
};

export type ProjectFilterStatus = 'all' | 'withArchitecture' | 'withoutArchitecture';
export type ProjectSortOrder = 'nameAsc' | 'nameDesc' | 'projectCountDesc' | 'architectureFirst' | 'needsArchitectureFirst';

export type ProjectFolderLike = {
  name: string;
  projectCount: number;
  childCount?: number;
};

export type ProjectNodeLike = {
  customer: string;
  project: string;
  path: string;
  hasArchitecture: boolean;
};

export function questionKey(question: Question): string {
  return `${question.area}:${question.question}`;
}

export function mergeQuestions(
  existing: Question[],
  incoming: Question[],
  answered: AnsweredQuestion[],
): Question[] {
  const answeredTexts = new Set(answered.map((a) => a.question));
  const merged = new Map(existing.map((question) => [questionKey(question), question]));
  incoming.forEach((question) => {
    if (!answeredTexts.has(question.question)) {
      merged.set(questionKey(question), {
        ...merged.get(questionKey(question)),
        ...question,
      });
    }
  });
  // Remove any existing questions that are now answered.
  for (const key of merged.keys()) {
    const q = merged.get(key)!;
    if (answeredTexts.has(q.question)) {
      merged.delete(key);
    }
  }
  return Array.from(merged.values());
}

function normalizedSearch(value: string): string {
  return value.trim().toLowerCase();
}

function compareByName(a: string, b: string): number {
  return a.localeCompare(b, undefined, { sensitivity: 'base', numeric: true });
}

export function filterAndSortProjectFolders<T extends ProjectFolderLike>(
  folders: T[],
  query: string,
  sortOrder: ProjectSortOrder,
): T[] {
  const term = normalizedSearch(query);
  const filtered = term
    ? folders.filter((folder) => folder.name.toLowerCase().includes(term))
    : folders;
  return [...filtered].sort((a, b) => {
    if (sortOrder === 'nameDesc') return compareByName(b.name, a.name);
    if (sortOrder === 'projectCountDesc') {
      return b.projectCount - a.projectCount || compareByName(a.name, b.name);
    }
    return compareByName(a.name, b.name);
  });
}

export function filterAndSortProjects<T extends ProjectNodeLike>(
  projects: T[],
  query: string,
  status: ProjectFilterStatus,
  sortOrder: ProjectSortOrder,
): T[] {
  const term = normalizedSearch(query);
  const filtered = projects.filter((project) => {
    if (status === 'withArchitecture' && !project.hasArchitecture) return false;
    if (status === 'withoutArchitecture' && project.hasArchitecture) return false;
    if (!term) return true;
    return [
      project.customer,
      project.project,
      project.path,
      project.hasArchitecture ? 'has architecture' : 'needs architecture',
    ].some((value) => value.toLowerCase().includes(term));
  });
  return [...filtered].sort((a, b) => {
    const aName = a.project || a.customer;
    const bName = b.project || b.customer;
    if (sortOrder === 'nameDesc') return compareByName(bName, aName);
    if (sortOrder === 'architectureFirst') {
      return Number(b.hasArchitecture) - Number(a.hasArchitecture) || compareByName(aName, bName);
    }
    if (sortOrder === 'needsArchitectureFirst') {
      return Number(a.hasArchitecture) - Number(b.hasArchitecture) || compareByName(aName, bName);
    }
    return compareByName(aName, bName);
  });
}
