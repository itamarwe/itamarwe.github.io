---
layout: post
title: "How to Use AI to Refactor Complex Code"
comments: true
date: 2025-12-16
categories: ai
---

I recently had to refactor a very complex and messy piece of code — a recursive algorithm over a graph in an existing, badly written codebase. I didn't believe AI could do it, and at first it didn't.

But I did eventually find a way to solve it with AI.

## The problem

The core logic was buried under classic anti-patterns: one giant function, lots of side effects, and no clear separation of responsibilities between modules.

Out of curiosity, I tried throwing the best models at it in "max mode" to see how far they'd get. They didn't solve it.

Eventually the AI did help solve the problem, but not out of the box. I had to change how I used it.

## What worked for me

### 1. Start with tests

Before changing anything, I wrote comprehensive tests around the existing behavior and the new cases I wanted to support. I also had to double check that the tests were correct — when the tests were wrong, AI happily produced strange code just to make them pass.

### 2. Ask AI to describe the solution

I wanted the solution and best practices to be within the context of the model. Instead of "refactor this file," I asked the models to summarize related papers, suggest relevant design patterns, and describe what the algorithm and code structure should look like.

### 3. Map the current code to that structure

Once I had a target design, I asked the models to map chunks of the existing code to that design and to add comments before each logical section: "builds the graph," "handles recursion and termination," "updates state," and so on. That turned one blob into labeled regions.

### 4. Carve out functions one by one

I then extracted those labeled sections into separate functions, step by step. Each new function had a narrow, clear responsibility and well-defined inputs/outputs. That alone made the code much easier to reason about.

### 5. Refactor and extend with confidence

With smaller, well-named functions and solid tests in place, I asked the models to refactor and extend the code. Short functions with clear responsibilities required far less context, and then magically, the AI succeeded in the task.

## The key insight

What works for humans works pretty well for AI too. Understanding clean code requires far less context, and is much easier to modify and extend — for both humans and AI.

The difference isn't that AI is bad at refactoring. It's that AI is bad at understanding messy code. Clean up the structure first, and suddenly the AI can help you tremendously.
