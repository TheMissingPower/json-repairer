// How this plugin's page draws its task's output: the repaired text, laid out, with the verdict's first
// difference when there is one. Every other output is drawn from its JSON Schema. Each renderer is
// (value, {task, verdict, send}) => Element.
import { h } from "./kit/components.js";

function pretty(text) {
  try {
    return JSON.stringify(JSON.parse(text), null, 2);
  } catch {
    return text;
  }
}

function drawRepair(answer, { verdict } = {}) {
  const where = verdict && verdict.details ? verdict.details.first_difference : null;
  return h(
    "div",
    { class: "repair" },
    h("p", { class: "heading", text: `Repaired JSON, ${answer.repaired_json.length} characters` }),
    where ? h("p", { class: "difference", text: `First difference from the original at ${where}` }) : null,
    h("pre", { class: "json", text: pretty(answer.repaired_json) }),
  );
}

export default { RepairOutput: drawRepair };
