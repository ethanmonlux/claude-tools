# Claude Code Prompt Guide

## The Pattern
```python
In [file], find [specific thing].
Change [exact current text] → [exact new text].
Do not change anything else.
```
That's it. Simple, surgical, unambiguous.

## Rules

**Be specific about location.**
File name, line number if possible, exact text to change. Don't say "the title" — say "line 1" or paste the exact string.

**Tell it what to change AND what not to change.**
"Do not change anything else" is the most important line. Claude Code will over-engineer if you don't constrain it. It will refactor things you didn't ask it to touch, rename variables, add comments, reorganize imports. The constraint line stops this.

**Show before and after.**
"Change X → Y" is clearer than describing what you want in prose. Paste the exact current text and the exact replacement. No ambiguity.

**One change per prompt.**
Don't bundle multiple unrelated changes in a single prompt. Separate prompts, separate commits, clean history. If something goes wrong you want to know exactly which change caused it.

**Combine only when efficient.**
Multiple related changes in the same file or the same logical unit can be batched. Don't batch changes across unrelated files.

Documentation updates (CHANGELOG.md, CLAUDE.md, ARCHITECTURE.md, README.md, TODO.md) are always a separate prompt after the code change is committed and verified. Never bundle code changes and documentation updates in the same prompt.

**All instructions must be inside the code block.**
The entire prompt — context, changes, and constraints — goes in a single code block for one-click copy-paste. Nothing outside it.

## Example
```python
In app/skills/prospect_research.py, find the import on line 47.

Change:
    try:
        import anthropic

To:
import anthropic

Place the import at the top of the file with the other imports, after the standard library imports and before the local imports.

Do not change anything else.
```
## What Happens Without This Pattern

Claude Code will:
- Refactor things you didn't ask it to touch
- Add "improvements" you didn't request
- Rename variables for consistency
- Reorganize file structure
- Add docstrings, type hints, comments
- Change logic while fixing formatting

The pattern prevents all of this. Constrain first, then let it work.

## Always Plan Before Implementing

Before writing any prompt, list:
1. Every file you will touch
2. Every change you will make
3. What you will NOT change

Review the plan. Then prompt.

## Start Every Session

The first prompt of every session must include "Read CLAUDE.md before making any changes." inside the code block — not as a separate instruction outside it.

Watch for the Read tool call on CLAUDE.md in CC's response. If you don't see it, tell CC to read it before proceeding.

This is non-negotiable. CLAUDE.md contains the architecture summary, safety rules, workflow rules, and list of what's already implemented. Reading it first prevents re-implementing things that exist and violating constraints.

## After Every Change

Run pytest and ruff check. Both must pass before committing. No exceptions.

## Session Workflow

1. Engineer starts CC session → first prompt includes "Read CLAUDE.md before making any changes."
2. Code prompt(s) → CC implements, runs pytest and ruff, commits, pushes. One prompt, one commit.
3. When all code changes are done, engineer receives all prompts at once — code prompts already sent, doc update prompt last.
4. Doc update prompt → CC updates CHANGELOG.md and any affected docs, commits, pushes.
5. Engineer opens PR, merges, deletes branch, /clear.
