# Anthropic Citations Quick Reference

Claude's Messages API can return source-grounded citation metadata when you provide documents and enable citations on the request. This is useful for document question answering workflows where users need to verify exactly which source text supports an answer.

## Availability and retention

- Citations are available on active Claude models except Haiku 3.
- The feature is eligible for Zero Data Retention (ZDR) arrangements. When an organization has ZDR enabled, submitted data is not stored after the API response is returned.
- Citations work with prompt caching, token counting, and batch processing.
- Citations are incompatible with Structured Outputs. Requests that enable citations and also set `output_config.format` or the deprecated `output_format` parameter will return a `400` error.

## Basic request shape

Enable citations on each document block by setting `citations.enabled` to `true`. Citations must currently be enabled on either all documents in a request or none of them.

```python
import anthropic

client = anthropic.Anthropic()

response = client.messages.create(
    model="claude-opus-4-8",
    max_tokens=1024,
    messages=[
        {
            "role": "user",
            "content": [
                {
                    "type": "document",
                    "source": {
                        "type": "text",
                        "media_type": "text/plain",
                        "data": "The grass is green. The sky is blue.",
                    },
                    "title": "My Document",
                    "context": "This is trustworthy background metadata.",
                    "citations": {"enabled": True},
                },
                {"type": "text", "text": "What color is the grass and sky?"},
            ],
        }
    ],
)
```

## How citation generation works

1. Add one or more supported document blocks to the user message.
2. Set `citations.enabled=true` on each document block.
3. Claude processes the document content into citable chunks.
4. The response may contain multiple text content blocks, each with citation objects that point back to source locations.

Only text can currently be cited. Images inside PDFs are not citable.

## Citable and non-citable fields

The text inside a document's `source` is citable. Optional `title` and `context` fields are passed to Claude for additional context, but they are not used as cited content. Use `context` for source metadata such as trust notes, dates, or stringified JSON metadata.

## Document types

| Type | Best for | Chunking | Citation location |
| --- | --- | --- | --- |
| Plain text | Simple prose and text snippets | Sentence chunking | 0-indexed character ranges |
| PDF | Text-based PDF documents | Extracted text, then sentence chunking | 1-indexed page ranges |
| Custom content | Lists, transcripts, RAG chunks, or custom granularity | No additional chunking | 0-indexed content block ranges |

`.csv`, `.xlsx`, `.docx`, `.md`, and `.txt` files are not supported directly as document blocks. Convert these files to plain text and send the text inline, or use another supported representation.

### Plain text document

```python
{
    "type": "document",
    "source": {
        "type": "text",
        "media_type": "text/plain",
        "data": "Plain text content...",
    },
    "title": "Document Title",
    "context": "Metadata that will not be cited from",
    "citations": {"enabled": True},
}
```

Plain text citations use `char_location` objects with `start_char_index` and `end_char_index`. Character indices are 0-indexed, and the end index is exclusive.

### PDF document

```python
{
    "type": "document",
    "source": {
        "type": "base64",
        "media_type": "application/pdf",
        "data": base64_encoded_pdf_data,
    },
    "title": "Document Title",
    "context": "Metadata that will not be cited from",
    "citations": {"enabled": True},
}
```

PDFs can also be supplied by URL or by `file_id`. PDF citations use `page_location` objects with `start_page_number` and `end_page_number`. Page numbers are 1-indexed, and the end page is exclusive.

### Custom content document

```python
{
    "type": "document",
    "source": {
        "type": "content",
        "content": [
            {"type": "text", "text": "First chunk"},
            {"type": "text", "text": "Second chunk"},
        ],
    },
    "title": "Document Title",
    "context": "Metadata that will not be cited from",
    "citations": {"enabled": True},
}
```

Custom content citations use `content_block_location` objects with `start_block_index` and `end_block_index`. Block indices are 0-indexed, and the end index is exclusive.

## Prompt caching with citations

When a document is large enough to benefit from prompt caching, add `cache_control` to the top-level document block. Citation blocks generated in model responses are not cached directly, but the source documents they reference can be cached.

```python
{
    "type": "document",
    "source": {
        "type": "text",
        "media_type": "text/plain",
        "data": long_document,
    },
    "citations": {"enabled": True},
    "cache_control": {"type": "ephemeral"},
}
```

## Response structure

When citations are enabled, response content can include several text blocks. Blocks that make source-backed claims may include a `citations` list. Each citation includes:

- `type`, such as `char_location`, `page_location`, or `content_block_location`.
- `cited_text`, supplied for convenience and not counted toward output tokens.
- `document_index`, a 0-indexed pointer to the source document in the request.
- `document_title`, when a title was supplied.
- Location fields appropriate to the document type.

For streaming responses, citation metadata is delivered with `citations_delta` events that add citation objects to the current text content block.
