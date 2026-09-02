# Reflow — Product Terminology Reference

To ensure a unified, professional user experience, Reflow enforces canonical terminology across all user interfaces, API documentation, and CLI tools.

---

## Canonical Terms & Definitions

| Term | Canonical Definition | Non-Canonical / Forbidden Synonyms |
| :--- | :--- | :--- |
| **Content Item** | A single piece of uploaded or created source material (video, text, image, PDF). | *Upload*, *Source File*, *Blob* |
| **Media Variant** | An aspect-ratio specific derivative of a video asset (`VERTICAL_9_16`, `SQUARE_1_1`, `PORTRAIT_4_5`, `LANDSCAPE_16_9`). | *Format*, *Aspect Ratio Copy*, *Resize* |
| **Short-Form Clip** | An AI-discovered or manually selected key segment extracted from a longer video. | *Snippet*, *Cut*, *Highlight* |
| **Carousel** | A multi-slide visual presentation deck exportable as PNG slide images or a PDF document. | *Slide Deck*, *PDF Export*, *Image Grid* |
| **Burn-in Captions** | Styled, word-highlighted subtitle text rendered directly onto video frames. | *Subtitles*, *Text Overlay*, *Lower Thirds* |
| **Publication** | A distribution event sending content, clips, or carousels to a target social platform. | *Post*, *Share*, *Submission* |
| **Platform Connection** | An authenticated OAuth or API credential connecting Reflow to an external platform (YouTube, Instagram, LinkedIn, etc.). | *Account*, *Channel Link*, *Integration* |
| **Automation** | A rule-based pipeline that executes actions when specific content events trigger. | *Workflow*, *Trigger Rule*, *Bot* |
| **System Job** | An asynchronous background task executed by Reflow workers (transcoding, transcribing, rendering, publishing). | *Task*, *Process*, *Work Unit* |
| **Incident** | A categorized operational fault or repeated job failure requiring operator review. | *Bug*, *Alert*, *Issue* |
| **Governance Gate** | A quality-control evaluation checking content resolution, prohibited terms, or duplicate publication rules before release. | *Quality Check*, *Filter*, *Blocker* |

---

## Rules of Usage

1. **UI Headings & Buttons**: Always use canonical terms (e.g. `Create Content Item`, `Schedule Publication`, `View System Jobs`).
2. **Status Badges**: Use standard uppercase status strings (`PROCESSING`, `QUEUED`, `SCHEDULED`, `PUBLISHED`, `FAILED`, `AWAITING_APPROVAL`).
3. **Error Reporting**: Combine user-friendly natural language with the canonical entity term (e.g. "Publication to YouTube failed due to invalid token.").
