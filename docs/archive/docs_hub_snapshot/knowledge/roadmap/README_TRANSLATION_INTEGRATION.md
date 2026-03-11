# Issue & Comment Translation Integration

## Overview

This repository includes an automated GitHub Actions workflow that translates new or edited issues and issue comments into German. The integration helps make project discussions accessible to German-speaking contributors and maintainers.

## How It Works

1. **Trigger**: The workflow runs automatically when:
   - A new issue is created
   - An existing issue is edited
   - A comment is added to an issue
   - An existing comment is edited

2. **Translation Process**:
   - The workflow reads the issue or comment body text
   - Translates it to German using:
     - **LibreTranslate** (free, public instance) by default
     - **DeepL** (if API key is configured) for higher quality translations
   - Posts or updates a bot comment with the translation
   - Marks translations with the prefix `[Übersetzung — DE]`

3. **Idempotency**: If a translation comment already exists, the workflow updates it instead of creating duplicate comments.

## Setup

### Basic Setup (No Configuration Required)

The workflow is ready to use immediately with LibreTranslate as the translation provider. No secrets or configuration are needed for basic functionality.

### Enhanced Setup (Optional DeepL Integration)

For higher-quality translations, you can configure DeepL:

1. **Get a DeepL API Key**:
   - Sign up for a free DeepL API account at [https://www.deepl.com/pro-api](https://www.deepl.com/pro-api)
   - The free tier includes 500,000 characters/month

2. **Add the Secret to Your Repository**:
   - Go to your repository's Settings → Secrets and variables → Actions
   - Click "New repository secret"
   - Name: `DEEPL_API_KEY`
   - Value: Your DeepL API key
   - Click "Add secret"

3. **Automatic Fallback**:
   - If DeepL is configured but fails, the workflow automatically falls back to LibreTranslate
   - This ensures translations always work, even if quota limits are reached

## Files Added

- `.github/workflows/translate-issues.yml` - GitHub Actions workflow definition
- `scripts/translate.js` - Node.js translation script (no external dependencies)
- `README_TRANSLATION_INTEGRATION.md` - This documentation file

## Privacy & Data Considerations

### Data Flow

**Default (LibreTranslate)**:
- Text is sent to the public LibreTranslate instance at `https://libretranslate.de`
- LibreTranslate is an open-source, self-hosted service
- Review their privacy policy: [https://libretranslate.com/privacy](https://libretranslate.com/privacy)

**With DeepL (Optional)**:
- Text is sent to DeepL's API at `https://api-free.deepl.com`
- DeepL processes translations according to their privacy policy
- Review their policy: [https://www.deepl.com/privacy](https://www.deepl.com/privacy)

### Important Notes

1. **Public Issues**: This workflow only processes public issue content that is already visible on GitHub.

2. **Sensitive Information**: Do not include sensitive information (passwords, API keys, personal data) in issues or comments. This is a general GitHub best practice regardless of translation.

3. **Bot Comments**: All translation comments are clearly marked as automated and include a reference to the original text.

4. **Rate Limits**: 
   - LibreTranslate: Generally has no strict rate limits but may be slower during high usage
   - DeepL Free: 500,000 characters/month
   - DeepL Pro: Higher limits based on subscription

## Customization

### Change Target Language

To translate to a different language, edit `.github/workflows/translate-issues.yml`:

```yaml
env:
  TARGET_LANG: 'DE'  # Change to: FR, ES, IT, etc.
```

Supported languages depend on the translation provider:
- **DeepL**: DE, FR, IT, ES, PT, NL, PL, RU, JA, ZH, and more
- **LibreTranslate**: Many languages (check [https://libretranslate.com](https://libretranslate.com))

### Disable the Workflow

To temporarily disable the translation workflow:

1. Go to the Actions tab in your repository
2. Find "Übersetze Issues & Kommentare → Deutsch" in the workflow list
3. Click the "..." menu → "Disable workflow"

To re-enable, follow the same steps and select "Enable workflow".

## Troubleshooting

### Workflow Not Running

- Check that the workflow file is in `.github/workflows/` directory
- Verify GitHub Actions are enabled for your repository (Settings → Actions → General)
- Check the Actions tab for any error messages

### Translation Not Appearing

- Check the Actions tab for workflow run logs
- Verify the issue/comment contains translatable text
- Ensure the text isn't already marked with `[Übersetzung — DE]`

### DeepL Not Working

- Verify the `DEEPL_API_KEY` secret is correctly set
- Check you haven't exceeded your monthly character limit
- The workflow will automatically fall back to LibreTranslate

### Rate Limit Issues

- For DeepL: Monitor your usage in the DeepL API dashboard
- For LibreTranslate: Consider self-hosting your own instance if you need higher reliability

## Definition of Done (DoD)

This integration is considered complete when:

✅ **Workflow File**:
- [x] `.github/workflows/translate-issues.yml` is present and valid
- [x] Workflow triggers on issue and comment events
- [x] Correct permissions are set (read contents, write issues)

✅ **Translation Script**:
- [x] `scripts/translate.js` exists and is executable by Node.js 18+
- [x] Uses only built-in Node.js APIs (no external npm dependencies)
- [x] Supports both LibreTranslate (default) and DeepL (optional)
- [x] Implements idempotent behavior (updates existing bot comments)
- [x] Marks translations with `[Übersetzung — DE]` prefix
- [x] Includes proper error handling and logging

✅ **Documentation**:
- [x] README documentation explains setup and usage
- [x] Privacy considerations are documented
- [x] Secret configuration instructions are clear
- [x] Troubleshooting guide is provided

✅ **Testing**:
- [x] Script syntax is valid
- [x] Workflow YAML is valid
- [x] Manual testing can be performed by creating a test issue

✅ **Commit & PR**:
- [x] Conventional commit format used
- [x] PR description summarizes changes
- [x] All required files are included

## Contributing

To improve this integration:

1. Test changes locally by setting environment variables and running the script
2. Update this documentation if you change functionality
3. Follow conventional commit guidelines for your commits

## License

This integration code follows the same license as the parent repository.
