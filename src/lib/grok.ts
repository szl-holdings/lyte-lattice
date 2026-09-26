import { createServerFn } from "@tanstack/react-start";
import { validateCompleteInput, type GrokResult } from "./grok-contract";
export { clampCompleteInput, grokRequestBody } from "./grok-contract";
export type {
  GrokMsg,
  GrokOk,
  GrokErr,
  GrokResult,
  CompleteInput,
  JsonSchemaSpec,
} from "./grok-contract";

export const completeGrok = createServerFn({ method: "POST" })
  .validator(validateCompleteInput)
  .handler(async ({ data }): Promise<GrokResult> => {
    // Server-only transport (reads XAI_API_KEY); keep it out of the browser bundle.
    const { completeOnce } = await import("./grok-stream.server");
    return completeOnce(data);
  });
