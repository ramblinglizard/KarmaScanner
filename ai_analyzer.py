"""
AI Analyzer Module

Handles AI-powered user analysis using Google Gemini API.
Includes intelligent chunking for large histories, rate limiting, and exponential backoff.
"""

import asyncpraw as praw
import asyncio
from datetime import datetime, timezone, timedelta
import google.generativeai as genai


async def extract_user_history_for_ai(username, time_limit_days, config, msg_queue):
    """Extracts user's posts and comments for AI analysis, filtered by time period."""
    reddit = praw.Reddit(
        client_id=config.get('client_id', ''),
        client_secret=config.get('client_secret', ''),
        user_agent=config.get('user_agent', 'RedditHistoryDownloader/2.0')
    )
    
    posts_list = []
    comments_list = []
    
    try:
        msg_queue.put(f"[INFO] Extracting history for u/{username}...")
        redditor = await reddit.redditor(username)
        
        # Calculate cutoff time
        if time_limit_days > 0:
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=time_limit_days)
            cutoff_timestamp = cutoff_time.timestamp()
        else:
            cutoff_timestamp = 0  # Get all history
        
        # Extract posts
        msg_queue.put("[INFO] Fetching posts...")
        post_count = 0
        async for post in redditor.submissions.new(limit=None):
            if post.created_utc < cutoff_timestamp:
                break
            posts_list.append({
                'type': 'post',
                'subreddit': post.subreddit.display_name,
                'title': post.title,
                'selftext': post.selftext,
                'score': post.score,
                'url': post.url,
                'created_utc': post.created_utc,
                'created_str': datetime.fromtimestamp(post.created_utc, tz=timezone.utc).strftime('%Y-%m-%d %H:%M')
            })
            post_count += 1
            if post_count % 50 == 0:
                msg_queue.put(f"  -> Found {post_count} posts...")
        
        msg_queue.put(f"[SUCCESS] Extracted {len(posts_list)} posts")
        
        # Extract comments
        msg_queue.put("[INFO] Fetching comments...")
        comment_count = 0
        async for comment in redditor.comments.new(limit=None):
            if comment.created_utc < cutoff_timestamp:
                break
            if comment.author is None and comment.body == "[removed]":
                continue
            comments_list.append({
                'type': 'comment',
                'subreddit': comment.subreddit.display_name,
                'body': comment.body,
                'score': comment.score,
                'created_utc': comment.created_utc,
                'created_str': datetime.fromtimestamp(comment.created_utc, tz=timezone.utc).strftime('%Y-%m-%d %H:%M')
            })
            comment_count += 1
            if comment_count % 100 == 0:
                msg_queue.put(f"  -> Found {comment_count} comments...")
        
        msg_queue.put(f"[SUCCESS] Extracted {len(comments_list)} comments")
        msg_queue.put(f"[SUMMARY] Total items: {len(posts_list) + len(comments_list)}")
        
        return posts_list, comments_list
        
    except Exception as e:
        err_text = str(e)
        if "404" in err_text:
            msg_queue.put(f"[ERROR] User '{username}' does not exist or has been deleted.")
        elif "403" in err_text:
            msg_queue.put(f"[ERROR] User '{username}' has been suspended from Reddit.")
        else:
            msg_queue.put(f"[ERROR] Could not extract user history: {e}")
        return [], []
    finally:
        if reddit:
            await reddit.close()


def format_history_for_ai(posts, comments, max_items=500):
    """Formats user history into an ULTRA-COMPACT text for AI analysis to save tokens."""
    all_items = posts + comments
    all_items.sort(key=lambda x: x['created_utc'], reverse=True)
    
    if len(all_items) > max_items:
        all_items = all_items[:max_items]
    
    # Ultra-compact header
    post_count = len([i for i in all_items if i['type'] == 'post'])
    comment_count = len(all_items) - post_count
    
    # Single line per item, minimal formatting
    lines = [f"Posts:{post_count} Comments:{comment_count}\n"]
    
    for item in all_items:
        if item['type'] == 'post':
            # Format: P|subreddit|title [truncated_body]
            title = item['title'][:80]  # Limit title
            body = item['selftext'][:150] if item['selftext'] else ""  # Limit body
            lines.append(f"P|r/{item['subreddit']}|{title}|{body}")
        else:
            # Format: C|subreddit|comment_text
            body = item['body'][:200]  # Limit comment length
            lines.append(f"C|r/{item['subreddit']}|{body}")
    
    return '\n'.join(lines)


def estimate_tokens(text):
    """Estimates the number of tokens in text (rough approximation: 1 token ≈ 4 characters)."""
    return len(text) // 4


def chunk_items(all_items, max_tokens_per_chunk=70000):
    """Splits items into chunks that fit within token limits."""
    chunks = []
    current_chunk = []
    current_tokens = 0
    
    header_tokens = 50  # Reserve for header
    
    for item in all_items:
        # Estimate tokens for this item
        if item['type'] == 'post':
            title = item['title'][:80]
            body = item['selftext'][:150] if item['selftext'] else ""
            item_text = f"P|r/{item['subreddit']}|{title}|{body}"
        else:
            body = item['body'][:200]
            item_text = f"C|r/{item['subreddit']}|{body}"
        
        item_tokens = estimate_tokens(item_text)
        
        # If adding this item would exceed limit, start new chunk
        if current_tokens + item_tokens > max_tokens_per_chunk and current_chunk:
            chunks.append(current_chunk)
            current_chunk = []
            current_tokens = header_tokens
        
        current_chunk.append(item)
        current_tokens += item_tokens
    
    # Add remaining items
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks


async def query_gemini_with_retry(model, prompt, msg_queue, max_retries=3):
    """Queries Gemini with exponential backoff for rate limiting."""
    for attempt in range(max_retries):
        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: model.generate_content(prompt)
            )
            return True, response.text
        except Exception as e:
            error_str = str(e)
            
            # Check if it's a rate limit error (429)
            if '429' in error_str or 'quota' in error_str.lower():
                if attempt < max_retries - 1:
                    # Exponential backoff: 5s, 10s, 20s
                    wait_time = 5 * (2 ** attempt)
                    msg_queue.put(f"[WARNING] Rate limit hit. Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    msg_queue.put(f"[ERROR] Rate limit persists after {max_retries} attempts")
                    return False, f"Rate limit error: {error_str}"
            else:
                # Non-rate-limit error, don't retry
                return False, f"Error: {error_str}"
    
    return False, "Max retries exceeded"


async def analyze_with_chunking(api_key, user_question, all_items, msg_queue):
    """Analyzes large history by chunking, with rate limiting and final synthesis."""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('models/gemini-2.0-flash-001')
    
    # Estimate total tokens
    total_text = '\n'.join([
        f"P|{i['subreddit']}|{i.get('title', '')[:80]}|{i.get('selftext', '')[:150]}"
        if i['type'] == 'post' else
        f"C|{i['subreddit']}|{i['body'][:200]}"
        for i in all_items
    ])
    total_tokens = estimate_tokens(total_text)
    
    msg_queue.put(f"[INFO] Total estimated tokens: ~{total_tokens:,}")
    
    # If fits in single request, use normal path
    if total_tokens < 80000:
        msg_queue.put("[INFO] History fits in single request")
        formatted_history = format_history_for_ai(
            [i for i in all_items if i['type'] == 'post'],
            [i for i in all_items if i['type'] == 'comment']
        )
        
        prompt = f"""Analyze this Reddit user's activity and answer the question below.

DATA FORMAT (ultra-compact to save tokens):
- First line: Posts:N Comments:M
- P|subreddit|title|body = Post
- C|subreddit|text = Comment

QUESTION: {user_question}

USER ACTIVITY:
{formatted_history}

Provide a detailed, insightful answer based on patterns and topics in their activity. Reference specific examples."""
        
        msg_queue.put("[INFO] Sending request to Gemini AI...")
        return await query_gemini_with_retry(model, prompt, msg_queue)
    
    # Multi-chunk analysis
    chunks = chunk_items(all_items, max_tokens_per_chunk=70000)
    msg_queue.put(f"[INFO] Splitting into {len(chunks)} chunks to stay within limits")
    
    partial_answers = []
    
    for i, chunk in enumerate(chunks, 1):
        msg_queue.put(f"[INFO] Analyzing chunk {i}/{len(chunks)} ({len(chunk)} items)...")
        
        # Format this chunk
        chunk_posts = [item for item in chunk if item['type'] == 'post']
        chunk_comments = [item for item in chunk if item['type'] == 'comment']
        chunk_formatted = format_history_for_ai(chunk_posts, chunk_comments, max_items=len(chunk))
        
        prompt = f"""Analyze this PARTIAL Reddit user activity (chunk {i}/{len(chunks)}) and answer the question.

QUESTION: {user_question}

PARTIAL ACTIVITY:
{chunk_formatted}

Provide insights based on THIS chunk only. Keep response concise as it will be combined with other chunks."""
        
        success, response = await query_gemini_with_retry(model, prompt, msg_queue)
        
        if not success:
            msg_queue.put(f"[WARNING] Chunk {i} failed: {response}")
            continue
        
        partial_answers.append(f"## Chunk {i}/{len(chunks)} Analysis:\n{response}")
        
        # Rate limiting: wait 5 seconds between chunks (free tier: 15 RPM = 4s minimum)
        if i < len(chunks):
            msg_queue.put(f"[INFO] Waiting 5s before next chunk (rate limiting)...")
            await asyncio.sleep(5)
    
    if not partial_answers:
        return False, "All chunks failed to analyze"
    
    # Synthesize final answer
    msg_queue.put(f"[INFO] Synthesizing {len(partial_answers)} partial answers into final response...")
    
    synthesis_prompt = f"""You analyzed a Reddit user in {len(chunks)} parts. Below are the partial analyses.

ORIGINAL QUESTION: {user_question}

PARTIAL ANALYSES:
{'\\n\\n'.join(partial_answers)}

Synthesize these partial analyses into ONE comprehensive, coherent answer to the original question. Combine insights, identify patterns across all chunks, and provide a unified perspective."""
    
    # Final synthesis (after another delay)
    await asyncio.sleep(5)
    success, final_response = await query_gemini_with_retry(model, synthesis_prompt, msg_queue)
    
    if success:
        msg_queue.put(f"[SUCCESS] Multi-chunk analysis complete!")
    
    return success, final_response


async def run_ai_analysis_async(username, time_limit_days, user_question, config, msg_queue):
    """Main function to run AI analysis on a Reddit user."""
    msg_queue.put(f"\n--- STARTING AI ANALYSIS FOR u/{username} ---")
    
    gemini_api_key = config.get('gemini_api_key', '').strip()
    if not gemini_api_key:
        msg_queue.put("[ERROR] Gemini API key not configured. Please add it in the Settings tab.")
        msg_queue.put("--- OPERATION COMPLETE ---")
        return False, ""
    
    posts, comments = await extract_user_history_for_ai(username, time_limit_days, config, msg_queue)
    
    if not posts and not comments:
        msg_queue.put("[ERROR] No history found for this user in the selected time period.")
        msg_queue.put("--- OPERATION COMPLETE ---")
        return False, ""
    
    msg_queue.put("[INFO] Preparing data for AI analysis...")
    
    # Combine posts and comments into unified list
    all_items = posts + comments
    
    # Use new chunking system with automatic rate limiting
    success, response = await analyze_with_chunking(gemini_api_key, user_question, all_items, msg_queue)
    
    msg_queue.put("--- OPERATION COMPLETE ---")
    return success, response
