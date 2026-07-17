"""K-means clustering with silhouette-selected k over extraction embeddings."""

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

RANDOM_STATE = 42  # deterministic landscapes for identical inputs


def choose_k(vectors: np.ndarray, *, k_min: int = 2, k_max: int = 10) -> int:
    """Pick k by silhouette score; degrades to 1 for tiny inputs."""
    n = len(vectors)
    if n < 4:
        return 1
    best_k, best_score = 1, -1.0
    for k in range(k_min, min(k_max, n - 1) + 1):
        labels = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init=10).fit_predict(vectors)
        if len(set(labels)) < 2:
            continue
        score = float(silhouette_score(vectors, labels))
        if score > best_score:
            best_k, best_score = k, score
    return best_k


def cluster_vectors(
    vectors: list[list[float]], *, k: int | None = None
) -> tuple[list[int], list[list[float]]]:
    """Cluster vectors; returns (labels, centroids)."""
    if not vectors:
        return [], []
    arr = np.asarray(vectors, dtype=float)
    if k is None:
        k = choose_k(arr)
    if k <= 1:
        return [0] * len(vectors), [arr.mean(axis=0).tolist()]
    model = KMeans(n_clusters=k, random_state=RANDOM_STATE, n_init=10).fit(arr)
    return model.labels_.tolist(), model.cluster_centers_.tolist()


def cosine_similarity(a: list[float], b: list[float]) -> float:
    va, vb = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
    if denom == 0.0:
        return 0.0
    return float(np.dot(va, vb) / denom)
