from django import forms
from apps.file_uploader.upload_utils import upload_file_to_digital_ocean, delete_file_from_digital_ocean
from django.utils.safestring import mark_safe


# -----------------------------
# Single Image Form
# -----------------------------
class SingleImageForm(forms.ModelForm):
    upload_image = forms.FileField(
        required=False,
        help_text=mark_safe("<b>Upload new image</b><br><small>Allowed formats: JPG, PNG, WEBP</small>")
    )
    delete_image = forms.ChoiceField(
        required=False,
        widget=forms.RadioSelect,
        choices=[],
        help_text="Select image to delete"
    )
    image_folder = "uploads"  # override dynamically in admin

    class Meta:
        model = None
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        image_url = getattr(self.instance, "image", None)

        # --- Beautified Preview Section ---
        if image_url:
            preview_html = f"""
            <div style="
                margin-top: 20px; 
                border: 1px solid #e5e7eb; 
                border-radius: 10px; 
                background: #fafafa; 
                padding: 15px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            ">
                <div style="font-weight:600; margin-bottom:8px; color:#333;">
                    Current Image Preview
                </div>
                <div style="display:flex; align-items:center; gap:15px;">
                    <div style='flex-shrink:0;'>
                        <label style="display:flex; align-items:center; gap:6px; cursor:pointer;">
                            <input type="radio" name="delete_image" value="{image_url}" 
                                style="accent-color:#d32f2f; transform:scale(1.2); cursor:pointer;">
                            <span style="font-size:13px; color:#d32f2f;">Delete this image</span>
                        </label>
                    </div>
                    <div style='flex-grow:1;'>
                        <img src="{image_url}" 
                            style="max-height:120px; border-radius:8px; border:1px solid #ccc; 
                                    padding:3px; background:#fff; cursor:pointer; transition:transform .2s ease;"
                            onclick="openImageModal(this.src)"
                            onmouseover="this.style.transform='scale(1.05)'" 
                            onmouseout="this.style.transform='scale(1)'">
                    </div>
                </div>
            </div>

            <!-- Modal HTML -->
            <div id="imageModal" style="
                display:none;
                position:fixed;
                top:0; left:0;
                width:100%; height:100%;
                backdrop-filter:blur(8px);
                background: rgba(0,0,0,0.4);
                justify-content:center;
                align-items:center;
                z-index:9999;
            " onclick="this.style.display='none'">
                <img id="modalImg" style="
                    max-width:90%; max-height:90%; 
                    border-radius:10px; 
                    box-shadow:0 4px 12px rgba(0,0,0,0.5);
                ">
            </div>

            <script>
            function openImageModal(src) {{
                const modal = document.getElementById('imageModal');
                const modalImg = document.getElementById('modalImg');
                modalImg.src = src;
                modal.style.display = 'flex';
            }}
            </script>
            """
            self.fields["upload_image"].help_text = mark_safe(
                (self.fields["upload_image"].help_text or "") + preview_html
            )

    def save(self, commit=True):
        instance = super().save(commit=False)
        to_delete = self.data.get("delete_image")

        # --- Delete selected image ---
        if to_delete:
            try:
                delete_file_from_digital_ocean(to_delete)
            except Exception:
                pass
            instance.image = None

        # --- Upload new image ---
        file = self.cleaned_data.get("upload_image")
        if file:
            # delete old one if exists
            if getattr(instance, "image", None):
                try:
                    delete_file_from_digital_ocean(instance.image)
                except Exception:
                    pass
            instance.image = upload_file_to_digital_ocean(file, folder=self.image_folder)

        if commit:
            instance.save()
        return instance
    
    
# -----------------------------
# Multi file input
# -----------------------------
class MultiFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultiFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultiFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            return [single_file_clean(d, initial) for d in data]
        return single_file_clean(data, initial)

# -----------------------------
# Multiple Images Form (Simplified - no separate delete field)
# -----------------------------
class MultipleImagesForm(forms.ModelForm):
    upload_images = MultiFileField(
        required=False,
        help_text=mark_safe("<b>Upload new images</b><br><small>Allowed formats: JPG, PNG, WEBP</small>")
    )
    # delete_images field removed - now handled in preview
    image_folder = "uploads"

    class Meta:
        model = None  # set in child
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        images = getattr(self.instance, "images", []) or []

        # --- Beautiful Preview Section for Multiple Images ---
        if images:
            preview_html = f"""
            <div style="
                margin-top: 20px; 
                border: 1px solid #e5e7eb; 
                border-radius: 10px; 
                background: #fafafa; 
                padding: 15px;
                box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            ">
                <div style="font-weight:600; margin-bottom:12px; color:#333; display: flex; justify-content: space-between; align-items: center;">
                    <span>Current Images Preview ({len(images)} images)</span>
                    <span style="font-size:12px; font-weight:normal; color:#666;">✓ Select images to delete</span>
                </div>
                <div style="display: flex; flex-wrap: wrap; gap: 15px; align-items: flex-start;">
            """
            
            for i, url in enumerate(images):
                img_html = f"""
                    <div style="
                        flex: 0 0 auto;
                        border: 1px solid #e5e7eb;
                        border-radius: 8px;
                        background: white;
                        padding: 10px;
                        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
                        text-align: center;
                        transition: all 0.2s ease;
                    " onmouseover="this.style.borderColor='#d32f2f'" onmouseout="this.style.borderColor='#e5e7eb'">
                        <label style="display: flex; flex-direction: column; align-items: center; gap: 8px; cursor: pointer;">
                            <div style="display: flex; align-items: center; gap: 6px; padding: 4px 8px; border-radius: 4px; background: #fff5f5;">
                                <input type="checkbox" name="delete_images" value="{url}" 
                                    style="accent-color:#d32f2f; transform:scale(1.2); cursor:pointer;">
                                <span style="font-size:12px; color:#d32f2f; font-weight:500;">Delete</span>
                            </div>
                            <img src="{url}" 
                                style="max-height: 100px; max-width: 150px; border-radius:6px; border:1px solid #ddd; 
                                        padding:2px; cursor:pointer; transition:transform .2s ease; object-fit: contain;"
                                onclick="openImageModal(this.src)"
                                onmouseover="this.style.transform='scale(1.03)'" 
                                onmouseout="this.style.transform='scale(1)'"
                                title="Click to enlarge">
                        </label>
                    </div>
                """
                preview_html += img_html

            preview_html += """
                </div>
                <div style="margin-top: 12px; font-size: 12px; color: #666; padding: 8px; background: #f0f9ff; border-radius: 4px; border-left: 3px solid #3b82f6;">
                    💡 Select the "Delete" checkboxes to remove images, then click Save to confirm deletion
                </div>
            </div>
            """

            # --- Modal HTML & JS ---
            modal_html = """
            <!-- Modal HTML -->
            <div id="imageModal" style="
                display:none;
                position:fixed;
                top:0; left:0;
                width:100%; height:100%;
                backdrop-filter:blur(8px);
                background: rgba(0,0,0,0.4);
                justify-content:center;
                align-items:center;
                z-index:9999;
            " onclick="this.style.display='none'">
                <img id="modalImg" style="
                    max-width:90%; max-height:90%; 
                    border-radius:10px; 
                    box-shadow:0 4px 12px rgba(0,0,0,0.5);
                    object-fit: contain;
                ">
            </div>

            <script>
            function openImageModal(src) {
                const modal = document.getElementById('imageModal');
                const modalImg = document.getElementById('modalImg');
                modalImg.src = src;
                modal.style.display = 'flex';
                
                // Close modal on ESC key
                document.addEventListener('keydown', function(e) {
                    if (e.key === 'Escape') {
                        modal.style.display = 'none';
                    }
                });
            }
            </script>
            """

            # Attach preview to upload_images help_text
            self.fields["upload_images"].help_text = mark_safe(
                (self.fields["upload_images"].help_text or "") + preview_html + modal_html
            )

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Delete selected images - now from the checkboxes in preview
        to_delete = self.data.getlist("delete_images") or []  # Use getlist for multiple values
        
        if to_delete:
            for url in to_delete:
                try:
                    delete_file_from_digital_ocean(url)
                except Exception:
                    pass
            # Remove deleted images from the instance
            current_images = getattr(instance, "images", []) or []
            instance.images = [url for url in current_images if url not in to_delete]

        # Upload new images
        new_files = self.cleaned_data.get("upload_images") or []
        all_urls = list(getattr(instance, "images", []) or [])
        for f in new_files:
            if f:
                url = upload_file_to_digital_ocean(f, folder=self.image_folder)
                all_urls.append(url)

        instance.images = list(dict.fromkeys(all_urls))  # unique urls

        if commit:
            instance.save()
        return instance