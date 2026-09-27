# T015 Beginner Usability Evaluation

Date: 2026-09-27

## Scope and honesty note

This evaluation uses three scripted novice personas in automated tests. No human participants were recruited, so the results must not be represented as moderated human research. The scenarios are repeatable regression evidence for the most likely first-run stopping points; a later release study can supplement them with observed human sessions.

## Personas and stopping points

| Persona | Scenario | Observed stopping point in the prior CLI | Change | Evidence |
|---|---|---|---|---|
| First-time learner | Opens the tool without knowing its menu | The intro described the product but did not explicitly say what to do next | Intro and menu now print a labeled next action | `test_three_scripted_novice_personas_can_recover_or_exit[first-time learner]` |
| Command-line novice | Enters an invalid menu number | The old message only rejected the input | Recovery now states what happened, why, and the exact next action | `test_invalid_choice_explains_what_why_and_recovery` |
| Persian-speaking learner | Starts in Persian on Windows | Navigation and the first task were English-only; terminal encoding was unverified | Added `--lang fa`, Persian navigation/first-task content, forced UTF-8 launcher output, and Unicode tests | `test_farsi_unicode_survives_supported_windows_launchers` |

## Result

All three scripted personas can either proceed or safely exit without an unexplained dead end. Every entry screen has a visible next action, recoverable errors use the same three-part structure, and saved progress remains intact on interrupted input.

## Follow-up human validation

Before a public usability claim, run three moderated sessions with people who have not used this repository. Record time to first correct command, prompts that require explanation, and any point where the participant cannot name the next action within ten seconds.
