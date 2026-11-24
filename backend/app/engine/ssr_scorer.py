from dataclasses import dataclass
import numpy as np
from app.core.llm import embed_texts
from app.engine.anchors import ANCHOR_SETS


@dataclass
class SSRResult:
    embedding: list[float]
    probabilities: dict[str, float]  # {"1": 0.05, ..., "5": 0.45}
    expected_likert: float           # 1.0 to 5.0
    base_utility_u0: float           # 0.0 to 100.0


class SSRScorer:
    def __init__(self) -> None:
        # Pre-embed all anchor sets once: shape = (num_sets, 5, dim)
        self.anchor_matrices: list[np.ndarray] = []
        for anchor_set in ANCHOR_SETS:
            ordered_texts = [anchor_set[r] for r in range(1, 6)]
            self.anchor_matrices.append(embed_texts(ordered_texts))

    def score_reaction(self, reaction_text: str) -> SSRResult:
        vec = embed_texts([reaction_text])[0]  # shape: (dim,)
        set_probs = []

        for anchor_mat in self.anchor_matrices:
            # Cosine similarity since both vec and anchor_mat are L2-normalized
            sims = anchor_mat @ vec  # shape: (5,)
            shifted = sims - np.min(sims)
            total = float(np.sum(shifted))

            if total > 1e-8:
                probs = shifted / total
            else:
                probs = np.full(5, 0.2)
            set_probs.append(probs)

        avg_probs = np.mean(set_probs, axis=0)
        ratings = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        expected_likert = float(np.dot(avg_probs, ratings))
        base_utility_u0 = ((expected_likert - 1.0) / 4.0) * 100.0

        return SSRResult(
            embedding=vec.tolist(),
            probabilities={str(i + 1): round(float(avg_probs[i]), 4) for i in range(5)},
            expected_likert=round(expected_likert, 3),
            base_utility_u0=round(base_utility_u0, 2),
        )