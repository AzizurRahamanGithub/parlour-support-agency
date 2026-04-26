from unfold.admin import ModelAdmin as UnfoldModelAdmin
from django.utils.html import format_html
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import SocialMedia, CustomUser, ContactMessage

from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _
from .forms import MultipleImagesForm 


# ── Dynamic Multi-Image Form Factory ────────────────────────────────
def make_multi_image_form(model, field_name, folder):
    """প্রতিটা JSON image field-এর জন্য আলাদা form তৈরি করে"""

    class _Form(MultipleImagesForm):
        image_folder = folder

        class Meta(MultipleImagesForm.Meta):
            model_class = model
            fields = "__all__"

        def __init__(self, *args, **kwargs):
            super(MultipleImagesForm, self).__init__(*args, **kwargs)
            images = getattr(self.instance, field_name, []) or []

            from django.utils.safestring import mark_safe
            from apps.file_uploader.forms import MultiFileField, MultiFileInput

            self.fields["upload_images"] = MultiFileField(
                required=False,
                widget=MultiFileInput(),
                help_text=mark_safe(f"<b>Upload new images</b><br><small>Allowed: JPG, PNG, WEBP</small>")
            )

            if images:
                preview_html = f"""
                <div style="margin-top:20px; border:1px solid #e5e7eb; border-radius:10px;
                            background:#fafafa; padding:15px; box-shadow:0 1px 3px rgba(0,0,0,0.05);">
                    <div style="font-weight:600; margin-bottom:12px; color:#333;
                                display:flex; justify-content:space-between; align-items:center;">
                        <span>Current Images ({len(images)})</span>
                        <span style="font-size:12px; font-weight:normal; color:#666;">✓ Select to delete</span>
                    </div>
                    <div style="display:flex; flex-wrap:wrap; gap:15px; align-items:flex-start;">
                """
                for url in images:
                    preview_html += f"""
                        <div style="flex:0 0 auto; border:1px solid #e5e7eb; border-radius:8px;
                                    background:white; padding:10px; text-align:center;">
                            <label style="display:flex; flex-direction:column; align-items:center; gap:8px; cursor:pointer;">
                                <div style="display:flex; align-items:center; gap:6px; padding:4px 8px;
                                            border-radius:4px; background:#fff5f5;">
                                    <input type="checkbox" name="delete_{field_name}" value="{url}"
                                        style="accent-color:#d32f2f; transform:scale(1.2); cursor:pointer;">
                                    <span style="font-size:12px; color:#d32f2f; font-weight:500;">Delete</span>
                                </div>
                                <img src="{url}"
                                    style="max-height:100px; max-width:150px; border-radius:6px;
                                           border:1px solid #ddd; cursor:pointer; object-fit:contain;"
                                    onclick="openImageModal(this.src)"
                                    title="Click to enlarge">
                            </label>
                        </div>
                    """
                preview_html += """
                    </div>
                    <div style="margin-top:12px; font-size:12px; color:#666; padding:8px;
                                background:#f0f9ff; border-radius:4px; border-left:3px solid #3b82f6;">
                        💡 Delete checkbox select করে Save করুন
                    </div>
                </div>
                <div id="imageModal" style="display:none; position:fixed; top:0; left:0;
                    width:100%; height:100%; backdrop-filter:blur(8px);
                    background:rgba(0,0,0,0.4); justify-content:center;
                    align-items:center; z-index:9999;" onclick="this.style.display='none'">
                    <img id="modalImg" style="max-width:90%; max-height:90%;
                        border-radius:10px; box-shadow:0 4px 12px rgba(0,0,0,0.5); object-fit:contain;">
                </div>
                <script>
                function openImageModal(src) {{
                    const modal = document.getElementById('imageModal');
                    document.getElementById('modalImg').src = src;
                    modal.style.display = 'flex';
                    document.addEventListener('keydown', e => {{ if(e.key==='Escape') modal.style.display='none'; }});
                }}
                </script>
                """
                self.fields["upload_images"].help_text = mark_safe(
                    str(self.fields["upload_images"].help_text) + preview_html
                )

        def save(self, commit=True):
            instance = super(MultipleImagesForm, self).save(commit=False)

            # Delete selected
            to_delete = self.data.getlist(f"delete_{field_name}") or []
            if to_delete:
                from apps.file_uploader.upload_utils import delete_file_from_digital_ocean
                for url in to_delete:
                    try:
                        delete_file_from_digital_ocean(url)
                    except Exception:
                        pass
                current = getattr(instance, field_name, []) or []
                setattr(instance, field_name, [u for u in current if u not in to_delete])

            # Upload new
            from apps.file_uploader.upload_utils import upload_file_to_digital_ocean
            new_files = self.cleaned_data.get("upload_images") or []
            all_urls = list(getattr(instance, field_name, []) or [])
            for f in new_files:
                if f:
                    url = upload_file_to_digital_ocean(f, folder=self.image_folder)
                    all_urls.append(url)
            setattr(instance, field_name, list(dict.fromkeys(all_urls)))

            if commit:
                instance.save()
            return instance

    _Form.__name__ = f"{field_name}_Form"
    return _Form



class SocialMediaInline(admin.TabularInline):
    model = SocialMedia
    extra = 1
    fields = ['platform', 'username', 'url']


# ── CustomUser Admin ─────────────────────────────────────────────────
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
        inlines = [SocialMediaInline]
        model = CustomUser

        list_display = (
            'email', 'full_name', 'phone_number', 'designation',
            'category', 'current_plan',
            'is_active', 'approval_status'
        )
        list_filter = ('is_active', 'is_staff', 'is_superuser', 'category', 'designation')
        search_fields = ('email', 'username', 'full_name', 'phone_number')
        ordering = ('-created_at',)
        actions = ['approve_users', 'deactivate_users']

        readonly_fields = (
                'created_at', 'last_login', 'date_joined',
                'upload_images_profile',   
                'upload_images_licence',   
                'upload_images_id',        
                'upload_images_id_with',   
            )

        fieldsets = (
            ('🔐 Login Info', {
                'fields': ('email', 'username', 'password')
            }),
            ('👤 Personal Info', {
                'fields': (
                    'full_name', 'phone_number', 'address',
                    'designation', 'category', 'current_plan'
                )
            }),
            ('📤 Upload New Images', {
                    'fields': ('image', 'licence_image', 'id_image', 'id_with_image'),
                }),
                ('🖼️ Profile Image Preview', {
                    'fields': ('upload_images_profile',),
                }),
                ('📄 Licence Image Preview', {
                    'fields': ('upload_images_licence',),
                }),
                ('🪪 ID Image Preview', {
                    'fields': ('upload_images_id',),
                }),
                ('🤳 ID With Face Preview', {
                    'fields': ('upload_images_id_with',),
}),
            ('✅ Permissions', {
                'fields': (
                    'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'
                )
            }),
            ('📅 Timestamps', {
                'fields': ('created_at', 'last_login', 'date_joined'),
                'classes': ('collapse',)
            }),
        )

        add_fieldsets = (
            (None, {
                'classes': ('wide',),
                'fields': (
                    'email', 'username', 'full_name', 'password1', 'password2',
                    'phone_number', 'category', 'is_active'
                )
            }),
        )

        @admin.display(description='🖼️ Profile Image')
        def upload_images_profile(self, obj):
            return self._build_preview_html(obj, 'image', 'image')

        @admin.display(description='📄 Licence Image')
        def upload_images_licence(self, obj):
            return self._build_preview_html(obj, 'licence_image', 'licence_image')

        @admin.display(description='🪪 ID Image')
        def upload_images_id(self, obj):
            return self._build_preview_html(obj, 'id_image', 'id_image')

        @admin.display(description='🤳 ID With Face')
        def upload_images_id_with(self, obj):
            return self._build_preview_html(obj, 'id_with_image', 'id_with_image')
        
        
        def get_form(self, request, obj=None, **kwargs):
            return super().get_form(request, obj, **kwargs)

        def _build_preview_html(self, obj, field_name, delete_key):
            from django.utils.safestring import mark_safe
            images = getattr(obj, field_name, []) or []
            if not images:
                return mark_safe("<small style='color:#999;'>No images yet</small>")

            html = f"""
            <div style="margin-top:10px; border:1px solid #e5e7eb; border-radius:10px;
                        background:#fafafa; padding:15px;">
                <div style="font-weight:600; margin-bottom:10px; color:#333;">
                    Current Images ({len(images)})
                </div>
                <div style="display:flex; flex-wrap:wrap; gap:12px;">
            """
            for url in images:
                html += f"""
                <div style="border:1px solid #e5e7eb; border-radius:8px; background:white; padding:8px; text-align:center;">
                    <label style="display:flex; flex-direction:column; align-items:center; gap:6px; cursor:pointer;">
                        <div style="display:flex; align-items:center; gap:4px; padding:3px 8px;
                                    border-radius:4px; background:#fff5f5;">
                            <input type="checkbox" name="delete_{delete_key}" value="{url}"
                                style="accent-color:#d32f2f; cursor:pointer;">
                            <span style="font-size:12px; color:#d32f2f;">Delete</span>
                        </div>
                        <img src="{url}"
                            style="max-height:90px; max-width:130px; border-radius:6px;
                                border:1px solid #ddd; cursor:pointer; object-fit:contain;"
                            onclick="openImageModal(this.src)" title="Click to enlarge">
                    </label>
                </div>
                """
            html += """
                </div>
            </div>
            <div id="imageModal" onclick="this.style.display='none'"
                style="display:none; position:fixed; top:0; left:0; width:100%; height:100%;
                    backdrop-filter:blur(8px); background:rgba(0,0,0,0.5);
                    justify-content:center; align-items:center; z-index:9999;">
                <img id="modalImg" style="max-width:90%; max-height:90%; border-radius:10px;
                    box-shadow:0 4px 20px rgba(0,0,0,0.6);">
            </div>
            <script>
            function openImageModal(src) {{
                document.getElementById('modalImg').src = src;
                document.getElementById('imageModal').style.display = 'flex';
            }}
            document.addEventListener('keydown', e => {{
                if(e.key === 'Escape') document.getElementById('imageModal').style.display = 'none';
            }});
            </script>
            """
            return mark_safe(html)

        def save_model(self, request, obj, form, change):
            """Upload + delete image fields handle করো"""
            from apps.file_uploader.upload_utils import upload_file_to_digital_ocean, delete_file_from_digital_ocean

            image_fields = {
                'upload_images_profile': ('image', 'user-profile'),
                'upload_images_licence': ('licence_image', 'user-licence'),
                'upload_images_id': ('id_image', 'user-id'),
                'upload_images_id_with': ('id_with_image', 'user-id-with-face'),
            }

            for field_key, (model_field, folder) in image_fields.items():
                # Delete selected
                to_delete = request.POST.getlist(f"delete_{model_field}")
                if to_delete:
                    for url in to_delete:
                        try:
                            delete_file_from_digital_ocean(url)
                        except Exception:
                            pass
                    current = getattr(obj, model_field, []) or []
                    setattr(obj, model_field, [u for u in current if u not in to_delete])

                # Upload new files
                new_files = request.FILES.getlist(field_key)
                if new_files:
                    all_urls = list(getattr(obj, model_field, []) or [])
                    for f in new_files:
                        url = upload_file_to_digital_ocean(f, folder=folder)
                        all_urls.append(url)
                    setattr(obj, model_field, list(dict.fromkeys(all_urls)))

            super().save_model(request, obj, form, change)

        # ── Approval ─────────────────────────────────────────────────────

        @admin.display(description='Approval')
        def approval_status(self, obj):
            if obj.is_active:
                return format_html('<span style="color:green; font-weight:bold;">✅ Approved</span>')
            return format_html('<span style="color:orange; font-weight:bold;">⏳ Pending</span>')

        @admin.action(description='✅ Approve selected users')
        def approve_users(self, request, queryset):
            updated = queryset.update(is_active=True)
            self.message_user(request, f"{updated} user(s) approved successfully.")

        @admin.action(description='🚫 Deactivate selected users')
        def deactivate_users(self, request, queryset):
            updated = queryset.update(is_active=False)
            self.message_user(request, f"{updated} user(s) deactivated.")

        # ── Custom URLs ──────────────────────────────────────────────────

        def get_urls(self):
            urls = super().get_urls()
            custom_urls = [
                path("admins/", self.admin_site.admin_view(self.view_admins), name="customuser_admins"),
                path("staff/", self.admin_site.admin_view(self.view_staff), name="customuser_staff"),
                path("users/", self.admin_site.admin_view(self.view_users), name="customuser_users"),
            ]
            return custom_urls + urls

        def view_admins(self, request):
            qs = self.model.objects.filter(is_superuser=True)
            return render(request, "customuser_list.html", dict(
                self.admin_site.each_context(request), title=_("Admin Users"), users=qs, section="Admins",
            ))

        def view_staff(self, request):
            qs = self.model.objects.filter(is_staff=True, is_superuser=False)
            return render(request, "customuser_list.html", dict(
                self.admin_site.each_context(request), title=_("Staff Members"), users=qs, section="Staff",
            ))

        def view_users(self, request):
            qs = self.model.objects.filter(is_staff=False, is_superuser=False)
            return render(request, "customuser_list.html", dict(
                self.admin_site.each_context(request), title=_("Regular Users"), users=qs, section="Users",
            ))



@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ("full_name", "email", "subject", "created_at")
    search_fields = ("full_name", "email", "subject", "message")
    list_filter = ("created_at",)
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)
    list_per_page = 25

    class Meta:
        verbose_name = "Contact Message"
        verbose_name_plural = "User Contact Messages"




