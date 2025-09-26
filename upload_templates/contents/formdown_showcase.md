# Formdown form demo

Easily embed a [Formdown](https://www.formdown.net/) form within a Markdown document.
Replace the attribute values with the options from your form dashboard.

## Support request

<div
  data-formdown-form="your-formdown-form"
  data-formdown-theme="system"
  data-formdown-label-style="floating"
  data-formdown-success-title="Thanks for reaching out!"
  data-formdown-success-message="We received your message and will reply soon."
  data-formdown-button-label="Send message"
></div>

### Common options

- `data-formdown-theme` — switch between `light`, `dark`, or `system` themes.
- `data-formdown-label-style` — choose `floating` or `stacked` labels.
- `data-formdown-success-title` / `data-formdown-success-message` — customize the confirmation copy.
- `data-formdown-button-label` — override the submit button text.

> **Tip:** Viewer automatically adds the Formdown loader script to Markdown pages that
> include elements with `data-formdown-*` attributes, so the embed works without adding
> extra code.
