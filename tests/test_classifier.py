import unittest

from core.classifier import TextCategory, TextClassifier, classify_text, classifier


class TextClassifierTests(unittest.TestCase):
    def test_all_expected_categories_are_exposed(self):
        self.assertEqual(
            classifier.get_all_categories(),
            [
                "URL",
                "CODE",
                "MARKDOWN",
                "JSON",
                "XML",
                "SQL",
                "TRACEBACK",
                "TODO",
                "CHAT",
                "LOG",
                "NOTE",
            ],
        )

    def test_url_classification(self):
        self.assertCategory("https://example.com/docs?page=1", TextCategory.URL)

    def test_code_classification(self):
        self.assertCategory(
            "def greet(name):\n    print(f'Hello {name}')\n    return name",
            TextCategory.CODE,
        )

    def test_markdown_classification(self):
        self.assertCategory("# Release notes\n\n- Added classifier\n- Fixed docs", TextCategory.MARKDOWN)

    def test_json_classification(self):
        self.assertCategory('{"name": "SessionChrono", "enabled": true}', TextCategory.JSON)

    def test_xml_classification(self):
        self.assertCategory('<?xml version="1.0"?><note><body>Hello</body></note>', TextCategory.XML)

    def test_sql_classification(self):
        self.assertCategory("SELECT id, title FROM notes WHERE category = 'URL';", TextCategory.SQL)

    def test_traceback_classification(self):
        self.assertCategory(
            'Traceback (most recent call last):\n  File "main.py", line 10, in <module>\nValueError: bad clipboard',
            TextCategory.TRACEBACK,
        )

    def test_todo_classification(self):
        self.assertCategory("TODO: follow up with task owner and fix importer", TextCategory.TODO)

    def test_chat_classification(self):
        self.assertCategory("User: Can you summarize this?\nAssistant: Yes, here is a summary.", TextCategory.CHAT)

    def test_log_classification(self):
        self.assertCategory("2026-06-11 10:20:30 ERROR failed status=500 request_id=abc", TextCategory.LOG)

    def test_plain_note_fallback(self):
        category, confidence = classifier.classify("Remember to buy milk on the way home.", confidence=True)
        self.assertEqual(category, TextCategory.NOTE.value)
        self.assertEqual(confidence, 0.0)

    def test_compatibility_wrapper_returns_string(self):
        self.assertEqual(classify_text("www.example.org"), TextCategory.URL.value)

    def test_empty_and_whitespace_are_safe_notes(self):
        self.assertEqual(classifier.classify(""), TextCategory.NOTE.value)
        self.assertEqual(classifier.classify("   \n\t  "), TextCategory.NOTE.value)

    def test_binary_like_string_is_safe_note(self):
        binary_like = "\x00\x01\x02" * 100 + "https://example.com"
        category, confidence = classifier.classify(binary_like, confidence=True)
        self.assertEqual(category, TextCategory.NOTE.value)
        self.assertEqual(confidence, 0.0)

    def test_very_large_string_is_classified_from_bounded_sample(self):
        large = "https://example.com\n" + ("plain text\n" * 200_000)
        category, confidence = classifier.classify(large, confidence=True)
        self.assertEqual(category, TextCategory.URL.value)
        self.assertGreater(confidence, 0.0)

    def test_confidence_increases_with_more_category_evidence(self):
        weak_category, weak_confidence = classifier.classify("https://example.com", confidence=True)
        strong_category, strong_confidence = classifier.classify(
            "https://example.com/path?query=value", confidence=True
        )
        self.assertEqual(weak_category, TextCategory.URL.value)
        self.assertEqual(strong_category, TextCategory.URL.value)
        self.assertGreater(strong_confidence, weak_confidence)

    def test_deterministic_tie_breaking_prefers_specific_category(self):
        test_classifier = TextClassifier()
        tie_score = 0.5
        best = test_classifier._best_category(
            {
                TextCategory.CODE: tie_score,
                TextCategory.JSON: tie_score,
                TextCategory.NOTE: 0.0,
            }
        )
        self.assertEqual(best, TextCategory.JSON)

    def assertCategory(self, text, expected):
        category, confidence = classifier.classify(text, confidence=True)
        self.assertEqual(category, expected.value)
        self.assertGreater(confidence, 0.0)


if __name__ == "__main__":
    unittest.main()
