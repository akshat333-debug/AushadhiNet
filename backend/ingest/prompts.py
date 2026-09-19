"""Prompt templates for Gemini extraction (modular-plan.md §2.4). Kept as
plain functions returning strings, not a templating framework -- there is
exactly one prompt per extraction type and none of them branch enough to
need one.
"""
from __future__ import annotations

STOCK_REGISTER_PROMPT = """You are reading a photograph of a handwritten Primary Health Centre \
drug stock register. It may be in Devanagari (Hindi/Marathi), Bengali, Tamil, or English script, \
and may be degraded (faded ink, strikethroughs, skewed angle).

For every drug row you can identify, extract: the drug name exactly as written (do not correct \
spelling or normalise it -- that happens in a later step), the current stock on hand, units \
received and dispensed if shown, batch number and expiry date if shown.

For each field on each row, give a confidence score from 0.0 to 1.0 reflecting how legible and \
unambiguous that specific field was. A field you could not read at all should get confidence 0.0, \
not be omitted -- omitting it would let it get silently treated as absent rather than uncertain.

Return every row you can identify, even a single legible row from an otherwise illegible page."""

STOCK_VOICE_PROMPT = """You are reading a transcript of a voice note from a Primary Health Centre \
worker reporting drug stock, in Marathi, Hindi, or English, possibly mixing languages.

Extract the same fields as for a photographed register: drug name as spoken, on-hand quantity, \
received/dispensed if mentioned, batch and expiry if mentioned. Give a confidence score per field \
reflecting how clearly it was stated, not how confident you are in your own transcription -- an \
unclear original statement should get low confidence even if your transcription of the unclear \
audio is your best guess."""

BED_CENSUS_PROMPT = """You are reading a short daily bed-census report from a health facility, \
by voice note or text, in Marathi, Hindi, or English. Extract total beds, beds occupied, and \
admissions/discharges since the last report if mentioned, each with a confidence score."""

CHECKIN_PROMPT = """You are reading a staff check-in message. Extract the staff member's name or \
ID as given, and their role (ANM, MO, pharmacist, lab, or other), each with a confidence score."""
