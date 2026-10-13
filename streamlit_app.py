import os
import streamlit as st
import cloudinary
import cloudinary.uploader
from pymongo import MongoClient
import datetime

# 1. SETUP CONNECTIONS
# Cloudinary credentials configuration
CLOUDINARY_URL = os.environ.get('CLOUDINARY_URL')
if CLOUDINARY_URL:
    cloudinary.config(cloudinary_url=CLOUDINARY_URL)
    print("cloudi... con...estblsh..")


# MongoDB connection initialization
client = MongoClient(st.secrets["MONGODB_URI"])
db = client["my_blog_database"]
posts_collection = db["blog_posts"]

# 2. STREAMLIT UI DESIGN
st.title("📝 Simple Blog Post Creator")
st.write("Write an article, add a picture, and publish it instantly.")

# Create the input fields for the blog post
title = st.text_input("Blog Post Title", placeholder="e.g., Cloudinary vs. Database")
content = st.text_area("Write your blog post here...", height=200)
uploaded_file = st.file_uploader("Upload a Cover Photo", type=["png", "jpg", "jpeg"])

# 3. SUBMIT & UPLOAD WORKFLOW
if st.button("🚀 Publish Blog Post"):
    if not title or not content:
        st.error("Please fill in both the title and the content fields!")
    elif not uploaded_file:
        st.error("Please upload a cover photo for your blog post!")
    else:
        with st.spinner("Processing..."):
            try:
                # ─── STEP 1 & 2: UPLOAD IMAGE TO CLOUDINARY & GET THE TEXT URL ───
                # We read the raw file bytes directly from Streamlit's file uploader
                file_bytes = uploaded_file.read()
                
                upload_result = cloudinary.uploader.upload(
                    file_bytes,
                    folder = "blog_covers",
                    transformation = [
                        {"width": 800, "height": 450, "crop": "fill"}, # Auto-crop to 16:9 banner
                        {"quality": "auto"},                          # Auto-compress size
                        {"fetch_format": "auto"}                       # Auto-convert to modern WebP/AVIF
                    ]
                )
                
                # Extract the lightweight text URL string returned by Cloudinary
                optimized_image_url = upload_result.get("secure_url")

                # ─── STEP 3: STORE ONLY THE TEXT REFERENCE IN MONGODB ───
                # Create the clean text record document
                blog_document = {
                    "title": title,
                    "content": content,
                    "cover_image_url": optimized_image_url,  # Tiny text string stored instead of a massive BLOB
                    "published_at": datetime.datetime.utcnow()
                }
                
                # Insert the text document straight into the database cluster
                posts_collection.insert_one(blog_document)
                
                st.success("🎉 Post successfully published!")
                st.balloons()
                
            except Exception as e:
                st.error(f"An unexpected error occurred: {e}")

# 4. LIVE FEED PREVIEW (DISPLAYING THE DATA)
st.markdown("---")
st.subheader("📰 Live Blog Feed")

# Fetch all saved documents from MongoDB, ordered by latest date
all_posts = posts_collection.find().sort("published_at", -1)

for post in all_posts:
    with st.container():
        # Display the image using the lightweight string URL fetched from MongoDB
        if "cover_image_url" in post:
            st.image(post["cover_image_url"], use_container_width=True)
        
        st.title(post["title"])
        st.caption(f"Published on: {post['published_at'].strftime('%B %d, %Y')}")
        st.write(post["content"])
        st.markdown("---")
