# AI architecture

AI supports learning; it does not run it. It reviews what the learner wrote and prepares drafts from
what the learner saved. Progress, XP and unlocking are decided by deterministic backend rules and
never by a model's answer.

## Capability registry

`api/src/peopleforce/modules/ai/capabilities.py`

| Capability | Kind | Prompt | Output model | Context it may see |
|---|---|---|---|---|
| `freelance_offer_feedback` | feedback | `freelance_offer_feedback` | `WritingFeedback` | quiz labels, the exercise, the submission |
| `professional_bio_feedback` | feedback | `professional_bio_feedback` | `WritingFeedback` | + approved `freelancer_offer` |
| `generate_platform_draft` | generation | `generate_platform_draft` | `PlatformDraft` | quiz labels, approved offer and bio, platform format rules |

Each capability declares its prompt name and label, output schema, the asset types it may read,
`max_tokens` and an optional timeout. Content refers to a capability **by name only**
(`aiReviewAction.capability`); an unknown name is rejected.

```python
class WritingFeedback(BaseModel):
    summary: str
    strengths: list[str]            # max 3
    improvements: list[Improvement] # max 3, {issue, suggestion}
    clarity_score: int              # 1..5
    specificity_score: int          # 1..5
    suggested_one_liner: str

class PlatformDraft(BaseModel):
    title: str
    body: str
    notes: list[str]                # max 3
```

`generate_platform_draft` picks the platform from the learner's preferred channel (Upwork, Fiverr,
LinkedIn; "direct" and "not sure" use LinkedIn) and passes that platform's format requirements.

## Provider abstraction

`infrastructure/ai/providers.py`

```python
class LlmProvider(Protocol):
    name: str
    model: str
    async def generate_structured(self, *, system, user, output_model, max_tokens, timeout) -> BaseModel
```

| `LLM_PROVIDER` | Adapter | Structured output |
|---|---|---|
| `gemini` | `GeminiProvider` (google-genai SDK) | `response_schema` + JSON mode, then validated again with Pydantic |
| `anthropic` | `AnthropicProvider` (anthropic SDK) | `messages.parse(output_format=Model)` |
| `none` | – | AI actions answer `503 ai_not_configured`; lessons remain completable |

`LLM_MODEL` selects the model id. Every adapter raises `LlmError(retryable=…)`; nothing else in the
app knows which provider is in use. Tested live with Gemini (`gemini-3.5-flash-lite`). The Anthropic
adapter is written against the SDK documentation but has not been run against the live API.

## Prompts

- **Langfuse** is the primary store when `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` are set:
  `get_prompt(name, label="production")`, 3-second fetch timeout.
- **Local fallback**: `modules/ai/prompts/<name>.md`, first line `version: N`. Used when Langfuse is not
  configured, unreachable, or has no such prompt.
- The resolved version (`langfuse:<n>` or `local:<n>`) is stored on every `ai_generations` row.
- The three prompts exist in Langfuse (version 1, label `production`). Edit them there to change
  behaviour without a deploy; move the `production` label to roll forward or back.

The prompt text is the system message. The user message is a JSON object, never string-concatenated
into the prompt, and the prompt states that submission text is material to review, not instructions.

## Context construction

`AiService.run` builds the user message:

```json
{
  "learner": {"specialization": "Backend / APIs", "experience": "1–3 years", "freelance_stage": "Never",
              "already_has": ["Existing work samples"], "preferred_channel": "Upwork", "goal": "Get my first client"},
  "approved_assets": [{"type": "freelancer_offer", "content": {…}}],
  "exercise": {"lesson": "…", "task": "…", "goal": "…"},
  "submission": [{"question": "What can you build?", "answer": "…"}]
}
```

- `learner` holds the explicit quiz answers as labels. The email and name are never sent.
- `approved_assets` contains only asset types the capability declares, and only approved ones.
- Every prompt forbids inventing clients, employers, projects, results, numbers, testimonials,
  certifications or years of experience, and tells the model to use a bracketed placeholder for a
  missing fact.

## Validation, storage, drafts

1. The provider returns JSON constrained by the schema.
2. It is validated with the capability's Pydantic model. A failure is treated like a provider failure.
3. Feedback is stored in `action_attempts.result`. A generated draft is stored as a
   `freelancer_assets` row with `origin = 'ai'`, `status = 'draft'`.
4. A draft becomes `approved` only through `POST /assets/{id}/approve`. Editing it
   (`PATCH /assets/{id}`) sets `origin = 'user'`. Only approved assets are reused as model context
   or count toward achievements.

## Tracing (Langfuse)

Verified live against the project's Langfuse (US region), following Langfuse's "what does a good trace
look like" guidance. Code: `infrastructure/ai/prompts.py` (`PromptStore.trace`, `.generation`) and
`modules/ai/service.py`.

| Aspect | What is sent |
|---|---|
| Scope | One trace per AI task (one feedback request, one draft). |
| Trace / root name | Verb-first and stable, from `Capability.trace_name`: `review-freelance-offer`, `review-professional-bio`, `generate-platform-draft`. Never contains ids or model names. |
| Root observation (`span`) | Input: the learner's answers (feedback) or the task (draft). Output: the validated result. This is what the traces table and evaluators read. |
| Model call (`generation`) | Named `generate-feedback` / `generate-draft`, nested under the root. Input as role-labelled messages (system prompt + user JSON), output as an assistant message. |
| Model, parameters, tokens | `model`, `model_parameters` (max output tokens, response format), `usage_details` (`input_tokens`, `output_tokens`, `reasoning_tokens` when the model thinks) returned by the provider adapter. |
| Prompt link | The generation is linked to the Langfuse prompt version it used. The three prompts were uploaded as text prompts with the `production` label; the local files remain the fallback. |
| User | `user_id` = internal user UUID (never the email). |
| Session | `"<user id>:<lesson id>"` for lesson feedback, so repeated requests on one draft read as one thread. |
| Tags | `ai-feedback` or `ai-generation`, plus the capability name. |
| Metadata | `capability`, `lesson_id`, `action_key`, `prompt_version` (empty values omitted). |
| Environment | `APP_ENV` (`development`, `production`), so test traffic can be filtered out. |
| Errors | Provider or validation failures mark the generation and the root `ERROR` with the reason. |
| Flush | The client is shut down (flushed) when the API stops. |

Every `ai_generations` row stores the Langfuse `trace_id`, so an audit row leads to its trace.
Tracing can never fail a request: without keys every call is a no-op, and prompt fetching falls back to
the local file after 3 seconds.

Known gaps:

- **Cost is empty.** `gemini-3.5-flash-lite` is not in Langfuse's price table. Add a model definition
  with its per-token prices in Langfuse (Settings → Models) and cost is computed from the token counts
  already sent.
- **Learner text is sent to Langfuse** (it is the thing being reviewed). No email or name is included.
  Turn on Langfuse masking if that text must not leave your infrastructure.
- **No thinking text** is captured: the configured model does not return reasoning. The adapter already
  reports reasoning token counts when present.
- **No quality scores yet.** There is no thumbs-up/down on feedback in the UI to send as a Langfuse score.

## Failure modes

| Failure | Response | What the learner keeps |
|---|---|---|
| Provider error, timeout, rate limit | `503 ai_unavailable` (`details.retryable`) | Draft already saved; retry or finish without feedback |
| Output fails validation | `503 ai_unavailable` | same |
| Model declines | `503 ai_unavailable`, `retryable: false` | same |
| AI not configured | `503 ai_not_configured`; UI disables the button | same |
| Daily limit (`AI_DAILY_LIMIT_PER_USER`, default 30) | `429 ai_limit_reached` | same |
| Langfuse down | local prompt is used; tracing skipped | no visible effect |

The failed attempt is still recorded in `ai_generations`. Because the source text is submitted by a
separate action before any AI call, an AI failure can never lose it
(`tests/test_first_run_flow.py::test_ai_failure_keeps_the_submission_and_the_lesson_completable`).

## Endpoints

| Endpoint | Purpose |
|---|---|
| `POST /journey/lessons/{id}/actions/{ai_review_key}` | Feedback on a saved draft |
| `POST /assets/platform-draft` | Generate or regenerate the platform draft (needs a saved offer) |
| `PATCH /assets/{id}` | Edit a generated draft |
| `POST /assets/{id}/approve` | Accept a draft |
| `GET /assets` | List the learner's assets |

Saved assets are listed on the profile page. Generating, editing and approving the platform draft are implemented and tested in the API but have **no buttons yet**.
