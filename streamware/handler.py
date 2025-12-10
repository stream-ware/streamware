"""
Streamware Protocol Handler

Handles stream:// URLs from system (browser, terminal).
Format: stream://<component>/<action>?param=value

Example:
    stream://http/get?url=https://example.com
    stream://curllm/browse?url=https://example.com
"""

import sys
import urllib.parse
from .core import flow
from .cli import output_result

class MockArgs:
    def __init__(self, output=None, format="json"):
        self.output = output
        self.format = format

def main():
    """Main handler entry point"""
    if len(sys.argv) < 2:
        print("Usage: stream-handler <url>")
        sys.exit(1)
        
    url = sys.argv[1]
    
    # Remove stream: prefix if present (browsers send it)
    if url.startswith("stream:"):
        # Handle stream:// vs stream:
        if url.startswith("stream://"):
            # Already in correct format for flow() if we map it
            # stream://http/get -> http://get (not valid for flow usually)
            # flow() expects protocol://...
            
            # We need to convert stream://protocol/action... to protocol://action...
            parsed = urllib.parse.urlparse(url)
            
            # Host becomes protocol, path becomes action
            protocol = parsed.netloc
            path = parsed.path.lstrip('/')
            query = parsed.query
            
            # Reconstruct as standard URI
            real_uri = f"{protocol}://{path}"
            if query:
                real_uri += f"?{query}"
                
            print(f"Executing: {real_uri}")
            
            try:
                pipeline = flow(real_uri)
                result = pipeline.run()
                
                # Show result
                print("\nResult:")
                print("-" * 50)
                output_result(result, MockArgs(format="json"))
                input("\nPress Enter to close...")
                
            except Exception as e:
                print(f"Error: {e}")
                input("\nPress Enter to close...")
                sys.exit(1)
                
    else:
        print(f"Invalid URL: {url}")
        sys.exit(1)

if __name__ == "__main__":
    main()
