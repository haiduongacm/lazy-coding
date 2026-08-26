"""AXI design principles for agent-native CLI tools."""

PRINCIPLES = [
    {
        "id": 1,
        "name": "Token-efficient output",
        "summary": "Use TOON format for ~40% token savings over JSON",
    },
    {
        "id": 2,
        "name": "Minimal default schemas",
        "summary": "3-4 fields per list item, not 10+",
    },
    {
        "id": 3,
        "name": "Content truncation",
        "summary": "Truncate large text with size hints and --full escape hatch",
    },
    {
        "id": 4,
        "name": "Pre-computed aggregates",
        "summary": "Include aggregated counts/statuses to eliminate round trips",
    },
    {
        "id": 5,
        "name": "Definitive empty states",
        "summary": "Explicit '0 results' rather than ambiguous empty output",
    },
    {
        "id": 6,
        "name": "Structured errors",
        "summary": "Idempotent mutations, structured errors, no interactive prompts",
    },
    {
        "id": 7,
        "name": "Ambient context",
        "summary": "Install opt-in session integrations first",
    },
    {
        "id": 8,
        "name": "Content first",
        "summary": "Running with no arguments shows live data, not help text",
    },
    {
        "id": 9,
        "name": "Contextual disclosure",
        "summary": "Include next-step suggestions after each output",
    },
    {
        "id": 10,
        "name": "Consistent help",
        "summary": "Concise per-subcommand reference when agents need it",
    },
]
