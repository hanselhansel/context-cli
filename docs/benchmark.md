# Share-of-Recommendation Benchmark

The benchmark command tracks how often AI models mention and recommend your brand versus competitors across multiple prompts. It provides a quantitative measure of your brand's share of AI recommendations.

## What It Does

The benchmark:

1. Loads a set of prompts from a file
2. Sends each prompt to one or more LLM models multiple times
3. Analyzes responses for brand mentions and recommendations
4. Uses an LLM-as-judge to evaluate recommendation quality
5. Computes share-of-recommendation metrics across all prompts

## Usage

```bash
pip install context-linter[generate]
context-cli benchmark prompts.txt -b "YourBrand" -c "Competitor1" -c "Competitor2"
```

### Options

| Flag | Description |
|---|---|
| `--brand` / `-b` | Target brand to track (required) |
| `--competitor` / `-c` | Competitor brand to compare against (repeatable) |
| `--model` / `-m` | LLM model to query (repeatable, default: `gpt-4o-mini`) |
| `--runs` / `-r` | Number of runs per model per prompt (default: 3) |
| `--yes` / `-y` | Skip the cost confirmation prompt |
| `--json` | Output results as JSON |

## Prompts File

The prompts file can be either a CSV or plain text file.

### CSV format

CSV files should have columns `prompt`, `category`, and `intent`:

```csv
prompt,category,intent
"best project management tools for startups",productivity,informational
"Asana vs Monday.com comparison",productivity,comparison
"how to manage remote team tasks",productivity,how-to
```

### Plain text format

One prompt per line:

```
best project management tools for startups
Asana vs Monday.com comparison
how to manage remote team tasks
```

## Metrics

The benchmark computes several metrics:

- **Mention rate** -- percentage of responses that mention a brand
- **Recommendation rate** -- percentage of responses that recommend a brand (as judged by the LLM judge)
- **Share of recommendation** -- a brand's recommendation count as a percentage of all recommendations across tracked brands
- **Position** -- average position when the brand appears in a ranked list
- **Sentiment** -- positive, neutral, or negative sentiment toward each brand

## LLM Judge

The benchmark uses an LLM-as-judge approach to evaluate whether a brand mention constitutes an actual recommendation. The judge model analyzes each response and determines:

- Whether each brand is mentioned
- Whether the mention is a recommendation, a neutral reference, or a negative mention
- The relative strength of the recommendation

This provides more accurate results than simple keyword matching, since it distinguishes between "Brand X is the best tool" and "Brand X has been losing market share."

## Output

The default output includes:

- Summary table with mention rate, recommendation rate, and share-of-recommendation per brand
- Per-prompt breakdown showing which brands were mentioned and recommended
- Model-by-model comparison (when using multiple models)
- Cost summary showing token usage and estimated cost
