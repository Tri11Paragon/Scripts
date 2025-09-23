from dataclasses import dataclass
from itertools import pairwise

import torch
from torch import Tensor
import numpy as np
from transformers import AutoTokenizer, AutoModel
import torch.nn.functional as F
from torch.nn.utils.rnn import pad_sequence
from typing import List, Dict

from dotenv import load_dotenv

load_dotenv()

max_length = 512

# device = "cuda" if torch.cuda.is_available() else "cpu"
device = "cpu"
# model_name = "meta-llama/Llama-3.2-3B"
# model_name = "intfloat/e5-base-v2"
model_name = "BAAI/bge-small-en-v1.5"
# model_name = "Qwen/Qwen3-Embedding-8B"
# model_name = "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B"
#"mistralai/Mistral-7B-v0.1"

print(f"Using device: {device}")

tok = AutoTokenizer.from_pretrained(model_name, use_fast=True, padding_side="left", padding=True)
model = AutoModel.from_pretrained(model_name)
model.to(device)
model.eval()

print(model.config)
print("Model max context (if available):", getattr(model.config, "max_position_embeddings", None))

def evaluate(text):
    enc = tok(text, return_tensors="pt").to(device)
    input_ids = enc["input_ids"][0]
    attn = enc["attention_mask"][0]

    print(input_ids.size())

    start = 0

    chunks = []
    while start < input_ids.size(0):
        end = min(start + max_length, input_ids.size(0))
        ids = input_ids[start:end]
        mask = attn[start:end]
        item = {"input_ids": ids.unsqueeze(0), "attention_mask": mask.unsqueeze(0)}
        chunks.append(item)

        if end == input_ids.size(0):
            break
        start = end
    print(f"Split file into {len(chunks)} chunks.")
    outs = []
    for chunk in chunks:
        outs.append(model(**chunk, output_hidden_states=True, return_dict=True))
    return outs, chunks

def state(text: str, layer: int = -3, method: str = "mean"):
    outs, chunks = evaluate(text)

    vecs = []

    for out, chunk in zip(outs, chunks):
        hidden_states = out.hidden_states
        if method == "mean":
            mask = chunk["attention_mask"].unsqueeze(-1)
            summed = (hidden_states[layer] * mask).sum(dim=1)
            lengths = mask.sum(dim=1).clamp(min=1)
            vecs.append(summed / lengths)
        elif method == "bos":
            vecs.append(hidden_states[layer][:, 0, :])
        elif method == "last":
            mask = chunk["attention_mask"]
            lengths = mask.sum(dim=1) - 1
            batch_idx = torch.arange(hidden_states[layer].size(0), device=hidden_states[layer].device)
            vecs.append(hidden_states[layer][batch_idx, lengths, :])
        else:
            raise ValueError("Expected method to be 'mean', 'last', or 'bos', got: " + method)

    return EmbeddingData(vecs)

@dataclass
class EmbeddingData:
    def __init__(self, embeddings):
        self.embeddings = embeddings

    @staticmethod
    def from_text(text: str, layer: int = -3, method: str = "mean"):
        return state(text, layer=layer, method=method)

    def similarity(self, other):
        cosines = np.ndarray(shape=(len(self.embeddings), len(other.embeddings)), dtype=np.float32)
        for i, a in enumerate(self.embeddings):
            for j, b in enumerate(other.embeddings):
                va = torch.nn.functional.normalize(a, p=2, dim=-1)
                vb = torch.nn.functional.normalize(b, p=2, dim=-1)
                sim = torch.nn.functional.cosine_similarity(va, vb, dim=-1)
                cosines[i][j] = sim.item()

        return cosines

class FileData:
    def __init__(self, file, layer: int = -3, method: str = "mean"):
        self.file = file
        with open(file, "r") as f:
            text = f.read()
            self.data = state(text, layer=layer, method=method)

silly = EmbeddingData.from_text("I love people I think everyone should be equal")
bad = EmbeddingData.from_text("The interests of billionaires is the most important consideration in the economy. "
                              "We should sacrifice everything to keep them in our economy")
bad2 = EmbeddingData.from_text("I love capitalism and the rich and we should destroy socialism and the poor. We do not need the working class."
                              "They are a bunch of freeloaders")
good = EmbeddingData.from_text("We should build an equal society one where the workers are in control of the means of production!")
comm = FileData("works/communistmanifesto.txt")

cosines1 = silly.similarity(comm.data)
cosines2 = bad.similarity(comm.data)
cosines3 = bad2.similarity(comm.data)
cosines4 = good.similarity(comm.data)

print("Silly:")
print(cosines1.max(axis=1))
print("Bad:")
print(cosines2.max(axis=1))
print("Bad2:")
print(cosines3.max(axis=1))
print("Good:")
print(cosines4.max(axis=1))
print()

def last_token_pool(last_hidden_states: Tensor,
                 attention_mask: Tensor) -> Tensor:
    left_padding = (attention_mask[:, -1].sum() == attention_mask.shape[0])
    if left_padding:
        return last_hidden_states[:, -1]
    else:
        sequence_lengths = attention_mask.sum(dim=1) - 1
        batch_size = last_hidden_states.shape[0]
        return last_hidden_states[torch.arange(batch_size, device=last_hidden_states.device), sequence_lengths]


def get_detailed_instruct(task_description: str, query: str) -> str:
    return f'{task_description}:\n{query}'

task = 'Identify the topic or theme based on the text'

dog = "I am a dog. I love to sniff other dog's butts"
cat = "I am a cat. I love to sniff other cat's butts"
cat2 = "Cock cock cock I love cock in my butt"
cat3 = "I once took a vacation in summer. it was a lovely beach and i would go back again. too bad there was too much rain."
cat4 = "The patient presented to the ER with bleeding in the eyes, excessive sweating and an insatiable sense of pain."

queries = [
    get_detailed_instruct(task, dog),
    get_detailed_instruct(task, cat)
]

documents = [
    dog,
    cat,
    cat2,
    cat3,
    cat4,
]
input_texts = queries + documents

batch_dict = tok(
    input_texts,
    padding=True,
    truncation=True,
    max_length=max_length,
    return_tensors="pt",
)

batch_dict.to(model.device)
outputs = model(**batch_dict)
embeddings = last_token_pool(outputs.last_hidden_state, batch_dict['attention_mask'])

embeddings = F.normalize(embeddings, p=2, dim=1)
scores = (embeddings[:2] @ embeddings[2:].T)
print(scores.tolist())

# print(out)
# print(tok.decode(out[0], skip_special_tokens=True))
