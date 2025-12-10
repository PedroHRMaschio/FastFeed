from fastapi import FastAPI, HTTPException
from src.schemas import PostCreate


app = FastAPI()

text_post = {
    1: {
        "title": "Getting Started with FastAPI",
        "content": "FastAPI is a modern, fast web framework for building APIs with Python 3.7+. It's based on standard Python type hints and provides automatic interactive API documentation. In this post, we'll explore the basics of setting up your first FastAPI application and why it's becoming the go-to choice for Python developers."
    },
    2: {
        "title": "10 Hidden Gems in Tokyo",
        "content": "Tokyo is full of surprises beyond the usual tourist spots. From quiet temples in Yanaka to the retro vibes of Koenji, discover places where locals actually hang out. Don't miss the tiny jazz bars in Kichijoji!"
    },
    3: {
        "title": "The Perfect Sourdough Recipe",
        "content": "After years of experimentation, I've finally perfected my sourdough recipe. The key is patience and maintaining your starter properly. Here's everything you need to know about hydration ratios, fermentation times, and achieving that perfect crust."
    },
    4: {
        "title": "Why I Switched to Vim",
        "content": "As a developer, I was skeptical about Vim for years. The learning curve seemed too steep. But after forcing myself to use it for just two weeks, I can't imagine going back. The efficiency gains are real, and my hands barely leave the keyboard anymore."
    },
    5: {
        "title": "Morning Routines That Actually Work",
        "content": "Forget the 5 AM wake-up calls and cold showers. A sustainable morning routine is about consistency, not extremes. Here's what actually helped me become more productive without burning out."
    },
    6: {
        "title": "Understanding Docker Containers",
        "content": "Docker has revolutionized how we deploy applications, but the concepts can be confusing at first. Let's break down images, containers, volumes, and networks in a way that actually makes sense. By the end of this guide, you'll be containerizing your apps with confidence."
    },
    7: {
        "title": "My Journey to Running a Marathon",
        "content": "A year ago, I couldn't run a mile without stopping. Today, I completed my first marathon. This is the training plan that got me there, including the mistakes I made and how I overcame them. Spoiler: it's not just about running more."
    },
    8: {
        "title": "Film Photography in 2025",
        "content": "In a world of digital perfection, shooting film forces you to slow down and be intentional. Each frame costs money, so you think before you shoot. The grain, the colors, the anticipation of getting your photos back - there's something magical about the analog process."
    },
    9: {
        "title": "Indie Games Worth Your Time",
        "content": "AAA titles get all the attention, but some of the best gaming experiences come from small indie studios. From narrative masterpieces to innovative gameplay mechanics, here are 5 indie games that deserve more recognition."
    },
    10: {
        "title": "Climate Action Starts at Home",
        "content": "Individual actions matter more than you think. Simple changes like reducing food waste, choosing sustainable products, and supporting green energy can collectively make a huge impact. Here's a practical guide to reducing your carbon footprint without completely overhauling your lifestyle."
    }
}


@app.get("/posts")
def get_all_posts(limit: int = None, page: int = 1):
    if limit:
        all_posts = list(text_post.values())
        start_index = (page - 1) * limit
        end_index = start_index + limit
        return all_posts[start_index:end_index]
    return text_post


@app.get("/posts/{post_id}")
def get_post(post_id: int):
    if post_id not in text_post:
        raise HTTPException(status_code=404, detail="Post not found")
    return text_post.get(post_id)


@app.post("/posts")
def create_post(post: PostCreate):
    new_post_id = max(text_post.keys()) + 1
    text_post[new_post_id] = post
    return text_post[new_post_id]

