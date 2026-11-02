//! Conservative post-ASR aliases, not decoder bias or financial interpretation.
use once_cell::sync::Lazy;
use regex::{Captures, Regex};
use serde::Deserialize;
use std::collections::HashMap;

#[derive(Deserialize)]
struct Term {
    canonical: String,
    aliases: Vec<String>,
}

#[derive(Deserialize)]
struct Glossary {
    terms: Vec<Term>,
}

struct Matcher {
    regex: Regex,
    replacements: HashMap<String, String>,
}

static MATCHER: Lazy<Matcher> = Lazy::new(|| {
    let glossary: Glossary =
        serde_json::from_str(include_str!("../../../packaging/finance-glossary.json"))
            .expect("invalid embedded finance glossary");
    let mut replacements = HashMap::new();
    for term in glossary.terms {
        for alias in term.aliases {
            assert!(!alias.is_empty() && !alias.chars().any(|c| c.is_numeric()));
            let previous = replacements.insert(alias.to_lowercase(), term.canonical.clone());
            assert!(previous.is_none(), "duplicate finance alias: {alias}");
        }
    }
    let mut aliases: Vec<_> = replacements.keys().cloned().collect();
    aliases.sort_by_key(|alias| std::cmp::Reverse(alias.len()));
    let pattern = format!(
        r"(?i)\b(?:{})\b",
        aliases
            .iter()
            .map(|alias| regex::escape(alias))
            .collect::<Vec<_>>()
            .join("|")
    );
    Matcher {
        regex: Regex::new(&pattern).expect("invalid embedded finance matcher"),
        replacements,
    }
});

/// Exact, Unicode word-boundary matches only; never fuzzy-match the whole list.
/// Personal spellings take precedence over canonical casing of the same term.
pub fn apply_finance_glossary(text: &str, personal_words: &[String]) -> String {
    MATCHER
        .regex
        .replace_all(text, |capture: &Captures<'_>| {
            let matched = &capture[0];
            let canonical = &MATCHER.replacements[&matched.to_lowercase()];
            personal_words
                .iter()
                .find(|word| word.to_lowercase() == canonical.to_lowercase())
                .unwrap_or(canonical)
                .clone()
        })
        .into_owned()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn mixed_finance_and_amounts() {
        assert_eq!(
            apply_finance_glossary(
                "L'ébitda est à 12,5 M€; nopat 8.25, WACC 10 %, DCF/ebitda 7,2x. Le b f r baisse.",
                &[]
            ),
            "L'EBITDA est à 12,5 M€; NOPAT 8.25, WACC 10 %, DCF/EBITDA 7,2x. Le BFR baisse."
        );
        assert_eq!(
            apply_finance_glossary(
                "EBITDA's cap ex and free cashflow; besoin en fond de roulement.",
                &[]
            ),
            "EBITDA's CAPEX and free cash flow; besoin en fonds de roulement."
        );
    }

    #[test]
    fn ordinary_speech_and_boundaries_remain_unchanged() {
        let text = "Le roi fait le tri. La loi est claire. Un van près du spa. No Pat, not now. Walk to the store. Ébitdax, anopate, 123nopat, ebitda2026, préebitda.\n12,5 % / 1.234,56 € / -42.";
        assert_eq!(apply_finance_glossary(text, &[]), text);
        // No correction across punctuation or line boundaries, no invented acronym.
        assert_eq!(
            apply_finance_glossary("n, o, p, a, t\nebit\nda", &[]),
            "n, o, p, a, t\nEBIT\nda"
        );
    }

    #[test]
    fn personal_spelling_and_idempotence() {
        let words = vec!["Ebitda".to_owned(), "MCI".to_owned()];
        let result = apply_finance_glossary("ébitda 42, mci", &words);
        assert_eq!(result, "Ebitda 42, mci");
        assert_eq!(apply_finance_glossary(&result, &words), result);
        assert_eq!(words, ["Ebitda", "MCI"]);
    }

    #[test]
    fn ten_minute_sized_text_preserves_numbers() {
        let input = "Ebitda 12,5 millions; nopat 8.25. Ordinary words stay intact.\n".repeat(250);
        let expected =
            "EBITDA 12,5 millions; NOPAT 8.25. Ordinary words stay intact.\n".repeat(250);
        assert_eq!(apply_finance_glossary(&input, &[]), expected);
    }
}
