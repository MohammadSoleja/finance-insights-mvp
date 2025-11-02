Lottie upload folder

Place your .lottie packages (or exported .json files) in this folder so I can extract and integrate them into the site.

Preferred filenames (helps automation):
- hero-analytics.lottie    -> main hero animation
- upload-icon.lottie      -> small upload animation for feature card
- insight-icon.lottie     -> small chart/insight animation for feature card
- security-icon.lottie    -> small security/lock animation for feature card

What I'll do after you upload:
1. Extract each .lottie package and list contained animation JSON(s).
2. Copy the chosen animation JSON(s) to:
   app_web/static/app_web/assets/lottie/<friendly-name>.json
   and any images to:
   app_web/static/app_web/assets/lottie/images/
3. Patch JSON "assets" base paths so Lottie can load embedded images from the static path.
4. Integrate into `app_web/templates/app_web/home.html` (hero + feature icons) using the lottie-player web component, with reduced-motion and static fallbacks.
5. Test locally (Django checks + quick smoke test) and report back.

How to upload files:
- Option A (recommended): Use your IDE / file manager and copy the .lottie files into this folder.
- Option B: Attach the .lottie files in this chat (if your client supports attachments) and tell me when done.

Local copy example (macOS / zsh) if you have files on desktop:

```bash
mkdir -p app_web/static/app_web/assets/lottie
cp ~/Desktop/hero-analytics.lottie app_web/static/app_web/assets/lottie/
cp ~/Desktop/upload-icon.lottie app_web/static/app_web/assets/lottie/
# repeat for the other files
```

When you're done uploading, reply here with "extract and integrate" and I'll extract the files, integrate them, and run quick checks. If you'd rather I only extract and list the contained animations first (so you can confirm which JSON to use), reply with "extract and list".

