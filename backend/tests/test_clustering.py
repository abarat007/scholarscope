import numpy as np
from src.services.synthesis.clustering import choose_k, cluster_vectors, cosine_similarity


def _blobs(centers: list[list[float]], per_center: int = 8, spread: float = 0.05):
    rng = np.random.default_rng(7)
    points = []
    for center in centers:
        points.extend(rng.normal(loc=center, scale=spread, size=(per_center, len(center))))
    return np.asarray(points)


def test_choose_k_finds_two_well_separated_blobs():
    vectors = _blobs([[0.0, 0.0], [10.0, 10.0]])
    assert choose_k(vectors) == 2


def test_choose_k_finds_three_blobs():
    vectors = _blobs([[0.0, 0.0], [10.0, 0.0], [0.0, 10.0]])
    assert choose_k(vectors) == 3


def test_tiny_input_degrades_to_single_cluster():
    labels, centroids = cluster_vectors([[1.0, 1.0], [1.1, 0.9]])
    assert labels == [0, 0]
    assert len(centroids) == 1


def test_cluster_vectors_groups_blob_members_together():
    vectors = _blobs([[0.0, 0.0], [10.0, 10.0]], per_center=5)
    labels, centroids = cluster_vectors(vectors.tolist())

    assert len(centroids) == 2
    first_blob, second_blob = set(labels[:5]), set(labels[5:])
    assert len(first_blob) == 1 and len(second_blob) == 1
    assert first_blob != second_blob


def test_cosine_similarity_bounds():
    assert cosine_similarity([1, 0], [1, 0]) == 1.0
    assert cosine_similarity([1, 0], [0, 1]) == 0.0
    assert cosine_similarity([1, 0], [-1, 0]) == -1.0
    assert cosine_similarity([0, 0], [1, 0]) == 0.0  # zero vector guard
