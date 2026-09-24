import assert from "node:assert/strict";
import { test } from "node:test";
import { completionMessages } from "./completion-history.ts";
import { validateCompleteInput, type GrokMsg } from "./grok-contract.ts";

const turns = (count: number, size: number): GrokMsg[] =>
  Array.from({ length: count }, (_, index) => ({
    role: index % 2 === 0 ? "user" : "assistant",
    content: `${index}:`.padEnd(size, "x"),
  }));

test("long Serve conversations fit the contract and retain the current prompt and instructions", () => {
  const history = turns(8, 6000);
  const before = structuredClone(history);
  const system = "Engine instructions.\n\nBound adapter instructions.";
  const user = "Newest question:".padEnd(7000, "q");
  // Reproduce the previously rejected eight-message Serve history.
  assert.throws(
    () =>
      validateCompleteInput({
        messages: [
          { role: "system", content: system },
          ...history,
          { role: "user", content: user },
        ],
      }),
    /32000/,
  );

  const messages = completionMessages(system, user, history);
  assert.doesNotThrow(() => validateCompleteInput({ messages }));
  assert.deepEqual(messages, [
    { role: "system", content: system },
    ...history.slice(-4),
    { role: "user", content: user },
  ]);
  assert.deepEqual(history, before);

  // The next long turn still works without clearing the stored conversation.
  const nextHistory: GrokMsg[] = [
    ...history,
    { role: "user", content: user },
    { role: "assistant", content: "Response".padEnd(6000, "a") },
  ];
  assert.doesNotThrow(() =>
    validateCompleteInput({
      messages: completionMessages(system, user, nextHistory.slice(-8)),
    }),
  );
});

test("history truncation preserves role order without orphaning an assistant response", () => {
  const history = turns(8, 6000);
  // Only three historical messages fit, so remove the oldest orphaned assistant.
  const messages = completionMessages("s".repeat(1000), "q".repeat(8000), history);
  assert.deepEqual(messages.slice(1, -1), history.slice(-2));
  assert.doesNotThrow(() => validateCompleteInput({ messages }));
});

test("oversized persisted turns and empty placeholders cannot trap future requests", () => {
  const history: GrokMsg[] = [
    { role: "user", content: "old question" },
    { role: "assistant", content: "x".repeat(40000) },
    { role: "assistant", content: " " },
  ];
  assert.deepEqual(completionMessages("Instructions", "Current question", history), [
    { role: "system", content: "Instructions" },
    { role: "user", content: "Current question" },
  ]);
});

test("short history stays unchanged and message-count limits reserve both mandatory messages", () => {
  const short = turns(4, 20);
  assert.deepEqual(
    completionMessages("Instructions", "Current question", short).slice(1, -1),
    short,
  );
  const long = turns(40, 20);
  const messages = completionMessages("Instructions", "Current question", long);
  assert.equal(messages.length, 32);
  assert.deepEqual(messages.slice(1, -1), long.slice(-30));
  assert.doesNotThrow(() => validateCompleteInput({ messages }));
});

test("an oversized instruction is preserved and still rejected by the server contract", () => {
  const system = "s".repeat(32000);
  const messages = completionMessages(system, "Current question", turns(8, 20));
  assert.equal(messages[0].content, system);
  assert.equal(messages.at(-1)?.content, "Current question");
  assert.throws(() => validateCompleteInput({ messages }), /32000/);
});
