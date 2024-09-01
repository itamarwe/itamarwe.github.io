---
layout: post
title: "The 'Return Early' Pattern"
comments: true
date: 2018-02-28
categories: personal
---

## The Pattern

In this post, I want to introduce a simple yet powerful coding pattern that has significantly improved the readability of my code: the "return early" pattern. Since adopting this approach, I've found it challenging to work with code that doesn't utilize it.

The "return early" pattern advocates for functions to *return* as soon as possible. Let's look at an example to illustrate this concept.

Consider the following piece of code:

**Note:** The examples are in Python syntax, but this pattern is applicable to any language that allows multiple return statements.


```
def function foo():
  if <condition a>:
    <code_block_a>
  else:
    <code_block_b>
  return <result>
```

The "return early" pattern suggests restructuring the code like this:

```
def function foo():
  if <condition a>:
    <code_block_a>
  return <result>

  <code_block_b>
  return <result>
```

While this change may appear minor, it can significantly simplify complex, nested if/else statements.

## Simplifying nested if/else statements

For instance, consider the following nested structure:

```
def function foo():
  if <condition a>:
    if <condition a_1>:
      <code_block_a_1>
    else:
      <code_block_a_2>
  else:
    <code_block_b>
  return <result>
```

This code is already challenging to read. By the time you reach `code_block_b`, you may have forgotten the original `<condition_a>`, requiring you to revisit the code multiple times to understand when each block is executed.

By applying the "return early" pattern, the code becomes much clearer:

```
def function foo():
  if not <condition a>:
    <code_block_b>
    return <result>

  if <condition a_1>:
      <code_block_a_1>
      return <result>

  <code_block_a_2>
  return <result>
```
This refactored version is far more readable. Each block clearly indicates under what condition it is executed, eliminating the need for complex nested if/else statements. As a result, the risk of introducing logic errors or bugs is significantly reduced when the code is straightforward.

## Analogy to the "promise" pattern
I find this pattern analogous to the transition from "callback hell" to the promise pattern in asynchronous programming. Both approaches share the common goal of transforming complex, nested code into a more linear and readable format.

## Additional advantages
The "return early" pattern also encourages cleaner code by promoting functions that perform a single task. According to the principles of ["clean code" principles](/code/2017/11/05/Clean-code-main-takeaways.html),
breaking code into small, focused functions is essential for maintainability. Developers often struggle to apply the "return early" pattern because their functions are too complex, handling multiple responsibilities. If a function cannot accommodate an early return, it often indicates that it should be broken down into smaller, more focused functions.

Adopting the "return early" pattern is a straightforward yet effective way to improve your code quality.
