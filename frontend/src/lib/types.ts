export type Question = {
  id: string;
  concept_id: string;
  subject: string;
  difficulty: number;
  stem: string;
  options: string[];
  correct_index: number;
  explanation?: string;
  bilingual_hint?: string | null;
  source?: string;
};

export type GradedAnswer = {
  question_id: string;
  chosen_index: number;
  correct: boolean;
  score: number;
  rationale?: string;
  misconception?: string | null;
};

export type Readiness = {
  coverage: number;
  mastery: number;
  revision: number;
  mock_trend: number;
  readiness: number;
  computed_at?: string;
};

export type PlanBlock = {
  subject: string;
  concept_id: string;
  minutes: number;
  activity: "learn" | "quiz" | "review" | "drill";
  note?: string;
};

export type PlanDay = {
  date: string;
  blocks: PlanBlock[];
  total_minutes: number;
};

export type WeeklyPlan = {
  generated_at?: string;
  rationale?: string;
  focus_concepts: string[];
  days: PlanDay[];
};

export type RankPrediction = {
  expected_readiness: number;
  readiness_low: number;
  readiness_high: number;
  expected_percentile: number;
  percentile_low: number;
  percentile_high: number;
  days_to_exam: number;
  samples: number;
};

export type Dashboard = {
  user_id: string;
  target_exam: string;
  exam_date: string | null;
  daily_hours: number;
  streak_days: number;
  plan: WeeklyPlan;
  readiness: Readiness;
  readiness_history: { timestamp: string; readiness: number }[];
  mastery: Record<string, number>;
  subject_mastery: Record<string, number>;
  rank_prediction: RankPrediction | null;
  nudge: { en?: string; hi?: string };
};

export type AgentStep = {
  agent: "orchestrator" | "planner" | "quizmaster" | "analyst" | "companion" | "system";
  headline: string;
  detail: string;
  payload: Record<string, unknown>;
  timestamp: string;
};

export type DiagnosticStartResponse = {
  user_id: string;
  questions: Question[];
};

export type DiagnosticSubmitResponse = {
  user_id: string;
  run_id: string;
  readiness: Readiness;
  plan: WeeklyPlan;
  nudge: { en?: string; hi?: string };
  mastery: Record<string, number>;
  trace_count: number;
};

// Mental health types
export type MoodEntry = {
  timestamp: string;
  score: number;
  tags: string[];
  note?: string;
};

export type CheckinResponse = {
  response_en: string;
  response_hi: string;
  detected_mood_score: number;
  mood_tags: string[];
  coping_suggestion: string;
  escalation_needed: boolean;
  follow_up_question?: string;
};

export type ChatResponse = {
  conversation_id: string;
  response_en: string;
  response_hi: string;
  mood_tags: string[];
  coping_suggestion: string;
  escalation_needed: boolean;
  parent_alerted: boolean;
};

export type MoodHistory = {
  mood_history: MoodEntry[];
  stress_level: number;
  mental_health_flags: Record<string, unknown>;
};

// Schedule / accountability types
export type StudySessionStatus = "pending" | "quiz_pending" | "completed" | "skipped" | "quiz_passed" | "quiz_failed";

export type StudySessionItem = {
  id: string;
  plan_date: string;
  concept_id: string;
  subject: string;
  activity: string;
  scheduled_minutes: number;
  status: StudySessionStatus;
  quiz_score?: number | null;
  completed_at?: string | null;
};

export type TodaySchedule = {
  date: string;
  sessions: StudySessionItem[];
  consecutive_misses: number;
  summary: { total: number; completed: number; skipped: number };
};

export type RealityCheckResult = {
  score: number;
  passed: boolean;
  graded_answers: GradedAnswer[];
  feedback_en: string;
  feedback_hi: string;
};

export type FriendStats = {
  user_id: string;
  display_name: string;
  target_exam: string;
  streak_days: number;
  readiness: number;
  coverage: number;
  mastery_avg: number;
  top_subjects: { subject: string; score: number }[];
  daily_hours: number;
  exam_date: string | null;
  is_self: boolean;
};

export type FriendsLeaderboard = {
  user_id: string;
  my_id: string;
  leaderboard: FriendStats[];
};

export type WeeklySummary = {
  completed: number;
  skipped: number;
  quiz_passed: number;
  quiz_failed: number;
  consecutive_misses: number;
  parent_alerted: boolean;
};
