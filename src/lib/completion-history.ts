import type { GrokMsg } from "./grok-contract.ts";

/** Keep recent dialogue within the server's 32-message / 32,000-character limits. */
export function completionMessages(
  system: string,
  user: string,
  history: readonly GrokMsg[] = [],
): GrokMsg[] {
  // Instructions and the current prompt have priority over historical context.
  // If these alone exceed the contract, retain them for server validation rather
  // than silently changing the instruction or current question.
  let remaining = 32000 - system.length - user.length;
  const recent: GrokMsg[] = [];
  const dialogue = history.filter(
    (message) =>
      (message.role === "user" || message.role === "assistant") && message.content.trim(),
  );
  for (let index = dialogue.length - 1; index >= 0 && recent.length < 30; index--) {
    const message = dialogue[index];
    if (message.content.length > remaining) break;
    recent.push({ role: message.role, content: message.content });
    remaining -= message.content.length;
  }
  recent.reverse();
  // Do not present an assistant answer after dropping the user turn it answered.
  while (recent[0]?.role === "assistant") recent.shift();
  return [{ role: "system", content: system }, ...recent, { role: "user", content: user }];
}
