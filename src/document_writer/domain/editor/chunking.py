from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    index: int
    text: str
    leading_separator: str = ""
    trailing_separator: str = ""


def _is_blank_line(line: str) -> bool:
    if line == "":
        return True
    return line.rstrip("\r\n") == ""

def _is_hard_separator(line: str) -> bool:
    return line.rstrip("\r\n") == "---"


def split_markdown(text: str) -> list[Chunk]:
    if text == "":
        return []
    lines = text.splitlines(keepends=True)
    chunks: list[Chunk] = []
    current_lines: list[str] = []
    leading_separator = ""
    trailing_separator = ""

    def _flush_current() -> None:
        nonlocal current_lines, leading_separator, trailing_separator
        chunk_text = "".join(current_lines)
        chunks.append(
            Chunk(
                index=len(chunks),
                text=chunk_text,
                leading_separator=leading_separator,
                trailing_separator=trailing_separator,
            )
        )
        current_lines = []
        leading_separator = ""
        trailing_separator = ""

    for line in lines:
        if _is_hard_separator(line):
            if current_lines:
                _flush_current()
            elif leading_separator:
                chunks.append(
                    Chunk(
                        index=len(chunks),
                        text="",
                        leading_separator=leading_separator,
                        trailing_separator="",
                    )
                )
                leading_separator = ""
            chunks.append(
                Chunk(
                    index=len(chunks),
                    text=line,
                    leading_separator="",
                    trailing_separator="",
                )
            )
            trailing_separator = ""
            continue
        if _is_blank_line(line):
            if current_lines:
                trailing_separator += line
            else:
                leading_separator += line
            continue

        if current_lines and trailing_separator:
            _flush_current()
        if not current_lines:
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        _flush_current()
    elif leading_separator:
        chunks.append(
            Chunk(
                index=0,
                text="",
                leading_separator=leading_separator,
                trailing_separator="",
            )
        )
    return chunks


def join_chunks(chunks: list[Chunk]) -> str:
    if not chunks:
        return ""
    return "".join(
        chunk.leading_separator + chunk.text + chunk.trailing_separator
        for chunk in chunks
    )


def assert_round_trip(text: str) -> None:
    reconstructed = join_chunks(split_markdown(text))
    assert reconstructed == text
