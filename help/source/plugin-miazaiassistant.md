---
DocType: How-to guide
Feature: Plugins, Renaming
HelpId: plugin-aiassistant
Level: advanced
Order: 670
Plugin: MiAZAIAssistant
Section: Plugins for documents
Summary: Let an AI model suggest a document's fields, or ask it questions about the document.
---

# Ask an AI model about a document

MiAZAIAssistant sends a document's text to a language model and uses the
answer to suggest filename fields, or to chat about the document.

!!! warning "What leaves your computer"
    With Claude, OpenAI or Gemini, the text of the document is sent to that
    company. With Ollama the model runs on your own computer and nothing leaves
    it. When no text can be extracted, the file itself is sent.

## Set it up {#setup}

1. Enable the plugin in **Repository settings > Plugins**.
2. Install the provider libraries: **Settings** (<kbd>Ctrl</kbd>+<kbd>,</kbd>) >
   **External libraries** > **Install / Update**.
3. In **Repository settings > Settings**, choose the **Provider** (Claude
   (Anthropic), OpenAI / OpenCode, Gemini (Google) or Ollama (local)), the
   **Model**, and for cloud providers the **API key**. The key is kept in the
   system keyring when there is one.

## Suggest the fields {#suggest}

- In the rename dialog (<kbd>F2</kbd>), open **Suggest** and choose **Ask the
  model**. The suggestion fills the fields; nothing is renamed until you press
  **Rename**.
- Or right-click and open **Documents > Assistants > Suggest filename…**.

A model can be wrong. Check each field before pressing **Rename**.

## Chat about a document {#chat}

Right-click and open **Documents > Assistants > Chat with document…**, then ask
your questions. An answer can be saved as a note on the document.
