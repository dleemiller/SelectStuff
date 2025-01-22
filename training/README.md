# Training Applications

Resources for prototyping and training new applications.

To train a new program, you need:
- Training data
- A DSPy Module and signature(s)
- LLM Access (eg. openrouter, ollama)


## Synthetic Data Generation

In the `news/news_app_data.ipynb` notebook there's an example of using a teacher model (eg. deepseek v3) to aggregate multiple responses,
for `Best-of-N` generation.

In this notebook, we create a program to generate metadata from news articles.
The output of this process establishes a set of training data that we can use to optimize
and evaluate the program for smaller models (eg. llama 3b).

The training data can be re-used for training other models, which is a more straightforward process.


## Training

The `/news/train_program.ipynb` notebook implements training for the `NewsApp`.
It uses the MIPROv2 optimizer with a teacher model for bootstrapping.


## Utilities

### WordLlamaScorer

A generated automated scoring and evaluation utility.
Uses `WordLlama` for string comparison, jaccard similarity for short strings,
basic distance functions for `int`, `float` and `date` types, and
WordLlama cross-similarity for lists of strings. Exact match for `Literal` and
fallback types.

I might add to this script more in the future (more types, configurability, etc).
It's a general purpose scorer, so it might not be applicable to every output.
In many cases, it's probably sufficient for training and eval.


### Aggregation

Scripts to help do aggregation of multiple responses for creating synthetic training sets.
