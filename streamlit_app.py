import os
import streamlit as st
import cloudinary
import cloudinary.uploader
from pymongo import MongoClient
from bson.objectid import ObjectId
import datetime

# 1. SETUP CONNECTIONS
CLOUDINARY_URL = os.environ.get('CLOUDINARY_URL')
if CLOUDINARY_URL:
    cloudinary.config(cloudinary_url=CLOUDINARY_URL)
    print("cloudi... con...estblsh..")


client = MongoClient(st.secrets["MONGODB_URI"])
db = client["my_blog_database"]
posts_collection = db["blog_posts"]

# 2. STATE MANAGEMENT FOR EDITING
if "edit_post_id" not in st.session_state:
    st.session_state.edit_post_id = None

# 3. INTERACTIVE FORMS (CREATE OR UPDATE)
st.title("📝 Simple Blog Post Dashboard")

if st.session_state.edit_post_id:
    # --- EDITING EXISTING POST MODE ---
    st.info("🔄 You are currently editing an existing post.")
    
    # Fetch current data from MongoDB to pre-fill the form fields
    current_post = posts_collection.find_one({"_id": ObjectId(st.session_state.edit_post_id)})
    
    edit_title = st.text_input("Modify Title", value=current_post["title"])
    edit_content = st.text_area("Modify Content", value=current_post["content"], height=150)
    edit_file = st.file_uploader("Replace Cover Photo (Optional)", type=["png", "jpg", "jpeg"])
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("💾 Save Updates", type="primary"):
            with st.spinner("Updating record..."):
                update_fields = {"title": edit_title, "content": edit_content}
                
                # Only replace image in Cloudinary if a new file is uploaded
                if edit_file:
                    upload_result = cloudinary.uploader.upload(
                        edit_file.read(),
                        folder="blog_covers",
                        transformation=[{"width": 800, "height": 450, "crop": "fill"}, {"quality": "auto"}]
                    )
                    update_fields["cover_image_url"] = upload_result.get("secure_url")
                
                posts_collection.update_one({"_id": ObjectId(st.session_state.edit_post_id)}, {"$set": update_fields})
                st.session_state.edit_post_id = None  # Clear edit state
                st.rerun()
                
    with col2:
        if st.button("❌ Cancel Edit"):
            st.session_state.edit_post_id = None
            st.rerun()
else:
    # --- CREATE NEW POST MODE ---
    st.write("Write an article, add a picture, and publish it instantly.")
    title = st.text_input("Blog Post Title", placeholder="e.g., Cloudinary vs. Database")
    content = st.text_area("Write your blog post here...", height=150)
    uploaded_file = st.file_uploader("Upload a Cover Photo", type=["png", "jpg", "jpeg"])

    if st.button("🚀 Publish Blog Post", type="primary"):
        if not title or not content or not uploaded_file:
            st.error("Please fill in all input fields and upload a cover photo!")
        else:
            with st.spinner("Publishing..."):
                upload_result = cloudinary.uploader.upload(
                    uploaded_file.read(),
                    folder="blog_covers",
                    transformation=[{"width": 800, "height": 450, "crop": "fill"}, {"quality": "auto"}]
                )
                
                blog_document = {
                    "title": title,
                    "content": content,
                    "cover_image_url": upload_result.get("secure_url"),
                    "published_at": datetime.datetime.utcnow()
                }
                posts_collection.insert_one(blog_document)
                st.success("🎉 Post published!")
                st.rerun()

# 4. LIVE FEED PREVIEW (WITH MODIFY & DELETE ACTIONS)
st.markdown("---")
st.subheader("📰 Live Blog Feed")

# Fetch all saved documents from MongoDB, ordered by latest date
all_posts = list(posts_collection.find().sort("published_at", -1))

if not all_posts:
    st.info("No blog posts found. Create your first post above!")

for post in all_posts:
    post_id_str = str(post["_id"])
    
    with st.container(border=True):
        if "cover_image_url" in post:
            st.image(post["cover_image_url"], use_container_width=True)
        
        st.subheader(post["title"])
        st.caption(f"Published on: {post['published_at'].strftime('%B %d, %Y')}")
        st.write(post["content"])
        
        # Action Row Buttons Layout
        btn_col1, btn_col2, _ = st.columns([1, 1, 4])
        
        with btn_col1:
            # Modify Button (Triggers edit form layout above)
            if st.button("✏️ Modify", key=f"mod_{post_id_str}"):
                st.session_state.edit_post_id = post_id_str
                st.rerun()
                
        with btn_col2:
            # Delete Button (Removes record from database cluster directly)
            if st.button("🗑️ Delete", key=f"del_{post_id_str}", type="secondary"):
                posts_collection.delete_one({"_id": ObjectId(post["_id"])})
                st.toast(f"Deleted: {post['title']}")
                st.rerun()
