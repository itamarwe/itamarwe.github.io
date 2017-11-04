---
layout: post
title:  "Clean"
date:   2017-11-05
categories: personal
---

A few years ago, I read the book "Clean code - A handbook of Agile software craftmanship"
by Robert C. Martin. It is still the book that influenced my code writing style
the most so far.

Although it was written originally for Java, and most examples are in Java, it is
in fact applicable for any programming language. I used its insights personally
when writing code in Java, Javascript, Python, C and more.

What I like about this book, is that it's realistic and pragmatic. First, it is filled
with real-world examples, second, it takes human-nature into consideration. It acknowledges
that code is never perfect, that we cannot write clean code on the first try and
that writing clean code is a process, that starts by writing code that works, and
then slowly transforming it into clean code.

As programmers, we try to be efficient. Many times we ask ourselves if it's ok to
have a such a long function name? Is it ok to split a module to so many files? The
answer is yes, and by showing real-world examples, the author demonstrates how it
eventually creates much more readable and maintainable code.

You might ask why is writing clean code important. If the code works, isn't that
enough? Well, the caveat of that approach, is that almost always code is a living
creature. Features are added continuously, team members change, bugs are found.
It means that the code is being modified often, and that more often than that, new
people need to get into the code and understand how it works and what it does. On
top of it all, writing clean code allows us to write code that works better, that
has less bugs. It assures that we define what every piece of our code does, and
that it can be easily validated.

Here is a collection of my key takeaways:

1. *Keep it short* - Files, functions and classes should be short. My rule of thumb
is no more than 200 lines per file and usually less than a 100. I never feel bad
about breaking a file, a class, a function to smaller files. On the contrary. The
more files I have, the easier they are to read and reason about. When files are longer
than 200 lines, it becomes hard to keep in mind the entire context. Merges are also usually
simpler when using smaller files, since the chances of 2 developers simultaneously
modifying the same file declines dramatically.

2. *Do one thing* - Functions and classes should be short and do one thing. Functions
should read as the to-do list for accomplishing the single purpose of the function.
The statements in a function should all belong to one level of abstraction below
that of the function and should not mix different levels of abstraction. Functions
should either do something or answer something, but not both. Each function or class
should have a single reason to change.

3. *No side-effects* - Functions should have no side-effects, they should only do
the one thing they are supposed to do. For example, a common pitfall is output arguments -
modifying one of the function's arguments to provide output. Function should usually
use the return statement as their only output. If a function needs change
the state of anything, have it change the state of its owning object.

4. *Reading code from top to bottom* - The code should be readable from top to bottom.
Every function should be followed by the functions at the next level of abstraction.
If one function calls another, they should be vertically close, and the caller
should be above the callee.

5. *Meaningful names* - Classes, functions, arguments should all have meaningful
names. Names should tell you why it exists, what it does and how it should be used.
Names should be explicit and should require as little context to understand. When
writing code we need to make sure it is understandable for others who read it with
no context. A couple of days after writing a piece of code we will have a hard time
remembering the context ourselves. Say what you mean, mean what you say. Don't be
afraid to make a name long. A long descriptive name is better than a short enigmatic
name.

6. *One word per concept* - Fetch, retrieve, get, extract - how are they different?
In one of the project I was working on chip, slide, cartridge, plastic were used
interchangeably.

7. *Don't repeat yourself* - Whenever you repeat yourself, abstract your code, put
it in a separate module and reuse it. It will also mean that when you upgrade this
piece of code or fix it you will only need to do it once.

8. *Comments* - You should almost never use comments. Good names are the best replacement
for comments. If a name requires a comment, then the name does not reveal the intent.
Don't comment bad code, rewrite it.

9. *Unitests* - Unitests should be written in parallel to the code. They allow us
to write bad code that does what it needs to do, and then improve it until we get
to clean code, without worrying about damaging our code's functionality. The more
tests we have in place the more comfortable we feel about modifying, evolving and
improving it. Tests should be fast, independent, repeatable, and self-validating
(return success or failure).

10. *First, make it work* - Get to a working piece of code as quickly as possible,
write tests for it, and then improve it.
