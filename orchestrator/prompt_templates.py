from pydantic import BaseModel, Field
from typing import List

VALID_FRAMEWORKS = ["agno", "google_adk", "strands", "mastra", "maf"]

class DesignSystem(BaseModel):
    brand_color: str = Field(
        description="Core brand accent hex code, e.g. #2563EB or #10B981. Must remain legible as an accent in both light and dark themes."
    )
    canvas_theme: str = Field(
        description="Default baseline mood: 'light' (e.g. #F8FAFC canvas with dark text) or 'dark' (e.g. #0B0F19 canvas with light text)."
    )
    cta_color: str = Field(
        description="High-contrast action hex code strictly for primary CTAs and buttons."
    )
    typography_mood: str = Field(
        description="Typographic character matching the UX angle (e.g., 'Modern geometric sans-serif', 'Warm editorial serif', 'Precision monospace')."
    )
    layout_hierarchy: str = Field(
        description="Structural UX flow, e.g. 'Problem-Agitation-Solution with sticky CTA', 'Split-screen interactive demo', 'Bento-grid feature breakdown'."
    )

class CopyBrief(BaseModel):
    hero_headline: str = Field(
        description="Crisp, benefit-driven hero headline directly tied to this angle's primary value proposition."
    )
    subheadline: str = Field(
        description="1-2 sentences explaining how the product delivers on the headline promise for this specific persona."
    )
    key_benefits: List[str] = Field(
        description="Exactly 3 concrete product capabilities or outcomes relevant to this persona. Avoid vague buzzwords."
    )
    cta_label: str = Field(
        description="Action-oriented button label reflecting user intent for this angle, e.g. 'Start Free Trial', 'Explore the Specs'."
    )

class AngleTask(BaseModel):
    angle_name: str = Field(
        description="Concise name of this value proposition angle, e.g. 'Frictionless Daily Routine' or 'Enterprise Compliance'."
    )
    target_persona: str = Field(
        description="Specific user segment or mindset addressed, including their primary pain point and motivation."
    )
    framework: str = Field(
        description="Assigned worker framework. Must be one of: agno, google_adk, strands, mastra, maf."
    )
    design_system: DesignSystem
    copy_brief: CopyBrief

class OrchestratorResponse(BaseModel):
    product_core_insight: str = Field(
        description="Core UX thesis distilled from the brief: what genuine problem this product solves and why it matters."
    )
    tasks: List[AngleTask] = Field(
        description="Exactly 5 distinct UX angle tasks, one assigned to each valid framework."
    )


ORCHESTRATOR_SYSTEM_PROMPT = """
You are a Principal Product & UX Strategist.
Your objective is to analyze a product brief and extract exactly 5 distinct, viable value proposition angles inherent to the product.

Each angle represents a genuine user persona, a unique problem-solution narrative, or a distinct mental model for how someone perceives value in this specific product.

---

### UX STRATEGY GUIDELINES

1. Grounded in Product Reality:
   - Derive every angle directly from features, use cases, and problems mentioned or reasonably inferred from the brief.
   - If the brief is for developer tooling, angles should focus on things like workflow speed, observability, integration, or reliability. If it's for consumer hardware, focus on daily habit integration, tactile build quality, aesthetics, or ease of cleaning.

2. Structural & Narrative Diversity:
   - The 5 angles must not just rephrase each other. Each must tackle a distinct friction point or user motivation.
   - Vary the `layout_hierarchy` to match the mental model (e.g., analytical users get data-dense comparisons; busy users get quick-scan problem-solution flows).

3. Accessible, Intentional Design Systems:
   - Ensure `primary_color` and `background_color` have strong WCAG-compliant contrast.
   - Use `accent_color` sparingly for interactive affordances and primary buttons.
   - Avoid defaulting every task to generic SaaS blue (#0066FF) and pure white (#FFFFFF). Use dark canvases, warm off-whites, earth tones, or slate gray where appropriate for the product context.

4. Framework Routing:
   - Assign each of the 5 tasks a unique framework from: agno, google_adk, strands, mastra, maf.
   - Treat frameworks as headless runtime workers. Do NOT alter your UX strategy based on the framework name.

---

### WHAT TO AVOID (CRITICAL CONSTRAINTS)

- AVOID Superficial Variations: Do not produce 5 angles that say the same thing using synonyms (e.g., "Fast Setup", "Quick Onboarding", and "Speedy Configuration" are duplicates—combine them into one and find a different angle).
- AVOID Generic Marketing Buzzwords: Never write headlines or benefits containing empty filler like "Revolutionize your workflow", "Supercharge your productivity", "Next-gen platform", or "All-in-one solution" unless qualified by specific product mechanisms.
- AVOID Fabricating Non-Existent Capabilities: Do not invent major enterprise features, hardware specs, or integrations that contradict or wildly exceed the scope of the provided product brief.
- AVOID Design Inconsistencies: Do not select pastel or low-contrast text against light backgrounds, and do not assign clashing aesthetic moods (e.g., pairing a serious enterprise security persona with playful neon cartoon styling).
- AVOID Duplicate Framework Assignments: Never assign the same framework to more than one task. All 5 frameworks must be utilized exactly once.
"""