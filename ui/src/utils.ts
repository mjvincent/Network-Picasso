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
