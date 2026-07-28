import { describe, it, expect } from 'vitest';
import {
  filterAndSortProjectFolders,
  filterAndSortProjects,
  questionKey,
  mergeQuestions,
  type Question,
  type AnsweredQuestion,
} from '../utils';

const q1: Question = { area: 'Regions and availability', question: 'Which regions?', source: 'rules' };
const q2: Question = { area: 'VPC topology', question: 'How many VPCs?', source: 'rules' };
const q3: Question = { area: 'Compute', question: 'Which compute platform?', source: 'llm' };

function answered(question: Question, answer = 'Some answer'): AnsweredQuestion {
  return {
    area: question.area,
    question: question.question,
    answer,
    source: 'architect',
    timestamp: new Date().toISOString(),
  };
}

describe('questionKey', () => {
  it('returns a stable key for the same question', () => {
    expect(questionKey(q1)).toBe(questionKey({ ...q1 }));
  });

  it('returns different keys for different questions', () => {
    expect(questionKey(q1)).not.toBe(questionKey(q2));
  });
});

describe('mergeQuestions', () => {
  it('deduplicates when the same question appears in existing and incoming', () => {
    const result = mergeQuestions([q1], [q1, q2], []);
    const keys = result.map(questionKey);
    const unique = new Set(keys);
    expect(unique.size).toBe(keys.length);
    expect(result.length).toBe(2);
  });

  it('filters answered questions out of incoming', () => {
    const result = mergeQuestions([], [q1, q2], [answered(q1)]);
    expect(result).toHaveLength(1);
    expect(result[0].question).toBe(q2.question);
  });

  it('removes already-answered questions from existing', () => {
    const result = mergeQuestions([q1, q2], [], [answered(q2)]);
    expect(result).toHaveLength(1);
    expect(result[0].question).toBe(q1.question);
  });

  it('adds new incoming questions not present in existing', () => {
    const result = mergeQuestions([q1], [q3], []);
    expect(result).toHaveLength(2);
    const questions = result.map((q) => q.question);
    expect(questions).toContain(q1.question);
    expect(questions).toContain(q3.question);
  });
});

describe('project browser utilities', () => {
  it('filters and sorts customer folders', () => {
    const result = filterAndSortProjectFolders([
      { name: 'Zenith Health', projectCount: 1 },
      { name: 'Acme Bank', projectCount: 3 },
      { name: 'Acme Retail', projectCount: 2 },
    ], 'acme', 'projectCountDesc');

    expect(result.map((folder) => folder.name)).toEqual(['Acme Bank', 'Acme Retail']);
  });

  it('filters projects by architecture status and search term', () => {
    const result = filterAndSortProjects([
      { customer: 'Acme Bank', project: 'DR Design', path: '/acme/dr', hasArchitecture: true },
      { customer: 'Acme Bank', project: 'Discovery', path: '/acme/discovery', hasArchitecture: false },
      { customer: 'Contoso', project: 'Landing Zone', path: '/contoso/lz', hasArchitecture: false },
    ], 'acme', 'withoutArchitecture', 'nameAsc');

    expect(result).toHaveLength(1);
    expect(result[0].project).toBe('Discovery');
  });

  it('can sort projects that still need architecture first', () => {
    const result = filterAndSortProjects([
      { customer: 'Acme Bank', project: 'Ready', path: '/acme/ready', hasArchitecture: true },
      { customer: 'Acme Bank', project: 'Needs Work', path: '/acme/needs', hasArchitecture: false },
    ], '', 'all', 'needsArchitectureFirst');

    expect(result[0].project).toBe('Needs Work');
  });
});
