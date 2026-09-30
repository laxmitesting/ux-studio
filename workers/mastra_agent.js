import { Agent } from "@mastra/core/agent";
import { openai } from "@ai-sdk/openai";

const agent = new Agent({
  name: "MastraFrontendArchitect",
  instructions:
    "You are an expert Frontend Architect and UX Engineer. Return only raw, valid HTML5 documents with encapsulated CSS in a <style> tag.",
  model: openai("gpt-5.4-mini"),
});

async function main() {
  const chunks = [];
  for await (const chunk of process.stdin) {
    chunks.push(chunk);
  }
  const prompt = Buffer.concat(chunks).toString("utf-8");

  try {
    const result = await agent.generate(prompt);
    process.stdout.write(result.text || "");
  } catch (err) {
    process.stderr.write(String(err));
    process.exit(1);
  }
}

main();