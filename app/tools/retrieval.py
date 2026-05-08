import httpx
from bs4 import BeautifulSoup
from app.models import SourceDocument


async def url_retrieval_tool(urls: list[str]) -> list[SourceDocument]:
    docs = []
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        for url in urls:
            try:
                resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                soup = BeautifulSoup(resp.text, "html.parser")
                for tag in soup(["script", "style", "nav", "footer", "header"]):
                    tag.decompose()
                text = soup.get_text(separator="\n", strip=True)
                docs.append(SourceDocument(
                    source_type="url",
                    source_id=url,
                    content=text[:8000],
                ))
            except Exception as e:
                docs.append(SourceDocument(
                    source_type="url",
                    source_id=url,
                    content="",
                    metadata={"error": str(e)},
                ))
    return docs


def file_retrieval_tool(files: list[dict]) -> list[SourceDocument]:
    docs = []
    for f in files:
        docs.append(SourceDocument(
            source_type="file",
            source_id=f.get("name", "unknown"),
            content=f.get("content", ""),
        ))
    return docs


def text_processor_tool(content: str) -> SourceDocument:
    return SourceDocument(
        source_type="text",
        source_id="inline",
        content=content,
    )
