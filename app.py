
import uuid

import streamlit as st
from supabase import create_client

st.set_page_config(
    page_title="My Stylist AI",
    page_icon="👗",
    layout="centered",
)

# Personal-use access gate
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("👗 My Stylist AI")
    password = st.text_input("Enter your private app password",
                             type="password")

    if st.button("Unlock my wardrobe"):
        if password == st.secrets["APP_PASSWORD"]:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Incorrect password")

    st.stop()

# Server-side database client
@st.cache_resource
def get_supabase():
    return create_client(
        st.secrets["SUPABASE_URL"],
        st.secrets["SUPABASE_SERVICE_ROLE_KEY"],
    )

supabase = get_supabase()
BUCKET = "wadrobe-images"

st.title("👗 My Stylist AI")
st.caption("Your personal wardrobe assistant")

closet_tab, outfit_tab, profile_tab = st.tabs(
    ["My Closet", "Outfit Builder", "My Fit Profile"]
)

def get_items():
    result = (
        supabase.table("wardrobe_items")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )
    return result.data or []

with closet_tab:
    st.subheader("Add a clothing item")

    photo = st.file_uploader(
        "Choose a clothing photo",
        type=["jpg", "jpeg", "png", "webp"],
    )

    category = st.selectbox(
        "Category",
        ["Top", "Bottom", "Dress", "Shoes", "Accessory"],
    )
    color = st.text_input("Main color")
    garment_length = st.selectbox(
        "Length",
        ["Unknown", "Cropped", "Waist", "Hip", "Knee",
         "Midi", "Maxi", "Full length"],
    )
    fit = st.selectbox(
        "Fit",
        ["Unknown", "Fitted", "Regular", "Relaxed", "Oversized"],
    )
    notes = st.text_input("Notes (optional)")

    if st.button("Save to My Closet", type="primary"):
        if not photo:
            st.warning("Please select a photo first.")
        else:
            try:
                image_bytes = photo.getvalue()
                path = f"{uuid.uuid4().hex}_{photo.name}"

                supabase.storage.from_(BUCKET).upload(
                    path,
                    image_bytes,
                    file_options={
                        "content-type": photo.type,
                        "upsert": "false",
                    },
                )

                supabase.table("wardrobe_items").insert({
                    "category": category,
                    "color": color.strip(),
                    "garment_length": garment_length,
                    "fit": fit,
                    "notes": notes.strip(),
                    "image_path": path,
                }).execute()

                st.success("Clothing item saved!")
                st.rerun()

            except Exception as error:
                st.error(
                    "Couldn't save the item. Check your "
                    "Supabase settings and try again."
                )
                st.exception(error)

    st.divider()
    st.subheader("My saved clothes")

    try:
        items = get_items()

        if not items:
            st.info("Your closet is empty. Upload your first item.")

        for item in items:
            with st.container(border=True):
                st.write(
                    f"**{item['category']}** · "
                    f"{item.get('color') or 'Color not specified'}"
                )
                st.caption(
                    f"Length: {item.get('garment_length') or 'Unknown'}"
                    f" · Fit: {item.get('fit') or 'Unknown'}"
                )

                try:
                    image_info = (
                        supabase.storage.from_(BUCKET)
                        .create_signed_url(item["image_path"], 3600)
                    )
                    image_url = (
                        image_info.get("signedURL")
                        or image_info.get("signedUrl")
                    )
                    if image_url:
                        st.image(image_url, width=220)
                except Exception:
                    st.caption("Image preview unavailable.")

    except Exception:
        st.error("Couldn't load your wardrobe. Check the database setup.")

with outfit_tab:
    st.subheader("Build an outfit from your clothes")

    try:
        items = get_items()
        tops = [x for x in items if x["category"] == "Top"]
        bottoms = [x for x in items if x["category"] == "Bottom"]
        dresses = [x for x in items if x["category"] == "Dress"]

        if not items:
            st.info("Add clothes to My Closet first.")
        else:
            request = st.text_input(
                "What are you dressing for?",
                placeholder="Casual day, work, art gallery...",
            )

            choices = []
            if tops and bottoms:
                choices.append("Top + Bottom")
            if dresses:
                choices.append("Dress")
            if not choices:
                st.info("Add a top and bottom, or a dress, to build outfits.")
            else:
                outfit_type = st.radio("Choose outfit type", choices)

                if outfit_type == "Top + Bottom":
                    top = st.selectbox(
                        "Choose a top", tops,
                        format_func=lambda x:
                        f"{x.get('color') or 'Unspecified'} top — {x['id'][:8]}",
                    )
                    bottom = st.selectbox(
                        "Choose a bottom", bottoms,
                        format_func=lambda x:
                        f"{x.get('color') or 'Unspecified'} bottom — {x['id'][:8]}",
                    )
                    selected = [top, bottom]
                else:
                    dress = st.selectbox(
                        "Choose a dress", dresses,
                        format_func=lambda x:
                        f"{x.get('color') or 'Unspecified'} dress — {x['id'][:8]}",
                    )
                    selected = [dress]

                if st.button("Show my outfit"):
                    st.subheader("Your selected outfit")
                    if request:
                        st.write(f"Occasion: {request}")

                    columns = st.columns(len(selected))
                    for col, item in zip(columns, selected):
                        with col:
                            st.write(item["category"])
                            st.write(item.get("color") or "Color unspecified")
                            try:
                                info = (
                                    supabase.storage.from_(BUCKET)
                                    .create_signed_url(
                                        item["image_path"], 3600
                                    )
                                )
                                url = info.get("signedURL") or info.get("signedUrl")
                                if url:
                                    st.image(url, use_container_width=True)
                            except Exception:
                                pass

                    st.info(
                        "This first version lets you combine your actual "
                        "items. Automatic matching and AI styling are "
                        "the next milestone."
                    )

    except Exception:
        st.error("Couldn't load items for outfit building.")

with profile_tab:
    st.subheader("My Fit Profile")
    st.write(
        "We will add persistent profile settings in the next milestone."
    )
    height = st.text_input("Height (optional)", placeholder="e.g. 5 ft 3 in")
    preferences = st.text_area(
        "Styling preferences",
        placeholder="Preferred lengths, colors, fits and occasions...",
    )
    st.caption(
        "These fields are not saved yet. We'll connect them to the "
        "database in the next milestone."
    )

if st.button("Lock my wardrobe"):
    st.session_state.authenticated = False
    st.rerun()
