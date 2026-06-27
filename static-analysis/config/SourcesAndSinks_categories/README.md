# SourcesAndSinks category profiles

Each file is self-contained and can be passed to FlowDroid as the source/sink file.

Use these files for first-pass, category-specific analysis. They intentionally keep broad sources commented out. For business-only categories such as finance, education, career, religion, and special identity, inspect the APK with JADX and add app-specific getter/callback/model methods as sources.

Suggested workflow:
1. Start with 05_device_identifiers, 07_location, 09_image_audio_video, 21_social_relationships, and 22_communication_content.
2. If a privacy policy mentions a business category, open the matching category file and add app-specific sources found in JADX.
3. Uncomment TextView/EditText sources only for focused manual checks, because they can taint nearly all user input.
