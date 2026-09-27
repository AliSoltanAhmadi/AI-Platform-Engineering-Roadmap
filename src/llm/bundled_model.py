#!/usr/bin/env python3
"""Deterministic offline responder grounded in a matched Knowledge Base topic."""


class BundledModel:
    name = "knowledge-base-v1"

    def respond_grounded(self, question, context):
        if not isinstance(context, str) or not context.strip():
            raise ValueError("Matched Knowledge Base context is required.")
        fields = {}
        for line in context.splitlines():
            label, separator, value = line.partition(":")
            if separator and value.strip():
                fields[label.strip().casefold()] = value.strip()
        explanation = fields.get("simple explanation")
        next_step = fields.get("next step")
        if not explanation or not next_step:
            raise ValueError("Knowledge Base context is missing explanation or next step.")
        return f"{explanation} Next, {next_step}"

    def respond(self, prompt):
        """Compatibility response that never pretends to know ungrounded facts."""
        return "No matched local Knowledge Base context was supplied."
