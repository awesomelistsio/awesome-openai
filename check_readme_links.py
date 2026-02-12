#!/usr/bin/env python3
"""
README Link Checker

This script checks the online status of links in a README.md file. It extracts all URLs from the README file
and sends HTTP requests to each URL to determine if the link is online or not.

Usage:
    python check_readme_links.py [path/to/README.md]
    
If no file path is provided, it will look for README.md in the current directory.

Author: Saswat Tulo
"""

import requests
import re
import sys
import os
from urllib.parse import urlparse
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

def extract_urls(content):
    """Extract URLs from markdown content using multiple patterns."""
    patterns = [
        r'\[.*?\]\((https?://.*?)\)',  # Markdown links
        r'<(https?://.*?)>',           # Direct links in angle brackets
        r'(?:^|\s)(https?://\S+)',     # Bare URLs
    ]
    
    urls = set()
    for pattern in patterns:
        matches = re.findall(pattern, content, re.MULTILINE)
        urls.update(matches)
    
    return list(urls)

def check_single_link(url, timeout=10):
    """Check if a single URL is accessible."""
    try:
        # Try HEAD request first (faster)
        response = requests.head(url, timeout=timeout, allow_redirects=True)
        
        # If HEAD fails, try GET (some servers don't support HEAD)
        if response.status_code >= 400:
            response = requests.get(url, timeout=timeout, allow_redirects=True)
        
        return {
            'url': url,
            'status_code': response.status_code,
            'status': 'online' if response.status_code < 400 else 'error',
            'error': None,
            'final_url': response.url if response.url != url else None
        }
    except requests.exceptions.Timeout:
        return {
            'url': url,
            'status_code': None,
            'status': 'timeout',
            'error': 'Request timed out',
            'final_url': None
        }
    except requests.exceptions.ConnectionError:
        return {
            'url': url,
            'status_code': None,
            'status': 'connection_error',
            'error': 'Connection failed',
            'final_url': None
        }
    except requests.exceptions.RequestException as e:
        return {
            'url': url,
            'status_code': None,
            'status': 'error',
            'error': str(e),
            'final_url': None
        }

def check_links(file_path, max_workers=5, timeout=10, verbose=False):
    """Check all links in a README file."""
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found.")
        return False
    
    try:
        with open(file_path, 'r', encoding='utf-8') as readme_file:
            contents = readme_file.read()
    except UnicodeDecodeError:
        print(f"Error: Could not read file '{file_path}' as UTF-8.")
        return False
    
    urls = extract_urls(contents)
    
    if not urls:
        print("No URLs found in the README file.")
        return True
    
    print(f"Found {len(urls)} URLs to check...\n")
    
    results = []
    online_count = 0
    error_count = 0
    
    # Check links concurrently
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {executor.submit(check_single_link, url, timeout): url for url in urls}
        
        for future in as_completed(future_to_url):
            result = future.result()
            results.append(result)
            
            # Print results as they come in
            if result['status'] == 'online':
                online_count += 1
                if verbose:
                    print(f"✓ {result['url']} (Status: {result['status_code']})")
                    if result['final_url']:
                        print(f"  → Redirected to: {result['final_url']}")
            else:
                error_count += 1
                print(f"✗ {result['url']} - {result['status'].title()}")
                if result['status_code']:
                    print(f"  Status code: {result['status_code']}")
                if result['error']:
                    print(f"  Error: {result['error']}")
    
    # Summary
    print(f"\n{'='*50}")
    print(f"Summary:")
    print(f"Total URLs checked: {len(urls)}")
    print(f"Online: {online_count}")
    print(f"Errors: {error_count}")
    print(f"{'='*50}")
    
    return error_count == 0

def main():
    parser = argparse.ArgumentParser(description='Check links in README.md files')
    parser.add_argument('file', nargs='?', default='README.md', 
                       help='Path to README file (default: README.md)')
    parser.add_argument('-t', '--timeout', type=int, default=10,
                       help='Request timeout in seconds (default: 10)')
    parser.add_argument('-w', '--workers', type=int, default=5,
                       help='Number of concurrent workers (default: 5)')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Show successful links as well')
    
    args = parser.parse_args()
    
    print(f"Checking links in: {args.file}")
    print(f"Timeout: {args.timeout}s | Workers: {args.workers}")
    print("-" * 50)
    
    success = check_links(args.file, args.workers, args.timeout, args.verbose)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()