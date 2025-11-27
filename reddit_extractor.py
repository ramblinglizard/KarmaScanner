"""
Reddit Extractor Module

Handles all Reddit API interactions for extracting user and subreddit data.
Includes filtering by score, text content, and concurrent comment processing.
"""

import asyncpraw as praw
import json
import asyncio
from datetime import datetime, timezone


async def download_user_submissions(redditor, msg_queue, limit, score_lower_threshold, score_upper_threshold, post_text_filter):
    """Fetches a user's posts, filtered by score and text, and saves them to a JSON file. Returns the count."""
    username = redditor.name
    posts_for_json = []
    limit_str = "maximum possible" if limit is None else str(limit)
    
    score_parts = []
    if score_lower_threshold is not None:
        score_parts.append(f"score >= {score_lower_threshold}")
    if score_upper_threshold is not None:
        score_parts.append(f"score <= {score_upper_threshold}")
    score_str = " and ".join(score_parts) if score_parts else "none"

    msg_queue.put(f"[INFO] Starting POST extraction for u/{username} (limit: {limit_str}, score threshold: {score_str})...")
    try:
        async for post in redditor.submissions.new(limit=limit):
            score_ok = True
            if score_lower_threshold is not None and post.score < score_lower_threshold:
                score_ok = False
            if score_upper_threshold is not None and post.score > score_upper_threshold:
                score_ok = False
            
            if not score_ok:
                continue

            if post_text_filter and not (post_text_filter.lower() in post.title.lower() or post_text_filter.lower() in post.selftext.lower()):
                continue

            posts_for_json.append({
                'subreddit': post.subreddit.display_name,
                'title': post.title,
                'selftext': post.selftext,
                'score': post.score,
                'url': post.url,
                'created_utc': post.created_utc,
                'created_utc_str': datetime.fromtimestamp(post.created_utc, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            })
        
        post_count = len(posts_for_json)
        timestamp = datetime.now().strftime("_%Y%m%d")
        json_filename = f"user_{username}_posts{timestamp}.json"
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(posts_for_json, f, indent=4, ensure_ascii=False)
        msg_queue.put(f"[SUCCESS] Post extraction complete. File saved: {json_filename}")
        msg_queue.put(f"[SUMMARY] Total posts extracted (after filtering): {post_count}")
        return post_count
    except Exception as e:
        msg_queue.put(f"[ERROR] Could not extract posts: {e}")
        return 0


async def download_user_comments(redditor, msg_queue, limit, score_lower_threshold, score_upper_threshold, comment_text_filter):
    """Fetches a user's comments, filtered by score and text, and saves them to a JSON file. Returns the count."""
    username = redditor.name
    comments_for_json = []
    limit_str = "maximum possible" if limit is None else str(limit)
    
    score_parts = []
    if score_lower_threshold is not None:
        score_parts.append(f"score >= {score_lower_threshold}")
    if score_upper_threshold is not None:
        score_parts.append(f"score <= {score_upper_threshold}")
    score_str = " and ".join(score_parts) if score_parts else "none"

    msg_queue.put(f"[INFO] Starting COMMENT extraction for u/{username} (limit: {limit_str}, score threshold: {score_str})...")
    try:
        async for comment in redditor.comments.new(limit=limit):
            score_ok = True
            if score_lower_threshold is not None and comment.score < score_lower_threshold:
                score_ok = False
            if score_upper_threshold is not None and comment.score > score_upper_threshold:
                score_ok = False

            if not score_ok:
                continue

            if comment.author is None and comment.body == "[removed]":
                continue

            if comment_text_filter and comment_text_filter.lower() not in comment.body.lower():
                continue

            comments_for_json.append({
                'subreddit': comment.subreddit.display_name,
                'body': comment.body,
                'score': comment.score,
                'permalink': f"https://www.reddit.com{comment.permalink}",
                'created_utc_str': datetime.fromtimestamp(comment.created_utc, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
            })

        comment_count = len(comments_for_json)
        timestamp = datetime.now().strftime("_%Y%m%d")
        json_filename = f"user_{username}_comments{timestamp}.json"
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(comments_for_json, f, indent=4, ensure_ascii=False)
        msg_queue.put(f"[SUCCESS] Comment extraction complete. File saved: {json_filename}")
        msg_queue.put(f"[SUMMARY] Total comments extracted (after filtering): {comment_count}")
        return comment_count
    except Exception as e:
        msg_queue.put(f"[ERROR] Could not extract comments: {e}")
        return 0


async def run_user_downloader_async(username, posts_limit, comments_limit, post_score_lower_threshold, post_score_upper_threshold, comment_score_lower_threshold, comment_score_upper_threshold, post_text_filter, comment_text_filter, msg_queue, config):
    """Target function for the user downloader thread."""
    reddit = praw.Reddit(
        client_id=config.get('client_id', ''),
        client_secret=config.get('client_secret', ''),
        user_agent=config.get('user_agent', 'RedditHistoryDownloader/2.0')
    )
    try:
        target_redditor = await reddit.redditor(username)

        results = await asyncio.gather(
            download_user_submissions(target_redditor, msg_queue, posts_limit, post_score_lower_threshold, post_score_upper_threshold, post_text_filter),
            download_user_comments(target_redditor, msg_queue, comments_limit, comment_score_lower_threshold, comment_score_upper_threshold, comment_text_filter)
        )
        post_count, comment_count = results
        
        if post_count == 0 and comment_count == 0:
            msg_queue.put(f"\n[WARNING] User '{username}' has no visible content. The user either has no posts/comments or has set their history to hidden.")
    except Exception as e:
        err_text = str(e)
        if "404" in err_text:
            msg_queue.put(f"[ERROR] User '{username}' does not exist or has been deleted.")
        elif "Redditor' object has no attribute 'id" in err_text or "403" in err_text:
            msg_queue.put(f"[ERROR] User '{username}' has been suspended from Reddit.")
        else:
            msg_queue.put(f"[ERROR] Could not find user '{username}'. Details: {e}")
    finally:
        if reddit: await reddit.close()
    msg_queue.put("--- OPERATION COMPLETE ---")


async def run_subreddit_downloader_async(subreddit_name, sort_method, post_limit, post_score_lower_threshold, post_score_upper_threshold, comment_score_lower_threshold, comment_score_upper_threshold, post_text_filter, comment_text_filter, msg_queue, config):
    """Target function for the subreddit downloader thread, optimized with asyncio and pagination."""
    reddit = praw.Reddit(
        client_id=config.get('client_id', ''),
        client_secret=config.get('client_secret', ''),
        user_agent=config.get('user_agent', 'RedditHistoryDownloader/2.0')
    )
    try:
        subreddit = await reddit.subreddit(subreddit_name)
        
        methods_to_download = [sort_method] if sort_method != 'all' else ['top', 'hot', 'new']
        
        limit_str = "all possible" if post_limit is None else str(post_limit)
        post_score_parts = [s for s in [f"score >= {post_score_lower_threshold}" if post_score_lower_threshold is not None else None, f"score <= {post_score_upper_threshold}" if post_score_upper_threshold is not None else None] if s]
        comment_score_parts = [s for s in [f"score >= {comment_score_lower_threshold}" if comment_score_lower_threshold is not None else None, f"score <= {comment_score_upper_threshold}" if comment_score_upper_threshold is not None else None] if s]
        post_score_str = " and ".join(post_score_parts) or "none"
        comment_score_str = " and ".join(comment_score_parts) or "none"

        msg_queue.put(f"[INFO] Starting extraction for r/{subreddit_name} (methods: {', '.join(methods_to_download)}, post limit: {limit_str})...")
        msg_queue.put(f"[INFO] Post score threshold: {post_score_str}, Comment score threshold: {comment_score_str}")

        posts_to_process = []
        processed_post_ids = set()

        for method in methods_to_download:
            if post_limit is not None and len(posts_to_process) >= post_limit:
                break

            msg_queue.put(f"\n--- Fetching posts from '{method}'. This may take a while... ---")
            
            submissions_iterator = getattr(subreddit, method)(limit=None)

            async for post in submissions_iterator:
                if post.id in processed_post_ids:
                    continue

                score_ok = True
                if post_score_lower_threshold is not None and post.score < post_score_lower_threshold:
                    score_ok = False
                if post_score_upper_threshold is not None and post.score > post_score_upper_threshold:
                    score_ok = False
                
                if not score_ok:
                    continue

                if post_text_filter and not (post_text_filter.lower() in post.title.lower() or post_text_filter.lower() in post.selftext.lower()):
                    continue

                posts_to_process.append(post)
                processed_post_ids.add(post.id)
                if post_limit:
                    msg_queue.put(f"  -> Found matching post {len(posts_to_process)}/{post_limit} (Score: {post.score})")
                
                if post_limit is not None and len(posts_to_process) >= post_limit:
                    break
        
        total_posts_to_process = len(posts_to_process)
        msg_queue.put(f"\n[INFO] Found {total_posts_to_process} unique posts. Now fetching comments concurrently...")

        semaphore = asyncio.Semaphore(15)

        async def process_post_concurrently(post, index, reddit_instance, comment_text_filter):
            async with semaphore:
                msg_queue.put(f"  -> ({index + 1}/{total_posts_to_process}) Processing post (Score: {post.score}): '{post.title[:40]}...' ")
                
                comments_list = []
                try:
                    submission = await reddit_instance.submission(id=post.id)
                    await submission.comments.replace_more(limit=10)
                    
                    for comment in submission.comments.list():
                        comment_score_ok = True
                        if comment_score_lower_threshold is not None and comment.score < comment_score_lower_threshold:
                            comment_score_ok = False
                        if comment_score_upper_threshold is not None and comment.score > comment_score_upper_threshold:
                            comment_score_ok = False

                        if not comment_score_ok:
                            continue

                        if comment.author is None and comment.body == "[removed]":
                            continue

                        if comment_text_filter and comment_text_filter.lower() not in comment.body.lower():
                            continue

                        comments_list.append({
                            'author': str(comment.author),
                            'body': comment.body,
                            'score': comment.score
                        })
                except Exception as e:
                    err_type = type(e).__name__
                    msg_queue.put(f"[WARNING] Could not fetch comments for post '{post.id}'. Error: {e} (Type: {err_type})")

                return {
                    'post_title': post.title,
                    'post_author': str(post.author),
                    'post_score': post.score,
                    'post_url': post.url,
                    'fetched_from': 'unknown',
                    'comments_count': len(comments_list),
                    'comments': comments_list
                }

        tasks = [process_post_concurrently(post, i, reddit, comment_text_filter) for i, post in enumerate(posts_to_process)]
        all_data = await asyncio.gather(*tasks)

        timestamp = datetime.now().strftime("_%Y%m%d")
        json_filename = f"subreddit_{subreddit_name}_{sort_method}_posts{timestamp}.json"
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, indent=4, ensure_ascii=False)
        msg_queue.put(f"\n[SUCCESS] Subreddit extraction complete. File saved: {json_filename}")
        msg_queue.put(f"TOTAL UNIQUE POSTS EXTRACTED (after filtering): {len(all_data)}")

    except Exception as e:
        err_text = str(e)
        if "403" in err_text:
            msg_queue.put(f"\n[ERROR] Could not access subreddit '{subreddit_name}'. It may be private or restricted.")
        elif "404" in err_text:
            msg_queue.put(f"\n[ERROR] Subreddit '{subreddit_name}' may have been banned.")
        elif "/subreddits/search" in err_text:
            msg_queue.put(f"\n[ERROR] Subreddit '{subreddit_name}' could not be found.")
        else:
            msg_queue.put(f"\n[ERROR] Could not process subreddit '{subreddit_name}'. Details: {e}")
    finally:
        if reddit: await reddit.close()
    msg_queue.put("\n--- OPERATION COMPLETE ---\\n")
