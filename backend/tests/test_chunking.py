import pytest
from src.services.ingestion.chunking import chunk_text, paper_chunk


def test_paper_chunk_joins_title_and_abstract():
    assert paper_chunk(" A Title ", "An abstract. ") == "A Title\n\nAn abstract."


def test_empty_text_yields_no_chunks():
    assert chunk_text("") == []
    assert chunk_text("   \n  ") == []


def test_short_text_is_a_single_normalized_chunk():
    assert chunk_text("one  two\nthree", max_words=10, overlap_words=2) == ["one two three"]


def test_long_text_splits_with_overlap():
    words = [f"w{i}" for i in range(500)]
    chunks = chunk_text(" ".join(words), max_words=100, overlap_words=20)

    assert len(chunks) == 6
    assert chunks[0].split()[0] == "w0"
    # each subsequent chunk starts one step (80 words) later
    assert chunks[1].split()[0] == "w80"
    # overlap: last 20 words of chunk N are the first 20 of chunk N+1
    assert chunks[0].split()[-20:] == chunks[1].split()[:20]
    # no words lost at the tail
    assert chunks[-1].split()[-1] == "w499"


def test_every_word_is_covered():
    words = [f"w{i}" for i in range(357)]
    chunks = chunk_text(" ".join(words), max_words=64, overlap_words=16)
    covered = {w for c in chunks for w in c.split()}
    assert covered == set(words)


@pytest.mark.parametrize(
    ("max_words", "overlap"),
    [(0, 0), (-5, 0), (10, 10), (10, 15), (10, -1)],
)
def test_invalid_parameters_raise(max_words, overlap):
    with pytest.raises(ValueError):
        chunk_text("some text", max_words=max_words, overlap_words=overlap)
