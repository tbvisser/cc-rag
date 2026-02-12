from app.config import get_settings


# Separators ordered by preference: paragraphs → lines → sentences → words → chars
SEPARATORS = ["\n\n", "\n", ". ", " ", ""]


def chunk_text(text: str) -> list[str]:
    """
    Split text into overlapping chunks using recursive character splitting.

    Tries to split on natural boundaries (paragraphs, lines, sentences)
    before falling back to word/character splits.
    """
    settings = get_settings()
    return _recursive_split(text, SEPARATORS, settings.chunk_size, settings.chunk_overlap)


def _recursive_split(
    text: str,
    separators: list[str],
    chunk_size: int,
    chunk_overlap: int,
) -> list[str]:
    if len(text) <= chunk_size:
        stripped = text.strip()
        return [stripped] if stripped else []

    # Find the best separator that produces splits
    separator = separators[-1]
    for sep in separators:
        if sep in text:
            separator = sep
            break

    # Split the text
    if separator == "":
        splits = list(text)
    else:
        splits = text.split(separator)

    # Merge splits into chunks respecting size limits
    chunks: list[str] = []
    current = ""

    for split in splits:
        piece = split if separator == "" else split + separator
        test = current + piece

        if len(test) > chunk_size and current:
            chunk = current.rstrip(separator).strip()
            if chunk:
                chunks.append(chunk)

            # Apply overlap: keep the tail of the current chunk
            if chunk_overlap > 0 and len(current) > chunk_overlap:
                current = current[-chunk_overlap:]
            else:
                current = ""

            current += piece
        else:
            current = test

    # Don't forget the last chunk
    if current:
        chunk = current.rstrip(separator).strip()
        if chunk:
            chunks.append(chunk)

    # If any chunk is still too large, recursively split with next separator
    remaining_separators = separators[separators.index(separator) + 1 :] if separator in separators else separators[-1:]
    if not remaining_separators:
        return chunks

    final_chunks: list[str] = []
    for chunk in chunks:
        if len(chunk) > chunk_size:
            final_chunks.extend(
                _recursive_split(chunk, remaining_separators, chunk_size, chunk_overlap)
            )
        else:
            final_chunks.append(chunk)

    return final_chunks
