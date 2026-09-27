# How trailmind's agentic loop works: tool calling and reasoning

This is a plain-language walkthrough of `run_agent()` — the reasoning
loop that lets trailmind's assistant call `search_destination_knowledge`
on its own, look at the result, and decide what to do next before
answering the user. It assumes no prior background in agent frameworks
or LLM tool calling, and every example is pulled from the real code in
this repo (`agent/app/services/chat_service.py`, `agent/app/llm.py`,
`agent/app/services/knowledge_service.py`, `agent/app/main.py`, and the
tests) — not a hypothetical framework.

If you haven't read `docs/chunking_embedding.md` yet, that one covers
what happens *inside* `search_destination_knowledge` (chunking,
embeddings, pgvector search). This doc is about the layer above it:
how the assistant decides to call that tool at all, and what it does
with the answer.

## 1. What "agentic loop" actually means here

A plain LLM call is stateless and single-shot: you send some text, the
model sends back some text, done. There's no way for the model to
*do* anything — it can only generate words based on what it already
knows or what you put in the prompt. If you ask "best tailor shops in
Hoi An" to a plain model with no tools, it either makes something up
from training data or admits it doesn't know current shop names.

trailmind's loop is different: the model is given a **tool** — a
described action it's allowed to request — and instead of always
answering in one shot, the loop lets the model take multiple *turns*
before producing a final answer. On any given turn the model can
either (a) write a normal answer, or (b) ask the surrounding code to
run a specific function with specific arguments and show it the
result, after which it gets another turn to actually answer.

Concretely, here's what actually happens for "best tailor shops in
Hoi An" (this is the scenario `test_tool_call_result_fed_back_and_final_answer_returned`
in `agent/tests/test_agent.py` encodes deterministically):

- **Round 1**: the model reads the system prompt + the user's
  question and decides it doesn't have this information itself. It
  doesn't write a reply. Instead it returns a request: "call
  `search_destination_knowledge` with `destination=da_nang_hoi_an,
  query=tailors`."
- The trailmind code (not the model) actually runs that Python
  function, gets back ranked snippets from the vector database, and
  appends the result to the conversation as a new message.
- **Round 2**: the model is called again, now with the tool's result
  sitting in front of it. This time it has what it needs, so it
  writes an actual answer: "Try Nathan Tailors."

The key distinction to hold onto throughout this doc: **the model
decides** whether to call a tool, which tool, and with what
arguments — that's a decision made inside the LLM. **The code
decides** how to run the tool, how to catch its errors, how many
rounds to allow, and when to give up. Neither side does the other's
job.

## 2. The core data structure: `messages` is the loop's entire state

Unlike a chatbot with a database of conversation history, this loop's
state (for a single call to `run_agent()`) is just one Python list of
dicts, called `messages`, that gets appended to as the loop runs and
sent back to the model in full on every round. This matches
CLAUDE.md's project-wide model, one level down: CLAUDE.md says trip
state lives in Supabase and only a compact summary gets rehydrated
into context each turn; within a *single* `run_agent()` call, the
`messages` list is that turn's entire working memory — everything the
model can "see" is in this list, nothing is implicit.

Each entry has a `role` (`system`, `user`, `assistant`, or `tool`) and
content appropriate to that role. Here's exactly what it looks like at
each step of the tailor-shop example, matching `agent.py` line by
line.

**Start of `run_agent()`** (`agent.py` lines 85-88):

```python
messages: list[dict] = [
    {"role": "system", "content": SYSTEM_PROMPT},
    {"role": "user", "content": user_message},
]
```

The **system prompt** is an instruction message that isn't from the
user — it sets the assistant's persona, ground rules, and boundaries,
and is included on every round. trailmind's is defined right in
`agent.py`:

```python
SYSTEM_PROMPT = (
    "You are trailmind, a trip-planning assistant. You help plan trips "
    "incrementally by answering questions using the search_destination_knowledge "
    "tool, which is backed by a travel knowledge base.\n\n"
    f"The knowledge base only covers these destinations: {', '.join(sorted(KNOWN_DESTINATIONS))}. "
    "If asked about anywhere else, say so plainly rather than guessing from "
    "general knowledge. Cite what you learn from the tool; don't invent "
    "specifics (prices, names, addresses) it didn't return."
)
```

Note this is where trailmind's "don't invent details" policy actually
lives — not as code that filters the model's output, but as an
instruction the model reads and (hopefully) follows. There's no code
anywhere checking whether the model made up a hotel name; the loop
relies on the model to hold up its end.

**After round 1** (`agent.py` lines 96-110), once the model has
requested a tool call, two more messages get appended:

```python
# the model's own turn, recorded so it (and we) remember it asked for this
{
    "role": "assistant",
    "content": "",  # turn.content was None here
    "tool_calls": [
        {"id": "call_1", "function": {
            "name": "search_destination_knowledge",
            "arguments": {"destination": "da_nang_hoi_an", "query": "tailors"},
        }},
    ],
},
# the tool's result, fed back as if it were a message in the conversation
{
    "role": "tool",
    "tool_call_id": "call_1",
    "content": '{"snippets": [{"rank": 1, "text": "Tailor shops...", "source_url": "https://x", "section_path": "Buy", "distance": 0.2}]}',
},
```

Two things worth noticing: the `tool_call_id` on the tool message
matches the `id` the model gave in its request, so the model can line
up which result answers which call (this matters more once a model
makes several calls in one round — see Section 4). And the tool's
result is serialized to a JSON *string* (`json.dumps(result)`) — from
the model's point of view a tool result is just more text it reads,
same as a user message, not a special structured object.

**Round 2**: the whole `messages` list above (now 4 entries) is sent
back to the model. This time it has what it needs and returns
`content="Try Nathan Tailors."` with no tool call, so `run_agent()`
returns that string and the loop ends. The final `messages` list is
never persisted anywhere past this — trailmind's actual trip state
(per CLAUDE.md) lives in Supabase, not in this list; this list is
scratch space for a single reasoning turn.

## 3. What a "tool" is from the model's perspective

A "tool" here is also called "function calling" in most model
documentation — same concept, two names. The important thing is that
the model isn't just told about the tool in English; it's given a
machine-readable schema so it knows exactly what arguments to produce
and in what shape. Natural language ("you can search a knowledge
base") isn't enough for a model to reliably emit `{"destination":
"da_nang_hoi_an", "query": "tailors"}` — it needs the parameter names,
types, and which are required, the same way a function signature tells
you that in code.

trailmind's schema, `TOOL_SCHEMA` in `agent.py`, is standard JSON
Schema wrapped in the "function" shape most providers (Ollama's API
included) expect:

```python
TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "search_destination_knowledge",
        "description": (
            "Search the travel knowledge base for a destination. "
            f"Only covers: {', '.join(sorted(KNOWN_DESTINATIONS))}."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "destination": {
                    "type": "string",
                    "description": "One of the known destination slugs.",
                },
                "query": {
                    "type": "string",
                    "description": "Free-text search query.",
                },
            },
            "required": ["destination", "query"],
        },
    },
}
```

This is passed to `llm.chat(messages, tools=[TOOL_SCHEMA])` on
*every* round (`agent.py` line 91) — the model doesn't "remember" the
tool exists between calls any more than it remembers anything else; the
loop hands it the full toolset again each time.

When the model decides to use a tool, the response comes back with a
`tool_calls` field instead of (or alongside) plain `content`. Here's
the actual shape Ollama returns, straight from
`agent/tests/test_llm.py`'s `test_parses_tool_call_response`:

```python
{
    "message": {
        "role": "assistant",
        "content": "",
        "tool_calls": [
            {
                "id": "call_1",
                "function": {
                    "name": "search_destination_knowledge",
                    "arguments": {"destination": "bangkok", "query": "street food"},
                },
            }
        ],
    }
}
```

Compare that to a plain-text response with no tool call
(`test_parses_plain_text_response`):

```python
{"message": {"role": "assistant", "content": "Hello!"}}
```

Same endpoint, same request shape — the *only* difference is whether
`tool_calls` shows up in the response. `OllamaLLMClient.chat()`
(`llm.py` lines 47-75) parses either shape into a uniform `LLMTurn`
dataclass:

```python
@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict

@dataclass
class LLMTurn:
    content: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)
```

So the rest of the codebase (`agent.py`) never touches Ollama's raw
JSON at all — it only ever deals with `LLMTurn`/`ToolCall` objects.
That's a deliberate seam; more on it in Section 8.

## 4. The loop mechanics, walked through

Here's the actual loop (`agent.py` lines 90-117), read line by line:

```python
for _ in range(max_tool_rounds):
    turn = llm.chat(messages, tools=[TOOL_SCHEMA])

    if not turn.tool_calls:
        return turn.content or ""

    messages.append({...assistant message with tool_calls...})
    for tc in turn.tool_calls:
        result = _run_tool(tc.name, tc.arguments, conn)
        messages.append({"role": "tool", "tool_call_id": tc.id, "content": json.dumps(result)})

# fell through the loop without a final answer
return "I wasn't able to put together an answer after checking the knowledge base a few times..."
```

1. **Call the model** with the full `messages` list so far, plus the
   tool schema.
2. **Check what came back.** If there's no `tool_calls`, the model
   decided it's done reasoning and wrote an answer — return it
   immediately. This is the exit condition; most of the time (a
   simple question) this happens on the very first round.
3. **If there are tool calls, dispatch each one.** The assistant's own
   "I want to call this" message is appended first (so the
   conversation has a record of what was requested), then the loop
   iterates over every tool call the model asked for in this round —
   `search_destination_knowledge` only ever produces one call per
   round in trailmind's tests, but the loop doesn't assume that; a
   model is allowed to request several tool calls in a single turn
   (e.g. if it wanted destinations Bangkok and Tokyo info at once,
   some models would emit two tool calls together), and each gets its
   own `_run_tool()` invocation and its own `tool` message appended,
   matched up by `tool_call_id`.
4. **Loop again.** After appending the tool result(s), the `for` loop
   goes around again and calls the model with the now-longer
   `messages` list. The model sees its own prior request and the
   result, and from there can either answer or ask for another tool
   call — chaining as many rounds as it needs (up to the cap).

This is a genuine loop rather than a fixed "call tool once, then
answer" pipeline because the model might legitimately need more than
one round — e.g., asking a follow-up query to the same tool with
different arguments if the first result wasn't quite what it needed.
`search_destination_knowledge` is a simple enough tool that in
practice this usually resolves in one round, but the loop structure
doesn't hardcode that assumption anywhere; it only hardcodes an upper
bound (Section 6).

## 5. Error handling: the LLM reads the error, not just the code

`_run_tool()` (`agent.py` lines 61-75) is where a tool call actually
gets executed:

```python
def _run_tool(name: str, arguments: dict, conn) -> dict:
    if name != "search_destination_knowledge":
        return {"error": f"unknown tool '{name}'"}

    try:
        snippets = search_destination_knowledge(
            destination=arguments.get("destination", ""),
            query=arguments.get("query", ""),
            conn=conn,
        )
        return {"snippets": [dataclasses.asdict(s) for s in snippets]}
    except UnknownDestinationError as e:
        return {"error": str(e)}
    except (EmbeddingError, VectorStoreError) as e:
        return {"error": f"knowledge base temporarily unavailable: {e}"}
```

`search_destination_knowledge` (`tools.py`) is written to *never*
fail silently — per its own docstring, it either returns real
snippets or raises one of three typed exceptions:
`UnknownDestinationError` (asked about somewhere outside the 4-city
knowledge base), `EmbeddingError` (Ollama's embedding model is
unreachable — see `docs/chunking_embedding.md` section 3), or
`VectorStoreError` (the pgvector database is unreachable).

The important design choice is what `_run_tool()` does with those
exceptions: it **catches them and turns them into an ordinary `{"error":
...}` dict**, which then gets JSON-serialized and appended as a normal
`role: "tool"` message, exactly like a success result. It does not
re-raise, and it does not decide what to tell the user. The next
`llm.chat()` call hands that error text to the model as just another
message to read, and the *model* decides — in its own next turn —
whether to apologize, rephrase and retry with different arguments, or
say something else entirely.

This is a direct, literal implementation of CLAUDE.md's stated
philosophy:

> Tools return structured results or a typed error — never silent
> failure. No fixed retry/surface policy: the agent decides whether to
> retry, work around, or surface the error to the user, based on the
> situation.

"The agent decides" isn't a metaphor here — it means the error string
becomes text sitting in the `messages` list, and the LLM literally
reads it before writing its reply. `agent/tests/test_agent.py` proves
this end to end. In `test_unknown_destination_error_fed_back_to_llm`,
the mocked tool raises `UnknownDestinationError("'bali' is not
covered")`, and the test asserts the resulting tool message (what the
model would have read) contains `"not covered"`, and that the
scripted "model's" next turn responds with "Sorry, I don't have
information on Bali." In
`test_embedding_error_fed_back_as_tool_result_not_raised`, an
`EmbeddingError` gets wrapped as `"knowledge base temporarily
unavailable: ollama down"` and fed back the same way — the test name
itself calls out that this is fed back, *not* raised up through
`run_agent()`. Nothing in `_run_tool()` decides "apologize" vs. "try
again" — that judgment call was pushed up into the model's own next
turn, on purpose.

Contrast this with `LLMError` in `llm.py` — raised when Ollama itself
is unreachable or returns a malformed response. That one *does*
propagate out of `run_agent()` uncaught, because it's not a tool
failure the model can reason about (there's no model to hand it to —
the model is the thing that's unreachable). `main.py` catches it at
the HTTP boundary instead and turns it into a 503:

```python
try:
    reply = run_agent(req.message, conn=conn)
except LLMError as e:
    raise HTTPException(status_code=503, detail=str(e)) from e
```

So there are two different failure layers with two different
handlers: tool-level failures are recoverable by the model and get fed
back into the conversation; LLM-infrastructure failures aren't
recoverable by anything inside the loop and get surfaced as an HTTP
error instead.

## 6. The `max_tool_rounds` guard: an infra decision, not a model decision

```python
MAX_TOOL_ROUNDS = 3
...
for _ in range(max_tool_rounds):
    ...
return "I wasn't able to put together an answer after checking the knowledge base a few times..."
```

Given that CLAUDE.md's philosophy is "the agent decides," it might
seem inconsistent that there's a hard cap the model has no say in.
But this cap exists for a different reason than the error-handling
policy above: it's a cost and safety guard against a model that gets
stuck calling tools indefinitely (a buggy model response, a
tool that keeps returning something the model doesn't recognize as
sufficient, etc.), not a judgment call about *how* to handle a
specific error. No matter how good the model's reasoning is, an
agentic loop that calls out to a live LLM and a live database on every
round needs *some* upper bound, or a single bad conversation can spin
forever, burning API/compute cost the whole time. That's an
infrastructure concern, decided once in code, not something to
delegate per-conversation to the thing you're trying to bound.

`test_gives_up_after_max_tool_rounds` in `test_agent.py` exercises
this directly: a `FakeLLMClient` scripted to always return a tool call
(never a final answer) is capped at `max_tool_rounds=2`, and the test
asserts the loop gives up gracefully with a message asking the user to
rephrase, rather than looping forever or crashing.

## 7. Testing the loop without a real LLM: `FakeLLMClient`

Calling a real model in every test would be slow, nondeterministic
(the exact wording changes run to run), and require Ollama running
locally. `agent/tests/test_agent.py` sidesteps all of that with a
tiny fake that implements the same interface as the real client:

```python
class FakeLLMClient:
    """Returns pre-scripted turns in order, one per .chat() call."""

    def __init__(self, turns: list[LLMTurn]):
        self._turns = list(turns)
        self.calls: list[list[dict]] = []

    def chat(self, messages, tools):
        self.calls.append(messages)
        return self._turns.pop(0)
```

It doesn't call any model at all — it just pops the next
pre-scripted `LLMTurn` off a list, in order, and separately records
every `messages` list it was called with. This lets a test script
*exactly* the model behavior it wants to verify the loop handles
correctly — e.g. "first turn: request a tool call with these specific
arguments; second turn: return this specific final answer" — and then
assert on both the return value and the exact shape of `messages` at
each call (`llm.calls[1][-1]` is "the last message the model saw on
its second call," which the tests use to check the tool result really
did get appended correctly, with the right content).

The point isn't just convenience — it's a separation of concerns.
`FakeLLMClient` tests are testing `run_agent()`'s *loop logic*: does
it append messages correctly, does it dispatch tool calls, does it
catch the right exceptions, does it respect `max_tool_rounds`. None of
that has anything to do with whether a real model is any good at
deciding when to call a tool. That's a genuinely reusable idea beyond
this project: whenever you're testing a system that calls out to a
nondeterministic external decision-maker (an LLM, but the same idea
applies to e.g. a third-party ranking API), you can get fast,
deterministic, fully-controllable tests by faking that piece to return
a scripted sequence of decisions, and testing everything your own code
does in response to each one.

## 8. The provider-swap seam: `LLMClient` as a `Protocol`

```python
class LLMClient(Protocol):
    def chat(self, messages: list[dict], tools: list[dict]) -> LLMTurn: ...
```

`Protocol` (from `typing`) is Python's way of doing **structural
typing** ("duck typing" with type-checker support): `OllamaLLMClient`
never declares `implements LLMClient` anywhere — it just happens to
have a `chat(self, messages, tools) -> LLMTurn` method with a matching
signature, and that's enough for it to count as an `LLMClient`
wherever one is expected (including in `run_agent()`'s type hint,
`llm: LLMClient | None = None`). `FakeLLMClient` from Section 7 is a
second example of the exact same thing — it also isn't declared as an
`LLMClient` anywhere, it just structurally matches.

This is the seam the file's own docstring calls out explicitly:

> OllamaLLMClient is the only implementation for now (local, no API
> key/cost). An AnthropicLLMClient implementing the same LLMClient
> protocol can be added later (Messages API tool use) without
> changing app/services/chat_service.py — that's the seam this
> interface exists for.

Concretely: `run_agent()` only ever calls `llm.chat(messages,
tools=[TOOL_SCHEMA])` and reads `turn.content` / `turn.tool_calls`. It
never touches Ollama's HTTP API, its JSON shape, or any Ollama-specific
detail — all of that is isolated inside `OllamaLLMClient.chat()`,
which does the translation from Ollama's actual response format into
the neutral `LLMTurn`/`ToolCall` dataclasses. If trailmind later adds
Anthropic's API as an alternative model provider, an
`AnthropicLLMClient` would need to do the equivalent translation from
Anthropic's Messages API tool-use format into the same `LLMTurn`
shape — and `agent.py`'s loop wouldn't need a single line changed,
because it was never written against Ollama's format in the first
place, only against the neutral one. This was a decision made early
(per the docstring) specifically so that swap wouldn't require
touching the loop logic later.

## 9. Where this loop meets the RAG pipeline

The tool call is the one place these two systems touch. From
`run_agent()`'s point of view, `search_destination_knowledge` is just
a Python function with a name, a docstring-derived JSON schema, and a
contract (typed snippets or a typed error) — the loop has no idea, and
doesn't need to know, that calling it triggers an embedding request to
Ollama's `nomic-embed-text` model and a cosine-distance nearest-neighbor
query against pgvector under the hood. That entire pipeline — chunking
the source documents, embedding them, storing them, and embedding the
live query to search against them — is described in
`docs/chunking_embedding.md`. This doc's loop only cares about the
function's signature and its two possible outcomes (snippets, or a
typed error); everything about *how* those snippets get found is
opaque to it by design, which is exactly what makes tool calling a
useful boundary — the reasoning loop and the retrieval pipeline can
each change independently as long as the function signature and error
types stay the same.

## 10. Key terms glossary

- **Agentic loop** — a multi-round exchange with a model where, instead
  of one prompt producing one final answer, the model can request
  actions (tool calls), see their results, and use those results to
  decide its next move — including asking for more actions — before
  producing a final answer. `run_agent()`'s `for` loop is trailmind's
  implementation of this.
- **Tool calling / function calling** — the mechanism by which a model,
  instead of writing prose, returns a structured request naming a
  function and the arguments to call it with. The two names refer to
  the same mechanism; different providers/docs favor one term or the
  other.
- **Tool schema** — a JSON Schema description of a tool's name,
  purpose, and parameters (types, descriptions, which are required)
  given to the model alongside the conversation, so it can produce
  well-formed arguments rather than guessing from a prose description.
  `TOOL_SCHEMA` in `agent.py` is trailmind's.
- **System prompt** — a message with `role: "system"` that sets the
  model's persona and ground rules, included on every round of the
  loop, distinct from the user's own messages.
- **Conversation state / `messages` as state** — in this loop, the
  entire history of what's happened (system prompt, user question,
  the model's tool requests, and each tool's results) lives in one
  ordinary Python list of dicts, rebuilt and resent to the model in
  full on every round. There's no hidden state anywhere else for the
  duration of one `run_agent()` call.
- **Typed error** — an error represented as a specific, named
  exception class (`UnknownDestinationError`, `EmbeddingError`,
  `VectorStoreError`) rather than a generic exception or a silently
  empty/wrong result, so callers can catch and handle each failure
  mode distinctly (per CLAUDE.md's "never silent failure").
- **Protocol / structural typing** — Python's `typing.Protocol` lets a
  class satisfy an interface just by having matching method
  signatures, with no explicit `implements`/inheritance declaration
  needed. `OllamaLLMClient` and `FakeLLMClient` both satisfy
  `LLMClient` this way, which is what lets either be passed into
  `run_agent()` interchangeably.
