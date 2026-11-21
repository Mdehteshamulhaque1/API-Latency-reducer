"""Pure helpers of the crawler sources: text extraction, trust ranking, keyword stripping."""
from app.ai.answers import sources


def test_extract_text_drops_navigation_scripts_and_short_fragments():
    html = """<html><head><title> Hello   World </title><style>p{}</style></head>
    <body><nav><a>Home</a><a>About us now</a></nav>
    <div><h2>Section one heading text</h2><p>This paragraph has enough words to be kept.</p>
    <p>Tiny</p><script>var x = 1;</script></div>
    <footer><p>Copyright notice that is long enough to pass</p></footer></body></html>"""
    title, text = sources.extract_text(html, max_chars=1000)
    assert title == "Hello World"
    assert "This paragraph has enough words to be kept." in text
    assert "Section one heading text" in text
    assert "Tiny" not in text and "var x" not in text and "Home" not in text
    assert "Copyright" not in text  # footer skipped


def test_extract_text_truncates():
    html = "<p>" + "word " * 500 + "</p>"
    _, text = sources.extract_text(html, max_chars=50)
    assert len(text) <= 50


def test_is_trusted_matches_domain_suffixes():
    trusted = [".gov", "wikipedia.org", ".ac.uk"]
    assert sources.is_trusted("https://www.irs.gov/forms", trusted)
    assert sources.is_trusted("https://en.wikipedia.org/wiki/Tax", trusted)
    assert sources.is_trusted("https://wikipedia.org/", trusted)
    assert sources.is_trusted("https://www.ox.ac.uk/", trusted)
    assert not sources.is_trusted("https://notgov.example.com/", trusted)
    assert not sources.is_trusted("https://examplegov.com/", trusted)
    assert not sources.is_trusted("not a url", trusted)


def test_is_fetchable_rejects_private_and_non_http():
    assert sources.is_fetchable("https://example.gov/page")
    assert not sources.is_fetchable("ftp://example.gov/file")
    assert not sources.is_fetchable("http://localhost:8000/admin")
    assert not sources.is_fetchable("http://127.0.0.1/")
    assert not sources.is_fetchable("http://10.0.0.5/internal")
    assert not sources.is_fetchable("http://169.254.169.254/latest/meta-data")
    assert not sources.is_fetchable("http://printer.local/")


def test_keywords_strip_question_words():
    assert sources.keywords("Who is the president of France?") == "president France"
    assert sources.keywords("what") == "what"  # nothing left: keep the original


def test_query_candidates_prefer_keywords_then_proper_nouns():
    assert sources.query_candidates("What is the capital city of Portugal?") == [
        "capital city Portugal",
        "Portugal",
        "city Portugal",
    ]
    assert sources.query_candidates("Who was Guido van Rossum?") == ["Guido van Rossum", "Guido", "Rossum"]
    assert sources.query_candidates("How big is New York City compared to Tokyo?") == [
        "big New York City compared Tokyo",
        "New York City",
        "New",
    ]
    assert sources.query_candidates("income tax") == ["income tax"]
    assert sources.query_candidates("what") == ["what"]


def test_cache_validity_rules():
    from app.ai.answers.semantic_cache import compatible, is_volatile, question_signature

    # Numbers and dates must agree.
    assert compatible("Who won the world cup in 2018?", "Which team won the 2018 world cup?")
    assert not compatible("Who won the world cup in 2018?", "Who won the world cup in 2022?")
    assert question_signature("Population of Delhi in 2011?") == ({"2011"}, set())
    # Time markers must agree.
    assert not compatible("What is the weather in Delhi?", "What was the weather in Delhi yesterday?")
    assert compatible("Who is the president of France?", "Who's France's president?")
    # Volatile topics never match semantically.
    assert is_volatile("What is the weather in Delhi?")
    assert is_volatile("Latest news about the election")
    assert is_volatile("Bitcoin price right now")
    assert not is_volatile("Who was the first president of Portugal?")
