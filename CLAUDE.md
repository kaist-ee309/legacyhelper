# Project Context: Marketplace

## 1. Project Overview

*   **Goal:** AI troubleshooting agent for legacy (linux/UNIX) systems. 
*   **Core Features:** 
*       1. Fetching system information/logging
*       2. Utilizing Tools for troubleshooting information retrieval (e.g. websearch on stackoverflow, archwiki...)
*       3. Provide possible options on commands, and let user choose which one to execute (human in the loop)

## 2. Tech Stack

*   **Framework:** Pydantic AI
*   **Language:** Python
*   **Package Manager:** uv
*   **UI Components:** rich
*   **Code testing:** pytest
*   **Code styling:** pylint, typing

## 3. Project Structure

A brief description of key directories to help with navigation.

*   **legacyhelper/tools:** MCP based tooling used for fetching system information and executing commands from client system.
*   **legacyhelper/core:** Core logic of AI agent that defines overall workflow (Human in the loop)
*   **legacyhelper/model:** Baseclass that wraps various APIs. Gemini support primary.
*   **test:** test utils/script for unit test.
*   **utils:** scripts for linting / code style qualification


## 4. Key Commands

A list of frequently used commands will save us time.

*   uv venv: configure/initialize virtual environment
*   uv add: add dependency to pyproject.toml


## 5. Coding Conventions

If you have specific coding rules, list them here.

*   **Style:** Comply to type hinting 

## 6. Current Goals

*   With those requirements, configure project structure and virtual environment for developing.
