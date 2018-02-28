---
layout: post
title:  "The \"return early\" pattern"
comments: true
date:   2018-02-28
categories: personal
---

## The pattern
Today I would like to share a simple but very important coding pattern. Using it
made my code much more readable. Since I discovered it I find it very hard to read
code that doesn't employ it.

The pattern is called "return early" because it recommends that your functions
*return* as early as possible.

Let's dive straight into an example. Imagine that you have a piece of code that
looks as follows:

** the examples are in Python syntax, but relevant to any language
that allows multiple return statements

```
def function foo():
  if <condition a>:
    <code_block_a>
  else:
    <code_block_b>
  return <result>
```

The "return early" pattern will suggest the code will be:

```
def function foo():
  if <condition a>:
    <code_block_a>
  return <result>
  
  <code_block_b>
  return <result>
```

That's all there is to it. Maybe it doesn't look like much, but let's
see how it can break down long and unreadable nested if/else statements.

## Simplifying nested if/else statements
For example:

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

This code block is already much less readable. When you read the code and you get
to `code_block_b` you probably don't even remember `<condition_a>` and you need
to go back and forth in order to understand when it is invoked.

On the other hand, by employing the "return early" pattern, it will look like this:

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
To me, the code block above is much more readable. It is very clear on what condition
every code block is invoked. You don't have any complex nested if/else statements.
The chances of getting the logic wrong here and introducing bugs is much lower
when the code is as straightforward.

## Analogy to the "promise" pattern
I find that this pattern is analogous to moving from "callback hell" to the promise
pattern. It has the same concept of breaking nested complex code to very linear
and readable code.

## Additional advantages
Here's another way in which this pattern will make your code cleaner. The pattern
forces your functions to do only one thing. If you know the ["clean code" principles](/code/2017/11/05/Clean-code-main-takeaways.html),
you know that breaking your code to many short functions that only do one thing is
the way to go. Many times developers have trouble employing the "return early" pattern
because their functions are doing many things, and in that case you cannot just
return in the middle of the function. If the "return early" pattern cannot be
employed in a function it's a good indicator that this function is not doing one
thing and needs to be broken down.

It's as easy as it gets.
