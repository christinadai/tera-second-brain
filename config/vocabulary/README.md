# Vocabulary

Three lists, kept separate because they answer different questions:

- `product_types.yaml`  what kind of thing is being discussed (Track A)
- `ingredients.yaml`    what is in it, and what claims get made about it (Track B)
- `pain_points.yaml`    what went wrong (both tracks)

## The `source` tag is the point

Every term carries one:

| source | Means |
|---|---|
| `provisional` | Guessed by Claude before real data was seen. **Unvalidated.** |
| `alma` | Taken from Alma's manual research notes. Observed in real posts. |
| `observed` | Surfaced by the unmatched-term review against collected data. |

A `provisional` term that survives to week 3 without ever matching anything is
a guess nobody checked. That is the failure this tag exists to make visible.

## Vocabulary rot

A term that is missing produces silence, not an error. The pipeline logs the
most frequent unmatched terms every run so gaps surface as data rather than as
a quiet absence in a briefing.

## Editing

Plain YAML, meant to be edited by hand, including by someone who does not write
code. Add a term under the right list, give it a `source`, save. No code change.
