"""
Web tool module for Amplifier.
Provides web search and fetch capabilities.
"""
import logging
import aiohttp
from typing import Dict, Any, Optional
from urllib.parse import urlparse, quote
from bs4 import BeautifulSoup

from amplifier_core import ModuleCoordinator, ToolResult

logger = logging.getLogger(__name__)


async def mount(coordinator: ModuleCoordinator, config: Optional[Dict[str, Any]] = None):
    """Mount web tools."""
    config = config or {}
    
    tools = [
        WebSearchTool(config),
        WebFetchTool(config),
    ]
    
    for tool in tools:
        await coordinator.mount('tools', tool, name=tool.name)
    
    logger.info(f"Mounted {len(tools)} web tools")
    return None


class WebSearchTool:
    """Simple web search tool (mock implementation)."""
    
    name = "web_search"
    description = "Search the web for information"
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.search_engine = config.get('search_engine', 'mock')
        self.api_key = config.get('api_key')
        self.max_results = config.get('max_results', 5)
    
    async def execute(self, input: Dict[str, Any]) -> ToolResult:
        """Execute web search."""
        query = input.get('query')
        if not query:
            return ToolResult(
                success=False,
                error={'message': 'Query is required'}
            )
        
        try:
            # Mock search results for now
            # In production, integrate with real search API
            results = await self._mock_search(query)
            
            return ToolResult(
                success=True,
                output={
                    'query': query,
                    'results': results,
                    'count': len(results)
                }
            )
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            return ToolResult(
                success=False,
                error={'message': str(e)}
            )
    
    async def _mock_search(self, query: str) -> list:
        """Mock search implementation."""
        # In production, replace with actual search API call
        return [
            {
                'title': f'Result 1 for {query}',
                'url': 'https://example.com/1',
                'snippet': f'This is a mock search result for {query}...'
            },
            {
                'title': f'Result 2 for {query}',
                'url': 'https://example.com/2',
                'snippet': f'Another mock result about {query}...'
            },
            {
                'title': f'Result 3 for {query}',
                'url': 'https://example.com/3',
                'snippet': f'More information about {query}...'
            }
        ][:self.max_results]


class WebFetchTool:
    """Fetch and parse web pages."""
    
    name = "web_fetch"
    description = "Fetch content from a web URL"
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.timeout = config.get('timeout', 10)
        self.max_size = config.get('max_size', 1024 * 1024)  # 1MB default
        self.allowed_domains = config.get('allowed_domains', [])
        self.blocked_domains = config.get('blocked_domains', [
            'localhost',
            '127.0.0.1',
            '0.0.0.0',
            '192.168.',
            '10.',
            '172.16.',
        ])
        self.extract_text = config.get('extract_text', True)
    
    async def execute(self, input: Dict[str, Any]) -> ToolResult:
        """Fetch content from URL."""
        url = input.get('url')
        if not url:
            return ToolResult(
                success=False,
                error={'message': 'URL is required'}
            )
        
        # Validate URL
        if not self._is_valid_url(url):
            return ToolResult(
                success=False,
                error={'message': f'Invalid or blocked URL: {url}'}
            )
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                    headers={'User-Agent': 'Amplifier/1.0'}
                ) as response:
                    # Check response
                    if response.status != 200:
                        return ToolResult(
                            success=False,
                            error={
                                'message': f'HTTP {response.status}: {response.reason}'
                            }
                        )
                    
                    # Check content size
                    content_length = response.headers.get('Content-Length')
                    if content_length and int(content_length) > self.max_size:
                        return ToolResult(
                            success=False,
                            error={'message': 'Content too large'}
                        )
                    
                    # Read content
                    content = await response.text()
                    
                    # Extract text if requested
                    if self.extract_text:
                        text = self._extract_text(content, response.content_type)
                    else:
                        text = content
                    
                    return ToolResult(
                        success=True,
                        output={
                            'url': url,
                            'content': text[:self.max_size],
                            'content_type': response.content_type,
                            'length': len(text)
                        }
                    )
                    
        except asyncio.TimeoutError:
            return ToolResult(
                success=False,
                error={'message': f'Timeout fetching {url}'}
            )
        except Exception as e:
            logger.error(f"Fetch error: {e}")
            return ToolResult(
                success=False,
                error={'message': str(e)}
            )
    
    def _is_valid_url(self, url: str) -> bool:
        """Validate URL for safety."""
        try:
            parsed = urlparse(url)
            
            # Must have scheme and netloc
            if not parsed.scheme or not parsed.netloc:
                return False
            
            # Only allow http/https
            if parsed.scheme not in ['http', 'https']:
                return False
            
            # Check blocked domains
            for blocked in self.blocked_domains:
                if blocked in parsed.netloc:
                    logger.warning(f"Blocked domain: {parsed.netloc}")
                    return False
            
            # Check allowed domains if configured
            if self.allowed_domains:
                allowed = any(
                    domain in parsed.netloc
                    for domain in self.allowed_domains
                )
                if not allowed:
                    logger.warning(f"Domain not in allowlist: {parsed.netloc}")
                    return False
            
            return True
            
        except Exception:
            return False
    
    def _extract_text(self, content: str, content_type: str) -> str:
        """Extract text from HTML content."""
        if 'html' in content_type:
            try:
                soup = BeautifulSoup(content, 'html.parser')
                
                # Remove script and style elements
                for script in soup(['script', 'style']):
                    script.decompose()
                
                # Get text
                text = soup.get_text()
                
                # Clean up whitespace
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                text = '\n'.join(chunk for chunk in chunks if chunk)
                
                return text
                
            except Exception as e:
                logger.warning(f"Failed to extract text: {e}")
                return content
        else:
            return content
