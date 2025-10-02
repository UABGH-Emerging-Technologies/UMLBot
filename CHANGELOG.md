# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added
- **Chat-Based UML Revision Workflow:**  
  Introduced an interactive chat interface for UML diagram generation, revision, and iterative feedback. Users can now describe, refine, and correct UML diagrams conversationally.
- **Generic Error Handler:**  
  Added a robust error handling system that captures, reports, and attempts to auto-correct errors from LLM calls, prompt construction, PlantUML rendering, and network issues. All errors are surfaced to the user with actionable messages and fallback behaviors.
- **Automated Error Correction:**  
  Integrated LLM-based repair strategies for invalid UML or rendering failures, with transparent user feedback.
- **Expanded Test Coverage:**  
  Added integration and unit tests for the chat-based UML workflow and generic error handler, ensuring reliability and correctness.

### Changed
- Documentation updated to reflect new chat-based workflow and error handling mechanisms.

### Fixed
- N/A

## [0.1.0] - 2024-01-01

- Initial release.