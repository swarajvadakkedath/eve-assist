# Contributing to AIOS

**Document ID:** 25-CONTRIBUTING  
**Status:** Approved  
**Version:** 1.0.0  
**Last Updated:** 2026-07-18

---

## 1. Purpose

This document defines how to contribute to AIOS, including code standards, PR process, and community guidelines.

## 2. Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Assume good intent
- No harassment or discrimination

## 3. Getting Started

1. Read the [Vision](00-Vision.md) and [Architecture](02-System-Architecture.md) documents
2. Set up the development environment (see [Developer Guide](24-Developer-Guide.md))
3. Find an issue to work on
4. Fork the repository
5. Create a feature branch

## 4. Pull Request Process

1. Create a feature branch from `main`
2. Write tests for your changes
3. Run all tests: `npm test`
4. Run linters: `npm run lint`
5. Update documentation if needed
6. Create a pull request
7. Request review from maintainers
8. Squash commits before merge

## 5. Code Review Guidelines

- All code must be reviewed
- Tests must pass
- No decrease in coverage
- Documentation must be updated
- Follow coding standards (see [06-Coding-Standards](06-Coding-Standards.md))
