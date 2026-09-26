import type { Project, StageResult } from "@/types/contracts";

export type StageViewProps<A> = {
  artifact: A;
  result: StageResult;
  project: Project;
  busy: boolean;
  /** Re-run this stage with inputs (RunStageRequest.inputs). */
  run: (inputs: Record<string, unknown>) => Promise<void>;
  /** PUT this stage's artifact (UpdateStageRequest). */
  save: (artifact: A, validate?: boolean) => Promise<void>;
  /** Run another stage, then show it. */
  runOther: (n: number, inputs: Record<string, unknown>) => Promise<void>;
  goto: (n: number) => void;
  onAutorun: () => void;
};
